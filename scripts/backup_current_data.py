#!/usr/bin/env python3
from pathlib import Path
import argparse, zipfile
from datetime import datetime
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--data-root",default="data"); ap.add_argument("--reports-root",default="reports/tff_factory"); args=ap.parse_args()
    data=Path(args.data_root); outdir=Path(args.reports_root)/"backups"; outdir.mkdir(parents=True,exist_ok=True)
    out=outdir/f"data_backup_before_clean_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    with zipfile.ZipFile(out,"w",zipfile.ZIP_DEFLATED) as z:
        if data.exists():
            for p in data.rglob("*"):
                if p.is_file(): z.write(p,p)
    print(out)
if __name__=="__main__": main()
