# Procedure-validity diagnostic, development protocol 0.1

Status: frozen development specification, 27 September 2026. This is a small
regression diagnostic and a shortcut screen, not a hidden evaluation or a claim
of frontier difficulty. Freeze this document's SHA-256 before the first study
execution. Design review predicts that a fixed identification script will solve
every fully observable case. Recording that ceiling is an intended outcome.

## Question and decision

Can a recipient notice that an inherited procedure's own check is insufficient,
then accept, reject/repair, or withhold judgment about its predictive validity?
The operational decision concerns the inherited model after apparatus
recalibration, on the fixed sequences below. It is not a claim of universal
physical validity. Forecasts after repair are scored separately from that
decision. A correct rejection alone does not earn a correct forecast.

This increment compares validation strategies given the same referee-written
source package. It does NOT test procedure packaging versus equivalent raw
evidence, independent donor discovery, real-world usefulness, or customer demand.
Those require separate studies. No language model or paid API is required.

## Exact family and timing

All states start at zero for each experiment. Commands before index zero are
zero. At command index t, u[t] = c * a[t-d]. A single-stage process updates

    q_next = rho*q + (1-rho)*K*u[t].

A two-stage process updates simultaneously, using the OLD first-stage state:

    v_next = rho*v + (1-rho)*K*u[t]
    q_next = rho*q + (1-rho)*v.

The observed sample AFTER this update is g*q_next+b. A certified reference-load
experiment bypasses the process and observes g*u[t]+b. A certified sensor
standard observes g*value+b and bypasses both actuator and process. These
anchors are provided by the task; the participant has not invented them.

The full, public, noiseless target catalogue is the Cartesian product:

| Parameter | Values |
| --- | --- |
| stages | 1, 2 |
| rho | 0.5, 0.75 |
| K | 1, 2 |
| g | 1, 2 |
| b | 0, 1 |
| c | 0.5, 1, 2 |
| d | 0, 1 |

There are 192 physical configurations. Every one is included once in a stable
lexicographic enumeration. No random seed, population sampling or independence
claim is involved. The shared donor is stages=1, rho=0.5, K=1, g=1, b=0, c=1,
d=0. Public source observations include standards 0/1, reference pulse [1,0],
and process pulse [1,0,0,0], with every sample retained. The fitted donor and
inherited procedure are supplied alongside those observations. The donor is a
fixture, not an independent discovery; do not claim source information saved
resources in this study. Report its six ticks, two resets and eight samples
(16 cost units) separately from target costs, plus the combined total.

## Actions, costs and access

The public-state engine accepts strictly validated JSON actions:

- `{"kind":"standard","value":0}` or value 1.
- `{"kind":"reference","commands":[1,0],"sample_at":[1,2]}`.
- `{"kind":"process","commands":[1,0,0,0],"sample_at":[1,2,3,4]}`.

Commands are -1, 0 or 1; lengths are 1 through 32. `sample_at` is a nonempty,
strictly increasing list of one-based sample indices within that sequence.
Each reference/process call includes one reset and every command tick, including
zero commands (waiting). Every requested reading counts as one sample. Sensor
standards cost one sample and no reset/tick. The charged unit sum is resets +
ticks + samples. Also report experiment calls separately, without adding them a
second time. The common target cap is 64 units. Invalid or over-budget actions
must leave state and costs unchanged. No wall time, inference tokens, euros or
physical settling-time equivalence is measured.

The public packet contains rules, source data/model/procedure, targets, access
limits, costs and observation history. It excludes the fixture identifier and
actual target parameters until completion. This is an interface separation,
not a sandbox or model identity attestation. This development catalogue is
public; a participant must not be advertised as isolated from its answers.

Two additional restricted-access fixtures demonstrate a specific impossibility:
stages is 1 or 2, while rho=0.5,K=1,g=1,b=0,c=1,d=1 are supplied as known.
The donor in these two cases has stages=1 and d=1. Every permitted transient
experiment has length ONE and resets first. Thus both targets always return
zero on a process/reference command; standards are identical. Repetition cannot
identify stages. The full length-six operational targets still differ. There
is one valid and one invalid inherited model in this indistinguishable pair.
This restriction deliberately removes necessary information; it is not a hard
but solvable test. The warranted validity judgment is `undetermined` in both.

## Inherited procedure and operational targets

The inherited procedure is a bounded declarative recipe, executed through the
same legal action interface, never through uploaded code:

1. Read standards 0 and 1; infer g and b.
2. Reference-load command [1,1], sample at 2; infer c from the calibrated reading.
3. Process command 1 repeated 32 times, sample at 32; check whether the physical
   response divided by c lies in [0.95,1.05].
