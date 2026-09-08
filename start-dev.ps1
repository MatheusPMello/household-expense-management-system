# HomeLedger - Fast Start Development Servers for Windows PowerShell
$ErrorActionPreference = "Stop"

if (-not (Test-Path "backend\venv") -or -not (Test-Path "frontend\node_modules")) {
    Write-Host "[HomeLedger] Dependencies not detected. Running initial setup..." -ForegroundColor Yellow
    & ".\setup.ps1"
}

Write-Host "`n=== [HomeLedger] Starting Development Servers ===" -ForegroundColor Green
Write-Host "Backend API:    http://localhost:8000" -ForegroundColor Cyan
Write-Host "API Swagger:    http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Frontend App:   http://localhost:5173" -ForegroundColor Cyan
Write-Host "`nPress Ctrl+C to stop both servers.`n" -ForegroundColor Yellow

$backendJob = Start-Process -FilePath ".\backend\venv\Scripts\uvicorn.exe" `
    -ArgumentList "app.main:app --reload --host 127.0.0.1 --port 8000" `
    -WorkingDirectory "$PSScriptRoot\backend" `
    -PassThru

Start-Sleep -Seconds 1

$frontendJob = Start-Process -FilePath "npm.cmd" `
    -ArgumentList "run dev" `
    -WorkingDirectory "$PSScriptRoot\frontend" `
    -PassThru

try {
    while ($true) {
        if ($backendJob.HasExited -or $frontendJob.HasExited) {
            break
        }
        Start-Sleep -Milliseconds 500
    }
}
finally {
    Write-Host "`n[HomeLedger] Shutting down servers..." -ForegroundColor Yellow
    if ($backendJob -and -not $backendJob.HasExited) {
        Stop-Process -Id $backendJob.Id -Force -ErrorAction SilentlyContinue
    }
    if ($frontendJob -and -not $frontendJob.HasExited) {
        Stop-Process -Id $frontendJob.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "[HomeLedger] Servers stopped." -ForegroundColor Green
}
