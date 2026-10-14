"""MIT: curate and verify public source/release ZIPs using explicit allowlists."""
import hashlib
import json
import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'
VERSION = json.loads((ROOT/'manifest.json').read_text('utf-8'))['patch']


def collect(source=False):
    names = ['README.md','使用说明.txt','LICENSE','NOTICE.md','install.ps1','manifest.json',
             '一键安装汉化.cmd','一键还原英文.cmd','检查安装环境.cmd',
             'reset_chem3d_menu_cache.ps1','重置Chem3D菜单缓存.cmd']
    if source:
        names += ['.gitignore']
    result = [ROOT / n for n in names]
    manifest=json.loads((ROOT/'manifest.json').read_text('utf-8'))
    result += sorted({ROOT/r['path'] for e in manifest['files'] for r in e['routes']})
    result += sorted((ROOT / 'docs').glob('*'))
    if source:
        catalogs={'xml_catalog.json','binary_catalog.json','extra_unique.json','managed_unique.json'}
        for folder in ('tools','tests','localization'):
            result += sorted(p for p in (ROOT/folder).glob('*') if p.is_file() and (p.suffix in ('.py','.ps1','.tsv') or p.name in catalogs))
    for file in result:
        if file.suffix.lower() in ('.dll','.exe','.ocx','.pdb','.zip') or file.name in ('managed_string_uses.json','managed_user_strings.json','baseline_manifest.json'):
            raise ValueError('Private artifact in export: ' + str(file))
        if not file.is_file():
            raise ValueError('Missing release file: ' + str(file))
    return result


def archive(name,files):
    path = DIST / name
    prefix = 'chemdraw-zh-patch/'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for file in files:
            z.write(file,prefix+file.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(path) as z:
        if z.testzip():
            raise ValueError('Corrupt ZIP')
        for file in files:
            if z.read(prefix+file.relative_to(ROOT).as_posix()) != file.read_bytes():
                raise ValueError('ZIP round trip failed')
    return path


if __name__ == '__main__':
    DIST.mkdir(exist_ok=True)
    paths = [archive('chemdraw-zh-patch-v%s-windows-x64.zip'%VERSION,collect()),
             archive('chemdraw-zh-patch-v%s-source.zip'%VERSION,collect(True))]
    checksums = ''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in paths)
    (DIST/'SHA256.txt').write_text(checksums,'utf-8')
    for p in paths:
        print(p.name,p.stat().st_size,'bytes; verified')
