# Starts the FastAPI backend (creates a venv + installs deps on first run).
$ErrorActionPreference = "Stop"
Set-Location -Path (Join-Path $PSScriptRoot "backend")

if (-not (Test-Path ".venv")) {
    Write-Host "Creating virtual environment..." -ForegroundColor Cyan
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
}
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created backend/.env from example — set a strong SECRET_KEY." -ForegroundColor Yellow
}

.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
