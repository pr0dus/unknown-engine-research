# Procedure-validity development result

**An inherited check can pass while the procedure's later predictions are wrong.
A short ordinary identification script solves this entire full-access family.**
The diagnostic is useful as a regression fixture; it fails the planned gate for
claiming frontier difficulty. Redesign is required before a frontier trial.

## A readable failure

Keep the donor's gain, calibration and delay, but change its process from one
response stage to two. The inherited procedure checks a long sustained command.
Its normalized reading after 32 updates is `1 - 33/2^32`, approximately
**0.999999992**, so it passes the allowed range [0.95, 1.05].

Its predictions for early responses are nevertheless wrong:

| Sustained-command update | Inherited prediction | Actual two-stage response |
| ---: | ---: | ---: |
| 1 | 0.5 | 0 |
| 2 | 0.75 | 0.25 |
| 3 | 0.875 | 0.5 |
| 4 | 0.9375 | 0.6875 |

This is a check that misses the property the procedure later relies on. The
short pulse reference identifies the changed dynamics and repairs the
forecasts. Neither this example nor the complete study is an independent AI
agent discovering a method.

## Complete disclosed comparison

The study includes **192 full-access configurations, two restricted controls,
five deterministic programs, and 970 complete records**. The verifier checks
**2,704 target experiment calls**. The 24 physical outputs in each run share one
world; neither outputs nor repeated policies are independent experimental units.
The catalogue is exhaustively enumerated, not sampled from a deployment
population. There are no model calls, paid API calls or external participants.

Under full access, 12 inherited models are valid after apparatus recalibration
and 180 are invalid on the fixed operational targets:

| Reference program | Invalid accepted / 180 | Valid rejected / 12 | Mean physical MSE | Target units |
| --- | ---: | ---: | ---: | ---: |
| Blind source reuse | 180 | 0 | 0.368564614 | 0 |
| Always reject, retain source forecast | 0 | 12 | 0.368564614 | 0 |
| Inherited settled-response check | 84 | 0 | 0.356866368 | 40 |
| Inherited check, then validate and repair | 0 | 0 | 0 | 54 |
| Fixed system identification | 0 | 0 | 0 | 16 |

The inherited check accepts 96 configurations, including 84 invalid models.
The process-gain changes (K=2) it correctly rejects still have prediction error because
that policy does not repair its forecasts. Rejection and prediction quality are
separate outcomes. The class imbalance also makes a single overall decision
percentage misleading: always rejecting agrees with 180 hidden labels while
rejecting every valid method and retaining inaccurate predictions.

Costs count resets, command/wait ticks and requested samples. Source production
adds 16 units to every run under this shared-source-package comparison; thus
validation/repair totals 70 units and fixed identification totals 32. These are
simulated units, not money, compute or measured physical time. Six versus four
target calls do not by themselves capture the large difference in command ticks.

The 16-unit reference is sufficient, not proven globally cost-optimal. Performing
the inherited 40-unit check before identification adds overhead without reducing
error here. This comparison does not demonstrate a resource advantage for
procedure transfer or for packaging a procedure instead of equivalent raw data.

## Explicit information limit

The restricted pair has a known one-tick actuator delay, but each permitted
experiment resets and lasts only one command. All eight legal actions give
identical observations under both mechanisms. Their later operational outputs
differ: one inherited model is valid and the other is invalid.

Both identification programs retain two hypotheses, report **undetermined**
and forecast their uniform mean. Their physical MSE is 0.0365702311 in each
case, at eight target units. The inherited-check policy cannot run its long
recipe and abstains without experiments, while retaining less accurate source
forecasts (mean MSE 0.0731404622 across the pair).

The eight-unit probes add no information in this restricted setting. An agent
could infer the limit from the public rules and make the same uniform-mixture
forecast without probing. The reference's restricted cost is a prescribed
control, not the minimum cost of recognizing uncertainty.

Blind acceptance and blanket rejection each happen to match one hidden label.
Neither receives restricted decision credit. **Access-profile decision
correctness** requires undetermined under this restriction; under full access,
it compares the submitted label with hidden validity. The JSON field
`warranted_decision_correct` names that narrow criterion. It does not certify
that a particular policy justified its answer from its observations.

## Freeze and verification

Seven protocol, implementation and test files, including the
[development protocol](../../docs/PROCEDURE_VALIDITY_PROTOCOL.md), were hashed in [freeze.json](freeze.json)
after review and unit tests, before this first complete recorded study. Fixed
script saturation had already been predicted analytically. This was not an
externally preregistered or hidden study, and local timestamps are not trusted
attestations.

The separate verifier imports no engine or policy implementation. It calculates
responses through rational impulse-response convolution rather than the
engine's state recurrence. It recomputes observations, actions, posteriors,
predictions, labels, scores, resource costs, aggregates and complete coverage.
It independently confirms 192 distinct identification signatures and equality
under every permitted action for the restricted pair.

- [report.json](report.json): complete aggregate results and limitations.
- [replays.json.gz](replays.json.gz): every disclosed run, including failures.
- [verification.json](verification.json): all 970 records and 2,704 target calls verified.
- [validation.json](validation.json): **154 tests passed**, all 970 core replays
  reconstructed, and isolated 0.5.0a3 wheel smoke checks passed.

The independent implementation supplies internal corroboration. It is not
external scientific replication, proof of referee honesty, model identity or
participant isolation. Earlier forecasting and transfer evidence is unchanged.

Reproduce from the source checkout into a new directory:

```sh
PYTHONPATH=src python -m unknown_engine.procedure_reference \
  --freeze evidence/procedure-gate/freeze.json \
  --output /tmp/unknown-engine-procedure-reproduction
python scripts/verify_procedure_gate.py /tmp/unknown-engine-procedure-reproduction
```

The [participant handoff](../../docs/PROCEDURE_PARTICIPANT_HANDOFF.md) explains
an open integration exercise and the separate requirements for a later agent
A/B study. No independent user has yet demonstrated a development decision or
real-use improvement from this diagnostic. The current support tiers continue
to fund development, rather than sell this as a validated evaluation service.
