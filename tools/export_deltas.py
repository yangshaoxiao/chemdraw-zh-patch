"""Export local full-file build as distributable differential patch; never copy DLLs."""
import argparse
import hashlib
import json
import pathlib
from delta import make_delta

sha = lambda b: hashlib.sha256(b).hexdigest()


def export(package, output, legacy_package=None):
    manifest = json.loads((package / 'manifest.json').read_text('utf-8-sig'))
    output.mkdir(parents=True, exist_ok=True)
    patches = output / 'patches'
    patches.mkdir(exist_ok=True)
    legacy = {}
    if legacy_package:
        old = json.loads((legacy_package / 'manifest.json').read_text('utf-8-sig'))
        legacy = {e['after']: legacy_package / 'payload' / e['payload'] for e in old['files']}
    result = {'format': 1, 'patch': '0.2.1', 'version': manifest['version'],
              'architecture': 'x64', 'statistics': manifest['statistics'], 'files': []}
    for number, entry in enumerate(manifest['files']):
        before = (package / 'originals' / entry['payload']).read_bytes()
        after = (package / 'payload' / entry['payload']).read_bytes()
        if sha(before) != entry['before'] or sha(after) != entry['after']:
            raise ValueError('Local package hash mismatch: ' + entry['relative'])
        item = {k: entry[k] for k in ('group', 'relative', 'before', 'after')}
        item['before_size'], item['after_size'] = len(before), len(after)
        item['routes'] = []
        pairs = [('install', before, after), ('restore', after, before)]
        if entry.get('legacy') and entry['legacy'] not in (entry['before'], entry['after']):
            if entry['legacy'] not in legacy:
                raise ValueError('Provide --legacy-package for v0.1 upgrade support')
            old = legacy[entry['legacy']].read_bytes()
            if sha(old) != entry['legacy']:
                raise ValueError('Legacy hash mismatch')
            pairs.append(('legacy-to-original', old, before))
        for name, source, target in pairs:
            delta = make_delta(source, target)
            path = 'patches/%03d-%s.cdp' % (number, name)
            (output / path).write_bytes(delta)
            item['routes'].append({'source': sha(source), 'target': sha(target),
                                   'path': path, 'sha256': sha(delta), 'size': len(delta)})
        result['files'].append(item)
    (output / 'manifest.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), 'utf-8')
    print('Exported', len(result['files']), 'files; differential bytes:', sum(p.stat().st_size for p in patches.glob('*.cdp')))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--package', type=pathlib.Path, required=True)
    parser.add_argument('--output', type=pathlib.Path, required=True)
    parser.add_argument('--legacy-package', type=pathlib.Path)
    args = parser.parse_args()
    export(args.package, args.output, args.legacy_package)
