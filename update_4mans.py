#!/usr/bin/env python3
"""
4MANS automatic data refresh
-----------------------------
Builds 4mans_app_data.json directly from Sleeper.

Designed for GitHub Actions:
- no API key required
- standard library only
- discovers Nactasty's completed 4-team leagues
- supports preseason current rosters / ownership
- pulls scored matchup weeks
- pulls Sleeper player map
- attempts Sleeper's stats feed for offense + IDP stats

The website itself stays static. This file only refreshes 4mans_app_data.json.
"""

import json
import math
import os
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

USERNAME = "Nactasty"
START_YEAR = 2025
CURRENT_YEAR = datetime.now(timezone.utc).year
# Keep 2026 available even if this script is tested before/around the season transition.
END_YEAR = max(2026, CURRENT_YEAR)
SEASONS = [str(y) for y in range(START_YEAR, END_YEAR + 1)]

API = "https://api.sleeper.app/v1"
STATS_BASES = (
    "https://api.sleeper.com",
    "https://api.sleeper.app",
)

# Stable manager identity used by the app.
MANAGERS = [
    {"key": "nactasty", "label": "nactasty", "user_id": "1100887324210114560"},
    {"key": "jpagonis", "label": "jpagonis", "user_id": "1204509851913310208"},
    {"key": "TheChavenator", "label": "TheChavenator", "user_id": "1228771047986180096"},
    {"key": "bingbongtinydong", "label": "bingbongtinydong", "user_id": "1230290123791269888"},
]
USER_TO_KEY = {m["user_id"]: m["key"] for m in MANAGERS}

OFFENSE_POS = {"QB", "RB", "WR", "TE", "K", "FB"}
DEFENSE_POS = {
    "DL", "DE", "DT", "LB", "ILB", "OLB", "DB", "CB", "S", "SS", "FS",
    "EDGE"
}

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def get_json(url, tries=3, timeout=45):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "4MANS/1.0",
                    "Accept": "application/json",
                },
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e
            if attempt < tries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET failed: {url}\n{last}")

def safe_num(v, default=0.0):
    try:
        if v is None or v == "":
            return default
        return float(v)
    except Exception:
        return default

def roster_points(roster):
    """Sleeper roster cumulative points, including decimal component when present."""
    settings = roster.get("settings") or {}
    base = safe_num(settings.get("fpts"))
    dec = safe_num(settings.get("fpts_decimal"))
    # Sleeper stores decimal separately as hundredths.
    if dec and abs(dec) < 100:
        base += dec / 100.0
    return round(base, 2)

def draft_is_complete(league_id):
    drafts = get_json(f"{API}/league/{league_id}/drafts")
    completed = [d for d in drafts if str(d.get("status", "")).lower() == "complete"]
    # Some completed drafts are identifiable by a completed timestamp even if status differs.
    if not completed:
        completed = [d for d in drafts if d.get("complete_time") or d.get("last_picked")]
    return bool(completed), [str(d.get("draft_id")) for d in completed if d.get("draft_id")]

def manager_key(owner_id):
    return USER_TO_KEY.get(str(owner_id))

def discover_leagues(user_id, season):
    leagues = get_json(f"{API}/user/{user_id}/leagues/nfl/{season}")
    out = []
    for league in leagues:
        if int(league.get("total_rosters") or 0) != 4:
            continue
        league_id = str(league["league_id"])
        try:
            complete, draft_ids = draft_is_complete(league_id)
        except Exception as e:
            print(f"WARNING draft check failed {league_id}: {e}")
            continue
        if not complete:
            continue
        league = dict(league)
        league["_draft_ids"] = draft_ids
        out.append(league)
    return out

def fetch_members(league_id):
    users = get_json(f"{API}/league/{league_id}/users")
    by_id = {str(u.get("user_id")): u for u in users}
    return by_id

def fetch_rosters(league_id):
    return get_json(f"{API}/league/{league_id}/rosters")

def normalize_player(player_id, pdata):
    pid = str(player_id)
    pdata = pdata or {}
    first = pdata.get("first_name") or ""
    last = pdata.get("last_name") or ""
    name = (first + " " + last).strip() or pdata.get("full_name") or pid
    pos = pdata.get("position")
    team = pdata.get("team")

    # Team defenses appear as IDs like DAL, SF, etc.
    if pid.isalpha() and len(pid) <= 4 and not pos:
        name = f"{pid} Defense"
        pos = "DEF"
        team = pid

    fantasy_positions = pdata.get("fantasy_positions") or ([pos] if pos else [])
    if pos in DEFENSE_POS:
        side = "defense"
    elif pos == "DEF":
        side = "defense"
    else:
        side = "offense"

    return {
        "player_id": pid,
        "player": name,
        "team": team or "",
        "position": pos or "",
        "fantasy_positions": fantasy_positions,
        "side": side,
    }

