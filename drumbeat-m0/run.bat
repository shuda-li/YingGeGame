@echo off
chcp 65001 >nul
cd /d "%~dp0"
title 踏鼓 M0

rem 依次尝试候选解释器，选中第一个能 import pygame 的
rem 第 1 个是本机已验证可用的环境；第 2 个用于其他装了依赖的机器
set PY=
for %%P in ("C:\Pychram\Python云烟\python.exe" "python") do (
  if not defined PY (
    "%%~P" -c "import pygame" >nul 2>&1
    if not errorlevel 1 set PY=%%~P
  )
)

if not defined PY (
  echo [错误] 没有找到已安装 pygame 的 Python 环境。
  echo.
  echo 请先安装依赖，例如：
  echo     python -m pip install pygame numpy sounddevice pyinstaller
  echo.
  echo 或直接用已装好依赖的解释器运行本目录下的 run.py。
  pause
  exit /b 1
)

echo 使用解释器: %PY%
"%PY%" run.py
if errorlevel 1 pause
