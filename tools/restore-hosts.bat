@echo off
rem Emergency undo: removes ONLY the CCS hosts override (normal DNS for the CDN host again). Works without the GUI.
rem Hand-added lines for cod-assets.cdn.callofduty.com are removed too. A backup is written to tools\work\hosts-backups first.
cd /d "%~dp0.."
python tools\ccshosts.py remove --elevate
python tools\ccshosts.py status
pause
