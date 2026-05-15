#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Patch MainActivity standings UI for clean mobile rendering.

The old UI rendered the whole table as monospace-like formatted text in a normal
TextView. On phones this wrapped columns and made tables unreadable. This patch
renders each team as a compact card, filters impossible rows defensively, and
keeps Balıkesirspor highlighted.
"""
from __future__ import annotations

from pathlib import Path

TARGET = Path("app/src/main/java/com/sinanjam/balkesskor/MainActivity.java")

NEW_METHODS = r'''    private void drawStandingsWeek(final JSONArray weeks, final int idx) {
        while (content.getChildCount() > standingsBaseChildren) content.removeViewAt(standingsBaseChildren);
        JSONObject snap = weeks.optJSONObject(Math.max(0, Math.min(idx, weeks.length() - 1)));
        if (snap == null) return;
        LinearLayout switcher = new LinearLayout(this);
        switcher.setOrientation(LinearLayout.HORIZONTAL);
        Button prev = darkButton("← Önceki");
        Button next = redButton("Sonraki →");
        switcher.addView(prev, new LinearLayout.LayoutParams(0, dp(48), 1));
        LinearLayout.LayoutParams np = new LinearLayout.LayoutParams(0, dp(48), 1);
        np.setMargins(dp(8), 0, 0, 0);
        switcher.addView(next, np);
        content.addView(switcher);
        prev.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { drawStandingsWeek(weeks, Math.max(0, idx - 1)); } });
        next.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { drawStandingsWeek(weeks, Math.min(weeks.length() - 1, idx + 1)); } });

        LinearLayout c = card();
        text(c, "Hafta " + snap.optInt("week"), 20, true, text);
        String source = snap.optString("source", "");
        if (source.length() > 0) text(c, "Kaynak: " + source, 11, false, muted);
        text(c, "Sıralama kartları: O/G/B/M, A-Y, averaj ve puan değerleri temizlenmiş veriden gösterilir.", 11, false, muted);
        JSONArray arr = snap.optJSONArray("standings");
        if (arr == null) return;
        int shown = 0;
        for (int i = 0; i < arr.length(); i++) {
            JSONObject t = arr.optJSONObject(i);
            if (t == null || !isValidStandingRow(t)) continue;
            boolean balkes = t.optBoolean("isBalkes") || isBalkesName(t.optString("team"));
            standingTeamCard(c, t, balkes);
            String penalty = t.optString("penaltyNote", "");
            int deducted = t.optInt("pointsDeducted", 0);
            if (balkes && (penalty.length() > 0 || deducted != 0)) {
                text(c, "Balıkesirspor ceza/not: " + (penalty.length() > 0 ? penalty : String.valueOf(deducted) + " puan"), 11, false, gold);
            }
            shown++;
        }
        if (shown == 0) {
            text(c, "Bu haftanın puan tablosu temizlenemedi. Veri yeniden üretildiğinde otomatik düzelecek.", 13, true, gold);
        }
    }

    private boolean isValidStandingRow(JSONObject t) {
        String team = t.optString("team", "");
        if (team.length() == 0) return false;
        String n = team.toLowerCase(new java.util.Locale("tr", "TR"));
        n = n.replace("ı", "i").replace("ğ", "g").replace("ü", "u").replace("ş", "s").replace("ö", "o").replace("ç", "c");
        if (n.equals("devre") || n.equals("1 devre") || n.equals("2 devre") || n.endsWith(" devre") || n.equals("takim")) return false;
        int played = t.optInt("played");
        int won = t.optInt("won");
        int drawn = t.optInt("drawn");
        int lost = t.optInt("lost");
        int gf = t.has("goalsFor") ? t.optInt("goalsFor") : t.optInt("for");
        int ga = t.has("goalsAgainst") ? t.optInt("goalsAgainst") : t.optInt("against");
        int gd = t.has("goalDifference") ? t.optInt("goalDifference") : gf - ga;
        int pts = t.optInt("points");
        if (played < 0 || played > 50 || won < 0 || drawn < 0 || lost < 0) return false;
        if (won + drawn + lost != played) return false;
        if (gf < 0 || ga < 0 || Math.abs(gd - (gf - ga)) > 1) return false;
        if (pts < -20 || pts > won * 3 + drawn + 15) return false;
        return true;
    }

    private void standingTeamCard(LinearLayout parent, JSONObject t, boolean balkes) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(10), dp(9), dp(10), dp(9));
        box.setBackground(balkes ? round(redSoft, dp(14), red) : round(surface2, dp(14), stroke));
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(-1, -2);
        bp.setMargins(0, dp(7), 0, 0);
        parent.addView(box, bp);

        LinearLayout top = row(box);
        TextView rank = new TextView(this);
        rank.setText(String.valueOf(t.optInt("rank")) + ".");
        rank.setTextColor(balkes ? Color.WHITE : muted);
        rank.setTextSize(14);
        rank.setTypeface(Typeface.DEFAULT_BOLD);
        top.addView(rank, new LinearLayout.LayoutParams(dp(34), -2));

        TextView team = new TextView(this);
        team.setText(t.optString("team"));
        team.setTextColor(Color.WHITE);
        team.setTextSize(balkes ? 16 : 14);
        team.setTypeface(Typeface.DEFAULT_BOLD);
        team.setSingleLine(false);
        top.addView(team, new LinearLayout.LayoutParams(0, -2, 1));

        TextView pts = new TextView(this);
        pts.setText(t.optInt("points") + " P");
        pts.setTextColor(balkes ? Color.WHITE : gold);
        pts.setTextSize(16);
        pts.setTypeface(Typeface.DEFAULT_BOLD);
        pts.setGravity(Gravity.RIGHT);
        top.addView(pts, new LinearLayout.LayoutParams(dp(62), -2));

        int gf = t.has("goalsFor") ? t.optInt("goalsFor") : t.optInt("for");
        int ga = t.has("goalsAgainst") ? t.optInt("goalsAgainst") : t.optInt("against");
        int gd = t.has("goalDifference") ? t.optInt("goalDifference") : gf - ga;
        String metrics = "O " + t.optInt("played") + "   G " + t.optInt("won") + "   B " + t.optInt("drawn") + "   M " + t.optInt("lost")
                + "   A/Y " + gf + "-" + ga + "   Av " + gd;
        TextView m = text(box, metrics, 12, false, balkes ? Color.WHITE : muted);
        m.setPadding(dp(34), dp(4), 0, 0);
    }

    private String standingsRowText(JSONObject t) {
        int gf = t.has("goalsFor") ? t.optInt("goalsFor") : t.optInt("for");
        int ga = t.has("goalsAgainst") ? t.optInt("goalsAgainst") : t.optInt("against");
        int gd = t.has("goalDifference") ? t.optInt("goalDifference") : gf - ga;
        return t.optInt("rank") + ". " + t.optString("team") + "  O " + t.optInt("played") + "  G " + t.optInt("won")
                + "  B " + t.optInt("drawn") + "  M " + t.optInt("lost") + "  " + gf + "-" + ga + "  Av " + gd + "  P " + t.optInt("points");
    }

'''


def find_method_end(src: str, start: int) -> int:
    brace = src.find('{', start)
    if brace < 0:
        raise SystemExit('method brace not found')
    depth = 0
    for i in range(brace, len(src)):
        ch = src[i]
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                return i + 1
    raise SystemExit('method end not found')


def main() -> None:
    src = TARGET.read_text(encoding='utf-8')
    a = src.find('    private void drawStandingsWeek(')
    b = src.find('    private void renderPlayers()', a)
    if a < 0 or b < 0:
        raise SystemExit('standings block markers not found')
    # Replace drawStandingsWeek + standingsRowText block, keeping renderPlayers and below.
    src = src[:a] + NEW_METHODS + src[b:]
    TARGET.write_text(src, encoding='utf-8')
    print('MainActivity standings UI patched for v2.9')


if __name__ == '__main__':
    main()
