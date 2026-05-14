const { onSchedule } = require("firebase-functions/v2/scheduler");
const { onRequest } = require("firebase-functions/v2/https");
const admin = require("firebase-admin");

admin.initializeApp();

async function refreshActiveUsers30dNow() {
  const db = admin.firestore();
  const cutoff = admin.firestore.Timestamp.fromMillis(
    Date.now() - 30 * 24 * 60 * 60 * 1000
  );

  const snapshot = await db
    .collection("app_activity")
    .where("lastSeen", ">=", cutoff)
    .count()
    .get();

  const count = snapshot.data().count;

  await db.doc("public_stats/app").set(
    {
      activeUsers30d: count,
      updatedAt: admin.firestore.FieldValue.serverTimestamp()
    },
    { merge: true }
  );

  return count;
}

exports.refreshActiveUsers30d = onSchedule(
  {
    schedule: "every 1 hours",
    region: "europe-west1"
  },
  async () => {
    await refreshActiveUsers30dNow();
  }
);

exports.refreshActiveUsers30dManual = onRequest(
  {
    region: "europe-west1"
  },
  async (req, res) => {
    const count = await refreshActiveUsers30dNow();
    res.json({ activeUsers30d: count });
  }
);
