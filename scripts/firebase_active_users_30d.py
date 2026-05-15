import os
from datetime import datetime, timedelta, timezone

from google.cloud import firestore


def main():
    project_id = os.environ.get("FIREBASE_PROJECT_ID", "balkes-skor")
    db = firestore.Client(project=project_id)

    cutoff = datetime.now(timezone.utc) - timedelta(days=30)

    query = (
        db.collection("app_activity")
        .where("lastSeen", ">=", cutoff)
    )

    count = 0
    for _doc in query.stream():
        count += 1

    db.document("public_stats/app").set(
        {
            "activeUsers30d": count,
            "updatedAt": firestore.SERVER_TIMESTAMP,
            "source": "github-actions"
        },
        merge=True
    )

    print(f"activeUsers30d={count}")


if __name__ == "__main__":
    main()
