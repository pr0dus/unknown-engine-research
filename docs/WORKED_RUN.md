# A complete recorded transfer run

This is `both-000`, pairing the existing `method_adaptive` and `blind_reuse` ordinary programs. It was selected to illustrate the process. The explanations below are retrospective; they are not the program's recorded reasoning. This is one disclosed development case, not an independent model trial or representative sample.

## Starting information

The source process is `q(x) = 2 - 2x + 2x² - 2x³`. The target instrument reports `z = gq + b`. The participant knows the finite, noiseless family and permitted changes, but does not initially know the target gain, offset or changed coefficient. Four target measurements are available. Source information carries a separately recorded cost of six measurements.

## Measurements and updates

| Step | Action | Observed reading | What the observation permits | Cost |
| --- | --- | ---: | --- | ---: |
| 1 | Calibrate against physical reference 0 | -2 | Instrument offset `b = -2`; gain and process remain unresolved. | 1 |
| 2 | Calibrate against physical reference 1 | 0 | Gain `g = 2`; convert readings with `q = (z + 2) / 2`. Calibration alone does not validate the process. | 1 |
| 3 | Probe process at `x = 0.5` | 1 | Physical response 1.5, compared with source prediction 1.25: residual 0.25. | 1 |
| 4 | Probe process at `x = 1` | 0 | Physical response 1, compared with source prediction 0: residual 1. | 1 |

Under the specified one-coefficient-change family, a changed coefficient of power `k` contributes residual `Δxᵏ`. The ratio `1 / 0.25 = 4 = 2²` identifies the quadratic term and the residual at 1 gives `Δ = +1`.

The repaired equation is `q(x) = 2 - 2x + 3x² - 2x³`. This fixed two-probe repair recipe is not claimed to be the cheapest strategy. The later reference comparison below does better on measurement cost.

## Predictions and disclosure

At `x = 1.5`, blind reuse predicts -3.25 while the repaired equation predicts -1. For the event `q >= -2`, their probabilities are therefore 0 and 1. The disclosed outcome is 1.

| Event | Adaptive probability | Blind-reuse probability | Revealed outcome |
| --- | ---: | ---: | ---: |
| `q@-1.5>=-2` | 1 | 1 | 1 |
| `q@-1.5>=0` | 1 | 1 | 1 |
| `q@-1.5>=2` | 1 | 1 | 1 |
| `q@-0.5>=-2` | 1 | 1 | 1 |
| `q@-0.5>=0` | 1 | 1 | 1 |
| `q@-0.5>=2` | 1 | 1 | 1 |
| `q@0.5>=-2` | 1 | 1 | 1 |
| `q@0.5>=0` | 1 | 1 | 1 |
| `q@0.5>=2` | 0 | 0 | 0 |
| `q@1.5>=-2` | 1 | 0 | 1 |
| `q@1.5>=0` | 0 | 0 | 0 |
| `q@1.5>=2` | 0 | 0 | 0 |

The final disclosure gives target gain 2, offset -2 and coefficients `[2, -2, 3, -2]`. The archive's condition label was not supplied to the program before forecasting. Exact probabilities 0 and 1 rely on this stipulated noiseless family; they do not establish certainty outside it. All twelve outcomes share a world and are not independent trials.

## Scores and full acquisition costs

Lower Brier loss is better; a constant 0.5 forecast has loss 0.25.

| Program | Brier loss | Target measurements | Source measurements | Total |
| --- | ---: | ---: | ---: | ---: |
| Adaptive worked example | 0 | 4 | 6 | 10 |
| Blind reuse | 1/12, approximately 0.083333 | 0 | 6 | 6 |
| Matched finite Bayesian reference | 0 | 2 | 6 | 8 |

The stronger reference probes at 0.5 and -2. It shares the initial information and maximum target budget but uses different experiment selection. Computation is not equalized or measured. None of these simulated measurement counts measures model tokens, money, elapsed time or development effort.

## Inspect and reproduce

- [Adaptive replay](../examples/worked-run/adaptive-replay.json)
- [Blind-reuse replay](../examples/worked-run/blind-replay.json)
- [Report JSON](../examples/worked-run/adaptive-report.json)
- [HTML report](../examples/worked-run/adaptive-report.html) — download and open locally

From the repository root, run `python scripts/verify_public_example.py`. The verifier compares both replays with the original archive and reconstructs the report. See [reproduction instructions](REPRODUCTION.md) for all studies and [the prospective pilot](INDEPENDENT_PROCEDURE_PILOT.md) for the distinct independent research gate.
