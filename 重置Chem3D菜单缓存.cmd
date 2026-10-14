@echo off
chcp 65001 >nul
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0reset_chem3d_menu_cache.ps1"
set "RESULT=%ERRORLEVEL%"
pause
exit /b %RESULT%
