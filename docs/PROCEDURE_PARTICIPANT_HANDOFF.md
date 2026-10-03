# Procedure validation: participant handoff

This is an **open development diagnostic**, not an independent hidden trial,
ranked competition or paid evaluation service. Every case and reference program
is disclosed. It is suitable for inspecting the protocol and testing an agent
integration. Its short fixed-script solution prevents a frontier-difficulty
claim. Read [the frozen protocol](PROCEDURE_VALIDITY_PROTOCOL.md) first.

## The useful decision

The eventual user question is: does adding explicit procedure validation to
agent B reduce inappropriate reuse compared with agent A, without excessive
rejection or experimental cost? The current reference programs can demonstrate
the failure and a repair. They do not answer that question for an independently
developed agent or establish a benefit in a real application.

The inherited procedure calibrates its instruments and checks an almost settled
response. A changed process can pass that check while responding differently to
short commands. Participants submit both a validity judgment about the inherited
model and physical forecasts after any repair. The report must keep these
separate: a correct rejection is not a correct forecast, and good repaired
forecasts do not make the inherited method valid.

## What a participant receives and returns

The public packet supplies the family assumptions, legal experiments and costs,
source readings, fitted source model, inherited recipe, access restrictions,
fixed prediction targets and observation history. A participant can request
bounded JSON experiments, then submit a decision (`valid`, `invalid`, or
`undetermined`) and predictions for every target key. No model weights or
provider credentials are submitted to the referee.

For full access, two standards and short reference/process pulses suffice for
exact identification. The restricted control permits only one command per
reset on an actuator with a one-tick delay. No legal sequence of experiments
can distinguish its two mechanisms. An unsupported lucky guess is not success
on that control.

The callable interface is `ProcedureEngine.state()`, `experiment(action)` and
`submit({"decision": ..., "predictions": ...})` in
`unknown_engine.procedure`. The included reference policies accept only a state
packet and an experiment callback. The engine can be operated separately from
the participant, but this library does not provide process isolation or a
production remote service. A local player with repository access can inspect
the answers; do not label such a run a blind evaluation.

The portable evidence contains forecasts, outcomes, validity decisions,
observations, reconstruction records and separate experiment, reset, tick and
sample counts. These are simulated resource units. A run does not confer an
intelligence level, certificate or global ranking. Support payments never
change scoring.

## Reproduce the disclosed reference exercise

From the preview checkout, use a new output directory:

```sh
PYTHONPATH=src python -m unknown_engine.procedure_reference \
  --freeze evidence/procedure-gate/freeze.json \
  --output /tmp/unknown-engine-procedure-reproduction
python scripts/verify_procedure_gate.py /tmp/unknown-engine-procedure-reproduction
```

This executes ordinary reference programs. It makes no model calls and cannot
be described as Claude, Codex or another external model playing. The freeze
record pins sources before the recorded development run; it is not an external
preregistration or a trusted timestamp.

## Before a claim about agent improvement

An independent developer should choose a specific A/B decision and freeze both
agent configurations before seeing evaluation outcomes. Record model identity
as reported by its provider, prompt bytes, tools, memory, sampling settings,
budgets, retries, timeouts and every failed attempt. No paid inference budget is
authorized by this handoff.

The disclosed cases may be used to build the integration and propose a fix.
Evaluate that fix on separately authored cases withheld from both the agent
developer and participant. Have an operator enforce the permitted interface and
retain an attempt ledger. Pair A and B on the same physical cases and access
conditions. Treat worlds, not individual correlated outputs, as the comparison
units; account for repeated stochastic runs and uncertainty when making a
comparative claim. Repeatedly tuning on the same withheld set turns it into
development data and requires a new confirmation set.

Report invalid acceptance, valid rejection, unresolved judgments, forecast
error and costs separately. Do not select only favorable cases or hide refusals.
Ask the independent user which actual development decision the report changed.
That feedback, and a confirmed improvement on new cases, would supply evidence
missing from the current project.

The proposed paid deliverable, if usefulness is established, is a scoped batch
comparison and written diagnosis with a reproducible evidence package. The
current GitHub support tiers fund development and promise no such service.
No participant has been recruited, contacted, verified or represented as having
completed that trial by this document.
