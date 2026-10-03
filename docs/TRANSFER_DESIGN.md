# Transfer and repair: bounded diagnostic design

**Scope decision, 27 September 2026:** proceed with a private `0.5.0a1`
candidate for a small, known-family transfer diagnostic. This is approval of a
bounded prototype, not acceptance of a research claim or a validated public
v0.5 release. The source, protocol, tests and release report must establish
which parts are implemented. This document contains design reasoning and a
hypothetical worked example; it reports no participant experiment.

The useful question is whether a recipient can test and repair a transferred
predictor when its sensor and physical process may have changed. The candidate
can validate the interaction protocol, experimental accounting, artifact
handoff and controlled comparisons. It does not establish scientific invention,
frontier-model difficulty, novelty or practical transfer outside this family.

## Explicit world and information assumptions

The donor process belongs to a disclosed cubic family:

\[
q_D(x)=a_0+a_1x+a_2x^2+a_3x^3,
\qquad z_D(x)=g_Dq_D(x)+b_D.
\]

The donor coefficient support is the public set `{-2, -1, 1, 2}`. Legal process
inputs are the public grid `{-2, -1, -0.5, 0, 0.5, 1, 2}`. The target either
retains the donor process or changes at most one coefficient:

\[
q_T(x)=q_D(x)+\delta x^k,
\qquad k\in\{0,1,2,3\},\quad \delta\in\{-2,-1,1,2\}.
\]

Its sensor independently retains or changes its affine calibration. Gain is
chosen from `{0.5, 1, 2}` and offset from `{-2, 0, 2}`. A sensor change changes
both, choosing uniformly from each support excluding the source value. The
four conditions have equal prior probability. These distributions are public
participant information, not secret advantages reserved for a reference
program. Numeric comparisons are exact for the allowed dyadic observations;
the interpolation/repair references separately document their tolerances.

This first diagnostic is noiseless. Floating-point formatting is not physical
noise. A future noisy track would require a different inference analysis,
repeat-measurement budget and versioned protocol.

Two certified standards bypass the process and pass through the same sensor:

\[
z_{\mathrm{cal}}(r)=gr+b,\qquad r\in\{0,1\}.
\]

Thus `calibrate(0)` and `calibrate(1)` identify `b` and `g`. Their certified
physical values and shared sensor path are explicit external anchors. The
agent does not invent these standards or solve calibration without assumptions.
Known action syntax, a known polynomial family and a known finite prior are
also substantial assistance. There is no hidden requirement to guess a command
or the designer's terminology.

## Costs, artifacts and a constructive strategy

The candidate donor budget is six measurements: two calibration readings and
four process readings at distinct inputs, `-1`, `0`, `1`, `2`.
Calibrated readings determine a cubic by interpolation. The candidate recipient
budget is four measurements, with every calibration and process measurement
costing one unit. These are diagnostic design settings, not measured frontier
resource limits.

A donor-side reference fixture produces a bounded declarative artifact:
predictor coefficients, calibration metadata, assumptions, and applicability
guidance. Its coefficients must be reconstructed from the six source
observations, not copied from hidden parameters. The current fixture does not
implement an independent donor agent, participant-authored method synthesis or
an executable applicability-test language. The referee must not execute
arbitrary submitted Python.
The recipient receives only its declared packet and the frozen artifact, with
no donor private state, seed or target shift label. Independence requires a
separate recipient state; using different participant names alone proves none.

With an accurate donor predictor, the recipient can use two calibrations and
process inputs `0.5` and `1`. After calibration, define

\[
d(x)=q_T(x)-q_D(x).
\]

Under the disclosed single-coefficient-shift assumption, nonzero residuals obey

\[
\frac{d(1)}{d(0.5)}=2^k,\qquad \delta=d(1).
\]

Ratios `1`, `2`, `4`, `8` distinguish the four possible changed degrees. Two
zero residuals identify no mechanism change within this family. Recipient
probes at `-1` and `1` instead would confound constant and quadratic changes.
The ratio argument is exact algebra under the stated assumptions, not a
statistical claim or a guarantee for arbitrary mechanisms. Implementations
must handle zero residuals and numeric tolerances explicitly.

