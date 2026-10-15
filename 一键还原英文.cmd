@echo off
chcp 65001 >nul
setlocal
title 免费开源 - 谨防付费转卖 - https://github.com/yangshaoxiao/chemdraw-zh-patch
echo ============================================================
echo 本汉化补丁免费开源，无收费激活，无设备绑定。
echo 谨防付费转卖：请优先从以下 GitHub 项目免费下载。
echo 官方项目地址: https://github.com/yangshaoxiao/chemdraw-zh-patch
echo 若您付费获得本补丁，请向卖家核实免费来源。
echo ChemDraw 软件本身仍须另行取得有效授权。
echo ============================================================
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -Mode Restore
set "RESULT=%ERRORLEVEL%"
echo.
if not "%RESULT%"=="0" echo 操作未完成，请查看上方错误。
echo.
echo 本补丁免费开源，谨防付费转卖。
echo 免费下载: https://github.com/yangshaoxiao/chemdraw-zh-patch
pause
exit /b %RESULT%
