#!/usr/bin/env python3
import json
import os
import re
import sys
import time
import urllib.request
import urllib.parse
import unicodedata
import difflib
from pathlib import Path
from datetime import datetime

ROOT = Path.cwd()
DATA = ROOT / "data"
RAW = ROOT / "tm_raw"
REPORTS = ROOT / "reports"

API = os.environ.get("TM_API", "http://127.0.0.1:8000").rstrip("/")
SLEEP = float(os.environ.get("TM_SLEEP", "10"))
YEARS_RAW = os.environ.get("TM_YEARS", "1990-2025")
PLAYER_ENDPOINTS = [x.strip() for x in os.environ.get("TM_PLAYER_ENDPOINTS", "profile,market_value,transfers,jersey_numbers").split(",") if x.strip()]

RAW.mkdir(exist_ok=True)
REPORTS.mkdir(exist_ok=True)
(RAW / "club_search").mkdir(parents=True, exist_ok=True)
(RAW / "club_players").mkdir(parents=True, exist_ok=True)
(RAW / "players").mkdir(parents=True, exist_ok=True)

def log(msg):
    stamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{stamp}] {msg}", flush=True)

def read_json(path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default

def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

def norm(s):
    s = str(s or "").strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    table = str.maketrans({
        "ı": "i",
        "İ": "i",
        "ğ": "g",
        "Ğ": "g",
        "ü": "u",
        "Ü": "u",
        "ş": "s",
        "Ş": "s",
        "ö": "o",
        "Ö": "o",
        "ç": "c",
        "Ç": "c"
    })
    s = s.translate(table)
    s = re.sub(r"[^a-z0-9 ]+", " ", s)
    return " ".join(s.split())

def safe(s):
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(s or "x"))[:120]

def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from walk(value)
    elif isinstance(obj, list):
        for value in obj:
            yield from walk(value)

def first(d, keys):
    if not isinstance(d, dict):
        return None
    for key in keys:
        value = d.get(key)
        if value not in (None, "", []):
            return value
    return None

def fetch_json(path, cache=None, retries=4):
    if path.startswith("http://") or path.startswith("https://"):
        url = path
    else:
        url = API + path

    if cache:
        cache = Path(cache)
        if cache.exists() and cache.stat().st_size > 2:
            cached = read_json(cache)
            if cached is not None:
                return cached

    last_error = ""
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "BalkesSkorTransfermarktEnricher/0.3"})
            with urllib.request.urlopen(req, timeout=180) as res:
                raw = res.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            if cache:
                write_json(cache, data)
            time.sleep(SLEEP)
            return data
        except Exception as ex:
            last_error = str(ex)
            log(f"Hata {attempt}/{retries}: {url} -> {last_error}")
            time.sleep(min(60, SLEEP * attempt))

    if cache:
        Path(str(cache) + ".error.txt").write_text(last_error, encoding="utf-8")
    return None

def wait_api():
    log(f"API kontrol ediliyor: {API}")
    while True:
        try:
            with urllib.request.urlopen(API + "/openapi.json", timeout=15) as res:
                if res.status == 200:
                    log("API hazır.")
                    return
        except Exception:
            log("API hazır değil. 15 saniye sonra tekrar denenecek.")
            time.sleep(15)

def parse_years(raw):
    years = set()
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            start, end = part.split("-", 1)
            for y in range(int(start), int(end) + 1):
                years.add(y)
        else:
            years.add(int(part))
    return sorted(years)

def years_from_manifest():
    manifest = read_json(DATA / "manifest.json", {})
    years = set()
    if isinstance(manifest, dict):
        for season in manifest.get("availableSeasons", []):
            sid = str(season.get("id", ""))
            match = re.match(r"([0-9]{4})", sid)
            if match:
                years.add(int(match.group(1)))
    return sorted(years)

