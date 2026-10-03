"""Bounded, noiseless procedure-validity development diagnostic.

The public finite catalogue is deliberately identifiable by a short fixed
script under full access. Restricted access demonstrates missing information,
not a hard but solvable intelligence test. This module is separate from the
frozen forecasting and transfer engines.
"""

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
from typing import Any


PROTOCOL = "unknown-engine/procedure-validity-0.1"
REPLAY_SCHEMA = PROTOCOL + "/replay"
MAX_BUDGET = 64
VALIDITY_TOLERANCE = 1e-9
OBSERVATION_TOLERANCE = 1e-12
PARAMETERS = {
    "stages": (1, 2), "rho": (0.5, 0.75), "K": (1, 2),
    "g": (1, 2), "b": (0, 1), "c": (0.5, 1, 2), "d": (0, 1),
}
SEQUENCES = {
    "sustained": (1, 1, 1, 1, 1, 1),
    "alternating": (1, -1, 1, -1, 1, -1),
    "late_pulse": (0, 0, 1, 0, 0, 0),
    "reversal": (1, 1, -1, -1, 0, 0),
}
TARGETS = tuple({"key": f"{name}@{step}", "sequence": name, "step": step,
                 "commands": list(commands)}
                for name, commands in SEQUENCES.items() for step in range(1, 7))
FORECAST_KEYS = tuple(target["key"] for target in TARGETS)
COST_FIELDS = ("ticks", "resets", "samples", "units", "experiment_calls")


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _profile(profile: str) -> str:
    if type(profile) is not str or profile not in ("full", "restricted"):
        raise ValueError("profile must be full or restricted.")
    return profile


def _finite(value: Any, field: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{field} must be a finite number, not a boolean.")
    try:
        number = float(value)
    except (OverflowError, ValueError) as exc:
        raise ValueError(f"{field} cannot be represented as a finite number.") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field} must be finite.")
    return number


def _model(model: Any) -> dict[str, int | float]:
    if type(model) is not dict or set(model) != set(PARAMETERS):
        raise ValueError("model must contain exactly stages, rho, K, g, b, c, and d.")
    clean = {}
    for key, values in PARAMETERS.items():
        number = _finite(model[key], key)
        if key in ("stages", "d") and type(model[key]) is not int:
            raise ValueError(f"{key} must be an integer.")
        if number not in values:
            raise ValueError(f"{key} is outside the declared catalogue.")
        clean[key] = next(value for value in values if value == number)
    return clean


def full_catalogue() -> list[dict[str, int | float]]:
    """All 192 configurations in stable parameter-order lexicographic order."""
    return [dict(zip(PARAMETERS, values)) for values in itertools.product(*PARAMETERS.values())]


def source_model(profile: str = "full") -> dict[str, int | float]:
    _profile(profile)
    return {"stages": 1, "rho": 0.5, "K": 1, "g": 1, "b": 0,
            "c": 1, "d": 0 if profile == "full" else 1}


def restricted_catalogue() -> list[dict[str, int | float]]:
    return [dict(source_model("restricted"), stages=stages) for stages in (1, 2)]


def declared_catalogue(profile: str = "full") -> list[dict[str, int | float]]:
    return full_catalogue() if _profile(profile) == "full" else restricted_catalogue()


def standard_actions() -> list[dict[str, Any]]:
    return [{"kind": "standard", "value": value} for value in (0, 1)]


def pulse_actions(profile: str = "full") -> list[dict[str, Any]]:
    _profile(profile)
    if profile == "restricted":
        return [{"kind": kind, "commands": [1], "sample_at": [1]} for kind in ("reference", "process")]
    return [{"kind": "reference", "commands": [1, 0], "sample_at": [1, 2]},
            {"kind": "process", "commands": [1, 0, 0, 0], "sample_at": [1, 2, 3, 4]}]


def legacy_actions() -> list[dict[str, Any]]:
    return standard_actions() + [
        {"kind": "reference", "commands": [1, 1], "sample_at": [2]},
        {"kind": "process", "commands": [1] * 32, "sample_at": [32]},
    ]


