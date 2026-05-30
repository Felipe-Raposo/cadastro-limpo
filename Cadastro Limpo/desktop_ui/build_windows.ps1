Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ToolsDir = Resolve-Path (Join-Path $ScriptDir "..")
$IconPath = Join-Path $ScriptDir "icon.ico"

if (-not (Test-Path -LiteralPath $IconPath -PathType Leaf)) {
    throw "Icon not found: $IconPath"
}

Set-Location $ToolsDir
python -m pip install --upgrade pip
python -m pip install pyinstaller
python -m pip install -e ".[gui]"

pyinstaller `
  --noconfirm `
  --windowed `
  --name cadastro-limpo `
  --icon "$IconPath" `
  --add-data "$IconPath;desktop_ui" `
  --add-data "$ToolsDir\patterns.json;." `
  --collect-data sanitiser `
  --paths "$ToolsDir" `
  desktop_ui/main.py

$exePath = Join-Path $ToolsDir "dist\cadastro-limpo\cadastro-limpo.exe"
if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
    throw "Build failed; executable not found: $exePath"
}
Write-Host "Build OK: $exePath"