def find_club():
    queries = ["Balıkesirspor", "Balikesirspor", "Balıkesirspor Kulübü", "Balikesirspor Kulubu"]
    candidates = []

    for query in queries:
        log(f"Kulüp aranıyor: {query}")
        data = fetch_json("/clubs/search/" + urllib.parse.quote(query, safe=""), RAW / "club_search" / f"{safe(query)}.json")
        if not data:
            continue

        for item in walk(data):
            name = first(item, ["name", "clubName", "title"])
            cid = first(item, ["id", "clubId"])
            if not name or not cid:
                continue
            n = norm(name)
            if "balikesir" not in n:
                continue
            score = 50
            if "balikesirspor" in n:
                score += 80
            if n == "balikesirspor":
                score += 50
            candidates.append({"id": str(cid), "name": str(name), "score": score, "raw": item})

    unique = {}
    for c in candidates:
        unique[c["id"]] = c
    candidates = sorted(unique.values(), key=lambda x: x["score"], reverse=True)
    write_json(REPORTS / "tm_club_candidates.json", candidates)

    if not candidates:
        raise SystemExit("Balikesirspor kulup ID bulunamadi. reports/tm_club_candidates.json kontrol et.")

    chosen = candidates[0]
    log("Kulüp seçildi: {} / ID={}".format(chosen.get("name", ""), chosen.get("id", "")))
    write_json(RAW / "balikesirspor_club_selected.json", chosen)
    return chosen

def player_score(item):
    score = 0
    for key in ["position", "dateOfBirth", "age", "marketValue", "nationality", "height", "foot", "shirtNumber"]:
        if isinstance(item, dict) and item.get(key) not in (None, "", []):
            score += 1
    return score

def extract_players(data):
    players = []
    seen = set()
    for item in walk(data):
        name = first(item, ["name", "playerName", "fullName"])
        pid = first(item, ["id", "playerId"])
        if not name or not pid:
            continue
        if "balikesirspor" in norm(name):
            continue
        score = player_score(item)
        key = (str(pid), norm(name))
        if key in seen:
            continue
        if score >= 1:
            seen.add(key)
            players.append({"id": str(pid), "name": str(name), "score": score, "raw": item})
    return players

def compact_dict(item):
    if not isinstance(item, dict):
        return {}
    keep = ["id", "name", "playerName", "position", "dateOfBirth", "age", "nationality", "height", "foot", "shirtNumber", "marketValue", "joined", "joinedOn", "signedFrom", "contract", "contractUntil", "imageUrl", "url"]
    out = {}
    for key in keep:
        if item.get(key) not in (None, "", []):
            out[key] = item.get(key)
    return out

def extract_summary(data):
    wanted = {"dateOfBirth", "placeOfBirth", "citizenship", "nationality", "height", "position", "foot", "currentClub", "marketValue", "currentMarketValue", "highestMarketValue", "contractExpires", "imageUrl", "url", "shirtNumber"}
    out = {}
    for item in walk(data):
        if not isinstance(item, dict):
            continue
        for key, value in item.items():
            if key in wanted and key not in out and value not in (None, "", []):
                out[key] = value
    return out

def best_match(name, tm_by_name):
    key = norm(name)
    if key in tm_by_name:
        return tm_by_name[key], "exact_name", 1.0

    keys = list(tm_by_name.keys())
    if not keys:
        return None, "none", 0.0

    scored = []
    for k in keys:
        ratio = difflib.SequenceMatcher(None, key, k).ratio()
        scored.append((ratio, k))
    scored.sort(reverse=True)
    best_score, best_key = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0.0

    if best_score >= 0.93 and best_score - second_score >= 0.03:
        return tm_by_name[best_key], "fuzzy_name", best_score

    return None, "unmatched", best_score

def load_tff_players():
    data = read_json(DATA / "players_index.json", None)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ["players", "items", "data"]:
            if isinstance(data.get(key), list):
                return data.get(key)
    return []

