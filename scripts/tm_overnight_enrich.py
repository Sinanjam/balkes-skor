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
SLEEP = float(os.environ.get("TM_SLEEP", "8"))
YEARS_RAW = os.environ.get("TM_YEARS", "1990-2025")
PLAYER_ENDPOINTS = [
    x.strip()
    for x in os.environ.get(
        "TM_PLAYER_ENDPOINTS",
        "profile,market_value,transfers,jersey_numbers"
    ).split(",")
    if x.strip()
]

RAW.mkdir(exist_ok=True)
REPORTS.mkdir(exist_ok=True)
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
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")

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

def safe_name(s):
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(s or "x"))[:120]

def walk(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from walk(v)

def first(d, keys):
    if not isinstance(d, dict):
        return None
    for k in keys:
        if k in d and d[k] not in (None, "", []):
            return d[k]
    return None

def get_url(path):
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return API + path

def fetch_json(path, cache_path=None, sleep_after=True, retries=5):
    url = get_url(path)

    if cache_path:
        cache_path = Path(cache_path)
        if cache_path.exists() and cache_path.stat().st_size > 2:
            try:
                return json.loads(cache_path.read_text(encoding="utf-8"))
            except Exception:
                pass

    last_error = ""
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "BalkesSkorDataEnricher/0.2"}
            )
            with urllib.request.urlopen(req, timeout=180) as res:
                raw = res.read().decode("utf-8", errors="replace")
            data = json.loads(raw)
            if cache_path:
                write_json(cache_path, data)
            if sleep_after:
                time.sleep(SLEEP)
            return data
        except Exception as ex:
            last_error = str(ex)
            log(f"İstek hatası {attempt}/{retries}: {url} -> {last_error}")
            time.sleep(min(60, SLEEP * attempt))

    if cache_path:
        Path(str(cache_path) + ".error.txt").write_text(last_error, encoding="utf-8")
    return None

def wait_api():
    log(f"Transfermarkt API bekleniyor: {API}")
    while True:
        try:
            with urllib.request.urlopen(API + "/openapi.json", timeout=15) as res:
                if res.status == 200:
                    log("Transfermarkt API hazır.")
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
            a, b = part.split("-", 1)
            a = int(a)
            b = int(b)
            for y in range(a, b + 1):
                years.add(y)
        else:
            years.add(int(part))
    return sorted(years)

def find_club_id():
    queries = [
        "Balıkesirspor",
        "Balikesirspor",
        "Balıkesirspor Kulübü",
        "Balikesirspor Kulubu"
    ]

    candidates = []
    for q in queries:
        path = "/clubs/search/" + urllib.parse.quote(q, safe="")
        cache = RAW / f"club_search_{safe_name(q)}.json"
        data = fetch_json(path, cache)
        if not data:
            continue

        for d in walk(data):
            name = first(d, ["name", "clubName", "title"])
            cid = first(d, ["id", "clubId"])
            if name and cid and "balikesir" in norm(name):
                n = norm(name)
                score = 0
                if n == "balikesirspor":
                    score += 100
                if "balikesirspor" in n:
                    score += 80
                if "balikesir" in n:
                    score += 50
                candidates.append({
                    "id": str(cid),
                    "name": str(name),
                    "score": score,
                    "raw": d
                })

    unique = {}
    for c in candidates:
        unique[c["id"]] = c

    candidates = sorted(unique.values(), key=lambda x: x["score"], reverse=True)
    write_json(REPORTS / "tm_club_candidates.json", candidates)

    if not candidates:
        raise SystemExit("Balıkesirspor Transfermarkt kulüp ID bulunamadı. reports/tm_club_candidates.json kontrol et.")

    chosen = candidates[0]
    log(f"Kulüp seçildi: {chosen[name]} / ID={chosen[id]}")
    return chosen["id"], chosen

