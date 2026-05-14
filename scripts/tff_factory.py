#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Balkes TFF Factory v2.2 no-standings fixed2

Bu sürümün hedefi:
- Puan tablosu/standings ÇEKMEZ.
- TFF maç detay sayfasından takım/skor/tarih alanlarını HTML id/class üzerinden parse eder.
- Önce selectedIds/knownIds adaylarını dener; selected yoksa allDiscovered fallback yapar.
- Non-Balkes adaylarını raporlayarak eler.
- Score span'leri ayrı ayrı geldiği için "2-1" regex'ine bağımlı kalmaz.
- Hiç maç üretmezse fail eder ve main'e boş data basmaz.
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
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Any

try:
    from bs4 import BeautifulSoup
except Exception:
    BeautifulSoup = None

TFF = "https://www.tff.org/Default.aspx"
FACTORY_VERSION = "v2.2-no-standings-fixed2"
TEAM_CANONICAL = "Balıkesirspor"


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
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


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
    encs.extend(["windows-1254", "iso-8859-9", "utf-8", "latin-1"])
    best, score = "", 10**9
    for enc in dict.fromkeys(encs):
        try:
            s = raw.decode(enc, errors="replace")
            bad = s.count("\ufffd") + s.count("ï¿½") * 2
            if bad < score:
                best, score = s, bad
        except Exception:
            pass
    return best or raw.decode("utf-8", errors="replace")


def fetch(url: str, path: Path, sleep_s: float = 1.0, force: bool = False) -> tuple[bool, str]:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size > 200 and not force:
        return True, path.read_text(encoding="utf-8", errors="replace")
    last = ""
    for attempt in range(1, 4):
        try:
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 BalkesTFFFactory-v22-fixed2/1.0",
                "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.7",
            })
            with urllib.request.urlopen(req, timeout=75) as res:
                body = res.read()
                ctype = res.headers.get("Content-Type", "")
            text = decode_bytes(body, ctype)
            path.write_text(text, encoding="utf-8")
            time.sleep(sleep_s)
            return True, text
        except Exception as exc:
            last = str(exc)
            log(f"fetch hata {attempt}/3: {url} -> {last}")
            time.sleep(max(2.0, sleep_s * attempt))
    path.with_suffix(path.suffix + ".error.txt").write_text(last, encoding="utf-8")
    return False, ""


def fix_mojibake(s: Any) -> str:
    s = str(s or "")
    s = s.replace("ï¿½", "İ").replace("\ufffd", "İ").replace("�", "İ")
    repl = {
        "Ä°": "İ", "Ä±": "ı", "ÅŸ": "ş", "Åž": "Ş", "ÄŸ": "ğ", "Äž": "Ğ",
        "Ã¼": "ü", "Ãœ": "Ü", "Ã¶": "ö", "Ã–": "Ö", "Ã§": "ç", "Ã‡": "Ç",
        "&nbsp;": " ",
    }
    for a, b in repl.items():
        s = s.replace(a, b)
    return html.unescape(s)


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
    if "balikes" in n and "spor" in n:
        return True
    return False


def clean_text(s: Any) -> str:
    return re.sub(r"\s+", " ", fix_mojibake(s)).strip()


def clean_team(s: Any) -> str:
    s = clean_text(s)
    if is_balkes(s):
        return TEAM_CANONICAL
    return s


def soup_from_html(raw: str):
    return BeautifulSoup(raw, "html.parser") if BeautifulSoup else None


def text_from_html(raw: str) -> str:
    soup = soup_from_html(raw)
    if soup:
        for t in soup(["script", "style", "noscript"]):
            t.decompose()
        return "\n".join(clean_text(x) for x in soup.get_text("\n").splitlines() if clean_text(x))
    raw = re.sub(r"<[^>]+>", "\n", raw)
    return "\n".join(clean_text(x) for x in raw.splitlines() if clean_text(x))


def extract_ids(raw: str, key: str = "macId") -> list[str]:
    return sorted(set(re.findall(rf"[?&]{re.escape(key)}=(\d+)", raw, re.I)), key=lambda x: int(x))


def extract_param(raw: str, key: str) -> list[str]:
    return sorted(set(re.findall(rf"[?&]{re.escape(key)}=(\d+)", raw, re.I)), key=lambda x: int(x))


