@echo off
setlocal
cd /d "E:\pantrymind-desktop\frontend"

where npm >nul 2>nul
if errorlevel 1 (
  echo npm was not found on PATH. Install Node.js or open this from a Node-enabled terminal.
  pause
  exit /b 1
)

echo Starting PantryMind Desktop...
echo This one command starts Vite, Electron, and the Python backend.
npm run electron:dev
pause
