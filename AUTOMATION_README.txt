4MANS AUTO-REFRESH — UPDATED LIVE VERSION

FILES TO UPLOAD

1. index_updated.html
   Rename to: index.html
   Location: repository root

2. update_4mans_updated.py
   Rename to: update_4mans.py
   Location: repository root, beside index.html and 4mans_app_data.json

3. refresh_live.yml
   Rename to: refresh.yml
   Location: .github/workflows/refresh.yml


WHAT CHANGED

• Baseline refresh remains every 3 hours.
• During common NFL game windows, GitHub Actions refreshes every 10 minutes.
• The web page checks for a newer 4mans_app_data.json every 60 seconds while it is open.
• Every automated refresh is stored in poll_history for the current season.
• Winnings By Week becomes a season timeline:
  - old history before this upgrade remains available as weekly anchor points
  - new history records every saved poll going forward
• Total Standings chart cards can be tapped to fill the screen.
• Stats and Ownership both now support:
  - Manager
  - NFL Team
  - Side: All / Offense / Defense
  - Position
  - Player search


IMPORTANT HISTORY NOTE

The app cannot reconstruct intra-game poll snapshots that were never stored.
So the graph can show prior completed weeks as historical anchors, and from the
moment this version is deployed it will begin building true poll-by-poll history.


REFRESH SCHEDULE

Baseline:
  17 */3 * * *

Live windows (UTC):
  */10 * * * 0
  */10 0-6 * * 1,2,5
  */10 16-23 * * 6

GitHub scheduled jobs can start a little late. The page itself checks for a new
JSON every 60 seconds, so once GitHub writes the updated file the open app will
pick it up without a manual browser refresh.


DEPLOY TEST

1. Upload/rename the three files above.
2. In GitHub, open Actions.
3. Open “Refresh 4MANS Data”.
4. Run workflow manually on main.
5. Wait for the green check.
6. Open 4mans_app_data.json.
7. Confirm:
   - version is 5
   - generated_at changed
   - the 2026 season contains poll_history
8. Open the GitHub Pages site.
9. Test:
   - tap each Total Standings chart card to expand / close
   - Stats filters and search
   - Ownership filters and search
   - Winnings timeline
