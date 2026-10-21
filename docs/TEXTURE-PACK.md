# Offline texture downloads

An offline copy stores texture chunks on your disk so the app can serve them locally. The app reads the texture catalogues from your game installation; the installer includes no game content.

## Download a copy

1. Open **Settings → Offline copy**.
2. Choose a storage folder with enough free space.
3. Select campaign-only or the full pack, then a texture level.
4. Read and accept the bulk-download notice.
5. Start the download. Pause and resume from the same page.
6. Select offline loading and start a session before opening the game.

## Approximate storage

| Level | Campaign | Full pack |
| --- | ---: | ---: |
| Standard | 53.6 GiB | 72.7 GiB |
| High | 60.3 GiB | 81.1 GiB |
| Ultra | 81.6 GiB | 110.7 GiB |

Actual requirements depend on the catalogues in your installation. Levels filter chunk sizes; they do not promise a rendering resolution. A higher level downloads missing chunks when you resume with that selection.

## Connections and speed

Start with the default connection count and request limit. The app tests responding CDN edges, retries transient failures, and resumes completed work. A download cap is entered in Mbps; displayed MiB/s measures bytes per second.

Downloads use the CDN routes configured in the app and catalogues from your installation. Keep downloaded content on your own machine. The app needs to stay running during a session even when the download is complete.
