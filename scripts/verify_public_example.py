"""Reconstruct the public worked example and check its source archive and report."""
import gzip
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from unknown_engine.transfer import verify_transfer_replay
from unknown_engine.transfer_report import build_run_report


def main():
    manifest_path=ROOT/'MANIFEST.json'
    if manifest_path.exists():
        manifest=json.loads(manifest_path.read_bytes())
        for name,digest in manifest['files'].items():
            path=(ROOT/name).resolve()
            assert path.is_relative_to(ROOT) and path.is_file(), name
            assert hashlib.sha256(path.read_bytes()).hexdigest()==digest, name
    directory=ROOT/'examples/worked-run'
    if not directory.exists(): directory=ROOT/'src/unknown_engine/research_assets'
    archive=json.loads(gzip.decompress((ROOT/'evidence/transfer-preview/replays.json.gz').read_bytes()))
    replays=[]
    for name,policy in [('adaptive','method_adaptive'),('blind','blind_reuse')]:
        replay=json.loads((directory/(name+'-replay.json')).read_bytes())
        original=next(r['replay'] for r in archive['records'] if r['world_id']=='both-000' and r['participant']==policy)
        assert replay==original, 'Example differs from archived run'
        assert verify_transfer_replay(replay)['valid'], 'Invalid replay'
        replays.append(replay)
    assert replays[0]['disclosure']['config']==replays[1]['disclosure']['config']
    stored=json.loads((directory/'adaptive-report.json').read_bytes())
    rebuilt=build_run_report(replays[0],stored['participant']['label'])
    rebuilt['provenance']['installed_package_version']=None
    assert stored==rebuilt, 'Report reconstruction differs'
    assert stored['metrics']['brier_loss']==0 and stored['metrics']['target_experiments']==4
    assert replays[1]['state']['result']['primary_brier']==1/12
    print(json.dumps({'verified':True,'source_archive_match':True,'paired_world':True,'run_id':stored['run_id']}))


if __name__=='__main__': main()
