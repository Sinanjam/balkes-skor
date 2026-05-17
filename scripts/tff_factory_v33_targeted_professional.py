#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Balkes TFF Factory v3.3 — targeted senior professional results.

v3.3 keeps v2.9's fast legacy probe and per-URL timeout behaviour, but changes
how the senior/professional guard is applied:

- Match detail validation rejects youth/PAF/academy/BAL/women/futsal records.
- The factory itself no longer suppresses an entire season merely because a raw
  legacy page exposed many mixed-team rows; post-run cleaning decides using the
  filtered senior professional data.
- The chain/manual workflows can optionally reset all data before a rebuild.
"""
from __future__ import annotations

from typing import Any

# Importing v29 patches base.fetch and the safe legacy pageID probe.
import tff_factory_v29_speed_complete_accuracy  # noqa: F401
import tff_factory as base

base.FACTORY_VERSION = "v3.3-targeted-senior-professional"

BANNED_COMPETITION_TOKENS = (
    "u21", "u 21", "paf", "a2 ligi", "akademi", "gelisim", "gelişim", "elit u",
    "u19", "u 19", "u18", "u 18", "u17", "u 17", "u16", "u 16", "u15", "u 15",
    "u14", "u 14", "bolgesel amator", "bölgesel amatör", "bal takimi", "bal takımı",
    "rezerv", "kadin", "kadın", "futsal",
)

PROFESSIONAL_SIGNALS = (
    "profesyonel takim", "profesyonel takım",
    "super lig", "süper lig", "spor toto super lig", "spor toto süper lig",
    "1 lig", "1.lig", "1lig", "1. lig",
    "2 lig", "2.lig", "2lig", "2. lig",
    "3 lig", "3.lig", "3lig", "3. lig",
    "turkiye kupasi", "türkiye kupası", "ziraat turkiye kupasi", "ziraat türkiye kupası",
    "play off musabakalari", "play-off müsabakaları", "play off müsabakaları",
)


def _joined_competition_text(detail: dict[str, Any]) -> str:
    parts = [
        detail.get("competition"), detail.get("competitionLabel"), detail.get("league"),
        detail.get("stage"), detail.get("stageLabel"), detail.get("category"),
    ]
    src = detail.get("source") or {}
    if isinstance(src, dict):
        parts.extend([src.get("competition"), src.get("title"), src.get("name")])
    return " | ".join(str(p or "") for p in parts if p is not None)


def is_senior_professional_competition(value: Any) -> bool:
    n = base.norm(value)
    if not n:
        return False
    if any(base.norm(tok) in n for tok in BANNED_COMPETITION_TOKENS):
        return False
    return any(base.norm(sig) in n for sig in PROFESSIONAL_SIGNALS)


_original_detail_valid = base.detail_is_valid_for_season


def detail_is_valid_for_season_v33(detail: dict[str, Any], season: str, seed: dict[str, Any]) -> tuple[bool, str]:
    ok, reason = _original_detail_valid(detail, season, seed)
    if not ok:
        return ok, reason
    comp_text = _joined_competition_text(detail)
    if not is_senior_professional_competition(comp_text):
        return False, "not_target_senior_professional:" + str(comp_text)[:160]
    return True, "ok"


base.detail_is_valid_for_season = detail_is_valid_for_season_v33

if __name__ == "__main__":
    raise SystemExit(base.main())
