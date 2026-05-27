# run_api.ps1 — Launch the Reversal Intelligence Engine API
# Run this from the workspace root: .\run_api.ps1
Set-Location "$PSScriptRoot\reversal_intelligence_engine"
uvicorn infrastructure.api.main:app --reload --host 127.0.0.1 --port 8000

