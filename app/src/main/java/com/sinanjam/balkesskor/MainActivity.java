package com.sinanjam.balkesskor;

import android.app.Activity;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.content.SharedPreferences;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.view.Gravity;
import android.view.View;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final String BASE_DATA_URL = "https://raw.githubusercontent.com/Sinanjam/balkes-skor/main/data/";
    private static final String DEFAULT_SEASON = "2025-2026";

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler ui = new Handler(Looper.getMainLooper());

    private LinearLayout root;
    private LinearLayout content;
    private TextView statusText;
    private boolean darkMode;

    private final int red = Color.rgb(227, 6, 19);
    private final int white = Color.WHITE;
    private final int textDark = Color.rgb(35, 35, 35);
    private final int bgLight = Color.rgb(248, 248, 248);
    private final int bgDark = Color.rgb(17, 17, 17);
    private final int cardDark = Color.rgb(34, 34, 34);

    interface JsonCallback {
        void ok(Object json);
        void fail(String message);
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        SharedPreferences prefs = getSharedPreferences("balkes_skor", MODE_PRIVATE);
        darkMode = prefs.getBoolean("darkMode", false);
        buildShell();
        showHome();
    }

    @Override
    protected void onDestroy() {
        executor.shutdownNow();
        super.onDestroy();
    }

    private void buildShell() {
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(darkMode ? bgDark : bgLight);
        setContentView(root);
        if (android.os.Build.VERSION.SDK_INT >= 21) {
            getWindow().setStatusBarColor(red);
            getWindow().setNavigationBarColor(darkMode ? Color.BLACK : Color.rgb(230, 230, 230));
        }

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(dp(16), dp(12), dp(16), dp(12));
        header.setBackgroundColor(red);
        root.addView(header, new LinearLayout.LayoutParams(-1, dp(86)));

        ImageView logo = new ImageView(this);
        logo.setImageResource(getResources().getIdentifier("ic_launcher", "mipmap", getPackageName()));
        logo.setAdjustViewBounds(true);
        header.addView(logo, new LinearLayout.LayoutParams(dp(58), dp(58)));

        LinearLayout titleBox = new LinearLayout(this);
        titleBox.setOrientation(LinearLayout.VERTICAL);
        titleBox.setPadding(dp(12), 0, 0, 0);
        header.addView(titleBox, new LinearLayout.LayoutParams(0, -1, 1));

        TextView title = new TextView(this);
        title.setText("Balkes Skor");
        title.setTextColor(Color.WHITE);
        title.setTextSize(24);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        titleBox.addView(title);

        TextView sub = new TextView(this);
        sub.setText("Balıkesirspor maç merkezi • Beta Debug");
        sub.setTextColor(Color.WHITE);
        sub.setTextSize(12);
        titleBox.addView(sub);

        LinearLayout nav = new LinearLayout(this);
        nav.setOrientation(LinearLayout.HORIZONTAL);
        nav.setGravity(Gravity.CENTER);
        nav.setPadding(dp(8), dp(8), dp(8), dp(8));
        nav.setBackgroundColor(darkMode ? Color.rgb(22, 22, 22) : Color.WHITE);
        root.addView(nav, new LinearLayout.LayoutParams(-1, dp(58)));

        nav.addView(navButton("Ana", new View.OnClickListener() { public void onClick(View v) { showHome(); } }), weightParams());
        nav.addView(navButton("Maçlar", new View.OnClickListener() { public void onClick(View v) { showMatches(); } }), weightParams());
        nav.addView(navButton("Puan", new View.OnClickListener() { public void onClick(View v) { showStandings(); } }), weightParams());
        nav.addView(navButton("Ayarlar", new View.OnClickListener() { public void onClick(View v) { showSettings(); } }), weightParams());

        ScrollView scroll = new ScrollView(this);
        content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(12), dp(12), dp(12), dp(28));
        scroll.addView(content);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
    }

    private LinearLayout.LayoutParams weightParams() {
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0, -1, 1);
        p.setMargins(dp(4), 0, dp(4), 0);
        return p;
    }

    private Button navButton(String text, View.OnClickListener listener) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextSize(12);
        b.setTextColor(Color.WHITE);
        b.setAllCaps(false);
        b.setTypeface(Typeface.DEFAULT_BOLD);
        b.setBackground(round(red, dp(14), red));
        b.setOnClickListener(listener);
        return b;
    }

    private void clear(String title) {
        content.removeAllViews();
        TextView h = new TextView(this);
        h.setText(title);
        h.setTextSize(22);
        h.setTypeface(Typeface.DEFAULT_BOLD);
        h.setTextColor(darkMode ? white : textDark);
        h.setPadding(dp(4), dp(2), dp(4), dp(10));
        content.addView(h);

        statusText = new TextView(this);
        statusText.setText("");
        statusText.setTextSize(12);
        statusText.setTextColor(darkMode ? Color.LTGRAY : Color.DKGRAY);
        statusText.setPadding(dp(4), 0, dp(4), dp(8));
        content.addView(statusText);
    }

    private void setStatus(String s) {
        if (statusText != null) statusText.setText(s == null ? "" : s);
    }

    private LinearLayout card() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(14), dp(12), dp(14), dp(12));
        box.setBackground(round(darkMode ? cardDark : Color.WHITE, dp(18), darkMode ? Color.rgb(60, 60, 60) : Color.rgb(230, 230, 230)));
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, -2);
        p.setMargins(0, 0, 0, dp(10));
        content.addView(box, p);
        return box;
    }

    private TextView text(LinearLayout parent, String value, int sp, boolean bold) {
        TextView tv = new TextView(this);
        tv.setText(value == null ? "" : value);
        tv.setTextSize(sp);
        tv.setTextColor(darkMode ? white : textDark);
        tv.setPadding(0, dp(2), 0, dp(2));
        if (bold) tv.setTypeface(Typeface.DEFAULT_BOLD);
        parent.addView(tv);
        return tv;
    }

    private void showHome() {
        clear("Ana Sayfa");
        setStatus("GitHub verisi kontrol ediliyor...");
        loadJson("seasons/" + DEFAULT_SEASON + "/season.json", new JsonCallback() {
            public void ok(final Object seasonObj) {
                loadJson("seasons/" + DEFAULT_SEASON + "/matches_index.json", new JsonCallback() {
                    public void ok(Object matchesObj) {
                        renderHome((JSONObject) seasonObj, (JSONArray) matchesObj);
                    }
                    public void fail(String message) { setStatus(message); }
                });
            }
            public void fail(String message) { setStatus(message); }
        });
    }

    private void renderHome(JSONObject season, JSONArray matches) {
        setStatus("Kaynak: GitHub raw JSON. İnternet yoksa yerel/cache veri kullanılır.");
        JSONObject summary = season.optJSONObject("summary");
        LinearLayout s = card();
        text(s, "2025-2026 Sezon Özeti", 18, true);
        if (summary != null) {
            text(s, summary.optInt("leagueMatches") + " lig maçı • " + summary.optInt("playoffMatches") + " play-off maçı", 14, false);
            text(s, summary.optInt("wins") + "G " + summary.optInt("draws") + "B " + summary.optInt("losses") + "M  |  " + summary.optInt("goalsFor") + "-" + summary.optInt("goalsAgainst") + "  |  " + summary.optInt("points") + " puan", 16, true);
            text(s, "Final sıra: " + summary.optInt("finalRank"), 14, false);
        }

        JSONObject last = null;
        for (int i = 0; i < matches.length(); i++) {
            JSONObject m = matches.optJSONObject(i);
            if (m != null && m.optJSONObject("score") != null && m.optJSONObject("score").optBoolean("played", false)) last = m;
        }
        final JSONObject lastMatch = last;
        if (lastMatch != null) {
            LinearLayout l = card();
            text(l, "Son Kayıtlı Maç", 18, true);
            text(l, lastMatch.optString("stage") + " • " + lastMatch.optString("dateDisplay"), 13, false);
            text(l, lastMatch.optString("homeTeam") + "  " + score(lastMatch) + "  " + lastMatch.optString("awayTeam"), 17, true);
            JSONObject balkes = lastMatch.optJSONObject("balkes");
            if (balkes != null) text(l, "Balkes sonucu: " + resultText(balkes.optString("result")) + " • Rakip: " + balkes.optString("opponent"), 14, false);
            l.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { showMatchDetail(lastMatch); } });
        }

        LinearLayout quick = card();
        text(quick, "Hızlı Erişim", 18, true);
        Button matchesBtn = redButton("Tüm maçları aç");
        matchesBtn.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { showMatches(); } });
        quick.addView(matchesBtn);
        Button standingsBtn = redButton("Puan durumunu aç");
        standingsBtn.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { showStandings(); } });
        quick.addView(standingsBtn);
    }

    private void showMatches() {
        clear("Maçlar");
        setStatus("Maç listesi yükleniyor...");
        loadJson("seasons/" + DEFAULT_SEASON + "/matches_index.json", new JsonCallback() {
            public void ok(Object json) {
                setStatus("2025-2026 • 30 lig + 2 play-off kaydı");
                JSONArray arr = (JSONArray) json;
                for (int i = 0; i < arr.length(); i++) {
                    final JSONObject m = arr.optJSONObject(i);
                    if (m == null) continue;
                    LinearLayout c = card();
                    String round = "playoff".equals(m.optString("roundType")) ? "Play-off" : m.optString("stage");
                    text(c, round + " • " + m.optString("dateDisplay"), 13, false);
                    text(c, m.optString("homeTeam") + "  " + score(m) + "  " + m.optString("awayTeam"), 16, true);
                    JSONObject balkes = m.optJSONObject("balkes");
                    if (balkes != null) text(c, resultText(balkes.optString("result")) + " • " + balkes.optInt("goalsFor") + "-" + balkes.optInt("goalsAgainst"), 13, false);
                    c.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { showMatchDetail(m); } });
                }
            }
            public void fail(String message) { setStatus(message); }
        });
    }

    private void showMatchDetail(JSONObject indexMatch) {
        clear("Maç Detayı");
        String detailUrl = indexMatch.optString("detailUrl", "");
        setStatus("Detay yükleniyor: " + detailUrl);
        loadJson(detailUrl, new JsonCallback() {
            public void ok(Object json) { renderMatchDetail((JSONObject) json); }
            public void fail(String message) { setStatus(message); }
        });
    }

    private void renderMatchDetail(JSONObject m) {
        setStatus("TFF açık verisinden dönüştürülmüş JSON.");
        LinearLayout top = card();
        text(top, m.optString("stage") + " • " + m.optString("dateDisplay"), 13, false);
        text(top, m.optString("homeTeam") + "\n" + score(m) + "\n" + m.optString("awayTeam"), 22, true).setGravity(Gravity.CENTER);
        text(top, "Stat: " + m.optString("venue", "-"), 13, false);
        JSONArray refs = m.optJSONArray("referees");
        if (refs != null && refs.length() > 0) {
            StringBuilder r = new StringBuilder("Hakemler: ");
            for (int i = 0; i < refs.length(); i++) {
                JSONObject ref = refs.optJSONObject(i);
                if (ref != null) {
                    if (i > 0) r.append(", ");
                    r.append(ref.optString("name"));
                }
            }
            text(top, r.toString(), 13, false);
        }

        JSONArray events = m.optJSONArray("events");
        LinearLayout ev = card();
        text(ev, "Olaylar", 18, true);
        if (events == null || events.length() == 0) {
            text(ev, "Olay kaydı yok.", 14, false);
        } else {
            for (int i = 0; i < events.length(); i++) {
                JSONObject e = events.optJSONObject(i);
                if (e == null) continue;
                text(ev, eventLine(e), 14, false);
            }
        }

        JSONObject lineups = m.optJSONObject("lineups");
        if (lineups != null) {
            renderLineup("Ev Sahibi İlk 11", lineups.optJSONObject("home"));
            renderLineup("Deplasman İlk 11", lineups.optJSONObject("away"));
        }
    }

    private void renderLineup(String title, JSONObject side) {
        if (side == null) return;
        LinearLayout c = card();
        text(c, title + " • " + side.optString("team"), 18, true);
        JSONArray start = side.optJSONArray("starting11");
        if (start != null) {
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < start.length(); i++) {
                JSONObject p = start.optJSONObject(i);
                if (p != null) sb.append(p.optString("shirt_no")).append(" ").append(p.optString("name")).append("\n");
            }
            text(c, sb.toString().trim(), 14, false);
        }
        JSONArray subs = side.optJSONArray("substitutes");
        if (subs != null && subs.length() > 0) {
            text(c, "Yedekler", 16, true);
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < subs.length(); i++) {
                JSONObject p = subs.optJSONObject(i);
                if (p != null) sb.append(p.optString("shirt_no")).append(" ").append(p.optString("name")).append("\n");
            }
            text(c, sb.toString().trim(), 13, false);
        }
    }

    private void showStandings() {
        clear("Puan Durumu");
        setStatus("Haftalık puan durumu yükleniyor...");
        loadJson("seasons/" + DEFAULT_SEASON + "/standings_by_week.json", new JsonCallback() {
            public void ok(Object json) { renderStandings((JSONArray) json, -1); }
            public void fail(String message) { setStatus(message); }
        });
    }

    private void renderStandings(final JSONArray weeks, int index) {
        content.removeAllViews();
        TextView h = new TextView(this);
        h.setText("Puan Durumu");
        h.setTextSize(22);
        h.setTypeface(Typeface.DEFAULT_BOLD);
        h.setTextColor(darkMode ? white : textDark);
        h.setPadding(dp(4), dp(2), dp(4), dp(10));
        content.addView(h);
        if (weeks.length() == 0) return;
        final int idx = index < 0 ? weeks.length() - 1 : Math.max(0, Math.min(index, weeks.length() - 1));
        JSONObject snap = weeks.optJSONObject(idx);
        if (snap == null) return;
        TextView info = new TextView(this);
        info.setText("Hafta " + snap.optInt("week") + " / " + weeks.length());
        info.setTextSize(13);
        info.setTextColor(darkMode ? Color.LTGRAY : Color.DKGRAY);
        info.setPadding(dp(4), 0, dp(4), dp(8));
        content.addView(info);

        LinearLayout nav = new LinearLayout(this);
        nav.setOrientation(LinearLayout.HORIZONTAL);
        nav.setPadding(0, 0, 0, dp(8));
        Button prev = redButton("← Önceki");
        Button next = redButton("Sonraki →");
        nav.addView(prev, weightParams());
        nav.addView(next, weightParams());
        content.addView(nav);
        prev.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { renderStandings(weeks, idx - 1); } });
        next.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { renderStandings(weeks, idx + 1); } });

        LinearLayout c = card();
        JSONArray arr = snap.optJSONArray("standings");
        if (arr == null) return;
        for (int i = 0; i < arr.length(); i++) {
            JSONObject t = arr.optJSONObject(i);
            if (t == null) continue;
            String line = t.optInt("rank") + ". " + t.optString("team") + "  " +
                    t.optInt("played") + "O " + t.optInt("won") + "G " + t.optInt("drawn") + "B " + t.optInt("lost") + "M  " +
                    t.optInt("goalsFor") + "-" + t.optInt("goalsAgainst") + "  " + t.optInt("points") + "P";
            TextView row = text(c, line, t.optBoolean("isBalkes") ? 15 : 13, t.optBoolean("isBalkes"));
            if (t.optBoolean("isBalkes")) {
                row.setTextColor(red);
            }
        }
    }

    private void showSettings() {
        clear("Ayarlar");
        setStatus("Build: beta/debug • Actions kullanılmaz.");
        LinearLayout c = card();
        text(c, "Veri Kaynağı", 18, true);
        text(c, BASE_DATA_URL, 13, false);
        text(c, "Uygulama GitHub raw JSON dosyalarını çeker; bağlantı yoksa cache/asset fallback kullanır.", 13, false);

        Button theme = redButton(darkMode ? "Aydınlık temaya geç" : "Karanlık temaya geç");
        theme.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                darkMode = !darkMode;
                getSharedPreferences("balkes_skor", MODE_PRIVATE).edit().putBoolean("darkMode", darkMode).apply();
                buildShell();
                showSettings();
            }
        });
        c.addView(theme);

        Button clear = redButton("Veri cache temizle");
        clear.setOnClickListener(new View.OnClickListener() {
            public void onClick(View v) {
                deleteDir(new File(getCacheDir(), "balkes_data"));
                Toast.makeText(MainActivity.this, "Cache temizlendi", Toast.LENGTH_SHORT).show();
            }
        });
        c.addView(clear);
    }

    private Button redButton(String text) {
        Button b = new Button(this);
        b.setText(text);
        b.setAllCaps(false);
        b.setTextColor(Color.WHITE);
        b.setTypeface(Typeface.DEFAULT_BOLD);
        b.setBackground(round(red, dp(12), red));
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, dp(46));
        p.setMargins(0, dp(8), 0, 0);
        b.setLayoutParams(p);
        return b;
    }

    private String score(JSONObject m) {
        JSONObject s = m.optJSONObject("score");
        if (s == null) return "-";
        return s.optString("display", s.optInt("home") + "-" + s.optInt("away"));
    }

    private String resultText(String code) {
        if ("W".equals(code)) return "Galibiyet";
        if ("D".equals(code)) return "Beraberlik";
        if ("L".equals(code)) return "Mağlubiyet";
        return code == null ? "" : code;
    }

    private String eventLine(JSONObject e) {
        String min = e.optString("minute_text", e.optInt("minute", 0) + ".dk");
        String type = e.optString("type");
        String team = e.optString("team");
        if ("goal".equals(type)) return min + " ⚽ " + team + " • " + e.optString("player");
        if ("yellow_card".equals(type)) return min + " 🟨 " + team + " • " + e.optString("player");
        if ("red_card".equals(type)) return min + " 🟥 " + team + " • " + e.optString("player");
        if ("substitution".equals(type)) return min + " ⇄ " + team + " • " + e.optString("player_in") + " / " + e.optString("player_out");
        return min + " • " + team + " • " + type;
    }

    private void loadJson(final String path, final JsonCallback cb) {
        executor.execute(new Runnable() {
            public void run() {
                try {
                    String txt = tryNetwork(path);
                    if (txt != null && txt.trim().length() > 0) {
                        writeCache(path, txt);
                        deliverOk(txt, cb);
                        return;
                    }
                } catch (Exception ignored) { }
                try {
                    String txt = readCache(path);
                    if (txt != null) {
                        deliverOk(txt, cb);
                        return;
                    }
                } catch (Exception ignored) { }
                try {
                    String txt = readAsset("data/" + path);
                    deliverOk(txt, cb);
                } catch (final Exception ex) {
                    ui.post(new Runnable() { public void run() { cb.fail("Veri okunamadı: " + path + " • " + ex.getMessage()); } });
                }
            }
        });
    }

    private void deliverOk(String txt, final JsonCallback cb) throws Exception {
        final Object json;
        String trimmed = txt.trim();
        if (trimmed.startsWith("[")) json = new JSONArray(trimmed);
        else json = new JSONObject(trimmed);
        ui.post(new Runnable() { public void run() { cb.ok(json); } });
    }

    private String tryNetwork(String path) throws Exception {
        URL url = new URL(BASE_DATA_URL + path);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setConnectTimeout(7000);
        conn.setReadTimeout(10000);
        conn.setRequestProperty("User-Agent", "BalkesSkor-Android-Beta");
        int code = conn.getResponseCode();
        if (code < 200 || code >= 300) throw new RuntimeException("HTTP " + code);
        return readStream(conn.getInputStream());
    }

    private String cacheName(String path) {
        return path.replace('/', '_').replace(':', '_');
    }

    private void writeCache(String path, String txt) throws Exception {
        File dir = new File(getCacheDir(), "balkes_data");
        if (!dir.exists()) dir.mkdirs();
        File f = new File(dir, cacheName(path));
        FileOutputStream out = new FileOutputStream(f);
        out.write(txt.getBytes(StandardCharsets.UTF_8));
        out.close();
    }

    private String readCache(String path) throws Exception {
        File f = new File(new File(getCacheDir(), "balkes_data"), cacheName(path));
        if (!f.exists()) return null;
        return readStream(new FileInputStream(f));
    }

    private String readAsset(String assetPath) throws Exception {
        return readStream(getAssets().open(assetPath));
    }

    private String readStream(InputStream input) throws Exception {
        BufferedReader br = new BufferedReader(new InputStreamReader(input, StandardCharsets.UTF_8));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = br.readLine()) != null) sb.append(line).append('\n');
        br.close();
        return sb.toString();
    }

    private boolean deleteDir(File f) {
        if (f == null || !f.exists()) return true;
        if (f.isDirectory()) {
            File[] children = f.listFiles();
            if (children != null) for (File c : children) deleteDir(c);
        }
        return f.delete();
    }

    private GradientDrawable round(int color, int radius, int strokeColor) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(color);
        d.setCornerRadius(radius);
        d.setStroke(dp(1), strokeColor);
        return d;
    }

    private int dp(int v) {
        return (int) (v * getResources().getDisplayMetrics().density + 0.5f);
    }
}
