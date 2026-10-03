# Unknown Engine — public research reproduction bundle

Release 2026-09-30.1. Apache-2.0; retain LICENSE and NOTICE. This curated export
contains simulator source, ordinary reference programs, already disclosed evidence,
verifiers and an independent-pilot handoff. It has no third-party runtime packages.
It is not the complete private repository or its history. Website operations,
account screenshots, participant credentials and moderation data are not included.
The third-party notice is retained from the repository; the screenshots/PDFs it
describes are not included here. Historical document links may refer to full-repo
materials outside this export; the commands and files below are self-contained.

Public website: https://unknown-engine-production.up.railway.app/
Walkthrough: [WORKED_RUN.md](WORKED_RUN.md) in this public repository.
Research results: the three evidence directories in this public repository. Website research-page deployment is pending as of 3 October 2026.

## Quick verification

Extract the ZIP and open a terminal in `unknown-engine-research`.
Use Python 3.10+; no installation, account, network or model key is needed.
All commands below operate locally. On native Windows, the campaign example
requires WSL because it uses POSIX file locking; other verifiers use the standard library.

```sh
python scripts/verify_public_example.py
python scripts/verify_transfer_preview.py evidence/transfer-preview
python scripts/verify_transfer_matched.py evidence/transfer-matched
python scripts/verify_procedure_gate.py evidence/procedure-gate
```

The first command checks every file digest in MANIFEST.json, matches both worked
replays against the original archive, reconstructs their physical world, and
rebuilds the report. Expected study coverage: 224 original transfer records,
480 matched records across 32 worlds, and 970 procedure records. The verifiers
print their checked coverage and fail on inconsistency. They may take a few minutes.
Hashes are consistency checks, not signatures, trusted timestamps or external replication.

## Rebuild a readable example report

Choose an output directory that does not exist:

```sh
PYTHONPATH=src python -m unknown_engine.transfer_report \
  --input examples/worked-run/adaptive-replay.json \
  --output /tmp/ue-worked-report \
  --participant-label "Ordinary adaptive reference — disclosed development example"
```

Open `/tmp/ue-worked-report/report.html`. Scores and canonical replay run ID
should match the supplied report. Installed package version metadata can differ.
The example is the existing `both-000` / `method_adaptive` run paired with
`blind_reuse`, selected to illustrate the workflow. It is not a new experiment,
AI-model result or representative sample. The online narrative was added retrospectively.

## Regenerate the studies

These commands run only ordinary deterministic programs. Use fresh output paths.
Physical cases and numerical results are reproducible; transfer commitment salts
are random, so regenerated archive bytes and receipt hashes will differ.

```sh
PYTHONPATH=src python -m unknown_engine.transfer_reference --output /tmp/ue-transfer
python scripts/verify_transfer_preview.py /tmp/ue-transfer

PYTHONPATH=src python -m unknown_engine.transfer_matched \
  --input evidence/transfer-preview/replays.json.gz \
  --spec docs/MATCHED_TRANSFER_PROTOCOL.md --output /tmp/ue-matched
python scripts/verify_transfer_matched.py /tmp/ue-matched

PYTHONPATH=src python -m unknown_engine.procedure_reference \
  --freeze evidence/procedure-gate/freeze.json --output /tmp/ue-procedure
python scripts/verify_procedure_gate.py /tmp/ue-procedure
```

Read the three `evidence/*/README.md` files before interpreting the results.
Method/raw equivalence, source costs, fixed-script saturation, disclosed-case
selection, correlated outputs and absence of external participants all matter.
The hosted cubic transfer game and the local dynamic procedure diagnostic are
separate tasks. Forecast performance alone does not establish causal understanding,
method invention, frontier difficulty or real-world usefulness.

## Independent researcher handoff

Read `docs/INDEPENDENT_PROCEDURE_PILOT.md`, complete its freeze worksheet, and use
`docs/PROCEDURE_CAMPAIGNS.md` for the local packet workflow. Integration check:

```sh
PYTHONPATH=src python examples/participant-campaign/run_references.py /tmp/ue-reference-campaign
```

This exercises four disclosed cases with named ordinary programs. It does not
run an external agent or provide an independently authored new family. Neither
the source nor the local CLI isolates a participant from the answers. Real
confirmation needs independent operation and reviewed new-family support.
Discuss a concrete use case or reproduction in the website's moderated comments;
do not post secrets or withheld case answers. Sponsorship never changes outcomes.
