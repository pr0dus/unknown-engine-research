"""Analytic audit checks, including the limits of the disclosed diagnostic."""

import copy
from fractions import Fraction
import importlib.util
from pathlib import Path
import unittest

from unknown_engine.procedure import ProcedureEngine
from unknown_engine.procedure_reference import run_policy


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("procedure_verifier", ROOT / "scripts" / "verify_procedure_gate.py")
VERIFIER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VERIFIER)


class AnalyticProcedureAuditTests(unittest.TestCase):
    def test_first_order_impulse_and_delayed_cascade_are_hand_checkable(self):
        source = VERIFIER.source_model("full")
        self.assertEqual(VERIFIER.physical_response(source, [1, 0, 0, 0]),
                         [Fraction(1, 2), Fraction(1, 4), Fraction(1, 8), Fraction(1, 16)])
        cascade = dict(source, stages=2, d=1)
        self.assertEqual(VERIFIER.physical_response(cascade, [1, 0, 0, 0]),
                         [Fraction(0), Fraction(0), Fraction(1, 4), Fraction(1, 4)])

    def test_sensor_and_reference_bypass_the_correct_components(self):
        model = dict(VERIFIER.source_model("full"), stages=2, g=2, b=1, K=2, c=0.5, d=1)
        self.assertEqual(VERIFIER.observations(model, {"kind": "standard", "value": 1}), [3.0])
        self.assertEqual(VERIFIER.observations(model, VERIFIER.transient("reference", [1, -1, 0])),
                         [1.0, 2.0, 0.0])
        self.assertEqual(VERIFIER.observations(model, VERIFIER.transient("process", [1, 0, 0, 0])),
                         [1.0, 1.0, 1.5, 1.5])

    def test_all_full_signatures_unique_and_all_restricted_actions_indistinguishable(self):
        result = VERIFIER.audit_identifiability()
        self.assertEqual(result["full_configurations"], 192)
        self.assertTrue(result["full_signatures_unique"])
        self.assertTrue(result["restricted_indistinguishable"])
        self.assertTrue(result["restricted_operational_targets_differ"])

    def test_costs_charge_resets_waits_and_samples_but_not_calls_twice(self):
        expected = {"full": [0, 0, 40, 54, 16], "restricted": [0, 0, 0, 8, 8]}
        for profile in expected:
            costs = [VERIFIER.total_cost(VERIFIER.expected_actions(profile, policy))["units"]
                     for policy in VERIFIER.POLICIES]
            self.assertEqual(costs, expected[profile])
        self.assertEqual(VERIFIER.total_cost(VERIFIER.expected_actions("full", "fixed_sysid")),
                         {"ticks": 6, "resets": 2, "samples": 8, "experiment_calls": 4, "units": 16})

    def test_calibratable_apparatus_gain_does_not_change_inherited_validity(self):
        source = VERIFIER.source_model("full")
        self.assertTrue(VERIFIER.is_valid(dict(source, c=2, g=2, b=1), "full"))
        self.assertFalse(VERIFIER.is_valid(dict(source, d=1), "full"))
        self.assertFalse(VERIFIER.is_valid(dict(source, stages=2), "full"))


class ProcedureReplayAuditTests(unittest.TestCase):
    @staticmethod
    def unit_record(profile, policy):
        # Disposable unit cases, never run_study or a saved evidence archive.
        model = dict(VERIFIER.source_model(profile), stages=2)
        if profile == "full":
            model.update(rho=0.75, K=2, g=2, b=1, c=0.5, d=1)
        engine = ProcedureEngine(model, profile=profile)
        answer = run_policy(policy, engine.state(), engine.experiment)
        engine.submit({key: answer[key] for key in ("decision", "predictions")})
        record = {"fixture_id": profile + "-unit", "profile": profile, "policy": policy,
                  "policy_summary": {key: value for key, value in answer.items() if key != "predictions"},
                  "replay": engine.replay()}
        return record, model

    def test_every_policy_on_full_and_restricted_unit_cases(self):
        for profile in ("full", "restricted"):
            for policy in VERIFIER.POLICIES:
                with self.subTest(profile=profile, policy=policy):
                    record, model = self.unit_record(profile, policy)
                    result, count = VERIFIER.audit_record(record, model)
                    self.assertEqual(count, len(VERIFIER.expected_actions(profile, policy)))
                    if policy in ("fixed_sysid", "validate_then_repair"):
                        self.assertEqual(record["policy_summary"]["hypotheses_remaining"], 1 if profile == "full" else 2)
                        self.assertEqual(result["decision"], "invalid" if profile == "full" else "undetermined")
                        self.assertEqual(result["mse"] == 0, profile == "full")

    def test_rehashed_observation_outcome_cost_and_policy_tampering_are_rejected(self):
        original, model = self.unit_record("full", "validate_then_repair")
        mutations = (
            lambda r: r["replay"]["state"]["history"][2]["observations"].__setitem__(0, 999.0),
            lambda r: r["replay"]["state"]["result"]["outcomes"].__setitem__("sustained@1", 999.0),
            lambda r: r["replay"]["state"]["result"]["target_costs"].__setitem__("units", 1),
            lambda r: r["replay"]["state"]["history"][0]["action"].__setitem__("value", 1),
            lambda r: r["policy_summary"].__setitem__("hypotheses_remaining", 2),
            lambda r: r["replay"]["state"]["result"].__setitem__("warranted_decision", "valid"),
        )
        for mutate in mutations:
            record = copy.deepcopy(original)
            mutate(record)
            record["replay"]["sha256"] = VERIFIER.canonical_digest(
                {key: value for key, value in record["replay"].items() if key != "sha256"})
            with self.assertRaises(ValueError):
                VERIFIER.audit_record(record, model)


if __name__ == "__main__":
    unittest.main()
