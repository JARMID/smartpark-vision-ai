@echo off
title SmartPark Vision AI - Mode Autonome Navigateur
echo ===============================================================================
echo   SmartPark Vision AI - Lancement Mode Autonome Navigateur
echo   Ce mode execute toute la simulation interactive directement dans le navigateur
echo   sans necessiter d'installation Python ou de serveur de base de donnees.
echo ===============================================================================
echo.
echo [*] Ouverture de l'interface de commande...
start "" "%~dp0static\index.html"
echo [OK] Interface ouverte avec succes.
timeout /t 3 >nul
