@echo off
title Swarm Detection installer
cd /d "%~dp0"
if exist "%~dp0install.ps1" (
  powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
) else (
  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://raw.githubusercontent.com/coden607/swarm/main/install.ps1 | iex"
)
echo.
pause
