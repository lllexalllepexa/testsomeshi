$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONPATH = $Root

$VenvStreamlit = Join-Path $Root ".venv\Scripts\streamlit.exe"

if (Test-Path $VenvStreamlit) {
    & $VenvStreamlit run dashboard/app.py
} else {
    python -m streamlit run dashboard/app.py
}
