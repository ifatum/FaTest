@echo off
REM Installs the FaTest shortcut (icon on the Desktop + Start Menu).
REM Just double-click this file.

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-shortcut.ps1"
pause
