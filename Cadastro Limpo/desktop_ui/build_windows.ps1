Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ToolsDir = Resolve-Path (Join-Path $ScriptDir "..")
$RootDir = Resolve-Path (Join-Path $ToolsDir "..")
$IconPath = Join-Path $ScriptDir "icon.ico"
$IconPngPath = Join-Path $ScriptDir "icon.png"
$VenvPython = Join-Path $RootDir ".venv\Scripts\python.exe"
$VenvPyInstaller = Join-Path $RootDir ".venv\Scripts\pyinstaller.exe"
if (Test-Path -LiteralPath $VenvPython -PathType Leaf) {
    $PythonExe = $VenvPython
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonExe = "python"
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonExe = "py"
} else {
    throw "Python not found. Activate a virtual environment or install Python."
}

if (-not (Test-Path -LiteralPath $IconPath -PathType Leaf)) {
    throw "Icon not found: $IconPath"
}

if (-not (Test-Path -LiteralPath $IconPngPath -PathType Leaf)) {
    throw "Icon PNG not found: $IconPngPath"
}

Set-Location $ToolsDir
& $PythonExe -m pip install --upgrade pip
& $PythonExe -m pip install pyinstaller
& $PythonExe -m pip install -e ".[gui]"

if (Test-Path -LiteralPath $VenvPyInstaller -PathType Leaf) {
    & $VenvPyInstaller `
      --noconfirm `
      --windowed `
      --name cadastro-limpo `
      --icon "$IconPath" `
      --add-data "$IconPath;desktop_ui" `
      --add-data "$IconPngPath;desktop_ui" `
      --add-data "$ToolsDir\patterns.json;." `
      --collect-data sanitiser `
      --paths "$ToolsDir" `
      desktop_ui/main.py
} else {
    & $PythonExe -m PyInstaller `
      --noconfirm `
      --windowed `
      --name cadastro-limpo `
      --icon "$IconPath" `
      --add-data "$IconPath;desktop_ui" `
      --add-data "$IconPngPath;desktop_ui" `
      --add-data "$ToolsDir\patterns.json;." `
      --collect-data sanitiser `
      --paths "$ToolsDir" `
      desktop_ui/main.py
}

$exePath = Join-Path $ToolsDir "dist\cadastro-limpo\cadastro-limpo.exe"
if (-not (Test-Path -LiteralPath $exePath -PathType Leaf)) {
    throw "Build failed; executable not found: $exePath"
}
Write-Host "Build OK: $exePath"
