@echo off
setlocal
cd /d "%~dp0"
title OBS Gesture Control V2.0
chcp 65001 > NUL

echo ===================================================
echo     OBS GESTURE CONTROL V2.0 - INICIALIZADOR
echo ===================================================
echo.

if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Ambiente virtual nao encontrado. Criando ambiente...
    python -m venv .venv
    echo [INFO] Instalando dependencias...
    call .venv\Scripts\pip.exe install -r requirements.txt
)

echo.
echo ===================================================
echo [INFO] Iniciando OBS Gesture Control V2...
echo ===================================================
echo.

".venv\Scripts\python.exe" main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERRO] O aplicativo encerrou com codigo de erro %ERRORLEVEL%.
    pause
)
