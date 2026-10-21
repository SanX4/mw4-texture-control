# Getting started

## Install

Download the Setup executable from [Releases](https://github.com/SanX4/mw4-texture-control/releases). Run it, choose an installation folder, and finish the setup. Open **MW4 Texture Control** from the Start menu.

For the portable edition, extract the entire ZIP to a writable folder and open **MW4 Texture Control.exe**. Keep the executable and its `_internal` folder together.

## First launch

1. Close the game.
2. Accept the app's first-run notice.
3. Select the folder containing your game. Confirm the detected folder or choose it manually.
4. Choose **While I play** to fetch textures on demand, or **Download them once** to save an offline copy.
5. Complete the one-time game setup if the app asks for it. Read the proposed action before applying it.

## Start a session

1. Press **Turn on HD textures** before launching the game.
2. Start the game normally and keep the app open.
3. Check the overview for delivered textures, transfer speed, and failed requests.
4. Close the game, then turn the session off.
5. Review the session summary or open the full report.

## Offline play

Open **Settings → Offline copy**. Choose a storage folder, texture level, and pack selection, then start the download. You can pause and resume it. A campaign copy can require roughly 54–82 GiB depending on the selected level; leave additional free space for the game and cache.

Once the copy is ready, select the offline loading mode and start a session before launching the game. The app still needs to run to serve the files from disk.

## More help

See [Settings and troubleshooting](USAGE.md) and [Offline downloads](TEXTURE-PACK.md).

## Check the in-game result

Use the app’s optional visual test with the same scene and graphics settings:

### Pick a spot

Choose a place in the game you can come back to: somewhere with plenty of distant or detailed surfaces, at the same time of day. Keep the graphics settings the same for the whole test, and close the game. Optional for a strict comparison: rename the game cache folder (xpak_cache) before each run, the game makes a new one.

### Before: tool off

Press the button to put the hosts file back (no redirect). Launch the game, go to your spot, wait five minutes so the textures settle, and take a screenshot. Save it as before-1 in the folder the last step opens.

### After: tool on

Close the game. Press Start session, launch the game, go to the same spot, wait the same time and take a screenshot. Save it as after-1.

### Compare

Put the two screenshots side by side at full size and look at distant surfaces, signs and small details. Some setups show a difference and some do not; this test tells you for yours. Open the Report tab to see what the game asked for in the "after" run.

## Words used in the app

**Session**  
The time between "Start session" and "Stop session". While it runs, the helper is up and the hosts entry sends the game's texture requests to it.

**Helper (proxy)**  
A small program on this PC that answers the game's texture requests. It gets each piece from your copy on disk if you have one, otherwise from the internet.

**Hosts file**  
A Windows file that can override where a web address points. This tool adds one marked block to it so the game talks to the helper. "Restore hosts" takes the block out again, and a backup is made first.

**UAC prompt**  
The Windows window that asks "Do you want to allow this app to make changes?". The program shows it once, when it starts, because it edits the protected hosts file and the game folder. Answer Yes to continue.

**CDN**  
The servers the game downloads its textures from.

**Edge**  
One particular CDN server address. The tool measures a few and uses the fastest.

**Texture piece (chunk)**  
The game streams its textures in many small pieces. Each request from the game is for one piece.

**Streaming**  
Loading textures while you play instead of all at the start. What the game asks for depends on where you are and what it decides to show.

**Quick fix**  
No big download. The helper fetches the pieces the game asks for while you play.

**Offline copy (mirror)**  
A copy of the texture pieces on your own drive (about 54 to 82 GB). The game is served from it, so playing needs little or no internet. The helper still has to run while you play: without it the game cannot reach the copy.

**Detail level**  
A cut-off for very large pieces (the highest-detail versions). Ultra serves everything; Standard leaves the largest out, and the game keeps the smaller version.

**Connections (workers)**  
How many downloads run at the same time when building an offline copy. More is not always faster; the default is a safe starting point.

**Requests per second (req/s)**  
How often the tool asks the CDN for a piece. It is capped so it does not hammer the servers.

**Doctor**  
A checklist that tests everything this tool depends on (port, hosts entry, folders, internet) and offers a safe fix for each failing check.

**Game cache**  
The folder where the game keeps pieces it has already received (xpak_cache). The game recreates it if it is missing.

**Game setup**  
Two small changes in the game folder so the game uses the textures it is sent: its Steam settings are set to online mode, and sp26\xpak_cache is linked to the cache the game fills. Done once, after you confirm.

**Disk guard**  
Watches the game cache and stops the game if it grows past the limit you set, so the drive cannot fill up.

**Report**  
After a session the tool writes a summary of what the game asked for and what was delivered. It is found in the Report tab.

