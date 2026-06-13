@echo off
chcp 65001 >nul
echo ============================================
echo  DesktopPet - PyInstaller 打包脚本
echo ============================================

cd /d "%~dp0"

REM 清理旧构建
if exist "dist\DesktopPet" rmdir /s /q "dist\DesktopPet"
if exist "build\DesktopPet" rmdir /s /q "build\DesktopPet"

echo.
echo [1/3] 正在打包，请耐心等待...

pyinstaller --noconfirm ^
    --onedir ^
    --console ^
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
    echo.
    echo [错误] 打包失败！
    pause
    exit /b 1
)

echo.
echo [2/3] 复制附加文件...

REM 复制 .env.example 到输出目录
copy ".env.example" "dist\DesktopPet\.env.example" >nul

echo.
echo [3/3] 打包完成！
echo.
echo 输出目录: dist\DesktopPet\
echo.
echo 启动方式: 运行 dist\DesktopPet\DesktopPet.exe
echo 数据目录: dist\DesktopPet\data\ （自动生成）
echo.
pause
