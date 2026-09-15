@echo off
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 -m tools.security_provider_launcher
  if errorlevel 1 pause
  exit /b
)
where python >nul 2>nul
if %errorlevel%==0 (
  python -m tools.security_provider_launcher
  if errorlevel 1 pause
  exit /b
)
echo Python 3 not found. Install Python 3 and try again.
pause
