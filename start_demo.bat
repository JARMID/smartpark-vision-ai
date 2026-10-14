@echo off
setlocal enabledelayedexpansion

title SmartPark Vision AI - Sovereign Control Center Launcher
color 0A

echo ===============================================================================
echo   SmartPark Vision AI - Centre de Controle Souverain (Algerie)
echo   Conforme Loi 18-07 et Loi 25-11 (ANPDP) - Zero Transfert Etranger
echo ===============================================================================
echo.

:: Check Python installation
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] ERREUR: Python 3 n'est pas installe ou n'est pas dans le PATH.
    echo [i] Vous pouvez executer la demo directement dans votre navigateur :
    echo     Double-cliquez sur "start_browser_only.bat" ou ouvrez "static\index.html".
    echo.
    pause
    exit /b 1
)

echo [*] Verification de l'environnement Python...
python -c "import fastapi, uvicorn, numpy" >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [*] Installation des dependances requises (FastAPI, Uvicorn, NumPy)...
    python -m pip install -r requirements.txt
    if %ERRORLEVEL% neq 0 (
        echo [!] Avertissement : Impossible d'installer via pip. Lancement direct...
    )
)

echo [*] Demarrage du serveur souverain FastAPI...
echo [*] Ouverture de l'interface dans votre navigateur : http://127.0.0.1:8080
echo.

:: Launch default browser after 1 second in background
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8080"

:: Run the demo server in the current window
python run_demo.py

pause
