@echo off
rem CCS Control GUI (unelevated; hosts changes prompt UAC). No console window.
cd /d "%~dp0.."
where pythonw >nul 2>&1 && (start "" pythonw tools\ccsgui.py) || (python tools\ccsgui.py)
