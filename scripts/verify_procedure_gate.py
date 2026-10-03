"""Independent audit of the procedure-validity development diagnostic.

No engine or policy modules are imported. Physical responses are calculated by
an analytic impulse-response convolution using rational arithmetic, rather than
the engine's state recurrence. A successful audit establishes reconstruction of
this disclosed finite diagnostic, not participant isolation or external review.
"""

from __future__ import annotations

from collections import Counter
from fractions import Fraction
from functools import lru_cache
import gzip
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
POLICIES = ("blind_source", "always_reject", "legacy_check", "validate_then_repair", "fixed_sysid")
PARAMETERS = ("stages", "rho", "K", "g", "b", "c", "d")
VALUES = ((1, 2), (0.5, 0.75), (1, 2), (1, 2), (0, 1), (0.5, 1, 2), (0, 1))
TARGET_COMMANDS = {
    "sustained": [1, 1, 1, 1, 1, 1],
    "alternating": [1, -1, 1, -1, 1, -1],
    "late_pulse": [0, 0, 1, 0, 0, 0],
    "reversal": [1, 1, -1, -1, 0, 0],
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def compare(actual, expected, where="value"):
    if isinstance(expected, dict):
        require(isinstance(actual, dict) and set(actual) == set(expected), "Wrong fields: " + where)
        for key, value in expected.items():
            compare(actual[key], value, where + "." + key)
    elif isinstance(expected, list):
        require(isinstance(actual, list) and len(actual) == len(expected), "Wrong length: " + where)
        for index, value in enumerate(expected):
            compare(actual[index], value, where + f"[{index}]")
    elif isinstance(expected, float):
        require(type(actual) in (int, float) and math.isfinite(actual)
                and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12),
                "Numeric mismatch: " + where)
    else:
        require(type(actual) is type(expected) and actual == expected, "Mismatch: " + where)


def source_model(profile):
    return dict(zip(PARAMETERS, (1, 0.5, 1, 1, 0, 1, 1 if profile == "restricted" else 0)))


def catalogue(profile):
    if profile == "restricted":
        return [dict(source_model(profile), stages=stage) for stage in (1, 2)]
    require(profile == "full", "Unknown access profile.")
    return [dict(zip(PARAMETERS, values)) for values in itertools.product(*VALUES)]


def physical_response(model, commands):
    """Physical q after each update, using the closed-form impulse response."""
    rho = Fraction(model["rho"])
    gain = Fraction(model["K"]) * Fraction(model["c"])
    stage, delay = model["stages"], model["d"]
    result = []
    for sample in range(1, len(commands) + 1):
        value = Fraction(0)
        for index, command in enumerate(commands):
            age = sample - index - delay - stage
            if age < 0 or not command:
                continue
            # Cascade convolution: (age + 1) geometric terms for two stages.
            multiplicity = age + 1 if stage == 2 else 1
            value += gain * command * (1 - rho) ** stage * multiplicity * rho ** age
        result.append(value)
    return result


def _observations(model, action):
    gain, bias = Fraction(model["g"]), Fraction(model["b"])
    if action["kind"] == "standard":
        return [float(gain * action["value"] + bias)]
    commands = action["commands"]
    if action["kind"] == "reference":
        physical = [Fraction(model["c"]) * (commands[index - model["d"]]
                    if index >= model["d"] else 0) for index in range(len(commands))]
    else:
        require(action["kind"] == "process", "Unknown action kind.")
        physical = physical_response(model, commands)
    return [float(gain * physical[index - 1] + bias) for index in action["sample_at"]]


@lru_cache(maxsize=4096)
def _cached_observations(model_values, action_json):
    return tuple(_observations(dict(zip(PARAMETERS, model_values)), json.loads(action_json)))


def observations(model, action):
    return list(_cached_observations(tuple(model[key] for key in PARAMETERS),
                                    json.dumps(action, sort_keys=True, separators=(",", ":"))))


def transient(kind, commands, samples=None):
    return {"kind": kind, "commands": commands,
            "sample_at": samples if samples is not None else list(range(1, len(commands) + 1))}


def expected_actions(profile, policy):
    require(policy in POLICIES, "Unknown policy.")
    standards = [{"kind": "standard", "value": value} for value in (0, 1)]
    if policy in ("blind_source", "always_reject") or (profile == "restricted" and policy == "legacy_check"):
        return []
    if profile == "restricted":
        return standards + [transient("reference", [1]), transient("process", [1])]
    legacy = standards + [transient("reference", [1, 1], [2]), transient("process", [1] * 32, [32])]
    pulses = [transient("reference", [1, 0]), transient("process", [1, 0, 0, 0])]
    if policy == "legacy_check":
        return legacy
    return (legacy if policy == "validate_then_repair" else standards) + pulses


