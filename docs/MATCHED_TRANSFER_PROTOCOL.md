# Matched inference follow-up: development analysis plan

**Status:** prospective specification for a follow-up implementation and analysis
on already disclosed development fixtures. This is not a preregistration of a
held-out experiment. The original 32 worlds and their previous reference results
were inspected before this plan was written. No model capability claim follows
from this analysis.

## Question and decision boundary

The original constructive repair policy always takes four target measurements.
The cold finite Bayesian reference chooses measurements adaptively. Their
comparison therefore mixes the value of source information with experiment
selection policy. This follow-up asks a narrower question:

> Under the same finite-family inference and experiment-selection algorithm,
> does source information change forecast error or the number of target
> measurements used on these disclosed fixtures?

Implement the follow-up separately. Preserve the original transfer module,
original report and replays. Record the follow-up protocol, source identities,
fixture identities and analysis settings in its own evidence. Do not replace
the earlier unfavorable comparison or relabel these worlds as unseen. A future
independent evaluation would require a different freeze and new instances.

## Fixed scope

- Use the same 32 disclosed physical worlds: eight in each of the `none`,
  `sensor`, `mechanism` and `both` cells of the original development fixture.
- Use the original known finite cubic process, affine sensor, legal action
  grid, exact noiseless observations and twelve physical-event targets.
- Compare recipient budgets `0, 1, 2, 3, 4`, with fresh independent recipient
  state at each budget or an exactly equivalent recorded policy prefix.
- Compare a cold recipient with a source-informed recipient. Both use the
  identical posterior-update, action-selection, tie-breaking, stopping and
  forecasting code. Only their initial information differs.
- Use three named arms: `donor_method_bayes`, `donor_raw_bayes`, and
  `cold_bayes_same_policy`. The first two differ only in the source encoding.
  This produces 480 final records: 32 worlds, five budgets and three arms.
  Check that independently executed budgets follow the same action prefixes.
- Reconstruct source information from the original six source measurements
  when checking equivalence with the supplied artifact. This source remains a
  referee-generated reference fixture, not an independent donor agent's work.

The original condition cells use different donors. Participants are paired
within a physical world; the four condition cells are not within-donor
intervention ablations. Only an explicitly defined future experiment may claim
such pairing.

## Priors and likelihoods

The source coefficient vector has four independent uniform entries from
`{-2,-1,1,2}`. Source gain is uniform on `{0.5,1,2}` and source offset on
`{-2,0,2}`, independently. Sensor-change and mechanism-change flags are
independent Bernoulli variables with probability one half.

Conditional on a mechanism change, choose one of four coefficient indices and
one of four nonzero deltas uniformly. Conditional on a sensor change, choose
both a different gain and a different offset, uniformly over the two remaining
values of each. A change in only one sensor parameter is not part of this
generator.

**Cold prior:** marginalize over the source. For each source coefficient vector,
give its unchanged target weight `16` and each of its sixteen single-coefficient
changes weight `1`, then aggregate weights of identical target vectors. Target
gain and offset are independent uniform marginals. They are also independent
of target coefficients under this generator. Preserve multiplicities; uniform
weight over distinct target models would be a different prior.

**Source-informed prior:** condition on the source coefficients, gain and offset
recovered from the artifact or raw observations. Give the unchanged mechanism
weight `16` and each changed mechanism weight `1`. Give the original gain/offset
pair weight `4` and each of the four pairs with both parameters changed weight
`1`. Multiply these two weights and aggregate identical target models. The
unnormalized total is `32*8=256`; each of the four change conditions has mass
one quarter. In particular, the conditional sensor prior is not uniform over
all nine gain/offset pairs.

All updates use the same exact observation likelihood. Legal inputs,
coefficients, gains and offsets yield dyadic readings, so exact equality is
appropriate here. A hypothesis survives when its predicted reading equals the
returned reading. An empty posterior is an implementation/protocol failure,
not an excuse to inspect the hidden configuration or silently add hypotheses.

## Common experiment policy

For each available action, group posterior hypotheses by their predicted
observation and sum their integer weights. Choose the action with maximum
entropy of the resulting observation distribution:

\[
H(Y_a)=-\sum_y P(Y_a=y)\log_2 P(Y_a=y).
\]

Because observations are deterministic conditional on the model, this equals
one-step expected information gain about that model. It is not a globally
optimal experiment policy, nor is it explicitly optimized for Brier loss or
physical measurement cost beyond each action costing one unit.

