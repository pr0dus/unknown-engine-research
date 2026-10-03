"""Public-information reference policies for the bounded transfer preview.

These are ordinary deterministic programs, not model evaluations. Policies get
only the public state and an experiment callback. The finite Bayesian policy
knows the *published family*, never the sampled configuration or fixture seed.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
import gzip
import itertools
import json
import math
from pathlib import Path
from typing import Any, Callable

from .transfer import (
    BIAS_VALUES, COEFFICIENT_VALUES, DELTA_VALUES, GAIN_VALUES, PROBE_VALUES,
    TransferEngine,
)


CONDITIONS = ("none", "sensor", "mechanism", "both")
FIXTURE_PREFIX = "unknown-engine-transfer-public-development-fixture-v1"
REPORT_SCHEMA = "unknown-engine-transfer-reference-report/0.1"
REPLAY_SCHEMA = "unknown-engine-transfer-reference-replays/0.1"
POLICIES = {
    "method_adaptive": {"arm": "method", "budget": 4,
                        "description": "Two calibration anchors and two sparse-change probes; uses donor coefficients."},
    "raw_adaptive": {"arm": "raw", "budget": 4,
                     "description": "Reconstructs the same donor information from six raw observations, then uses the identical adaptive procedure."},
    "blind_reuse": {"arm": "blind", "budget": 4,
                    "description": "Reuses donor physical coefficients without any target experiment."},
    "cold_limited_linear": {"arm": "none", "budget": 4,
                             "description": "Limited baseline: two calibration anchors and a two-point linear fit; not a strong general cold-start solver."},
    "cold_full_cubic": {"arm": "none", "budget": 6,
                         "description": "Two calibration anchors plus four process probes identify the cubic; has a larger target budget."},
    "cold_finite_bayes": {"arm": "none", "budget": 4,
                          "description": "Full published finite joint prior; greedy one-step information gain over calibration and process actions. Not a proven optimal experiment policy."},
    "constant_0_5": {"arm": "none", "budget": 4,
                       "description": "Valid constant 0.5 forecasts with no experiments."},
}

Experiment = Callable[[dict[str, Any]], dict[str, Any]]


def polynomial(coefficients, x):
    return sum(coefficient * x ** power for power, coefficient in enumerate(coefficients))


def interpolate(points):
    """Small Vandermonde solve; no third-party numerical dependency."""
    n = len(points)
    rows = [[x ** k for k in range(n)] + [y] for x, y in points]
    for col in range(n):
        pivot = max(range(col, n), key=lambda i: abs(rows[i][col]))
        rows[col], rows[pivot] = rows[pivot], rows[col]
        scale = rows[col][col]
        if abs(scale) < 1e-12:
            raise ValueError("Interpolation points do not identify a polynomial.")
        rows[col] = [v / scale for v in rows[col]]
        for i in range(n):
            if i != col:
                multiplier = rows[i][col]
                rows[i] = [a - multiplier * b for a, b in zip(rows[i], rows[col])]
    return [round(row[-1], 12) for row in rows]


def _reading(experiment: Experiment, action):
    state = experiment(action)
    return state["history"][-1]["observation"]


def _calibrate(experiment):
    bias = _reading(experiment, {"kind": "calibrate", "value": 0})
    gain = _reading(experiment, {"kind": "calibrate", "value": 1}) - bias
    if gain <= 0:
        raise ValueError("Observed calibration violates the published positive-gain family.")
    return gain, bias


def _donor_coefficients(state):
    if state.get("artifact") is not None:
        return list(state["artifact"]["coefficients"])
    data = state["source_data"]
    anchors = {row["value"]: row["observation"] for row in data["calibration"]}
    bias, gain = anchors[0], anchors[1] - anchors[0]
    return interpolate([(row["x"], (row["observation"] - bias) / gain)
                        for row in data["process"]])


def _adaptive(state, experiment):
    coefficients = _donor_coefficients(state)
    gain, bias = _calibrate(experiment)
    residuals = []
    for x in (0.5, 1):
        q = (_reading(experiment, {"kind": "probe", "x": x}) - bias) / gain
        residuals.append(q - polynomial(coefficients, x))
    if abs(residuals[0]) < 1e-10 and abs(residuals[1]) < 1e-10:
        return coefficients
    # Under the public one-coefficient-change assumption, r(1)/r(.5)=2**k.
    if abs(residuals[0]) < 1e-10:
        raise ValueError("Observations violate the published sparse-change family.")
    ratio = residuals[1] / residuals[0]
    power = min(range(4), key=lambda k: abs(2 ** k - ratio))
    if abs(2 ** power - ratio) > 1e-8:
        raise ValueError("Observations violate the published sparse-change family.")
    coefficients[power] += residuals[1]
    return coefficients


def finite_prior():
    """Marginal target prior, including multiplicity of equivalent generators.

    Four conditions are equally likely. A mechanism is unchanged with mass 1/2;
    otherwise one coefficient and one of four deltas are chosen uniformly.
    The target gain/bias marginal remains uniform and independent of coefficients
    because a sensor change uniformly chooses a different member of each support.
    Integer weights preserve the exact relative probabilities.
    """
    coefficient_weights = defaultdict(int)
    alternatives = 4 * len(DELTA_VALUES)
    for original in itertools.product(COEFFICIENT_VALUES, repeat=4):
        coefficient_weights[original] += alternatives
        for power in range(4):
            for delta in DELTA_VALUES:
                changed = list(original)
                changed[power] += delta
                coefficient_weights[tuple(changed)] += 1
    return [(coefficients, gain, bias, weight)
            for coefficients, weight in sorted(coefficient_weights.items())
            for gain in GAIN_VALUES for bias in BIAS_VALUES]


def _model_reading(model, action):
    coefficients, gain, bias, _ = model
    q = action["value"] if action["kind"] == "calibrate" else polynomial(coefficients, action["x"])
    return gain * q + bias


def _finite_bayes(state, experiment, budget):
    models = finite_prior()
    actions = ([{"kind": "calibrate", "value": value} for value in (0, 1)] +
               [{"kind": "probe", "x": x} for x in PROBE_VALUES])
    for _ in range(budget):
        total_weight = sum(model[3] for model in models)
        best_action, best_entropy = None, -1.0
        for action in actions:
            groups = defaultdict(int)
            for model in models:
                groups[_model_reading(model, action)] += model[3]
            entropy = -sum((weight / total_weight) * math.log2(weight / total_weight)
                           for weight in groups.values())
            if entropy > best_entropy + 1e-12:
                best_action, best_entropy = action, entropy
        if best_entropy <= 1e-12:
            break
        observed = _reading(experiment, best_action)
        # All family inputs/readings are dyadic, so exact equality is intentional.
        models = [model for model in models if _model_reading(model, best_action) == observed]
        if not models:
            raise ValueError("Observation has zero likelihood under the public finite family.")
        actions.remove(best_action)
    denominator = sum(model[3] for model in models)
    return {target["key"]: sum(model[3] for model in models
                              if polynomial(model[0], target["x"]) >= target["threshold"]) / denominator
            for target in state["targets"]}


def reference_forecast(name: str, state: dict, experiment: Experiment):
    """Return probabilities, using only the supplied public state and callback."""
    if name not in POLICIES:
        raise ValueError("Unknown reference policy.")
    if name == "constant_0_5":
        return {target["key"]: 0.5 for target in state["targets"]}
    if name == "cold_finite_bayes":
        return _finite_bayes(state, experiment, POLICIES[name]["budget"])
    if name in ("method_adaptive", "raw_adaptive"):
        coefficients = _adaptive(state, experiment)
    elif name == "blind_reuse":
        coefficients = _donor_coefficients(state)
    else:
        gain, bias = _calibrate(experiment)
        xs = (-1, 0, 1, 2) if name == "cold_full_cubic" else (-1, 1)
        coefficients = interpolate([(x, (_reading(experiment, {"kind": "probe", "x": x}) - bias) / gain)
                                    for x in xs])
    return {target["key"]: float(polynomial(coefficients, target["x"]) >= target["threshold"])
            for target in state["targets"]}


def _metrics(rows):
    count = len(rows)
    return {"worlds": count,
            "mean_brier": sum(row["primary_brier"] for row in rows) / count,
            **{f"mean_{key}": sum(row[key] for row in rows) / count
               for key in ("target_cost", "donor_cost", "total_cost")},
            **{f"sum_{key}": sum(row[key] for row in rows)
               for key in ("target_cost", "donor_cost", "total_cost")}}


def build_report(records, worlds_per_condition):
    participants = {}
    for name, settings in POLICIES.items():
        selected = [record for record in records if record["participant"] == name]
        participants[name] = {"policy": settings,
                              "overall": _metrics([r["replay"]["state"]["result"] for r in selected]),
                              "by_condition": {condition: _metrics([r["replay"]["state"]["result"] for r in selected
                                                                      if r["condition"] == condition])
                                               for condition in CONDITIONS}}
    indexed = {(r["world_id"], r["participant"]): r["replay"]["state"]["result"] for r in records}
    worlds = sorted({r["world_id"] for r in records})
    comparisons = {}
    for comparator in ("raw_adaptive", "blind_reuse", "cold_limited_linear", "cold_full_cubic", "cold_finite_bayes", "constant_0_5"):
        deltas = [indexed[(world, "method_adaptive")]["primary_brier"] - indexed[(world, comparator)]["primary_brier"]
                  for world in worlds]
        comparisons[comparator] = {"paired_worlds": len(worlds), "mean_brier_difference_method_minus_comparator": sum(deltas) / len(deltas),
                                   "method_lower_loss_worlds": sum(delta < -1e-12 for delta in deltas),
                                   "equal_loss_worlds": sum(abs(delta) <= 1e-12 for delta in deltas),
                                   "method_higher_loss_worlds": sum(delta > 1e-12 for delta in deltas)}
    return {"schema": REPORT_SCHEMA,
            "scope": "Public deterministic development fixtures and reference programs only; zero model calls. Not held-out, independent, frontier-model, or real-world evidence.",
            "fixture": {"seed_prefix": FIXTURE_PREFIX, "conditions": list(CONDITIONS), "worlds_per_condition": worlds_per_condition,
                        "worlds": len(worlds), "records": len(records), "physical_configs_deterministic": True,
                        "commitment_salts_random": True},
            "cost_accounting": "Each recipient using source information is charged all six donor experiments plus its target experiments. Costs are not amortized; cold and constant policies receive no source information. Compute, implementation, and human design costs are not measured.",
            "limitations": ["The published finite noiseless family is intentionally small and exactly identifiable with sufficient measurements.",
                            "Raw and method arms contain the same information; their equality is a required control, not evidence of an artifact-format advantage.",
                            "The four-experiment linear cold baseline is deliberately limited; compare the finite-family Bayesian baseline before claiming benefit.",
                            "The Bayesian reference uses greedy one-step information gain, not an optimal multi-step experimental design solver.",
                            "The six-experiment cold cubic reference has a larger target budget; report this resource difference alongside loss.",
                            "No evidence here establishes novel scientific invention, autonomous cross-laboratory transfer, or usefulness outside this simulator."],
            "participants": participants, "paired_comparisons": comparisons}


def run_development(worlds_per_condition=8):
    if isinstance(worlds_per_condition, bool) or not isinstance(worlds_per_condition, int) or not 1 <= worlds_per_condition <= 100:
        raise ValueError("worlds_per_condition must be an integer from 1 to 100.")
    records = []
    for condition in CONDITIONS:
        for index in range(worlds_per_condition):
            world_id = f"{condition}-{index:03d}"
            seed = f"{FIXTURE_PREFIX}:{world_id}"
            for name, settings in POLICIES.items():
                engine = TransferEngine(seed=seed, condition=condition, arm=settings["arm"], budget=settings["budget"])
                state = engine.state()
                probabilities = reference_forecast(name, state, engine.experiment)
                engine.submit(probabilities)
                records.append({"world_id": world_id, "condition": condition, "participant": name,
                                "arm": settings["arm"], "budget": settings["budget"], "replay": engine.replay(True)})
    return build_report(records, worlds_per_condition), {"schema": REPLAY_SCHEMA, "records": records}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--worlds-per-condition", default=8, type=int)
    parser.add_argument("--overwrite", action="store_true", help="Replace report.json and replays.json.gz; remove a legacy replays.json after writing the compressed replacement.")
    args = parser.parse_args(argv)
    paths = [args.output / name for name in ("report.json", "replays.json.gz")]
    legacy_replays = args.output / "replays.json"
    if not args.overwrite and any(path.exists() for path in [*paths, legacy_replays]):
        parser.error("Evidence files already exist; use a different directory or explicitly pass --overwrite.")
    report, replays = run_development(args.worlds_per_condition)
    args.output.mkdir(parents=True, exist_ok=True)
    paths[0].write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
    replay_bytes = (json.dumps(replays, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    paths[1].write_bytes(gzip.compress(replay_bytes, mtime=0))
    if gzip.decompress(paths[1].read_bytes()) != replay_bytes:
        raise RuntimeError("Compressed replay round-trip failed; legacy file was retained.")
    if legacy_replays.exists():
        legacy_replays.unlink()
    print(json.dumps({"output": str(args.output), "worlds": report["fixture"]["worlds"],
                      "records": report["fixture"]["records"], "model_calls": 0}))


if __name__ == "__main__":
    main()