def _action(action: Any, max_length: int = 32) -> dict[str, Any]:
    if type(action) is not dict or type(action.get("kind")) is not str:
        raise ValueError("action must be a standard, reference, or process object.")
    kind = action["kind"]
    if kind == "standard" and set(action) == {"kind", "value"}:
        value = _finite(action["value"], "value")
        if value not in (0, 1):
            raise ValueError("standard value must be 0 or 1.")
        return {"kind": kind, "value": int(value)}
    if kind not in ("reference", "process") or set(action) != {"kind", "commands", "sample_at"}:
        raise ValueError("Unknown action kind or unexpected action fields.")
    commands, sample_at = action["commands"], action["sample_at"]
    if type(commands) is not list or not 1 <= len(commands) <= max_length:
        raise ValueError(f"commands must be a list with 1 through {max_length} entries.")
    normalized = []
    for value in commands:
        number = _finite(value, "command")
        if number not in (-1, 0, 1):
            raise ValueError("commands must be -1, 0, or 1.")
        normalized.append(int(number))
    if (type(sample_at) is not list or not sample_at
            or any(type(index) is not int or not 1 <= index <= len(commands) for index in sample_at)
            or any(left >= right for left, right in zip(sample_at, sample_at[1:]))):
        raise ValueError("sample_at must be nonempty, strictly increasing one-based integer indices within commands.")
    return {"kind": kind, "commands": normalized, "sample_at": list(sample_at)}


def action_cost(action: dict[str, Any]) -> dict[str, int]:
    clean = _action(action)
    standard = clean["kind"] == "standard"
    ticks, resets, samples = (0, 0, 1) if standard else (len(clean["commands"]), 1, len(clean["sample_at"]))
    return {"ticks": ticks, "resets": resets, "samples": samples,
            "units": ticks + resets + samples, "experiment_calls": 1}


def _series(model: dict[str, Any], commands: list[int]) -> list[float]:
    q = v = 0.0
    outputs = []
    for t in range(len(commands)):
        u = model["c"] * commands[t - model["d"]] if t >= model["d"] else 0
        old_v = v
        if model["stages"] == 2:
            v = model["rho"] * old_v + (1 - model["rho"]) * model["K"] * u
            q = model["rho"] * q + (1 - model["rho"]) * old_v
        else:
            q = model["rho"] * q + (1 - model["rho"]) * model["K"] * u
        outputs.append(q)
    return outputs


def response(model: dict[str, Any], kind: str, commands: list[int], sample_at: list[int]) -> list[float]:
    """Deterministic observed samples; a standard uses commands=[value], sample_at=[1]."""
    clean_model = _model(model)
    if kind == "standard":
        if type(commands) is not list or len(commands) != 1 or sample_at != [1] or any(type(x) is not int for x in sample_at):
            raise ValueError("A standard uses commands=[value] and sample_at=[1].")
        action = _action({"kind": "standard", "value": commands[0]})
        return [clean_model["g"] * action["value"] + clean_model["b"]]
    action = _action({"kind": kind, "commands": commands, "sample_at": sample_at})
    if kind == "process":
        physical = _series(clean_model, action["commands"])
    else:
        physical = [clean_model["c"] * action["commands"][t - clean_model["d"]] if t >= clean_model["d"] else 0
                    for t in range(len(action["commands"]))]
    return [clean_model["g"] * physical[index - 1] + clean_model["b"] for index in action["sample_at"]]


def action_response(model: dict[str, Any], action: dict[str, Any]) -> list[float]:
    clean = _action(action)
    if clean["kind"] == "standard":
        return response(model, "standard", [clean["value"]], [1])
    return response(model, clean["kind"], clean["commands"], clean["sample_at"])


def prediction(model: dict[str, Any]) -> dict[str, float]:
    """The 24 physical q forecasts, before sensor gain and bias."""
    clean = _model(model)
    values = {name: _series(clean, list(commands)) for name, commands in SEQUENCES.items()}
    return {target["key"]: values[target["sequence"]][target["step"] - 1] for target in TARGETS}


def operational_validity(model: dict[str, Any], profile: str = "full") -> bool:
    """Operator/candidate-model label for donor predictions with true target c."""
    clean = _model(model)
    inherited = source_model(profile)
    inherited["c"] = clean["c"]
    expected, actual = prediction(inherited), prediction(clean)
    return all(abs(expected[key] - actual[key]) <= VALIDITY_TOLERANCE for key in FORECAST_KEYS)


