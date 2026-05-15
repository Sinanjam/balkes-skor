#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Balkes TFF Factory v3.2 professional-team guard.

v2.9/v3.1 correctly found many Balıkesirspor-related TFF matches, but legacy
pages also expose U21, U19, PAF/academy/reserve team fixtures. That polluted
professional seasons with 150-250 matches. This wrapper keeps the v2.9 speed
and legacy branch guards, then adds a hard publication guard:

- match must be Balıkesirspor
- match date must belong to the requested season
- competition must be the professional-team competition
- youth/academy/reserve/PAF fixtures are rejected
"""
from __future__ import annotations

from typing import Any

# Importing v29 applies its fast fetch + legacy probe monkey patches.
import tff_factory_v29_speed_complete_accuracy  # noqa: F401
import tff_factory as base

base.FACTORY_VERSION = "v3.2-professional-team-guard"

YOUTH_MARKERS = {
    "u21", "u 21", "u19", "u 19", "u18", "u 18", "u17", "u 17",
    "elit akademi", "akademi", "paf", "genc", "genclik ligi", "rezerv",
    "bolgesel gelisim", "gelişim", "gelisim",
}


def _norm(value: Any) -> str:
    return base.norm(value)


def is_professional_competition(detail: dict[str, Any]) -> bool:
    comp_raw = str(detail.get("competition") or detail.get("competitionLabel") or "")
    comp = _norm(comp_raw)
    if not comp:
        return False
    if any(marker in comp for marker in YOUTH_MARKERS):
        return False
    # TFF detail pages for the senior team usually include this marker.
    if "profesyonel takim" in comp:
        return True
    # Some old cup labels may be shorter, but they should still not be youth.
    if "turkiye kupasi" in comp or "ziraat" in comp:
        return True
    # Do not accept ambiguous legacy labels: better to skip than pollute data.
    return False


def detail_is_valid_for_season_v32(detail: dict[str, Any], season: str, seed: dict[str, Any]) -> tuple[bool, str]:
    # First keep the base v2.9 guards: Balkes + date + teams.
    valid, reason = base._V32_ORIGINAL_DETAIL_VALIDATOR(detail, season, seed)  # type: ignore[attr-defined]
    if not valid:
        return valid, reason
    if not is_professional_competition(detail):
        return False, "non_professional_or_youth_competition:" + str(detail.get("competition") or "")[:120]
    return True, "ok"


if not hasattr(base, "_V32_ORIGINAL_DETAIL_VALIDATOR"):
    base._V32_ORIGINAL_DETAIL_VALIDATOR = base.detail_is_valid_for_season  # type: ignore[attr-defined]
base.detail_is_valid_for_season = detail_is_valid_for_season_v32

if __name__ == "__main__":
    raise SystemExit(base.main())
