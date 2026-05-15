#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Standings Builder v3.1 chain-safe wrapper.

Adds two safety fixes over tff_standings_builder.py:
1) Do not build a full league table from already-published Balkes-only match JSON.
   This prevents fake standings when a season has no target TFF URL.
2) Use faster per-URL network guards for standings pages/details, so a chain job
   can skip dead TFF branches without waiting 75s x 3.

The scoring/penalty logic remains in the base builder.
"""
from __future__ import annotations

from pathlib import Path
import socket
import time
import urllib.error
import urllib.request

import tff_standings_builder as base

base.BUILDER_VERSION = "standings-builder-v3.1-chain-safe"

STANDINGS_PAGE_TIMEOUT_SECONDS = 10
DETAIL_TIMEOUT_SECONDS = 18
POLITE_SLEEP_SECONDS = 0.05
MIN_EXISTING_FULL_LEAGUE_MATCHES = 60
MAX_BALKES_MATCH_RATIO_FOR_FULL_TABLE = 0.60


def _path_timeout(path: Path) -> int:
    p = str(path)
    if "weekly_pages" in p or "official" in p or "standings_raw" in p:
        return STANDINGS_PAGE_TIMEOUT_SECONDS
    return DETAIL_TIMEOUT_SECONDS


def fetch_url_v31(url: str, path: Path, sleep_s: float = 0.8, force: bool = False):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 200 and not force:
        return True, path.read_text(encoding="utf-8", errors="replace")

    timeout = _path_timeout(path)
    last = ""
    # Two attempts are enough for flaky public HTML; long retry loops are handled
    # at the workflow group level by continuing to the next group.
    for attempt in range(1, 3):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 BalkesSkorStandingsBuilder-v31/1.0",
                "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
                "Connection": "close",
            })
            with urllib.request.urlopen(req, timeout=timeout) as res:
                raw = res.read()
                ctype = res.headers.get("Content-Type", "")
            text = base.decode_bytes(raw, ctype)
            path.write_text(text, encoding="utf-8")
            if sleep_s:
                time.sleep(min(float(sleep_s or 0), POLITE_SLEEP_SECONDS))
            return True, text
        except urllib.error.HTTPError as exc:
            last = f"HTTP Error {exc.code}: {exc.reason}"
            if int(getattr(exc, "code", 0) or 0) in {502, 503, 504}:
                base.log(f"standings fetch hızlı atla: {url} -> {last}")
                break
            base.log(f"standings fetch hata {attempt}/2: {url} -> {last}")
        except (TimeoutError, socket.timeout) as exc:
            last = f"timeout after {timeout}s: {exc}"
            base.log(f"standings fetch hızlı atla: {url} -> {last}")
            break
        except Exception as exc:  # noqa: BLE001
            last = str(exc)
            err_norm = last.lower()
            if "timed out" in err_norm or "timeout" in err_norm:
                base.log(f"standings fetch hızlı atla: {url} -> timeout after {timeout}s")
                break
            base.log(f"standings fetch hata {attempt}/2: {url} -> {last}")
        time.sleep(0.4 * attempt)

    path.with_suffix(path.suffix + ".error.txt").write_text(last, encoding="utf-8")
    return False, ""


_original_load_existing = base.load_existing_league_matches


def _is_balkes_match(match: dict) -> bool:
    return bool(base.is_balkes(match.get("homeTeam", "")) or base.is_balkes(match.get("awayTeam", "")))


def load_existing_league_matches_v31(data_root: Path, season: str, seed: dict):
    matches = _original_load_existing(data_root, season, seed)
    if not matches:
        return []

    teams = {
        base.norm(m.get("homeTeam", "")) for m in matches if m.get("homeTeam")
    } | {
        base.norm(m.get("awayTeam", "")) for m in matches if m.get("awayTeam")
    }
    teams = {t for t in teams if t}
    balkes_count = sum(1 for m in matches if _is_balkes_match(m))
    ratio = balkes_count / max(1, len(matches))

    # The TFF match factory publishes Balıkesirspor-focused data. A full league
    # standings table cannot be computed from only Balkes matches: it creates
    # fake ranks/points for opponents. Official target pages or full fixture
    # collection must be used instead.
    if len(matches) < MIN_EXISTING_FULL_LEAGUE_MATCHES or ratio >= MAX_BALKES_MATCH_RATIO_FOR_FULL_TABLE:
        base.log(
            f"{season}: mevcut maç JSON'u full lig tablosu için yetersiz; "
            f"matches={len(matches)} teams={len(teams)} balkesRatio={ratio:.2f}. "
            "Yanlış tablo yazmamak için atlandı."
        )
        return []
    return matches


base.fetch_url = fetch_url_v31
base.load_existing_league_matches = load_existing_league_matches_v31

if __name__ == "__main__":
    raise SystemExit(base.main())
