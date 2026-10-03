"""Independently audit matched priors, decisions, forecasts, and aggregates.

This verifier deliberately does not import transfer_matched. Its priors are
enumerated from the full source-and-change generative process; raw source
polynomials use exact Lagrange interpolation, rather than the participant's
Gaussian elimination. Existing engine replay reconstruction is a second check.
"""

from __future__ import annotations

from collections import defaultdict
from fractions import Fraction
from functools import lru_cache
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from unknown_engine.transfer import verify_transfer_replay  # noqa: E402

PROTOCOL = "unknown-engine-transfer-matched/0.1"
ARMS = {"donor_method_bayes": "method", "donor_raw_bayes": "raw", "cold_bayes_same_policy": "none"}
CONDITIONS = ("none", "sensor", "mechanism", "both")
EXPECTED_FIXTURES = {f"{condition}-{index:03d}": condition for condition in CONDITIONS for index in range(8)}
FIXTURE_PREFIX = "unknown-engine-transfer-public-development-fixture-v1"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def compare(actual, expected, where):
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and set(actual) == set(expected), "Wrong fields: " + where)
        for key, value in expected.items():
            compare(actual[key], value, where + "." + key)
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), "Wrong length: " + where)
        for i, value in enumerate(expected):
            compare(actual[i], value, where + f"[{i}]")
    elif isinstance(expected, float):
        require(type(actual) in (int, float) and math.isfinite(actual) and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12),
                "Numeric mismatch: " + where)
    else:
        require(type(actual) is type(expected) and actual == expected, "Mismatch: " + where)


def polynomial(coefficients, x):
    result = 0
    for coefficient in reversed(coefficients):
        result = result * x + coefficient
    return result


def recover_source(initial):
    artifact = initial.get("artifact")
    if artifact is not None:
        return tuple(artifact["coefficients"]), artifact["source_calibration"]["gain"], artifact["source_calibration"]["bias"]
    raw = initial.get("source_data")
    if raw is None:
        return None
    anchors = {row["value"]: Fraction(row["observation"]) for row in raw["calibration"]}
    offset = anchors[0]
    scale = anchors[1] - offset
    points = [(Fraction(row["x"]), (Fraction(row["observation"]) - offset) / scale) for row in raw["process"]]
    coefficients = [Fraction(0) for _ in range(4)]
    for i, (x, y) in enumerate(points):
        basis, denominator = [Fraction(1)], Fraction(1)
        for j, (other_x, _) in enumerate(points):
            if i == j:
                continue
            expanded = [Fraction(0)] * (len(basis) + 1)
            for k, value in enumerate(basis):
                expanded[k] -= other_x * value
                expanded[k + 1] += value
            basis = expanded
            denominator *= x - other_x
        for k, value in enumerate(basis):
            coefficients[k] += y * value / denominator
    require(all(value.denominator == 1 for value in coefficients), "Noninteger reconstructed donor.")
    return tuple(int(value) for value in coefficients), float(scale), float(offset)


@lru_cache(maxsize=128)
def enumerate_prior(coefficient_values, deltas, gains, biases, source):
    """Directly sum source worlds and four conditions, without symmetry shortcuts."""
    models = defaultdict(int)
    source_coefficients = itertools.product(coefficient_values, repeat=4) if source is None else (source[0],)
    for coefficients in source_coefficients:
        for gain in (gains if source is None else (source[1],)):
            for bias in (biases if source is None else (source[2],)):
                changed_coefficients = []
                for index in range(4):
                    for delta in deltas:
                        values = list(coefficients)
                        values[index] += delta
                        changed_coefficients.append((tuple(values), 1))
                changed_sensors = [(new_gain, new_bias, 1) for new_gain in gains for new_bias in biases
                                   if new_gain != gain and new_bias != bias]
                for condition in CONDITIONS:
                    mechanisms = changed_coefficients if condition in ("mechanism", "both") else [(coefficients, len(changed_coefficients))]
                    sensors = changed_sensors if condition in ("sensor", "both") else [(gain, bias, len(changed_sensors))]
                    for target_coefficients, weight_m in mechanisms:
                        for target_gain, target_bias, weight_s in sensors:
                            models[(target_coefficients, target_gain, target_bias)] += weight_m * weight_s
    return tuple((key, weight) for key, weight in sorted(models.items()))