def _zero_cost() -> dict[str, int]:
    return {key: 0 for key in COST_FIELDS}


def _sum_cost(first: dict[str, int], second: dict[str, int]) -> dict[str, int]:
    return {key: first[key] + second[key] for key in COST_FIELDS}


def _source_package(profile: str) -> tuple[list[dict[str, Any]], dict[str, int]]:
    source = source_model(profile)
    rows, costs = [], _zero_cost()
    for action in standard_actions() + pulse_actions("full"):
        cost = action_cost(action)
        rows.append({"action": action, "observations": action_response(source, action), "cost": cost})
        costs = _sum_cost(costs, cost)
    return rows, costs


class ProcedureEngine:
    """Operator-owned fixture; participant interfaces expose defensive copies."""

    def __init__(self, model: dict[str, Any], profile: str = "full", budget: int = MAX_BUDGET):
        self._model = _model(model)
        self.profile = _profile(profile)
        if self.profile == "restricted" and self._model not in restricted_catalogue():
            raise ValueError("Restricted fixtures contain only the two publicly declared stage possibilities.")
        if type(budget) is not int or not 0 <= budget <= MAX_BUDGET:
            raise ValueError(f"budget must be an integer from 0 through {MAX_BUDGET}.")
        self.budget = budget
        self._history: list[dict[str, Any]] = []
        self._costs = _zero_cost()
        self._source_data, self._source_costs = _source_package(profile)
        self._finished = False
        self._result: dict[str, Any] | None = None

    def state(self) -> dict[str, Any]:
        packet = {
            "protocol": PROTOCOL, "profile": self.profile, "finished": self._finished,
            "access": {"max_sequence_length": 32 if self.profile == "full" else 1,
                       "target_unit_budget": self.budget, "remaining_units": self.budget - self._costs["units"]},
            "source_model": source_model(self.profile), "source_data": self._source_data,
            "source_procedure": {
                "actions": legacy_actions(),
                "calibration": "Infer b and g from standards 0 and 1. Infer c from the calibrated reference [1,1] sample at 2.",
                "guard": "Run process command 1 for 32 ticks. Divide the calibrated final physical response by c; accept if it lies in [0.95,1.05].",
                "prediction": "Predict with the donor's stages, rho, K, and d, using inferred target c.",
                "scope": "Approximately settled response check; transient assumptions are not tested. This recipe cannot execute under restricted access.",
                "provenance": "Referee-written fixture and procedure, not independently discovered by a participant.",
            },
            "rules": {
                "catalogue": declared_catalogue(self.profile),
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
                "observation_tolerance": OBSERVATION_TOLERANCE,
                "validity_tolerance": VALIDITY_TOLERANCE,
                "decision_scoring": "Access-scoped label rule: full access agrees with hidden validity; restricted access requires undetermined. This scores labels, not proof that a policy gathered adequate evidence.",
            },
            "targets": list(TARGETS), "forecast_keys": list(FORECAST_KEYS),
            "costs": self._costs, "source_costs": self._source_costs,
            "history": self._history,
        }
        if self._finished:
            packet["result"] = self._result
        return copy.deepcopy(packet)

    def experiment(self, action: dict[str, Any]) -> dict[str, Any]:
        if self._finished:
            raise ValueError("The fixture is finished.")
        clean = _action(action, 32 if self.profile == "full" else 1)
        cost = action_cost(clean)
        cumulative = _sum_cost(self._costs, cost)
        if cumulative["units"] > self.budget:
            raise ValueError("The target experiment unit budget would be exceeded.")
        observations = action_response(self._model, clean)
        self._history.append({"step": len(self._history) + 1, "action": clean,
                              "observations": observations, "cost": cost, "cumulative_cost": cumulative})
        self._costs = cumulative
        return self.state()

    def submit(self, forecast: dict[str, Any]) -> dict[str, Any]:
        if self._finished:
            raise ValueError("The fixture is finished.")
        if type(forecast) is not dict or set(forecast) != {"decision", "predictions"}:
            raise ValueError("Submit exactly decision and predictions.")
        decision, predictions = forecast["decision"], forecast["predictions"]
        if type(decision) is not str or decision not in ("valid", "invalid", "undetermined"):
            raise ValueError("decision must be valid, invalid, or undetermined.")
        if type(predictions) is not dict or set(predictions) != set(FORECAST_KEYS):
            raise ValueError("Submit a prediction for every target, with no extra keys.")
        clean = {key: _finite(predictions[key], key) for key in FORECAST_KEYS}
        outcomes = prediction(self._model)
        errors = [clean[key] - outcomes[key] for key in FORECAST_KEYS]
        try:
            mse = math.fsum((error ** 2) / len(errors) for error in errors)
        except OverflowError as exc:
            raise ValueError("Predictions produce an unrepresentable squared error.") from exc
        if not math.isfinite(mse):
            raise ValueError("Predictions produce a nonfinite squared error.")
        valid = operational_validity(self._model, self.profile)
        truth = "valid" if valid else "invalid"
        warranted = truth if self.profile == "full" else "undetermined"
        result = {
            "decision": decision, "truth_validity": truth, "warranted_decision": warranted,
            "warranted_decision_correct": decision == warranted,
            "decision_scoring_scope": "Access-scoped label agreement, not certification of the policy's evidence: full compares to hidden validity; restricted requires undetermined.",
            "hidden_validity_agreement": decision == truth,
            "invalid_model_acceptance": int(not valid and decision == "valid"),
            "valid_model_rejection": int(valid and decision == "invalid"),
            "undetermined": decision == "undetermined", "mse": mse,
            "max_absolute_error": max(abs(error) for error in errors),
            "predictions": clean, "outcomes": outcomes,
            "target_costs": dict(self._costs), "source_costs": dict(self._source_costs),
            "total_costs": _sum_cost(self._costs, self._source_costs),
        }
        self._result, self._finished = result, True
        return self.state()

    def replay(self) -> dict[str, Any]:
        if not self._finished:
            raise ValueError("Cannot disclose an unfinished fixture.")
        record = {"schema": REPLAY_SCHEMA, "protocol": PROTOCOL, "finished": True,
                  "state": self.state(),
                  "disclosure": {"model": copy.deepcopy(self._model), "profile": self.profile, "budget": self.budget}}
        record["sha256"] = _digest(record)
        return record


