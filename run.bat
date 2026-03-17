@echo off
cd /d "%~dp0"
title Heartopia Bot

echo [*] Checking Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

echo [*] Installing / updating dependencies...
pip install -r requirements.txt -q

echo [*] Starting Heartopia Bot...
python main.py %*

pause
