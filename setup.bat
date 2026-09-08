@echo off
REM HomeLedger - Fast Setup Batch File for Windows
echo.
echo ===================================================
echo     [HomeLedger] Fast Configuration and Setup
echo ===================================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"

pause
