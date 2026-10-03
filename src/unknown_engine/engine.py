"""Deterministic causal forecasting sandbox; no model or network dependencies.

Instance parameters remain secret until completion. The family of mechanics,
event definitions, scoring, action timing, and evaluation protocol are public.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
import random
import secrets
from typing import Any


VERSION = "unknown-engine/0.1.0"
SENSORS = ("flow", "reserve", "heat", "demand", "signal", "stability")
HORIZONS = (1, 3, 6)
EVENTS = (
    {"id": "shortfall", "description": "Demand exceeds reserve by at least 2: demand >= reserve + 2."},
    {"id": "overheat", "description": "The heat sensor reaches at least 6: heat >= 6."},
    {"id": "synchrony", "description": "Flow and signal differ by at most 1: abs(flow - signal) <= 1."},
)
FORECAST_KEYS = tuple(f"{event['id']}@{h}" for event in EVENTS for h in HORIZONS)


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def event_values(sensors: dict[str, int]) -> dict[str, int]:
    """Public predicates, evaluated at a point in time (not anywhere in a window)."""
    return {
        "shortfall": int(sensors["demand"] >= sensors["reserve"] + 2),
        "overheat": int(sensors["heat"] >= 6),
        "synchrony": int(abs(sensors["flow"] - sensors["signal"]) <= 1),
    }


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _brier(probabilities: dict[str, float], outcomes: dict[str, int]) -> float:
    return _mean([(probabilities[key] - outcomes[key]) ** 2 for key in FORECAST_KEYS])


def verify_replay(record: dict[str, Any]) -> dict[str, Any]:
    """Check integrity, commitment ordering, and optional seed disclosure.

    A hash chain is not a signature: a party able to replace the entire record
    can rewrite it. Publish or retain checkpoint hashes independently if needed.
    This verifier does not itself re-simulate the world or validate unchained
    replay.state fields such as score summaries; compare a re-simulated replay
    for that stronger check.
    """
    try:
        entries = record["transcript"]
        if not isinstance(entries, list) or not entries:
            raise ValueError("Missing transcript.")
        previous = "0" * 64
        pending: dict[int, str] = {}
        resolved: set[int] = set()
        for index, entry in enumerate(entries):
            expected = {"index": index, "kind": entry["kind"], "data": entry["data"], "previous": previous}
            if entry["index"] != index or entry["previous"] != previous or entry["hash"] != _digest(expected):
                raise ValueError(f"Broken hash chain at entry {index}.")
            if index == 0 and entry["kind"] != "genesis":
                raise ValueError("Missing genesis entry.")
            if entry["kind"] == "forecast":
                round_index = entry["data"]["round"]
                if round_index in pending or round_index in resolved:
                    raise ValueError("Duplicate forecast round.")
                pending[round_index] = entry["hash"]
            if entry["kind"] == "outcome":
                round_index = entry["data"]["round"]
                if pending.pop(round_index, None) != entry["data"]["forecast_entry_hash"]:
                    raise ValueError("Outcome without its prior forecast commitment.")
                resolved.add(round_index)
            previous = entry["hash"]
        if pending:
            raise ValueError("Unresolved forecast commitment.")
        if record["chain_head"] != previous:
            raise ValueError("Wrong chain head.")
        genesis = entries[0]["data"]
        if genesis["commitment"] != record["commitment"]:
            raise ValueError("Genesis commitment mismatch.")
        for field in ("version", "difficulty", "rounds_total"):
            if record[field] != genesis[field]:
                raise ValueError(f"Genesis {field} mismatch.")
        state = record["state"]
        if state["chain_head"] != previous or state["commitment"] != record["commitment"]:
            raise ValueError("Public state checkpoint mismatch.")
        if state["round"] != len(resolved) or state["finished"] != record["finished"]:
            raise ValueError("Public round state mismatch.")
        if record["finished"] != (len(resolved) == record["rounds_total"]):
            raise ValueError("Completion flag mismatch.")
        disclosed = record.get("disclosure")
        if disclosed is not None:
            if not record.get("finished"):
                raise ValueError("Disclosure before completion.")
            if _digest(disclosed["commitment_payload"]) != record["commitment"]:
                raise ValueError("Seed/configuration commitment mismatch.")
            payload = disclosed["commitment_payload"]
            if disclosed["seed"] != payload["seed"] or disclosed["config"] != payload["config"]:
                raise ValueError("Disclosure fields mismatch.")
            if (payload["version"] != record["version"] or payload["difficulty"] != record["difficulty"]
                    or payload["rounds"] != record["rounds_total"]):
                raise ValueError("Disclosure match configuration mismatch.")
        return {"valid": True, "entries": len(entries), "resolved_rounds": len(resolved),
                "disclosure_verified": disclosed is not None,
                "scope": "Hash-chain and disclosure integrity; not server authenticity, unchained state score summaries, or world re-simulation."}
    except (KeyError, TypeError, ValueError) as exc:
        return {"valid": False, "error": str(exc)}


class Engine:
    """An independent seeded match. All returned data are defensive copies."""

    def __init__(self, difficulty: str = "standard", seed: int | str | None = None, rounds: int = 12):
        if difficulty not in ("standard", "frontier"):
            raise ValueError("difficulty must be standard or frontier.")
        if isinstance(rounds, bool) or not isinstance(rounds, int) or not 1 <= rounds <= 100:
            raise ValueError("rounds must be an integer from 1 to 100.")
        if seed is not None and (isinstance(seed, bool) or not isinstance(seed, (int, str))):
            raise ValueError("seed must be an integer, string, or None.")
        self.difficulty = difficulty
        self.rounds_total = rounds
        self._seed = secrets.token_hex(32) if seed is None else str(seed)
        self._rng = random.Random(self._seed)
        self._config = self._make_config()
        self._commitment_payload = {"version": VERSION, "difficulty": difficulty, "rounds": rounds,
                                    "seed": self._seed, "config": self._config}
        self._commitment = _digest(self._commitment_payload)
        self._x = [self._rng.uniform(-0.65, 0.65) for _ in SENSORS]
        self._drivers = [math.sin(phase) for phase in self._config["phases"]]
        self._latent_history = [self._x.copy()]
        self._history: list[dict[str, Any]] = []
        self._tick = 0
        self._round = 0
        self._inspections_left = 6
        self._inspected_this_round = False
        self._latest_inspection = None
        self._latest_result = None
        self._results: list[dict[str, Any]] = []
        self._transcript: list[dict[str, Any]] = []
        self._chain_head = "0" * 64
        for _ in range(18):
            self._advance()
        self._append("genesis", {"version": VERSION, "difficulty": difficulty,
                                  "rounds_total": rounds, "commitment": self._commitment,
                                  "initial_history": self._history,
                                  "events": list(EVENTS), "horizons": list(HORIZONS),
                                  "inspection_budget": 6})

    def _make_config(self) -> dict[str, Any]:
        pairs = []
        for i in range(len(SENSORS)):
            others = [j for j in range(len(SENSORS)) if j != i]
            pairs.append(self._rng.sample(others, 2))
        total_ticks = self.rounds_total * 6
        # Even a short match has a scheduled change after initial observations.
        change_offset = max(2, round(total_ticks * self._rng.uniform(0.35, 0.65)))
        return {
            "pairs": pairs,
            "signs": [[self._rng.choice((-1, 1)), self._rng.choice((-1, 1))] for _ in SENSORS],
            "delays": [self._rng.randint(2, 4) for _ in SENSORS],
            "periods": [self._rng.uniform(11, 29) for _ in SENSORS],
            "phases": [self._rng.uniform(0, 2 * math.pi) for _ in SENSORS],
            "biases": [self._rng.uniform(-0.10, 0.10) for _ in SENSORS],
            "change_tick": 18 + change_offset,
            "change_target": self._rng.randrange(len(SENSORS)),
            "change_factor": -1.0,
            "noise_sd": 0.055 if self.difficulty == "standard" else 0.075,
        }

    def _sensors(self) -> dict[str, int]:
        return {name: min(9, max(0, int(math.floor((value + 1) * 4.5 + 0.5))))
                for name, value in zip(SENSORS, self._x)}

    def _advance(self, action: dict[str, Any] | None = None) -> None:
        self._tick += 1
        next_drivers = []
        for i in range(len(SENSORS)):
            phase = self._config["phases"][i] + self._tick * 2 * math.pi / self._config["periods"][i]
            feedback = 0.12 * self._x[(i + 2) % 6] if self.difficulty == "frontier" else 0.0
            next_drivers.append(0.38 * self._drivers[i] + 0.62 * math.sin(phase + feedback)
                                + self._rng.gauss(0, 0.025))
        next_x = []
        for i in range(len(SENSORS)):
            j, k = self._config["pairs"][i]
            s1, s2 = self._config["signs"][i]
            if self._tick >= self._config["change_tick"] and i == self._config["change_target"]:
                s1 *= self._config["change_factor"]
            delay = self._config["delays"][i]
            delayed = self._latent_history[max(0, len(self._latent_history) - delay)][k]
            interaction = 0.0
            if self.difficulty == "frontier":
                interaction = 0.30 * self._x[j] * delayed + 0.14 * (1 if self._x[k] > 0.2 else -1)
            target = (self._config["biases"][i] + 1.05 * next_drivers[i]
                      + 0.48 * s1 * self._x[j] + 0.32 * s2 * delayed + interaction)
            noise = self._rng.gauss(0, self._config["noise_sd"])
            # Smooth saturation keeps bounded sensors without repeated hard clips.
            value = 0.35 * self._x[i] + 0.65 * math.tanh(1.25 * target) + noise
            next_x.append(max(-1.0, min(1.0, value)))
        self._x = next_x
        self._drivers = next_drivers
        if action is not None and action["kind"] == "pulse":
            index = SENSORS.index(action["sensor"])
            measured = self._sensors()[action["sensor"]]
            pulsed = max(0, min(9, measured + action["delta"]))
            self._x[index] = pulsed / 4.5 - 1.0
        self._latent_history.append(self._x.copy())
        self._history.append({"tick": self._tick, "sensors": self._sensors()})

    def _append(self, kind: str, data: dict[str, Any]) -> str:
        entry = {"index": len(self._transcript), "kind": kind, "data": copy.deepcopy(data),
                 "previous": self._chain_head}
        entry["hash"] = _digest(entry)
        self._transcript.append(entry)
        self._chain_head = entry["hash"]
        return self._chain_head

    def _baselines(self) -> dict[str, dict[str, float]]:
        current = event_values(self._sensors())
        historical = [event_values(item["sensors"]) for item in self._history]
        empirical = {event["id"]: (1 + sum(row[event["id"]] for row in historical)) / (len(historical) + 2)
                     for event in EVENTS}
        return {
            "constant": {key: 0.5 for key in FORECAST_KEYS},
            "persistence": {key: float(current[key.split("@")[0]]) for key in FORECAST_KEYS},
            "empirical": {key: empirical[key.split("@")[0]] for key in FORECAST_KEYS},
        }

    def state(self) -> dict[str, Any]:
        return copy.deepcopy({
            "version": VERSION, "difficulty": self.difficulty,
            "round": self._round, "rounds_total": self.rounds_total,
            "finished": self._round >= self.rounds_total,
            "tick": self._tick, "sensors": self._sensors(), "history": self._history,
            "events": list(EVENTS), "horizons": list(HORIZONS), "forecast_keys": list(FORECAST_KEYS),
            "controls": list(SENSORS), "inspection_options": list(SENSORS),
            "inspections_left": self._inspections_left, "inspected_this_round": self._inspected_this_round,
            "latest_inspection": self._latest_inspection, "latest_result": self._latest_result,
            "commitment": self._commitment, "chain_head": self._chain_head,
            "scores": self._scores(),
            "protocol": {
                "forecast": "Probabilities describe each event at exactly t+1, t+3, and t+6, conditional on the submitted action.",
                "pulse": "Normal dynamics run to t+1, then the selected measured sensor changes by +/-2, clipped to 0..9. No further action occurs until t+6 is resolved.",
                "inspection": "At most one current hidden driver per round; 6 inspections per match. Inspection does not advance time.",
                "change": "One precommitted coupling changes sign during the match; its time and target are hidden.",
                "scoring": "Mean Brier loss across 9 resolved binary forecasts; lower is better. Baselines use only preceding public history and ignore actions and inspection.",
            },
        })

    def inspect(self, sensor: str) -> dict[str, Any]:
        if self._round >= self.rounds_total:
            raise ValueError("The match has finished.")
        if not isinstance(sensor, str) or sensor not in SENSORS:
            raise ValueError("Unknown inspection sensor.")
        if self._inspected_this_round:
            raise ValueError("Only one inspection is allowed per round.")
        if self._inspections_left <= 0:
            raise ValueError("The inspection budget is exhausted.")
        value = self._drivers[SENSORS.index(sensor)]
        self._latest_inspection = {
            "round": self._round, "tick": self._tick, "sensor": sensor,
            "driver": min(9, max(0, int(math.floor((value + 1) * 4.5 + 0.5)))),
            "description": "Current hidden driving input, quantized 0..9. Its future trajectory and couplings remain unknown.",
        }
        self._inspections_left -= 1
        self._inspected_this_round = True
        self._append("inspection", {**self._latest_inspection, "inspections_left": self._inspections_left})
        return self.state()

    @staticmethod
    def _validate_action(action: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(action, dict):
            raise ValueError("action must be an object.")
        if action.get("kind") == "hold" and set(action) == {"kind"}:
            return {"kind": "hold"}
        if action.get("kind") == "pulse" and set(action) == {"kind", "sensor", "delta"}:
            if (isinstance(action["sensor"], str) and action["sensor"] in SENSORS
                    and type(action["delta"]) is int and action["delta"] in (-2, 2)):
                return copy.deepcopy(action)
        raise ValueError("Use {'kind':'hold'} or {'kind':'pulse','sensor':<sensor>,'delta':-2 or 2}.")

    def submit(self, probabilities: dict[str, float], action: dict[str, Any], rationale: str = "") -> dict[str, Any]:
        if self._round >= self.rounds_total:
            raise ValueError("The match has finished.")
        if not isinstance(probabilities, dict) or set(probabilities) != set(FORECAST_KEYS):
            raise ValueError("probabilities must contain exactly the nine forecast_keys.")
        normalized = {}
        for key in FORECAST_KEYS:
            value = probabilities[key]
            if type(value) not in (int, float) or not 0 <= value <= 1 or not math.isfinite(value):
                raise ValueError(f"{key} must be a finite probability from 0 to 1.")
            normalized[key] = float(value)
        validated_action = self._validate_action(action)
        if not isinstance(rationale, str) or len(rationale) > 2000:
            raise ValueError("rationale must be a string of at most 2000 characters.")
        # Everything above is validated before any record, RNG draw, or state mutation.
        baselines = self._baselines()
        start_tick = self._tick
        forecast_data = {"round": self._round, "tick": start_tick, "probabilities": normalized,
                         "action": validated_action, "rationale": rationale, "baselines": baselines}
        forecast_hash = self._append("forecast", forecast_data)
        outcomes: dict[str, int] = {}
        horizon_sensors: dict[str, dict[str, int]] = {}
        for horizon in range(1, max(HORIZONS) + 1):
            self._advance(validated_action if horizon == 1 else None)
            if horizon in HORIZONS:
                observed = self._sensors()
                horizon_sensors[str(horizon)] = observed
                for event, value in event_values(observed).items():
                    outcomes[f"{event}@{horizon}"] = value
        loss = _brier(normalized, outcomes)
        by_horizon = {
            str(h): {"brier": _mean([(normalized[f"{e['id']}@{h}"] - outcomes[f"{e['id']}@{h}"]) ** 2
                                      for e in EVENTS]), "count": len(EVENTS)} for h in HORIZONS
        }
        result = {"round": self._round, "tick_started": start_tick, "tick_finished": self._tick,
                  "action": validated_action, "probabilities": normalized, "outcomes": outcomes,
                  "horizon_sensors": horizon_sensors, "brier": loss, "by_horizon": by_horizon,
                  "baselines": {name: {"probabilities": values, "brier": _brier(values, outcomes)}
                                for name, values in baselines.items()},
                  "forecast_entry_hash": forecast_hash,
                  "forecast_commitment": forecast_hash,
                  "uncertainty_note": "Nine correlated forecasts; a single round does not establish statistical significance."}
        outcome_hash = self._append("outcome", result)
        result["outcome_entry_hash"] = outcome_hash
        self._latest_result = copy.deepcopy(result)
        self._results.append(copy.deepcopy(result))
        self._round += 1
        self._inspected_this_round = False
        return self.state()

    def _scores(self) -> dict[str, Any]:
        if not self._results:
            return {"rounds_completed": 0, "resolved_forecasts": 0, "brier": None,
                    "baseline_0_5": 0.25, "persistence_brier": None, "empirical_brier": None,
                    "skill_vs_constant": None, "by_horizon": {}, "calibration": [],
                    "interpretation": "Exploratory match results; no significance or general-intelligence claim."}
        loss = _mean([result["brier"] for result in self._results])
        calibration = []
        for low, high in ((0.0, 0.2), (0.2, 0.4), (0.4, 0.6), (0.6, 0.8), (0.8, 1.0)):
            observations = [(r["probabilities"][k], r["outcomes"][k]) for r in self._results for k in FORECAST_KEYS
                            if low <= r["probabilities"][k] and (r["probabilities"][k] < high or high == 1.0)]
            calibration.append({"low_inclusive": low, "high": high, "high_inclusive": high == 1.0,
                                "count": len(observations),
                                "mean_probability": _mean([v[0] for v in observations]) if observations else None,
                                "event_frequency": _mean([v[1] for v in observations]) if observations else None})
        return {
            "rounds_completed": len(self._results), "resolved_forecasts": len(self._results) * len(FORECAST_KEYS),
            "brier": loss, "baseline_0_5": 0.25,
            "persistence_brier": _mean([r["baselines"]["persistence"]["brier"] for r in self._results]),
            "empirical_brier": _mean([r["baselines"]["empirical"]["brier"] for r in self._results]),
            "skill_vs_constant": 1 - loss / 0.25,
            "by_horizon": {str(h): {"brier": _mean([r["by_horizon"][str(h)]["brier"] for r in self._results]),
                                    "count": len(self._results) * len(EVENTS)} for h in HORIZONS},
            "calibration": calibration,
            "interpretation": "Exploratory match results; horizons and rounds are correlated. No significance or general-intelligence claim.",
        }

    def replay(self, reveal: bool = False) -> dict[str, Any]:
        if not isinstance(reveal, bool):
            raise ValueError("reveal must be a boolean.")
        finished = self._round >= self.rounds_total
        if reveal and not finished:
            raise ValueError("Seed and configuration are disclosed only after match completion.")
        result = {"version": VERSION, "difficulty": self.difficulty, "rounds_total": self.rounds_total,
                  "finished": finished, "commitment": self._commitment, "chain_head": self._chain_head,
                  "transcript": self._transcript, "state": self.state()}
        if reveal:
            result["disclosure"] = {"seed": self._seed, "config": self._config,
                                    "commitment_payload": self._commitment_payload}
        return copy.deepcopy(result)
