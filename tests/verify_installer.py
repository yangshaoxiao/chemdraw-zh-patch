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


def verify(package,legacy_package=None,previous_package=None):
    fixture=ROOT/('test-'+uuid.uuid4().hex[:8])
    fixture.mkdir()
    binpath=fixture/'磁盘 D 带空格'/'Program Files'/'RevvitySignalsSoftware'/'ChemDrawApplications_x64'
    datapath=fixture/'公共 数据'/'RevvitySignalsSoftware'/'ChemDrawApplications'/'ChemDraw'
    roots={'bin':binpath,'data':datapath,'gui':datapath/'GUI'}
    manifest=json.loads((ROOT/'manifest.json').read_text('utf-8'))
    script=(ROOT/'install.ps1').read_text('utf-8-sig')
    guard="if (Get-Process -Name 'ChemDraw','ChemDraw64','ChemDrawCtl','CAWPROP','Chem3D' -ErrorAction SilentlyContinue)"
    assert guard in script
    script=script.replace(guard,'if ($false)')
    excel_guard="if ($excelPending.Count -and (Get-Process -Name 'EXCEL' -ErrorAction SilentlyContinue))"
    assert excel_guard in script
    script=script.replace(excel_guard,'if ($false)')
    root_assignment="$roots = @{bin=$BinPath; data=$DataPath; gui=(Join-Path $DataPath 'GUI')}"
    assert root_assignment in script
    boundary=str(fixture)+'\\'
    script=script.replace(root_assignment,root_assignment+"\n    if (-not $BinPath.StartsWith('"+boundary+"',[StringComparison]::OrdinalIgnoreCase) -or -not $DataPath.StartsWith('"+boundary+"',[StringComparison]::OrdinalIgnoreCase)) { throw 'Fixture escaped isolated directories' }")
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
            # Windows/PowerShell can replace ProgramFiles when the host starts.
            # Set simulated defaults inside this disposable PowerShell process.
            quote=lambda value:"'"+str(value).replace("'","''")+"'"
            setup=("$env:ProgramFiles="+quote(binpath.parents[1])+"\n"+
                   "${env:ProgramFiles(x86)}="+quote(fixture/'No x86 install')+"\n"+
                   "$env:ProgramData="+quote(datapath.parents[2])+"\n"+
                   "& "+quote(fixture/'install.ps1')+" -Mode "+quote(mode)+" -Elevated")
            args=['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-Command',setup]
        else:
            args+=['-BinPath',str(binpath),'-DataPath',str(datapath)]
        result=subprocess.run(args,input=b'\n',capture_output=True,timeout=180,env=env)
        if (result.returncode==0)!=ok:
            raise AssertionError((mode,result.returncode,result.stdout.decode('utf-8',errors='replace'),result.stderr.decode('utf-8',errors='replace')))
    def check(state):
        for entry in manifest['files']:
            assert sha((roots[entry['group']]/entry['relative']).read_bytes())==entry[state],entry['relative']
    run('Validate');check('before');passed.append('custom Unicode and space paths; full reconstruction preflight')
    if any(e.get('optional_component')=='chemoffice_excel' for e in manifest['files']):
        marker="if ($false) { throw '请先保存全部 Excel 工作簿并完全退出 Excel，再安装或还原 ChemOffice Excel 汉化。' }"
        assert marker in script
        simulated=script.replace(marker,marker.replace('if ($false)','if ($excelPending.Count)'))
        write_script(simulated);run('Install',False);check('before');run('Validate');check('before');write_script()
        passed.append('Excel running blocks pending add-in writes while read-only validate remains allowed')
    run('Install');check('after');passed.append('install all manifest files using local source plus deltas')
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
        applied=0
        for entry in manifest['files']:
            routes=[r for r in entry['routes'] if r['source'] not in (entry['before'],entry['after'])]
            if not routes:continue
            routes=[r for r in routes if r['source'] in oldmap]
            if not routes:continue
            route=routes[0];data=oldmap[route['source']].read_bytes()
            assert sha(data)==route['source']
            (roots[entry['group']]/entry['relative']).write_bytes(data)
            applied+=1
        assert applied>0,'No actual v0.1 states were exercised'
        run('Install');check('after');passed.append('upgrade known v0.1 states through two differential routes')
        run('Restore');check('before');passed.append('restore English after v0.1 upgrade')
    if previous_package:
        old=json.loads((previous_package/'manifest.json').read_text('utf-8-sig'))
        for entry in old['files']:
            data=(previous_package/'payload'/entry['payload']).read_bytes()
            assert sha(data)==entry['after']
            (roots[entry['group']]/entry['relative']).write_bytes(data)
        run('Install');check('after');passed.append('upgrade prior v0.2/v0.2.1 state to current manifest')
        run('Restore');check('before');passed.append('restore English after analysis-layout upgrade')
    injected=script.replace("if ((Digest $job.Destination) -ne $job.Expected) { throw '写入后校验失败。' }",
        "if ($touched.Count -eq 2) { throw 'Injected second-write failure' }\n                if ((Digest $job.Destination) -ne $job.Expected) { throw '写入后校验失败。' }")
    assert injected!=script
    write_script(injected);run('Install',False);check('before');write_script()
    passed.append('partial transaction rollback restores all before hashes')
    optional=[e for e in manifest['files'] if e.get('optional_component')=='chem3d']
    if optional:
        assert len(optional)==2
        stored=[]
        for e in optional:
            target=roots[e['group']]/e['relative'];stored.append((target,target.read_bytes()));target.unlink()
        run('Validate');run('Install');run('Restore')
        for e in manifest['files']:
            if e not in optional:assert sha((roots[e['group']]/e['relative']).read_bytes())==e['before']
        passed.append('ChemDraw-only installation skips absent Chem3D and restores all core files')
        stored[0][0].write_bytes(stored[0][1]);run('Install',False)
        stored[1][0].write_bytes(stored[1][1]);check('before')
        passed.append('reject incomplete Chem3D installation before writes')
    drivers=[e for e in manifest['files'] if e.get('optional_component')=='chem3d_driver']
    if drivers:
        stored=[]
        for e in drivers:
            target=roots[e['group']]/e['relative'];stored.append((target,target.read_bytes()));target.unlink()
        run('Validate');run('Install');run('Restore')
        for e in manifest['files']:
            if e not in drivers:assert sha((roots[e['group']]/e['relative']).read_bytes())==e['before']
        for target,data in stored:target.write_bytes(data)
        check('before');passed.append('absent calculation drivers skip safely; core install and restore remain valid')
    excel_entries=[e for e in manifest['files'] if e.get('optional_component')=='chemoffice_excel']
    if excel_entries:
        stored=[]
        for e in excel_entries:
            target=roots[e['group']]/e['relative'];stored.append((target,target.read_bytes()));target.unlink()
        run('Validate');run('Install');run('Restore')
        for e in manifest['files']:
            if e not in excel_entries:assert sha((roots[e['group']]/e['relative']).read_bytes())==e['before']
        for target,data in stored:target.write_bytes(data)
        check('before');passed.append('absent ChemOffice Excel add-in skips safely and core restore remains valid')
    # Valid hash for invalid instructions: must fail reconstruction before software writes.
    entry=manifest['files'][0];route=entry['routes'][0];patch=fixture/route['path'];data=patch.read_bytes()
    bad_data=b'CDZHD1\0'+entry['after_size'].to_bytes(8,'little')+b'\x7f'
    patch.write_bytes(bad_data)
    bad=json.loads(json.dumps(manifest));r=bad['files'][0]['routes'][0];r['size']=len(bad_data);r['sha256']=sha(bad_data)
    write_manifest(bad);run('Install',False);check('before');patch.write_bytes(data);write_manifest()
    passed.append('reject invalid delta opcode before software writes')
    report={'checked_at':'2026-10-15','patch':manifest['patch'],'files':len(manifest['files']),'passed':passed,
            'fixture_scope':'isolated custom Unicode/space paths; no production file writes',
            'production_files_changed':False,'version':manifest['version']}
    (ROOT/'docs'/'verification_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--local-package',type=pathlib.Path,required=True)
    parser.add_argument('--legacy-package',type=pathlib.Path)
    parser.add_argument('--previous-package',type=pathlib.Path)
    args=parser.parse_args();verify(args.local_package,args.legacy_package,args.previous_package)
