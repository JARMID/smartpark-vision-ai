@echo off
title Smart Park - Demarrage Ecosysteme Complet
color 0A
echo ===============================================================================
echo   Smart Park - Lancement de l'Ecosysteme Complet
echo   FastAPI + Jumeau 3D WebGL + Poste Operateur Bureau
echo ===============================================================================
echo.
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] ERREUR: Python 3 introuvable dans le PATH.
    pause
    exit /b 1
)

:: Start Backend Server in Background
start "Smart Park - Serveur Souverain FastAPI" cmd /c "python run_demo.py"

:: Wait 2 seconds for server socket binding
timeout /t 2 /nobreak >nul

:: Launch Desktop Operator Workstation
start "Smart Park - Poste Operateur" cmd /c "python desktop/app.py --server http://127.0.0.1:8080"

:: Open Browser Viewport
start http://127.0.0.1:8080
