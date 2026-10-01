# 4MANS GitHub + Supabase migration

The polished interface is published at the main GitHub Pages URL, `/4Mans/`.
The preview path remains available with the same interface.
All data and image paths use the existing repository. Login and predictions use the independent
Supabase `fourmans` Edge Function in project `siakdeksohfnwurgrdvn`.

## Member access

The commissioner account and existing prediction records were copied privately from the old
backend. Existing username/password login is retained. Browser sessions are new on GitHub Pages.
Only nactasty can create invitations or rule on results. Invitation links work on the current
website path. Do not add credentials, imported password hashes, or session tokens to this repository.

The backend verifies opaque, randomly generated bearer sessions against SHA-256 hashes in
its private sessions table, with a 30-day expiry. This is custom member authentication,
not Supabase Auth email login. `verify_jwt=false` is intentional: the handler authenticates
these sessions itself. Browser tokens stay in localStorage on the GitHub Pages origin.
All application tables have RLS enabled and no public grants; only the Edge Function's
server-side service role can access them. The SQL transaction bridge is invoker-security,
service-role-only, and receives only server-constructed parameterized statements. Public clients
cannot call it. Multi-statement edits and rulings are committed atomically.

## Stats updates

`Refresh 4MANS Data` wakes at minutes 7, 17, 27, 37, 47, and 57. `refresh_gate.py` uses
nflverse's NFL schedule, with Eastern kickoff times converted through an IANA timezone.
It refreshes from 30 minutes before kickoff through seven hours after kickoff, covering
pregame, overtime/delays and postgame corrections, including postseason and international dates.
Otherwise it refreshes when saved data is three hours old. If the schedule is unavailable,
it refreshes conservatively rather than skipping a possible game. Manual dispatch always runs.
These are scheduled targets: GitHub Actions can start late or drop scheduled ticks.

The player map and schedule are cached for one day. Current and preceding weekly scores
are re-fetched; archived seasons are reused. An incomplete league set, missing manager,
lost historical score, or lost stats feed prevents replacing saved data. Updates write
atomically. The frontend checks saved JSON every minute; this does not trigger a Sleeper pull.
The annual image workflow remains in place.

## Validation

`node tests/dashboard.cjs` checks manager switching/sorting, league history, position-specific
stats and navigation. `python tests/updater.py` checks score preservation and tied payouts.
`python tests/game-window.py` checks kickoff windows, DST, international starts and postseason.
`tests/predictions.mjs` exercises the actual route with SQLite fixtures; it needs esbuild.
The hosted backend was also checked with temporary accounts and requests covering login,
creator edits, stale acceptance, payouts, reopening, authorization and season locking.
Temporary QA records were removed. No hosted load-capacity claim is made.

## Deployment and recovery

Edge source is in `supabase/functions/fourmans`; schema is in `supabase/migrations`.
Deploy function changes to the same project. Supabase supplies its own server-side service key;
never place it in HTML. To switch the homepage after the preview login check, publish this
branch's `index.html` as the root index. Revert that file to restore the previous homepage.
Keep the old Sites deployment read-only until the user verifies their real login.
Pause the old Sites schedule after the GitHub replacement is accepted. Export future account
and prediction backups privately; do not commit them to the public repository.

## Current publication status

The commissioner accepted the GitHub preview. The polished interface is now the root homepage.
The GitHub refresh workflow is configured for game-window and baseline updates.
All six 2025 sample predictions and their responses/rulings were removed from Supabase;
the application starts with zero predictions. All years now use real prediction records.
The custom member login and commissioner account are preserved.
