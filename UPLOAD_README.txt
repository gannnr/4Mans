4MANS v8 upload set

Replace these repo files with the files in this package:
1. index.html
2. update_4mans.py
3. refresh_player_images.py
4. .github/workflows/refresh_player_images.yml

What changed:
- One shared player image cache: assets/players/<player_id>.jpg
- Historical and current seasons use the same headshot file.
- Annual Aug 30 workflow refreshes/overwrites existing shared headshots.
- Image refresh includes players referenced by ALL seasons in 4mans_app_data.json.
- Corrected weekly Sleeper stats URL to /v1/stats/nfl/regular/<season>/<week>.
- Weekly stats saved in seasons[year].weekly_stats for player detail cards.
- Player detail cards remain position-aware (QB/RB/WR/TE/K/DEF/IDP).
- JSON schema version is now 8.

After upload:
A. Run Actions > Refresh 4MANS Data manually once.
B. Confirm 4mans_app_data.json starts with "version":8.
C. Open JSON/search for "weekly_stats" and confirm week objects contain player IDs/stats.
D. Run Actions > Refresh 4MANS Player Images once to migrate into shared assets/players/<id>.jpg.
E. Old assets/players/2026/ can remain temporarily; v8 no longer references it.
