#!/usr/bin/env python3
"""
Refresh shared 4MANS image caches for players, managers, and leagues.

Storage:
  assets/players/<player_id>.jpg
  assets/managers/<manager_key>.jpg
  assets/leagues/<league_id>.jpg

The workflow runs annually and can also be run manually. Use --refresh-existing
when you want to replace existing cached photos with the latest Sleeper images.
"""

import argparse
import json
import re
import time
import urllib.request
from pathlib import Path

API = "https://api.sleeper.app/v1"
PLAYER_PATTERNS = [
    "https://sleepercdn.com/content/nfl/players/thumb/{player_id}.jpg",
    "https://sleepercdn.com/content/nfl/players/{player_id}.jpg",
]
AVATAR_PATTERN = "https://sleepercdn.com/avatars/{avatar}"
FALLBACK_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320" viewBox="0 0 320 320">
  <rect width="320" height="320" rx="24" fill="#f2f2ef"/>
  <circle cx="160" cy="118" r="58" fill="#d9d8d2"/>
  <path d="M62 278c8-56 50-86 98-86s90 30 98 86" fill="#d9d8d2"/>
  <text x="160" y="302" font-family="Arial, sans-serif" font-size="28" text-anchor="middle" fill="#6f716d">N/A</text>
</svg>
'''


def get_json(url, tries=3, timeout=45):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "4MANS-Images/2.0", "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e
            if attempt < tries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET failed: {url}\n{last}")


def fetch_bytes(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": "4MANS-Images/2.0", "Accept": "image/*,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        ctype = r.headers.get_content_type() or ""
        data = r.read()
    return ctype, data


def ensure_fallback(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "na.svg"
    if not path.exists() or path.read_text(encoding="utf-8") != FALLBACK_SVG:
        path.write_text(FALLBACK_SVG, encoding="utf-8")


def load_app(path="4mans_app_data.json"):
    p = Path(path)
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def safe_name(value):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", str(value))


def download(urls, out_file):
    for url in urls:
        try:
            ctype, data = fetch_bytes(url)
        except Exception:
            continue
        if ctype.startswith("image/") and data and len(data) >= 128:
            out_file.parent.mkdir(parents=True, exist_ok=True)
            out_file.write_bytes(data)
            return url
    return ""


def player_ids(app):
    ids = set()
    for season in (app.get("seasons") or {}).values():
        ids.update(str(pid) for pid in ((season or {}).get("player_directory") or {}).keys())
        for row in ((season or {}).get("ownership") or []):
            if row.get("player_id"):
                ids.add(str(row["player_id"]))
    if ids:
        return sorted(ids, key=lambda x: (not x.isdigit(), x))
    all_players = get_json(f"{API}/players/nfl?active=true", timeout=120)
    return sorted((str(x) for x in all_players.keys()), key=lambda x: (not x.isdigit(), x))


def manager_targets(app):
    out = []
    for m in app.get("managers") or []:
        key, uid = str(m.get("key") or ""), str(m.get("user_id") or "")
        if key and uid:
            out.append((key, uid))
    return out


def league_ids(app):
    ids = set()
    for season in (app.get("seasons") or {}).values():
        for league in (season or {}).get("leagues") or []:
            lid = str(league.get("league_id") or "")
            if lid:
                ids.add(lid)
    return sorted(ids)


def avatar_url(obj):
    avatar = str((obj or {}).get("avatar") or "").strip()
    if not avatar or avatar.lower() in {"none", "null"}:
        return ""
    return AVATAR_PATTERN.format(avatar=avatar)


def refresh_players(app, refresh_existing=False, limit=0):
    out_dir = Path("assets/players")
    ensure_fallback(out_dir)
    ids = player_ids(app)
    if limit:
        ids = ids[:limit]
    manifest = {"players": {}}
    for i, pid in enumerate(ids, 1):
        out_file = out_dir / f"{pid}.jpg"
        if out_file.exists() and out_file.stat().st_size >= 128 and not refresh_existing:
            manifest["players"][pid] = {"path": f"assets/players/{pid}.jpg", "status": "cached"}
            continue
        urls = [p.format(player_id=pid) for p in PLAYER_PATTERNS]
        source = download(urls, out_file)
        if source:
            manifest["players"][pid] = {"path": f"assets/players/{pid}.jpg", "status": "refreshed" if refresh_existing else "downloaded", "source": source}
        else:
            out_file.unlink(missing_ok=True)
            manifest["players"][pid] = {"path": "assets/players/na.svg", "status": "fallback"}
        if i % 50 == 0:
            print(f"Players {i}/{len(ids)}")
    (out_dir / "manifest.json").write_text(json.dumps(manifest, separators=(",", ":")), encoding="utf-8")
    return len(ids)


def refresh_managers(app, refresh_existing=False):
    out_dir = Path("assets/managers")
    ensure_fallback(out_dir)
    manifest = {"managers": {}}
    for key, uid in manager_targets(app):
        out_file = out_dir / f"{safe_name(key)}.jpg"
        if out_file.exists() and out_file.stat().st_size >= 128 and not refresh_existing:
            manifest["managers"][key] = {"path": f"assets/managers/{safe_name(key)}.jpg", "status": "cached"}
            continue
        try:
            user = get_json(f"{API}/user/{uid}") or {}
        except Exception as e:
            print(f"WARNING manager lookup failed {key}: {e}")
            user = {}
        url = avatar_url(user)
        source = download([url], out_file) if url else ""
        if source:
            manifest["managers"][key] = {"path": f"assets/managers/{safe_name(key)}.jpg", "status": "refreshed" if refresh_existing else "downloaded", "source": source}
        else:
            out_file.unlink(missing_ok=True)
            manifest["managers"][key] = {"path": "assets/managers/na.svg", "status": "fallback"}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, separators=(",", ":")), encoding="utf-8")
    return len(manifest["managers"])


def refresh_leagues(app, refresh_existing=False):
    out_dir = Path("assets/leagues")
    ensure_fallback(out_dir)
    manifest = {"leagues": {}}
    ids = league_ids(app)
    for i, lid in enumerate(ids, 1):
        out_file = out_dir / f"{safe_name(lid)}.jpg"
        if out_file.exists() and out_file.stat().st_size >= 128 and not refresh_existing:
            manifest["leagues"][lid] = {"path": f"assets/leagues/{safe_name(lid)}.jpg", "status": "cached"}
            continue
        try:
            league = get_json(f"{API}/league/{lid}") or {}
        except Exception as e:
            print(f"WARNING league lookup failed {lid}: {e}")
            league = {}
        url = avatar_url(league)
        source = download([url], out_file) if url else ""
        if source:
            manifest["leagues"][lid] = {"path": f"assets/leagues/{safe_name(lid)}.jpg", "status": "refreshed" if refresh_existing else "downloaded", "source": source}
        else:
            out_file.unlink(missing_ok=True)
            manifest["leagues"][lid] = {"path": "assets/leagues/na.svg", "status": "fallback"}
        if i % 25 == 0:
            print(f"Leagues {i}/{len(ids)}")
    (out_dir / "manifest.json").write_text(json.dumps(manifest, separators=(",", ":")), encoding="utf-8")
    return len(ids)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0, help="Player-only test limit.")
    parser.add_argument("--refresh-existing", action="store_true", help="Replace existing cached images.")
    args = parser.parse_args()
    app = load_app()
    print("players:", refresh_players(app, args.refresh_existing, args.limit))
    print("managers:", refresh_managers(app, args.refresh_existing))
    print("leagues:", refresh_leagues(app, args.refresh_existing))
    print("4MANS image refresh complete")


if __name__ == "__main__":
    main()
