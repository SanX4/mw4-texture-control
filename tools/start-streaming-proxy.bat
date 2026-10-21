@echo off
rem LEGACY console launcher - prefer tools\ccs-gui.bat (GUI: hosts, proxy, guard, doctor, reports). Locations come from the GUI settings
rem (Game tab -> tools\work\gui_settings.json); nothing is hard-coded here. Port 80 usually needs no admin on current Windows; the hosts override must already be active
rem (tools\ccshosts.py apply --elevate).  Args are passed through: --max-raw-mib N  --budget-gib N  --offline
cd /d "%~dp0.."
for /f "delims=" %%i in ('python -c "import sys;sys.path.insert(0,'tools');from ccslib import paths;print(paths.MIRROR)"') do set MIR=%%i
python tools\ccsproxy.py --max-raw-mib 4096 --budget-gib 120 --origin "%MIR%" %*
pause
