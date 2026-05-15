#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Balkes TFF Factory v2.8 hot wrapper.

Keeps v2.7 correctness rules, but fixes the real-world stall seen on legacy
TFF pages: some dead branches do not return HTTP 504 immediately; they hang
until urllib's long default timeout. This wrapper fast-skips unreachable HTTP
and network-timeout branches without imposing any season-wide duration/probe
limit.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import time
import urllib.error
import urllib.request

import tff_factory as base

base.FACTORY_VERSION = "v2.8-safe-legacy-fast-timeout-branch-guard"

LEGACY_FETCH_TIMEOUT_SECONDS = 12


def fetch_fast(url: str, path: Path, sleep_s: float = 1.0, force: bool = False) -> tuple[bool, str]:
    """Fast network guard for legacy archive runs.

    This does not cap a season or reduce validation. It only avoids waiting
    75s x 3 on URLs that are already unreachable. All accepted match details
    still pass Balıkesirspor + season-date validation inside tff_factory.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    base.FETCH_LAST_ERROR_BY_PATH[str(path)] = ""
    if path.exists() and path.stat().st_size > 200 and not force:
        return True, path.read_text(encoding="utf-8", errors="replace")

    last = ""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 BalkesTFFFactory-v28-fast-timeout/1.0",
            "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
        })
        with urllib.request.urlopen(req, timeout=LEGACY_FETCH_TIMEOUT_SECONDS) as res:
            body = res.read()
            ctype = res.headers.get("Content-Type", "")
        text = base.decode_bytes(body, ctype)
        path.write_text(text, encoding="utf-8")
        if sleep_s:
            # keep a small politeness sleep, but never let old workflow's 1.0s
            # make the dead-branch scan painfully slow.
            time.sleep(min(float(sleep_s or 0), 0.25))
        return True, text
    except urllib.error.HTTPError as exc:
        last = f"HTTP Error {exc.code}: {exc.reason}"
        base.FETCH_LAST_ERROR_BY_PATH[str(path)] = f"http_{exc.code}"
        base.log(f"fetch hızlı atla: {url} -> {last}")
    except Exception as exc:  # network timeout, reset, SSL, DNS, etc.
        last = str(exc)
        err_norm = last.lower()
        if "timed out" in err_norm or "timeout" in err_norm:
            base.FETCH_LAST_ERROR_BY_PATH[str(path)] = "timeout"
        else:
            base.FETCH_LAST_ERROR_BY_PATH[str(path)] = "error"
        base.log(f"fetch hızlı atla: {url} -> {last}")

    path.with_suffix(path.suffix + ".error.txt").write_text(last, encoding="utf-8")
    return False, ""


base.fetch = fetch_fast


def discover_legacy_pageid_probe_v28(item: dict[str, Any], raw_root: Path, sleep_s: float, force: bool = False):
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
        return base.is_gateway_fetch_error(err) or err == "error"

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
                    diag("page_fast_skip", page_id, err)
                continue

            sel_delta, all_delta = add_raw(raw)
            groups = base.extract_param(raw, "grupID")[:group_limit]
            page_hint = base.legacy_probe_should_expand_weeks(raw, len(selected) - sel_delta, selected)
            if sel_delta or page_hint:
                diag("page_hint", page_id, baseSelectedDelta=sel_delta, baseAllDelta=all_delta, groups=groups[:20])

            group_errors = 0
            for gid in groups:
                if group_errors >= skip_after:
                    diag("page_group_list_abandoned", page_id, "cumulative_unreachable_errors", gatewayErrors=group_errors)
                    break

                graw, gerr = fetch_once(f"pageID_{page_id}_group_{gid}", base.tff_url(pageID=page_id, grupID=gid))
                if not graw:
                    if is_bad(gerr):
                        group_errors += 1
                        diag("group_fast_skip", page_id, gerr, grupID=gid, cumulative=group_errors)
                    continue

                g_sel_delta, _ = add_raw(graw)
                expand = base.legacy_probe_should_expand_weeks(graw, len(selected) - g_sel_delta, selected)
                if not expand or max_week <= 0:
                    continue

                week_errors = 0
                for week in range(1, max_week + 1):
                    if week_errors >= skip_after:
                        diag("group_week_branch_abandoned", page_id, "cumulative_unreachable_errors", grupID=gid, gatewayErrors=week_errors)
                        break
                    wraw, werr = fetch_once(f"pageID_{page_id}_group_{gid}_week_{week:02d}", base.tff_url(pageID=page_id, grupID=gid, hafta=week))
                    if not wraw:
                        if is_bad(werr):
                            week_errors += 1
                            diag("group_week_fast_skip", page_id, werr, grupID=gid, week=week, cumulative=week_errors)
                        continue
                    add_raw(wraw)

            if not groups and page_hint and max_week > 0:
                page_week_errors = 0
                for week in range(1, max_week + 1):
                    if page_week_errors >= skip_after:
                        diag("page_week_branch_abandoned", page_id, "cumulative_unreachable_errors", gatewayErrors=page_week_errors)
                        break
                    wraw, werr = fetch_once(f"pageID_{page_id}_week_{week:02d}", base.tff_url(pageID=page_id, hafta=week))
                    if not wraw:
                        if is_bad(werr):
                            page_week_errors += 1
                            diag("page_week_fast_skip", page_id, werr, week=week, cumulative=page_week_errors)
                        continue
                    add_raw(wraw)

    return sorted(selected, key=lambda x: int(x)), sorted(all_ids, key=lambda x: int(x)), diagnostics


base.discover_legacy_pageid_probe = discover_legacy_pageid_probe_v28

if __name__ == "__main__":
    raise SystemExit(base.main())
