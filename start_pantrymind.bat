@echo off
title PantryMind Launcher
cd /d "D:\pantrymind-desktop"

echo Starting PantryMind Backend...
start "PantryMind Backend" cmd /k ".\.venv\Scripts\python.exe main.py"

echo Starting PantryMind Desktop App...
start "PantryMind Frontend" cmd /k "cd frontend && npm run electron:dev"

echo PantryMind servers are booting up in separate windows!
