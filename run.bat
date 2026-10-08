@echo off
cd /d "%~dp0"
title OBS Gesture Control V2.0
chcp 65001 > NUL
echo ===================================================
echo     OBS GESTURE CONTROL V2.0 - INICIALIZADOR
echo ===================================================
echo.

IF NOT EXIST ".venv" (
    echo [INFO] Criando ambiente virtual Python (.venv)...
    python -m venv .venv
)

echo [INFO] Ativando ambiente virtual...
call .venv\Scripts\activate.bat

echo [INFO] Instalando/Verificando dependencias...
pip install -r requirements.txt --quiet

echo.
echo ===================================================
echo [INFO] Iniciando OBS Gesture Control V2...
echo ===================================================
python main.py

pause
