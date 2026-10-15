"""MIT: build a standalone WinForms launcher containing only public differential data."""
import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]

def build(output_dir=None):
    manifest = json.loads((ROOT / 'manifest.json').read_text('utf-8'))
    version = manifest['patch']
    out = pathlib.Path(output_dir).resolve() if output_dir else ROOT / 'dist' / ('v' + version + '-gui')
    out.mkdir(parents=True, exist_ok=True)
    names = {'install.ps1', 'manifest.json', 'LICENSE', 'NOTICE.md'}
    for entry in manifest['files']:
        for route in entry['routes']:
            name = route['path']
            if not name.startswith('patches/') or '..' in pathlib.PurePosixPath(name).parts or pathlib.PurePosixPath(name).suffix != '.cdp':
                raise ValueError('Invalid public delta path')
            data = (ROOT / name).read_bytes()
            if len(data) != route['size'] or hashlib.sha256(data).hexdigest() != route['sha256']:
                raise ValueError('Delta mismatch: ' + name)
            names.add(name)
    payload = out / 'patch.zip'
    with zipfile.ZipFile(payload, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name in sorted(names):
            info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, (ROOT / name).read_bytes())
    digest = hashlib.sha256(payload.read_bytes()).hexdigest()
    info = out / 'BuildInfo.cs'
    info.write_text('using System.Reflection;\n[assembly: AssemblyTitle("ChemDraw 免费汉化工具")]\n'
                    '[assembly: AssemblyVersion("' + version + '.0")]\n'
                    'internal static class BuildInfo { internal const string Version="' + version + '"; '
                    'internal const string PayloadHash="' + digest + '"; }\n', encoding='utf-8-sig')
    compiler = pathlib.Path(os.environ['WINDIR']) / 'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    exe = out / ('ChemDraw-ZH-v' + version + '.exe')
    subprocess.run([str(compiler), '/nologo', '/target:winexe', '/platform:x64', '/optimize+',
                    '/out:' + str(exe), '/win32manifest:' + str(ROOT / 'gui/app.manifest'),
                    '/resource:' + str(payload) + ',patch.zip', '/reference:System.Windows.Forms.dll',
                    '/reference:System.Drawing.dll', '/reference:System.IO.Compression.dll',
                    str(ROOT / 'gui/Launcher.cs'), str(info)], check=True)
    (out / 'SHA256.txt').write_bytes((hashlib.sha256(exe.read_bytes()).hexdigest() + '  ' + exe.name + '\n').encode('utf-8'))
    print(str(exe), exe.stat().st_size, 'bytes;', len(names), 'embedded public files')
    return exe

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir")
    build(parser.parse_args().output_dir)
