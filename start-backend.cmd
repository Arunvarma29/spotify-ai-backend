@echo off
rem Starts the API and its in-process worker in one window.
rem Stores are configured in .env and may be hosted.
rem
rem   start-backend.cmd
rem
rem Start local containers separately with "docker compose up -d", or use
rem hosted stores configured in .env.

cd /d "%~dp0"

if exist "%~dp0.venv\Scripts\python.exe" (
  set "PYTHON=%~dp0.venv\Scripts\python.exe"
) else (
  set "PYTHON=python"
)

echo Using the stores configured in .env (no Docker containers are started)...

rem Remove old standalone workers for this project before using the in-process worker.
echo Stopping any standalone worker left from a previous run...
powershell -NoProfile -Command "$root=[regex]::Escape('%CD%'); Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Where-Object { $_.CommandLine -match $root -and $_.CommandLine -match 'run_processor\.py' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"

set "RUN_WORKER_IN_API=true"

echo Starting the API on http://127.0.0.1:8000 ...
"%PYTHON%" -m uvicorn memory.api:app --port 8000