def extract_balkes_ids(raw: str) -> list[str]:
    ids: set[str] = set()
    soup = soup_from_html(raw)
    if soup:
        for a in soup.find_all("a", href=True):
            href = html.unescape(a.get("href") or "")
            m = re.search(r"[?&]macId=(\d+)", href, re.I)
            if not m:
                continue
            parent = a.find_parent("tr") or a.find_parent(["div", "li", "p", "td"]) or a.parent
            ctx = clean_text(parent.get_text(" ", strip=True) if parent else a.get_text(" ", strip=True))
            # TFF bazı fikstür satırlarında link metni boş olabiliyor; küçük çevre fallback.
            if is_balkes(ctx):
                ids.add(m.group(1))
    # Eski sayfalarda soup parent yeterli değilse küçük pencere fallback.
    for m in re.finditer(r"[?&]macId=(\d+)", raw, re.I):
        ctx = raw[max(0, m.start() - 700): min(len(raw), m.end() + 700)]
        if is_balkes(ctx):
            ids.add(m.group(1))
    return sorted(ids, key=lambda x: int(x))


def parse_date_any(s: Any) -> str:
    s = fix_mojibake(s)
    m = re.search(r"\b(\d{1,2})[./](\d{1,2})[./](\d{4})\b", s)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(y, mo, d).isoformat()
        except Exception:
            return ""
    ay = {
        "ocak": 1, "subat": 2, "şubat": 2, "mart": 3, "nisan": 4, "mayis": 5, "mayıs": 5,
        "haziran": 6, "temmuz": 7, "agustos": 8, "ağustos": 8, "eylul": 9, "eylül": 9,
        "ekim": 10, "kasim": 11, "kasım": 11, "aralik": 12, "aralık": 12,
    }
    m = re.search(r"\b(\d{1,2})\s+([A-Za-zÇĞİÖŞÜçğıöşü]+)\s+(\d{4})\b", s)
    if m:
        d = int(m.group(1)); mon = norm(m.group(2)); y = int(m.group(3))
        if mon in ay:
            return date(y, ay[mon], d).isoformat()
    return ""


def parse_time_any(s: Any) -> str:
    s = fix_mojibake(s)
    # Tarih içindeki 07.09 gibi parçaları saat sanmamak için önce "tarih - saat" formunu yakala.
    m = re.search(r"\b\d{1,2}[./]\d{1,2}[./]\d{4}\s*[-–]\s*([01]?\d|2[0-3])[:.](\d{2})\b", s)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    # Genel saat formu: nokta yerine tercihen iki nokta üst üste.
    m = re.search(r"\b([01]?\d|2[0-3]):(\d{2})\b", s)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    # Noktalı saat için tarih biçimiyle çakışmayan durumları al.
    cleaned = re.sub(r"\b\d{1,2}[./]\d{1,2}[./]\d{4}\b", " ", s)
    m = re.search(r"\b([01]?\d|2[0-3])\.(\d{2})\b", cleaned)
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
    a, b = season_bounds(season, seed)
    return a <= iso_date <= b


def classify_type(*parts: Any) -> tuple[str, str]:
    n = norm(" ".join(str(x or "") for x in parts))
    if any(k in n for k in ["ziraat", "turkiye kupasi", "ztk", "kupa"]):
        return "cup", "Ziraat Türkiye Kupası"
    if any(k in n for k in ["play off", "playoff", "play offs", "playoffs"]):
        return "playoff", "Play-off"
    if "hazirlik" in n or "friendly" in n:
        return "friendly_or_unknown", "Hazırlık/Bilinmeyen"
    return "league", "Lig"


def first_by_id_contains(soup, token: str):
    if not soup:
        return None
    token = token.lower()
    for tag in soup.find_all(True):
        tid = " ".join([str(tag.get("id") or ""), " ".join(tag.get("class") or [])]).lower()
        if token in tid:
            return tag
    return None


def all_by_id_contains(soup, token: str):
    if not soup:
        return []
    token = token.lower()
    out = []
    for tag in soup.find_all(True):
        tid = " ".join([str(tag.get("id") or ""), " ".join(tag.get("class") or [])]).lower()
        if token in tid:
            out.append(tag)
    return out


