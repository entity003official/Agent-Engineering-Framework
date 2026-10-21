@echo off
setlocal
cd /d "%~dp0"
where pythonw >nul 2>nul
if not errorlevel 1 (
  start "" pythonw "%~dp0AEF-Desktop.pyw"
  exit /b 0
)
python "%~dp0aef_gui.py"
if errorlevel 1 pause
