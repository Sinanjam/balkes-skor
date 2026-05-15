#!/usr/bin/env python3
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from google.cloud import firestore


def _count_query(query) -> int:
    """Use Firestore aggregation count when available; fall back to streaming."""
    try:
        result = query.count(alias="activeUsers30d").get()
        if result and result[0]:
            return int(result[0][0].value)
    except Exception as exc:  # noqa: BLE001
        print(f"Aggregation count kullanılamadı, stream fallback: {exc}")

    count = 0
    for _doc in query.stream():
        count += 1
    return count


def main() -> None:
    project_id = os.environ.get("FIREBASE_PROJECT_ID", "").strip()
    if not project_id:
        raise SystemExit("FIREBASE_PROJECT_ID secret/env boş.")

    db = firestore.Client(project=project_id)
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    query = db.collection("app_activity").where("lastSeen", ">=", cutoff)
    count = _count_query(query)

    db.document("public_stats/app").set(
        {
            "activeUsers30d": count,
            "updatedAt": firestore.SERVER_TIMESTAMP,
            "source": "github-actions",
            "windowDays": 30,
        },
        merge=True,
    )

    print(f"activeUsers30d={count}")


if __name__ == "__main__":
    main()
