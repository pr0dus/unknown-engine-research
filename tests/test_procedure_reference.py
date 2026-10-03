"""Small diagnostic fixtures for frozen controls; not the frozen study run."""

import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from unknown_engine.procedure import ProcedureEngine
from unknown_engine.procedure_reference import (
    FREEZE_SCHEMA, REQUIRED_FREEZE_PATHS, _aggregate, _posterior_answer,
    run_policy, run_study, verify_freeze,
)


def model(**changes):
    return dict(stages=1, rho=0.5, K=1, g=1, b=0, c=1, d=0) | changes


def completed(name, parameters=None, profile="full"):
    engine = ProcedureEngine(parameters or model(), profile=profile, budget=64)
    answer = run_policy(name, engine.state(), engine.experiment)
    final = engine.submit({"decision": answer["decision"], "predictions": answer["predictions"]})
    return engine, answer, final["result"]


class ProcedureReferenceTests(unittest.TestCase):
    def test_uninformed_controls_take_no_actions_and_keep_same_source_forecast(self):
        engine = ProcedureEngine(model(K=2), budget=64)
        packet = engine.state()

        def forbidden(_action):
            self.fail("An uninformed control tried to observe the target.")

        blind = run_policy("blind_source", packet, forbidden)
        reject = run_policy("always_reject", packet, forbidden)
        self.assertEqual(blind["decision"], "valid")
        self.assertEqual(reject["decision"], "invalid")
        self.assertEqual(blind["predictions"], reject["predictions"])
        self.assertEqual(engine.state(), packet)

    def test_legacy_guard_accepts_a_wrong_transient_model(self):
        parameters = model(stages=2, rho=0.75, g=2, b=1, c=0.5, d=1)
        engine, answer, result = completed("legacy_check", parameters)
        self.assertTrue(answer["legacy_guard_passed"])
        self.assertEqual(answer["decision"], "valid")
        self.assertTrue(result["invalid_model_acceptance"])
        self.assertGreater(result["mse"], 0)
        self.assertEqual(result["target_costs"]["units"], 40)
        self.assertEqual(result["target_costs"]["experiment_calls"], 4)
        self.assertEqual(len(engine.state()["history"]), 4)

    def test_short_identification_and_repair_agree_but_charge_different_costs(self):
        parameters = model(stages=2, rho=0.75, g=2, b=1, c=0.5, d=1)
        fixed_engine, fixed, fixed_result = completed("fixed_sysid", parameters)
        repair_engine, repair, repair_result = completed("validate_then_repair", parameters)
        self.assertEqual(fixed["predictions"], repair["predictions"])
        self.assertEqual(fixed["decision"], "invalid")
        self.assertEqual(repair["decision"], "invalid")
        self.assertTrue(repair["legacy_guard_passed"])
        for answer, result in ((fixed, fixed_result), (repair, repair_result)):
            self.assertEqual(answer["hypotheses_remaining"], 1)
            self.assertEqual(result["mse"], 0)
            self.assertEqual(result["max_absolute_error"], 0)
            self.assertTrue(result["warranted_decision_correct"])
            self.assertEqual(result["source_costs"]["units"], 16)
        self.assertEqual(fixed_result["target_costs"]["units"], 16)
        self.assertEqual(fixed_result["target_costs"]["experiment_calls"], 4)
        self.assertEqual(repair_result["target_costs"]["units"], 54)
        self.assertEqual(repair_result["target_costs"]["experiment_calls"], 6)
        self.assertEqual(repair_result["total_costs"]["units"], 70)
        self.assertEqual(len(fixed_engine.state()["history"]), 4)
        self.assertEqual(len(repair_engine.state()["history"]), 6)

    def test_sensor_and_actuator_changes_do_not_invalidate_correct_dynamics(self):
        _, answer, result = completed("fixed_sysid", model(g=2, b=1, c=2))
        self.assertEqual(answer["decision"], "valid")
        self.assertEqual(result["mse"], 0)
        self.assertEqual(answer["hypotheses_remaining"], 1)

    def test_correct_rejection_does_not_erase_bad_forecasts(self):
        _, answer, result = completed("legacy_check", model(K=2))
        self.assertEqual(answer["decision"], "invalid")
        self.assertTrue(result["warranted_decision_correct"])
        self.assertGreater(result["mse"], 0)
        _, repaired, repaired_result = completed("fixed_sysid", model(K=2))
        self.assertEqual(repaired["decision"], "invalid")
        self.assertEqual(repaired_result["mse"], 0)

    def test_restricted_pair_has_identical_history_and_warranted_abstention(self):
        for name in ("fixed_sysid", "validate_then_repair"):
            runs = [completed(name, model(stages=stages, d=1), "restricted") for stages in (1, 2)]
            self.assertEqual(runs[0][0].state()["history"], runs[1][0].state()["history"])
            self.assertEqual(runs[0][1], runs[1][1])
            for _, answer, result in runs:
                self.assertEqual(answer["decision"], "undetermined")
                self.assertEqual(answer["hypotheses_remaining"], 2)
                self.assertEqual(result["target_costs"]["units"], 8)
                self.assertTrue(result["warranted_decision_correct"])
                self.assertGreater(result["mse"], 0)

    def test_restricted_legacy_does_not_attempt_illegal_long_actions(self):
        _, answer, result = completed("legacy_check", model(d=1), "restricted")
        self.assertEqual(answer["decision"], "undetermined")
        self.assertEqual(result["target_costs"]["units"], 0)
        self.assertEqual(result["target_costs"]["experiment_calls"], 0)

    def test_restricted_lucky_guesses_have_no_warranted_decision_credit(self):
        for name in ("blind_source", "always_reject"):
            rows = []
            for stages in (1, 2):
                engine, _, _ = completed(name, model(stages=stages, d=1), "restricted")
                rows.append({"replay": engine.replay()})
            aggregate = _aggregate(rows)
            self.assertEqual(aggregate["hidden_validity_agreement_count"], 1)
            self.assertEqual(aggregate["warranted_decision_correct_count"], 0)
            self.assertEqual(aggregate["hidden_validity_agreements_without_warrant_count"], 1)

    def test_inconsistent_public_observation_is_not_silently_ignored(self):
        engine = ProcedureEngine(model(), budget=64)
        packet = engine.experiment({"kind": "standard", "value": 0})
        packet = copy.deepcopy(packet)
        packet["history"][0]["observations"][0] = 9999
        with self.assertRaisesRegex(ValueError, "No declared model"):
            _posterior_answer(packet)

    def test_freeze_requires_spec_source_and_verifier_and_detects_drift(self):
        with tempfile.TemporaryDirectory() as temp:
            repository = Path(temp)
            hashes = {}
            for name in REQUIRED_FREEZE_PATHS:
                path = repository / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture bytes for " + name, encoding="utf-8")
                hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
            freeze = repository / "freeze.json"
            freeze.write_text(json.dumps({"schema": FREEZE_SCHEMA, "files": hashes}), encoding="utf-8")
            self.assertEqual(verify_freeze(freeze, repository)["files"], hashes)
            missing_verifier = dict(hashes)
            del missing_verifier["scripts/verify_procedure_gate.py"]
            freeze.write_text(json.dumps({"schema": FREEZE_SCHEMA, "files": missing_verifier}), encoding="utf-8")
            with self.assertRaises(ValueError):
                verify_freeze(freeze, repository)
            freeze.write_text(json.dumps({"schema": FREEZE_SCHEMA, "files": hashes}), encoding="utf-8")
            (repository / REQUIRED_FREEZE_PATHS[0]).write_text("changed", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Frozen file changed"):
                verify_freeze(freeze, repository)

    def test_study_refuses_invalid_freeze_or_existing_output_before_any_world(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            freeze = base / "freeze.json"
            freeze.write_text("{}", encoding="utf-8")
            output = base / "new-evidence"
            with patch("unknown_engine.procedure_reference.ProcedureEngine") as engine:
                with self.assertRaises(ValueError):
                    run_study(output, freeze)
                self.assertFalse(output.exists())
                output.mkdir()
                with self.assertRaisesRegex(ValueError, "new directory"):
                    run_study(output, freeze)
                engine.assert_not_called()


if __name__ == "__main__":
    unittest.main()
