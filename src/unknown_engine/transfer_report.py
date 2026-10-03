"""Portable reports for completed, disclosed transfer-practice runs.

Reports are local, reproducible scorecards, not a ranked or certified evaluation.
The deterministic reference receives the same public information and experiment
budget, and is run only after the participant has completed the world.
"""

from __future__ import annotations

import argparse
import hashlib
from html import escape
from importlib import metadata
import json
from pathlib import Path
from typing import Any

from .transfer import TransferEngine, verify_transfer_replay
from .transfer_matched import matched_forecast


REPORT_SCHEMA = "unknown-engine-transfer-run-report/0.1"
COMPARISON_TOLERANCE = 1e-12
NEUTRAL_BRIER = 0.25


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _comparison(participant: float, reference: float) -> str:
    difference = participant - reference
    if abs(difference) <= COMPARISON_TOLERANCE:
        return "tied"
    return "better" if difference < 0 else "worse"


def _source_provenance() -> dict[str, Any]:
    try:
        version = metadata.version("unknown-engine")
    except metadata.PackageNotFoundError:
        version = None
    directory = Path(__file__).resolve().parent
    return {
        "installed_package_version": version,
        "source_sha256": {
            name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
            for name in ("transfer.py", "transfer_matched.py", "transfer_report.py")
        },
        "reference_function": "unknown_engine.transfer_matched.matched_forecast",
        "reference_implementation": "Exact weighted finite-family Bayesian posterior with greedy observation-entropy selection and deterministic action ordering.",
    }


