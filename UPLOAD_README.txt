4MANS v10 UPLOAD PACKAGE

FILES ARE ALREADY NAMED FOR PRODUCTION. DO NOT RENAME THEM.

Replace/add these files in GitHub:

Repo root:
- index.html
- update_4mans.py   (same v9 updater you supplied; included with the correct production name for convenience)
- refresh_player_images.py
- UPLOAD_README.txt

Workflow folder:
- .github/workflows/refresh_player_images.yml

WHAT CHANGED
- Expanded LEAGUES CURRENTLY WINNING chart is now interactive.
- Tap a manager bar while expanded to select it.
- Selected bar gets a yellow outline.
- A non-clickable list below shows the leagues that manager is currently winning.
- Winning-league list shows league photo, league name, current 1st-place status, and points.
- Weekly Full Roster no longer has the redundant manager dropdown.
- The four manager score tiles are now the selector.
- Team MVPs no longer has the redundant manager dropdown.
- The four season-total manager tiles are now the selector.
- Manager photos and league photos are shown in the new/updated UI.
- Annual image refresh now caches player + manager + league Sleeper images.
- Image refresh overwrites existing cached images each August 30 and still supports manual runs.

AFTER UPLOAD
1. Run GitHub Actions -> Refresh 4MANS Images once.
2. Wait for it to finish green. This creates assets/managers and assets/leagues and refreshes player images.
3. If you also replaced update_4mans.py, no schema change was made; a separate data refresh is not required solely for this package because the image workflow runs update_4mans.py first.
4. Wait for GitHub Pages to deploy, then test on iPhone Safari.

NOTE
League rows inside the expanded winning-leagues list are intentionally informational only. Tapping them does nothing.