def action_cost(action):
    return {"resets": int(action["kind"] != "standard"),
            "ticks": len(action.get("commands", [])),
            "samples": 1 if action["kind"] == "standard" else len(action["sample_at"]),
            "experiment_calls": 1}


def total_cost(actions):
    counts = {key: sum(action_cost(action)[key] for action in actions)
              for key in ("resets", "ticks", "samples", "experiment_calls")}
    counts["units"] = counts["resets"] + counts["ticks"] + counts["samples"]
    return counts


@lru_cache(maxsize=256)
def _forecast(model_values):
    model = dict(zip(PARAMETERS, model_values))
    return {key: [float(value) for value in physical_response(model, commands)]
            for key, commands in TARGET_COMMANDS.items()}


def forecast(model):
    return _forecast(tuple(model[key] for key in PARAMETERS))


def flat_forecast(model):
    return {f"{name}@{step}": value for name, series in forecast(model).items()
            for step, value in enumerate(series, 1)}


def is_valid(model, profile):
    inherited = dict(source_model(profile), c=model["c"])
    actual, predicted = forecast(model), forecast(inherited)
    return all(abs(a - b) <= 1e-9 for key in actual for a, b in zip(actual[key], predicted[key]))


@lru_cache(maxsize=1)
def audit_identifiability():
    """Prove the stated finite catalogue property independently of its engine."""
    actions = expected_actions("full", "fixed_sysid")
    signatures = {}
    for model in catalogue("full"):
        signature = tuple(value for action in actions for value in observations(model, action))
        require(signature not in signatures, "Fixed script fails full-catalogue identification.")
        signatures[signature] = model
        # Independently recover parameters with the stated ratio shortcut.
        b, top = signature[:2]
        g = top - b
        reference = [(value - b) / g for value in signature[2:4]]
        d = int(reference[0] == 0)
        c = reference[d]
        pulse = [(value - b) / g for value in signature[4:]]
        first = next(index for index, value in enumerate(pulse) if value != 0)
        ratio = pulse[first + 1] / pulse[first]
        stages = 1 if ratio in (0.5, 0.75) else 2
        rho = ratio / stages
        K = pulse[first] / (c * (1 - rho) ** stages)
        recovered = dict(zip(PARAMETERS, (stages, rho, K, g, b, c, d)))
        compare(recovered, {key: float(value) if key not in ("stages", "d") else value
                            for key, value in model.items()}, "shortcut")
    require(total_cost(actions)["units"] == 16, "Wrong fixed-script cost.")
    left, right = catalogue("restricted")
    # These are all legal actions in the restricted profile, not merely the
    # chosen reference script. Reset before every call makes repetition futile.
    legal = ([{"kind": "standard", "value": value} for value in (0, 1)] +
             [transient(kind, [command]) for kind in ("reference", "process") for command in (-1, 0, 1)])
    require(all(observations(left, action) == observations(right, action) for action in legal),
            "Restricted pair is distinguishable by a legal action.")
    require(is_valid(left, "restricted") and not is_valid(right, "restricted"), "Wrong restricted validity pair.")
    require(forecast(left) != forecast(right), "Restricted operational targets do not differ.")
    return {"full_configurations": len(signatures), "full_signatures_unique": True,
            "fixed_script_target_units": 16, "restricted_legal_actions": len(legal),
            "restricted_indistinguishable": True, "restricted_operational_targets_differ": True}


def aggregate(results):
    count = len(results)
    average = lambda key: math.fsum(row[key] for row in results) / count
    return {
        "runs": count,
        "mean_squared_physical_prediction_error": average("mse"),
        "maximum_absolute_error": max(row["max_absolute_error"] for row in results),
        "decision_counts": {decision: sum(row["decision"] == decision for row in results)
                            for decision in ("valid", "invalid", "undetermined")},
        "warranted_decision_correct_count": sum(row["warranted_decision_correct"] for row in results),
        "warranted_decision_correct_fraction": average("warranted_decision_correct"),
        "hidden_validity_agreement_count": sum(bool(row["hidden_validity_agreement"]) for row in results),
        "hidden_validity_agreements_without_warrant_count": sum(
            bool(row["hidden_validity_agreement"]) and not row["warranted_decision_correct"] for row in results),
        "invalid_model_acceptance_count": sum(row["invalid_model_acceptance"] for row in results),
        "valid_model_rejection_count": sum(row["valid_model_rejection"] for row in results),
        "undetermined_count": sum(row["undetermined"] for row in results),
        **{"mean_" + field: {key: math.fsum(row[field][key] for row in results) / count
                              for key in ("ticks", "resets", "samples", "units", "experiment_calls")}
           for field in ("target_costs", "source_costs", "total_costs")},
    }