Use the same deterministic tie-break in both arms: calibration `0`, calibration
`1`, then process inputs in ascending order `-2,-1,-0.5,0,0.5,1,2`, with a
numerical tolerance of `1e-12` for entropy ties. Remove actions already taken.
Different selected actions are legitimate consequences of different initial
information; forcibly matching action sequences would answer another question.

Before the first action and after each update, compute each target's posterior
positive weight. Stop when all twelve targets have positive weight either zero
or equal to the total posterior weight. This is zero uncertainty about the
scored events, not necessarily complete recovery of the process or sensor.
Use integer weight comparisons for this test. Otherwise continue until the
declared budget is exhausted. If every remaining action has only one possible
observation (an exact test, not an entropy-tolerance threshold),
stop and retain the current posterior uncertainty rather than inventing a
measurement or answer.

At stopping, predict the posterior probability of each event. The forecast
targets are fixed and do not change with the chosen experimental actions.

## Outcomes, costs and reporting

For every arm, budget and physical world, retain probabilities, outcomes,
observed experiment sequence, posterior stopping reason and actual target
measurement cost. Retain comparable intermediate summaries if used to build
budget curves. Evidence must distinguish a valid probabilistic answer from a
failed or incomplete execution.

Report:

- Mean Brier loss and the paired source-minus-cold difference at every budget.
- Mean posterior expected Brier loss, `mean(p*(1-p))`, separately from realized
  Brier loss. This is uncertainty under the stipulated prior, not an additional
  empirical validation score.
- Actual target cost, not merely the allowed budget, with the paired difference.
- The fraction of worlds for which all event probabilities are resolved before
  exhausting the budget, plus the stopping-cost distribution.
- Results separately for all four change conditions, with the pairing caveat
  above and no selective omission of unfavorable cells.
- Exact source-artifact versus raw-source posterior equivalence.
- Source production cost `6` as a separate, declared fixture cost, and total
  charged cost `6 + target_cost` for a single source-informed recipient.

Inference computation, implementation effort, human design time and money are
not measured by these experiment units. A cold policy's smaller action count
does not establish smaller wall-clock compute, and a transferred artifact is
not free to create. The twelve targets in one world are dependent; do not
treat them as independent experimental replicates. These are descriptive
development results. Any interval should be explicitly exploratory and grouped
by physical world, not advertised as confirmatory statistical significance.

## Amortization is an arithmetic projection

For `N` equal to `1, 2, 4, 8, 16`, an optional projection may report the
per-recipient cost:

\[
C_S(N)=6/N+\overline C_{S,\mathrm{target}},
\qquad C_C=\overline C_{C,\mathrm{target}}.
\]

This assumes one source artifact is reusable by `N` recipients with the same
average target costs and relevant performance as those measured here. The
current fixtures are not such a cohort experiment: no additional target worlds
are generated, no reuse success rate is established, and no independence claim
is added by this arithmetic.

If the measured target-cost saving is positive, a formal break-even expression
is `N > 6 / target_cost_saving`; if it is zero or negative, there is no finite
break-even count under this projection. Compare costs at declared comparable
forecast performance; a cheap policy with worse forecasts is a tradeoff, not
unqualified savings. Never call projected game units euros saved in a lab.

## Interpretation gates

1. **Correctness:** priors normalize, duplicated generator histories retain
   their weights, updates preserve the true disclosed model, and both arms use
   the same policy logic. Any failure invalidates the comparison until fixed
   and the development analysis is transparently rerun.
2. **Source information:** lower loss at a fixed budget or equal forecast
   performance with lower target cost supports a limited information benefit
   for this algorithm and fixture set. An advantage confined to certain budgets
   or change types must be reported that way.
3. **Economic interpretation:** include source costs. Amortization projections
   can identify conditions worth testing; they do not establish realized savings.
4. **Research contribution:** even a positive result does not establish new
   method invention, a hard benchmark, practical usefulness or novelty. The
   source supplies exact parameters inside a disclosed finite family. Frontier
   claims need another task and independent evidence.

No advantage is an acceptable result. Preserve it. If both methods saturate at
small budgets, do not conceal the ceiling by removing the strong baseline or
promoting the weak linear baseline. A follow-up model trial would need its own
purpose and authorization for inference resources; it is not part of this plan.