def parse_int_text(s: Any):
    m = re.search(r"-?\d+", clean_text(s))
    return int(m.group(0)) if m else None


def teams_from_soup(soup, txt: str) -> tuple[str, str]:
    home = away = ""
    t1 = first_by_id_contains(soup, "lnkTakim1")
    t2 = first_by_id_contains(soup, "lnkTakim2")
    if t1:
        home = clean_team(t1.get_text(" ", strip=True))
    if t2:
        away = clean_team(t2.get_text(" ", strip=True))
    if home and away:
        return home, away

    # Title fallback: "EV DEPLASMAN - Maç Detayları TFF". Balkes olan tarafı bulmak için satırı parçala.
    first = txt.splitlines()[0] if txt.splitlines() else ""
    first = re.sub(r"\s+-\s+Maç Detayları.*$", "", first, flags=re.I)
    # Bilinen ayraç yoksa ilk Balkes varyantı etrafında böl.
    if is_balkes(first):
        # En iyi fallback: meta description'da genellikle "TAKIM1 TAKIM2 - Türkiye..." var.
        # Bu fallback her zaman mükemmel değil, soup id'leri yoksa kalite D olur.
        pass
    return home, away


def score_from_soup(soup, txt: str) -> tuple[Any, Any, str, bool]:
    h = a = None
    # Modern TFF detay sayfası:
    # lblTakim1Skor -> ev skoru, Label12/lblTakim2Skor -> deplasman skoru.
    t1 = first_by_id_contains(soup, "lblTakim1Skor")
    if t1:
        h = parse_int_text(t1.get_text(" ", strip=True))
    t2 = first_by_id_contains(soup, "lblTakim2Skor") or first_by_id_contains(soup, "Label12")
    if t2:
        a = parse_int_text(t2.get_text(" ", strip=True))

    if h is None or a is None:
        # MacDetaySayi sınıfındaki iki sayı.
        nums = []
        for tag in all_by_id_contains(soup, "MacDetaySayi"):
            v = parse_int_text(tag.get_text(" ", strip=True))
            if v is not None:
                nums.append(v)
        if len(nums) >= 2:
            h, a = nums[0], nums[1]

    if h is None or a is None:
        m = re.search(r"\b(\d{1,2})\s*[-–]\s*(\d{1,2})\b", txt)
        if m:
            h, a = int(m.group(1)), int(m.group(2))

    played = h is not None and a is not None
    return h, a, f"{h}-{a}" if played else "", played


def parse_match_code(soup, txt: str) -> str:
    tag = first_by_id_contains(soup, "lblKod")
    if tag:
        return clean_text(tag.get_text(" ", strip=True))
    m = re.search(r"(?:Müsabaka|Musabaka|Maç|Mac)\s*Kodu\s*:?\s*(\d+)", txt, re.I)
    return m.group(1) if m else ""


def parse_date_time(soup, txt: str) -> tuple[str, str]:
    tag = first_by_id_contains(soup, "lblTarih")
    raw = tag.get_text(" ", strip=True) if tag else txt
    return parse_date_any(raw), parse_time_any(raw)


def parse_competition(soup, txt: str) -> str:
    tag = first_by_id_contains(soup, "lblOrganizasyonAdi")
    return clean_text(tag.get_text(" ", strip=True)) if tag else ""


def parse_stadium(soup) -> str:
    tag = first_by_id_contains(soup, "lnkStad")
    return clean_text(tag.get_text(" ", strip=True)) if tag else ""