def canonical_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     allow_nan=False).encode("utf-8")).hexdigest()


def check_freeze(directory):
    raw = (directory / "freeze.json").read_bytes()
    freeze = json.loads(raw)
    require(freeze.get("schema") == "unknown-engine-procedure-freeze/0.1", "Wrong freeze schema.")
    files = freeze.get("files")
    required = {"docs/PROCEDURE_VALIDITY_PROTOCOL.md", "src/unknown_engine/procedure.py",
                "src/unknown_engine/procedure_reference.py", "scripts/verify_procedure_gate.py"}
    require(isinstance(files, dict) and required.issubset(files), "Missing required frozen sources.")
    for name, digest in files.items():
        require(isinstance(name, str) and not Path(name).is_absolute() and ".." not in Path(name).parts,
                "Unsafe frozen path.")
        path = (ROOT / name).resolve()
        require(path.is_relative_to(ROOT) and path.is_file(), "Frozen source missing or outside repository.")
        require(type(digest) is str and len(digest) == 64 and all(char in "0123456789abcdef" for char in digest),
                "Malformed frozen SHA-256.")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == digest, "Frozen source changed: " + name)
    return hashlib.sha256(raw).hexdigest(), files


def policy_answer(profile, policy, history):
    source = source_model(profile)
    if policy in ("blind_source", "always_reject"):
        return {"decision": "valid" if policy == "blind_source" else "invalid", "predictions": flat_forecast(source)}
    if policy == "legacy_check" and profile == "restricted":
        return {"decision": "undetermined", "predictions": flat_forecast(source)}
    guard = None
    if profile == "full" and policy in ("legacy_check", "validate_then_repair"):
        b = history[0]["observations"][0]
        g = history[1]["observations"][0] - b
        c = (history[2]["observations"][0] - b) / g
        ratio = (history[3]["observations"][0] - b) / g / c
        guard = 0.95 <= ratio <= 1.05
        if policy == "legacy_check":
            return {"decision": "valid" if guard else "invalid", "predictions": flat_forecast(dict(source, c=c)),
                    "legacy_guard_passed": guard}
    hypotheses = [model for model in catalogue(profile) if all(
        all(abs(a - b) <= 1e-12 for a, b in zip(observations(model, row["action"]), row["observations"]))
        for row in history)]
    require(bool(hypotheses), "Empty independently reconstructed posterior.")
    labels = {is_valid(model, profile) for model in hypotheses}
    decision = "undetermined" if len(labels) > 1 else "valid" if True in labels else "invalid"
    forecasts = [flat_forecast(model) for model in hypotheses]
    answer = {"decision": decision,
              "predictions": {key: math.fsum(row[key] for row in forecasts) / len(forecasts) for key in forecasts[0]},
              "hypotheses_remaining": len(hypotheses)}
    if guard is not None:
        answer["legacy_guard_passed"] = guard
    return answer


def expected_result(model, profile, answer, target_costs):
    predictions, outcomes = answer["predictions"], flat_forecast(model)
    errors = [predictions[key] - outcomes[key] for key in outcomes]
    valid = is_valid(model, profile)
    truth = "valid" if valid else "invalid"
    warranted = truth if profile == "full" else "undetermined"
    decision = answer["decision"]
    source_costs = total_cost(expected_actions("full", "fixed_sysid"))
    return {
        "decision": decision, "truth_validity": truth, "warranted_decision": warranted,
        "warranted_decision_correct": decision == warranted,
        "decision_scoring_scope": "Access-scoped label agreement, not certification of the policy's evidence: full compares to hidden validity; restricted requires undetermined.",
        "hidden_validity_agreement": decision == truth,
        "invalid_model_acceptance": int(not valid and decision == "valid"),
        "valid_model_rejection": int(valid and decision == "invalid"),
        "undetermined": decision == "undetermined",
        "mse": math.fsum(error * error / len(errors) for error in errors),
        "max_absolute_error": max(abs(error) for error in errors),
        "predictions": predictions, "outcomes": outcomes,
        "target_costs": target_costs, "source_costs": source_costs,
        "total_costs": {key: target_costs[key] + source_costs[key] for key in target_costs},
    }


