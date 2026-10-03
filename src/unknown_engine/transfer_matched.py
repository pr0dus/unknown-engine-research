"""Matched-policy follow-up on previously disclosed development fixtures.

Only the information supplied before the first target experiment differs.
All participants use the same greedy information-gain policy and stopping rule.
There are no model calls, hidden-test claims, or new physical-world families.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction
from functools import lru_cache
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path

from .transfer import TransferEngine, verify_transfer_replay


PROTOCOL = "unknown-engine-transfer-matched/0.1"
PARTICIPANTS = {"donor_method_bayes": "method", "donor_raw_bayes": "raw", "cold_bayes_same_policy": "none"}
BUDGETS = (0, 1, 2, 3, 4)
CONDITIONS = ("none", "sensor", "mechanism", "both")
COHORT_SIZES = (1, 2, 4, 8, 16)
ENTROPY_TIE_TOLERANCE = 1e-12
FIXTURE_PREFIX = "unknown-engine-transfer-public-development-fixture-v1"
EXPECTED_FIXTURES = {f"{condition}-{index:03d}": condition for condition in CONDITIONS for index in range(8)}


def _poly(coefficients, x):
    return sum(a * x ** k for k, a in enumerate(coefficients))


def _recover_source(state):
    """Recover exactly the same donor information from either public encoding."""
    artifact = state.get("artifact")
    if artifact is not None:
        return (tuple(artifact["coefficients"]), artifact["source_calibration"]["gain"],
                artifact["source_calibration"]["bias"])
    raw = state.get("source_data")
    if raw is None:
        return None
    anchors = {row["value"]: Fraction(row["observation"]) for row in raw["calibration"]}
    bias, gain = anchors[0], anchors[1] - anchors[0]
    rows = [[Fraction(row["x"]) ** k for k in range(4)] + [(Fraction(row["observation"]) - bias) / gain]
            for row in raw["process"]]
    for k in range(4):
        pivot = next(i for i in range(k, 4) if rows[i][k])
        rows[k], rows[pivot] = rows[pivot], rows[k]
        factor = rows[k][k]
        rows[k] = [value / factor for value in rows[k]]
        for i in range(4):
            if i != k:
                factor = rows[i][k]
                rows[i] = [a - factor * b for a, b in zip(rows[i], rows[k])]
    coefficients = tuple(row[-1] for row in rows)
    if any(value.denominator != 1 for value in coefficients):
        raise ValueError("Source data does not reconstruct the advertised integer family.")
    return tuple(int(value) for value in coefficients), float(gain), float(bias)


@lru_cache(maxsize=128)
def _make_prior(coeff_values, deltas, gains, biases, source):
    """Integer weights implement the published uniform four-condition prior."""
    coefficient_weights = defaultdict(int)
    source_vectors = itertools.product(coeff_values, repeat=4) if source is None else (source[0],)
    unchanged_weight = 4 * len(deltas)
    for coefficients in source_vectors:
        coefficient_weights[coefficients] += unchanged_weight
        for k in range(4):
            for delta in deltas:
                changed = list(coefficients)
                changed[k] += delta
                coefficient_weights[tuple(changed)] += 1
    if source is None:
        sensors = [(gain, bias, 1) for gain in gains for bias in biases]
    else:
        unchanged_sensor_weight = (len(gains) - 1) * (len(biases) - 1)
        sensors = [(source[1], source[2], unchanged_sensor_weight)]
        sensors += [(gain, bias, 1) for gain in gains for bias in biases if gain != source[1] and bias != source[2]]
    return tuple((coefficients, gain, bias, weight * sensor_weight)
                 for coefficients, weight in sorted(coefficient_weights.items())
                 for gain, bias, sensor_weight in sensors)


def public_prior(state):
    rules = state["public_rules"]
    if rules["condition_prior"] != {condition: 0.25 for condition in CONDITIONS}:
        raise ValueError("This reference supports the frozen uniform four-condition family only.")
    return _make_prior(tuple(rules["source_coefficient_values"]), tuple(rules["coefficient_delta_values"]),
                       tuple(rules["source_gain_values"]), tuple(rules["source_bias_values"]), _recover_source(state))


def _read(model, action):
    coefficients, gain, bias, _ = model
    value = action["value"] if action["kind"] == "calibrate" else _poly(coefficients, action["x"])
    return gain * value + bias


def _forecast(models, targets):
    weight = sum(model[3] for model in models)
    counts = {target["key"]: sum(model[3] for model in models if _poly(model[0], target["x"]) >= target["threshold"])
              for target in targets}
    probabilities = {key: count / weight for key, count in counts.items()}
    risk = sum(count * (weight - count) for count in counts.values()) / (len(counts) * weight * weight)
    certain = all(count in (0, weight) for count in counts.values())
    return probabilities, risk, certain


def _select_action(models, actions):
    total = sum(model[3] for model in models)
    scored = []
    for action in actions:
        bins = defaultdict(int)
        for model in models:
            bins[_read(model, action)] += model[3]
        value = -sum((weight / total) * math.log2(weight / total) for weight in bins.values())
        scored.append((action, value, len(bins)))
    if not scored:
        return None, -1.0, False
    if all(bucket_count == 1 for _, _, bucket_count in scored):
        return None, 0.0, False
    maximum = max(value for _, value, _ in scored)
    action, value, _ = next(row for row in scored if maximum - row[1] <= ENTROPY_TIE_TOLERANCE)
    return action, value, True


def matched_forecast(state, experiment):
    """Public-state-only participant; no seed, condition, or engine access."""
    models = public_prior(state)
    rules = state["public_rules"]
    actions = ([{"kind": "calibrate", "value": value} for value in rules["calibration_values"]] +
               [{"kind": "probe", "x": x} for x in rules["probe_values"]])
    trace = []
    for step in range(state["budget_total"] + 1):
        probabilities, risk, certain = _forecast(models, state["targets"])
        stop = "zero_forecast_uncertainty" if certain else ("budget_exhausted" if step == state["budget_total"] else None)
        action, entropy, informative = (None, None, False) if stop else _select_action(models, actions)
        if not stop and not informative:
            stop, action = "no_informative_action", None
        trace.append({"step": step, "hypotheses": len(models), "probabilities": probabilities,
                      "posterior_expected_brier": risk, "selected_action": action,
                      "observation_entropy_bits": entropy, "stopping_reason": stop})
        if stop:
            return {"probabilities": probabilities, "posterior_expected_brier": risk,
                    "stopping_reason": stop, "trace": trace}
        updated = experiment(action)
        observation = updated["history"][-1]["observation"]
        models = tuple(model for model in models if _read(model, action) == observation)
        if not models:
            raise ValueError("Observation is inconsistent with the published family and supplied donor information.")
        actions.remove(action)
    raise AssertionError("Budget loop did not terminate.")


def load_fixtures(path):
    """Operator-only extraction from completed, disclosed, existing evidence."""
    path = Path(path)
    data = path.read_bytes()
    payload = gzip.decompress(data) if path.suffix == ".gz" else data
    envelope = json.loads(payload)
    if envelope.get("schema") != "unknown-engine-transfer-reference-replays/0.1":
        raise ValueError("Expected the archived public development replay envelope.")
    fixtures, configs = {}, {}
    for record in envelope["records"]:
        replay = record["replay"]
        verified = verify_transfer_replay(replay)
        if not verified.get("valid"):
            raise ValueError("Input replay failed verification: " + str(verified.get("error")))
        world = record["world_id"]
        fixture = {"world_id": world, "condition": record["condition"], "seed": replay["disclosure"]["seed"]}
        if fixture["condition"] != replay["disclosure"]["config"]["condition"]:
            raise ValueError("Input condition mismatch.")
        if world in fixtures and (fixture != fixtures[world] or configs[world] != replay["disclosure"]["config"]):
            raise ValueError("Input participant worlds disagree.")
        fixtures[world], configs[world] = fixture, replay["disclosure"]["config"]
    ordered = [fixtures[key] for key in sorted(fixtures)]
    if set(fixtures) != set(EXPECTED_FIXTURES) or any(
            fixture["condition"] != EXPECTED_FIXTURES[fixture["world_id"]]
            or fixture["seed"] != FIXTURE_PREFIX + ":" + fixture["world_id"] for fixture in ordered):
        raise ValueError("Expected exactly the original 32 named public fixtures, eight per condition, with their canonical seeds.")
    return ordered, hashlib.sha256(data).hexdigest()


def _metrics(records):
    n = len(records)
    budget = records[0]["budget"]
    result = {"worlds": n}
    for key in ("primary_brier", "target_cost", "donor_cost", "total_cost"):
        name = "mean_brier" if key == "primary_brier" else "mean_" + key
        result[name] = sum(record["replay"]["state"]["result"][key] for record in records) / n
    result["mean_posterior_expected_brier"] = sum(record["policy"]["posterior_expected_brier"] for record in records) / n
    result["zero_forecast_uncertainty_worlds"] = sum(record["policy"]["stopping_reason"] == "zero_forecast_uncertainty" for record in records)
    resolved = [record for record in records if record["policy"]["stopping_reason"] == "zero_forecast_uncertainty"]
    result["resolved_before_budget_fraction"] = sum(record["replay"]["state"]["result"]["target_cost"] < budget for record in resolved) / n
    result["resolved_at_budget_fraction"] = sum(record["replay"]["state"]["result"]["target_cost"] == budget for record in resolved) / n
    result["stopping_cost_counts"] = {str(cost): sum(record["replay"]["state"]["result"]["target_cost"] == cost for record in records)
                                      for cost in range(budget + 1)}
    return result


def make_report(records, provenance):
    curves = {name: {str(budget): {
        "overall": _metrics([r for r in records if r["participant"] == name and r["budget"] == budget]),
        "by_condition": {condition: _metrics([r for r in records if r["participant"] == name and r["budget"] == budget and r["condition"] == condition]) for condition in CONDITIONS}}
        for budget in BUDGETS} for name in PARTICIPANTS}
    indexed = {(r["world_id"], r["participant"], r["budget"]): r for r in records}
    worlds = sorted({r["world_id"] for r in records})
    paired = {}
    for budget in BUDGETS:
        donors = [indexed[(world, "donor_method_bayes", budget)]["replay"]["state"]["result"] for world in worlds]
        cold = [indexed[(world, "cold_bayes_same_policy", budget)]["replay"]["state"]["result"] for world in worlds]
        paired[str(budget)] = {"worlds": len(worlds),
                               "mean_brier_difference_donor_minus_cold": sum(d["primary_brier"] - c["primary_brier"] for d, c in zip(donors, cold)) / len(worlds),
                               "mean_target_experiments_saved": sum(c["target_cost"] - d["target_cost"] for d, c in zip(donors, cold)) / len(worlds),
                               "donor_lower_loss_worlds": sum(d["primary_brier"] < c["primary_brier"] - 1e-12 for d, c in zip(donors, cold)),
                               "equal_loss_worlds": sum(abs(d["primary_brier"] - c["primary_brier"]) <= 1e-12 for d, c in zip(donors, cold)),
                               "donor_higher_loss_worlds": sum(d["primary_brier"] > c["primary_brier"] + 1e-12 for d, c in zip(donors, cold))}
    donor = curves["donor_method_bayes"]["4"]["overall"]
    cold = curves["cold_bayes_same_policy"]["4"]["overall"]
    saving = cold["mean_target_cost"] - donor["mean_target_cost"]
    no_worse_loss = donor["mean_brier"] <= cold["mean_brier"] + 1e-12
    comparable = {"budget_cap": 4, "donor_mean_brier": donor["mean_brier"], "cold_mean_brier": cold["mean_brier"],
                  "donor_empirical_mean_loss_no_higher": no_worse_loss,
                  "mean_target_experiments_saved": saving}
    projection = {"scope": "Arithmetic projection only. Assumes one six-experiment source reused across independent recipients with the suite's mean target costs and losses. No same-source recipient cohort was run; this assumption is untested.",
                  "comparison": comparable, "rows": [], "break_even": None}
    for n in COHORT_SIZES:
        projection["rows"].append({"recipients": n, "donor_cost_once": 6,
                                   "projected_donor_total_cost": 6 + n * donor["mean_target_cost"],
                                   "projected_cold_total_cost": n * cold["mean_target_cost"],
                                   "projected_donor_cost_per_recipient": donor["mean_target_cost"] + 6 / n,
                                   "projected_cold_cost_per_recipient": cold["mean_target_cost"]})
    if no_worse_loss and saving > 0:
        ratio = Fraction(6) / Fraction(saving)
        projection["break_even"] = {"recipients_at_least_as_cheap": math.ceil(ratio),
                                     "recipients_for_strict_cost_saving": math.floor(ratio) + 1,
                                     "exact_cost_equality_recipient_count": int(ratio) if ratio.denominator == 1 else None}
    return {"schema": PROTOCOL + "/report", "scope": "Matched-policy diagnostic on reused public development fixtures; zero model calls and no held-out or real-world claim.",
            "provenance": provenance,
            "design": {"participants": PARTICIPANTS, "budget_caps": list(BUDGETS), "worlds": len(worlds), "records": len(records),
                       "action_selection": "Greedy Shannon entropy of possible observation readings; calibration values in public order, then process probes in public order; first action within 1e-12 of the maximum wins.",
                       "stopping": "Stop when every forecast has posterior probability exactly 0 or 1, at budget exhaustion, or when every remaining action has exactly one possible reading; no repair, retry, or extra observation.",
                       "donor_information": "Method artifact and raw six-observation data encode identical source coefficients, gain, and bias; both receive the same conditional prior.",
                       "donor_cost": 6, "donor_cost_provenance": "Fixed six-observation referee-generated source fixture; not measured agent discovery or measured donor compute."},
            "curves": curves, "paired_donor_minus_cold": paired, "amortization_projection": projection,
            "limitations": ["This follow-up was designed after observing the earlier public-fixture results; it is exploratory, not a blinded or prospectively selected confirmation.",
                            "The matched policy is greedy one-step information gain, not optimal decision-theoretic experimental design.",
                            "Source information can reduce uncertainty; any benefit here does not establish an advantage of artifact format over equivalent raw data.",
                            "Compute, development effort, and human model-design costs are unmeasured; source cost is a fixed referee-fixture convention.",
                            "Finite noiseless family and exact calibration assumptions limit external validity."]}


def run_matched(fixtures, provenance):
    records = []
    for fixture in fixtures:
        for budget in BUDGETS:
            for name, arm in PARTICIPANTS.items():
                engine = TransferEngine(seed=fixture["seed"], condition=fixture["condition"], arm=arm, budget=budget)
                policy = matched_forecast(engine.state(), engine.experiment)
                engine.submit(policy["probabilities"])
                records.append({"world_id": fixture["world_id"], "condition": fixture["condition"],
                                "participant": name, "budget": budget, "policy": policy, "replay": engine.replay(True)})
    envelope = {"schema": PROTOCOL + "/replays", "records": records}
    return make_report(records, provenance), envelope


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="Previously disclosed transfer-preview replay file.")
    parser.add_argument("--spec", required=True, type=Path, help="Frozen study specification; record its hash before any execution.")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("Output directory already exists; matched evidence is never overwritten.")
    spec_bytes = args.spec.read_bytes()
    fixtures, source_hash = load_fixtures(args.input)
    provenance = {"source_replays_path": args.input.as_posix(), "source_replays_sha256": source_hash,
                  "specification_path": args.spec.as_posix(), "specification_sha256": hashlib.sha256(spec_bytes).hexdigest(),
                  "fixtures_reused": True, "model_calls": 0}
    for label, path in (("policy_source", Path(__file__)), ("engine_source", Path(__file__).with_name("transfer.py"))):
        provenance[label + "_path"] = "src/unknown_engine/" + path.name
        provenance[label + "_sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    report, envelope = run_matched(fixtures, provenance)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    data = (json.dumps(envelope, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    (args.output / "replays.json.gz").write_bytes(gzip.compress(data, mtime=0))
    print(json.dumps({"output": args.output.as_posix(), "worlds": len(fixtures), "records": len(envelope["records"]), "model_calls": 0}))


if __name__ == "__main__":
    main()