def build_run_report(replay: dict[str, Any], participant_label: str | None = None) -> dict[str, Any]:
    """Verify a completed disclosure, then calculate its paired run scorecard.

    The optional label is a self-report and is never identity verification. This
    function projects a fixed schema; arbitrary extra fields and credentials
    cannot be carried from a session envelope into the report.
    """
    verification = verify_transfer_replay(replay)
    if not verification.get("valid"):
        raise ValueError("A valid, completed, disclosed transfer replay is required: " + str(verification.get("error", "verification failed")))
    if participant_label is not None and (type(participant_label) is not str or not participant_label.strip() or len(participant_label) > 160):
        raise ValueError("participant_label must be a nonempty string of at most 160 characters, or None.")

    state = replay["state"]
    result = state["result"]
    disclosure = replay["disclosure"]
    # The operator creates a paired world only after accepting the final replay.
    # matched_forecast itself receives only public state and an experiment callback.
    engine = TransferEngine(seed=disclosure["seed"], condition=disclosure["config"]["condition"],
                            arm=replay["arm"], budget=replay["budget_total"])
    policy = matched_forecast(engine.state(), engine.experiment)
    reference_state = engine.submit(policy["probabilities"])
    reference_replay = engine.replay(reveal=True)
    reference_verification = verify_transfer_replay(reference_replay)
    if not reference_verification.get("valid") or reference_replay["disclosure"]["config"] != disclosure["config"]:
        raise ValueError("The paired deterministic reference failed verification or physical-world matching.")
    reference_result = reference_state["result"]
    replay_sha = _sha(replay)
    loss = result["primary_brier"]
    reference_loss = reference_result["primary_brier"]

    return {
        "schema": REPORT_SCHEMA,
        "run_id": "ue-" + replay_sha,
        "replay_sha256": replay_sha,
        "protocol": replay["protocol"],
        "family": replay["family"],
        "arm": replay["arm"],
        "budget_total": replay["budget_total"],
        "participant": {"label": participant_label, "identity_verified": False,
                        "label_provenance": "Optional self-reported label; no provider, model, person, or organization identity was verified."},
        "verification": {
            "completed_disclosed_replay_verified": True,
            "simulation_verified": True,
            "receipt_entries": verification["entries"],
            "commitment": replay["commitment"],
            "chain_head": replay["chain_head"],
            "scope": verification["scope"],
            "canonical_replay_encoding": "UTF-8 JSON; sorted keys; separators comma and colon; ensure_ascii=true; no NaN/Infinity. SHA-256 identifies these canonical replay bytes, not pretty-printed file bytes.",
        },
        "metrics": {
            "brier_loss": loss,
            "neutral_brier_loss": NEUTRAL_BRIER,
            "brier_skill_score": 1 - loss / NEUTRAL_BRIER,
            "brier_skill_explanation": "1 - Brier loss / 0.25. This is relative forecast loss, NOT accuracy: 1 means zero loss, 0 ties constant 0.5, and negative values are worse than that neutral reference.",
            "versus_neutral": _comparison(loss, NEUTRAL_BRIER),
            "target_experiments": result["target_cost"],
            "source_experiments": result["donor_cost"],
            "total_experiments": result["total_cost"],
            "cost_unit": "Declared experiment units; excludes computation, model tokens, money, and development effort.",
            "source_cost_provenance": "Six-experiment referee-generated donor fixture when donor information is supplied; zero in the none arm. Not measured participant discovery effort.",
        },
        "targets": [
            {"key": target["key"], "x": target["x"], "threshold": target["threshold"],
             "probability": result["probabilities"][target["key"]],
             "outcome": result["outcomes"][target["key"]],
             "brier_loss": (result["probabilities"][target["key"]] - result["outcomes"][target["key"]]) ** 2}
            for target in state["targets"]
        ],
        "reference": {
            "name": "matched_finite_bayes",
            "comparison_scope": "Post-completion deterministic reference on the identical physical world, with the same initial public information, information arm, and target experiment budget. Computation is not equalized or measured; the policy is not asserted to be optimal.",
            "arm": replay["arm"], "budget_total": replay["budget_total"],
            "physical_world_sha256": _sha(disclosure["config"]),
            "physical_pairing_verified": True,
            "completed_disclosed_replay_verified": True,
            "brier_loss": reference_loss,
            "posterior_expected_brier": policy["posterior_expected_brier"],
            "target_experiments": reference_result["target_cost"],
            "source_experiments": reference_result["donor_cost"],
            "total_experiments": reference_result["total_cost"],
            "participant_minus_reference_brier": loss - reference_loss,
            "participant_vs_reference": _comparison(loss, reference_loss),
            "probabilities": dict(policy["probabilities"]),
            "experiment_actions": [dict(row["action"]) for row in reference_state["history"]],
            "stopping_reason": policy["stopping_reason"],
        },
        "provenance": _source_provenance(),
        "comparison_tolerance": COMPARISON_TOLERANCE,
        "limitations": [
            "Single practice run in a public, finite, noiseless family with exact calibration. It is not a frontier benchmark or evidence of real-world forecasting ability.",
            "These twelve targets share one world and are not twelve independent trials. No population confidence interval or general ability conclusion follows from this run.",
            "Replay reconstruction checks internal consistency. Hashes are not signatures and cannot detect an entirely substituted record without an independently retained commitment or checkpoint.",
            "The report does not verify participant identity, model identity, isolation, unseen data, or whether the participant accessed disclosed answers elsewhere.",
            "A strong deterministic reference is computed after completion using the same information and experiment budget; it may use different computation and different experiments. One-run wins are possible without general superiority.",
            "No global ranking, intelligence certification, performance tier, or sponsor privilege is awarded. Payments do not affect scores or comparison rules.",
        ],
    }