4. Predict with the donor's stages=1, rho=0.5, K=1 and d, using inferred c.

This checks an approximately settled unit response. It does not test the
transient assumptions used in step 4. Some invalid targets pass it. Sensor,
actuator-gain and process-gain effects remain separately observable through the
anchors; if a future family lacks those anchors, causal diagnoses must weaken.

All policies predict physical q after each of six updates, from reset, on each
of these fixed command sequences:

- sustained: [1,1,1,1,1,1]
- alternating: [1,-1,1,-1,1,-1]
- late pulse: [0,0,1,0,0,0]
- reversal: [1,1,-1,-1,0,0]

These 24 outputs share one physical world; they are not 24 independent trials.
The scoring sequences are public and fixed, and are distinct from the chosen
reference probes. No claim that they were unknown to the designer is made.
The inherited model is operationally valid when its predictions with the true
target c differ from the true outputs by at most 1e-9 at every target. Report
mean squared physical prediction error after any repair (not Brier loss and not
accuracy), maximum absolute error, invalid-model acceptance, valid-model
rejection, and undetermined judgments separately. The probability of validity
is not requested. An abstention does not erase a submitted forecast's error.

## Frozen reference strategies

All strategies are supplied only the public packet and an experiment callback.
Policies use the same source package and common 64-unit cap. No hidden target
parameter or fixture identifier may be passed to them.

- `blind_source`: zero target actions, declares valid, forecasts the source.
- `always_reject`: zero target actions, declares invalid, forecasts the source.
- `legacy_check`: runs the four-call inherited recipe, declares valid if its
  check passes and invalid otherwise, and uses its calibrated donor forecasts.
- `validate_then_repair`: runs that same recipe, then a reference pulse [1,0]
  and process pulse [1,0,0,0], retaining every pulse sample. It filters the
  publicly declared catalogue against all observations, decides validity only
  when all remaining possibilities agree, and forecasts their uniform mean.
- `fixed_sysid`: skips the legacy check, using standards 0/1, reference pulse
  [1,0], and process pulse [1,0,0,0]. It uses the same filtering, decision and
  forecasting code as validate_then_repair. This is the strong simple control.

Under restricted access, legacy_check cannot execute its recipe and returns
undetermined with source forecasts and zero target actions. Both identification
policies instead use standards 0/1 and single-command [1] reference/process
probes, then the same filtering and decision rule. The public restricted prior
contains only its two stated stage possibilities. Blind/always-reject remain
uninformed controls and must not be credited for a lucky true/false guess in
an indistinguishable pair. Report warranted-decision correctness separately
from agreement with hidden validity. Here `warranted_decision_correct` is an
ACCESS-PROFILE criterion: full-access decisions are compared with hidden
validity, while restricted-access decisions must be undetermined. It does not
certify that an individual policy justified its decision from its own history;
an uninformed full-access guess can agree with hidden truth by luck. No
per-history evidential-calibration claim is supported by this field.

Filtering uses absolute observation tolerance 1e-12. The short probes are
exact dyadic floats; long-check rounding does not affect the 5% guard. Uniform
weighting is a declared reference choice, not an empirical target distribution.
Policies do not receive the outcome of their validity decision during play.

## Shortcut proof and decision gate

Two standards recover g,b. The reference pulse recovers c,d. For the process
pulse, the first nonzero physical output occurs at index d+1 (one stage) or
d+2 (two stages), counted from one. The ratio of the first two nonzero readings
is rho for one stage and 2*rho for two stages. Those sets {0.5,0.75} and {1,1.5}
are disjoint. The amplitude determines K. The four-sample pulse includes both
readings even for two stages with d=1. Thus a fixed script identifies all 192
full-access cases for 16 target cost units (2 resets, 6 ticks, 8 samples).

Before the study run, freeze this spec and implementation hashes in a separate
record. Include every fixture, policy, action, observation, decision and error;
retain unsuccessful outcomes. Hashes support reconstruction, not an external
timestamp, referee honesty or participant isolation. Verify dynamics with a
separate analytic impulse-response implementation, independently recompute
scores/costs/decisions, and verify the full-catalogue identification property.

If the proof and executable results agree, the disposition is **regression
diagnostic passed; frontier-difficulty claim rejected; redesign required before
a frontier trial**. A useful guard-failure example can still support future
agent A/B regression tests. Do not silently add noise, variables or an unknown
family after seeing results, or represent deterministic programs as AI models.
Independent participant and real-use claims remain open even if every test
passes. No external participant is contacted or paid run authorized by this
protocol.
