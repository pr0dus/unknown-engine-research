"""Verify development evidence by re-simulation and independent aggregation.

Run: python scripts/verify_transfer_preview.py [evidence-directory]
This reads evidence only; it never creates worlds for a participant or rewrites
evidence. Replay reconstruction uses disclosed seeds after completion.
"""

from __future__ import annotations

from collections import defaultdict
import gzip
import json
import math
from pathlib import Path
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from unknown_engine.transfer import verify_transfer_replay  # noqa: E402


EXPECTED_POLICIES = {
    "method_adaptive": ("method", 4), "raw_adaptive": ("raw", 4),
    "blind_reuse": ("blind", 4), "cold_limited_linear": ("none", 4),
    "cold_full_cubic": ("none", 6), "cold_finite_bayes": ("none", 4),
    "constant_0_5": ("none", 4),
}
CONDITIONS = ("none", "sensor", "mechanism", "both")
PREFIX = "unknown-engine-transfer-public-development-fixture-v1"


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _matching(actual, expected, location):
    if isinstance(expected, dict):
        _require(isinstance(actual, dict) and actual.keys() == expected.keys(), "Wrong fields: " + location)
        for key, value in expected.items():
            _matching(actual[key], value, location + "." + key)
    elif type(expected) is float:
        _require(type(actual) in (float, int) and math.isfinite(actual) and
                 math.isclose(actual, expected, rel_tol=1e-12, abs_tol=1e-12), "Mismatch: " + location)
    else:
        _require(type(actual) is type(expected) and actual == expected, "Mismatch: " + location)


def _aggregate(rows):
    n = len(rows)
    _require(n > 0, "An aggregation cell is empty.")
    result = {"worlds": n, "mean_brier": math.fsum(row["primary_brier"] for row in rows) / n}
    for name in ("target_cost", "donor_cost", "total_cost"):
        total = sum(row[name] for row in rows)
        result["mean_" + name] = total / n
        result["sum_" + name] = total
    return result