def verify_procedure_replay(record: dict[str, Any]) -> dict[str, Any]:
    """Strict content-hash and deterministic reconstruction, not authenticity."""
    try:
        if type(record) is not dict or set(record) != {"schema", "protocol", "finished", "state", "disclosure", "sha256"}:
            raise ValueError("A completed disclosed replay with the exact schema is required.")
        if record["schema"] != REPLAY_SCHEMA or record["protocol"] != PROTOCOL or record["finished"] is not True:
            raise ValueError("Wrong replay schema, protocol, or completion flag.")
        canonical = _canonical(record)
        if len(canonical) > 1_000_000:
            raise ValueError("Replay exceeds the size limit.")
        unsigned = {key: value for key, value in record.items() if key != "sha256"}
        if record["sha256"] != _digest(unsigned):
            raise ValueError("Replay content hash mismatch.")
        disclosure = record["disclosure"]
        if type(disclosure) is not dict or set(disclosure) != {"model", "profile", "budget"}:
            raise ValueError("Wrong disclosure schema.")
        restored = ProcedureEngine(disclosure["model"], disclosure["profile"], disclosure["budget"])
        history = record["state"]["history"]
        if type(history) is not list or len(history) > MAX_BUDGET:
            raise ValueError("Invalid observation history.")
        for row in history:
            restored.experiment(row["action"])
        result = record["state"]["result"]
        restored.submit({"decision": result["decision"], "predictions": result["predictions"]})
        if _canonical(restored.replay()) != canonical:
            raise ValueError("Deterministic reconstruction disagrees with the replay.")
        return {"valid": True, "simulation_verified": True, "experiments": len(history),
                "scope": "Content hash and complete deterministic reconstruction of observations, costs, decisions, and scores. Not a signature, participant isolation, identity attestation, or independent timestamp."}
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError) as exc:
        return {"valid": False, "simulation_verified": False, "error": str(exc)}
