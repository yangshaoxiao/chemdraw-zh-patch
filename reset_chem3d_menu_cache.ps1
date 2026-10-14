# SPDX-License-Identifier: MIT
$ErrorActionPreference = 'Stop'
try {
    if (Get-Process -Name 'Chem3D' -ErrorAction SilentlyContinue) { throw '请保存文档并关闭 Chem3D 后重试。' }
    Write-Host '此操作会重置 Chem3D 的菜单和工具栏自定义布局，先导出备份。'
    $paths = @('HKCU\Software\RevvitySignalsSoftware_x64\Chem3D\Chem3D\BCG',
               'HKCU\Software\RevvitySignalsSoftware\Chem3D\Chem3D\BCG')
    $backup = Join-Path $PSScriptRoot ('backups\chem3d-menu-' + [guid]::NewGuid().ToString('N'))
    $exports = @()
    # Export every existing key successfully before deleting any key.
    foreach ($path in $paths) {
        $providerPath = $path.Replace('HKCU\','HKCU:\')
        if (-not (Test-Path -LiteralPath $providerPath)) { continue }
        New-Item -ItemType Directory -Path $backup -Force | Out-Null
        $file = Join-Path $backup (([string]$exports.Count) + '.reg')
        & "$env:SystemRoot\System32\reg.exe" export $path $file /y | Out-Null
        if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $file -PathType Leaf) -or (Get-Item -LiteralPath $file).Length -eq 0) { throw '菜单缓存备份失败，未执行重置。' }
        $exports += @{Path=$providerPath; Backup=$file}
    }
    $touched = @()
    try {
        foreach ($entry in $exports) {
            if ($entry.Path -notin @($paths | ForEach-Object { $_.Replace('HKCU\','HKCU:\') })) { throw '注册表目标越界。' }
            $touched += $entry
            Remove-Item -LiteralPath $entry.Path -Recurse -Force
        }
    } catch {
        $failure = $_
        foreach ($entry in $touched) {
            & "$env:SystemRoot\System32\reg.exe" import $entry.Backup | Out-Null
            if ($LASTEXITCODE -ne 0) { Write-Host "缓存恢复失败，请保留并手动导入备份：$($entry.Backup)" }
        }
        throw $failure
    }
    if ($exports.Count) { Write-Host "菜单缓存已重置。备份：$backup；需要恢复时可导入该目录内的 .reg 文件。" }
    else { Write-Host '未发现菜单缓存，无需重置。' }
    exit 0
} catch { Write-Host "重置失败：$_" -ForegroundColor Red; exit 1 }
