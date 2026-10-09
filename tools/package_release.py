"""MIT: curate and verify public source/release ZIPs using explicit allowlists."""
import hashlib
import json
import pathlib
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
DIST = ROOT / 'dist'


def collect(source=False):
    names = ['README.md','使用说明.txt','LICENSE','NOTICE.md','install.ps1','manifest.json',
             '一键安装汉化.cmd','一键还原英文.cmd','检查安装环境.cmd']
    if source:
        names += ['.gitignore']
    result = [ROOT / n for n in names]
    result += sorted((ROOT / 'patches').glob('*.cdp'))
    result += sorted((ROOT / 'docs').glob('*'))
    if source:
        for folder in ('tools','tests','localization'):
            result += sorted(p for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    for file in result:
        if file.suffix.lower() in ('.dll','.exe','.pdb','.zip') or file.name in ('managed_string_uses.json','managed_user_strings.json','baseline_manifest.json'):
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
    paths = [archive('ChemDraw26_中文补丁_v0.2.1_通用差分版.zip',collect()),
             archive('chemdraw-zh-patch_v0.2.1_开源源码.zip',collect(True))]
    checksums = ''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n' for p in paths)
    (DIST/'SHA256.txt').write_text(checksums,'utf-8')
    for p in paths:
        print(p.name,p.stat().st_size,'bytes; verified')
