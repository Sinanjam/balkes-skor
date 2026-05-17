#!/usr/bin/env fish
set -l seasons $argv
if test (count $seasons) -eq 0
    echo "Kullanım: fish start_v37_repair.fish 2024-2025 2023-2024"
    echo "veya:   fish start_v37_repair.fish \"2024-2025,2023-2024\""
    exit 1
end
mkdir -p .github
python3 -c 'import json,sys,datetime,re
raw=" ".join(sys.argv[1:])
parts=[x for x in re.split(r"[\s,;]+", raw.strip()) if x]
seen=set(); seasons=[]
for p in parts:
    if not re.match(r"^\d{4}-\d{4}$", p): raise SystemExit(f"Sezon formatı hatalı: {p}")
    if p not in seen: seen.add(p); seasons.append(p)
seasons=sorted(seasons, key=lambda s:int(s[:4]), reverse=True)
obj={"seasons":seasons,"auto_push_main":True,"skip_standings":False,"standings_mode":"auto","standings_detail_mode":"missing","standings_workers":6,"standings_week_param_mode":"smart","legacy_broad_probe_limit":350,"strict_legacy_targets":True,"allow_partial":True,"chain_label":"repair-v37-exact-seasons","updated_at":datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00","Z")}
open(".github/tff-repair-v37-trigger.json","w",encoding="utf-8").write(json.dumps(obj,ensure_ascii=False,indent=2)+"\n")
print("v3.7 repair trigger:", ", ".join(seasons))' $seasons
git add .github/tff-repair-v37-trigger.json
git commit -m "Trigger v3.7 exact season repair"
git push origin main
