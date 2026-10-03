# Unknown Engine — open research

[Play the live research alpha](https://unknown-engine-production.up.railway.app/) · [Worked run](docs/WORKED_RUN.md) · [Support the research](https://github.com/sponsors/pr0dus) · [Contribute](CONTRIBUTING.md)

**Can an agent detect when a transferred procedure has become unreliable, even while its usual check still passes, and choose an economical experiment to decide what to do?**

Unknown Engine is an early research project by [pr0dus](https://github.com/pr0dus). This Apache-2.0 repository publishes runnable scientific source, ordinary reference programs, disclosed experiment records, verification scripts and a prospective independent-study protocol. It is intended for inspection, reproduction and criticism.

The hosted game studies calibration and transfer of cubic response models. The separate local procedure diagnostic studies a changing dynamical process and the validity of an inherited checking procedure. These are distinct tasks. [Read the design](docs/TRANSFER_DESIGN.md) and [procedure protocol](docs/PROCEDURE_VALIDITY_PROTOCOL.md).

## What is available

- Python source with no third-party runtime packages.
- A [complete worked run](docs/WORKED_RUN.md), with four measurements, predictions, outcomes and full simulated acquisition costs.
- Three complete disclosed studies: **224 original transfer records, 480 matched records and 970 procedure records**.
- [Archived report and replay files](examples/worked-run/) and verification scripts.
- A [prospective independent pilot](docs/INDEPENDENT_PROCEDURE_PILOT.md) and a runnable [participant campaign example](examples/participant-campaign/run_references.py).
- An [open sponsorship plan](SPONSORSHIP.md), [publication provenance](docs/PUBLICATION.md) and [checksums](MANIFEST.json).

## What the results say

| Finding | Interpretation |
| --- | --- |
| Source information roughly halves target measurements in the matched study, from about 3.06 to 1.53. | Adding six source measurements makes the single-recipient total about 7.53. Repeated reuse is not yet established. |
| The method and information-equivalent raw-data arms behave identically under the shared policy. | These results do not show a distinct method-transfer advantage. |
| A fixed ordinary program solves all 192 full-access procedure configurations. | This family is a regression diagnostic; it does not demonstrate frontier difficulty. |
| The studies use internal, disclosed simulated cases and ordinary programs. | Independent usefulness, external agent performance, novelty and real-world validity remain unestablished. |

Read the full [original transfer](evidence/transfer-preview/README.md), [matched transfer](evidence/transfer-matched/README.md) and [procedure](evidence/procedure-gate/README.md) results, including negative findings and information limits.

## Reproduce locally

Use Python 3.10 or later from this repository's root. No model key, network connection or package installation is required for these checks.

```sh
python scripts/verify_public_example.py
python scripts/verify_transfer_preview.py evidence/transfer-preview
python scripts/verify_transfer_matched.py evidence/transfer-matched
python scripts/verify_procedure_gate.py evidence/procedure-gate
```

The first command checks the manifest, matches the worked replays to the original archive and rebuilds the report. The remaining commands verify all 1,674 archived records. Checksums prove consistency, not authorship, trusted timestamps or independent replication.

To exercise the campaign interface with ordinary reference programs on four disclosed cases, choose a fresh output path. This command requires Linux/macOS; on Windows use WSL:

```sh
PYTHONPATH=src python examples/participant-campaign/run_references.py /tmp/ue-reference-campaign
```

[Reproduction instructions](docs/REPRODUCTION.md) include complete deterministic study regeneration. Regenerated random commitment salts change archive bytes even when physical cases and numerical results reproduce.

## Help test whether this is useful

Tell us what decision this diagnostic could improve for your agent or workflow. Reproduction attempts, inexpensive counterexamples and null results are useful contributions. See [CONTRIBUTING.md](CONTRIBUTING.md).

The independent study is **prepared, not run**. A genuinely new confirmation family still needs a reviewed adapter and independently authored cases. No independent participant or successful A/B result is claimed. AI tools assist development; the included experimental records come from ordinary deterministic programs, not hidden model evaluations.

## Sponsorship and license

Sponsorship supports development, documentation, testing and carefully budgeted future evaluations. It gives no influence over scores or conclusions, buys no custom work, and is not required to use or contribute to the project. [What support funds](SPONSORSHIP.md).

Code, project-authored documentation and included research records are licensed under [Apache-2.0](LICENSE). Retain [NOTICE](NOTICE) and applicable [third-party notices](THIRD_PARTY_NOTICES.md).

This is the initial curated public source release, published in October 2026 from previously prepared research. Its new Git history starts at publication. The separate development repository and website operations are not included. The live game is available; the additional website research pages await deployment. The files linked here work independently of that rollout.
