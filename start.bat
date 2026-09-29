@echo off
:: ==========================================================
:: AirChat Quick Start Script (Windows)
:: ==========================================================
chcp 65001 >nul
title AirChat Secure Server

set PORT=8000
set HOST=0.0.0.0

echo 🚀 Buscando intérprete de Python...

where python >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set PYTHON_BIN=python
    goto :check_port
)

where py >nul 2>nul
if %ERRORLEVEL% equ 0 (
    set PYTHON_BIN=py
    goto :check_port
)

echo ❌ Error: No se encontró Python en el PATH del sistema.
pause
exit /b 1

:check_port
:: Detectar y liberar el puerto si ya está en uso (evitar Address already in use)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :%PORT% ^| findstr LISTENING 2^>nul') do (
    echo ⚠️  El puerto %PORT% está ocupado por el proceso PID: %%a
    echo 🧹 Liberando puerto %PORT%...
    taskkill /F /PID %%a >nul 2>nul
)

:start
echo 🚀 Iniciando AirChat con %PYTHON_BIN%...
echo 📍 Dirección local: http://localhost:%PORT%
echo ⚙️  Presiona Ctrl+C para detener el servidor.
echo ----------------------------------------------------------

%PYTHON_BIN% -m uvicorn main:app --host %HOST% --port %PORT% --reload
pause
