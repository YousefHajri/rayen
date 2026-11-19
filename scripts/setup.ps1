# RAYEN v0.2 setup — Windows PowerShell.  Usage:  powershell -ExecutionPolicy Bypass -File scripts\setup.ps1 [-WithBlender]
param([switch]$WithBlender)
Set-Location (Join-Path $PSScriptRoot "..")
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
& $py -m pip install --upgrade pip
& $py -m pip install -r requirements.txt
if ($WithBlender) {
  $v = & $py -c "import sys;print(f'{sys.version_info[0]}.{sys.version_info[1]}')"
  if ($v -eq "3.13") { & $py -m pip install bpy }
  else { Write-Host "bpy needs Python 3.13. Or install Blender (winget install BlenderFoundation.Blender) and run: blender -b -P skills\rayen-render\scripts\render.py -- scene.json -o out" }
}
& $py scripts\selftest.py
