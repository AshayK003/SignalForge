@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
title Hermes Agent Gateway
echo.
echo  ===================================
echo   Hermes Agent Gateway - SignalForge
echo  ===================================
echo.

REM Find hermes.exe
set "HERMES=%LOCALAPPDATA%\hermes\hermes-agent\.venv\Scripts\hermes.exe"
if not exist "%HERMES%" (
    echo ERROR: hermes.exe not found at %HERMES%
    echo Install Hermes Agent first.
    pause
    exit /b 1
)

echo Starting Hermes Gateway...
"%HERMES%" gateway run
