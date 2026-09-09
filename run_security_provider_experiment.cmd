@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 tools\security_provider_experiment.py
  if errorlevel 1 pause
  exit /b
)
where python >nul 2>nul
if %errorlevel%==0 (
  python tools\security_provider_experiment.py
  if errorlevel 1 pause
  exit /b
)
echo Python 3 not found. Install Python 3 and try again.
pause
