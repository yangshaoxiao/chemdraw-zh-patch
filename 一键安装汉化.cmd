@echo off
chcp 65001 >nul
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -Mode Install
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" echo 操作未完成，请查看上方错误。
pause
exit /b %RESULT%