**Six measurements are a sufficient donor strategy, not a cold-start lower
bound.** A finite coefficient prior and precise measurements can allow much
faster identification. Restricting inputs to seven choices does not remove all
such shortcuts. For example, when an ablation declares that coefficients remain
in the original support, calibrated readings at `0.5` and `-0.5` reveal
`4*a0 + a2` and `4*a1 + a3`; these combinations uniquely identify many allowed
coefficient pairs. This example does not give a recovery rate for the full
unknown-shift mixture. An exact finite-hypothesis reference is mandatory before
interpreting any claimed donor advantage.

## Hypothetical worked example

The following numbers are chosen on paper. They are not generated evaluation
worlds or measured agent results.

Let the donor have

\[
q_D(x)=1+2x-x^2+x^3,\qquad g_D=1,\quad b_D=0.
\]

Its six-measurement record could contain:

| Measurement | Reading |
| --- | ---: |
| Calibration standard 0 | 0 |
| Calibration standard 1 | 1 |
| Process input -1 | -3 |
| Process input 0 | 1 |
| Process input 1 | 3 |
| Process input 2 | 9 |

Now suppose the recipient first measures input `1` and observes `12`. Before
calibration, at least three explanations within the allowed process-shift
family remain (each with candidate sensor `z = 2*q + 2`):

1. The constant coefficient changed by `+2`: `q_T(x)=q_D(x)+2`.
2. The linear coefficient changed by `+2`: `q_T(x)=q_D(x)+2*x`.
3. The quadratic coefficient changed by `+2`: `q_T(x)=q_D(x)+2*x^2`.

A cubic-coefficient change by `+2` is a fourth explanation. The sensor
parameters in these hypotheses are not supplied to the recipient; they must
be tested. All four predict the same first raw reading but different responses
at other inputs. The separate equivalence example below shows why sensor and
process changes also need calibration anchors to be distinguished generally.

Suppose the next two measurements are calibration standards `0` and `1`, giving
`2` and `4`. They establish `b_T=2`, `g_T=2`. The first process reading therefore
means `q_T(1)=5`, with residual `d(1)=2`. A final process measurement at `0.5`
gives `6.75`; hence `q_T(0.5)=2.375` and `d(0.5)=0.5`. The ratio is `4`, so the
permitted repair is

\[
q_T(x)=1+2x+x^2+x^3.
\]

This uses four recipient measurements. Three single-coefficient explanations
that remain immediately after calibration are changes to degree 0, 1 or 2,
each by `+2`; the final `0.5` probe separates these, as well as degree 3. The
worked example establishes a feasible diagnostic strategy. It does not show
that an agent discovered one or that a cold-start solver cannot match it.

## What cannot be identified without anchors

If calibration actions are removed, take a donor with gain `1` and offset `0`
and consider two target worlds:

- World A: `q_T(x)=q_D(x)` and `z=2*q_T(x)+2`.
- World B: `q_T(x)=q_D(x)+2` and `z=2*q_T(x)-2`.

Both produce exactly `2*q_D(x)+2` for every process input, including adaptive
sequences, while differing in their physical process and potentially in a
physical-event threshold. Both are admitted by the current generator: A is a
sensor-only change, B changes both sensor and mechanism, both sensor parameters
change from the donor, and B has a permitted constant-term change. No sequence
of process readings alone distinguishes them. With the worked-example donor,
their physical responses at `0.5` are `1.875` and `3.875`, so they disagree on
the scored threshold `q(0.5)>=2` despite identical sensor readings.

That is an observation-equivalence argument within the access model. An
agent should retain both possibilities if anchors are unavailable. A guessed
hidden label must not be treated as superior diagnosis merely because it
happens to match the referee's choice. Conversely, some operational predictions
can remain identifiable even when the decomposition into process and sensor
is not. An inability to attribute change does not automatically establish that
the transferred method is useless.

## Evaluation and controlled comparisons