def parse_officials(soup, txt: str) -> list[dict[str, str]]:
    officials = []
    if soup:
        for a in soup.find_all("a", href=True):
            href = a.get("href") or ""
            raw = clean_text(a.get_text(" ", strip=True))
            if "hakemId=" not in href and "(Hakem)" not in raw and "Yardımcı Hakem" not in raw:
                continue
            m = re.match(r"(.+?)\((.+?)\)\s*$", raw)
            if m:
                name, role = clean_text(m.group(1)), clean_text(m.group(2))
            else:
                name, role = raw, "Hakem"
            officials.append({"role": role, "name": name})
    if officials:
        return officials

    patterns = [
        ("Hakem", r"\bHakem\s*:?\s*([A-ZÇĞİÖŞÜa-zçğıöşü .'-]{4,80})"),
        ("1. Yardımcı Hakem", r"(?:1\.?\s*Yardımcı Hakem|1\.?\s*Yardimci Hakem)\s*:?\s*([A-ZÇĞİÖŞÜa-zçğıöşü .'-]{4,80})"),
        ("2. Yardımcı Hakem", r"(?:2\.?\s*Yardımcı Hakem|2\.?\s*Yardimci Hakem)\s*:?\s*([A-ZÇĞİÖŞÜa-zçğıöşü .'-]{4,80})"),
        ("Gözlemci", r"\bGözlemci\s*:?\s*([A-ZÇĞİÖŞÜa-zçğıöşü .'-]{4,80})"),
    ]
    for role, pat in patterns:
        m = re.search(pat, txt, re.I)
        if m:
            officials.append({"role": role, "name": clean_text(m.group(1))})
    return officials


def parse_sections_raw(txt: str) -> dict[str, str]:
    lines = txt.splitlines()
    sections = {"full_text_excerpt": txt[:25000]}
    picks = {
        "officials_raw": ["hakem", "gozlemci", "gözlemci"],
        "lineups_raw": ["ilk 11", "yedek"],
        "events_raw": ["sari kart", "sarı kart", "kirmizi kart", "kırmızı kart", "oyuna giren", "oyundan cikan", "oyundan çıkan", "gol", " dk"],
    }
    for key, needles in picks.items():
        hits = [x for x in lines if any(n in norm(x) for n in needles)]
        if hits:
            sections[key] = "\n".join(hits[:250])
    return sections


def parse_events_best_effort(txt: str, home: str, away: str) -> list[dict[str, Any]]:
    events = []
    current_team = ""
    for line in txt.splitlines():
        n = norm(line)
        if home and norm(home) in n:
            current_team = home
        elif away and norm(away) in n:
            current_team = away
        mm = re.search(r"\b(\d{1,3})\s*(?:\.?\s*dk|dakika|')\b", n)
        if not mm:
            continue
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
        if typ:
            events.append({"type": typ, "minute": int(mm.group(1)), "team": current_team, "raw": line})
    return events


def parse_detail(mid: str, raw: str, season: str, source_url: str, seed: dict[str, Any]) -> dict[str, Any]:
    soup = soup_from_html(raw)
    txt = text_from_html(raw)
    home, away = teams_from_soup(soup, txt)
    sh, sa, sdisp, played = score_from_soup(soup, txt)
    match_date, match_time = parse_date_time(soup, txt)
    competition = parse_competition(soup, txt)
    match_type, match_label = classify_type(competition)
    is_home = is_balkes(home)
    is_away = is_balkes(away)
    opponent = away if is_home else home if is_away else (away or home)
    gf = sh if is_home else sa if is_away else None
    ga = sa if is_home else sh if is_away else None
    result = ""
    if played and gf is not None and ga is not None:
        result = "W" if gf > ga else "D" if gf == ga else "L"

    officials = parse_officials(soup, txt)
    sections = parse_sections_raw(txt)
    events = parse_events_best_effort(txt, home, away)
    return {
        "id": str(mid),
        "matchCode": parse_match_code(soup, txt),
        "season": season,
        "competition": competition,
        "stadium": parse_stadium(soup),
        "date": match_date,
        "time": match_time,
        "dateDisplay": " - ".join(x for x in [match_date, match_time] if x),
        "homeTeam": home,
        "awayTeam": away,
        "matchType": match_type,
        "matchTypeLabel": match_label,
        "score": {"home": sh, "away": sa, "display": sdisp, "played": played},
        "balkes": {
            "isHome": bool(is_home),
            "isAway": bool(is_away),
            "opponent": opponent,
            "goalsFor": gf,
            "goalsAgainst": ga,
            "result": result,
        },
        "officials": officials,
        "referees": officials,
        "lineups": {
            "home": {"team": home, "starting11": [], "substitutes": [], "raw": sections.get("lineups_raw", "")},
            "away": {"team": away, "starting11": [], "substitutes": [], "raw": sections.get("lineups_raw", "")},
        },
        "events": events,
        "sections_raw": sections,
        "quality": "A" if home and away and played and match_date else "B" if home and away and match_date else "D",
        "source": {"name": "TFF", "url": source_url, "retrievedAt": now(), "sourceType": "official_tff_match_detail"},
    }


