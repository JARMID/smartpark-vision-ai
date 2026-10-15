@echo off
title Smart Park - Poste Operateur et Caisse (Desktop Station)
color 0B
echo ===============================================================================
echo   Smart Park - Poste Operateur et Caisse Dedie (Bureau Windows)
echo   Branding Cyber Obsidian & Mint - ESC/POS - Modbus - ALPR 4-Canaux
echo ===============================================================================
echo.
where python >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [!] ERREUR: Python 3 introuvable dans le PATH.
    pause
    exit /b 1
)
python desktop/app.py --server http://127.0.0.1:8080
pause
