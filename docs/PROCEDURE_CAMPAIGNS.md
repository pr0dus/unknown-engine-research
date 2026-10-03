# Local participant A/B campaigns

**Version compatibility:** the 0.5.0a5 report-layout update changes the campaign
module hash. Continue or export an existing 0.5.0a4 campaign using its original
a4 checkout/wheel. New a5 campaigns pin the new implementation. Do not edit old
ledger hashes to bypass the source check. Historical example reports remain
unchanged; [release-review examples](../examples/release-review/README.md)
show the current layout.


This interface turns the [participant handoff](PROCEDURE_PARTICIPANT_HANDOFF.md)
into a runnable, operator-owned comparison. It executes **no participant code,
model calls or paid inference**. An external runner supplies JSON responses and
its own inference resources. Linux and macOS are supported; the file lock uses
`fcntl`, so native Windows is not supported. Python 3.10 or later is required.

The comparison asks whether agent configuration B improves procedure validation
relative to A on the same cases and simulated experiment budget. This is a
**disclosed development diagnostic**, with a public short fixed-script solution.
It is not a blind evaluation, independent model trial, frontier challenge,
verified identity, ranking or certification. It does not establish practical
transfer or willingness to pay. Sponsorship never changes the scoring.

## A runnable integration check

From an installed checkout, this ordinary-program example exercises the exact
packet interface and exports a report. Choose a new directory outside Git:

```sh
PYTHONPATH=src python examples/participant-campaign/run_references.py /tmp/ue-reference-campaign
```

It compares `legacy_check` with `fixed_sysid` on four disclosed cases. It makes
no language-model calls. This is an integration demonstration of known reference
behavior, not new evidence about independent participants. Its output is private
until you deliberately share it. The default four-case mix must not be treated
as a representative population or inferential model ranking.

## Freeze two real participant configurations

Install the package with `python -m pip install .`. The console command is
`unknown-engine-campaign`; the equivalent command from a checkout is
`PYTHONPATH=src python -m unknown_engine.procedure_campaign`.

Create a JSON file such as `/tmp/ue-configs.json` containing exactly two objects:

```json
[
  {
    "label": "A — current agent",
    "configuration": {
      "model": "provider/model identity, self-reported",
      "prompt": "Exact prompt text goes here.",
      "tools": [],
      "memory": "fresh per case",
      "settings": {"temperature": 0},
      "runner_version": "your commit or package version",
      "timeout_seconds": 120,
      "declared_retry_policy": "no resampling of completed attempts"
    }
  },
  {
    "label": "B — explicit procedure validation",
    "configuration": {
      "model": "same provider/model, self-reported",
      "prompt": "Exact revised prompt text goes here.",
      "tools": [],
      "memory": "fresh per case",
      "settings": {"temperature": 0},
      "runner_version": "your commit or package version",
      "timeout_seconds": 120,
      "declared_retry_policy": "no resampling of completed attempts"
    }
  }
]
```

`configuration` can contain arbitrary finite JSON. Declare model, prompt,
sampling, tools, memory, resource limits and runner version honestly. Do not
include credentials, personal data or private material you cannot later share:
the final local report includes the configurations. Names are self-reported;
the tool neither verifies model identity nor proves a model was called.

```sh
unknown-engine-campaign init /tmp/ue-participants --configs /tmp/ue-configs.json
unknown-engine-campaign next /tmp/ue-participants > /tmp/ue-packet.json
```

The destination must not exist and must be outside every Git checkout. Its
owner-only directory and ledger permissions are 0700 and 0600. Keep that
operator directory inaccessible to participant processes. File permissions are
only a precaution: this package does **not** sandbox processes or prevent a
participant running as the same user from reading it.

The default selection contains a full-access unchanged model, a full-access
changed-stage model and the two restricted information-limit controls. Each
appears once per configuration, A then B, paired on the same physical model.
Opaque case identifiers do not make public deterministic case ordering secret.
Use `--all` at initialization for all 192 full-access configurations plus both
restricted controls: 194 worlds, 388 scheduled attempts. `--budget N` applies the
same 0–64 simulated target-unit cap to both arms; the default is 64. Changing the
budget changes the diagnostic conditions and must be reported.

Configuration hashes cover the **canonical JSON values**, including labels,
using sorted keys, compact separators, ASCII escapes and finite numbers.
Whitespace *inside* prompt strings is preserved; indentation and key order in
the input JSON file are not part of the hash. The manifest also pins the exact
bytes of `procedure.py` and `procedure_campaign.py` and the procedure protocol.
A changed implementation refuses to resume the campaign. Start a new campaign
when changing code or configurations; retain the earlier campaign and failures.

## Exchange packets

`next` starts the next scheduled attempt, or repeats its current packet without
starting another. The packet includes the experiment rules, inherited procedure,
source observations, targets, observation history and remaining budget. It omits
the target's actual model, scores and answers. Each response must copy the exact
`campaign_id`, `participant_id`, `case_id` and integer `sequence` from that packet.

For example, a first sensor-standard experiment response is:

```json
{
  "schema": "unknown-engine/procedure-campaign-0.1/response",
  "campaign_id": "COPY FROM PACKET",
  "participant_id": "COPY FROM PACKET",
  "case_id": "COPY FROM PACKET",
  "sequence": 1,
  "kind": "experiment",
  "payload": {"kind": "standard", "value": 0}
}
```

Save the exact bound response as `/tmp/ue-response.json`, then run:

```sh
unknown-engine-campaign respond /tmp/ue-participants --response /tmp/ue-response.json > /tmp/ue-packet.json
```