def player_dict_score(d):
    score = 0
    for k in [
        "position",
        "dateOfBirth",
        "age",
        "marketValue",
        "nationality",
        "height",
        "foot",
        "shirtNumber"
    ]:
        if isinstance(d, dict) and k in d and d[k] not in (None, "", []):
            score += 1
    return score

def extract_players(data):
    found = []
    seen = set()

    for d in walk(data):
        name = first(d, ["name", "playerName", "fullName"])
        pid = first(d, ["id", "playerId"])
        if not name or not pid:
            continue
        if "balikesirspor" in norm(name):
            continue

        key = (str(pid), norm(name))
        if key in seen:
            continue

        score = player_dict_score(d)
        if score >= 1:
            seen.add(key)
            found.append({
                "id": str(pid),
                "name": str(name),
                "score": score,
                "raw": d
            })

    return found

def compact_roster(raw):
    if not isinstance(raw, dict):
        return {}

    keep = [
        "id",
        "name",
        "playerName",
        "position",
        "dateOfBirth",
        "age",
        "nationality",
        "height",
        "foot",
        "shirtNumber",
        "marketValue",
        "joined",
        "joinedOn",
        "signedFrom",
        "contract",
        "contractUntil",
        "imageUrl",
        "url"
    ]

    out = {}
    for k in keep:
        if k in raw and raw[k] not in (None, "", []):
            out[k] = raw[k]
    return out

def extract_summary(data):
    out = {}
    wanted = {
        "dateOfBirth",
        "placeOfBirth",
        "citizenship",
        "nationality",
        "height",
        "position",
        "foot",
        "currentClub",
        "marketValue",
        "currentMarketValue",
        "highestMarketValue",
        "contractExpires",
        "imageUrl",
        "url",
        "shirtNumber"
    }

    for d in walk(data):
        if not isinstance(d, dict):
            continue
        for k, v in d.items():
            if k in wanted and k not in out and v not in (None, "", []):
                out[k] = v

    return out

def best_match(name, tm_by_name):
    key = norm(name)

    if key in tm_by_name:
        return tm_by_name[key], "exact_name", 1.0

    keys = list(tm_by_name.keys())
    if not keys:
        return None, "none", 0.0

    scores = []
    for k in keys:
        ratio = difflib.SequenceMatcher(None, key, k).ratio()
        scores.append((ratio, k))

    scores.sort(reverse=True)
    best_score, best_key = scores[0]
    second = scores[1][0] if len(scores) > 1 else 0.0

    if best_score >= 0.93 and best_score - second >= 0.03:
        return tm_by_name[best_key], "fuzzy_name", best_score

    return None, "unmatched", best_score

