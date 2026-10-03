"""Exercise paired packet handoff with ordinary programs, without model calls.

From the repository: PYTHONPATH=src python examples/participant-campaign/run_references.py /tmp/new-ue-campaign
The output directory must be new and outside a Git checkout.
"""
import argparse
import hashlib
import json
from pathlib import Path

from unknown_engine import procedure_reference
from unknown_engine import procedure_campaign as campaign


def envelope(packet, kind, payload):
    return {name: packet[name] for name in
            ("campaign_id", "participant_id", "case_id", "sequence")} | {
                "schema": campaign.SCHEMA + "/response", "kind": kind, "payload": payload}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    policies = {"a": "legacy_check", "b": "fixed_sysid"}
    source_hash = hashlib.sha256(Path(procedure_reference.__file__).read_bytes()).hexdigest()
    campaign.init_campaign(args.directory, [
        {"label": "Ordinary reference: " + policy,
         "configuration": {"policy": policy, "policy_source_sha256": source_hash,
                           "inference": "none", "scope": "disclosed integration smoke"}}
        for policy in policies.values()
    ])
    while True:
        packet = campaign.next_packet(args.directory)
        if packet.get("complete"):
            break

        def experiment(action):
            nonlocal packet
            packet = campaign.respond(args.directory, envelope(packet, "experiment", action))
            return packet["state"]

        answer = procedure_reference.run_policy(policies[packet["participant_id"]], packet["state"], experiment)
        campaign.respond(args.directory, envelope(packet, "submit",
                         {name: answer[name] for name in ("decision", "predictions")}))
    result = campaign.report(args.directory)
    export = args.directory / "export"
    exit_code = campaign.main(["report", str(args.directory), "--output", str(export)])
    if exit_code:
        raise SystemExit(exit_code)
    print(json.dumps({"participants": result["participants"], "paired": result["paired"]}, indent=2))


if __name__ == "__main__":
    main()