Use a separate transfer track; do not reinterpret historical forecasting
scores. Freeze donor/target distributions, budgets, event definitions, scoring,
artifact schema, baseline strategies and participant prompts before evaluation.
Every target shift follows precommitted rules. No participant-dependent
punishment or secret modification follows an action.

Compare these conditions on matched donor-target pairs:

| Condition | Information and purpose |
| --- | --- |
| Artifact with repair | Frozen donor artifact and four target measurements |
| Raw donor observations | Same source information before its compression into an artifact |
| Cold start | Public prior and four target measurements; no donor information |
| Blind reuse | Reuse the donor predictor without target validation |
| Exact finite inference | Enumerate all compatible public hypotheses and update them on each allowed measurement |
| Privileged reference | Knows target parameters; explicitly separate from observation-matched methods |

The exact finite reference must respect the same information condition and
budget as its comparator. Its posterior weights must follow the declared
generator distribution, including multiplicities when several latent histories
produce the same target. It should use an informative legal experiment policy;
an intentionally poor fixed policy is not a sufficient strong baseline.

Raw source observations and an exact fitted donor artifact may encode equivalent
information. Equal performance is an expected control, not evidence against
artifact correctness. Improvement over cold start alone establishes value of
source information; it does not establish new scientific reasoning. Record
donor production costs as well as recipient costs. Sharing one donor artifact
across many recipients is a separate amortization question.

Evaluate physical-event forecasts on a fixed set of target inputs and thresholds
independent of the participant's experimental choices. Participants cannot earn
an easier prediction target by selecting an action. Publish Brier loss,
valid-submission coverage, failure counts, calibration/process measurements and
diagnostic results separately. A failed response is not a model-authored 0.5
forecast. Any failure-adjusted aggregate needs an explicit, separate definition.
Do not infer broad calibration quality from a few noiseless binary events.
The implemented target grid includes `-0.5` and `0.5`, which are also legal
experimental inputs, and `-1.5` and `1.5`, which are not. Thus only part of the
forecast grid tests unprobed inputs; do not describe all twelve targets as
held-out interventions.

Required ablations include no change, sensor-only change, mechanism-only change
and both; artifact present versus absent; artifact versus raw observations;
and a clearly labelled no-anchor non-identifiability diagnostic. No-anchor
results require a different interpretation, not an unfair demand to name the
hidden cause. Future budget curves may reveal whether any transfer benefit
exists only at a narrow resource setting.
The initial development runner pairs participant policies within each
donor-target world. Its condition-specific seeds do not hold the donor fixed
across the four change conditions. Those condition summaries are descriptive
cells, not a controlled within-donor estimate of each shift's effect. A later
preregistered condition ablation must explicitly share donors and account for
the resulting dependence.

## Next independent test and rejection criteria

First verify the diagnostic with reference programs and replayable development
examples. These establish execution and mathematical consistency, not model
ability. The next independent model test needs a new preregistration and fresh
hidden instances after freezing model identity, prompt, inference settings,
tool access, artifacts and scoring. A repository-aware designer or a subagent
sharing hidden files is not a blinded recipient. Remote participant compute
cannot be assumed equal merely because environment-action budgets match.

Before advancing a transfer-benefit claim, the intended comparison is the
paired recipient loss difference between artifact-assisted repair and the
strongest matched-budget cold-start reference, with raw-source access as a
source-information control. Report effects separately by shift type and group
uncertainty by donor-target unit; shared donors create dependence. Choose a
confirmatory sample size from pilot variability rather than inventing a power
claim now. Strong ordinary and developed prompts should be frozen before hidden
evaluation. The development result below fails this advancement gate; an
independent model smoke could still check usability, but should not be sold as
confirmation that this family demands a new capability.

Redesign or reject the proposed contribution if:

- identifiers, precision quirks, errors or artifact metadata reveal the answer;
- cold-start finite inference eliminates the claimed transfer benefit;
- blind reuse performs as well across all informative change conditions;
- forecast thresholds or the evaluation grid conceal meaningful model errors;
- the constructive reference fails its promised noiseless diagnostic cases;
- gains disappear when donor information, target budgets or failures are
  accounted for correctly; or
