"""MIT: integration checks in isolated directories, using a local private full-file build."""
import argparse
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import uuid

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
sha=lambda b:hashlib.sha256(b).hexdigest()


def verify(package,legacy_package=None):
    fixture=ROOT/('test-'+uuid.uuid4().hex[:8])
    fixture.mkdir()
    binpath=fixture/'磁盘 D 带空格'/'Program Files'/'RevvitySignalsSoftware'/'ChemDrawApplications_x64'
    datapath=fixture/'公共 数据'/'RevvitySignalsSoftware'/'ChemDrawApplications'/'ChemDraw'
    roots={'bin':binpath,'data':datapath,'gui':datapath/'GUI'}
    manifest=json.loads((ROOT/'manifest.json').read_text('utf-8'))
    script=(ROOT/'install.ps1').read_text('utf-8-sig')
    # Guard disabled only in a private fixture: our targets cannot be used by the running app.
    guard="if (Get-Process -Name 'ChemDraw','ChemDraw64','ChemDrawCtl','CAWPROP' -ErrorAction SilentlyContinue)"
    assert guard in script
    script=script.replace(guard,'if ($false)')
    shutil.copytree(ROOT/'patches',fixture/'patches')
    for entry in manifest['files']:
        original=(package/'originals'/entry['group']/entry['relative']).read_bytes()
        assert sha(original)==entry['before']
        dest=roots[entry['group']]/entry['relative']
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(original)
    def write_script(value=script):
        (fixture/'install.ps1').write_text(value,'utf-8-sig')
    def write_manifest(value=manifest):
        (fixture/'manifest.json').write_text(json.dumps(value,ensure_ascii=False,indent=2),'utf-8')
    write_script();write_manifest()
    passed=[]
    def run(mode,ok=True,auto=False):
        args=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(fixture/'install.ps1'),'-Mode',mode,'-Elevated']
        env=os.environ.copy()
        if auto:
            env['ProgramFiles']=str(binpath.parents[1])
            env['ProgramFiles(x86)']=str(fixture/'No x86 install')
            env['ProgramData']=str(datapath.parents[2])
        else:
            args+=['-BinPath',str(binpath),'-DataPath',str(datapath)]
        result=subprocess.run(args,input=b'\n',capture_output=True,timeout=180,env=env)
        if (result.returncode==0)!=ok:
            raise AssertionError((mode,result.returncode,result.stdout.decode('utf-8',errors='replace'),result.stderr.decode('utf-8',errors='replace')))
    def check(state):
        for entry in manifest['files']:
            assert sha((roots[entry['group']]/entry['relative']).read_bytes())==entry[state],entry['relative']
    run('Validate');check('before');passed.append('custom Unicode and space paths; full reconstruction preflight')
    run('Install');check('after');passed.append('install all 78 files using local source plus deltas')
    run('Install');check('after');passed.append('idempotent install')
    run('Restore');check('before');passed.append('restore English through reverse deltas')
    run('Restore');check('before');passed.append('idempotent restore')
    # Isolate standard path discovery from the machine's actual registry entries.
    auto_script=script.replace("foreach ($hive in @('HKLM:','HKCU:'))","foreach ($hive in @())")
    assert auto_script!=script
    write_script(auto_script);run('Validate',auto=True);check('before');write_script()
    passed.append('automatic ProgramFiles/ProgramData discovery on simulated different drive')
    entry=manifest['files'][-1];target=roots[entry['group']]/entry['relative'];original=target.read_bytes()
    target.write_bytes(original+b'USER EDIT');run('Install',False)
    assert target.read_bytes()==original+b'USER EDIT'
    target.write_bytes(original);check('before');passed.append('reject unknown target edits before writes')
    route=entry['routes'][0];patch=fixture/route['path'];data=patch.read_bytes()
    patch.write_bytes(data+b'CORRUPTED');run('Install',False);check('before');patch.write_bytes(data)
    passed.append('reject corrupt differential files')
    bad=json.loads(json.dumps(manifest));bad['files'][0]['relative']='../outside.xml'
    write_manifest(bad);run('Install',False);check('before');write_manifest()
    passed.append('reject destination traversal')
    bad=json.loads(json.dumps(manifest));bad['files'][0]['routes'][0]['path']='../outside.cdp'
    write_manifest(bad);run('Install',False);check('before');write_manifest()
    passed.append('reject delta path traversal')
    bad=json.loads(json.dumps(manifest));bad['files'].append(bad['files'][0])
    write_manifest(bad);run('Install',False);check('before');write_manifest()
    passed.append('reject duplicate destinations')
    bad=json.loads(json.dumps(manifest));bad['version']='0.0.0.0'
    write_manifest(bad);run('Install',False);check('before');write_manifest()
    passed.append('reject wrong software version')
    if legacy_package:
        old=json.loads((legacy_package/'manifest.json').read_text('utf-8'))
        oldmap={e['after']:legacy_package/'payload'/e['payload'] for e in old['files']}
        for entry in manifest['files']:
            routes=[r for r in entry['routes'] if r['source'] not in (entry['before'],entry['after'])]
            if not routes:continue
            route=routes[0];data=oldmap[route['source']].read_bytes()
            assert sha(data)==route['source']
            (roots[entry['group']]/entry['relative']).write_bytes(data)
        run('Install');check('after');passed.append('upgrade known v0.1 states through two differential routes')
        run('Restore');check('before');passed.append('restore English after v0.1 upgrade')
    injected=script.replace("if ((Digest $job.Destination) -ne $job.Expected) { throw '写入后校验失败。' }",
        "if ($touched.Count -eq 2) { throw 'Injected second-write failure' }\n                if ((Digest $job.Destination) -ne $job.Expected) { throw '写入后校验失败。' }")
    assert injected!=script
    write_script(injected);run('Install',False);check('before');write_script()
    passed.append('partial transaction rollback restores all before hashes')
    # Valid hash for invalid instructions: must fail reconstruction before software writes.
    entry=manifest['files'][0];route=entry['routes'][0];patch=fixture/route['path'];data=patch.read_bytes()
    bad_data=b'CDZHD1\0'+entry['after_size'].to_bytes(8,'little')+b'\x7f'
    patch.write_bytes(bad_data)
    bad=json.loads(json.dumps(manifest));r=bad['files'][0]['routes'][0];r['size']=len(bad_data);r['sha256']=sha(bad_data)
    write_manifest(bad);run('Install',False);check('before');patch.write_bytes(data);write_manifest()
    passed.append('reject invalid delta opcode before software writes')
    report={'checked_at':'2026-10-09','files':len(manifest['files']),'passed':passed,
            'fixture_scope':'isolated custom Unicode/space paths; no production file writes',
            'production_files_changed':False,'version':manifest['version']}
    (ROOT/'docs'/'verification_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--local-package',type=pathlib.Path,required=True)
    parser.add_argument('--legacy-package',type=pathlib.Path)
    args=parser.parse_args();verify(args.local_package,args.legacy_package)
