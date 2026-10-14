param([Parameter(Mandatory=$true)][string]$BinPath, [string[]]$Files=@('ChemDrawManaged.dll','ChemDrawManaged.CDAX.dll','Revvity.ChemDraw.ChemDrawDotNET.dll'), [string]$OutputPath=(Join-Path $PSScriptRoot 'managed_string_uses.json'))
# SPDX-License-Identifier: MIT
$ErrorActionPreference='Stop'
$root=$BinPath

$codes=@{}
[Reflection.Emit.OpCodes].GetFields([Reflection.BindingFlags]'Public,Static') | ForEach-Object { $v=$_.GetValue($null); $codes[([int]$v.Value -band 65535).ToString()]=$v }
$result=@(); foreach($file in $Files) { $asm=[Reflection.Assembly]::LoadFrom((Join-Path $root $file))
foreach($type in $asm.GetTypes()) {
 foreach($m in @(@($type.GetMethods([Reflection.BindingFlags]'Public,NonPublic,Instance,Static,DeclaredOnly')) + @($type.GetConstructors([Reflection.BindingFlags]'Public,NonPublic,Instance,Static,DeclaredOnly')))) {
  $body=$m.GetMethodBody(); if(-not $body){continue}; $b=$body.GetILAsByteArray();$ops=@();$i=0
  while($i -lt $b.Length){
   $start=$i;$c=[int]$b[$i];$i++;if($c -eq 254){$c=65024+[int]$b[$i];$i++};$op=$codes[$c.ToString()];if(-not $op){throw "opcode $c"}
   $size=switch([string]$op.OperandType){ InlineNone {0} ShortInlineBrTarget {1} ShortInlineI {1} ShortInlineVar {1} InlineVar {2} InlineI8 {8} InlineR {8} InlineSwitch {4+4*[BitConverter]::ToInt32($b,$i)} default {4} }
   $arg='';if($size -eq 4){$token=[BitConverter]::ToInt32($b,$i);try {if($op.Name -eq 'ldstr'){$arg=$m.Module.ResolveString($token)} elseif($op.Name -match 'call|newobj'){$arg=[string]$m.Module.ResolveMethod($token)}}catch{}}
   $ops+= [pscustomobject]@{Offset=$start;Op=$op.Name;Arg=$arg};$i+=$size
  }
  for($j=0;$j -lt $ops.Count;$j++) {
   if($ops[$j].Op -eq 'ldstr') {
    $end=[Math]::Min($j+3,$ops.Count-1)
    $next=if($j+1 -lt $ops.Count){$ops[$j+1].Arg}else{''}
    $result+=[pscustomobject]@{File=$file;Type=$type.FullName;Method=$m.Name;Text=$ops[$j].Arg;Offset=$ops[$j].Offset;IL=[Convert]::ToBase64String($b);Next=$next;Context=($ops[$j..$end] | ForEach-Object {$_.Op+' '+$_.Arg}) -join ' | '}
   }
  }
 }
}
}
$result | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $OutputPath
Write-Output ("String references: " + $result.Count)