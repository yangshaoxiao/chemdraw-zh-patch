param(
    [ValidateSet('Validate','Install','Restore')][string]$Mode = 'Install',
    [string]$BinPath,
    [string]$DataPath,
    [switch]$Elevated,
    [string]$LogPath
)
# SPDX-License-Identifier: MIT
$ErrorActionPreference = 'Stop'
$packageRoot = $PSScriptRoot

function Digest([string]$path) {
    $stream = [IO.File]::OpenRead($path)
    $hash = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
    finally { $hash.Dispose(); $stream.Dispose() }
}
function Within([string]$root, [string]$relative) {
    if ([IO.Path]::IsPathRooted($relative)) { throw '不允许绝对文件路径。' }
    $base = [IO.Path]::GetFullPath($root).TrimEnd('\') + '\'
    $full = [IO.Path]::GetFullPath((Join-Path $base $relative))
    if (-not $full.StartsWith($base,[StringComparison]::OrdinalIgnoreCase)) { throw "路径越界：$relative" }
    $walk = $full
    while ($walk) {
        if (Test-Path -LiteralPath $walk) {
            $item = Get-Item -LiteralPath $walk -Force
            if ($item.LinkType -in @('SymbolicLink','Junction')) { throw "目录含符号链接或联接：$walk" }
        }
        $parent = Split-Path -Parent $walk
        if ($parent -eq $walk) { break }
        $walk = $parent
    }
    return $full
}
function Version-OK([string]$folder,[string]$version) {
    $exe = Join-Path $folder 'ChemDraw.exe'
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { return $false }
    return (Get-Item -LiteralPath $exe).VersionInfo.FileVersion -eq $version
}
function Find-Bin([string]$version) {
    $candidates = [Collections.Generic.List[string]]::new()
    foreach ($base in @($env:ProgramFiles,${env:ProgramFiles(x86)})) {
        if ($base) { $candidates.Add((Join-Path $base 'RevvitySignalsSoftware\ChemDrawApplications_x64')) }
    }
    foreach ($hive in @('HKLM:','HKCU:')) {
        foreach ($prefix in @('SOFTWARE\Microsoft\Windows\CurrentVersion','SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion')) {
            $app = Get-ItemProperty "$hive\$prefix\App Paths\ChemDraw.exe" -ErrorAction SilentlyContinue
            if ($app -and $app.'(default)') { $candidates.Add((Split-Path -Parent $app.'(default)')) }
            foreach ($record in @(Get-ItemProperty "$hive\$prefix\Uninstall\*" -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName -match 'ChemDraw|ChemOffice' })) {
                if ($record.InstallLocation) {
                    $candidates.Add($record.InstallLocation)
                    $candidates.Add((Join-Path $record.InstallLocation 'ChemDrawApplications_x64'))
                }
                if ($record.DisplayIcon) {
                    $icon = ($record.DisplayIcon -replace ',\s*-?\d+\s*$','').Trim('"')
                    if ($icon -match '(?i)ChemDraw\.exe$') { $candidates.Add((Split-Path -Parent $icon)) }
                }
            }
        }
    }
    $valid = @($candidates | Where-Object { Version-OK $_ $version } | ForEach-Object { [IO.Path]::GetFullPath($_).TrimEnd('\') } | Select-Object -Unique)
    if ($valid.Count -eq 1) { return $valid[0] }
    if ($valid.Count -gt 1) { Write-Host "检测到多个同版本安装：`n$($valid -join "`n")" }
    else { Write-Host "未自动找到 ChemDraw $version x64。" }
    $manual = (Read-Host '请粘贴含 ChemDraw.exe 的安装文件夹路径（留空退出）').Trim().Trim('"')
    if (-not $manual -or -not (Version-OK $manual $version)) { throw '安装路径不存在或版本不匹配。' }
    return [IO.Path]::GetFullPath($manual).TrimEnd('\')
}
function Check-Package($manifest,$roots) {
    $seen = @{}
    $jobs = @()
    $chem3dNames = @('Chem3D.exe','Chem3DCtl.ocx')
    $driverNames = @('AutoDockUI.dll','CambridgeSoft.ChemOffice.ConflexDriver.dll','CambridgeSoft.ChemOffice.GamessDriver.dll','CambridgeSoft.ChemOffice.GaussianDriver.dll','CambridgeSoft.ChemOffice.MopacDriver.dll','CambridgeSoft.ChemOffice.DriverShared.dll')
    $chem3dPresent = @($chem3dNames | Where-Object { Test-Path -LiteralPath (Within $roots.bin $_) -PathType Leaf })
    if ($chem3dPresent.Count -eq 1) { throw 'Chem3D 组件不完整，请先修复软件安装。' }
    if ($chem3dPresent.Count -eq 2 -and -not (Version-OK-Chem3D $roots.bin $manifest.version)) { throw 'Chem3D 版本与此补丁不匹配。' }
    if ($chem3dPresent.Count -eq 2 -and $Mode -ne 'Restore' -and $manifest.calculation_ansi_code_page) {
        if ($manifest.calculation_ansi_code_page -ne 936) { throw '未知的计算界面编码要求。' }
        if (-not ('ChemDrawZhRuntimeCodePage' -as [type])) {
            Add-Type -TypeDefinition 'using System.Runtime.InteropServices; public static class ChemDrawZhRuntimeCodePage { [DllImport("kernel32.dll")] public static extern uint GetACP(); }'
        }
        if ([ChemDrawZhRuntimeCodePage]::GetACP() -ne 936) { throw '本版 Chem3D 计算菜单需要 Windows ANSI 代码页 936；当前环境不兼容，未修改软件。还原英文不受此限制。' }
    }
    foreach ($entry in $manifest.files) {
        if (-not $roots.ContainsKey($entry.group)) { throw '未知文件组。' }
        $target = Within $roots[$entry.group] $entry.relative
        if ($seen.ContainsKey($target)) { throw "重复目标：$target" }; $seen[$target] = $true
        foreach ($route in $entry.routes) {
            $delta = Within $packageRoot $route.path
            if (-not $route.path.StartsWith('patches/')) { throw '差分文件目录错误。' }
            if ((Get-Item -LiteralPath $delta).Length -ne $route.size -or (Digest $delta) -ne $route.sha256) { throw "差分文件校验失败：$delta" }
        }
        if ($entry.optional_component) {
            if ($entry.group -ne 'bin') { throw '未知可选组件。' }
            if ($entry.optional_component -eq 'chem3d' -and $entry.relative -in $chem3dNames) {
                if (-not $chem3dPresent.Count) { continue }
            } elseif ($entry.optional_component -eq 'chem3d_driver' -and $entry.relative -in $driverNames) {
                if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { continue }
            } else { throw '未知可选组件。' }
        }
        if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "目标文件缺失：$target" }
        $current = Digest $target
        $allowed = @($entry.before,$entry.after) + @($entry.routes | ForEach-Object { $_.source })
        if ($current -notin $allowed) { throw "文件版本不匹配或已被其他补丁修改：$target" }
        $expected = if ($Mode -eq 'Restore') { $entry.before } else { $entry.after }
        $jobs += [pscustomobject]@{ Entry=$entry; Destination=$target; Current=$current; Expected=$expected }
    }
    return $jobs
}

function Version-OK-Chem3D([string]$folder,[string]$version) {
    foreach ($name in @('Chem3D.exe','Chem3DCtl.ocx')) {
        if ((Get-Item -LiteralPath (Join-Path $folder $name)).VersionInfo.FileVersion -ne $version) { return $false }
    }
    return $true
}

$transcribing = $false
$exitCode = 1
try {
    $m = Get-Content -LiteralPath (Join-Path $packageRoot 'manifest.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($m.format -ne 1 -or $m.architecture -ne 'x64') { throw '不支持的补丁清单格式。' }
    if (-not $BinPath) { $BinPath = Find-Bin $m.version }
    if (-not (Version-OK $BinPath $m.version)) { throw "仅支持 ChemDraw $($m.version) x64，请使用对应版本补丁。" }
    $BinPath = [IO.Path]::GetFullPath($BinPath).TrimEnd('\')
    $exe = Within $BinPath 'ChemDraw.exe'
    $pe = [IO.File]::ReadAllBytes($exe)
    $header = [BitConverter]::ToInt32($pe,0x3c)
    if ([BitConverter]::ToUInt16($pe,$header+4) -ne 0x8664) { throw '当前程序不是受支持的 x64 版本。' }
    $pe = $null
    if (-not $DataPath) {
        $DataPath = Join-Path $env:ProgramData 'RevvitySignalsSoftware\ChemDrawApplications\ChemDraw'
        if (-not (Test-Path -LiteralPath (Join-Path $DataPath 'GUI') -PathType Container)) {
            $DataPath = (Read-Host '请粘贴 ChemDraw 数据文件夹路径（其内应有 GUI 和 ChemDraw Items）').Trim().Trim('"')
        }
    }
    if (-not $DataPath -or -not (Test-Path -LiteralPath (Join-Path $DataPath 'GUI') -PathType Container)) { throw '未找到 ChemDraw 数据文件夹。' }
    $DataPath = [IO.Path]::GetFullPath($DataPath).TrimEnd('\')
    $roots = @{bin=$BinPath; data=$DataPath; gui=(Join-Path $DataPath 'GUI')}
    $checked = @(Check-Package $m $roots)
    $pending = @($checked | Where-Object { $_.Current -ne $_.Expected })
    if (-not $LogPath) {
        $logs = Join-Path $packageRoot 'logs'
        New-Item -ItemType Directory -Path $logs -Force | Out-Null
        $LogPath = Join-Path $logs ((Get-Date -Format 'yyyyMMdd-HHmmss')+'-'+[guid]::NewGuid().ToString('N').Substring(0,8)+'.txt')
    }
    if ($Mode -ne 'Validate' -and $pending.Count) {
        if (Get-Process -Name 'ChemDraw','ChemDraw64','ChemDrawCtl','CAWPROP','Chem3D' -ErrorAction SilentlyContinue) { throw '请保存文档并退出 ChemDraw、Chem3D 和化学性质窗口。' }
        $admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
        if (-not $admin -and -not $Elevated) {
            Write-Host '预检查通过，请在 Windows 管理员权限提示中选择“是”。'
            $childArgs = @('-NoProfile','-ExecutionPolicy','Bypass','-File',('"'+$PSCommandPath+'"'),'-Mode',$Mode,'-Elevated','-LogPath',('"'+$LogPath+'"'),'-BinPath',('"'+$BinPath+'"'),'-DataPath',('"'+$DataPath+'"'))
            $child = Start-Process -FilePath 'powershell.exe' -ArgumentList $childArgs -Verb RunAs -WindowStyle Hidden -Wait -PassThru
            if (Test-Path -LiteralPath $LogPath) { Get-Content -LiteralPath $LogPath -Encoding UTF8 | Write-Host }
            exit $child.ExitCode
        }
    }
    Start-Transcript -LiteralPath $LogPath -Force | Out-Null
    $transcribing = $true
    Write-Host "ChemDraw 中文扩展补丁 v$($m.patch) | $Mode | 文件：$($checked.Count)"
    Write-Host '本项目免费提供；原创代码采用 MIT 许可证。ChemDraw 本身须另行获得有效使用授权。'
    Write-Host "程序目录：$BinPath`n数据目录：$DataPath"
    Add-Type -TypeDefinition @'
using System;
using System.IO;
public static class ChemDrawDelta {
    static byte[] Read(BinaryReader reader, int size) {
        byte[] value = reader.ReadBytes(size);
        if (value.Length != size) throw new InvalidDataException("Truncated delta");
        return value;
    }
    public static byte[] Apply(byte[] source, string path, long targetSize) {
        if (targetSize < 0 || targetSize > 268435456) throw new InvalidDataException("Output limit");
        using (var input = File.OpenRead(path))
        using (var reader = new BinaryReader(input))
        using (var output = new MemoryStream()) {
            byte[] magic = {67,68,90,72,68,49,0};
            byte[] actual = Read(reader, magic.Length);
            for (int i=0; i<magic.Length; i++) if(actual[i]!=magic[i]) throw new InvalidDataException("Format");
            if (reader.ReadUInt64() != (ulong)targetSize) throw new InvalidDataException("Target size");
            while(true) {
                byte op = reader.ReadByte();
                if(op==0) break;
                if(op==1) {
                    ulong offset=reader.ReadUInt64(), count=reader.ReadUInt64();
                    if(offset>(ulong)source.LongLength || count>(ulong)source.LongLength-offset || count>(ulong)(targetSize-output.Length)) throw new InvalidDataException("COPY bounds");
                    output.Write(source,(int)offset,(int)count);
                } else if(op==2) {
                    uint count=reader.ReadUInt32();
                    if(count>(ulong)(targetSize-output.Length)) throw new InvalidDataException("LITERAL bounds");
                    byte[] data=Read(reader,(int)count); output.Write(data,0,data.Length);
                } else throw new InvalidDataException("Opcode");
            }
            if(output.Length!=targetSize || input.Position!=input.Length) throw new InvalidDataException("Final length");
            return output.ToArray();
        }
    }
}
'@
    $transaction = $null
    if ($Mode -ne 'Validate' -and $pending.Count) {
        $transaction = Join-Path $packageRoot ('backups\'+[guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $transaction -Force | Out-Null
    }
    # Reconstruct and hash every required output before writing any software file.
    $journal = @()
    foreach ($job in $pending) {
        $data = [IO.File]::ReadAllBytes($job.Destination)
        $state = $job.Current
        if ($state -notin @($job.Entry.before,$job.Entry.after)) {
            $route = @($job.Entry.routes | Where-Object { $_.source -eq $state -and $_.target -eq $job.Entry.before })
            if ($route.Count -ne 1) { throw '旧补丁还原路线缺失。' }
            $data = [ChemDrawDelta]::Apply($data,(Within $packageRoot $route[0].path),$job.Entry.before_size)
            $state = $job.Entry.before
        }
        if ($state -ne $job.Expected) {
            $route = @($job.Entry.routes | Where-Object { $_.source -eq $state -and $_.target -eq $job.Expected })
            if ($route.Count -ne 1) { throw '差分转换路线缺失。' }
            $size = if ($job.Expected -eq $job.Entry.before) { $job.Entry.before_size } else { $job.Entry.after_size }
            $data = [ChemDrawDelta]::Apply($data,(Within $packageRoot $route[0].path),$size)
        }
        $hash = [Security.Cryptography.SHA256]::Create()
        try { $generated = ([BitConverter]::ToString($hash.ComputeHash($data))).Replace('-','').ToLowerInvariant() } finally { $hash.Dispose() }
        if ($generated -ne $job.Expected) { throw "重建结果校验失败：$($job.Destination)" }
        if ($transaction) {
            $relative = $job.Entry.group+'/'+$job.Entry.relative
            $stage = Within (Join-Path $transaction 'stage') $relative
            $backup = Within (Join-Path $transaction 'before') $relative
            New-Item -ItemType Directory -Path (Split-Path -Parent $stage),(Split-Path -Parent $backup) -Force | Out-Null
            [IO.File]::WriteAllBytes($stage,$data)
            Copy-Item -LiteralPath $job.Destination -Destination $backup
            if ((Digest $backup) -ne $job.Current) { throw '操作前备份校验失败。' }
            $job | Add-Member -NotePropertyName Stage -NotePropertyValue $stage
            $job | Add-Member -NotePropertyName Backup -NotePropertyValue $backup
            $journal += @{target=$job.Destination; backup=$backup; before=$job.Current; after=$job.Expected}
        }
        $data = $null
    }
    if ($Mode -eq 'Validate') { Write-Host '版本、差分文件和重建结果校验通过，未修改软件。'; $exitCode=0 }
    elseif (-not $pending.Count) {
        Write-Host '已经是目标状态，无需重复处理。'
        if ($Mode -eq 'Restore') { Write-Host '当前已处于英文状态。' } else { Write-Host '请启动 ChemDraw / Chem3D；若 Chem3D 菜单仍为英文，可单独运行菜单缓存重置工具。' }
        $exitCode=0
    }
    else {
        $journal | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $transaction 'journal.json') -Encoding UTF8
        $touched = [Collections.Generic.List[object]]::new()
        try {
            foreach ($job in $pending) {
                if ((Digest $job.Destination) -ne $job.Current -or (Digest $job.Stage) -ne $job.Expected) { throw '写入前文件变化。' }
                $touched.Add($job)
                Copy-Item -LiteralPath $job.Stage -Destination $job.Destination -Force
                if ((Digest $job.Destination) -ne $job.Expected) { throw '写入后校验失败。' }
            }
            foreach ($job in $checked) { if ((Digest $job.Destination) -ne $job.Expected) { throw '最终校验失败。' } }
        } catch {
            $failure = $_; $errors = @()
            foreach ($job in $touched) {
                try {
                    if ((Digest $job.Destination) -eq $job.Current) { continue }
                    if ((Digest $job.Backup) -ne $job.Current) { throw '回滚备份损坏。' }
                    Copy-Item -LiteralPath $job.Backup -Destination $job.Destination -Force
                    if ((Digest $job.Destination) -ne $job.Current) { throw '回滚校验失败。' }
                } catch { $errors += "$($job.Destination)：$_" }
            }
            if ($errors.Count) { Write-Host ('回滚未完全成功：'+($errors -join "`n")) }
            else { Write-Host '本次写入已回滚到操作前状态。' }
            throw $failure
        }
        Write-Host "处理成功，全部文件校验通过。操作前备份：$transaction"
        if ($Mode -eq 'Restore') { Write-Host '已恢复英文。' } else { Write-Host '已安装汉化，请启动 ChemDraw 和 Chem3D。' }
        $exitCode=0
    }
} catch { Write-Host "操作失败：$_" -ForegroundColor Red }
finally { if ($transcribing) { Stop-Transcript | Out-Null } }
exit $exitCode