def report_to_html(report: dict[str, Any]) -> str:
    """Return a self-contained, printable scorecard; all text fields are escaped."""
    if type(report) is not dict or report.get("schema") != REPORT_SCHEMA:
        raise ValueError("Unsupported run report schema.")
    text = lambda value: escape(str(value), quote=True)
    number = lambda value: format(float(value), ".6f")
    metrics, reference = report["metrics"], report["reference"]
    neutral_comparison = {"better": "Better than neutral 0.5 forecasts", "tied": "Tied with neutral 0.5 forecasts",
                          "worse": "Worse than neutral 0.5 forecasts"}.get(metrics["versus_neutral"], "Neutral comparison unavailable")
    label = report["participant"]["label"]
    participant = (f'<p class="participant">{text(label)} <span>(self-reported; unverified)</span></p>'
                   if label is not None else '<p class="participant">Participant identity not recorded</p>')
    rows = "".join(
        f'<tr><th scope="row">{text(row["key"])}</th><td>{number(row["probability"])}</td>'
        f'<td>{text(row["outcome"])}</td><td>{number(row["brier_loss"])}</td></tr>'
        for row in report["targets"]
    )
    limitations = "".join(f"<li>{text(item)}</li>" for item in report["limitations"])
    source_hashes = "".join(f"<dt>{text(name)}</dt><dd><code>{text(value)}</code></dd>"
                            for name, value in report["provenance"]["source_sha256"].items())
    actions = "".join(f"<li><code>{text(json.dumps(action, sort_keys=True))}</code></li>"
                      for action in reference["experiment_actions"])
    actions = f"<ol>{actions}</ol>" if actions else "<p>No target experiments used by the reference.</p>"
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light"><title>Unknown Engine — Run report</title>
<style>
:root{{font-family:system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#17212b;background:#f3f6f8;line-height:1.55}}
body{{margin:0;padding:24px}}main{{max-width:960px;margin:auto;background:white;padding:32px;border:1px solid #d4dde4;border-radius:14px}}
h1{{line-height:1.15;font-size:2rem;margin:8px 0 16px}}h2{{font-size:1.25rem;margin-top:30px}}h3{{font-size:1rem}}
.eyebrow{{font-weight:750;letter-spacing:.06em;text-transform:uppercase;color:#27526a;font-size:.8rem}}
.participant{{font-weight:650;overflow-wrap:anywhere}}.participant span{{font-weight:400}}.note{{padding:14px 18px;border-left:4px solid #477a93;background:#f0f6fa}}
.scores{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin-top:22px}}
.score{{padding:18px;border:1px solid #c8d5de;border-radius:8px}}.score strong{{display:block;font-size:1.9rem;line-height:1.2;margin:8px 0}}
.table-wrap{{overflow-x:auto}}.table-wrap:focus-visible{{outline:3px solid #27526a;outline-offset:4px}}table{{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums}}th,td{{padding:10px 12px;border-bottom:1px solid #d5dde4;text-align:right}}
th:first-child,td:first-child{{text-align:left}}thead th{{background:#eaf1f5}}tbody th{{font-weight:500}}code{{font-size:.85em;overflow-wrap:anywhere;word-break:break-word}}
dl{{display:grid;grid-template-columns:minmax(140px,1fr) minmax(0,3fr);gap:7px 16px}}dt{{font-weight:650}}dd{{margin:0;overflow-wrap:anywhere}}li{{margin:.5rem 0}}
footer{{margin-top:28px;font-size:.9rem;color:#455663}}@media(max-width:600px){{body{{padding:8px}}main{{padding:20px 14px}}h1{{font-size:1.6rem}}dl{{display:block}}dd{{margin-bottom:12px}}th,td{{padding:9px 7px}}}}
@media print{{body{{background:white;padding:0}}main{{border:0;padding:0;max-width:none}}.score,table tr{{break-inside:avoid}}h2,h3{{break-after:avoid}}.table-wrap{{overflow:visible}}}}
</style></head><body><main>
<div class="eyebrow">Unknown Engine · Practice run</div><h1>Your experiment report</h1>{participant}
<p class="note">Completed replay reconstructed successfully. This verifies the recorded simulation and scoring; it does not certify the participant or establish a global rank.</p>
<div class="scores"><div class="score">Brier loss · lower is better<strong>{number(metrics["brier_loss"])}</strong>{text(neutral_comparison)}</div>
<div class="score">Brier skill · not accuracy<strong>{number(metrics["brier_skill_score"])}</strong>Relative to neutral Brier loss 0.25</div>
<div class="score">Target experiments used<strong>{text(metrics["target_experiments"])} / {text(report["budget_total"])}</strong>{text(metrics["source_experiments"])} source + {text(metrics["target_experiments"])} target = {text(metrics["total_experiments"])} total units</div></div>
<p>{text(metrics["brier_skill_explanation"])}</p><p>{text(metrics["cost_unit"])} {text(metrics["source_cost_provenance"])}</p>
<h2 id="comparison-title">Comparison on your world</h2><p>{text(reference["comparison_scope"])}</p>
<div class="table-wrap" tabindex="0" role="region" aria-labelledby="comparison-title"><table><thead><tr><th>Participant</th><th>Brier loss</th><th>Target units</th><th>Source units</th><th>Total units</th></tr></thead><tbody>
<tr><th scope="row">Your run</th><td>{number(metrics["brier_loss"])}</td><td>{text(metrics["target_experiments"])}</td><td>{text(metrics["source_experiments"])}</td><td>{text(metrics["total_experiments"])}</td></tr>
<tr><th scope="row">Finite Bayesian reference</th><td>{number(reference["brier_loss"])}</td><td>{text(reference["target_experiments"])}</td><td>{text(reference["source_experiments"])}</td><td>{text(reference["total_experiments"])}</td></tr>
<tr><th scope="row">Neutral 0.5 forecast</th><td>0.250000</td><td>—</td><td>—</td><td>—</td></tr></tbody></table></div>
<p>Analytical neutral baseline; no comparator run or cost comparison.</p>
<p>Your Brier loss is <strong>{text(reference["participant_vs_reference"])}</strong> relative to the finite Bayesian reference. Difference (your loss minus reference loss): <strong>{number(reference["participant_minus_reference_brier"])}</strong>. Negative differences favor your run. Differences within {text(report["comparison_tolerance"])} are reported as tied.</p>
<h3>Reference experiment sequence</h3>{actions}<p>Stopping reason: <code>{text(reference["stopping_reason"])}</code>.</p>
<h2 id="forecasts-title">Your twelve forecasts</h2><div class="table-wrap" tabindex="0" role="region" aria-labelledby="forecasts-title"><table><thead><tr><th>Physical event</th><th>Probability</th><th>Outcome</th><th>Squared loss</th></tr></thead><tbody>{rows}</tbody></table></div>
<h2>Run and verification details</h2><dl><dt>Run ID</dt><dd><code>{text(report["run_id"])}</code></dd><dt>Protocol</dt><dd>{text(report["protocol"])}</dd><dt>Family</dt><dd>{text(report["family"])}</dd>
<dt>Information arm</dt><dd>{text(report["arm"])}</dd><dt>Experiment budget</dt><dd>{text(report["budget_total"])}</dd><dt>Canonical replay SHA-256</dt><dd><code>{text(report["replay_sha256"])}</code></dd>
<dt>World configuration SHA-256</dt><dd><code>{text(reference["physical_world_sha256"])}</code></dd><dt>Installed package version</dt><dd>{text(report["provenance"]["installed_package_version"] or "Unavailable in this source checkout")}</dd></dl>
<p>{text(report["verification"]["canonical_replay_encoding"])}</p><h3>Implementation SHA-256</h3><dl>{source_hashes}</dl>
<h2>What this report establishes</h2><ul>{limitations}</ul><footer>Keep the completed disclosed replay alongside the JSON report. This HTML is a readable rendering, not a signed certificate. No payment changes the scoring rules.</footer>
</main></body></html>'''


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="One completed, disclosed replay JSON file (not an evidence collection).")
    parser.add_argument("--output", type=Path, required=True, help="New directory for report.json and report.html; existing paths are never overwritten.")
    parser.add_argument("--participant-label", help="Optional self-reported label; not verified identity.")
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("Output directory already exists; reports are never overwritten.")
    try:
        with args.input.open("rb") as handle:
            payload = handle.read(1_000_001)
        if len(payload) > 1_000_000:
            raise ValueError("Input replay exceeds the size limit.")
        replay = json.loads(payload)
        report = build_run_report(replay, participant_label=args.participant_label)
        rendered = report_to_html(report)
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output / "report.json").write_text(json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8")
        (args.output / "report.html").write_text(rendered, encoding="utf-8")
    except (OSError, ValueError, TypeError, RecursionError) as exc:
        parser.error(str(exc))
    print(json.dumps({"run_id": report["run_id"], "report_json": str(args.output / "report.json"),
                      "report_html": str(args.output / "report.html")}))


if __name__ == "__main__":
    main()
