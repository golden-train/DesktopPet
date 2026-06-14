@echo off
chcp 65001 >nul
echo ============================================
echo  DesktopPet - Build Installer
echo ============================================
echo.

cd /d "%~dp0"

REM --- Step 1: PyInstaller ---
echo [1/2] Building with PyInstaller...
echo.

if not exist "dist\DesktopPet\DesktopPet.exe" (
    pyinstaller --noconfirm ^
        --onedir ^
        --windowed ^
        --name "DesktopPet" ^
        --icon "data\assets\images\firefly\icon\icon.ico" ^
        --add-data "data;data" ^
        --hidden-import PySide6.QtMultimedia ^
        --hidden-import PySide6.QtNetwork ^
        --hidden-import qfluentwidgets ^
        --hidden-import openai ^
        --hidden-import psutil ^
        --collect-all qfluentwidgets ^
        src\main.py

    if %errorlevel% neq 0 (
        echo [ERROR] PyInstaller build failed!
        pause
        exit /b 1
    )

    copy ".env.example" "dist\DesktopPet\.env.example" >nul
) else (
    echo [SKIP] Build already exists, using dist\DesktopPet\
)

REM 确保打包版首次启动显示许可协议
set "MAIN_JSON=dist\DesktopPet\_internal\data\config\main.json"
if not exist "%MAIN_JSON%" set "MAIN_JSON=dist\DesktopPet\data\config\main.json"
if exist "%MAIN_JSON%" (
    powershell -Command "(Get-Content '%MAIN_JSON%') -replace '\"license_accepted\":\s*true', '\"license_accepted\": false' | Set-Content '%MAIN_JSON%' -Encoding UTF8"
    echo [INFO] License reset to false for first-time users
)

echo [1/2] Done.
echo.

REM --- Step 2: Inno Setup Installer ---
echo [2/2] Compiling Inno Setup installer...

set ISCC=
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    set ISCC="%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set ISCC="C:\Program Files\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files (x86)\Inno Setup 5\ISCC.exe" (
    set ISCC="C:\Program Files (x86)\Inno Setup 5\ISCC.exe"
) else (
    echo.
    echo [ERROR] Inno Setup not found!
    echo Download: https://jrsoftware.org/isdl.php
    echo.
    pause
    exit /b 1
)

%ISCC% "DesktopPet.iss" /Qp

if %errorlevel% neq 0 (
    echo [ERROR] Installer compilation failed!
    pause
    exit /b 1
)

echo [2/2] Done.
echo.
echo ============================================
echo  SUCCESS!
echo ============================================
echo.
echo  Installer: dist\DesktopPet_Setup_1.0.0.exe

for %%I in ("dist\DesktopPet_Setup_1.0.0.exe") do (
    set SIZE=%%~zI
)
setlocal enabledelayedexpansion
echo  Size: !SIZE! bytes
endlocal

echo.
echo  Original directory: dist\DesktopPet\
echo.
pause