An experiment returns the next state packet with a new sequence. To finish an
attempt, send `kind: "submit"` with a payload containing **exactly** `decision`
and `predictions`. `decision` is `valid`, `invalid` or `undetermined`.
`predictions` must supply a finite numeric physical forecast for **every** key
in `state.forecast_keys`, with no extra keys. This is physical MSE, not Brier
loss. The same ProcedureEngine validates actions, forecasts and budgets as in
the frozen diagnostic.

After a submission or terminal failure, the acknowledgement supplies no scores
or answers. Run `next` to start the next arm/case. Scores and actual models stay
withheld from the interface until **every** scheduled attempt has submitted or
explicitly failed, preventing the first arm's result from leaking through the
API while the second arm is still playing. This does not prevent access to
answers already present in the disclosed source code, cross-case memory,
out-of-band communication, or a dishonest operator.

Use fresh participant state per case if that is your declared comparison.
The runner, not this package, must enforce memory separation, external token
limits, model settings, wall-clock timeouts, tool restrictions and paid budgets.
The fixed A/B order is not counterbalanced; inference and latency claims require
a separately designed protocol. One attempt per case is an integration exercise,
not a robust stochastic-model evaluation.

## Rejections, retries and failures

A properly bound response containing an illegal experiment, over-budget action,
invalid forecast, malformed failure payload or unknown response kind is recorded
as a **rejected participant response**. It advances the packet sequence, leaves
all physical observations and engine costs unchanged, and returns the current
packet with `last_rejection` and `rejected_responses`. The participant can correct
its response using the new sequence. The third such rejection terminally fails
the attempt. These rejections remain in the report; they cannot disappear inside
a successful corrected run.

Stale sequences, replayed responses, wrong campaign/participant/case identities,
and invalid transport envelopes are rejected without modifying the ledger. A
lost response can be recovered with `next`; resending an already accepted packet
does not repeat the action or charge more units. A duplicate transport message
is not interpreted as a second participant attempt. `next` is also the recovery
path when a caller is unsure whether a write completed.

The JSON transport rejects duplicate keys, nonfinite constants and files over
64 KiB (configuration input: 256 KiB). A packet that cannot be parsed or bound
cannot be attributed automatically to an attempt. If this reflects a real
participant failure rather than a transport mistake, the operator **must** record
it with `fail`; do not silently resample an answer. The runner should retain its
raw provider logs separately. No automatic timeout or hidden model retry occurs.

```sh
unknown-engine-campaign fail /tmp/ue-participants --packet /tmp/ue-packet.json --reason "Participant timed out before submitting forecasts"
unknown-engine-campaign next /tmp/ue-participants > /tmp/ue-packet.json
```

`fail` is bound to the saved packet's identities and sequence, so a stale failure
cannot end a different attempt. The reason is retained together with observations
and costs accumulated before failure. Failure is never converted into
`undetermined`, zero MSE or a successful refusal. Finished attempts cannot be
reopened; a new campaign is a new declared study, not a way to hide failures.

## Export and interpret the report

After `next` returns `complete: true`, choose another new output directory:

```sh
unknown-engine-campaign report /tmp/ue-participants --output /tmp/ue-participant-report
```

The command writes `report.json` and a script-free, printable `report.html`.
The HTML escapes labels and failure text, includes no remote assets, and keeps
the large machine evidence in the companion JSON. Reports are local; nothing
is automatically uploaded, published or sent to anyone.

The report includes:

- All scheduled attempts and dispositions, including every terminal failure.
- Invalid-model acceptance, valid-model rejection, unresolved judgments,
  warranted-decision agreement and rejected responses as separate counts.
- Full-access and restricted-control strata. For each, the scheduled, submitted
  and failed valid/invalid denominators are explicit. An always-reject strategy
  must not look good merely because invalid models dominate the full catalogue.
- Physical forecast MSE for submitted cases, with coverage. Restricted controls
  warrant `undetermined` but still incur forecast error; evaluate them separately
  from the main full-access cases. Pooled means are descriptive only.
- Per-world B-minus-A forecast error **only when both arms submitted**. The number
  excluded due to either arm failing is explicit. This success-only comparison
  can favor an unreliable agent, so always read it with all-attempt dispositions.
- Target cost counts for every attempt, plus source cost counts separately.
  The supplied source package costs 16 units per attempt; no amortization or
  source-discovery benefit is claimed. Costs are simulated units, not money,
  elapsed time or model inference tokens.
- Exact configurations, implementation hashes, every ledger event, observations,
  forecasts, outcomes, per-submission deterministic replays and failure reasons.

Every operation reconstructs accepted actions and submissions from the ledger;
recorded rejections are checked against the pinned engine. Persistence uses an
exclusive local file lock and atomic replacement. A SHA-256 content hash detects
accidental corruption. These mechanisms are not a signature, trusted timestamp,
external verification, model attestation or protection against a local operator
rewriting a ledger and its hash. Network filesystems with different lock or
atomicity semantics are outside this local-tool guarantee.

The valid/invalid label follows the frozen access-scoped scoring rule: in full
access it compares to hidden truth, and in restricted access the warranted label
is always `undetermined`. It does not certify that a participant's particular
history justified its answer. The diagnostic grants no intelligence tier and
makes no population-confidence claim from correlated output points.

For a stronger research claim, first specify the development decision, freeze
A/B configurations, retain every failure, and run separately authored cases
withheld from the developer under independent operation. Repeatedly tuning on a
set turns it into development data. An independent user showing that the result
changed a useful decision remains an unmet milestone, not something this CLI
establishes by itself.
