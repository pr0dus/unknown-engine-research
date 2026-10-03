# Diagnostic transfer development evidence

This folder contains 32 disclosed development fixtures evaluated by seven deterministic programs. There were no model calls, independent donor discoveries, held-out trials or API charges.

**Main finding:** the finite-prior cold reference matches the transferred-method reference's zero Brier loss and uses fewer target experiments (3.09375 on average versus 4), with no six-experiment donor cost. The proposed advantage is not established by this toy family.

This compares a fixed four-probe repair policy with adaptive cold experimental design. It does not show that donor information is useless; a source-conditioned Bayesian policy and amortized donor costs remain untested.

- `report.json`: program definitions, aggregate and condition-level scores/costs, paired comparisons and limitations.
- `replays.json.gz`: all 224 completed records, public packets, observations, forecasts and disclosed world configurations.
- `verification.json`: reconstruction and independent arithmetic/pairing verification.
- `validation.json`: source/evidence digests and software validation scope.

Run `python scripts/verify_transfer_preview.py evidence/transfer-preview` from the repository root. See [preview status](../../docs/PREVIEW_STATUS.md) for interpretation, scope and release limitations. Existing historical evidence outside this folder is unchanged.
