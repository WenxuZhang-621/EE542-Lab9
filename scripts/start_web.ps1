param([switch]$Install, [switch]$SqlitePreview)
$ErrorActionPreference = 'Stop'
$labRoot = Split-Path $PSScriptRoot -Parent
Set-Location -LiteralPath $labRoot
$labPython = Join-Path $labRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $labPython)) {
    $labBundledPython = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3.12 -m venv .venv
    } elseif (Test-Path -LiteralPath $labBundledPython) {
        & $labBundledPython -m venv .venv
    } else {
        & python -m venv .venv
    }
    if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12+ and retry.' }
    $Install = $true
}
if ($Install) {
    & $labPython -m pip install -r requirements-a.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
if ($SqlitePreview) { & $labPython -X utf8 -m scripts.setup_a --sqlite-preview }
else { & $labPython -X utf8 -m scripts.setup_a }
if ($LASTEXITCODE -ne 0) { throw 'Configuration setup failed.' }
Write-Host 'Start MySQL and Llama separately. Add your OpenAI key to .env locally.'
Write-Host 'Open http://127.0.0.1:8000. Press Ctrl+C to stop the web server.'
& $labPython -X utf8 -m webapp.backend.run