def get_matchup_week(league_id, week):
    rows = get_json(f"{API}/league/{league_id}/matchups/{week}")
    return rows if isinstance(rows, list) else []

def week_has_activity(rows):
    if not rows:
        return False
    for r in rows:
        if abs(safe_num(r.get("points"))) > 0:
            return True
        pp = r.get("players_points") or {}
        if any(abs(safe_num(v)) > 0 for v in pp.values()):
            return True
    return False

def build_week_rows(raw_rows, roster_to_manager, cumulative_pf, cumulative_pa):
    # Group matchup opponents by matchup_id.
    groups = defaultdict(list)
    for r in raw_rows:
        groups[str(r.get("matchup_id"))].append(r)

    output = []
    for r in raw_rows:
        rid = int(r.get("roster_id"))
        mgr = roster_to_manager.get(rid)
        if not mgr:
            continue

        pf = round(safe_num(r.get("points")), 2)
        pa = None
        group = groups.get(str(r.get("matchup_id")), [])
        opponents = [x for x in group if int(x.get("roster_id")) != rid]
        if len(opponents) == 1:
            pa = round(safe_num(opponents[0].get("points")), 2)

        cumulative_pf[mgr] += pf
        if pa is not None:
            cumulative_pa[mgr] += pa

        output.append({
            "manager": mgr,
            "pf": pf,
            "pa": pa,
            "players": [str(x) for x in (r.get("players") or [])],
            "starters": [str(x) for x in (r.get("starters") or [])],
            "players_points": {str(k): safe_num(v) for k, v in (r.get("players_points") or {}).items()},
        })
    return output

def add_places(rows):
    """Rank by PF descending. Competition rank for ties."""
    valid = [r for r in rows if r.get("pf") is not None]
    sorted_vals = sorted({safe_num(r["pf"]) for r in valid}, reverse=True)
    rank_for = {v: i + 1 for i, v in enumerate(sorted_vals)}
    for r in rows:
        if r.get("pf") is None:
            r["place"] = None
        else:
            r["place"] = rank_for[safe_num(r["pf"])]
    return rows

def fetch_stats_feed(season):
    """
    Sleeper stats endpoints are not part of the main public docs and have changed shape
    historically. Try known forms. Returning {} is safe: the app still refreshes leagues,
    standings and ownership.
    """
    urls = []
    for base in STATS_BASES:
        urls.extend([
            f"{base}/stats/nfl/regular/{season}",
            f"{base}/stats/nfl/{season}?season_type=regular",
        ])

    for url in urls:
        try:
            data = get_json(url, tries=2, timeout=60)
            if data:
                print(f"Stats feed OK: {url}")
                return data
        except Exception as e:
            print(f"Stats feed fallback failed: {url} :: {e}")
    print(f"WARNING: no stats feed available for {season}")
    return {}

def stats_by_player(raw):
    """
    Normalize common Sleeper stats response shapes to {player_id: stats_dict}.
    """
    if isinstance(raw, dict):
        # Most common shape: {"player_id": {...stats...}}
        if raw and all(isinstance(v, dict) for v in raw.values()):
            # Some responses wrap stats under "stats".
            out = {}
            for k, v in raw.items():
                if isinstance(v, dict):
                    if "player_id" in v and "stats" in v:
                        out[str(v["player_id"])] = v.get("stats") or {}
                    else:
                        out[str(k)] = v.get("stats") if isinstance(v.get("stats"), dict) else v
            return out
    if isinstance(raw, list):
        out = {}
        for item in raw:
            if not isinstance(item, dict):
                continue
            pid = item.get("player_id")
            if pid is None:
                continue
            out[str(pid)] = item.get("stats") if isinstance(item.get("stats"), dict) else item
        return out
    return {}

def pick_stat(stats, *names):
    for n in names:
        if n in stats and stats[n] is not None:
            return safe_num(stats[n])
    return 0.0

