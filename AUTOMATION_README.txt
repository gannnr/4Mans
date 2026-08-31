4MANS AUTO-REFRESH FILES

Upload:
1. update_4mans.py
   -> repository root, beside index.html and 4mans_app_data.json

2. refresh.yml
   -> .github/workflows/refresh.yml

IMPORTANT:
The workflow schedule is:
  17 */3 * * *

That means GitHub will start it at minute 17 every third UTC hour.
Using minute 17 instead of exactly minute 00 reduces GitHub's peak cron congestion.

After uploading:
1. Open your GitHub repository.
2. Tap Actions.
3. Open "Refresh 4MANS Data".
4. Tap "Run workflow".
5. Choose main and run it.
6. Wait for a green check mark.
7. Return to the repository and open 4mans_app_data.json.
8. Its "generated_at" value should have changed.

GitHub Pages will then use that refreshed JSON automatically.

NOTE:
GitHub scheduled Actions are not guaranteed to begin at the exact second/minute
listed in cron. A short delay is normal.
