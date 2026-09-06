# PHANTOM dev starter (Windows PowerShell)
# Usage: powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

# Backend
Start-Process -NoNewWindow pwsh -ArgumentList "-Command", "cd '$root\backend'; .\.venv\Scripts\Activate.ps1; uvicorn main:app --host 127.0.0.1 --port 8899 --reload"

# Frontend
Start-Process -NoNewWindow pwsh -ArgumentList "-Command", "cd '$root\frontend'; npm run dev"

Start-Process "http://localhost:5173"
Write-Host "PHANTOM dev: backend :8899, frontend :5173" -ForegroundColor Magenta
