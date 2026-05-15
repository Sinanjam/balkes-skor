#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Balkes TFF Factory v3.2 — senior professional guard.

This wrapper keeps the v2.9 speed/legacy probe behaviour, but fixes the bad-data
failure seen in chained runs: old TFF pages can surface Balıkesirspor youth/PAF/
academy/BAL matches alongside the professional team. Those matches made some
seasons publish 150-250 matches.

v3.2 only publishes senior/professional-team matches. It also suppresses a season
instead of writing an empty or obviously partial season directory.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import shutil

# Importing v29 patches base.fetch and the safe legacy probe.
import tff_factory_v29_speed_complete_accuracy  # noqa: F401
import tff_factory as base

base.FACTORY_VERSION = "v3.2-senior-professional-guard"

BANNED_COMPETITION_TOKENS = (
    "u21", "u 21", "paf", "akademi", "gelisim", "gelişim", "elit u", "u19", "u 19",
    "u18", "u 18", "u17", "u 17", "u16", "u 16", "u15", "u 15", "u14", "u 14",
    "bolgesel amator", "bölgesel amatör", "bal takimi", "bal takımı", "rezerv",
    "kadin", "kadın", "futsal",
)

PROFESSIONAL_SIGNALS = (
    "profesyonel takim",
    "super lig",
    "spor toto super lig",
    "1 lig",
    "1lig",
    "2 lig",
    "2lig",
    "3 lig",
    "3lig",
    "turkiye kupasi",
    "play off musabakalari",
)

MIN_PUBLISH_MATCHES = 8
MIN_PUBLISH_LEAGUE_MATCHES = 8
MAX_REASONABLE_MATCHES = 80


def is_senior_professional_competition(value: Any) -> bool:
    n = base.norm(value)
    if not n:
        return False
    if any(base.norm(tok) in n for tok in BANNED_COMPETITION_TOKENS):
        return False
    if "profesyonel takim" in n:
        return True
    if "turkiye kupasi" in n:
        return True
    if "play off" in n and "lig" in n:
        return True
    # Some old pages may not include the explicit "Profesyonel Takım" suffix.
    return any(sig in n for sig in PROFESSIONAL_SIGNALS)


def detail_is_senior_professional(detail: dict[str, Any]) -> tuple[bool, str]:
    competition = detail.get("competition") or detail.get("competitionLabel") or ""
    if is_senior_professional_competition(competition):
        return True, "ok"
    return False, "not_senior_professional_competition:" + str(competition)[:120]


_original_detail_valid = base.detail_is_valid_for_season


def detail_is_valid_for_season_v32(detail: dict[str, Any], season: str, seed: dict[str, Any]) -> tuple[bool, str]:
    ok, reason = _original_detail_valid(detail, season, seed)
    if not ok:
        return ok, reason
    ok2, reason2 = detail_is_senior_professional(detail)
    if not ok2:
        return False, reason2
    return True, "ok"


def _read_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default
    return default


def _write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _match_type(m: dict[str, Any]) -> str:
    return str(m.get("matchType") or m.get("type") or "league")


def _score_played(m: dict[str, Any]) -> bool:
    score = m.get("score") or {}
    return bool(score.get("played"))


def _season_quality_from_disk(data_root: Path, season: str) -> tuple[bool, dict[str, Any]]:
    season_dir = data_root / "seasons" / season
    index_path = season_dir / "matches_index.json"
    index = _read_json(index_path, [])
    if not isinstance(index, list):
        return False, {"reason": "matches_index_not_list"}
    total = len(index)
    league = sum(1 for m in index if _match_type(m) == "league")
    played = sum(1 for m in index if _score_played(m))
    comps = sorted({str(m.get("competition") or "") for m in index})
    bad_comps = [c for c in comps if c and not is_senior_professional_competition(c)]
    ok = True
    reasons: list[str] = []
    if total <= 0:
        ok = False; reasons.append("empty_season")
    if total > MAX_REASONABLE_MATCHES:
        ok = False; reasons.append(f"too_many_matches:{total}")
    if total < MIN_PUBLISH_MATCHES:
        ok = False; reasons.append(f"too_few_matches:{total}")
    if league < MIN_PUBLISH_LEAGUE_MATCHES:
        ok = False; reasons.append(f"too_few_league_matches:{league}")
    if bad_comps:
        ok = False; reasons.append("non_senior_competitions_present")
    return ok, {"total": total, "league": league, "played": played, "badCompetitions": bad_comps[:20], "reasons": reasons}


_original_process_season = base.process_season


def process_season_v32(item: dict[str, Any], args: Any, seed: dict[str, Any]) -> dict[str, Any]:
    rep = _original_process_season(item, args, seed)
    season = rep.get("season") or item.get("season")
    if not season or rep.get("skipped"):
        return rep
    data_root = Path(args.data_root)
    reports_root = Path(args.reports_root)
    ok, quality = _season_quality_from_disk(data_root, str(season))
    rep["seniorProfessionalGuard"] = quality
    if not ok:
        season_dir = data_root / "seasons" / str(season)
        if season_dir.exists():
            shutil.rmtree(season_dir)
        rep["publicationSuppressed"] = True
        rep["suppressedReason"] = ";".join(quality.get("reasons") or ["senior_guard_failed"])
        rep["matchesPublished"] = 0
        base.log(f"{season}: v3.2 senior guard yayını bastırdı -> {rep['suppressedReason']}")
        _write_json(reports_root / "seasons" / f"{season}_quality.json", rep)
    return rep


base.detail_is_valid_for_season = detail_is_valid_for_season_v32
base.process_season = process_season_v32

if __name__ == "__main__":
    raise SystemExit(base.main())
