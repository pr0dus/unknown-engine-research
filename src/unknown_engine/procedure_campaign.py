"""Local, disclosed A/B participant campaigns; no participant code is executed.

An operator keeps the ledger private and transports bounded JSON packets. This
is interface separation, not OS isolation, model attestation, or a hidden trial.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import fcntl
import hashlib
import html
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import uuid
from typing import Any

from . import procedure
from .procedure import COST_FIELDS, MAX_BUDGET, ProcedureEngine

SCHEMA = "unknown-engine/procedure-campaign-0.1"
PACKET_LIMIT = 65_536
CONFIG_LIMIT = 262_144
LEDGER_LIMIT = 128_000_000
MAX_REJECTIONS = 3
DISCLAIMER = (
    "Disclosed development diagnostic. Configurations and model identities are self-reported; "
    "no external participant identity, model invocation, or isolation is verified. "
    "These cases have a short fixed-script solution. This is not a hidden evaluation, "
    "frontier-difficulty claim, certification, or global ranking. Payment never changes scoring."
)


def _json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError, OverflowError, RecursionError) as exc:
        raise ValueError("A finite, bounded JSON value is required.") from exc


def _hash(value: Any) -> str:
    return hashlib.sha256(_json(value).encode()).hexdigest()


def _pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def read_json(path: str | Path, limit: int = PACKET_LIMIT) -> Any:
    with Path(path).open("rb") as stream:
        raw = stream.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("JSON file exceeds its size limit.")
    try:
        return json.loads(raw, object_pairs_hook=_pairs,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON number.")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("Malformed JSON file.") from exc


def _bounded(value: Any, limit: int) -> None:
    if len(_json(value).encode()) > limit:
        raise ValueError("JSON value exceeds its size limit.")


def _engine_hash() -> str:
    return hashlib.sha256(Path(procedure.__file__).read_bytes()).hexdigest()


def _campaign_hash() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def _outside_git(directory: Path) -> None:
    if any((parent / ".git").exists() for parent in (directory, *directory.parents)):
        raise ValueError("The private operator directory must be outside any Git checkout.")


def _write(directory: Path, document: dict[str, Any]) -> None:
    signed = dict(document, sha256=_hash(document))
    encoded = (_json(signed) + "\n").encode()
    if len(encoded) > LEDGER_LIMIT:
        raise ValueError("Campaign ledger exceeds its size limit.")
    fd, temporary = tempfile.mkstemp(prefix=".campaign-", dir=directory)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, directory / "campaign.json")
        folder = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(folder)
        finally:
            os.close(folder)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextlib.contextmanager
def _lock(directory: Path):
    _outside_git(directory)
    if not directory.is_dir():
        raise ValueError("Campaign directory does not exist.")
    if directory.stat().st_mode & 0o077:
        raise ValueError("Operator directory must have owner-only permissions (0700).")
    with (directory / ".lock").open("a+b") as stream:
        os.chmod(directory / ".lock", 0o600)
        fcntl.flock(stream, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def init_campaign(directory: str | Path, configs: list[dict[str, Any]], *, all_cases: bool = False,
                  budget: int = MAX_BUDGET) -> dict[str, Any]:
    """Create one campaign. The destination must not already exist."""
    directory = Path(directory).resolve()
    _outside_git(directory)
    _bounded(configs, CONFIG_LIMIT)
    if type(configs) is not list or len(configs) != 2:
        raise ValueError("Provide exactly two labelled configurations.")
    if type(budget) is not int or not 0 <= budget <= MAX_BUDGET:
        raise ValueError(f"budget must be an integer in 0..{MAX_BUDGET}.")
    participants = []
    for identity, item in zip(("a", "b"), configs):
        if (type(item) is not dict or set(item) != {"label", "configuration"}
                or type(item["label"]) is not str or not item["label"].strip() or len(item["label"]) > 160):
            raise ValueError("Each configuration requires a nonempty label and a configuration JSON value.")
        participants.append({"id": identity, **item, "configuration_sha256": _hash(item)})
    if participants[0]["label"] == participants[1]["label"]:
        raise ValueError("Use distinct participant labels.")
    models = procedure.full_catalogue() if all_cases else [procedure.source_model(), dict(procedure.source_model(), stages=2)]
    cases = [{"id": uuid.uuid4().hex, "profile": "full", "model": model} for model in models]
    cases += [{"id": uuid.uuid4().hex, "profile": "restricted", "model": model}
              for model in procedure.restricted_catalogue()]
    manifest = {"schema": SCHEMA, "campaign_id": uuid.uuid4().hex,
                "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
                "engine_sha256": _engine_hash(), "campaign_implementation_sha256": _campaign_hash(),
                "procedure_protocol": procedure.PROTOCOL, "participants": participants,
                "selection": "all" if all_cases else "small", "budget": budget, "cases": cases}
    directory.mkdir(mode=0o700, parents=False)
    try:
        _write(directory, {"manifest": manifest, "events": []})
    except Exception:
        # Leave the directory for inspection if persistence fails; do not replace an existing campaign.
        raise
    return {"campaign_id": manifest["campaign_id"], "cases": len(cases),
            "scheduled_attempts": 2 * len(cases), "scope": DISCLAIMER}


def _failure(payload: Any) -> None:
    if (type(payload) is not dict or set(payload) != {"reason"}
            or type(payload["reason"]) is not str or not 1 <= len(payload["reason"].strip()) <= 2000):
        raise ValueError("Failure payload must contain a nonempty reason of at most 2000 characters.")


def _apply_response(trial: dict[str, Any], kind: str, payload: Any) -> None:
    if kind == "experiment":
        trial["engine"].experiment(payload)
    elif kind == "submit":
        trial["engine"].submit(payload)
        trial["status"] = "submitted"
    elif kind == "fail":
        _failure(payload)
        trial["status"], trial["failure"] = "failed", payload
    else:
        raise ValueError("Response kind must be experiment, submit, or fail.")
    trial["last_rejection"] = None


def _record_rejection(trial: dict[str, Any], reason: str) -> None:
    trial["rejected_responses"] += 1
    trial["last_rejection"] = reason
    if trial["rejected_responses"] >= MAX_REJECTIONS:
        trial["status"] = "failed"
        trial["failure"] = {"reason": f"Participant exhausted the {MAX_REJECTIONS}-response rejection limit: {reason}"}


def _load(directory: Path) -> tuple[dict[str, Any], dict[tuple[str, str], dict[str, Any]]]:
    record = read_json(directory / "campaign.json", LEDGER_LIMIT)
    if type(record) is not dict or set(record) != {"manifest", "events", "sha256"}:
        raise ValueError("Invalid campaign ledger schema.")
    document = {"manifest": record["manifest"], "events": record["events"]}
    if record["sha256"] != _hash(document):
        raise ValueError("Campaign content hash mismatch; do not continue a corrupted ledger.")
    manifest, events = document["manifest"], document["events"]
    if (type(manifest) is not dict or set(manifest) != {"schema", "campaign_id", "created_at", "engine_sha256", "campaign_implementation_sha256", "procedure_protocol", "participants", "selection", "budget", "cases"}
            or manifest["schema"] != SCHEMA or manifest["engine_sha256"] != _engine_hash()
            or manifest["campaign_implementation_sha256"] != _campaign_hash()
            or manifest["procedure_protocol"] != procedure.PROTOCOL):
        raise ValueError("Campaign schema, implementation, or engine hash mismatch.")
    if manifest["selection"] not in ("small", "all") or type(events) is not list:
        raise ValueError("Invalid campaign selection or events.")
    people = manifest["participants"]
    if type(people) is not list or len(people) != 2:
        raise ValueError("Invalid participant configuration manifest.")
    for identity, person in zip(("a", "b"), people):
        if (type(person) is not dict or set(person) != {"id", "label", "configuration", "configuration_sha256"}
                or person["id"] != identity or person["configuration_sha256"] != _hash({"label": person["label"], "configuration": person["configuration"]})):
            raise ValueError("Frozen participant configuration mismatch.")
    cases = manifest["cases"]
    expected = procedure.full_catalogue() if manifest["selection"] == "all" else [procedure.source_model(), dict(procedure.source_model(), stages=2)]
    expected_cases = [("full", model) for model in expected] + [("restricted", model) for model in procedure.restricted_catalogue()]
    if type(cases) is not list or len(cases) != len(expected_cases):
        raise ValueError("Invalid case manifest.")
    trials = {}
    for case, (profile, model) in zip(cases, expected_cases):
        if (type(case) is not dict or set(case) != {"id", "profile", "model"}
                or type(case["id"]) is not str or len(case["id"]) != 32
                or case["profile"] != profile or case["model"] != model):
            raise ValueError("Case manifest differs from the declared development selection.")
        for person in people:
            key = case["id"], person["id"]
            if key in trials:
                raise ValueError("Duplicate case identity.")
            trials[key] = {"engine": ProcedureEngine(model, profile, manifest["budget"]),
                           "status": "pending", "sequence": 0, "failure": None, "rejected_responses": 0, "last_rejection": None,
                           "profile": profile, "truth_validity": "valid" if procedure.operational_validity(model, profile) else "invalid"}
    if len(events) > len(trials) * (MAX_BUDGET + MAX_REJECTIONS + 2):
        raise ValueError("Too many campaign events.")
    for event in events:
        if type(event) is not dict or set(event) != {"case_id", "participant_id", "sequence", "kind", "payload"}:
            raise ValueError("Invalid event schema.")
        key = (event["case_id"], event["participant_id"])
        active_key = next((key for key, trial in trials.items() if trial["status"] in ("pending", "active")), None)
        if key not in trials or key != active_key:
            raise ValueError("Event is out of the fixed campaign order.")
        trial = trials[key]
        if type(event["sequence"]) is not int or event["sequence"] != trial["sequence"]:
            raise ValueError("Event sequence mismatch.")
        if event["kind"] == "start":
            if trial["status"] != "pending" or event["payload"] != {}:
                raise ValueError("Invalid start event.")
            trial["status"] = "active"
        else:
            if trial["status"] != "active":
                raise ValueError("Response precedes attempt start.")
            if event["kind"] == "rejected":
                rejection = event["payload"]
                if type(rejection) is not dict or set(rejection) != {"kind", "payload", "reason"}:
                    raise ValueError("Malformed recorded rejection.")
                try:
                    _apply_response(trial, rejection["kind"], rejection["payload"])
                except ValueError as exc:
                    if str(exc) != rejection["reason"]:
                        raise ValueError("Rejected response reconstruction differs.") from exc
                    _record_rejection(trial, rejection["reason"])
                else:
                    raise ValueError("A recorded rejection was actually a legal response.")
            else:
                _apply_response(trial, event["kind"], event["payload"])
        trial["sequence"] += 1
    return document, trials


def _packet(manifest: dict[str, Any], key: tuple[str, str], trial: dict[str, Any]) -> dict[str, Any]:
    person = next(person for person in manifest["participants"] if person["id"] == key[1])
    return {"schema": SCHEMA + "/state", "campaign_id": manifest["campaign_id"],
            "participant_id": key[1], "case_id": key[0], "sequence": trial["sequence"],
            "participant": {name: person[name] for name in ("label", "configuration_sha256")},
            "state": trial["engine"].state(), "rejected_responses": trial["rejected_responses"],
            "rejection_limit": MAX_REJECTIONS, "last_rejection": trial["last_rejection"], "scope": DISCLAIMER}


def next_packet(directory: str | Path) -> dict[str, Any]:
    directory = Path(directory).resolve()
    with _lock(directory):
        document, trials = _load(directory)
        for key, trial in trials.items():
            if trial["status"] not in ("pending", "active"):
                continue
            if trial["status"] == "pending":
                document["events"].append({"case_id": key[0], "participant_id": key[1],
                                           "sequence": 0, "kind": "start", "payload": {}})
                _write(directory, document)
                trial["sequence"], trial["status"] = 1, "active"
            return _packet(document["manifest"], key, trial)
        return {"schema": SCHEMA + "/complete", "campaign_id": document["manifest"]["campaign_id"],
                "complete": True, "attempts": len(trials), "scope": DISCLAIMER}


def respond(directory: str | Path, envelope: dict[str, Any]) -> dict[str, Any]:
    """Accept exactly one experiment, submission, or explicit failure atomically."""
    _bounded(envelope, PACKET_LIMIT)
    fields = {"schema", "campaign_id", "participant_id", "case_id", "sequence", "kind", "payload"}
    if type(envelope) is not dict or set(envelope) != fields or envelope["schema"] != SCHEMA + "/response":
        raise ValueError("Response requires the exact bound response schema.")
    directory = Path(directory).resolve()
    with _lock(directory):
        document, trials = _load(directory)
        manifest = document["manifest"]
        key = envelope["case_id"], envelope["participant_id"]
        if (type(key[0]) is not str or type(key[1]) is not str
                or envelope["campaign_id"] != manifest["campaign_id"] or key not in trials):
            raise ValueError("Response is bound to a different campaign, participant, or case.")
        trial = trials[key]
        if (trial["status"] != "active" or type(envelope["sequence"]) is not int
                or envelope["sequence"] != trial["sequence"]):
            raise ValueError("Response is stale, replayed, or the attempt is not active.")
        kind, payload = envelope["kind"], envelope["payload"]
        event_kind, event_payload = kind, payload
        try:
            _apply_response(trial, kind, payload)
        except ValueError as exc:
            event_kind = "rejected"
            event_payload = {"kind": kind, "payload": payload, "reason": str(exc)}
            _record_rejection(trial, str(exc))
        document["events"].append({"case_id": key[0], "participant_id": key[1],
                                   "sequence": envelope["sequence"], "kind": event_kind, "payload": event_payload})
        _write(directory, document)
        trial["sequence"] += 1
        if trial["status"] == "active":
            return _packet(manifest, key, trial)
        # Do not disclose scores/outcomes while the other arm or later cases remain playable.
        return {"schema": SCHEMA + "/ack", "campaign_id": manifest["campaign_id"],
                "participant_id": key[1], "case_id": key[0], "status": trial["status"],
                "sequence": trial["sequence"], "rejected_responses": trial["rejected_responses"],
                "failure": trial["failure"], "next": "Use next to begin the next scheduled attempt."}


def _mean(values: list[float]) -> float | None:
    return math.fsum(value / len(values) for value in values) if values else None


def _summarize(label: str, arm: list[dict[str, Any]]) -> dict[str, Any]:
    submitted = [trial for trial in arm if trial["status"] == "submitted"]
    results = [trial["engine"].state()["result"] for trial in submitted]
    eligible = {f"{disposition}_{truth}": sum(trial["truth_validity"] == truth for trial in group)
                for disposition, group in (("scheduled", arm), ("submitted", submitted),
                                           ("failed", [t for t in arm if t["status"] == "failed"]))
                for truth in ("valid", "invalid")}
    accepted = sum(r["invalid_model_acceptance"] for r in results)
    rejected = sum(r["valid_model_rejection"] for r in results)
    return {"label": label, "scheduled": len(arm), "attempted": len(arm),
            "submitted": len(results), "failed": len(arm) - len(results),
            "invalid_model_acceptance": accepted, "valid_model_rejection": rejected,
            "eligible_hidden_validity_counts": eligible,
            "invalid_acceptance_rate_submitted_invalid_only": accepted / eligible["submitted_invalid"] if eligible["submitted_invalid"] else None,
            "valid_rejection_rate_submitted_valid_only": rejected / eligible["submitted_valid"] if eligible["submitted_valid"] else None,
            "undetermined": sum(r["undetermined"] for r in results),
            "warranted_undetermined_scheduled": sum(t["profile"] == "restricted" for t in arm),
            "warranted_undetermined_submitted": sum(t["profile"] == "restricted" for t in submitted),
            "warranted_decision_correct": sum(r["warranted_decision_correct"] for r in results),
            "rejected_responses": sum(t["rejected_responses"] for t in arm),
            "mse_submitted_only": _mean([r["mse"] for r in results]),
            "mse_coverage": {"submitted": len(results), "scheduled": len(arm)},
            "target_costs_all_attempts": {field: sum(t["engine"].state()["costs"][field] for t in arm) for field in COST_FIELDS},
            "source_costs_all_attempts": {field: sum(t["engine"].state()["source_costs"][field] for t in arm) for field in COST_FIELDS}}


def _paired_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    errors = [row["mse_b_minus_a_both_submitted"] for row in rows if row["mse_b_minus_a_both_submitted"] is not None]
    return {"scheduled_worlds": len(rows), "both_submitted": len(errors),
            "excluded_due_to_failure": len(rows) - len(errors), "mean_mse_b_minus_a_both_submitted": _mean(errors)}


def report(directory: str | Path) -> dict[str, Any]:
    """A completed campaign report reconstructs every accepted event before scoring."""
    directory = Path(directory).resolve()
    with _lock(directory):
        document, trials = _load(directory)
        if any(trial["status"] in ("pending", "active") for trial in trials.values()):
            raise ValueError("Finish or explicitly fail every scheduled attempt before disclosing the report.")
        manifest = document["manifest"]
        rows, summaries = [], {}
        for person in manifest["participants"]:
            arm = [trial for key, trial in trials.items() if key[1] == person["id"]]
            summaries[person["id"]] = _summarize(person["label"], arm)
            summaries[person["id"]]["by_profile"] = {
                profile: _summarize(person["label"], [trial for trial in arm if trial["profile"] == profile])
                for profile in ("full", "restricted")}
        paired = []
        for case in manifest["cases"]:
            arms = {}
            for person in manifest["participants"]:
                trial = trials[(case["id"], person["id"])]
                state = trial["engine"].state()
                arms[person["id"]] = {"status": trial["status"], "failure": trial["failure"],
                    "target_costs": state["costs"], "source_costs": state["source_costs"],
                    "rejected_responses": trial["rejected_responses"],
                    "result": state.get("result"), "observations": state["history"]}
                if trial["status"] == "submitted":
                    arms[person["id"]]["replay"] = trial["engine"].replay()
            difference = None
            if all(arms[identity]["status"] == "submitted" for identity in ("a", "b")):
                difference = arms["b"]["result"]["mse"] - arms["a"]["result"]["mse"]
                paired.append(difference)
            rows.append({"case_id": case["id"], "profile": case["profile"], "disclosed_model": case["model"],
                         "arms": arms, "mse_b_minus_a_both_submitted": difference,
                         "target_units_b_minus_a_all_attempts": arms["b"]["target_costs"]["units"] - arms["a"]["target_costs"]["units"]})
        output = {"schema": SCHEMA + "/report", "manifest": manifest, "scope": DISCLAIMER,
                  "verification": "Reconstructed every accepted event using the pinned engine; content hashes detect accidental change, not operator dishonesty.",
                  "metric_notes": "Physical MSE, not Brier loss. Failed runs have no forecast score and never count as undetermined. Decision counts apply only to submitted runs. Source costs are reported per attempt; no amortization claim. Paired MSE excludes any case with a failed arm, with coverage explicit. Full-access cases and restricted information-limit controls must be interpreted separately; use the by_profile strata. Pooled means are descriptive only. Worlds are comparison units; this descriptive census has no inferential confidence interval.",
                  "participants": summaries, "paired": {"scheduled_worlds": len(rows), "both_submitted": len(paired),
                  "excluded_due_to_failure": len(rows) - len(paired), "mean_mse_b_minus_a_both_submitted": _mean(paired), "by_profile": {
                      profile: _paired_summary([row for row in rows if row["profile"] == profile])
                      for profile in ("full", "restricted")}},
                  "cases": rows, "events": document["events"]}
        output["sha256"] = _hash(output)
        return output


def render_html(value: dict[str, Any]) -> str:
    """Script-free report; display rounding never changes machine evidence."""
    escape = lambda item: html.escape(str(item), quote=True)

    def number(item: Any) -> str:
        return "—" if item is None else format(item, ".6g")

    def table(caption: str, headings: list[str], rows: list[list[Any]]) -> str:
        header = "".join(f"<th scope='col'>{escape(item)}</th>" for item in headings)
        body = "".join("<tr>" + "".join(f"<td>{escape(item)}</td>" for item in row) + "</tr>" for row in rows)
        return (f"<div class='table-wrap' role='region' tabindex='0' aria-label='{escape(caption)}'>"
                f"<table><caption>{escape(caption)}</caption><thead><tr>{header}</tr></thead>"
                f"<tbody>{body}</tbody></table></div>")

    sections = []
    for profile in ("full", "restricted"):
        decisions, costs = [], []
        for identity in ("a", "b"):
            row = value["participants"][identity]["by_profile"][profile]
            eligible = row["eligible_hidden_validity_counts"]
            decisions.append([identity.upper(), f"{row['submitted']} / {row['scheduled']}", row["failed"],
                              f"{row['invalid_model_acceptance']} / {eligible['submitted_invalid']}",
                              f"{row['valid_model_rejection']} / {eligible['submitted_valid']}", row["undetermined"]])
            costs.append([identity.upper(), number(row["mse_submitted_only"]),
                          row["target_costs_all_attempts"]["units"], row["source_costs_all_attempts"]["units"],
                          row["rejected_responses"]])
        title = "Full access" if profile == "full" else "Restricted controls"
        sections.append(f"<section><h3>{title}</h3>" +
                        table(title + ": completion and decisions",
                              ["Arm", "Submitted / scheduled", "Failed", "Invalid accepted / eligible", "Valid rejected / eligible", "Undetermined"], decisions) +
                        table(title + ": forecasts and costs",
                              ["Arm", "MSE, submitted only", "Target units", "Source units", "Rejected replies"], costs) + "</section>")
    paired = []
    for profile, row in value["paired"]["by_profile"].items():
        paired.append([profile, row["scheduled_worlds"], row["both_submitted"], row["excluded_due_to_failure"],
                       number(row["mean_mse_b_minus_a_both_submitted"])])
    rows = []
    for row in value["cases"]:
        descriptions = []
        for identity in ("a", "b"):
            arm = row["arms"][identity]
            if arm["status"] == "failed":
                description = "failed: " + arm["failure"]["reason"]
            else:
                description = arm["result"]["decision"] + "; MSE " + number(arm["result"]["mse"])
            descriptions.append(description + "; target units " + str(arm["target_costs"]["units"]))
        rows.append([row["case_id"], row["profile"], *descriptions, number(row["mse_b_minus_a_both_submitted"])])
    legend = "".join(f"<li><strong>{identity.upper()}</strong>: {escape(value['participants'][identity]['label'])}</li>"
                     for identity in ("a", "b"))
    provenance = "".join(f"<li>{escape(person['label'])}: <code>{escape(person['configuration_sha256'])}</code></li>"
                         for person in value["manifest"]["participants"])
    return ("<!doctype html><html lang='en'><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>"
            "<meta http-equiv='Content-Security-Policy' content=\"default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'\">"
            "<title>Unknown Engine participant comparison</title><style>"
            "body{font:17px/1.5 system-ui;max-width:1000px;margin:2rem auto;padding:1rem;color:#15202b}"
            "h1,h2,h3{line-height:1.2}h2{margin-top:2rem}h3{margin-bottom:.5rem}"
            "p,li,code{overflow-wrap:anywhere}.table-wrap{overflow-x:auto;margin:.8rem 0 1.2rem}"
            ".table-wrap:focus-visible{outline:3px solid #175c80;outline-offset:3px}"
            "table{border-collapse:collapse;width:100%;min-width:36rem;font-size:.85rem}"
            "caption{text-align:left;font-weight:650;padding:0 0 .4rem}"
            "td,th{border:1px solid #c8d3da;padding:.5rem;text-align:left;vertical-align:top;overflow-wrap:break-word}"
            "th{background:#edf3f6}code{font-size:.85em}.cases td:first-child{word-break:break-all}"
            "@page{size:A4;margin:16mm}"
            "@media print{body{margin:0;padding:0;font-size:9.5pt;line-height:1.35}h2{margin-top:1rem}"
            "h1,h2,h3,caption{break-after:avoid}.table-wrap{overflow:visible;margin:.6rem 0 .8rem}"
            "table{min-width:0;font-size:8.5pt;table-layout:fixed;break-inside:avoid}td,th{padding:.3rem}"
            "tr{break-inside:avoid}thead{display:table-header-group}a{color:inherit}}"
            "</style><main><h1>Participant comparison</h1>"
            f"<p>{escape(DISCLAIMER)}</p><p>Campaign <code>{escape(value['manifest']['campaign_id'])}</code></p>"
            f"<ul>{legend}</ul><h2>All scheduled attempts, separated by access</h2>"
            "<p>Acceptance/rejection denominators count submitted invalid/valid models respectively; failures stay visible separately. Restricted controls require undetermined. Costs include every attempt, including failures.</p>"
            f"{''.join(sections)}<p>{escape(value['metric_notes'])}</p>"
            "<p>Display values use six significant digits. A dash means no eligible score. Exact values remain in the JSON report.</p>"
            "<h2>Paired coverage by access</h2><p>MSE differences use only worlds where both arms submitted. Negative B − A favors B.</p>" +
            table("Paired worlds", ["Access", "Scheduled worlds", "Both submitted", "Excluded by failure", "Mean MSE B − A"], paired) +
            "<h2>Individual worlds</h2><div class='cases'>" +
            table("Per-world dispositions", ["World ID", "Access", "A disposition", "B disposition", "MSE B − A"], rows) + "</div>" +
            f"<h2>Provenance and evidence</h2><p>{escape(value['verification'])}</p><ul>{provenance}</ul>"
            "<p>The companion <a href='report.json'>report.json</a> contains exact configurations, predictions, outcomes, failure records, all events, costs and replay evidence.</p>"
            f"<p>Report SHA-256: <code>{escape(value['sha256'])}</code></p></main></html>")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    init = commands.add_parser("init", help="Freeze two configurations and disclosed paired cases")
    init.add_argument("directory"); init.add_argument("--configs", required=True)
    init.add_argument("--all", action="store_true", dest="all_cases"); init.add_argument("--budget", type=int, default=MAX_BUDGET)
    next_command = commands.add_parser("next", help="Get/repeat the current participant packet")
    next_command.add_argument("directory")
    response = commands.add_parser("respond", help="Accept one bound JSON response")
    response.add_argument("directory"); response.add_argument("--response", required=True)
    failure = commands.add_parser("fail", help="Retain a terminal failure for the current bound packet")
    failure.add_argument("directory"); failure.add_argument("--packet", required=True); failure.add_argument("--reason", required=True)
    report_command = commands.add_parser("report", help="Export JSON and printable HTML after all attempts end")
    report_command.add_argument("directory"); report_command.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            value = init_campaign(args.directory, read_json(args.configs, CONFIG_LIMIT), all_cases=args.all_cases, budget=args.budget)
        elif args.command == "next":
            value = next_packet(args.directory)
        elif args.command == "respond":
            value = respond(args.directory, read_json(args.response))
        elif args.command == "fail":
            packet = read_json(args.packet)
            value = respond(args.directory, {name: packet[name] for name in ("campaign_id", "participant_id", "case_id", "sequence")} |
                            {"schema": SCHEMA + "/response", "kind": "fail", "payload": {"reason": args.reason}})
        else:
            result = report(args.directory)
            destination = Path(args.output).resolve()
            _outside_git(destination)
            destination.mkdir(mode=0o700, parents=False)
            for filename, content in (("report.json", json.dumps(result, indent=2) + "\n"), ("report.html", render_html(result))):
                descriptor = os.open(destination / filename, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
                    stream.write(content)
            value = {"report_json": str(destination / "report.json"), "report_html": str(destination / "report.html"), "sha256": result["sha256"]}
        print(json.dumps(value, indent=2, allow_nan=False))
        return 0
    except (ValueError, OSError, KeyError, TypeError, OverflowError, RecursionError) as exc:
        print(json.dumps({"error": str(exc), "accepted": False}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
