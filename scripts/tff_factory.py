#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Balkes TFF Factory v2.2 manual clean-db

Amaç:
- Otomatik cron yok; workflow manuel çalışır.
- Bir run içinde birden fazla sezon taranır.
- Clean database modunda data/ sıfırdan kurulur.
- TFF-only veri üretir.
- Raw HTML repo'ya commitlenmez, artifact olur.
- Encoding bozukluklarına toleranslı Balıkesirspor tespiti yapar.
- Sezon/tarih guard ile yanlış sezon karışmasını engeller.
- Duplicate yazmaz, şüpheli kayıtları raporlar.
- Detay parser: skor/tarih/takım/hakem/kadro/olay için en iyi çaba + sections_raw.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import time
import unicodedata
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Any

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

TFF = "https://www.tff.org/Default.aspx"
FACTORY_VERSION = "v2.2-manual-clean-db"


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def read_json(path: Path | str, default: Any = None) -> Any:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path | str, obj: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def tff_url(**params: Any) -> str:
    return TFF + "?" + urllib.parse.urlencode(params)


def decode_bytes(raw: bytes, content_type: str = "") -> str:
    encs = []
    m = re.search(r"charset=([A-Za-z0-9_\-]+)", content_type or "", re.I)
    if m:
        encs.append(m.group(1))
    head = raw[:4096].decode("ascii", errors="ignore")
    m2 = re.search(r"charset=['\"]?([A-Za-z0-9_\-]+)", head, re.I)
    if m2:
        encs.append(m2.group(1))
    encs.extend(["utf-8", "windows-1254", "iso-8859-9", "latin-1"])
    best = ""
    best_bad = 10**9
    for enc in dict.fromkeys(encs):
        try:
            s = raw.decode(enc, errors="replace")
            bad = s.count("\ufffd") + s.count("ï¿½") * 2
            if bad < best_bad:
                best, best_bad = s, bad
        except Exception:
            continue
    return best or raw.decode("utf-8", errors="replace")


def fetch(url: str, path: Path, sleep_s: float = 1.5, force: bool = False) -> tuple[bool, str]:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 200 and not force:
        return True, path.read_text(encoding="utf-8", errors="replace")

    last_error = ""
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 BalkesTFFFactory-v22/1.0",
                "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
            })
            with urllib.request.urlopen(req, timeout=75) as res:
                body = res.read()
                content_type = res.headers.get("Content-Type", "")
            text = decode_bytes(body, content_type)
            path.write_text(text, encoding="utf-8")
            time.sleep(sleep_s)
            return True, text
        except Exception as exc:
            last_error = str(exc)
            log(f"fetch hata {attempt}/3: {url} -> {last_error}")
            time.sleep(max(2.0, sleep_s * attempt))
    path.with_suffix(path.suffix + ".error.txt").write_text(last_error, encoding="utf-8")
    return False, ""


def fix_mojibake(s: Any) -> str:
    s = str(s or "")
    # Replacement karakterlerini kaybetmeden arama için sadeleştir.
    s = s.replace("ï¿½", "i").replace("\ufffd", "i").replace("�", "i")
    # Bazı klasik mojibake dönüşümleri.
    replacements = {
        "Ä°": "İ", "Ä±": "ı", "ÅŸ": "ş", "Åž": "Ş", "ÄŸ": "ğ", "Äž": "Ğ",
        "Ã¼": "ü", "Ãœ": "Ü", "Ã¶": "ö", "Ã–": "Ö", "Ã§": "ç", "Ã‡": "Ç",
    }
    for a, b in replacements.items():
        s = s.replace(a, b)
    return s


def norm(s: Any) -> str:
    s = fix_mojibake(s).lower().strip()
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = s.translate(str.maketrans({
        "ı": "i", "İ": "i", "ğ": "g", "Ğ": "g", "ü": "u", "Ü": "u",
        "ş": "s", "Ş": "s", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c"
    }))
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def is_balkes(s: Any) -> bool:
    n = norm(s)
    if "balkes" in n:
        return True
    if "balikesirspor" in n or "balikesir spor" in n:
        return True
    # Bozuk encoding: BALIKES�RSPOR -> balikesirspor veya balikes ispor/rspor.
    if "balikes" in n and ("spor" in n or "futbol" in n):
        return True
    return False


