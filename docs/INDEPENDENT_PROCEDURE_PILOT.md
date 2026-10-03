# Independent procedure-validation pilot — prospective handoff

Status: prepared, not started. No independent researcher, agent result or new
confirmation family is represented as existing. This document operationalizes
the research gate; it is not a completed preregistration or evidence of novelty.

## Decision and roles

Question: does explicitly checking an inherited procedure's assumptions reduce
incorrect reuse, at acceptable rejection, abstention, execution-failure and
resource costs, for an independent developer's actual agent-development decision?

Before running, the developer records the decision they would otherwise make,
their current alternative test, and what outcome would change that decision.
Record the developer, case author and operator roles and affiliations voluntarily;
do not describe project-authored cases or internal verification as independent.
The case author and operator must keep confirmation answers from the developer
and participant. Retain exact case files privately until disclosure is agreed.

## Development, freeze, confirmation

1. Use the supplied disclosed cases and reference campaign to integrate the runner
   and identify a failure. The 192 full-access cases are solved by a fixed script;
   more seeds from that family do not establish a harder or new ability.
2. Define A (current agent) and B (one specified procedure-validation change).
   Freeze exact prompts/configurations, provider-reported model/version, code,
   tools, memory resets, sampling, context limits, timeout/retry rules, experiment
   budget and any externally funded inference budget. Archive bytes and SHA-256
   hashes before inspecting confirmation outcomes. Hashes are not trusted timestamps.
3. A separate case author supplies an unused mechanism family with valid transfer,
   repairable failure and cases where the legal evidence cannot settle validity.
   Define event targets, legal access, costs, truth labels and observable-equivalence
   criteria before running. Validate each case with independently implemented
   calculations. The current campaign CLI supports only the existing family;
   a new-family adapter and scoring review are prerequisites, not completed features.
4. Freeze the complete case allocation, repeats, order randomization and analysis
   before running either arm. Pair physical cases and access/budget across A and B.
   Choose sample size from a stated precision/power target using development data
   or a declared conservative assumption; do not choose it after a favorable result.
5. Retain every allocated attempt, including timeouts, refusals, malformed outputs,
   crashes, retries and missing submissions. Record all retry costs. No resampling
   of a failed attempt into an invisible successful replacement.

## Required freeze worksheet

Fill every item before confirmation; blank items mean the trial is not ready:

- Independent developer's decision and current alternative: ___
- A and B configuration/prompt/code hashes and the single intended change: ___
- Case author/operator roles, access separation and family provenance: ___
- Case/stratum counts, stochastic repeats, order allocation and case file hashes: ___
- Experiment, compute/token, time and monetary limits and retry handling: ___
- Primary effect: reduction in invalid acceptance; minimally useful reduction: ___
- Maximum acceptable increases in valid rejection, unresolved decisions,
  execution failures, forecast error and total resource use, each separately: ___
- Interval estimator, confidence level, clustering unit and missing-data bounds: ___
- Sample-size rationale, stopping rule and exception/deviation log location: ___
- Independent confirmation release/disclosure plan: ___

## Comparisons and reporting

Compare with fixed system identification, a cheap decision-focused experiment
policy appropriate to the new family, blind reuse and always-reject controls.
Keep the existing fixed-script ceiling visible for the existing family. Do not
make one comparator deliberately weak or give it less usable information.

Report invalid accepted / allocated invalid cases and / submitted invalid cases;
valid rejected with both corresponding denominators; valid/invalid/undetermined
and execution-failure counts by truth/access stratum; physical prediction error;
all-attempt costs and source acquisition separately. An execution failure is not
a scientifically justified `undetermined` judgment. Missing predictions do not
earn zero error. Report paired completed-case error alongside exclusions and
predeclared bounds/sensitivity for missing outcomes, never as an all-attempt gain.

Compute uncertainty on paired world-level differences, clustering repeated
stochastic runs and related variants at their independent source/world unit.
The outputs from one world are correlated. Publish per-stratum counts and costs;
do not let a high proportion of invalid cases hide unnecessary rejection.
Simulated experiment units do not measure model tokens, money or elapsed time;
collect those separately in the external runner.

Success requires the frozen practical effect and cost criteria, survival against
the strong ordinary baselines, and the developer's recorded decision after seeing
the report. Report null and negative results. If both arms saturate, the report
does not change a useful decision, or the gain disappears against a cheap baseline,
revise the hypothesis. Repeated tuning on confirmation cases makes them development
data and requires a fresh confirmation set.

## Runnable integration exercise

The research bundle includes source, disclosed evidence and the local campaign CLI.
Python 3.10+ is required; campaign locking requires Linux/macOS (Windows: use WSL).
No install, network access, credentials or model calls are needed for this check:

```sh
PYTHONPATH=src python examples/participant-campaign/run_references.py /tmp/ue-reference-campaign
```

Choose a fresh output path. Read `docs/PROCEDURE_CAMPAIGNS.md` for the JSON packet
interface and `docs/PROCEDURE_PARTICIPANT_HANDOFF.md` for participant requirements.
The example compares named ordinary programs on four disclosed cases. It verifies
integration only. The source package is not an isolation boundary: an operator
must expose only allowed packets to a participant during an actual withheld trial.

## Joining and feedback

Use the public website's moderated comments to describe a concrete agent, decision,
existing test and reproduction result. Never post API keys, private prompts or
unreleased confirmation answers. The maintainer can discuss scope after review.
Publication, participant identity, a response time and paid service are not promised.
Sponsorship does not affect scoring, comparisons or conclusions.