def main():
    wait_api()

    club = find_club()
    club_id = club["id"]

    years = sorted(set(parse_years(YEARS_RAW)) | set(years_from_manifest()))
    log(f"Sezon yil sayisi: {len(years)}")

    profile = fetch_json(f"/clubs/{urllib.parse.quote(str(club_id), safe="")}/profile", RAW / "balikesirspor_club_profile.json")
    if profile:
        log("Kulüp profili kaydedildi.")

    tm_by_name = {}
    roster_rows = []

    for year in years:
        log(f"Kadro çekiliyor: {year}")
        data = fetch_json(f"/clubs/{urllib.parse.quote(str(club_id), safe="")}/players?season_id={year}", RAW / "club_players" / f"balikesirspor_{year}_players.json")
        if not data:
            log(f"Kadro alınamadı: {year}")
            continue

        players = extract_players(data)
        log(f"{year} oyuncu adayı: {len(players)}")

        for player in players:
            player["seasonId"] = year
            roster_rows.append(player)
            key = norm(player["name"])
            if key not in tm_by_name:
                tm_by_name[key] = {"id": player["id"], "name": player["name"], "seasonIds": [year], "records": [player]}
            else:
                tm_by_name[key]["seasonIds"] = sorted(set(tm_by_name[key]["seasonIds"] + [year]))
                tm_by_name[key]["records"].append(player)

    write_json(REPORTS / "tm_all_roster_players.json", roster_rows)

    roster_index = []
    for key, value in sorted(tm_by_name.items(), key=lambda x: x[0]):
        best = value["records"][0]
        roster_index.append({
            "id": value["id"],
            "name": value["name"],
            "seasonIds": value["seasonIds"],
            "roster": compact_dict(best.get("raw", {}))
        })
    write_json(DATA / "transfermarkt_roster_index.json", roster_index)

    log(f"Transfermarkt benzersiz oyuncu: {len(roster_index)}")

    tff_players = load_tff_players()
    if not tff_players:
        log("data/players_index.json liste olarak okunamadı veya boş. Sadece transfermarkt_roster_index.json üretildi.")
        write_json(REPORTS / "tm_match_report.json", {
            "generatedAt": datetime.utcnow().isoformat() + "Z",
            "clubId": club_id,
            "years": years,
            "tmUniquePlayers": len(roster_index),
            "tffPlayers": 0,
            "matched": 0,
            "unmatched": 0,
            "note": "players_index.json liste degil veya bos"
        })
        log("BİTTİ.")
        return

    enriched = []
    matched = []
    unmatched = []

    log(f"TFF oyuncu sayısı: {len(tff_players)}")

    for idx, player in enumerate(tff_players, start=1):
        p = dict(player)
        name = p.get("name", "")
        tm, method, confidence = best_match(name, tm_by_name)

        if not tm:
            p["transfermarkt"] = {"matched": False, "bestScore": round(confidence, 4)}
            unmatched.append({"name": name, "bestScore": round(confidence, 4)})
            enriched.append(p)
            continue

        pid = tm["id"]
        raw_best = tm["records"][0].get("raw", {})
        info = {
            "matched": True,
            "id": pid,
            "name": tm["name"],
            "matchedBy": method,
            "confidence": round(confidence, 4),
            "seasonIds": tm["seasonIds"],
            "roster": compact_dict(raw_best),
            "details": {}
        }

        tm_name_for_log = tm.get("name", "")
        log(f"Oyuncu {idx}/{len(tff_players)}: {name} -> {tm_name_for_log}")

        for endpoint in PLAYER_ENDPOINTS:
            detail = fetch_json(f"/players/{urllib.parse.quote(str(pid), safe="")}/{endpoint}", RAW / "players" / f"{safe(pid)}_{endpoint}.json")
            if detail:
                info["details"][endpoint] = extract_summary(detail)

        p["transfermarkt"] = info
        matched.append({"tffName": name, "tmName": tm["name"], "tmId": pid, "matchedBy": method, "confidence": round(confidence, 4), "seasonIds": tm["seasonIds"]})
        enriched.append(p)

    write_json(DATA / "players_index.transfermarkt.json", enriched)
    write_json(REPORTS / "tm_match_report.json", {
        "generatedAt": datetime.utcnow().isoformat() + "Z",
        "clubId": club_id,
        "years": years,
        "tmUniquePlayers": len(roster_index),
        "tffPlayers": len(tff_players),
        "matched": len(matched),
        "unmatched": len(unmatched),
        "matchedPlayers": matched,
        "unmatchedPlayers": unmatched
    })
    (REPORTS / "tm_unmatched_players.txt").write_text("\n".join(x["name"] for x in unmatched if x.get("name")), encoding="utf-8")

    log("BİTTİ.")
    log(f"Eşleşen: {len(matched)}")
    log(f"Eşleşmeyen: {len(unmatched)}")
    log("Ana çıktı: data/players_index.transfermarkt.json")
    log("Kadro indeksi: data/transfermarkt_roster_index.json")
    log("Rapor: reports/tm_match_report.json")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Durduruldu.")
        sys.exit(130)
