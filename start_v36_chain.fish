#!/usr/bin/env fish
set -l start_season "2025-2026"
set -l clean_all "true"
set -l end_year "1990"
set -l group_size "4"
set -l wait_minutes "5"
set -l group_timeout_minutes "300"

if test (count $argv) -ge 1
    set start_season $argv[1]
end
if test (count $argv) -ge 2
    set clean_all $argv[2]
end

mkdir -p .github
python3 -c 'import json,sys,datetime
obj={
 "start_season":sys.argv[1],
 "end_year":int(sys.argv[2]),
 "group_size":int(sys.argv[3]),
 "wait_minutes":int(sys.argv[4]),
 "group_timeout_minutes":int(sys.argv[5]),
 "clean_all_before_start":sys.argv[6].lower()=="true",
 "auto_push_main":True,
 "skip_standings":False,
 "standings_mode":"auto",
 "standings_detail_mode":"missing",
 "standings_workers":6,
 "standings_week_param_mode":"smart",
 "legacy_broad_probe_limit":350,
 "strict_legacy_targets":True,
 "chain_label":"chain-1991-v36-dispatch",
 "updated_at":datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00","Z"),
}
open(".github/tff-chain-v36-trigger.json","w",encoding="utf-8").write(json.dumps(obj,ensure_ascii=False,indent=2)+"\n")' $start_season $end_year $group_size $wait_minutes $group_timeout_minutes $clean_all

git add .github/tff-chain-v36-trigger.json
git commit -m "Trigger v3.6 compact dispatch chain $start_season"
git push origin main
