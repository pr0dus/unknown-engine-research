"""Dynamics, access boundaries, and replay integrity for the bounded diagnostic."""

import copy
import hashlib
import itertools
import json
import math
import unittest

from unknown_engine.procedure import (
    FORECAST_KEYS, ProcedureEngine, action_response, full_catalogue, legacy_actions,
    operational_validity, prediction, pulse_actions, response, restricted_catalogue,
    source_model, standard_actions, verify_procedure_replay,
)


class ProcedureTests(unittest.TestCase):
    def test_catalogue_is_exact_unique_stable_cartesian_product(self):
        expected = list(itertools.product((1, 2), (.5, .75), (1, 2), (1, 2), (0, 1), (.5, 1, 2), (0, 1)))
        actual = full_catalogue()
        self.assertEqual([tuple(model.values()) for model in actual], expected)
        self.assertEqual(len({tuple(model.items()) for model in actual}), 192)
        actual[0]["K"] = 999
        self.assertNotEqual(full_catalogue()[0]["K"], 999)

    def test_single_and_two_stage_timing_uses_old_first_stage(self):
        one = source_model()
        self.assertEqual(response(one, "process", [1, 0, 0, 0], [1, 2, 3, 4]), [.5, .25, .125, .0625])
        two = dict(one, stages=2)
        self.assertEqual(response(two, "process", [1, 0, 0, 0], [1, 2, 3, 4]), [0, .25, .25, .1875])
        delayed = dict(two, d=1)
        self.assertEqual(response(delayed, "process", [1, 0, 0, 0], [1, 2, 3, 4]), [0, 0, .25, .25])

    def test_anchors_bypass_correct_components_and_reset_each_call(self):
        model = dict(source_model(), stages=2, K=2, c=2, d=1, g=2, b=1)
        self.assertEqual(response(model, "standard", [0], [1]), [1])
        self.assertEqual(response(model, "standard", [1], [1]), [3])
        self.assertEqual(response(model, "reference", [1, -1, 0], [1, 2, 3]), [1, 5, -3])
        action = {"kind": "process", "commands": [1, 0, 0, 0], "sample_at": [1, 2, 3, 4]}
        engine = ProcedureEngine(model)
        first = engine.experiment(action)["history"][-1]["observations"]
        second = engine.experiment(action)["history"][-1]["observations"]
        self.assertEqual(first, [1, 1, 3, 3])
        self.assertEqual(first, second)

    def test_source_and_target_costs_count_waiting_ticks_and_calls_once(self):
        engine = ProcedureEngine(source_model())
        self.assertEqual(engine.state()["source_costs"], {"ticks": 6, "resets": 2, "samples": 8, "units": 16, "experiment_calls": 4})
        for action in standard_actions() + pulse_actions():
            engine.experiment(action)
        self.assertEqual(engine.state()["costs"], engine.state()["source_costs"])
        engine = ProcedureEngine(source_model())
        for action in legacy_actions():
            engine.experiment(action)
        self.assertEqual(engine.state()["costs"], {"ticks": 34, "resets": 2, "samples": 4, "units": 40, "experiment_calls": 4})

    def test_invalid_actions_and_overbudget_are_atomic(self):
        invalid = [
            {}, {"kind": "standard", "value": True}, {"kind": "standard", "value": float("nan")},
            {"kind": "standard", "value": 0, "extra": 1},
            {"kind": "process", "commands": [True], "sample_at": [1]},
            {"kind": "process", "commands": [1], "sample_at": [True]},
            {"kind": "process", "commands": [1], "sample_at": [1.0]},
            {"kind": "process", "commands": [1], "sample_at": []},
            {"kind": "process", "commands": [1, 0], "sample_at": [2, 1]},
            {"kind": "process", "commands": [1, 0], "sample_at": [1, 1]},
            {"kind": "reference", "commands": [1], "sample_at": [2]},
            {"kind": "process", "commands": [1] * 33, "sample_at": [1]},
            {"kind": "process", "commands": [1], "sample_at": [1]},  # valid, but three units exceed this cap
        ]
        engine = ProcedureEngine(source_model(), budget=2)
        before = engine.state()
        for action in invalid:
            with self.subTest(action=action), self.assertRaises(ValueError):
                engine.experiment(action)
            self.assertEqual(engine.state(), before)
        engine.experiment({"kind": "standard", "value": 0})
        engine.experiment({"kind": "standard", "value": 1})
        before = engine.state()
        with self.assertRaises(ValueError):
            engine.experiment({"kind": "standard", "value": 1})
        self.assertEqual(engine.state(), before)

    def test_public_packets_exclude_target_identity_and_are_defensive(self):
        first = ProcedureEngine(full_catalogue()[0])
        second = ProcedureEngine(full_catalogue()[-1])
        self.assertEqual(first.state(), second.state())
        state = first.state()
        self.assertNotIn("model", state)
        self.assertNotIn("fixture_id", state)
        self.assertNotIn("result", state)
        state["rules"]["catalogue"][0]["K"] = 42
        state["source_model"]["rho"] = 42
        state["history"].append({})
        self.assertEqual(first.state(), second.state())
        with self.assertRaises(ValueError):
            first.replay()

    def test_restricted_pair_is_observationally_identical_but_operationally_distinct(self):
        models = restricted_catalogue()
        self.assertEqual([operational_validity(model, "restricted") for model in models], [True, False])
        self.assertNotEqual(prediction(models[0]), prediction(models[1]))
        engines = [ProcedureEngine(model, "restricted") for model in models]
        self.assertEqual(engines[0].state(), engines[1].state())
        actions = standard_actions() + [{"kind": kind, "commands": [value], "sample_at": [1]}
                                       for kind in ("reference", "process") for value in (-1, 0, 1)]
        for action in actions * 2:
            self.assertEqual(engines[0].experiment(action), engines[1].experiment(action))
        for engine in engines:
            with self.assertRaises(ValueError):
                engine.experiment({"kind": "process", "commands": [1, 0], "sample_at": [1]})
            result = engine.submit({"decision": "undetermined", "predictions": prediction(source_model("restricted"))})["result"]
            self.assertTrue(result["warranted_decision_correct"])
            self.assertFalse(result["hidden_validity_agreement"])
        self.assertEqual(engines[0].state()["result"]["mse"], 0)
        self.assertGreater(engines[1].state()["result"]["mse"], 0)

    def test_operational_validity_ignores_sensor_and_recalibrates_actuator_gain(self):
        model = dict(source_model(), g=2, b=1, c=2)
        self.assertTrue(operational_validity(model))
        self.assertEqual(prediction(model), prediction(dict(model, g=1, b=0)))
        for key, value in (("stages", 2), ("rho", .75), ("K", 2), ("d", 1)):
            self.assertFalse(operational_validity(dict(model, **{key: value})))

    def test_completion_scores_mse_and_decision_separately(self):
        model = dict(source_model(), stages=2)
        engine = ProcedureEngine(model)
        outcomes = prediction(model)
        predicted = {key: value + .5 for key, value in outcomes.items()}
        result = engine.submit({"decision": "invalid", "predictions": predicted})["result"]
        self.assertEqual(result["mse"], .25)
        self.assertEqual(result["max_absolute_error"], .5)
        self.assertTrue(result["warranted_decision_correct"])
        self.assertTrue(result["hidden_validity_agreement"])
        self.assertEqual(result["invalid_model_acceptance"], 0)
        self.assertEqual(result["total_costs"]["units"], 16)
        before = engine.replay()
        with self.assertRaises(ValueError):
            engine.submit({"decision": "invalid", "predictions": outcomes})
        with self.assertRaises(ValueError):
            engine.experiment({"kind": "standard", "value": 0})
        self.assertEqual(engine.replay(), before)

    def test_invalid_forecasts_and_configs_are_rejected_without_mutation(self):
        engine = ProcedureEngine(source_model())
        initial = engine.state()
        for invalid in (True, float("nan"), float("inf"), 10 ** 1000, 1e308):
            forecast = prediction(source_model())
            forecast[FORECAST_KEYS[0]] = invalid
            with self.subTest(invalid=str(invalid)[:20]), self.assertRaises(ValueError):
                engine.submit({"decision": "valid", "predictions": forecast})
            self.assertEqual(engine.state(), initial)
        with self.assertRaises(ValueError):
            engine.submit({"decision": "valid", "predictions": prediction(source_model()), "extra": 1})
        for model in (dict(source_model(), d=True), dict(source_model(), stages=1.0), dict(source_model(), K=math.nan), dict(source_model(), extra=1)):
            with self.assertRaises(ValueError):
                ProcedureEngine(model)
        for budget in (True, -1, 65, .5):
            with self.assertRaises(ValueError):
                ProcedureEngine(source_model(), budget=budget)
        with self.assertRaises(ValueError):
            ProcedureEngine(source_model(), "restricted")

    def test_replay_verifies_and_detects_rehashed_observation_score_cost_tampering(self):
        engine = ProcedureEngine(dict(source_model(), stages=2))
        for action in standard_actions() + pulse_actions():
            engine.experiment(action)
        engine.submit({"decision": "invalid", "predictions": prediction(source_model())})
        original = engine.replay()
        self.assertTrue(verify_procedure_replay(original)["valid"])
        self.assertTrue(verify_procedure_replay(json.loads(json.dumps(original)))["valid"])
        for field in ("observation", "cost", "score", "truth", "extra", "model"):
            modified = copy.deepcopy(original)
            if field == "observation":
                modified["state"]["history"][0]["observations"][0] += 1
            elif field == "cost":
                modified["state"]["costs"]["units"] -= 1
            elif field == "score":
                modified["state"]["result"]["mse"] = 0
            elif field == "truth":
                modified["state"]["result"]["warranted_decision_correct"] = False
            elif field == "extra":
                modified["state"]["extra"] = 1
            else:
                modified["disclosure"]["model"]["K"] = 2
            unsigned = {key: value for key, value in modified.items() if key != "sha256"}
            modified["sha256"] = hashlib.sha256(json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode()).hexdigest()
            with self.subTest(field=field):
                self.assertFalse(verify_procedure_replay(modified)["valid"])
        self.assertFalse(verify_procedure_replay({})["valid"])


if __name__ == "__main__":
    unittest.main()
