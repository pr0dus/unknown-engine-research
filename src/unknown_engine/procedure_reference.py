"""Frozen deterministic controls for the public procedure-validity diagnostic.

The policies accept only a public packet and an experiment callback. Study
operators enumerate the declared catalogue outside those policies. None of
these deterministic reference programs is an AI-model participant.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any, Callable

from .procedure import (
    ProcedureEngine, action_response, full_catalogue, operational_validity,
    prediction, restricted_catalogue,
)


POLICIES = ("blind_source", "always_reject", "legacy_check", "validate_then_repair", "fixed_sysid")
FREEZE_SCHEMA = "unknown-engine-procedure-freeze/0.1"
ARCHIVE_SCHEMA = "unknown-engine-procedure-reference-replays/0.1"
REPORT_SCHEMA = "unknown-engine-procedure-study/0.1"
SPEC_PATH = "docs/PROCEDURE_VALIDITY_PROTOCOL.md"
REQUIRED_FREEZE_PATHS = (
    SPEC_PATH, "src/unknown_engine/procedure.py", "src/unknown_engine/procedure_reference.py",
    "scripts/verify_procedure_gate.py",
)
OBSERVATION_TOLERANCE = 1e-12
DECISION_TOLERANCE = 1e-9

Packet = dict[str, Any]
Experiment = Callable[[dict[str, Any]], Packet]


def _standards() -> list[dict[str, Any]]:
    return [{"kind": "standard", "value": value} for value in (0, 1)]


def _legacy_actions() -> list[dict[str, Any]]:
    return _standards() + [
        {"kind": "reference", "commands": [1, 1], "sample_at": [2]},
        {"kind": "process", "commands": [1] * 32, "sample_at": [32]},
    ]


def _pulses(packet: Packet) -> list[dict[str, Any]]:
    if packet["profile"] == "restricted":
        return [{"kind": kind, "commands": [1], "sample_at": [1]}
                for kind in ("reference", "process")]
    return [
        {"kind": "reference", "commands": [1, 0], "sample_at": [1, 2]},
        {"kind": "process", "commands": [1, 0, 0, 0], "sample_at": [1, 2, 3, 4]},
    ]


def _observe(packet: Packet, experiment: Experiment, actions: list[dict[str, Any]]) -> Packet:
    for action in actions:
        packet = experiment(action)
    return packet


def _source_answer(packet: Packet, decision: str) -> dict[str, Any]:
    return {"decision": decision, "predictions": prediction(packet["source_model"])}


def blind_source(packet: Packet, experiment: Experiment) -> dict[str, Any]:
    """Uninformed positive control; zero target actions."""
    return _source_answer(packet, "valid")


def always_reject(packet: Packet, experiment: Experiment) -> dict[str, Any]:
    """Uninformed negative control; zero target actions and no repaired model."""
    return _source_answer(packet, "invalid")


def _legacy_fit(packet: Packet) -> tuple[dict[str, Any], bool]:
    # Called only after the declared four actions. Every value is an observation.
    zero, one, reference, process = packet["history"][-4:]
    bias = zero["observations"][0]
    gain = one["observations"][0] - bias
    actuator = (reference["observations"][0] - bias) / gain
    ratio = (process["observations"][0] - bias) / gain / actuator
    model = dict(packet["source_model"], c=actuator)
    return model, 0.95 <= ratio <= 1.05


def legacy_check(packet: Packet, experiment: Experiment) -> dict[str, Any]:
    """Follow the inherited steady-response guard and donor transient model."""
    if packet["access"]["max_sequence_length"] < 32:
        return _source_answer(packet, "undetermined")
    packet = _observe(packet, experiment, _legacy_actions())
    model, passes = _legacy_fit(packet)
    return {"decision": "valid" if passes else "invalid", "predictions": prediction(model),
            "legacy_guard_passed": passes}


def _posterior_answer(packet: Packet) -> dict[str, Any]:
    remaining = []
    for candidate in packet["rules"]["catalogue"]:
        compatible = True
        for row in packet["history"]:
            expected = action_response(candidate, row["action"])
            observed = row["observations"]
            if len(expected) != len(observed) or any(
                    abs(a - b) > OBSERVATION_TOLERANCE for a, b in zip(expected, observed)):
                compatible = False
                break
        if compatible:
            remaining.append(candidate)
    if not remaining:
        raise ValueError("No declared model matches the public observations.")
    validities = {operational_validity(model, packet["profile"]) for model in remaining}
    decision = "undetermined" if len(validities) > 1 else "valid" if validities == {True} else "invalid"
    forecasts = [prediction(model) for model in remaining]
    predictions = {key: math.fsum(row[key] for row in forecasts) / len(forecasts)
                   for key in forecasts[0]}
    return {"decision": decision, "predictions": predictions,
            "hypotheses_remaining": len(remaining)}


def validate_then_repair(packet: Packet, experiment: Experiment) -> dict[str, Any]:
    """Execute the inherited check, then test its omitted transient assumptions."""
    if packet["profile"] == "restricted":
        packet = _observe(packet, experiment, _standards() + _pulses(packet))
        return _posterior_answer(packet)
    packet = _observe(packet, experiment, _legacy_actions())
    _, passes = _legacy_fit(packet)
    packet = _observe(packet, experiment, _pulses(packet))
    return dict(_posterior_answer(packet), legacy_guard_passed=passes)


def fixed_sysid(packet: Packet, experiment: Experiment) -> dict[str, Any]:
    """A fixed four-call identification script; the strong simple control."""
    packet = _observe(packet, experiment, _standards() + _pulses(packet))
    return _posterior_answer(packet)


def run_policy(name: str, packet: Packet, experiment: Experiment) -> dict[str, Any]:
    if name not in POLICIES:
        raise ValueError("Unknown frozen policy.")
    return globals()[name](packet, experiment)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_freeze(freeze_path: Path, repository: Path | None = None) -> dict[str, Any]:
    """Verify the specification and source byte hashes before any study world."""
    repository = (repository or Path(__file__).resolve().parents[2]).resolve()
    raw = freeze_path.read_bytes()
    record = json.loads(raw)
    if not isinstance(record, dict) or record.get("schema") != FREEZE_SCHEMA:
        raise ValueError("Unsupported procedure freeze record.")
    expected = record.get("files")
    if not isinstance(expected, dict) or not set(REQUIRED_FREEZE_PATHS).issubset(expected):
        raise ValueError("Freeze must include the development specification, both implementation modules and independent verifier.")
    actual = {}
    for name, digest in expected.items():
        if (not isinstance(name, str) or Path(name).is_absolute() or ".." in Path(name).parts
                or not isinstance(digest, str) or re.fullmatch(r"[0-9a-f]{64}", digest) is None):
            raise ValueError("Freeze paths must be repository-relative and SHA-256 hashes must be lowercase hexadecimal.")
        path = (repository / name).resolve()
        if not path.is_relative_to(repository) or not path.is_file():
            raise ValueError("A frozen file is missing or outside the repository.")
        actual[name] = _sha(path)
        if actual[name] != digest:
            raise ValueError("Frozen file changed: " + name)
    return {"freeze_sha256": hashlib.sha256(raw).hexdigest(), "files": actual}


def _aggregate(rows: list[dict[str, Any]]) -> dict[str, Any]:
    results = [row["replay"]["state"]["result"] for row in rows]
    count = len(results)
    average = lambda key: math.fsum(result[key] for result in results) / count
    cost_average = lambda field: {
        key: math.fsum(result[field][key] for result in results) / count
        for key in ("ticks", "resets", "samples", "units", "experiment_calls")
    }
    return {
        "runs": count,
        "mean_squared_physical_prediction_error": average("mse"),
        "maximum_absolute_error": max(result["max_absolute_error"] for result in results),
        "decision_counts": {key: sum(result["decision"] == key for result in results)
                            for key in ("valid", "invalid", "undetermined")},
        "warranted_decision_correct_count": sum(result["warranted_decision_correct"] for result in results),
        "warranted_decision_correct_fraction": average("warranted_decision_correct"),
        "hidden_validity_agreement_count": sum(bool(result["hidden_validity_agreement"]) for result in results),
        "hidden_validity_agreements_without_warrant_count": sum(
            bool(result["hidden_validity_agreement"]) and not result["warranted_decision_correct"]
            for result in results),
        "invalid_model_acceptance_count": sum(result["invalid_model_acceptance"] for result in results),
        "valid_model_rejection_count": sum(result["valid_model_rejection"] for result in results),
        "undetermined_count": sum(result["undetermined"] for result in results),
        "mean_target_costs": cost_average("target_costs"),
        "mean_source_costs": cost_average("source_costs"),
        "mean_total_costs": cost_average("total_costs"),
    }


def run_study(output: Path, freeze_path: Path) -> dict[str, Any]:
    """Execute the disclosed diagnostic only after source/specification freeze."""
    if output.exists():
        raise ValueError("Output must be a new directory; prior evidence is never overwritten.")
    freeze = verify_freeze(freeze_path)
    frozen_bytes = freeze_path.read_bytes()
    if hashlib.sha256(frozen_bytes).hexdigest() != freeze["freeze_sha256"]:
        raise ValueError("Freeze record changed before study execution.")
    records = []
    for profile, catalogue in (("full", full_catalogue()), ("restricted", restricted_catalogue())):
        for fixture_number, model in enumerate(catalogue):
            for name in POLICIES:
                engine = ProcedureEngine(model, profile=profile, budget=64)
                answer = run_policy(name, engine.state(), engine.experiment)
                engine.submit({"decision": answer["decision"], "predictions": answer["predictions"]})
                records.append({
                    "fixture_id": f"{profile}-{fixture_number:03d}", "profile": profile, "policy": name,
                    "policy_summary": {key: value for key, value in answer.items() if key != "predictions"},
                    "replay": engine.replay(),
                })
    profiles = {
        profile: {name: _aggregate([row for row in records if row["profile"] == profile and row["policy"] == name])
                  for name in POLICIES}
        for profile in ("full", "restricted")
    }
    fixed = profiles["full"]["fixed_sysid"]
    expected_ceiling = (fixed["runs"] == 192 and fixed["maximum_absolute_error"] <= DECISION_TOLERANCE
                        and fixed["warranted_decision_correct_count"] == 192
                        and fixed["mean_target_costs"]["units"] == 16)
    guard_failure = profiles["full"]["legacy_check"]["invalid_model_acceptance_count"] > 0
    warranted_abstention = all(
        profiles["restricted"][name]["undetermined_count"] == 2
        and profiles["restricted"][name]["warranted_decision_correct_count"] == 2
        for name in ("validate_then_repair", "fixed_sysid"))
    report = {
        "schema": REPORT_SCHEMA, "freeze_sha256": freeze["freeze_sha256"], "frozen_files": freeze["files"],
        "fixture_count": 194, "record_count": len(records), "policies": list(POLICIES),
        "profiles": profiles,
        "warranted_decision_criterion": "Access-profile criterion: full-access decisions agree with hidden operational validity; restricted-access decisions must be undetermined. This does not certify actual policy reasoning or validate whether its particular history warranted its answer.",
        "expected_shortcut_observed": expected_ceiling,
        "legacy_guard_failure_observed": guard_failure,
        "restricted_identification_warranted_abstention_observed": warranted_abstention,
        "disposition": ("Regression diagnostic passed; frontier-difficulty claim rejected; redesign required before a frontier trial."
                        if expected_ceiling and guard_failure and warranted_abstention else "An expected diagnostic gate failed; investigate implementation/protocol mismatch before making any difficulty claim."),
        "independent_verification": "Not established by this runner; use the separately implemented verifier on this complete archive.",
        "limitations": [
            "All 192 full configurations and both restricted fixtures are disclosed development cases, not sampled independent trials.",
            "Policies are deterministic programs, not language models. Twenty-four outputs within a world are not independent trials.",
            "No population confidence interval, posterior-calibration, external validity, independent discovery or real-use claim is made.",
            "The source fixture costs 16 units per run; this comparison does not test whether source transfer saved resources.",
            "Warranted-decision correctness uses full-access truth or restricted-access undetermined as the frozen criterion, not an assessment of actual agent reasoning.",
            "Uninformed restricted-access guesses receive no warranted-decision credit even when they match the hidden validity.",
            "Costs count resets, command ticks and samples; computation, inference tokens, money and physical time are not measured.",
            "Local hashes are neither an external timestamp nor evidence of participant isolation or referee honesty.",
        ],
    }
    archive = {"schema": ARCHIVE_SCHEMA, "freeze_sha256": freeze["freeze_sha256"], "records": records}
    if verify_freeze(freeze_path) != freeze:
        raise ValueError("Freeze record or frozen files changed during the study.")
    output.mkdir(parents=True)
    (output / "freeze.json").write_bytes(frozen_bytes)
    archive_path = output / "replays.json.gz"
    with archive_path.open("wb") as target:
        with gzip.GzipFile(fileobj=target, mode="wb", filename="", mtime=0) as stream:
            stream.write(json.dumps(archive, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8"))
    report["archive_sha256"] = _sha(archive_path)
    (output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path, help="New output directory; existing evidence is refused.")
    parser.add_argument("--freeze", required=True, type=Path, help="Specification and implementation SHA-256 freeze record.")
    args = parser.parse_args(argv)
    report = run_study(args.output, args.freeze)
    print(json.dumps({key: report[key] for key in ("record_count", "expected_shortcut_observed", "disposition")}, indent=2))


if __name__ == "__main__":
    main()
