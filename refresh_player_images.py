#!/usr/bin/env python3
"""
Download and freeze Sleeper player headshots for the current season.

Usage examples:
  python refresh_player_images.py
  python refresh_player_images.py --season 2026
  python refresh_player_images.py --season 2026 --limit 50

This script is designed for GitHub Actions and uses only the Python standard library.
It reads player IDs from 4mans_app_data.json when available so it only downloads the
players relevant to 4MANS.
"""

import argparse
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.sleeper.app/v1"
HEADSHOT_PATTERNS = [
    "https://sleepercdn.com/content/nfl/players/thumb/{player_id}.jpg",
    "https://sleepercdn.com/content/nfl/players/{player_id}.jpg",
]
FALLBACK_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" width="320" height="320" viewBox="0 0 320 320">
  <rect width="320" height="320" rx="24" fill="#f2f2ef"/>
  <circle cx="160" cy="118" r="58" fill="#d9d8d2"/>
  <path d="M62 278c8-56 50-86 98-86s90 30 98 86" fill="#d9d8d2"/>
  <text x="160" y="302" font-family="Arial, sans-serif" font-size="28" text-anchor="middle" fill="#6f716d">N/A</text>
</svg>
'''


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_json(url, tries=3, timeout=45):
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "4MANS-Images/1.0", "Accept": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as e:
            last = e
            if attempt < tries - 1:
                time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(f"GET failed: {url}\n{last}")


def fetch_bytes(url, timeout=45):
    req = urllib.request.Request(url, headers={"User-Agent": "4MANS-Images/1.0", "Accept": "image/*,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        ctype = r.headers.get_content_type() or ""
        data = r.read()
    return ctype, data


def ensure_fallback(out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    na = out_dir.parent / "na.svg"
    if not na.exists() or na.read_text(encoding="utf-8") != FALLBACK_SVG:
        na.write_text(FALLBACK_SVG, encoding="utf-8")
    return na


def load_target_player_ids(season: str, app_path="4mans_app_data.json"):
    path = Path(app_path)
    if path.exists():
        try:
            app = json.loads(path.read_text(encoding="utf-8"))
            s = ((app.get("seasons") or {}).get(str(season)) or {})
            pdir = s.get("player_directory") or {}
            if pdir:
                return sorted(pdir.keys(), key=lambda x: (not str(x).isdigit(), str(x)))
            ownership = s.get("ownership") or []
            ids = sorted({str(r.get("player_id")) for r in ownership if r.get("player_id")})
            if ids:
                return ids
        except Exception:
            pass
    # Fallback: use all active players from Sleeper (much larger).
    players = get_json(f"{API}/players/nfl?active=true", timeout=120)
    return sorted([str(pid) for pid in players.keys()], key=lambda x: (not str(x).isdigit(), str(x)))


def download_headshot(player_id: str, out_file: Path):
    for pattern in HEADSHOT_PATTERNS:
        url = pattern.format(player_id=player_id)
        try:
            ctype, data = fetch_bytes(url)
        except Exception:
            continue
        if not ctype.startswith("image/"):
            continue
        if not data or len(data) < 128:
            continue
        out_file.write_bytes(data)
        return url
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", default=str(datetime.now(timezone.utc).year))
    parser.add_argument("--limit", type=int, default=0)
    args = parser.parse_args()

    season = str(args.season)
    out_dir = Path("assets") / "players" / season
    ensure_fallback(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    player_ids = load_target_player_ids(season)
    if args.limit > 0:
        player_ids = player_ids[: args.limit]

    manifest_path = out_dir / "manifest.json"
    prior_manifest = {}
    if manifest_path.exists():
        try:
            prior_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except Exception:
            prior_manifest = {}

    manifest = {
        "generated_at": now_iso(),
        "season": season,
        "headshot_fallback": "assets/players/na.svg",
        "players": {},
    }

    ok = 0
    miss = 0
    skipped = 0
    for i, pid in enumerate(player_ids, 1):
        out_file = out_dir / f"{pid}.jpg"
        if out_file.exists() and out_file.stat().st_size > 128:
            manifest["players"][pid] = {
                "path": f"assets/players/{season}/{pid}.jpg",
                "status": "cached",
                "source": (prior_manifest.get("players") or {}).get(pid, {}).get("source", ""),
            }
            skipped += 1
            continue

        source = download_headshot(pid, out_file)
        if source:
            manifest["players"][pid] = {
                "path": f"assets/players/{season}/{pid}.jpg",
                "status": "downloaded",
                "source": source,
            }
            ok += 1
        else:
            if out_file.exists():
                out_file.unlink(missing_ok=True)
            manifest["players"][pid] = {
                "path": "assets/players/na.svg",
                "status": "fallback",
                "source": "",
            }
            miss += 1

        if i % 50 == 0:
            print(f"Processed {i}/{len(player_ids)}")

    manifest_path.write_text(json.dumps(manifest, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")

    print("\nHeadshot refresh complete")
    print("season:", season)
    print("target players:", len(player_ids))
    print("downloaded:", ok)
    print("already cached:", skipped)
    print("fallback only:", miss)
    print("manifest:", manifest_path)


if __name__ == "__main__":
    main()