def text_from_html(raw: str) -> str:
    if BeautifulSoup:
        soup = BeautifulSoup(raw, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        raw = soup.get_text("\n")
    else:
        raw = re.sub(r"<[^>]+>", "\n", raw)
    lines = []
    for line in raw.splitlines():
        line = re.sub(r"\s+", " ", html.unescape(fix_mojibake(line))).strip()
        if line:
            lines.append(line)
    return "\n".join(lines)


def soup_from_html(raw: str):
    if not BeautifulSoup:
        return None
    return BeautifulSoup(raw, "html.parser")


def extract_ids(raw: str, key: str = "macId") -> list[str]:
    return sorted(set(re.findall(rf"(?:[?&]|){re.escape(key)}=(\d+)", raw, re.I)), key=lambda x: int(x))


def extract_param(raw: str, key: str) -> list[str]:
    return sorted(set(re.findall(rf"[?&]{re.escape(key)}=(\d+)", raw, re.I)), key=lambda x: int(x))


def extract_balkes_ids_near_link(raw: str, window: int = 2200) -> list[str]:
    found = []
    for m in re.finditer(r"(?:[?&]|)macId=(\d+)", raw, re.I):
        ctx = raw[max(0, m.start() - window):min(len(raw), m.end() + window)]
        if is_balkes(ctx):
            found.append(m.group(1))
    return sorted(set(found), key=lambda x: int(x))


def parse_score(s: str) -> tuple[int, int, str] | None:
    m = re.search(r"\b(\d{1,2})\s*[-–]\s*(\d{1,2})\b", s)
    if not m:
        return None
    h, a = int(m.group(1)), int(m.group(2))
    return h, a, f"{h}-{a}"


def parse_date_any(s: str) -> str:
    s = fix_mojibake(s)
    # dd.mm.yyyy
    m = re.search(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d).isoformat()
        except Exception:
            return ""
    # yyyy-mm-dd
    m = re.search(r"\b(\d{4})-(\d{1,2})-(\d{1,2})\b", s)
    if m:
        try:
            return date(int(m.group(1)), int(m.group(2)), int(m.group(3))).isoformat()
        except Exception:
            return ""
    return ""


def parse_time_any(s: str) -> str:
    m = re.search(r"\b([01]?\d|2[0-3])[:.](\d{2})\b", s)
    return f"{int(m.group(1)):02d}:{m.group(2)}" if m else ""


def season_bounds(season: str, seed: dict[str, Any]) -> tuple[str, str]:
    guard = (seed.get("seasonDateGuard") or {}).get(season) or {}
    if guard.get("start") and guard.get("end"):
        return guard["start"], guard["end"]
    y = int(season[:4])
    return f"{y}-07-01", f"{y+1}-06-30"


def date_in_season(iso_date: str, season: str, seed: dict[str, Any]) -> bool:
    if not iso_date:
        return False
    start, end = season_bounds(season, seed)
    return start <= iso_date <= end


def classify_type(*parts: Any) -> tuple[str, str]:
    n = norm(" ".join(str(x or "") for x in parts))
    if any(k in n for k in ["ziraat", "turkiye kupasi", "turkish cup", "ztk", " kupa "]):
        return "cup", "Ziraat Türkiye Kupası"
    if any(k in n for k in ["play off", "playoff", "play offs", "playoffs"]):
        return "playoff", "Play-off"
    if any(k in n for k in ["hazirlik", "friendly"]):
        return "friendly_or_unknown", "Hazırlık/Bilinmeyen"
    return "league", "Lig"


def likely_team_lines(lines: list[str]) -> list[str]:
    bad = ["tff", "tam saha", "anasayfa", "haber", "istatistik", "detay", "profesyonel", "amatör", "fikstür", "puan"]
    out = []
    for line in lines:
        n = norm(line)
        if len(line) < 3 or len(line) > 90:
            continue
        if any(b in n for b in bad):
            continue
        if re.search(r"\d", line) and not is_balkes(line):
            continue
        if len(re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]", line)) >= 4:
            out.append(line)
    return out


def teams_near_score(txt: str) -> tuple[str, str]:
    lines = [x for x in txt.splitlines() if x.strip()]
    for i, line in enumerate(lines):
        if parse_score(line):
            before = likely_team_lines(lines[max(0, i - 10):i])
            after = likely_team_lines(lines[i + 1:i + 11])
            if before and after:
                return before[-1], after[0]
    # Alternatif: aynı blokta Balıkesirspor ve diğer takım.
    candidates = likely_team_lines(lines[:80])
    for i, line in enumerate(candidates):
        if is_balkes(line):
            if i > 0:
                return candidates[i - 1], line
            if i + 1 < len(candidates):
                return line, candidates[i + 1]
    return "", ""


def parse_match_code(txt: str) -> str:
    m = re.search(r"(?:Müsabaka|Musabaka|Maç|Mac)\s*Kodu\s*:?\s*(\d+)", txt, re.I)
    return m.group(1) if m else ""


def parse_officials(txt: str) -> list[dict[str, str]]:
    officials = []
    patterns = [
        ("referee", r"\bHakem\s*:?\s*([A-ZÇĞİÖŞÜa-zçğıöşü .'-]{4,80})"),
        ("assistant1", r"(?:1\.?\s*Yardımcı Hakem|1\.?\s*Yardimci Hakem)\s*:?\s*([A-ZÇĞİÖŞÜa-zçğıöşü .'-]{4,80})"),
        ("assistant2", r"(?:2\.?\s*Yardımcı Hakem|2\.?\s*Yardimci Hakem)\s*:?\s*([A-ZÇĞİÖŞÜa-zçğıöşü .'-]{4,80})"),
        ("observer", r"\bGözlemci\s*:?\s*([A-ZÇĞİÖŞÜa-zçğıöşü .'-]{4,80})"),
    ]
    for role, pat in patterns:
        m = re.search(pat, txt, re.I)
        if m:
            name = re.sub(r"\s+", " ", m.group(1)).strip(" :-")
            officials.append({"role": role, "name": name})
    return officials


def parse_sections_raw(txt: str) -> dict[str, str]:
    # Parser'ın kaçırdığı bilgi kaybolmasın.
    sections = {}
    low = norm(txt)
    mapping = {
        "officials_raw": ["hakem", "gozlemci"],
        "lineups_raw": ["ilk 11", "yedek", "oyuncular"],
        "events_raw": ["sari kart", "kirmizi kart", "oyuncu degisikligi", "gol", " dk", "dakika"],
    }
    lines = txt.splitlines()
    for key, needles in mapping.items():
        hits = [line for line in lines if any(n in norm(line) for n in needles)]
        if hits:
            sections[key] = "\n".join(hits[:250])
    sections["full_text_excerpt"] = txt[:25000]
    return sections


def parse_events_best_effort(txt: str, home: str, away: str) -> list[dict[str, Any]]:
    events = []
    current_team = ""
    for line in txt.splitlines():
        n = norm(line)
        if is_balkes(line):
            current_team = home if is_balkes(home) else "Balıkesirspor"
        elif home and norm(home) in n:
            current_team = home
        elif away and norm(away) in n:
            current_team = away

        minute_match = re.search(r"\b(\d{1,3})\s*(?:\.?\s*dk|dakika|')\b", n)
        if not minute_match:
            continue
        minute = int(minute_match.group(1))

        typ = ""
        if "sari" in n and "kart" in n:
            typ = "yellow_card"
        elif "kirmizi" in n and "kart" in n:
            typ = "red_card"
        elif "oyundan cikan" in n or "cikti" in n:
            typ = "substitution_out"
        elif "oyuna giren" in n or "girdi" in n:
            typ = "substitution_in"
        elif "gol" in n:
            typ = "goal"
        if not typ:
            continue

        player = re.sub(r"\b\d{1,3}\s*(?:\.?\s*dk|dakika|')\b", "", line, flags=re.I)
        player = re.sub(r"(Sarı Kart|Sari Kart|Kırmızı Kart|Kirmizi Kart|Oyuna Giren|Oyundan Çıkan|Oyundan Cikan|Gol)", "", player, flags=re.I).strip(" :-")
        events.append({"type": typ, "minute": minute, "team": current_team, "player": player, "raw": line})
    return events


def parse_lineups_best_effort(txt: str, home: str, away: str) -> dict[str, Any]:
    # TFF'nin eski tabloları çok değişken. Temel oyuncu bloklarını raw olarak da saklıyoruz.
    sections = parse_sections_raw(txt)
    return {
        "home": {"team": home, "starting11": [], "substitutes": [], "raw": sections.get("lineups_raw", "")},
        "away": {"team": away, "starting11": [], "substitutes": [], "raw": sections.get("lineups_raw", "")},
    }


def parse_detail(mid: str, raw: str, season: str, source_url: str, seed: dict[str, Any]) -> dict[str, Any]:
    txt = text_from_html(raw)
    home, away = teams_near_score(txt)
    sc = parse_score(txt)
    match_date = parse_date_any(txt)
    match_time = parse_time_any(txt)
    mt, ml = classify_type(txt)

    if sc:
        h, a, display = sc
    else:
        h = a = None
        display = ""

    is_home = is_balkes(home)
    opponent = away if is_home else home
    gf = h if is_home else a
    ga = a if is_home else h
    result = ""
    try:
        result = "W" if gf > ga else "D" if gf == ga else "L"
    except Exception:
        pass

    sections = parse_sections_raw(txt)
    officials = parse_officials(txt)
    events = parse_events_best_effort(txt, home, away)
    lineups = parse_lineups_best_effort(txt, home, away)

    return {
        "id": str(mid),
        "matchCode": parse_match_code(txt),
        "season": season,
        "homeTeam": home,
        "awayTeam": away,
        "date": match_date,
        "time": match_time,
        "dateDisplay": " - ".join(x for x in [match_date, match_time] if x),
        "competition": "",
        "roundType": "",
        "week": "",
        "stage": "",
        "matchType": mt,
        "matchTypeLabel": ml,
        "score": {"home": h, "away": a, "display": display, "played": bool(display)},
        "balkes": {
            "isHome": is_home,
            "opponent": opponent,
            "goalsFor": gf,
            "goalsAgainst": ga,
            "result": result,
        },
        "officials": officials,
        "referees": officials,
        "lineups": lineups,
        "events": events,
        "sections_raw": sections,
        "quality": "B" if home and away and display and match_date else "D",
        "source": {"name": "TFF", "url": source_url, "retrievedAt": now(), "sourceType": "official_tff_match_detail"},
    }


def detail_is_valid_for_season(detail: dict[str, Any], season: str, seed: dict[str, Any]) -> tuple[bool, str]:
    txt = json.dumps(detail, ensure_ascii=False)
    if not is_balkes(txt):
        return False, "balkes_not_found"
    if not detail.get("date"):
        return False, "date_missing"
    if not date_in_season(detail["date"], season, seed):
        return False, f"date_out_of_season:{detail.get('date')}"
    if not detail.get("score", {}).get("display"):
        return False, "score_missing"
    if not detail.get("homeTeam") or not detail.get("awayTeam"):
        return False, "teams_missing"
    return True, "ok"


def fetch_detail_if_valid(mid: str, season: str, raw_root: Path, sleep_s: float, force: bool, seed: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    for source_url in [tff_url(pageID=29, macId=mid), tff_url(macId=mid, pageID=528)]:
        ok, raw = fetch(source_url, raw_root / season / "matches" / f"{mid}.html", sleep_s, force)
        if not ok:
            continue
        detail = parse_detail(mid, raw, season, source_url, seed)
        valid, reason = detail_is_valid_for_season(detail, season, seed)
        if valid:
            return detail, "ok"
        # Bir URL bozuk parse olduysa diğer formu da dene.
        last_reason = reason
    return None, locals().get("last_reason", "fetch_failed")


def row_team_and_numbers(cells: list[str]) -> tuple[str, list[int]]:
    joined = " ".join(cells)
    nums = [int(x) for x in re.findall(r"\b\d+\b", joined)]
    for cell in cells:
        if is_balkes(cell):
            return cell, nums
    candidates = []
    for cell in cells:
        n = norm(cell)
        if not n or n in {"takim", "takimlar", "o", "g", "b", "m", "a", "y", "av", "p", "puan"}:
            continue
        if re.fullmatch(r"[\d+\-–]+", cell):
            continue
        if len(re.findall(r"[A-Za-zÇĞİÖŞÜçğıöşü]", cell)) >= 3:
            candidates.append(cell)
    return (candidates[0] if candidates else ""), nums


def parse_standings(raw: str) -> list[dict[str, Any]]:
    if not BeautifulSoup:
        return []
    soup = BeautifulSoup(raw, "html.parser")
    tables = []
    for table in soup.find_all("table"):
        rows = []
        for tr in table.find_all("tr"):
            cells = [html.unescape(fix_mojibake(c.get_text(" ", strip=True))).strip() for c in tr.find_all(["td", "th"])]
            cells = [c for c in cells if c]
            if len(cells) < 3:
                continue
            team, nums = row_team_and_numbers(cells)
            if not team or len(nums) < 3:
                continue
            gf = nums[5] if len(nums) > 5 else 0
            ga = nums[6] if len(nums) > 6 else 0
            rows.append({
                "rank": nums[0] if nums else len(rows) + 1,
                "team": team,
                "played": nums[1] if len(nums) > 1 else 0,
                "won": nums[2] if len(nums) > 2 else 0,
                "drawn": nums[3] if len(nums) > 3 else 0,
                "lost": nums[4] if len(nums) > 4 else 0,
                "goalsFor": gf,
                "goalsAgainst": ga,
                "goalDifference": gf - ga,
                "points": nums[-1],
                "isBalkes": is_balkes(team),
            })
        # Takım tekrarlarını temizle.
        clean = []
        seen = set()
        for r in rows:
            k = norm(r["team"])
            if k in seen:
                continue
            seen.add(k)
            clean.append(r)
        if len(clean) >= 4:
            tables.append(clean)
    with_balkes = [t for t in tables if any(r.get("isBalkes") for r in t)]
    if with_balkes:
        return max(with_balkes, key=len)
    return max(tables, key=len) if tables else []


def discover(item: dict[str, Any], raw_root: Path, sleep_s: float) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    season = item["season"]
    selected: set[str] = set()
    all_ids: set[str] = set()
    standings_candidates = []

    for page_id in item.get("pageIds", []):
        page_url = tff_url(pageID=page_id)
        ok, raw = fetch(page_url, raw_root / season / "pages" / f"pageID_{page_id}.html", sleep_s)
        if not ok:
            continue
        all_ids.update(extract_ids(raw))
        selected.update(extract_balkes_ids_near_link(raw))
        table = parse_standings(raw)
        if table:
            standings_candidates.append({"pageID": page_id, "groupID": None, "week": None, "url": page_url, "standings": table})

        groups = extract_param(raw, "grupID")
        weeks = extract_param(raw, "hafta") + extract_param(raw, "haftaID") + extract_param(raw, "haftaNo")

        for gid in groups[:25]:
            group_url = tff_url(pageID=page_id, grupID=gid)
            ok2, group_raw = fetch(group_url, raw_root / season / "standings" / f"pageID_{page_id}_group_{gid}.html", sleep_s)
            if not ok2:
                continue
            all_ids.update(extract_ids(group_raw))
            selected.update(extract_balkes_ids_near_link(group_raw))
            table = parse_standings(group_raw)
            if table:
                standings_candidates.append({"pageID": page_id, "groupID": gid, "week": None, "url": group_url, "standings": table})

            if not item.get("tryWeeklyStandings", True):
                continue
            candidate_weeks = sorted(set(
                weeks + extract_param(group_raw, "hafta") + extract_param(group_raw, "haftaID") +
                extract_param(group_raw, "haftaNo") + [str(x) for x in range(1, 41)]
            ), key=lambda x: int(x))
            seen_table_hashes = set()
            for week in candidate_weeks:
                week_url = tff_url(pageID=page_id, grupID=gid, hafta=week)
                ok3, week_raw = fetch(week_url, raw_root / season / "standings" / f"pageID_{page_id}_group_{gid}_week_{week}.html", sleep_s)
                if not ok3:
                    continue
                table = parse_standings(week_raw)
                if not table:
                    continue
                h = hashlib.sha1(json.dumps(table, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
                if h in seen_table_hashes:
                    continue
                seen_table_hashes.add(h)
                standings_candidates.append({"pageID": page_id, "groupID": gid, "week": int(week), "url": week_url, "standings": table})

    return sorted(selected, key=lambda x: int(x)), sorted(all_ids, key=lambda x: int(x)), standings_candidates


def match_signature(match: dict[str, Any]) -> str:
    b = match.get("balkes") or {}
    score = match.get("score") or {}
    opponent = b.get("opponent") or match.get("awayTeam") or match.get("homeTeam") or ""
    return "|".join([
        str(match.get("date") or ""),
        norm(opponent),
        "home" if b.get("isHome") else "away",
        str(score.get("display") or ""),
    ])


def index_from_detail(detail: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "id", "matchCode", "season", "competition", "roundType", "week", "stage",
        "date", "time", "dateDisplay", "homeTeam", "awayTeam", "matchType",
        "matchTypeLabel", "score", "balkes", "quality"
    ]
    out = {k: detail.get(k) for k in keys if detail.get(k) not in (None, "", {}, [])}
    out["detailUrl"] = f"seasons/{detail['season']}/matches/{detail['id']}.json"
    out["source"] = detail["source"]
    return out


def process_season(item: dict[str, Any], args: argparse.Namespace, seed: dict[str, Any]) -> dict[str, Any]:
    season = item["season"]
    data_root = Path(args.data_root)
    raw_root = Path(args.raw_root)
    reports_root = Path(args.reports_root)

    log(f"=== {season} başladı ===")
    selected, all_ids, standings_candidates = discover(item, raw_root, args.sleep)

    queue = set(selected) | {str(x) for x in item.get("knownMatchIds", [])}
    # Clean DB'de asıl güvenilir yol: tüm keşfedilenleri detay sayfasında doğrulamak.
    candidates = sorted((set(all_ids) | queue), key=lambda x: int(x))
    if args.max_discovery_probe > 0:
        candidates = candidates[:args.max_discovery_probe]

    log(f"{season}: selectedIds={len(selected)}, allDiscoveredIds={len(all_ids)}, detailCandidates={len(candidates)}")

    season_dir = data_root / "seasons" / season
    matches_dir = season_dir / "matches"
    matches_dir.mkdir(parents=True, exist_ok=True)

    by_id: dict[str, dict[str, Any]] = {}
    duplicate_candidates = []
    rejected = {}
    for i, mid in enumerate(candidates, start=1):
        detail, reason = fetch_detail_if_valid(mid, season, raw_root, args.sleep, args.force, seed)
        if detail:
            by_id[str(mid)] = detail
        else:
            rejected[reason] = rejected.get(reason, 0) + 1
        if i % 50 == 0:
            log(f"{season}: detail doğrulama {i}/{len(candidates)}, hits={len(by_id)}")

    # Duplicate engeli: aynı maç imzası gelirse daha zengin olanı tut.
    by_sig: dict[str, dict[str, Any]] = {}
    for mid, detail in by_id.items():
        sig = match_signature(detail)
        if sig in by_sig:
            old = by_sig[sig]
            duplicate_candidates.append({"kept": old["id"], "dropped": mid, "signature": sig})
            if len(json.dumps(detail, ensure_ascii=False)) > len(json.dumps(old, ensure_ascii=False)):
                by_sig[sig] = detail
        else:
            by_sig[sig] = detail

    final_details = sorted(by_sig.values(), key=lambda m: (m.get("date") or "", int(str(m.get("id") or 0))))
    for detail in final_details:
        write_json(matches_dir / f"{detail['id']}.json", detail)

    index_arr = [index_from_detail(d) for d in final_details]
    write_json(season_dir / "matches_index.json", index_arr)

    selected_tables = []
    for candidate in standings_candidates:
        table = candidate.get("standings") or []
        if any(row.get("isBalkes") for row in table):
            selected_tables.append({
                "week": candidate.get("week") or len(selected_tables) + 1,
                "source": {"name": "TFF", "url": candidate["url"], "retrievedAt": now(), "sourceType": "official_tff_standings"},
                "pageID": candidate.get("pageID"),
                "groupID": candidate.get("groupID"),
                "standings": table,
            })

    if selected_tables:
        uniq = {}
        for x in selected_tables:
            h = hashlib.sha1(json.dumps(x["standings"], ensure_ascii=False, sort_keys=True).encode()).hexdigest()
            uniq[h] = x
        write_json(season_dir / "standings_by_week.json", sorted(uniq.values(), key=lambda x: int(x["week"])))
    else:
        write_json(season_dir / "standings_by_week.json", [])

    type_counts = {}
    wins = draws = losses = gf = ga = 0
    for m in index_arr:
        mt = m.get("matchType") or "league"
        type_counts[mt] = type_counts.get(mt, 0) + 1
        b = m.get("balkes") or {}
        if b.get("result") == "W":
            wins += 1
        elif b.get("result") == "D":
            draws += 1
        elif b.get("result") == "L":
            losses += 1
        try:
            gf += int(b.get("goalsFor") or 0)
            ga += int(b.get("goalsAgainst") or 0)
        except Exception:
            pass

    season_json = {
        "id": season,
        "name": season,
        "competition": "",
        "sourcePolicy": "TFF-only",
        "factoryVersion": FACTORY_VERSION,
        "updatedAt": now(),
        "summary": {
            "matches": len(index_arr),
            "wins": wins,
            "draws": draws,
            "losses": losses,
            "goalsFor": gf,
            "goalsAgainst": ga,
            "goalDifference": gf - ga,
            "matchTypes": type_counts,
        },
        "files": {
            "matchesIndex": f"seasons/{season}/matches_index.json",
            "standingsByWeek": f"seasons/{season}/standings_by_week.json",
        },
    }
    write_json(season_dir / "season.json", season_json)

    quality = {
        "season": season,
        "selectedIds": len(selected),
        "allDiscoveredIds": len(all_ids),
        "detailCandidates": len(candidates),
        "matchesPublished": len(index_arr),
        "detailFiles": len(list(matches_dir.glob("*.json"))),
        "duplicatesDropped": len(duplicate_candidates),
        "rejectedReasons": rejected,
        "standingsSnapshots": len(selected_tables),
        "balkesTableFound": bool(selected_tables),
        "matchTypeCounts": type_counts,
        "seasonGuard": {"start": season_bounds(season, seed)[0], "end": season_bounds(season, seed)[1]},
        "generatedAt": now(),
    }
    write_json(reports_root / "seasons" / f"{season}_quality.json", quality)
    if duplicate_candidates:
        write_json(reports_root / "seasons" / f"{season}_duplicate_candidates.json", duplicate_candidates)
    return quality


def build_manifest(data_root: Path, processed_seasons: list[str]) -> None:
    available = []
    for p in sorted((data_root / "seasons").glob("*/matches_index.json"), reverse=True):
        arr = read_json(p, [])
        if isinstance(arr, list) and len(arr) > 0:
            sid = p.parent.name
            available.append({"id": sid, "name": sid, "matchCount": len(arr)})

    manifest = {
        "app": "Balkes Skor",
        "schemaVersion": 3,
        "dataVersion": 1,
        "appVersion": "0.5.0-beta-debug",
        "generatedAt": now(),
        "team": "Balıkesirspor",
        "assets": {"logo": "assets/logo_balkes_skor.png"},
        "availableSeasons": available,
        "global": {
            "playersIndexUrl": "players_index.json",
            "opponentsIndexUrl": "opponents_index.json",
            "searchIndexUrl": "search_index.json",
            "dataReportUrl": "data_report.json"
        },
        "appDataVersion": int(datetime.now().timestamp()),
        "appMinVersion": "0.5.0-beta-debug",
        "lastUpdated": now(),
        "dataBaseUrl": "https://raw.githubusercontent.com/Sinanjam/balkes-skor/main/data/",
        "factoryVersion": FACTORY_VERSION,
        "processedSeasonsInLastRun": processed_seasons,
    }
    write_json(data_root / "manifest.json", manifest)


def rebuild_global_indexes(data_root: Path) -> None:
    players = {}
    opponents = {}
    search = []
    for p in sorted((data_root / "seasons").glob("*/matches_index.json")):
        arr = read_json(p, [])
        if not isinstance(arr, list):
            continue
        for m in arr:
            if not isinstance(m, dict):
                continue
            b = m.get("balkes") or {}
            opp = b.get("opponent")
            if opp:
                key = norm(opp)
                item = opponents.setdefault(key, {"name": opp, "matches": 0})
                item["matches"] += 1
            search.append({
                "type": "match",
                "season": m.get("season"),
                "id": m.get("id"),
                "title": f"{m.get('homeTeam','')} {m.get('score',{}).get('display','')} {m.get('awayTeam','')}",
                "date": m.get("date"),
                "url": m.get("detailUrl"),
            })
    write_json(data_root / "players_index.json", [])
    write_json(data_root / "opponents_index.json", sorted(opponents.values(), key=lambda x: norm(x["name"])))
    write_json(data_root / "search_index.json", search)


def build_data_report(data_root: Path, reports_root: Path, processed: list[dict[str, Any]]) -> None:
    manifest = read_json(data_root / "manifest.json", {})
    seasons = manifest.get("availableSeasons", []) if isinstance(manifest, dict) else []
    total = sum(int(s.get("matchCount") or 0) for s in seasons if isinstance(s, dict))
    report = {
        "generatedAt": now(),
        "sourcePolicy": "TFF-only",
        "factoryVersion": FACTORY_VERSION,
        "totalAppMatches": total,
        "seasons": seasons,
        "playersIndexed": 0,
        "opponentsIndexed": len(read_json(data_root / "opponents_index.json", [])),
        "notes": [
            "Temiz database modu TFF resmi/açık sayfalarından yeniden kurar.",
            "Raw HTML repo'ya commitlenmez; GitHub Actions artifact olarak saklanır.",
            "Encoding bozuklukları ve sezon dışı maçlar için guard uygulanır.",
            "Hakkında metni APK içinde sabit kalacaktır."
        ],
    }
    write_json(data_root / "data_report.json", report)
    write_json(reports_root / "tff_factory_summary.json", {
        "generatedAt": now(),
        "status": "ok",
        "sourcePolicy": "TFF-only",
        "factoryVersion": FACTORY_VERSION,
        "processed": processed,
        "after": {"seasons": len(seasons), "matches": total},
        "safeToPush": True,
    })


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", default="sources/tff/registry/balkes_tff_seed_registry.json")
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--raw-root", default="sources/tff/raw")
    ap.add_argument("--reports-root", default="reports/tff_factory")
    ap.add_argument("--start-season", default="2025-2026")
    ap.add_argument("--max-seasons", type=int, default=3)
    ap.add_argument("--sleep", type=float, default=1.5)
    ap.add_argument("--max-discovery-probe", type=int, default=1500)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    seed = read_json(args.seed, {})
    by = {s["season"]: s for s in seed.get("seasons", []) if isinstance(s, dict) and s.get("season")}
    queue = []
    seen = False
    for sid in seed.get("runOrder", []):
        if sid == args.start_season:
            seen = True
        if seen and sid in by:
            queue.append(by[sid])
    queue = queue[:max(1, args.max_seasons)]
    if not queue:
        raise SystemExit(f"start-season bulunamadı: {args.start_season}")

    log("queue=" + ", ".join(x["season"] for x in queue))
    processed = []
    for item in queue:
        processed.append(process_season(item, args, seed))

    processed_seasons = [x["season"] for x in processed]
    build_manifest(Path(args.data_root), processed_seasons)
    rebuild_global_indexes(Path(args.data_root))
    build_data_report(Path(args.data_root), Path(args.reports_root), processed)
    total_matches = sum(int(x.get("matchesPublished") or 0) for x in processed)
    if total_matches <= 0:
        raise SystemExit("HATA: Bu run hiç maç üretmedi; main'e basılmamalı.")
    log(f"DONE {FACTORY_VERSION}: processed={processed_seasons}, run_matches={total_matches}")


if __name__ == "__main__":
    main()