def expected_state(profile, history, result):
    source = source_model(profile)
    return {
        "protocol": "unknown-engine/procedure-validity-0.1", "profile": profile, "finished": True,
        "access": {"max_sequence_length": 32 if profile == "full" else 1,
                   "target_unit_budget": 64, "remaining_units": 64 - result["target_costs"]["units"]},
        "source_model": source,
        "source_data": [{"action": action, "observations": observations(source, action), "cost": total_cost([action])}
                        for action in expected_actions("full", "fixed_sysid")],
        "source_procedure": {
            "actions": expected_actions("full", "legacy_check"),
            "calibration": "Infer b and g from standards 0 and 1. Infer c from the calibrated reference [1,1] sample at 2.",
            "guard": "Run process command 1 for 32 ticks. Divide the calibrated final physical response by c; accept if it lies in [0.95,1.05].",
            "prediction": "Predict with the donor's stages, rho, K, and d, using inferred target c.",
            "scope": "Approximately settled response check; transient assumptions are not tested. This recipe cannot execute under restricted access.",
            "provenance": "Referee-written fixture and procedure, not independently discovered by a participant.",
        },
        "rules": {
            "catalogue": catalogue(profile),
            "state_reset": "Every reference/process experiment starts with zero states and zero commands before index zero.",
            "actuator": "At zero-based index t, u[t]=c*a[t-d]; commands before index zero are zero.",
            "single_stage": "q_next=rho*q+(1-rho)*K*u[t]. Sample after updating.",
            "two_stage": "v_next=rho*v+(1-rho)*K*u[t]; q_next=rho*q+(1-rho)*v using OLD v. Updates are simultaneous.",
            "sensor": "Process observes g*q_next+b; certified reference load bypasses process and observes g*u[t]+b; certified standard bypasses actuator and process and observes g*value+b.",
            "commands": [-1, 0, 1], "standard_values": [0, 1],
            "observations": "Noiseless floats; requested samples use strictly increasing one-based indices. The finite family is public.",
            "cost": "One unit per command tick, reset, and requested sample. A standard costs one sample only. Experiment calls are counted separately, not charged twice.",
            "validity": "Donor stages/rho/K/d with true target c must match every operational physical target within 1e-9.",
            "prediction_score": "Mean squared physical prediction error; not Brier loss or accuracy. Abstention does not erase forecast error.",
            "observation_tolerance": 1e-12, "validity_tolerance": 1e-9,
            "decision_scoring": "Access-scoped label rule: full access agrees with hidden validity; restricted access requires undetermined. This scores labels, not proof that a policy gathered adequate evidence.",
        },
        "targets": [{"key": f"{name}@{step}", "sequence": name, "step": step, "commands": commands}
                    for name, commands in TARGET_COMMANDS.items() for step in range(1, 7)],
        "forecast_keys": list(result["outcomes"]),
        "costs": result["target_costs"], "source_costs": result["source_costs"],
        "history": history, "result": result,
    }


def audit_record(record, model):
    require(isinstance(record, dict) and set(record) == {"fixture_id", "profile", "policy", "policy_summary", "replay"},
            "Wrong archive record fields.")
    profile, policy, replay = record["profile"], record["policy"], record["replay"]
    require(isinstance(replay, dict) and set(replay) == {"schema", "protocol", "finished", "state", "disclosure", "sha256"},
            "Wrong replay fields.")
    require(replay["schema"] == "unknown-engine/procedure-validity-0.1/replay"
            and replay["protocol"] == "unknown-engine/procedure-validity-0.1" and replay["finished"] is True,
            "Wrong replay schema or completion.")
    compare(replay["disclosure"], {"model": model, "profile": profile, "budget": 64}, "disclosure")
    require(replay["sha256"] == canonical_digest({key: value for key, value in replay.items() if key != "sha256"}),
            "Replay content hash mismatch.")
    actions = expected_actions(profile, policy)
    history = [{"step": index + 1, "action": action, "observations": observations(model, action),
                "cost": total_cost([action]), "cumulative_cost": total_cost(actions[:index + 1])}
               for index, action in enumerate(actions)]
    answer = policy_answer(profile, policy, history)
    compare(record["policy_summary"], {key: value for key, value in answer.items() if key != "predictions"}, "policy_summary")
    result = expected_result(model, profile, answer, total_cost(actions))
    compare(replay["state"], expected_state(profile, history, result), record["fixture_id"] + "." + policy)
    return result, len(history)