def predicted_reading(model, action):
    coefficients, gain, bias = model
    upstream = action["value"] if action["kind"] == "calibrate" else polynomial(coefficients, action["x"])
    return gain * upstream + bias


def audit_policy(initial, observations, policy):
    rules = initial["public_rules"]
    require(rules["condition_prior"] == {condition: 0.25 for condition in CONDITIONS}, "Unexpected condition prior.")
    models = dict(enumerate_prior(tuple(rules["source_coefficient_values"]), tuple(rules["coefficient_delta_values"]),
                                  tuple(rules["source_gain_values"]), tuple(rules["source_bias_values"]), recover_source(initial)))
    actions = ([{"kind": "calibrate", "value": value} for value in rules["calibration_values"]] +
               [{"kind": "probe", "x": x} for x in rules["probe_values"]])
    trace = []
    for step in range(initial["budget_total"] + 1):
        weight = sum(models.values())
        require(weight > 0, "Empty posterior.")
        probabilities = {}
        risk = Fraction(0)
        certain = True
        for target in initial["targets"]:
            count = sum(w for (coefficients, _, _), w in models.items()
                        if polynomial(coefficients, target["x"]) >= target["threshold"])
            p = Fraction(count, weight)
            probabilities[target["key"]] = float(p)
            risk += p * (1 - p) / len(initial["targets"])
            certain = certain and count in (0, weight)
        stop = "zero_forecast_uncertainty" if certain else ("budget_exhausted" if step == initial["budget_total"] else None)
        selected, entropy = None, None
        if not stop:
            entropies = []
            bucket_counts = []
            for action in actions:
                outcomes = defaultdict(int)
                for model, w in models.items():
                    outcomes[predicted_reading(model, action)] += w
                entropies.append(-math.fsum((w / weight) * math.log2(w / weight) for w in outcomes.values()))
                bucket_counts.append(len(outcomes))
            largest = max(entropies) if entropies else -1
            if all(count == 1 for count in bucket_counts):
                stop, entropy = "no_informative_action", largest
            else:
                index = next(i for i, value in enumerate(entropies) if largest - value <= 1e-12)
                selected, entropy = actions[index], entropies[index]
        trace.append({"step": step, "hypotheses": len(models), "probabilities": probabilities,
                      "posterior_expected_brier": float(risk), "selected_action": selected,
                      "observation_entropy_bits": entropy, "stopping_reason": stop})
        if stop:
            require(len(observations) == step, "Experiments continue after the common stopping rule.")
            expected = {"probabilities": probabilities, "posterior_expected_brier": float(risk), "stopping_reason": stop, "trace": trace}
            compare(policy, expected, "policy")
            return expected
        require(step < len(observations), "Missing experiment before stopping.")
        observation = observations[step]
        require(observation["action"] == selected, "Greedy action differs from independently enumerated policy.")
        models = {model: w for model, w in models.items() if predicted_reading(model, selected) == observation["observation"]}
        actions.remove(selected)
    raise ValueError("Policy did not stop.")


def aggregate(rows):
    budget = rows[0]["budget"]
    result = {"worlds": len(rows)}
    for field in ("brier", "target_cost", "donor_cost", "total_cost", "posterior_expected_brier"):
        result["mean_" + field] = math.fsum(row[field] for row in rows) / len(rows)
    result["zero_forecast_uncertainty_worlds"] = sum(row["stop"] == "zero_forecast_uncertainty" for row in rows)
    result["resolved_before_budget_fraction"] = sum(row["stop"] == "zero_forecast_uncertainty" and row["target_cost"] < budget for row in rows) / len(rows)
    result["resolved_at_budget_fraction"] = sum(row["stop"] == "zero_forecast_uncertainty" and row["target_cost"] == budget for row in rows) / len(rows)
    result["stopping_cost_counts"] = {str(cost): sum(row["target_cost"] == cost for row in rows) for cost in range(budget + 1)}
    return result


def _resolve(path):
    path = Path(path)
    return path if path.is_absolute() else ROOT / path


