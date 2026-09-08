@echo off
REM HomeLedger - Fast Start Batch File for Windows
echo.
echo ===================================================
echo     [HomeLedger] Starting Development Servers
echo ===================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-dev.ps1"
