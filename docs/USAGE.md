# Settings and troubleshooting

## Settings

Open **Settings** to change how textures load, manage the offline copy, select a game folder, run **Check my PC**, open reports and logs, or enable **Reduce motion**. Advanced mode provides detailed streaming, texture, game, and setup controls.

## Game setup

The app may offer a one-time game-folder setup for the connectivity setting and texture cache link. Close the game before applying or undoing it. Use the app's setup controls to undo a change; backups are retained for restoration.

## Common problems

| Problem | Action |
| --- | --- |
| Windows refuses a hosts-file change | Start the app with administrator permission, then use Check my PC to inspect the failure. |
| Another program is using port 80 | Check my PC identifies the listener. Resolve the port conflict before starting the session. |
| No texture requests appear | Close the game, start the app's session, then launch the game again. Check whether a VPN or DNS setting bypasses the local route. |
| Downloads fail or stall | Check your connection and free disk space, then inspect the download log. Pause and resume if needed. |
| The hosts entry disappears | Use the recovery action shown by the app, then inspect any software that manages the hosts file. |
| A session ended unexpectedly | Run Restore hosts from the Start menu or app folder, then restart the app. |

## Reports and storage

An installed edition uses `%LOCALAPPDATA%\MW4TextureControl` for settings, logs, and reports. A portable edition uses `data` beside the executable. Offline texture copies remain in the storage folder you selected.

Session statistics describe requests handled by the app. To assess the picture in-game, use the same scene, graphics settings, and waiting time with the session off and on.

## Update and uninstall

Close the game and stop the active session before updating. Run a newer Setup executable over the existing installation. Settings are stored separately from installed program files.

Uninstall through Windows Settings → Apps or the Start menu. The uninstaller handles active helpers and the app's hosts entry and asks before deleting saved settings. Texture copies and the game folder are kept.

## Connection diagnostics and controls

Open Settings → Connection diagnostics to see the active streaming and download CDN addresses, fallback status, last successful delivery, and the last failure reason. Use the action beside a problem to inspect the connection, disk space, or logs.

Stop streaming ends the streaming session while offline downloads continue. Pause downloads lets in-flight download objects finish and leaves streaming active. Stop everything ends streaming and downloads. Closing the window lists the active work and offers to stop it or leave it running.

Disk protection pauses new transfers when the cache limit is reached or free disk space falls below 2 GiB. Existing transfers can finish. The game stays open. Free cache space to resume streaming; resume the offline download manually. Force-close is an explicit optional setting with a confirmation.

Text size in Settings cycles between 100%, 115%, and 130%. Advanced Settings also has a text-size selector. Tab and Shift+Tab move through controls; Enter or Space activates buttons; Escape closes Settings. Focus stays within Settings while it is open and returns to its button when closed.

Choose a writable **Offline storage** folder in Settings before downloading, especially if the game is installed under Program Files. Stop streaming and pause downloads before changing it.
