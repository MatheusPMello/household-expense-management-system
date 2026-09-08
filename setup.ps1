# HomeLedger - Fast Setup Script for Windows PowerShell
$ErrorActionPreference = "Stop"

Write-Host "`n=== [HomeLedger] Fast Configuration & Setup ===" -ForegroundColor Green

# 1. Check Prerequisites
Write-Host "`n[1/5] Checking environment prerequisites..." -ForegroundColor Cyan
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Error "Python is not installed or not in your PATH. Please install Python 3.10+."
    exit 1
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Error "Node.js / npm is not installed. Please install Node.js 18+."
    exit 1
}

# 2. Setup Python Virtual Environment
Write-Host "`n[2/5] Initializing Python virtual environment in backend/venv..." -ForegroundColor Cyan
if (-not (Test-Path "backend\venv")) {
    python -m venv backend\venv
}

# 3. Install Backend Dependencies
Write-Host "`n[3/5] Installing backend dependencies via pip..." -ForegroundColor Cyan
& ".\backend\venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
& ".\backend\venv\Scripts\pip.exe" install -r backend\requirements.txt --quiet

# 4. Apply Database Migrations
Write-Host "`n[4/5] Applying database migrations with Alembic..." -ForegroundColor Cyan
Push-Location backend
& ".\venv\Scripts\alembic.exe" upgrade head
Pop-Location

# 5. Install Frontend Dependencies
Write-Host "`n[5/5] Installing frontend dependencies via npm..." -ForegroundColor Cyan
Push-Location frontend
npm install --silent
Pop-Location

Write-Host "`n=== [HomeLedger] Setup Completed Successfully! ===" -ForegroundColor Green
Write-Host "To launch the development stack, run: .\start-dev.ps1`n" -ForegroundColor Yellow
