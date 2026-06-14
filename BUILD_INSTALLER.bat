@echo off
chcp 65001 >nul
echo ============================================
echo  DesktopPet - Build Installer
echo ============================================
echo.

cd /d "%~dp0"

REM --- Step 1: PyInstaller ---
echo [1/3] Building with PyInstaller...
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
    echo [SKIP] Build exists, using dist\DesktopPet\
)

echo [1/3] Done.
echo.

REM --- Step 2: Reset license for first-time users ---
echo [2/3] Resetting license prompt for first-time users...

set "MAIN_JSON=dist\DesktopPet\_internal\data\config\main.json"
if not exist "%MAIN_JSON%" set "MAIN_JSON=dist\DesktopPet\data\config\main.json"
if exist "%MAIN_JSON%" (
    powershell -Command "(Get-Content '%MAIN_JSON%') -replace '\"license_accepted\":\s*true', '\"license_accepted\": false' | Set-Content '%MAIN_JSON%' -Encoding ASCII"
    echo [INFO] License reset to false
)

echo [2/3] Done.
echo.

REM --- Step 3: Inno Setup Installer ---
echo [3/3] Compiling Inno Setup installer...

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

echo [3/3] Done.
echo.
echo ============================================
echo  SUCCESS!
echo ============================================
echo.
echo  Output: dist\DesktopPet_Setup_1.2.0.exe
echo.
pause
