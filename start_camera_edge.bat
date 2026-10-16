@echo off
title Smart Park - Daemon Video et Capteurs Optiques Edge
color 0B
cls
echo ===============================================================================
echo               S M A R T   P A R K   -   C A M E R A   E D G E
echo        Daemon Autonome d'Acquisition RTSP, ALPR et Biometrie Locale
echo ===============================================================================
echo.
echo [*] Chargement de la configuration : config/cameras.yaml
echo [*] Initialisation des flux RTSP multi-canaux (CAM-01 a CAM-04)...
echo [*] Verification du controleur Modbus PLC (Port 502)...
echo [*] Demarrage du serveur de telemetrie Edge sur http://127.0.0.1:8082...
echo.
python -m src.camera.edge_daemon --config config/cameras.yaml --host 127.0.0.1 --port 8082
pause