- benefits require the original generator and fail on separately designed
  transfer tasks.

A correct prototype and an informative negative result can still be worth
publishing. They cannot be relabelled as frontier hardness. A single finite
polynomial family gives no evidence of independently authored family transfer
or real laboratory/industrial utility.

### Initial development gate outcome

The [32-world reference report](../evidence/transfer-preview/report.json)
records the following development results, with eight fixtures per change
condition and no model calls:

| Reference | Mean Brier loss | Mean target cost | Mean donor cost | Mean total cost |
| --- | ---: | ---: | ---: | ---: |
| Method with repair | 0 | 4 | 6 | 10 |
| Raw observations with repair | 0 | 4 | 6 | 10 |
| Cold finite Bayesian inference | 0 | 3.09375 | 0 | 3.09375 |

The cold reference correctly predicts every scored binary event on these
fixtures while using fewer target measurements on average. The implemented
artifact-repair policy offers no demonstrated loss or measurement-cost advantage
over this strong reference. This is a useful negative result for that policy
comparison and a ceiling for its current loss comparison, not a successful
frontier claim. It does not prove the globally optimal policy or every possible
instance has been solved. The separate replay verifier checks consistency of the
stored evidence; this scope assessment does not substitute for that verification.

The two policies optimize differently: artifact repair follows a fixed
constructive four-probe strategy, whereas cold inference chooses probes by
information gain. Consequently this result does not prove that donor information
cannot save target measurements. That stronger question needs a finite posterior
conditioned on the donor information and comparably adaptive experiment selection,
potentially across several budget limits. Extra information can always be
ignored. Donor production costs must remain visible; any amortization across
recipients must be explicitly reported rather than assumed.

The appropriate research response is to resolve this policy comparison before
claiming general experimental savings, and to revise and baseline-screen the
task family before presenting it as a frontier challenge. Preserve these
fixtures and their result rather than replacing the cold reference, hiding its
result, or silently changing the tested rules. The private alpha remains a
usable diagnostic/interface implementation.

## Alternatives, precedents and larger ambitions

A delayed nonlinear dynamical system could make calibration depend on history,
but would complicate the identifiability and score comparisons before this
handoff works. An independently authored laboratory family could test broader
method reuse, but requires additional authorship, verification and transfer
evidence. The cubic diagnostic is preferable for the first implementation
because a constructive solution and a strong exact baseline can expose broken
claims cheaply. It is not preferable because it is thought to be harder.

Relevant primary precedents constrain the contribution:

- [Bareinboim and Pearl, 2014](https://papers.nips.cc/paper_files/paper/2014/hash/29d8ab58bcd65e45a831feeaed051d23-Abstract.html)
  establishes transportability results with limited experiments given structural
  assumptions. Transfer of causal knowledge is not a new idea.
- [Varici et al., 2024](https://proceedings.mlr.press/v238/varici24a.html)
  studies recovery of latent causal representations under unknown observation
  transformations and specified interventions. Unknown measurement mappings are
  already a substantial research area.
- [Chen et al., 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/4ae163cb8788970e53b4fd9578141139-Abstract-Conference.html)
  studies identification of changed latent mechanisms under a fixed linear
  observation mixing model. Mechanism-change diagnosis is not itself novel.
- [Rauschen et al., 2024](https://www.nature.com/articles/s44160-023-00473-6)
  demonstrates transfer of encoded chemistry procedures across robotic platforms
  and laboratories. It motivates portable procedures; success in this toy
  diagnostic would not establish comparable physical usefulness.

These references are selected precedents, not an exhaustive novelty review.

[Issue #4](https://github.com/pr0dus/unknown-engine/issues/4) proposes three
separate tracks: a bounded benchmark, research-frontier worlds and a genuine
open-problem arena. This candidate is only a diagnostic step toward the bounded
track. The latter two tracks, invention of instruments or representations,
cumulative scientific discovery, an independently validated transfer claim and
the Millennium-problem ambitions remain unimplemented and unestablished. This
document does not execute or complete Issue #4's full design-and-research brief.
