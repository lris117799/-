@echo off
chcp 65001 >nul
echo ========================================
echo   卡丽希娅助手 - 启动程序
echo ========================================
echo.
echo 正在启动...
echo.

cd /d "%~dp0"
.\venv\Scripts\python.exe main.py

pause