def verify_directory(directory):
    directory = Path(directory)
    freeze_digest, files = check_freeze(directory)
    report = json.loads((directory / "report.json").read_bytes())
    archive_bytes = (directory / "replays.json.gz").read_bytes()
    require(archive_bytes[:2] == b"\x1f\x8b" and archive_bytes[4:8] == b"\0\0\0\0", "Expected deterministic gzip mtime zero.")
    archive = json.loads(gzip.decompress(archive_bytes))
    require(isinstance(archive, dict) and set(archive) == {"schema", "freeze_sha256", "records"}, "Wrong archive fields.")
    require(archive["schema"] == "unknown-engine-procedure-reference-replays/0.1", "Wrong archive schema.")
    require(report["schema"] == "unknown-engine-procedure-study/0.1", "Wrong report schema.")
    require(archive["freeze_sha256"] == report["freeze_sha256"] == freeze_digest, "Freeze digest mismatch.")
    compare(report["frozen_files"], files, "frozen_files")
    require(report["archive_sha256"] == hashlib.sha256(archive_bytes).hexdigest(), "Archive SHA-256 mismatch.")
    fixtures = {f"{profile}-{index:03d}": (profile, model)
                for profile in ("full", "restricted") for index, model in enumerate(catalogue(profile))}
    expected_order = [(fixture, policy) for fixture in fixtures for policy in POLICIES]
    records = archive["records"]
    require(isinstance(records, list) and len(records) == len(expected_order), "Expected all 970 fixture-policy records.")
    verified, experiment_count = {}, 0
    for index, record in enumerate(records):
        key = record["fixture_id"], record["policy"]
        require(key == expected_order[index], "Missing, duplicate, reordered or unexpected fixture-policy record.")
        profile, model = fixtures[key[0]]
        require(record["profile"] == profile, "Wrong fixture profile.")
        result, count = audit_record(record, model)
        verified[key] = result
        experiment_count += count
    expected_profiles = {profile: {policy: aggregate([verified[(fixture, policy)] for fixture, (kind, _) in fixtures.items() if kind == profile])
                                  for policy in POLICIES} for profile in ("full", "restricted")}
    compare(report["profiles"], expected_profiles, "profiles")
    compare(report["fixture_count"], 194, "fixture_count")
    compare(report["record_count"], 970, "record_count")
    compare(report["policies"], list(POLICIES), "policies")
    fixed = expected_profiles["full"]["fixed_sysid"]
    ceiling = (fixed["runs"] == 192 and fixed["maximum_absolute_error"] <= 1e-9
               and fixed["warranted_decision_correct_count"] == 192 and fixed["mean_target_costs"]["units"] == 16)
    guard_failure = expected_profiles["full"]["legacy_check"]["invalid_model_acceptance_count"] > 0
    abstention = all(expected_profiles["restricted"][policy]["undetermined_count"] == 2
                     and expected_profiles["restricted"][policy]["warranted_decision_correct_count"] == 2
                     for policy in ("validate_then_repair", "fixed_sysid"))
    compare(report["expected_shortcut_observed"], ceiling, "expected_shortcut_observed")
    compare(report["legacy_guard_failure_observed"], guard_failure, "legacy_guard_failure_observed")
    compare(report["restricted_identification_warranted_abstention_observed"], abstention,
            "restricted_identification_warranted_abstention_observed")
    disposition = ("Regression diagnostic passed; frontier-difficulty claim rejected; redesign required before a frontier trial."
                   if ceiling and guard_failure and abstention else
                   "An expected diagnostic gate failed; investigate implementation/protocol mismatch before making any difficulty claim.")
    compare(report["disposition"], disposition, "disposition")
    require(report["warranted_decision_criterion"] == "Access-profile criterion: full-access decisions agree with hidden operational validity; restricted-access decisions must be undetermined. This does not certify actual policy reasoning or validate whether its particular history warranted its answer.",
            "Wrong warranted-decision criterion.")
    return {"verified": True, "records": len(verified), "fixtures": len(fixtures), "experiments": experiment_count,
            "source_hashes_verified": len(files), "freeze_sha256": freeze_digest,
            "analytic_identifiability": audit_identifiability(), "disposition": disposition,
            "scope": "Separate analytic-convolution reconstruction of every disclosed observation, policy action, forecast, label, cost and aggregate. Not external replication, a signature, a timestamp, participant isolation or real-world validation."}


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/verify_procedure_gate.py EVIDENCE_DIRECTORY")
    try:
        result = verify_directory(sys.argv[1])
    except (OSError, KeyError, TypeError, ValueError, OverflowError, RecursionError) as exc:
        print(json.dumps({"verified": False, "error": str(exc)}, indent=2))
        raise SystemExit(1) from exc
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
