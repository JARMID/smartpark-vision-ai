@echo off
title Smart Park - Console de Lancement Officielle
color 0F
:MENU
cls
echo ===============================================================================
echo                         S M A R T   P A R K
echo         Plateforme Souveraine de Gestion Intelligente de Stationnement
echo ===============================================================================
echo.
echo   [1] Lancer l'Ecosysteme Complet (Serveur + Web + Poste Operateur)
echo   [2] Lancer le Poste Operateur Bureau (Caisse, Tickets ESC/POS, Modbus)
echo   [3] Lancer l'Application Mobile/Chauffeur (Application Windows Native)
echo   [4] Lancer le Daemon Cameras Edge (Acquisition RTSP, ALPR, Biometrie)
echo   [5] Ouvrir le Centre de Controle Web (Navigateur)
echo   [6] Executer le Diagnostic Complet des Sous-Systemes (97 Tests Unitaires)
echo   [7] Quitter
echo.
echo ===============================================================================
set /p CHOICE="  Selectionnez une option [1-7] : "

if "%CHOICE%"=="1" goto FULL
if "%CHOICE%"=="2" goto DESKTOP
if "%CHOICE%"=="3" goto MOBILE
if "%CHOICE%"=="4" goto CAMERA
if "%CHOICE%"=="5" goto WEB
if "%CHOICE%"=="6" goto DIAGNOSTIC
if "%CHOICE%"=="7" goto QUIT
goto MENU

:FULL
call start_full_ecosystem.bat
goto MENU

:DESKTOP
call start_desktop.bat
goto MENU

:MOBILE
call start_mobile_windows.bat
goto MENU

:CAMERA
call start_camera_edge.bat
goto MENU

:WEB
start http://127.0.0.1:8080
goto MENU

:DIAGNOSTIC
cls
echo ===============================================================================
echo   Execution du diagnostic de l'ensemble des sous-systemes...
echo ===============================================================================
echo.
python -m unittest discover tests
echo.
echo [Poste Bureau] Test autonome headless:
python desktop/app.py --headless
echo.
pause
goto MENU

:QUIT
exit /b 0
