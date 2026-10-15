# SPDX-License-Identifier: MIT
"""MIT: recover a verified English baseline from the user's own local installation."""
import argparse
import hashlib
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'tools'))
from delta import apply_delta

sha = lambda b: hashlib.sha256(b).hexdigest()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bin', type=pathlib.Path, required=True)
    parser.add_argument('--data', type=pathlib.Path, required=True)
    args = parser.parse_args()
    roots = {'bin':args.bin.resolve(),'data':args.data.resolve(),'gui':args.data.resolve()/'GUI'}
    public = HERE.parent
    manifest = json.loads((public/'manifest.json').read_text('utf-8'))
    entries = []
    prepared = []
    for e in manifest['files']:
        if e.get('optional_component') in ('chem3d','chem3d_driver','chemoffice_excel') and not (roots[e['group']]/e['relative']).is_file():
            continue
        data = (roots[e['group']]/e['relative']).read_bytes()
        state = sha(data)
        if state != e['before']:
            routes = [r for r in e['routes'] if r['source']==state and r['target']==e['before']]
            if len(routes)!=1:
                raise ValueError('Unknown installed file: '+e['relative'])
            route = routes[0]
            patch = (public/route['path']).read_bytes()
            if sha(patch)!=route['sha256']:
                raise ValueError('Damaged delta')
            data = apply_delta(data,patch)
        if sha(data)!=e['before']:
            raise ValueError('English baseline hash mismatch')
        target = HERE/'baseline'/e['group']/e['relative']
        if target.exists() and target.read_bytes()!=data:
            raise ValueError('Refusing to overwrite a different baseline')
        prepared.append((target,data))
        entries.append({k:e[k] for k in ('group','relative','before')} | {'legacy':None})
    for target,data in prepared:
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes(data)
    (HERE/'baseline_manifest.json').write_text(json.dumps({'version':manifest['version'],
        'roots':{k:str(v) for k,v in roots.items()},'files':entries},ensure_ascii=False,indent=2),'utf-8')
    print('Captured verified local English baseline:',len(entries),'files; installed files unchanged.')
