# Matched-policy development follow-up

**Source information reduces target measurements under the same inference and
experiment-selection algorithm on these 32 already disclosed fixtures.** At
budget four, both recipients have zero Brier loss. Source-informed recipients
use 1.53125 target measurements on average; cold recipients use 3.0625.
Charging the six source measurements makes the single-recipient total
**7.53125 versus 3.0625**, so this is not an end-to-end cost saving for one
recipient.

This exploratory follow-up was designed after inspecting the earlier results.
It is not a held-out model evaluation, a new hard benchmark, evidence of
independent agent discovery, or a practical deployment result. Zero model
calls and no paid inference were used.

## Design and provenance

- Frozen specification: [MATCHED_TRANSFER_PROTOCOL.md](../../docs/MATCHED_TRANSFER_PROTOCOL.md),
  SHA256 `3e7be7d5b4f7fdccf470d83655092e364e2fa8e5ad2ea576960fd7c94cf6f0f3`.
- The same 32 physical fixtures as [the original preview](../transfer-preview/README.md):
  eight each in `none`, `sensor`, `mechanism`, and `both`.
- Three arms: `donor_method_bayes`, `donor_raw_bayes`, and
  `cold_bayes_same_policy`; five target-budget caps, zero through four.
- 480 complete records represent repeated arms and budgets on 32 worlds, not
  480 independent experimental units. The twelve targets within a world are
  also dependent.
- All arms use identical posterior updates, greedy observation-entropy action
  selection, tie-breaking, and stopping code. Only initial source information
  differs. They stop when all scored events have exact posterior probabilities
  zero or one, at budget exhaustion, or if every remaining action has only one
  possible observation.
- The method and raw arms encode the same donor coefficients and source sensor
  calibration. The source is a referee fixture with a declared production cost
  of six; it was not discovered by an independent donor agent.

The report pins the archived replay bytes, frozen specification, original
engine source and matched participant source by SHA256. Earlier source and
evidence remain unchanged. Fresh commitment salts make recreated replay files
different; physical worlds and numerical results are deterministic.

The original baseline used a different stopping criterion. The present cold
cost, 3.0625, therefore differs from the archived 3.09375. This new comparison
does not replace or rescore that earlier result.

## Budget curves

Lower Brier loss is better. Target costs below are actual measurements, not
merely the allowed cap. The method and raw arms have identical probabilities,
actions, stopping decisions, scores and costs in every paired record.

| Target cap | Source-informed Brier | Cold Brier | Source-informed target cost | Cold target cost |
|---:|---:|---:|---:|---:|
| 0 | 0.0688680013 | 0.2160278236 | 0 | 0 |
| 1 | 0.0137299633 | 0.1681741502 | 1 | 1 |
| 2 | 0.0000180219 | 0.0850365638 | 1.5 | 2 |
| 3 | 0 | 0.0066922794 | 1.53125 | 2.875 |
| 4 | 0 | 0 | 1.53125 | 3.0625 |

At cap four, source-informed stopping costs are one measurement in 16 worlds,
two in 15, and three in one. Cold stopping costs are two in four worlds, three
in 22, and four in six. All source-informed worlds resolve before exhausting
the cap; 81.25% of cold worlds resolve before it and 18.75% resolve at it.

Mean posterior expected Brier is reported separately in `report.json`. It is
uncertainty under the stipulated finite prior, not an independent empirical
validation score. Full per-condition curves and stopping distributions are
included without selecting only favorable cells.

At cap four, all cells have zero loss:

| Change condition | Source-informed target cost | Cold target cost |
|---|---:|---:|
| None | 1.25 | 3 |
| Sensor | 1.875 | 2.875 |
| Mechanism | 1.5 | 3.375 |
| Both | 1.5 | 3 |

The condition cells use different donors. Pairing holds across participant
arms and budgets within each world; these cells are not within-donor
intervention ablations.

## Arithmetic reuse projection

At equal observed zero loss and budget cap four, the mean target saving is
1.53125 measurements. If one six-measurement source could serve independent
recipients with these same mean target costs and performance, projected cost
per recipient would be `6/N + 1.53125`, versus cold cost `3.0625`.

| Assumed recipients | Projected source-informed cost per recipient | Projected cold cost per recipient |
|---:|---:|---:|
| 1 | 7.53125 | 3.0625 |
| 2 | 4.53125 | 3.0625 |
| 4 | 3.03125 | 3.0625 |
| 8 | 2.28125 | 3.0625 |
| 16 | 1.90625 | 3.0625 |

Strict projected saving requires `N > 6 / 1.53125 = 192/49`, so the first
integer count is four. **No same-source recipient cohort was run.** Its
reusability and performance assumptions remain untested. These are simulated
measurement units, not euros or measured compute savings.

## Verification and limits

`verification.json` records successful checks of all 480 records and 2,082
receipt entries. The verifier reconstructs every engine replay and independently:

- Enumerates the complete source-and-change generative prior, retaining all
  multiplicities, rather than using the participant's marginalization shortcut.
- Reconstructs raw donor coefficients with exact Lagrange interpolation, rather
  than the participant's Gaussian elimination.
- Recomputes greedy actions, posterior probabilities, exact stopping,
  outcomes, losses, costs, curves and reuse arithmetic.
- Checks artifact/raw equality and action-prefix consistency across budgets.
- Checks the archived fixture set and provenance-file hashes.

Run:

```sh
python scripts/verify_transfer_matched.py evidence/transfer-matched
```

To reproduce into a new directory, which must not already exist:

```sh
PYTHONPATH=src python -m unknown_engine.transfer_matched \
  --input evidence/transfer-preview/replays.json.gz \
  --spec docs/MATCHED_TRANSFER_PROTOCOL.md \
  --output /tmp/unknown-engine-matched-reproduction
```

The finite, noiseless, explicitly specified family is small; both methods
saturate at low budgets. The greedy policy is not a globally optimal
experimental-design policy and does not optimize Brier loss directly. Exact
source parameters convey useful information, but equivalence to raw data
prevents an artifact-format advantage claim. Human design, implementation,
inference compute, money and actual donor discovery effort are unmeasured.
These descriptive results justify a narrower next experiment, not claims of
novel scientific invention, frontier capability or real-world usefulness.