def verify_directory(directory):
    directory = Path(directory)
    report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    envelope = json.loads(gzip.decompress((directory / "replays.json.gz").read_bytes()))
    require(report["schema"] == PROTOCOL + "/report" and envelope["schema"] == PROTOCOL + "/replays", "Wrong matched protocol.")
    provenance = report["provenance"]
    for key in ("source_replays", "specification", "policy_source", "engine_source"):
        data = _resolve(provenance[key + "_path"]).read_bytes()
        require(hashlib.sha256(data).hexdigest() == provenance[key + "_sha256"], "Changed provenance file: " + key)
    source_path = _resolve(provenance["source_replays_path"])
    source_data = source_path.read_bytes()
    original = json.loads(gzip.decompress(source_data) if source_path.suffix == ".gz" else source_data)
    require(original["schema"] == "unknown-engine-transfer-reference-replays/0.1", "Wrong archived fixture schema.")
    fixtures = {}
    for record in original["records"]:
        replay = record["replay"]
        require(verify_transfer_replay(replay).get("valid"), "Archived fixture replay failed reconstruction.")
        value = (record["condition"], replay["disclosure"]["seed"], replay["disclosure"]["config"])
        require(record["condition"] == value[2]["condition"], "Archived condition mismatch.")
        if record["world_id"] in fixtures:
            require(fixtures[record["world_id"]] == value, "Archived physical pairing mismatch.")
        fixtures[record["world_id"]] = value
    require(set(fixtures) == set(EXPECTED_FIXTURES), "Expected exactly the original 32 named public fixtures.")
    require(all(value[0] == EXPECTED_FIXTURES[world] and value[1] == FIXTURE_PREFIX + ":" + world for world, value in fixtures.items()),
            "Canonical fixture conditions or seeds changed.")
    records = envelope["records"]
    indexed, actions_by_key, probabilities_by_key = {}, {}, {}
    entries = 0
    for record in records:
        world, name, budget = record["world_id"], record["participant"], record["budget"]
        require(world in fixtures and name in ARMS and type(budget) is int and budget in range(5), "Unknown record key.")
        key = world, name, budget
        require(key not in indexed, "Duplicate record.")
        replay = record["replay"]
        checked = verify_transfer_replay(replay)
        require(checked.get("valid") is True, "Matched replay reconstruction failed: " + str(checked.get("error")))
        entries += checked["entries"]
        require(replay["arm"] == ARMS[name] and replay["budget_total"] == budget, "Arm or budget mismatch.")
        condition, seed, config = fixtures[world]
        require(record["condition"] == condition and replay["disclosure"]["seed"] == seed and replay["disclosure"]["config"] == config,
                "Matched replay is not the archived physical fixture.")
        initial = replay["transcript"][0]["data"]["initial_state"]
        observations = [entry["data"] for entry in replay["transcript"] if entry["kind"] == "experiment"]
        audited = audit_policy(initial, observations, record["policy"])
        result = replay["state"]["result"]
        compare(result["probabilities"], audited["probabilities"], "submitted posterior")
        targets = initial["targets"]
        outcomes = {target["key"]: int(polynomial(config["target"]["coefficients"], target["x"]) >= target["threshold"]) for target in targets}
        require(outcomes == result["outcomes"], "Outcome mismatch.")
        brier = math.fsum((audited["probabilities"][key] - outcome) ** 2 for key, outcome in outcomes.items()) / len(targets)
        donor_cost, target_cost = (0 if ARMS[name] == "none" else 6), len(observations)
        require(all(row["cost"] == 1 for row in observations), "Nonunit experiment cost.")
        for field, expected in {"primary_brier": brier, "donor_cost": donor_cost, "target_cost": target_cost, "total_cost": donor_cost + target_cost}.items():
            compare(result[field], expected, field)
        indexed[key] = {"brier": brier, "target_cost": target_cost, "donor_cost": donor_cost, "total_cost": donor_cost + target_cost,
                        "posterior_expected_brier": audited["posterior_expected_brier"], "stop": audited["stopping_reason"], "budget": budget}
        actions_by_key[key] = [row["action"] for row in observations]
        probabilities_by_key[key] = audited["probabilities"]
    require(set(indexed) == {(world, name, budget) for world in fixtures for name in ARMS for budget in range(5)}, "Incomplete record grid.")
    for world in fixtures:
        for budget in range(5):
            method, raw = (world, "donor_method_bayes", budget), (world, "donor_raw_bayes", budget)
            require(indexed[method] == indexed[raw] and actions_by_key[method] == actions_by_key[raw] and probabilities_by_key[method] == probabilities_by_key[raw],
                    "Equivalent method/raw information produces different behavior.")
            for name in ARMS:
                prefix = actions_by_key[(world, name, budget)]
                longest = actions_by_key[(world, name, 4)]
                require(prefix == longest[:len(prefix)], "Action path is not a common prefix across budgets.")
    curves = {name: {str(budget): {
        "overall": aggregate([indexed[(world, name, budget)] for world in fixtures]),
        "by_condition": {condition: aggregate([indexed[(world, name, budget)] for world in fixtures if fixtures[world][0] == condition]) for condition in CONDITIONS}}
        for budget in range(5)} for name in ARMS}
    compare(report["curves"], curves, "curves")
    paired = {}
    for budget in range(5):
        pairs = [(indexed[(world, "donor_method_bayes", budget)], indexed[(world, "cold_bayes_same_policy", budget)]) for world in fixtures]
        paired[str(budget)] = {"worlds": len(fixtures),
                              "mean_brier_difference_donor_minus_cold": math.fsum(d["brier"] - c["brier"] for d, c in pairs) / len(pairs),
                              "mean_target_experiments_saved": math.fsum(c["target_cost"] - d["target_cost"] for d, c in pairs) / len(pairs),
                              "donor_lower_loss_worlds": sum(d["brier"] < c["brier"] - 1e-12 for d, c in pairs),
                              "equal_loss_worlds": sum(abs(d["brier"] - c["brier"]) <= 1e-12 for d, c in pairs),
                              "donor_higher_loss_worlds": sum(d["brier"] > c["brier"] + 1e-12 for d, c in pairs)}
    compare(report["paired_donor_minus_cold"], paired, "paired differences")
    donor, cold = curves["donor_method_bayes"]["4"]["overall"], curves["cold_bayes_same_policy"]["4"]["overall"]
    saving = cold["mean_target_cost"] - donor["mean_target_cost"]
    no_worse = donor["mean_brier"] <= cold["mean_brier"] + 1e-12
    projection = report["amortization_projection"]
    compare(projection["comparison"], {"budget_cap": 4, "donor_mean_brier": donor["mean_brier"], "cold_mean_brier": cold["mean_brier"],
                                      "donor_empirical_mean_loss_no_higher": no_worse, "mean_target_experiments_saved": saving}, "projection basis")
    compare(projection["rows"], [{"recipients": n, "donor_cost_once": 6,
                                  "projected_donor_total_cost": 6 + n * donor["mean_target_cost"],
                                  "projected_cold_total_cost": n * cold["mean_target_cost"],
                                  "projected_donor_cost_per_recipient": donor["mean_target_cost"] + 6 / n,
                                  "projected_cold_cost_per_recipient": cold["mean_target_cost"]} for n in (1, 2, 4, 8, 16)], "projection rows")
    expected_break_even = None
    if no_worse and saving > 0:
        ratio = Fraction(6) / Fraction(saving)
        expected_break_even = {"recipients_at_least_as_cheap": math.ceil(ratio), "recipients_for_strict_cost_saving": math.floor(ratio) + 1,
                               "exact_cost_equality_recipient_count": int(ratio) if ratio.denominator == 1 else None}
    compare(projection["break_even"], expected_break_even, "projection break-even")
    require(report["design"]["participants"] == ARMS and report["design"]["budget_caps"] == list(range(5)), "Wrong design controls.")
    require(report["design"]["worlds"] == len(fixtures) and report["design"]["records"] == len(records), "Wrong design counts.")
    require(provenance["fixtures_reused"] is True and provenance["model_calls"] == 0, "Incorrect provenance label.")
    return {"verified": True, "worlds": len(fixtures), "records": len(records), "receipt_entries": entries,
            "independent_full_generative_prior_enumeration": True, "independent_raw_lagrange_reconstruction": True,
            "independent_greedy_actions_stopping_and_posteriors": True, "independent_losses_costs_curves_and_projections": True,
            "raw_method_behavior_equal": True, "budget_action_prefixes_match": True,
            "archived_fixtures_and_specification_hashes_verified": True,
            "scope": "Exploratory reused development fixtures only; arithmetic amortization is not an observed recipient-cohort result."}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        raise SystemExit("Usage: verify_transfer_matched.py evidence-directory")
    try:
        result = verify_directory(args[0])
    except (OSError, EOFError, KeyError, TypeError, ValueError, OverflowError, zlib.error) as exc:
        print(json.dumps({"verified": False, "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