def verify_directory(directory):
    directory = Path(directory)
    report = json.loads((directory / "report.json").read_text(encoding="utf-8"))
    plain, compressed = directory / "replays.json", directory / "replays.json.gz"
    _require(plain.is_file() != compressed.is_file(), "Exactly one of replays.json or replays.json.gz must exist.")
    replay_bytes = plain.read_bytes() if plain.is_file() else gzip.decompress(compressed.read_bytes())
    envelope = json.loads(replay_bytes.decode("utf-8"))
    _require(report["schema"] == "unknown-engine-transfer-reference-report/0.1", "Wrong report schema.")
    _require(envelope["schema"] == "unknown-engine-transfer-reference-replays/0.1", "Wrong replay schema.")
    records = envelope["records"]
    _require(isinstance(records, list) and bool(records), "Missing replay records.")
    _require(set(report["participants"]) == set(EXPECTED_POLICIES), "Wrong participant set.")
    n = report["fixture"]["worlds_per_condition"]
    _require(type(n) is int and 1 <= n <= 100, "Invalid number of fixtures.")
    expected_worlds = {f"{condition}-{index:03d}": condition for condition in CONDITIONS for index in range(n)}
    indexed, configurations = {}, {}
    groups, cells = defaultdict(list), defaultdict(list)
    entries = 0
    for record in records:
        name, world, condition = record["participant"], record["world_id"], record["condition"]
        _require(name in EXPECTED_POLICIES and world in expected_worlds and expected_worlds[world] == condition,
                 "Unknown participant, fixture, or condition.")
        _require((world, name) not in indexed, "Duplicate participant/fixture pair.")
        arm, budget = EXPECTED_POLICIES[name]
        replay = record["replay"]
        _require(record["arm"] == replay["arm"] == arm and record["budget"] == replay["budget_total"] == budget,
                 "Arm or budget mismatch.")
        checked = verify_transfer_replay(replay)
        _require(checked.get("valid") is True and checked.get("simulation_verified") is True,
                 "Replay reconstruction failed: " + str(checked.get("error")))
        entries += checked["entries"]
        disclosure, state = replay["disclosure"], replay["state"]
        _require(disclosure["seed"] == PREFIX + ":" + world, "Wrong public fixture seed.")
        config = disclosure["config"]
        _require(config["condition"] == condition, "Wrong disclosed condition.")
        if world in configurations:
            _require(configurations[world] == config, "Participant worlds are not physically paired.")
        configurations[world] = config
        # Re-evaluate events and losses without calling the engine's polynomial,
        # scoring implementation, or the reference runner's aggregation code.
        coefficients = config["target"]["coefficients"]
        independent_outcomes = {}
        for target in state["targets"]:
            response = math.fsum(coefficients[i] * target["x"] ** i for i in range(4))
            independent_outcomes[target["key"]] = int(response >= target["threshold"])
        result = state["result"]
        _require(result["outcomes"] == independent_outcomes, "Outcome mismatch.")
        probabilities = result["probabilities"]
        _require(set(probabilities) == set(independent_outcomes), "Wrong forecast keys.")
        _require(all(type(p) in (int, float) and math.isfinite(p) and 0 <= p <= 1 for p in probabilities.values()),
                 "Invalid forecast probability.")
        brier = math.fsum((probabilities[k] - y) ** 2 for k, y in independent_outcomes.items()) / len(independent_outcomes)
        experiments = [entry["data"] for entry in replay["transcript"] if entry["kind"] == "experiment"]
        _require(all(row["cost"] == 1 for row in experiments), "Wrong experiment cost.")
        target_cost = len(experiments)
        donor_cost = 0 if arm == "none" else 6
        recomputed = {"primary_brier": brier, "target_cost": target_cost, "donor_cost": donor_cost,
                      "total_cost": target_cost + donor_cost}
        for field, value in recomputed.items():
            _matching(result[field], value, f"{world}/{name}/{field}")
        _require(result["experiments_used"] == target_cost <= budget and result["coverage"] == 1,
                 "Invalid coverage or experiment budget.")
        indexed[(world, name)] = recomputed
        groups[name].append(recomputed)
        cells[(name, condition)].append(recomputed)
    _require(set(indexed) == {(world, name) for world in expected_worlds for name in EXPECTED_POLICIES},
             "Missing participant/fixture pairs.")
    _matching(report["fixture"], {"seed_prefix": PREFIX, "conditions": list(CONDITIONS), "worlds_per_condition": n,
                                 "worlds": len(expected_worlds), "records": len(records),
                                 "physical_configs_deterministic": True, "commitment_salts_random": True}, "fixture")
    for name, (arm, budget) in EXPECTED_POLICIES.items():
        participant = report["participants"][name]
        _require(participant["policy"]["arm"] == arm and participant["policy"]["budget"] == budget,
                 "Report policy metadata mismatch.")
        _matching(participant["overall"], _aggregate(groups[name]), name + ".overall")
        _matching(participant["by_condition"], {condition: _aggregate(cells[(name, condition)]) for condition in CONDITIONS},
                  name + ".by_condition")
    expected_comparisons = {}
    for other in EXPECTED_POLICIES:
        if other == "method_adaptive":
            continue
        differences = [indexed[(world, "method_adaptive")]["primary_brier"] - indexed[(world, other)]["primary_brier"]
                       for world in sorted(expected_worlds)]
        expected_comparisons[other] = {"paired_worlds": len(differences),
                                      "mean_brier_difference_method_minus_comparator": math.fsum(differences) / len(differences),
                                      "method_lower_loss_worlds": sum(d < -1e-12 for d in differences),
                                      "equal_loss_worlds": sum(abs(d) <= 1e-12 for d in differences),
                                      "method_higher_loss_worlds": sum(d > 1e-12 for d in differences)}
    _matching(report["paired_comparisons"], expected_comparisons, "paired_comparisons")
    for world in expected_worlds:
        _require(indexed[(world, "method_adaptive")] == indexed[(world, "raw_adaptive")], "Same-information control failed.")
    return {"verified": True, "worlds": len(expected_worlds), "records": len(records), "receipt_entries": entries,
            "simulation_verified": True, "independent_outcomes_losses_costs_and_aggregates": True,
            "physical_pairing_verified": True,
            "scope": "Development reference evidence only. Verification checks mathematical consistency, not independent model participation, held-out evaluation, novelty, or external transfer."}


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) > 1:
        raise SystemExit("Usage: verify_transfer_preview.py [evidence-directory]")
    directory = Path(args[0]) if args else ROOT / "evidence" / "transfer-preview"
    try:
        result = verify_directory(directory)
    except (OSError, EOFError, KeyError, TypeError, ValueError, OverflowError, zlib.error) as exc:
        print(json.dumps({"verified": False, "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