def detail_is_valid_for_season(detail: dict[str, Any], season: str, seed: dict[str, Any]) -> tuple[bool, str]:
    if not (is_balkes(detail.get("homeTeam")) or is_balkes(detail.get("awayTeam")) or is_balkes(json.dumps(detail.get("balkes", {}), ensure_ascii=False))):
        return False, "balkes_not_found"
    if not detail.get("date"):
        return False, "date_missing"
    if not date_in_season(detail["date"], season, seed):
        return False, f"date_out_of_season:{detail.get('date')}"
    if not detail.get("homeTeam") or not detail.get("awayTeam"):
        return False, "teams_missing"
    # Skor yoksa da fikstür olarak kabul edelim; uygulama played=false gösterebilir.
    return True, "ok"


def fetch_detail_if_valid(mid: str, season: str, raw_root: Path, sleep_s: float, force: bool, seed: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    last_reason = "fetch_failed"
    # Modern TFF için pageID=29 asıl detay. İkinci URL bazı eski sayfalarda işe yarayabilir.
    for url in [tff_url(pageID=29, macId=mid), tff_url(macId=mid, pageID=528)]:
        ok, raw = fetch(url, raw_root / season / "matches" / f"{mid}.html", sleep_s, force)
        if not ok:
            continue
        detail = parse_detail(mid, raw, season, url, seed)
        valid, reason = detail_is_valid_for_season(detail, season, seed)
        if valid:
            return detail, "ok"
        last_reason = reason
    return None, last_reason


def parse_standings(raw: str) -> list[dict[str, Any]]:
    # Bu factory maç içindir. Puan tablosu Nix standings hattına bırakıldı.
    return []


def discover(item: dict[str, Any], raw_root: Path, sleep_s: float, force: bool = False) -> tuple[list[str], list[str], list[dict[str, Any]]]:
    season = item["season"]
    selected, all_ids = set(), set()
    for page_id in item.get("pageIds", []):
        url = tff_url(pageID=page_id)
        ok, raw = fetch(url, raw_root / season / "pages" / f"pageID_{page_id}.html", sleep_s, force)
        if not ok:
            continue
        all_ids.update(extract_ids(raw))
        selected.update(extract_balkes_ids(raw))
        for gid in extract_param(raw, "grupID")[:30]:
            gurl = tff_url(pageID=page_id, grupID=gid)
            ok2, graw = fetch(gurl, raw_root / season / "standings" / f"pageID_{page_id}_group_{gid}.html", sleep_s, force)
            if not ok2:
                continue
            all_ids.update(extract_ids(graw))
            selected.update(extract_balkes_ids(graw))
    return sorted(selected, key=lambda x: int(x)), sorted(all_ids, key=lambda x: int(x)), []


def match_signature(match: dict[str, Any]) -> str:
    b = match.get("balkes") or {}
    sc = match.get("score") or {}
    return "|".join([
        str(match.get("date") or ""),
        norm(b.get("opponent") or match.get("homeTeam") or match.get("awayTeam") or ""),
        "home" if b.get("isHome") else "away",
        str(sc.get("display") or "unplayed"),
    ])


def index_from_detail(d: dict[str, Any]) -> dict[str, Any]:
    keys = ["id", "matchCode", "season", "competition", "stadium", "date", "time", "dateDisplay", "homeTeam", "awayTeam", "matchType", "matchTypeLabel", "score", "balkes", "quality"]
    out = {k: d.get(k) for k in keys if d.get(k) not in (None, "", {}, [])}
    out["detailUrl"] = f"seasons/{d['season']}/matches/{d['id']}.json"
    out["source"] = d["source"]
    return out


def process_season(item: dict[str, Any], args: argparse.Namespace, seed: dict[str, Any]) -> dict[str, Any]:
    season = item["season"]
    data_root = Path(args.data_root)
    raw_root = Path(args.raw_root)
    reports_root = Path(args.reports_root)
    log(f"=== {season} başladı ===")
    selected, all_ids, _ = discover(item, raw_root, args.sleep, args.force)
    known = {str(x) for x in item.get("knownMatchIds", [])}
    if selected or known:
        candidates = sorted(set(selected) | known, key=lambda x: int(x))
        mode = "selected_or_known"
    else:
        candidates = list(all_ids)
        mode = "all_discovered_fallback"
    if args.max_discovery_probe > 0:
        candidates = candidates[:args.max_discovery_probe]
    log(f"{season}: selectedIds={len(selected)}, allDiscoveredIds={len(all_ids)}, detailCandidates={len(candidates)}, candidateMode={mode}")

    season_dir = data_root / "seasons" / season
    matches_dir = season_dir / "matches"
    matches_dir.mkdir(parents=True, exist_ok=True)

    by_id: dict[str, dict[str, Any]] = {}
    rejected: dict[str, int] = {}
    rejected_samples: dict[str, list[str]] = {}
    for i, mid in enumerate(candidates, start=1):
        detail, reason = fetch_detail_if_valid(mid, season, raw_root, args.sleep, args.force, seed)
        if detail:
            by_id[str(mid)] = detail
        else:
            rejected[reason] = rejected.get(reason, 0) + 1
            rejected_samples.setdefault(reason, [])
            if len(rejected_samples[reason]) < 20:
                rejected_samples[reason].append(str(mid))
        if i % 50 == 0 or i == len(candidates):
            log(f"{season}: detail doğrulama {i}/{len(candidates)}, hits={len(by_id)}")

    by_sig: dict[str, dict[str, Any]] = {}
    duplicates = []
    for mid, d in by_id.items():
        sig = match_signature(d)
        if sig in by_sig:
            old = by_sig[sig]
            duplicates.append({"kept": old["id"], "dropped": mid, "signature": sig})
            if len(json.dumps(d, ensure_ascii=False)) > len(json.dumps(old, ensure_ascii=False)):
                by_sig[sig] = d
        else:
            by_sig[sig] = d

    details = sorted(by_sig.values(), key=lambda m: (m.get("date") or "", int(str(m.get("id") or 0))))
    for d in details:
        write_json(matches_dir / f"{d['id']}.json", d)
    index = [index_from_detail(d) for d in details]
    write_json(season_dir / "matches_index.json", index)
    write_json(season_dir / "standings_by_week.json", [])

    type_counts: dict[str, int] = {}
    wins = draws = losses = gf = ga = 0
    for m in index:
        mt = m.get("matchType") or "league"
        type_counts[mt] = type_counts.get(mt, 0) + 1
        b = m.get("balkes") or {}
        if b.get("result") == "W": wins += 1
        elif b.get("result") == "D": draws += 1
        elif b.get("result") == "L": losses += 1
        if b.get("goalsFor") is not None:
            gf += int(b.get("goalsFor") or 0)
        if b.get("goalsAgainst") is not None:
            ga += int(b.get("goalsAgainst") or 0)

    write_json(season_dir / "season.json", {
        "id": season,
        "name": season,
        "sourcePolicy": "TFF-only",
        "factoryVersion": FACTORY_VERSION,
        "updatedAt": now(),
        "summary": {"matches": len(index), "wins": wins, "draws": draws, "losses": losses, "goalsFor": gf, "goalsAgainst": ga, "goalDifference": gf - ga, "matchTypes": type_counts},
        "files": {"matchesIndex": f"seasons/{season}/matches_index.json", "standingsByWeek": f"seasons/{season}/standings_by_week.json"},
    })

    quality = {
        "season": season,
        "selectedIds": len(selected),
        "allDiscoveredIds": len(all_ids),
        "detailCandidates": len(candidates),
        "candidateMode": mode,
        "matchesPublished": len(index),
        "detailFiles": len(list(matches_dir.glob("*.json"))),
        "duplicatesDropped": len(duplicates),
        "rejectedReasons": rejected,
        "rejectedSamples": rejected_samples,
        "standingsSkipped": True,
        "standingsSnapshots": 0,
        "balkesTableFound": False,
        "matchTypeCounts": type_counts,
        "seasonGuard": {"start": season_bounds(season, seed)[0], "end": season_bounds(season, seed)[1]},
        "generatedAt": now(),
    }
    write_json(reports_root / "seasons" / f"{season}_quality.json", quality)
    if duplicates:
        write_json(reports_root / "seasons" / f"{season}_duplicate_candidates.json", duplicates)
    return quality


def build_manifest(data_root: Path, processed: list[str]) -> None:
    seasons = []
    for p in sorted((data_root / "seasons").glob("*/matches_index.json"), reverse=True):
        arr = read_json(p, [])
        if isinstance(arr, list) and arr:
            seasons.append({"id": p.parent.name, "name": p.parent.name, "matchCount": len(arr)})
    write_json(data_root / "manifest.json", {
        "app": "Balkes Skor",
        "schemaVersion": 3,
        "dataVersion": 1,
        "appVersion": "0.5.0-beta-debug",
        "generatedAt": now(),
        "team": "Balıkesirspor",
        "availableSeasons": seasons,
        "global": {"playersIndexUrl": "players_index.json", "opponentsIndexUrl": "opponents_index.json", "searchIndexUrl": "search_index.json", "dataReportUrl": "data_report.json"},
        "appDataVersion": int(datetime.now().timestamp()),
        "appMinVersion": "0.5.0-beta-debug",
        "lastUpdated": now(),
        "dataBaseUrl": "https://raw.githubusercontent.com/Sinanjam/balkes-skor/main/data/",
        "factoryVersion": FACTORY_VERSION,
        "processedSeasonsInLastRun": processed,
    })


def rebuild_global_indexes(data_root: Path) -> None:
    opponents = {}
    search = []
    for p in sorted((data_root / "seasons").glob("*/matches_index.json")):
        arr = read_json(p, [])
        for m in arr if isinstance(arr, list) else []:
            b = m.get("balkes") or {}
            opp = b.get("opponent")
            if opp:
                item = opponents.setdefault(norm(opp), {"name": opp, "matches": 0})
                item["matches"] += 1
            search.append({"type": "match", "season": m.get("season"), "id": m.get("id"), "title": f"{m.get('homeTeam','')} {m.get('score',{}).get('display','')} {m.get('awayTeam','')}", "date": m.get("date"), "url": m.get("detailUrl")})
    write_json(data_root / "players_index.json", [])
    write_json(data_root / "opponents_index.json", sorted(opponents.values(), key=lambda x: norm(x["name"])))
    write_json(data_root / "search_index.json", search)


def build_data_report(data_root: Path, reports_root: Path, processed: list[dict[str, Any]]) -> None:
    manifest = read_json(data_root / "manifest.json", {})
    seasons = manifest.get("availableSeasons", []) if isinstance(manifest, dict) else []
    total = sum(int(s.get("matchCount") or 0) for s in seasons)
    write_json(data_root / "data_report.json", {
        "generatedAt": now(),
        "sourcePolicy": "TFF-only",
        "factoryVersion": FACTORY_VERSION,
        "totalAppMatches": total,
        "seasons": seasons,
        "playersIndexed": 0,
        "opponentsIndexed": len(read_json(data_root / "opponents_index.json", [])),
        "notes": ["Puan tablosu bu factory içinde çekilmez; Nix standings hattı kullanılacak.", "Raw HTML repo'ya commitlenmez; artifact olarak saklanır."],
    })
    write_json(reports_root / "tff_factory_summary.json", {
        "generatedAt": now(),
        "status": "ok",
        "sourcePolicy": "TFF-only",
        "factoryVersion": FACTORY_VERSION,
        "processed": processed,
        "after": {"seasons": len(seasons), "matches": total},
        "safeToPush": total > 0,
    })


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", default="sources/tff/registry/balkes_tff_seed_registry.json")
    ap.add_argument("--data-root", default="data")
    ap.add_argument("--raw-root", default="sources/tff/raw")
    ap.add_argument("--reports-root", default="reports/tff_factory")
    ap.add_argument("--start-season", default="2025-2026")
    ap.add_argument("--max-seasons", type=int, default=3)
    ap.add_argument("--sleep", type=float, default=1.0)
    ap.add_argument("--max-discovery-probe", type=int, default=1500)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skip-standings", action="store_true", default=True)
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
    run_matches = sum(int(x.get("matchesPublished") or 0) for x in processed)
    if run_matches <= 0:
        raise SystemExit("HATA: Bu run hiç maç üretmedi; main'e basılmamalı.")
    log(f"DONE {FACTORY_VERSION}: processed={processed_seasons}, run_matches={run_matches}")


if __name__ == "__main__":
    main()
