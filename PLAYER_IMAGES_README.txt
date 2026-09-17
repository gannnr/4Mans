4MANS PLAYER IMAGES + WEEKLY ROSTER FOUNDATION

FILES TO ADD

1. update_4mans_images_rosters.py
   Rename to: update_4mans.py
   Location: repository root

2. refresh_player_images.py
   Location: repository root

3. refresh_player_images.yml
   Location: .github/workflows/refresh_player_images.yml

WHAT THIS ADDS

• top-level assets metadata in 4mans_app_data.json
• season-level player_directory for all relevant players
• headshot path for each player
• weekly roster snapshots under each league week:
  - players
  - starters
  - bench
  - weekly player points
  - weekly place / pf / pa
• annual player-image workflow
• local fallback image: assets/players/na.svg
• manifest file: assets/players/<season>/manifest.json

HEADSHOT PATH RULE

The data file points to:
  assets/players/<season>/<player_id>.jpg

If a picture cannot be downloaded, the downloader records that player's path as:
  assets/players/na.svg

IMPORTANT

This is the data + asset foundation for the future Week Detail / Player Detail UI.
It does NOT yet build the full-screen roster browser in index.html.
But after this upload, the JSON and image assets will be ready for that next step.

DEPLOY ORDER

1. Replace update_4mans.py with the new version.
2. Add refresh_player_images.py.
3. Add the workflow file to .github/workflows/refresh_player_images.yml.
4. Run the normal 4MANS data refresh workflow once.
5. Run the new player image workflow once.
6. Confirm your repo now has:
   - assets/players/na.svg
   - assets/players/<season>/manifest.json
   - many .jpg files in assets/players/<season>/
7. Open 4mans_app_data.json and confirm:
   - version is 6
   - each season now contains player_directory
   - each scored week contains rosters inside week objects

NEXT STEP AFTER THIS

After you upload these files, I can build the front-end experience:
Leagues -> Week -> Full-screen roster -> Player popup with picture + labeled stats.
