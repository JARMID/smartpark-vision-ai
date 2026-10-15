@echo off
title Smart Park - Application Mobile (Executable Windows Natif)
color 0B
echo ===============================================================================
echo   Smart Park - Application Chauffeur et Patrouille Securite
echo   Executable Windows Natif Flutter 3.x (Impeller / DirectX 12)
echo ===============================================================================
echo.

set EXE_PATH=mobile\build\windows\x64\runner\Release\smartpark_mobile.exe

if exist "%EXE_PATH%" (
    echo [*] Lancement de l'application native Smart Park...
    start "" "%EXE_PATH%"
) else (
    echo [*] Executable natif non trouve. Lancement de la compilation Flutter Windows...
    cd mobile
    call flutter run -d windows
    cd ..
)
