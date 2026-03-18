@echo off
REM CHARLIEC - Generator Capacity Envelope (8 runs, 720s timeout each).
REM Set SPEC_ID and WORKSPACE_ID to an active spec and its workspace (edit below or set in system env).
REM Do not change code or config during the run.

set REPO_ROOT=%~dp0
cd /d "%REPO_ROOT%"

if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) else if exist "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
)

if "%SPEC_ID%"=="" set SPEC_ID=PASTE_SPEC_ID_HERE
if "%WORKSPACE_ID%"=="" set WORKSPACE_ID=PASTE_WORKSPACE_ID_HERE

if "%SPEC_ID%"=="PASTE_SPEC_ID_HERE" (
    echo Set SPEC_ID and WORKSPACE_ID: edit this file or set env vars, then run again.
    pause
    exit /b 1
)

echo Running 8-run capacity envelope (max 720s per run)...
python development\run_capacity_envelope_tests.py
echo.
echo Output: Live Results\Generator Capacity Envelope.txt
pause
