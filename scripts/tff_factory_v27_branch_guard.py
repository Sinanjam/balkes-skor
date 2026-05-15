#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any

import tff_factory as base

base.FACTORY_VERSION = "v2.7-safe-legacy-branch-abandon"


def discover_legacy_pageid_probe_v27(item: dict[str, Any], raw_root: Path, sleep_s: float, force: bool = False):
    season = item["season"]
    selected: set[str] = set()
    all_ids: set[str] = set()
    diagnostics: list[dict[str, Any]] = []
    ranges = base.legacy_probe_ranges(item)
    max_week = base.legacy_probe_max_week(item)
    group_limit = base.legacy_probe_group_limit(item)
    skip_after = base.legacy_probe_gateway_skip_after(item)
    seen_urls: set[str] = set()

    def add_raw(raw: str):
        before_sel = len(selected)
        before_all = len(all_ids)
        all_ids.update(base.extract_ids(raw))
        selected.update(base.extract_balkes_ids(raw))
        return len(selected) - before_sel, len(all_ids) - before_all

    def fetch_once(label: str, url: str):
        if url in seen_urls:
            return "", "seen"
        seen_urls.add(url)
        path = raw_root / season / "legacy_pageid_probe" / f"{label}.html"
        ok, raw = base.fetch(url, path, sleep_s, force)
        return (raw if ok else ""), base.FETCH_LAST_ERROR_BY_PATH.get(str(path), "")

    def is_bad(err: str) -> bool:
        return base.is_gateway_fetch_error(err)

    def diag(kind: str, page_id: int, err: str = "", **extra: Any):
        obj = {"kind": kind, "pageID": page_id}
        if err:
            obj["error"] = err
        obj.update(extra)
        diagnostics.append(obj)

    for start, end in ranges:
        for page_id in range(start, end + 1):
            raw, err = fetch_once(f"pageID_{page_id}", base.tff_url(pageID=page_id))
            if not raw:
                if is_bad(err):
                    diag("page_gateway_skip", page_id, err)
                continue

            sel_delta, all_delta = add_raw(raw)
            groups = base.extract_param(raw, "grupID")[:group_limit]
            page_hint = base.legacy_probe_should_expand_weeks(raw, len(selected) - sel_delta, selected)
            if sel_delta or page_hint:
                diag("page_hint", page_id, baseSelectedDelta=sel_delta, baseAllDelta=all_delta, groups=groups[:20])

            group_errors = 0
            for gid in groups:
                if group_errors >= skip_after:
                    diag("page_group_list_abandoned", page_id, "cumulative_gateway_errors", gatewayErrors=group_errors)
                    break

                graw, gerr = fetch_once(f"pageID_{page_id}_group_{gid}", base.tff_url(pageID=page_id, grupID=gid))
                if not graw:
                    if is_bad(gerr):
                        group_errors += 1
                        diag("group_gateway_skip", page_id, gerr, grupID=gid, cumulative=group_errors)
                    continue

                g_sel_delta, _ = add_raw(graw)
                expand = base.legacy_probe_should_expand_weeks(graw, len(selected) - g_sel_delta, selected)
                if not expand or max_week <= 0:
                    continue

                week_errors = 0
                for week in range(1, max_week + 1):
                    if week_errors >= skip_after:
                        diag("group_week_branch_abandoned", page_id, "cumulative_gateway_errors", grupID=gid, gatewayErrors=week_errors)
                        break
                    wraw, werr = fetch_once(f"pageID_{page_id}_group_{gid}_week_{week:02d}", base.tff_url(pageID=page_id, grupID=gid, hafta=week))
                    if not wraw:
                        if is_bad(werr):
                            week_errors += 1
                            diag("group_week_gateway_skip", page_id, werr, grupID=gid, week=week, cumulative=week_errors)
                        continue
                    add_raw(wraw)

            if not groups and page_hint and max_week > 0:
                page_week_errors = 0
                for week in range(1, max_week + 1):
                    if page_week_errors >= skip_after:
                        diag("page_week_branch_abandoned", page_id, "cumulative_gateway_errors", gatewayErrors=page_week_errors)
                        break
                    wraw, werr = fetch_once(f"pageID_{page_id}_week_{week:02d}", base.tff_url(pageID=page_id, hafta=week))
                    if not wraw:
                        if is_bad(werr):
                            page_week_errors += 1
                            diag("page_week_gateway_skip", page_id, werr, week=week, cumulative=page_week_errors)
                        continue
                    add_raw(wraw)

    return sorted(selected, key=lambda x: int(x)), sorted(all_ids, key=lambda x: int(x)), diagnostics


base.discover_legacy_pageid_probe = discover_legacy_pageid_probe_v27

if __name__ == "__main__":
    raise SystemExit(base.main())