def app_stat_row(meta, stats, ownership, fpts_all, fpts_by_manager):
    side = meta["side"]
    base = {
        "player_id": meta["player_id"],
        "player": meta["player"],
        "team": meta["team"],
        "position": meta["position"],
        "side": side,
        "ownership": ownership,
        "fpts_all": fpts_all,
        "fpts_by_manager": fpts_by_manager,
    }
    if side == "offense":
        base.update({
            "rush_yd": pick_stat(stats, "rush_yd", "rush_yds"),
            "rush_td": pick_stat(stats, "rush_td"),
            "rec": pick_stat(stats, "rec"),
            "rec_yd": pick_stat(stats, "rec_yd", "rec_yds"),
            "rec_td": pick_stat(stats, "rec_td"),
            "pass_yd": pick_stat(stats, "pass_yd", "pass_yds"),
            "pass_td": pick_stat(stats, "pass_td"),
            "pass_int": pick_stat(stats, "pass_int"),
        })
    else:
        base.update({
            "tackles": pick_stat(stats, "idp_tkl", "tkl"),
            "solo": pick_stat(stats, "idp_tkl_solo", "tkl_solo"),
            "ast": pick_stat(stats, "idp_tkl_ast", "tkl_ast"),
            "sacks": pick_stat(stats, "idp_sack", "sack"),
            "tfl": pick_stat(stats, "idp_tkl_loss", "tkl_loss"),
            "qbh": pick_stat(stats, "idp_qb_hit", "qb_hit"),
            "ints": pick_stat(stats, "idp_int", "int"),
            "pd": pick_stat(stats, "idp_pass_def", "pass_def"),
            "ff": pick_stat(stats, "idp_ff", "ff"),
            "fr": pick_stat(stats, "idp_fum_rec", "fum_rec"),
            "def_td": pick_stat(stats, "idp_def_td", "def_td"),
        })
    return base

