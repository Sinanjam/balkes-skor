#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

from google.cloud import firestore


def as_utc_datetime(value: Any) -> datetime | None:
    """Normalize Firestore/Python/string timestamp values to UTC datetime."""
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            raw = raw.replace("Z", "+00:00")
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return None
    return None


def count_recent_by_stream(db: firestore.Client, cutoff: datetime) -> tuple[int, int, int, list[str]]:
    """Count recent unique installation docs by streaming app_activity.

    The app_activity collection stores one document per Firebase Installation ID.
    Streaming is intentionally used for v1.0.0 because the collection is tiny and
    it is more diagnostic than a blind aggregation query.
    """
    recent = 0
    total = 0
    missing = 0
    sample: list[str] = []
    for doc in db.collection("app_activity").stream():
        total += 1
        data = doc.to_dict() or {}
        last_seen = as_utc_datetime(data.get("lastSeen"))
        if last_seen is None:
            missing += 1
            continue
        if last_seen >= cutoff:
            recent += 1
            if len(sample) < 10:
                sample.append(doc.id)
    return recent, total, missing, sample


def main() -> None:
    project_id = os.environ.get("FIREBASE_PROJECT_ID", "").strip()
    if not project_id:
        raise SystemExit("FIREBASE_PROJECT_ID secret/env boş.")

    db = firestore.Client(project=project_id)
    now_utc = datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(days=30)

    count, total_docs, missing_last_seen, sample_recent = count_recent_by_stream(db, cutoff)

    db.document("public_stats/app").set(
        {
            "activeUsers30d": count,
            "totalInstallationsTracked": total_docs,
            "missingLastSeen": missing_last_seen,
            "updatedAt": firestore.SERVER_TIMESTAMP,
            "source": "github-actions-stream-v2",
            "windowDays": 30,
            "cutoffUtc": cutoff.isoformat().replace("+00:00", "Z"),
        },
        merge=True,
    )

    print(f"project_id={project_id}")
    print(f"cutoffUtc={cutoff.isoformat().replace('+00:00', 'Z')}")
    print(f"appActivityDocs={total_docs}")
    print(f"missingLastSeen={missing_last_seen}")
    print(f"recentSample={','.join(sample_recent)}")
    print(f"activeUsers30d={count}")


if __name__ == "__main__":
    main()