def main():
    wait_api()

    manifest = read_json(DATA / "manifest.json", {})
    tff_players = read_json(DATA / "players_index.json", [])

    if not isinstance(tff_players, list):
        raise SystemExit("data/players_index.json liste değil veya okunamadı.")

    manifest_years = []
    for s in manifest.get("availableSeasons", []):
        sid = str(s.get("id", ""))
        m = re.match(r"([0-9]{4})", sid)
        if m:
            manifest_years.append(int(m.group(1)))

    years = sorted(set(parse_years(YEARS_RAW)) | set(manifest_years))

    log(f"TFF oyuncu sayısı: {len(tff_players)}")
    log(f"Denenen sezon yılı sayısı: {len(years)}")

    club_id, club = find_club_id()
    write_json(RAW / "balikesirspor_club_selected.json", club)

    profile = fetch_json(
        f"/clubs/{urllib.parse.quote(str(club_id), safe=)}/profile",
        RAW / "balikesirspor_club_profile.json"
    )
    if profile:
        log("Kulüp profili çekildi.")

    tm_players_by_name = {}
    all_roster_players = []

    for year in years:
        log(f"Kadro çekiliyor: season_id={year}")
        data = fetch_json(
            f"/clubs/{urllib.parse.quote(str(club_id), safe=)}/players?season_id={year}",
            RAW / "club_players" / f"balikesirspor_{year}_players.json"
        )

        if not data:
            log(f"Kadro boş veya hata: {year}")
            continue

        players = extract_players(data)
        log(f"{year} oyuncu adayı: {len(players)}")

        for p in players:
            p["seasonId"] = year
            all_roster_players.append(p)

            key = norm(p["name"])
            if key not in tm_players_by_name:
                tm_players_by_name[key] = {
                    "id": p["id"],
                    "name": p["name"],
                    "seasonIds": [year],
                    "records": [p]
                }
            else:
                item = tm_players_by_name[key]
                item["seasonIds"] = sorted(set(item["seasonIds"] + [year]))
                item["records"].append(p)

    write_json(REPORTS / "tm_all_roster_players.json", all_roster_players)

    log(f"Toplam Transfermarkt kadro oyuncu adayı: {len(all_roster_players)}")
    log(f"Benzersiz Transfermarkt isim: {len(tm_players_by_name)}")

    matched = []
    unmatched = []
    enriched = []

    for idx, player in enumerate(tff_players, start=1):
        p = dict(player)
        name = p.get("name", "")
        tm, method, confidence = best_match(name, tm_players_by_name)

        if not tm:
            p["transfermarkt"] = {
                "matched": False,
                "bestScore": round(confidence, 4)
            }
            unmatched.append({
                "name": name,
                "bestScore": round(confidence, 4)
            })
            enriched.append(p)
            continue

        pid = tm["id"]
        raw_best = tm["records"][0].get("raw", {})

        tm_info = {
            "matched": True,
            "id": pid,
            "name": tm["name"],
            "matchedBy": method,
            "confidence": round(confidence, 4),
            "seasonIds": tm["seasonIds"],
            "roster": compact_roster(raw_best),
            "details": {}
        }

        log(f"Oyuncu {idx}/{len(tff_players)} eşleşti: {name} -> {tm[name]}")

        for endpoint in PLAYER_ENDPOINTS:
            cache = RAW / "players" / f"{safe_name(pid)}_{endpoint}.json"
            detail = fetch_json(
                f"/players/{urllib.parse.quote(str(pid), safe=)}/{endpoint}",
                cache
            )
            if detail:
                tm_info["details"][endpoint] = extract_summary(detail)

        p["transfermarkt"] = tm_info

        matched.append({
            "tffName": name,
            "tmName": tm["name"],
            "tmId": pid,
            "matchedBy": method,
            "confidence": round(confidence, 4),
            "seasonIds": tm["seasonIds"]
        })

        enriched.append(p)

    out_path = DATA / "players_index.transfermarkt.json"
    write_json(out_path, enriched)

    write_json(REPORTS / "tm_match_report.json", {
        "generatedAt": datetime.utcnow().isoformat() + "Z",
        "api": API,
        "clubId": club_id,
        "years": years,
        "tffPlayers": len(tff_players),
        "tmRosterCandidates": len(all_roster_players),
        "tmUniqueNames": len(tm_players_by_name),
        "matched": len(matched),
        "unmatched": len(unmatched),
        "playerEndpoints": PLAYER_ENDPOINTS,
        "matchedPlayers": matched,
        "unmatchedPlayers": unmatched
    })

    (REPORTS / "tm_unmatched_players.txt").write_text(
        "\n".join(x["name"] for x in unmatched if x.get("name")),
        encoding="utf-8"
    )

    log("BİTTİ.")
    log(f"Eşleşen: {len(matched)}")
    log(f"Eşleşmeyen: {len(unmatched)}")
    log(f"Zenginleştirilmiş çıktı: {out_path}")
    log("Rapor: reports/tm_match_report.json")
    log("Eşleşmeyenler: reports/tm_unmatched_players.txt")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("Elle durduruldu.")
        sys.exit(130)
