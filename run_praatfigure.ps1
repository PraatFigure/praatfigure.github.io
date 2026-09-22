$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$launcher = Join-Path $projectRoot ".venv\Scripts\praatfigure.exe"

if (-not (Test-Path -LiteralPath $launcher)) {
    throw "PraatFigure environment is missing. Run: python -m venv .venv; .\.venv\Scripts\python.exe -m pip install -e `".[all]`""
}

& $launcher @args
exit $LASTEXITCODE
