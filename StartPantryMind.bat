@echo off
title PantryMind — Starting...
cd /d "E:\pantrymind-desktop - Copy"

echo.
echo   ╔═══════════════════════════════════════╗
echo   ║        PantryMind Desktop             ║
echo   ║   Starting backend + Electron app...  ║
echo   ╚═══════════════════════════════════════╝
echo.

:: ── 1. Start Python backend in a minimised window ──
echo [1/2] Starting backend server...
start "PantryMind Backend" /min cmd /k "cd /d "E:\pantrymind-desktop - Copy" && .\.venv\Scripts\python.exe main.py"

:: Give the backend a few seconds to bind the port
timeout /t 4 /nobreak >nul

:: ── 2. Start Electron + Vite frontend ──
echo [2/2] Starting desktop app...
start "PantryMind Frontend" cmd /k "cd /d "E:\pantrymind-desktop - Copy\frontend" && npm run electron:dev"

echo.
echo Both servers are booting up — this window will close in 3 seconds.
timeout /t 3 /nobreak >nul
exit