def build():
    print("4MANS refresh started", now_iso())

    user = get_json(f"{API}/user/{urllib.parse.quote(USERNAME)}")
    user_id = str(user["user_id"])

    # Sleeper advises fetching the player map sparingly. The GitHub workflow runs every
    # 3 hours, but a single 5MB call per run is still modest. If desired later we can cache
    # this once/day in the repo.
    print("Fetching Sleeper player map...")
    player_map = get_json(f"{API}/players/nfl", timeout=120)

    app = {
        "version": 4,
        "generated_at": now_iso(),
        "managers": [{"key": m["key"], "label": m["label"]} for m in MANAGERS],
        "seasons": {},
    }

    for season in SEASONS:
        print(f"\n=== {season} ===")
        leagues = discover_leagues(user_id, season)
        print("qualifying leagues:", len(leagues))

        app_leagues = []
        exposure_counts = {m["key"]: defaultdict(int) for m in MANAGERS}
        league_counts = {m["key"]: 0 for m in MANAGERS}

        # For Analysis FPTS approximation: season Sleeper-scored player points by
        # manager/league. This keeps the behavior of the current app.
        player_league_points = defaultdict(lambda: defaultdict(dict))
        relevant_player_ids = set()

        total_pf = {m["key"]: 0.0 for m in MANAGERS}
        total_pa = {m["key"]: 0.0 for m in MANAGERS}
        any_scored_week = False

        for li, league in enumerate(sorted(leagues, key=lambda x: (x.get("name") or "").lower()), 1):
            lid = str(league["league_id"])
            lname = league.get("name") or f"League {lid}"
            print(f"[{li}/{len(leagues)}] {lname}")

            rosters = fetch_rosters(lid)
            members = fetch_members(lid)

            roster_to_manager = {}
            current_players_by_manager = {m["key"]: [] for m in MANAGERS}
            for roster in rosters:
                rid = int(roster.get("roster_id"))
                owner_id = str(roster.get("owner_id") or "")
                mgr = manager_key(owner_id)
                if not mgr:
                    # Fall back to league member display name if this exact quartet ever
                    # has a username casing change.
                    member = members.get(owner_id) or {}
                    display = str(member.get("display_name") or member.get("username") or "")
                    lowered = display.lower()
                    for m in MANAGERS:
                        if lowered == m["key"].lower() or lowered == m["label"].lower():
                            mgr = m["key"]
                            break
                if not mgr:
                    continue

                roster_to_manager[rid] = mgr
                league_counts[mgr] += 1
                plist = [str(p) for p in (roster.get("players") or [])]
                current_players_by_manager[mgr] = plist
                for pid in plist:
                    exposure_counts[mgr][pid] += 1
                    relevant_player_ids.add(pid)

            # Scan weeks until 18. Only publish weeks with actual scoring activity.
            cumulative_pf = defaultdict(float)
            cumulative_pa = defaultdict(float)
            weeks = []
            for week in range(1, 19):
                try:
                    raw = get_matchup_week(lid, week)
                except Exception as e:
                    print(f"  week {week} fetch warning: {e}")
                    continue

                if not week_has_activity(raw):
                    continue

                any_scored_week = True
                rows = build_week_rows(raw, roster_to_manager, cumulative_pf, cumulative_pa)

                # Capture player points for Analysis.
                for row in rows:
                    mgr = row["manager"]
                    for pid, pts in row["players_points"].items():
                        relevant_player_ids.add(pid)
                        old = player_league_points[pid][mgr].get(lid, 0.0)
                        player_league_points[pid][mgr][lid] = old + safe_num(pts)

                # Weekly displayed PF is cumulative-through-week in the Leagues page.
                display_rows = []
                for m in MANAGERS:
                    key = m["key"]
                    if key in roster_to_manager.values():
                        display_rows.append({
                            "manager": key,
                            "pf": round(cumulative_pf[key], 2),
                            "pa": round(cumulative_pa[key], 2),
                        })
                add_places(display_rows)
                weeks.append({"week": week, "rows": display_rows})

            # Current / season totals. Prefer accumulated matchup data when available.
            totals = []
            for m in MANAGERS:
                key = m["key"]
                if key not in roster_to_manager.values():
                    continue
                if weeks:
                    pf = round(cumulative_pf[key], 2)
                    pa = round(cumulative_pa[key], 2)
                else:
                    # Preseason: performance values must remain null, not zero.
                    pf = None
                    pa = None
                totals.append({"manager": key, "pf": pf, "pa": pa})
                if pf is not None:
                    total_pf[key] += pf
                if pa is not None:
                    total_pa[key] += pa
            add_places(totals)

            app_leagues.append({
                "league_id": lid,
                "name": lname,
                "state": "active_or_complete" if weeks else "preseason",
                "display_status": "" if weeks else "Waiting for season to start",
                "totals": totals,
                "weeks": sorted(weeks, key=lambda x: x["week"], reverse=True),
            })

        # Ownership table from current rosters.
        ownership_rows = []
        all_ids = sorted(relevant_player_ids)
        for pid in all_ids:
            meta = normalize_player(pid, player_map.get(pid) or {})
            own = {}
            for m in MANAGERS:
                key = m["key"]
                denom = max(1, league_counts[key])
                own[key] = round(100.0 * exposure_counts[key].get(pid, 0) / denom, 1)
            if any(v > 0 for v in own.values()):
                ownership_rows.append({
                    "player_id": pid,
                    "player": meta["player"],
                    "position": meta["position"],
                    "team": meta["team"],
                    "ownership": own,
                })

        # Raw player stats.
        raw_stats = stats_by_player(fetch_stats_feed(season))
        stats_rows = []
        for pid in all_ids:
            meta = normalize_player(pid, player_map.get(pid) or {})
            own = {}
            for m in MANAGERS:
                key = m["key"]
                denom = max(1, league_counts[key])
                own[key] = round(100.0 * exposure_counts[key].get(pid, 0) / denom, 1)

            by_mgr = {}
            all_league_values = []
            for m in MANAGERS:
                key = m["key"]
                vals = list(player_league_points[pid][key].values())
                by_mgr[key] = round(sum(vals) / len(vals), 2) if vals else None
                all_league_values.extend(vals)
            fpts_all = round(sum(all_league_values) / len(all_league_values), 2) if all_league_values else None

            stats_rows.append(app_stat_row(
                meta,
                raw_stats.get(pid) or {},
                own,
                fpts_all,
                by_mgr,
            ))

        app["seasons"][season] = {
            "summary": {
                "state": "active_or_complete" if any_scored_week else "preseason",
                # Kept for backwards compatibility with index.html.
                # Current index recalculates winnings from league totals.
                "current_winnings": {m["key"]: 0 for m in MANAGERS},
                "winning_leagues": {m["key"]: 0 for m in MANAGERS},
                "weekly_winnings": {},
                "points_for": {k: round(v, 2) for k, v in total_pf.items()},
                "points_against": {k: round(v, 2) for k, v in total_pa.items()},
            },
            "leagues": app_leagues,
            "ownership": ownership_rows,
            "stats": stats_rows,
        }

    tmp = "4mans_app_data.json.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(app, f, separators=(",", ":"), ensure_ascii=False)
    os.replace(tmp, "4mans_app_data.json")

    print("\nWrote 4mans_app_data.json")
    print("generated_at:", app["generated_at"])
    for season, data in app["seasons"].items():
        print(
            season,
            "leagues=", len(data["leagues"]),
            "ownership=", len(data["ownership"]),
            "stats=", len(data["stats"]),
            "state=", data["summary"]["state"],
        )

if __name__ == "__main__":
    build()
