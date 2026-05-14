#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
p = Path("app/src/main/java/com/sinanjam/balkesskor/MainActivity.java")
if not p.exists():
    print("UYARI: MainActivity.java bulunamadı; uygulama görünüm patch'i atlandı.")
    raise SystemExit(0)
s = p.read_text(encoding="utf-8")
s = s.replace('''                    String stage = m.optString("stage");
                    text(c, stage + " • " + m.optString("dateDisplay"), 12, true, muted);''', '''                    text(c, matchMeta(m), 12, true, muted);''')
s = s.replace('''        text(top, m.optString("stage") + " • " + m.optString("dateDisplay"), 13, false, muted);''', '''        text(top, matchMeta(m), 13, false, muted);''')
s = s.replace('''        if (m.optString("venue", "").length() > 0) text(top, "Stat: " + m.optString("venue"), 13, false, muted);''', '''        String stadium = m.optString("stadium", m.optString("venue", ""));
        if (stadium.length() > 0) text(top, "Stat: " + stadium, 13, false, muted);''')
s = s.replace('''        if (side.optString("coach", "").length() > 0) text(c, "Teknik sorumlu: " + side.optString("coach"), 12, false, muted);''', '''        String coach = sideCoach(side);
        if (coach.length() > 0) text(c, "Teknik sorumlu: " + coach, 12, false, muted);''')
s = s.replace('''                if (p != null) text(c, cleanNo(p.optString("shirt_no")) + "  " + p.optString("name"), 13, false, text);''', '''                if (p != null) text(c, cleanNo(p.optString("shirt_no", p.optString("number", ""))) + "  " + p.optString("name"), 13, false, text);''')
s = s.replace('''                    sb.append(cleanNo(p.optString("shirt_no"))).append(" ").append(p.optString("name"));''', '''                    sb.append(cleanNo(p.optString("shirt_no", p.optString("number", "")))).append(" ").append(p.optString("name"));''')
s = s.replace('''        if ("card".equals(type) || "yellow_card".equals(type) || "red_card".equals(type)) return min + "  🟨  " + e.optString("player") + "  •  " + team;''', '''        if ("card".equals(type) || "yellow_card".equals(type) || "red_card".equals(type)) {
            String icon = "red_card".equals(type) || "red".equals(e.optString("card")) ? "🟥" : "🟨";
            return min + "  " + icon + "  " + e.optString("player") + "  •  " + team;
        }''')
if "private String matchMeta(JSONObject m)" not in s:
    marker = '''    private boolean contains(String[] arr, String v) {'''
    helpers = '''    private String matchMeta(JSONObject m) {
        String label = m.optString("matchTypeLabel", m.optString("typeLabel", m.optString("stage", "")));
        if (label.length() == 0) {
            String t = m.optString("matchType", m.optString("type", ""));
            if ("cup".equals(t)) label = "ZTK";
            else if ("playoff".equals(t)) label = "Play-off";
            else if ("league".equals(t)) label = "Lig";
        }
        String d = m.optString("dateDisplay", m.optString("date", ""));
        if (label.length() > 0 && d.length() > 0) return label + " • " + d;
        if (label.length() > 0) return label;
        return d;
    }

    private String sideCoach(JSONObject side) {
        String coach = side.optString("coach", "");
        if (coach.length() > 0) return coach;
        JSONArray staff = side.optJSONArray("technicalStaff");
        if (staff != null && staff.length() > 0) {
            JSONObject first = staff.optJSONObject(0);
            if (first != null) return first.optString("name", "");
        }
        return "";
    }

'''
    if marker in s:
        s = s.replace(marker, helpers + marker)
    else:
        print('UYARI: helper marker bulunamadı, MainActivity helper eklenemedi.')
p.write_text(s, encoding="utf-8")
print("MainActivity maç türü/stat/forma no görünüm patch'i uygulandı.")
