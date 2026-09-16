$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$env:PYTHONPATH = $Root

$VenvActivate = Join-Path $Root ".venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    & $VenvActivate
}

python -m superstore.etl.load_and_clean
python -m superstore.etl.data_quality_runner
python -m superstore.analysis.eda
python -m superstore.analysis.stats_models
