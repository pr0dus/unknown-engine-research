"""Small, exactly observed diagnostic-transfer practice world.

This module is separate from the frozen 0.1 engine.  Its finite polynomial
family is deliberately public and enumerable; it is not a frontier benchmark
or evidence of a transfer advantage.  Only the operator owns this object.
Players receive defensive JSON-compatible state dictionaries.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import random
import secrets
from typing import Any


PROTOCOL = "unknown-engine/transfer-0.5-alpha.1"
FAMILY = "finite-cubic-affine-sensor/1"
CONDITIONS = ("none", "sensor", "mechanism", "both")
ARMS = ("method", "raw", "none", "blind")
COEFFICIENT_VALUES = (-2, -1, 1, 2)
DELTA_VALUES = (-2, -1, 1, 2)
GAIN_VALUES = (0.5, 1, 2)
BIAS_VALUES = (-2, 0, 2)
PROBE_VALUES = (-2, -1, -0.5, 0, 0.5, 1, 2)
DONOR_X = (-1, 0, 1, 2)
DONOR_COST = 6
MAX_BUDGET = 64
TARGETS = tuple(
    {"key": f"q@{x:g}>={threshold:g}", "x": x, "threshold": threshold}
    for x in (-1.5, -0.5, 0.5, 1.5)
    for threshold in (-2, 0, 2)
)
FORECAST_KEYS = tuple(target["key"] for target in TARGETS)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def polynomial(coefficients: list[float] | tuple[float, ...], x: float) -> float:
    """Evaluate ascending-power coefficients; all allowed world values are dyadic."""
    result = 0.0
    for coefficient in reversed(coefficients):
        result = result * x + coefficient
    return result


def _number(value: Any, lower: float, upper: float, field: str) -> float:
    # Check magnitude before conversion so huge Python integers cannot overflow.
    if type(value) not in (int, float) or not lower <= value <= upper:
        raise ValueError(f"{field} must be a finite number from {lower} to {upper}.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field} must be finite.")
    return result


def _public_rules() -> dict[str, Any]:
    return {
        "physical_response": "q(x)=a0+a1*x+a2*x^2+a3*x^3; degree at most three",
        "sensor": "z=g*q(x)+b; g is positive",
        "condition_prior": {condition: 0.25 for condition in CONDITIONS},
        "source_coefficient_values": list(COEFFICIENT_VALUES),
        "source_coefficients_independent_uniform": True,
        "source_gain_values": list(GAIN_VALUES),
        "source_bias_values": list(BIAS_VALUES),
        "source_gain_and_bias_independent_uniform": True,
        "sensor_change": "Both gain and bias change, each chosen uniformly from its source grid excluding its source value.",
        "mechanism_change": "Exactly one coefficient index is chosen uniformly and receives one independent uniform nonzero delta.",
        "coefficient_delta_values": list(DELTA_VALUES),
        "probe_values": list(PROBE_VALUES),
        "calibration_values": [0, 1],
        "calibration": "A known standardized reference value replaces the process output upstream of the same target sensor. It bypasses the process, so its reading is g*value+b.",
        "observations": "Noiseless, exact dyadic values; no rounding or unknown calibration error. The target is static and experiments do not alter it.",
        "forecast_event": "q(x)>=threshold, using the physical response, not the sensor reading",
        "experiment_cost": 1,
        "donor_experiment_cost": DONOR_COST,
        "scoring": "Mean squared probability error over all 12 binary targets (Brier loss); lower is better. Scores are revealed only after final submission.",
        "practice_validation": "Invalid requests are rejected without cost or state changes; this is not a ranked no-repair model trial.",
        "scope": "Known finite family, enumerable by a cold solver; this practice world establishes no novelty, frontier difficulty, or transfer advantage.",
    }


class TransferEngine:
    """Operator-side world; ``condition`` is an operator-only fixture control.

    A seed determines the physical world independently of arm and budget.
    A fresh random commitment salt means newly created copies have different
    receipts; disclosed replays can nevertheless be reconstructed exactly.
    """

    def __init__(self, seed: int | str | None = None, condition: str | None = None,
                 arm: str = "method", budget: int = 4):
        if condition is not None and (type(condition) is not str or condition not in CONDITIONS):
            raise ValueError("condition must be none, sensor, mechanism, both, or None.")
        if type(arm) is not str or arm not in ARMS:
            raise ValueError("arm must be method, raw, none, or blind.")
        if type(budget) is not int or not 0 <= budget <= MAX_BUDGET:
            raise ValueError(f"budget must be an integer from 0 to {MAX_BUDGET}.")
        if seed is not None:
            if type(seed) not in (int, str):
                raise ValueError("seed must be an integer, string, or None.")
            if (type(seed) is str and (not seed or len(seed) > 256)) or (type(seed) is int and seed.bit_length() > 800):
                raise ValueError("seed is empty or exceeds the fixture seed size limit.")
        self._seed = secrets.token_hex(32) if seed is None else str(seed)
        self.arm = arm
        self.budget_total = budget
        self._config = self._make_config(condition)
        self._history: list[dict[str, Any]] = []
        self._result: dict[str, Any] | None = None
        self._finished = False
        self._artifact, self._source_data = self._make_donor()
        self._start_transcript(secrets.token_hex(32))

    def _make_config(self, condition: str | None) -> dict[str, Any]:
        rng = random.Random(self._seed)
        source = {"coefficients": [rng.choice(COEFFICIENT_VALUES) for _ in range(4)],
                  "gain": rng.choice(GAIN_VALUES), "bias": rng.choice(BIAS_VALUES)}
        # Draw every candidate before selecting condition: paired conditions share
        # the same donor and potential changes, and arm never affects generation.
        gain = rng.choice([value for value in GAIN_VALUES if value != source["gain"]])
        bias = rng.choice([value for value in BIAS_VALUES if value != source["bias"]])
        coefficient = rng.randrange(4)
        delta = rng.choice(DELTA_VALUES)
        chosen = rng.choice(CONDITIONS) if condition is None else condition
        target = copy.deepcopy(source)
        if chosen in ("sensor", "both"):
            target.update(gain=gain, bias=bias)
        if chosen in ("mechanism", "both"):
            target["coefficients"][coefficient] += delta
        return {"condition": chosen, "source": source, "target": target,
                "changed_coefficient": coefficient if chosen in ("mechanism", "both") else None,
                "delta": delta if chosen in ("mechanism", "both") else 0}

    def _make_donor(self) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
        source = self._config["source"]
        raw = {"calibration": [{"value": value, "observation": source["gain"] * value + source["bias"]}
                               for value in (0, 1)],
               "process": [{"x": x, "observation": source["gain"] * polynomial(source["coefficients"], x) + source["bias"]}
                           for x in DONOR_X], "cost": DONOR_COST,
               "provenance": "Referee-generated six-measurement donor fixture; cost is six declared experiment units, not an independently observed participant discovery."}
        # Derive the reference method using only the six donor measurements.
        # Four-point cubic interpolation at -1, 0, 1, 2 is exact here.
        fitted_bias = raw["calibration"][0]["observation"]
        fitted_gain = raw["calibration"][1]["observation"] - fitted_bias
        measured = {row["x"]: (row["observation"] - fitted_bias) / fitted_gain
                    for row in raw["process"]}
        a0 = measured[0]
        odd_sum = (measured[1] - measured[-1]) / 2
        a2 = (measured[1] + measured[-1]) / 2 - a0
        a3 = (measured[2] - a0 - 4 * a2 - 2 * odd_sum) / 6
        fitted_coefficients = [a0, odd_sum - a3, a2, a3]
        if fitted_coefficients != source["coefficients"]:
            raise AssertionError("Donor fixture interpolation disagrees with its generator.")
        artifact = {
            "format": "ascending-cubic-coefficients/1",
            "coefficients": fitted_coefficients,
            "source_calibration": {"gain": fitted_gain, "bias": fitted_bias},
            "provenance": "Referee reference artifact derived by calibration and cubic interpolation from the six-measurement donor fixture; not independently discovered by a participant.",
            "assumptions": ["Degree at most three, ascending coefficient order.",
                            "Noiseless static process and one affine sensor shared by process and calibration references.",
                            "The two standardized references are exact and bypass the process."],
            "applicability": ["Recalibrate the target instrument before interpreting process measurements.",
                              "Compare corrected target probes with source predictions; the source equation may have changed.",
                              "Validity outside the declared family or probe domain is not established."],
            "donor_probe_values": list(DONOR_X),
            "donor_cost": DONOR_COST,
        }
        if self.arm in ("method", "blind"):
            return copy.deepcopy(artifact), None
        if self.arm == "raw":
            return None, raw
        return None, None

    def _start_transcript(self, salt: str) -> None:
        self._salt = salt
        self._commitment_payload = {"protocol": PROTOCOL, "family": FAMILY,
                                    "seed": self._seed, "salt": salt, "config": self._config,
                                    "arm": self.arm, "budget_total": self.budget_total}
        self._commitment = _digest(self._commitment_payload)
        self._transcript: list[dict[str, Any]] = []
        self._chain_head = "0" * 64
        initial = self.state()
        self._append("genesis", {"initial_state": initial})

    def _append(self, kind: str, data: dict[str, Any]) -> str:
        entry = {"index": len(self._transcript), "kind": kind,
                 "data": copy.deepcopy(data), "previous": self._chain_head}
        entry["hash"] = _digest(entry)
        self._transcript.append(entry)
        self._chain_head = entry["hash"]
        return self._chain_head

    def state(self) -> dict[str, Any]:
        state = {"protocol": PROTOCOL, "family": FAMILY, "arm": self.arm,
                 "budget_total": self.budget_total,
                 "budget_remaining": self.budget_total - len(self._history),
                 "step": len(self._history), "finished": self._finished,
                 "history": self._history, "artifact": self._artifact,
                 "source_data": self._source_data,
                 "forecast_keys": list(FORECAST_KEYS), "targets": list(TARGETS),
                 "public_rules": _public_rules(),
                 "donor_cost": 0 if self.arm == "none" else DONOR_COST,
                 "commitment": self._commitment, "chain_head": self._chain_head}
        if self._finished:
            state["result"] = self._result
        return copy.deepcopy(state)

    def experiment(self, action: dict[str, Any]) -> dict[str, Any]:
        if self._finished:
            raise ValueError("The world is finished.")
        if len(self._history) >= self.budget_total:
            raise ValueError("The target experiment budget is exhausted.")
        if type(action) is not dict or type(action.get("kind")) is not str:
            raise ValueError("action must be a calibration or probe object.")
        kind = action["kind"]
        if kind == "calibrate" and set(action) == {"kind", "value"}:
            value = _number(action["value"], 0, 1, "value")
            if value not in (0, 1):
                raise ValueError("Calibration value must be 0 or 1.")
            clean = {"kind": kind, "value": value}
            physical = value
        elif kind == "probe" and set(action) == {"kind", "x"}:
            value = _number(action["x"], -2, 2, "x")
            if value not in PROBE_VALUES:
                raise ValueError("Probe x must be one of the public probe_values.")
            clean = {"kind": kind, "x": value}
            physical = polynomial(self._config["target"]["coefficients"], value)
        else:
            raise ValueError("Unknown action or unexpected action fields.")
        target = self._config["target"]
        observation = target["gain"] * physical + target["bias"]
        row = {"step": len(self._history) + 1, "action": clean,
               "observation": observation, "cost": 1}
        self._history.append(row)
        self._append("experiment", row)
        return self.state()

    def submit(self, probabilities: dict[str, Any]) -> dict[str, Any]:
        if self._finished:
            raise ValueError("The world is finished.")
        if type(probabilities) is not dict or set(probabilities) != set(FORECAST_KEYS):
            raise ValueError("A probability for every forecast key, and no other fields, is required.")
        values = {key: _number(probabilities[key], 0, 1, key) for key in FORECAST_KEYS}
        outcomes = {target["key"]: int(polynomial(self._config["target"]["coefficients"], target["x"]) >= target["threshold"])
                    for target in TARGETS}
        loss = sum((values[key] - outcomes[key]) ** 2 for key in FORECAST_KEYS) / len(FORECAST_KEYS)
        receipt = self._append("forecast", {"probabilities": values,
                                             "experiments_used": len(self._history)})
        donor_cost = 0 if self.arm == "none" else DONOR_COST
        self._result = {"primary_brier": loss, "coverage": 1.0,
                        "constant_baseline": 0.25,
                        "experiments_used": len(self._history),
                        "target_cost": len(self._history), "donor_cost": donor_cost,
                        "total_cost": donor_cost + len(self._history),
                        "probabilities": values, "outcomes": outcomes,
                        "forecast_receipt_hash": receipt}
        self._finished = True
        self._append("outcome", self._result)
        return self.state()

    def replay(self, reveal: bool = False) -> dict[str, Any]:
        if type(reveal) is not bool:
            raise ValueError("reveal must be boolean.")
        if reveal and not self._finished:
            raise ValueError("Cannot disclose an unfinished world.")
        record = {"protocol": PROTOCOL, "family": FAMILY, "arm": self.arm,
                  "budget_total": self.budget_total, "finished": self._finished,
                  "commitment": self._commitment, "chain_head": self._chain_head,
                  "state": self.state(), "transcript": self._transcript}
        if reveal:
            record["disclosure"] = {"seed": self._seed, "salt": self._salt,
                                    "config": self._config,
                                    "commitment_payload": self._commitment_payload}
        return copy.deepcopy(record)


def verify_transfer_replay(record: dict[str, Any]) -> dict[str, Any]:
    """Reconstruct a completed disclosed replay, including scores and public state.

    Hashes are integrity checks, not signatures. An entire substituted record
    cannot be detected without an independently retained commitment/checkpoint.
    Undisclosed records deliberately do not receive a successful verification.
    """
    try:
        if type(record) is not dict or set(record) != {
                "protocol", "family", "arm", "budget_total", "finished",
                "commitment", "chain_head", "state", "transcript", "disclosure"}:
            raise ValueError("A completed disclosed replay with the exact schema is required.")
        if record["protocol"] != PROTOCOL or record["family"] != FAMILY or record["finished"] is not True:
            raise ValueError("Wrong protocol, family, or completion flag.")
        entries = record["transcript"]
        if type(entries) is not list or not 3 <= len(entries) <= MAX_BUDGET + 3:
            raise ValueError("Invalid transcript length.")
        # Bound serialized input before processing nested arbitrary structures.
        canonical = _canonical(record)
        if len(canonical) > 1_000_000:
            raise ValueError("Replay exceeds the size limit.")
        previous = "0" * 64
        for index, entry in enumerate(entries):
            if type(entry) is not dict or set(entry) != {"index", "kind", "data", "previous", "hash"}:
                raise ValueError("Invalid receipt schema.")
            unsigned = {"index": index, "kind": entry["kind"], "data": entry["data"], "previous": previous}
            if type(entry["index"]) is not int or entry["index"] != index or entry["previous"] != previous or entry["hash"] != _digest(unsigned):
                raise ValueError(f"Broken receipt chain at {index}.")
            previous = entry["hash"]
        if record["chain_head"] != previous:
            raise ValueError("Wrong chain head.")
        if entries[0]["kind"] != "genesis" or entries[-2]["kind"] != "forecast" or entries[-1]["kind"] != "outcome":
            raise ValueError("Invalid genesis/forecast/outcome ordering.")
        disclosure = record["disclosure"]
        if type(disclosure) is not dict or set(disclosure) != {"seed", "salt", "config", "commitment_payload"}:
            raise ValueError("Invalid disclosure schema.")
        salt = disclosure["salt"]
        if type(salt) is not str or len(salt) != 64 or any(c not in "0123456789abcdef" for c in salt):
            raise ValueError("Invalid commitment salt.")
        if type(disclosure["seed"]) is not str:
            raise ValueError("Disclosed seed must be a string.")
        restored = TransferEngine(seed=disclosure["seed"], condition=disclosure["config"]["condition"],
                                  arm=record["arm"], budget=record["budget_total"])
        if restored._config != disclosure["config"]:
            raise ValueError("Disclosed world does not match its seed.")
        restored._start_transcript(salt)
        for entry in entries[1:-2]:
            if entry["kind"] != "experiment":
                raise ValueError("Unexpected receipt before final forecast.")
            restored.experiment(entry["data"]["action"])
        restored.submit(entries[-2]["data"]["probabilities"])
        if _canonical(restored.replay(reveal=True)) != canonical:
            raise ValueError("Deterministic reconstruction disagrees with the replay.")
        return {"valid": True, "simulation_verified": True, "disclosure_verified": True,
                "entries": len(entries), "experiments": len(restored._history),
                "scope": "Full deterministic reconstruction including observations, scores, costs, and public state; not server authenticity or proof of participant isolation."}
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError) as exc:
        return {"valid": False, "simulation_verified": False, "error": str(exc)}
