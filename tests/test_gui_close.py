"""Exercise the real close-request block with fake processes, never desktop apps."""
import json
import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class NormalCloseTests(unittest.TestCase):
    def run_close(self, closes=True, has_window=True, excel_pending=True):
        source = (ROOT / 'install.ps1').read_text('utf-8-sig')
        start = source.index('        if ($CloseApplications) {\n            Write-Host')
        end = source.index("        if (Get-Process -Name 'ChemDraw'", start)
        block = source[start:end].replace('AddSeconds(20)', 'AddSeconds(0)')
        setup = r'''
$ErrorActionPreference='Stop'
$CloseApplications=$true
$script:closed=$false
$script:requests=0
$script:names=@()
$fake=[pscustomobject]@{MainWindowHandle=[IntPtr]HANDLE;ProcessName='EXCEL'}
$fake | Add-Member ScriptMethod CloseMainWindow { $script:requests++; $script:closed=CLOSES; return $true }
function Get-Process { param($Name,$ErrorAction)
    $script:names=@($Name)
    if (-not $script:closed -and 'EXCEL' -in $Name) { return $fake }
}
$pending=PENDING
$failed=$false
try {
'''.replace('HANDLE', '1' if has_window else '0').replace('CLOSES', '$true' if closes else '$false')
        setup = setup.replace('PENDING', "@([pscustomobject]@{Entry=[pscustomobject]@{optional_component='chemoffice_excel'}})" if excel_pending else '@()')
        script = setup + block + "\n} catch { $failed=$true }\n[pscustomobject]@{failed=$failed;requests=$script:requests;closed=$script:closed;names=$script:names} | ConvertTo-Json -Compress\n"
        work = ROOT / 'dist' / 'close-tests'
        work.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=work, suffix='.ps1', delete=False) as f:
            path = pathlib.Path(f.name)
            f.write(script.encode('utf-8-sig'))
        try:
            result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(path)], capture_output=True, timeout=15)
            self.assertEqual(result.returncode, 0, result.stderr)
            return json.loads(result.stdout.decode('utf-8', errors='replace').strip().splitlines()[-1])
        finally:
            path.unlink()

    def test_saved_app_receives_normal_close(self):
        r = self.run_close()
        self.assertFalse(r['failed']); self.assertTrue(r['closed']); self.assertEqual(r['requests'], 1)

    def test_unsaved_app_blocks_patch(self):
        r = self.run_close(closes=False)
        self.assertTrue(r['failed']); self.assertFalse(r['closed']); self.assertEqual(r['requests'], 1)

    def test_background_process_is_not_force_killed(self):
        r = self.run_close(has_window=False)
        self.assertTrue(r['failed']); self.assertEqual(r['requests'], 0)

    def test_excel_not_closed_when_addin_has_no_pending_change(self):
        r = self.run_close(excel_pending=False)
        self.assertFalse(r['failed']); self.assertEqual(r['requests'], 0); self.assertNotIn('EXCEL', r['names'])

if __name__ == '__main__':
    unittest.main()
