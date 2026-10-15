"""Export local full-file build as distributable differential patch; never copy DLLs."""
import argparse
import hashlib
import json
import pathlib
from delta import make_delta

sha = lambda b: hashlib.sha256(b).hexdigest()


def export(package, output, legacy_package=None, previous_packages=(), patch_version='0.2.1', previous_deltas=()):
    manifest = json.loads((package / 'manifest.json').read_text('utf-8-sig'))
    output.mkdir(parents=True, exist_ok=True)
    patches = output / 'patches'
    patches.mkdir(exist_ok=True)
    legacy = {}
    legacy_by_target = {}
    if legacy_package:
        old = json.loads((legacy_package / 'manifest.json').read_text('utf-8-sig'))
        legacy = {e['after']: legacy_package / 'payload' / e['payload'] for e in old['files']}
        legacy_by_target = {e['payload'].replace('\\','/'):e for e in old['files']}
    previous = []
    for folder in previous_packages:
        old = json.loads((folder/'manifest.json').read_text('utf-8-sig'))
        previous.append({e['group']+'/'+e['relative']:(folder/'payload'/e['payload'],e['after']) for e in old['files']})
    compatible=[]
    for folder in previous_deltas:
        old=json.loads((folder/'manifest.json').read_text('utf-8-sig'))
        if old['version']!=manifest['version']:raise ValueError('Previous deltas have a different version')
        compatible.append((folder,{e['group']+'/'+e['relative']:e for e in old['files']}))
    result = {'format': 1, 'patch': patch_version, 'version': manifest['version'],
              'architecture': 'x64', 'statistics': manifest['statistics'], 'files': []}
    if manifest['statistics'].get('calculation_ui_strings'):
        result['calculation_ansi_code_page']=936
    for number, entry in enumerate(manifest['files']):
        before = (package / 'originals' / entry['payload']).read_bytes()
        after = (package / 'payload' / entry['payload']).read_bytes()
        if sha(before) != entry['before'] or sha(after) != entry['after']:
            raise ValueError('Local package hash mismatch: ' + entry['relative'])
        item = {k: entry[k] for k in ('group', 'relative', 'before', 'after')}
        if entry['group']=='bin' and entry['relative'] in ('Chem3D.exe','Chem3DCtl.ocx'):
            item['optional_component']='chem3d'
        if entry['group']=='bin' and entry.get('kind')=='reviewed_calculation_ui':
            item['optional_component']='chem3d_driver'
        if entry['group']=='bin' and entry.get('kind')=='reviewed_excel_ui':
            item['optional_component']='chemoffice_excel'
        item['before_size'], item['after_size'] = len(before), len(after)
        item['routes'] = []
        pairs = [('install', before, after), ('restore', after, before)]
        old_entry=legacy_by_target.get(entry['group']+'/'+entry['relative'])
        legacy_hash=entry.get('legacy') or (old_entry['after'] if old_entry and old_entry['before']==entry['before'] else None)
        if legacy_hash and legacy_hash not in (entry['before'], entry['after']):
            if legacy_hash not in legacy:
                raise ValueError('Provide --legacy-package for v0.1 upgrade support')
            old = legacy[legacy_hash].read_bytes()
            if sha(old) != legacy_hash:
                raise ValueError('Legacy hash mismatch')
            pairs.append(('legacy-to-original', old, before))
        seen={sha(source) for _,source,_ in pairs}
        for n,package_map in enumerate(previous,1):
            old=package_map.get(entry['group']+'/'+entry['relative'])
            if old and old[1] not in seen and old[0].is_file():
                data=old[0].read_bytes()
                if sha(data)!=old[1]:raise ValueError('Previous package hash mismatch')
                pairs.append(('previous-%d-to-original'%n,data,before));seen.add(old[1])
        for name, source, target in pairs:
            delta = make_delta(source, target)
            path = 'patches/%03d-%s.cdp' % (number, name)
            (output / path).write_bytes(delta)
            item['routes'].append({'source': sha(source), 'target': sha(target),
                                   'path': path, 'sha256': sha(delta), 'size': len(delta)})
        for folder,entries in compatible:
            old=entries.get(entry['group']+'/'+entry['relative'])
            if not old or old['before']!=entry['before']:continue
            for route in old['routes']:
                if route['target']!=entry['before'] or route['source'] in seen:continue
                relative=pathlib.PurePosixPath(route['path'])
                if relative.is_absolute() or '..' in relative.parts:raise ValueError('Previous delta path traversal')
                data=(folder/relative).read_bytes()
                if sha(data)!=route['sha256'] or len(data)!=route['size']:raise ValueError('Previous delta hash mismatch')
                path='patches/%03d-compatible-%s-to-original.cdp'%(number,route['source'])
                (output/path).write_bytes(data)
                item['routes'].append({**route,'path':path});seen.add(route['source'])
        result['files'].append(item)
    (output / 'manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf-8')
    print('Exported', len(result['files']), 'files; differential bytes:', sum(p.stat().st_size for p in patches.glob('*.cdp')))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    parser.add_argument('--legacy-package', type=pathlib.Path)
    parser.add_argument('--previous-package',type=pathlib.Path,action='append',default=[])
    parser.add_argument('--patch-version',default='0.2.1')
    parser.add_argument('--previous-deltas',type=pathlib.Path,action='append',default=[])
    args = parser.parse_args()
    export(args.package, args.output, args.legacy_package,args.previous_package,args.patch_version,args.previous_deltas)
