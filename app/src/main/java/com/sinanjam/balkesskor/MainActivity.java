package com.sinanjam.balkesskor;

import android.app.Activity;
import android.app.AlertDialog;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.pm.PackageInfo;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkInfo;
import android.net.Uri;
import android.view.Gravity;
import android.view.View;
import android.view.Window;
import android.widget.Button;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final String BASE_DATA_URL = "https://raw.githubusercontent.com/Sinanjam/balkes-skor/main/data/";
    private static final String LATEST_RELEASE_API = "https://api.github.com/repos/Sinanjam/balkes-skor/releases/latest";
    private static final String LATEST_RELEASE_URL = "https://github.com/Sinanjam/balkes-skor/releases/latest";

    private final ExecutorService executor = Executors.newSingleThreadExecutor();
    private final Handler ui = new Handler(Looper.getMainLooper());

    private LinearLayout root;
    private LinearLayout content;
    private LinearLayout navBar;
    private JSONObject manifest;
    private JSONArray availableSeasons;
    private String currentSeasonId = "2025-2026";
    private final ArrayList<NavState> backStack = new ArrayList<NavState>();
    private int standingsBaseChildren = 1;

    private final int red = Color.rgb(230, 0, 18);
    private final int redSoft = Color.rgb(145, 11, 22);
    private final int bg = Color.rgb(10, 11, 15);
    private final int surface = Color.rgb(22, 24, 31);
    private final int surface2 = Color.rgb(31, 34, 43);
    private final int stroke = Color.rgb(62, 65, 76);
    private final int text = Color.rgb(247, 247, 247);
    private final int muted = Color.rgb(174, 178, 190);
    private final int green = Color.rgb(60, 190, 120);
    private final int yellow = Color.rgb(245, 190, 70);

    private static class NavState {
        String screen;
        String arg;
        NavState(String screen, String arg) { this.screen = screen; this.arg = arg; }
    }

    interface JsonCallback {
        void ok(Object json);
        void fail(String message);
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Window w = getWindow();
        if (android.os.Build.VERSION.SDK_INT >= 21) {
            w.setStatusBarColor(Color.BLACK);
            w.setNavigationBarColor(Color.BLACK);
        }
        showSplash();
        startAppChecks();
    }

    @Override
    protected void onDestroy() {
        executor.shutdownNow();
        super.onDestroy();
    }

    private void showSplash() {
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER);
        root.setPadding(dp(28), dp(28), dp(28), dp(28));
        root.setBackground(gradient(bg, Color.rgb(35, 8, 13)));
        setContentView(root);

        ImageView logo = new ImageView(this);
        logo.setImageResource(getResources().getIdentifier("logo_balkes_skor", "drawable", getPackageName()));
        logo.setAdjustViewBounds(true);
        LinearLayout.LayoutParams lpLogo = new LinearLayout.LayoutParams(dp(172), dp(172));
        lpLogo.setMargins(0, 0, 0, dp(18));
        root.addView(logo, lpLogo);

        TextView title = new TextView(this);
        title.setText("Balkes Skor");
        title.setTextColor(text);
        title.setTextSize(30);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setGravity(Gravity.CENTER);
        root.addView(title);

        TextView sub = new TextView(this);
        sub.setText("Balıkesirspor maç merkezi");
        sub.setTextColor(muted);
        sub.setTextSize(14);
        sub.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams lpSub = new LinearLayout.LayoutParams(-1, -2);
        lpSub.setMargins(0, dp(4), 0, dp(22));
        root.addView(sub, lpSub);

        ProgressBar pb = new ProgressBar(this);
        root.addView(pb, new LinearLayout.LayoutParams(dp(44), dp(44)));

        TextView loading = new TextView(this);
        loading.setText("Yükleniyor...");
        loading.setTextColor(muted);
        loading.setTextSize(13);
        loading.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams lpLoad = new LinearLayout.LayoutParams(-1, -2);
        lpLoad.setMargins(0, dp(16), 0, 0);
        root.addView(loading, lpLoad);
    }

    private void startAppChecks() {
        executor.execute(new Runnable() {
            public void run() {
                if (!isOnline()) {
                    ui.post(new Runnable() { public void run() { showOffline(); } });
                    return;
                }
                try {
                    String latestRaw = fetchUrl(LATEST_RELEASE_API);
                    JSONObject latest = new JSONObject(latestRaw);
                    String tag = latest.optString("tag_name", "").trim();
                    String htmlUrl = latest.optString("html_url", LATEST_RELEASE_URL);
                    if (isNewerTag(tag)) {
                        final String fTag = tag;
                        final String fUrl = htmlUrl;
                        ui.post(new Runnable() { public void run() { showUpdateRequired(fTag, fUrl); } });
                        return;
                    }
                } catch (Exception ignored) {
                    // Release kontrolü geçici aksarsa veri kontrolü devam etsin.
                }

                try {
                    String m = fetchUrl(BASE_DATA_URL + "manifest.json");
                    manifest = new JSONObject(m);
                    availableSeasons = manifest.optJSONArray("availableSeasons");
                    if (availableSeasons != null && availableSeasons.length() > 0) {
                        JSONObject first = availableSeasons.optJSONObject(0);
                        if (first != null) currentSeasonId = first.optString("id", currentSeasonId);
                    }
                    ui.post(new Runnable() { public void run() { buildShell(); openRootHome(); } });
                } catch (Exception ex) {
                    ui.post(new Runnable() { public void run() { showOffline(); } });
                }
            }
        });
    }

    private String getAppVersionName() {
        try {
            PackageInfo info = getPackageManager().getPackageInfo(getPackageName(), 0);
            if (info != null && info.versionName != null) return info.versionName;
        } catch (Exception ignored) {
        }
        return "0.0.0";
    }

    private boolean isNewerTag(String tag) {
        if (tag == null || tag.length() == 0) return false;
        String clean = tag.startsWith("v") ? tag.substring(1) : tag;
        String current = getAppVersionName();
        return !(clean.equals(current) || tag.equals(current));
    }

    private void showOffline() {
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER);
        root.setPadding(dp(28), dp(28), dp(28), dp(28));
        root.setBackgroundColor(bg);
        setContentView(root);

        ImageView logo = new ImageView(this);
        logo.setImageResource(getResources().getIdentifier("logo_balkes_skor", "drawable", getPackageName()));
        root.addView(logo, new LinearLayout.LayoutParams(dp(126), dp(126)));

        TextView title = new TextView(this);
        title.setText("Uygulama için internete bağlanın");
        title.setTextColor(text);
        title.setTextSize(21);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        title.setGravity(Gravity.CENTER);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(-1, -2);
        lp.setMargins(0, dp(22), 0, dp(8));
        root.addView(title, lp);

        TextView sub = new TextView(this);
        sub.setText("Balkes Skor güncel maç verisini internet üzerinden alır.");
        sub.setTextColor(muted);
        sub.setTextSize(14);
        sub.setGravity(Gravity.CENTER);
        root.addView(sub, new LinearLayout.LayoutParams(-1, -2));

        Button retry = redButton("Tekrar dene");
        retry.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { showSplash(); startAppChecks(); } });
        LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(-1, dp(50));
        bp.setMargins(0, dp(24), 0, 0);
        root.addView(retry, bp);
    }

    private void showUpdateRequired(String tag, final String url) {
        AlertDialog.Builder b = new AlertDialog.Builder(this);
        b.setTitle("Güncelleme var");
        b.setMessage("Balkes Skor için yeni sürüm hazır: " + tag);
        b.setCancelable(false);
        b.setPositiveButton("Güncelle", new DialogInterface.OnClickListener() {
            public void onClick(DialogInterface dialog, int which) { openUrl(url == null || url.length() == 0 ? LATEST_RELEASE_URL : url); }
        });
        b.show();
    }

    private void buildShell() {
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(bg);
        setContentView(root);
        if (android.os.Build.VERSION.SDK_INT >= 21) {
            getWindow().setStatusBarColor(Color.BLACK);
            getWindow().setNavigationBarColor(Color.BLACK);
        }

        LinearLayout header = new LinearLayout(this);
        header.setOrientation(LinearLayout.HORIZONTAL);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(dp(14), dp(12), dp(14), dp(12));
        header.setBackground(gradient(redSoft, red));
        root.addView(header, new LinearLayout.LayoutParams(-1, dp(82)));

        ImageView logo = new ImageView(this);
        logo.setImageResource(getResources().getIdentifier("logo_balkes_skor", "drawable", getPackageName()));
        logo.setAdjustViewBounds(true);
        header.addView(logo, new LinearLayout.LayoutParams(dp(56), dp(56)));

        LinearLayout titles = new LinearLayout(this);
        titles.setOrientation(LinearLayout.VERTICAL);
        titles.setPadding(dp(12), 0, 0, 0);
        header.addView(titles, new LinearLayout.LayoutParams(0, -1, 1));

        TextView title = new TextView(this);
        title.setText("Balkes Skor");
        title.setTextColor(Color.WHITE);
        title.setTextSize(24);
        title.setTypeface(Typeface.DEFAULT_BOLD);
        titles.addView(title);

        TextView sub = new TextView(this);
        sub.setText("Balıkesirspor maç merkezi");
        sub.setTextColor(Color.WHITE);
        sub.setTextSize(12);
        titles.addView(sub);

        navBar = new LinearLayout(this);
        navBar.setOrientation(LinearLayout.HORIZONTAL);
        navBar.setGravity(Gravity.CENTER);
        navBar.setPadding(dp(10), dp(8), dp(10), dp(8));
        navBar.setBackgroundColor(Color.rgb(13, 14, 19));
        root.addView(navBar, new LinearLayout.LayoutParams(-1, dp(58)));
        addNav("Ana", "home");
        addNav("Maçlar", "matches");
        addNav("Puan", "standings");
        addNav("Oyuncular", "players");

        ScrollView scroll = new ScrollView(this);
        content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(dp(12), dp(12), dp(12), dp(30));
        scroll.addView(content);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));
    }

    private void addNav(String label, final String screen) {
        Button b = navButton(label);
        b.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { go(new NavState(screen, currentSeasonId)); } });
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(0, -1, 1);
        p.setMargins(dp(4), 0, dp(4), 0);
        navBar.addView(b, p);
    }

    private void openRootHome() {
        backStack.clear();
        backStack.add(new NavState("home", currentSeasonId));
        renderCurrent();
    }

    private void go(NavState state) {
        if (state.arg != null && state.arg.length() > 0 && !state.screen.equals("match")) currentSeasonId = state.arg;
        backStack.add(state);
        renderCurrent();
    }

    private void renderCurrent() {
        if (backStack.size() == 0) { openRootHome(); return; }
        NavState s = backStack.get(backStack.size() - 1);
        if (s.arg != null && s.arg.length() > 0 && !s.screen.equals("match")) currentSeasonId = s.arg;
        if ("home".equals(s.screen)) renderHome();
        else if ("matches".equals(s.screen)) renderMatches(currentSeasonId);
        else if ("standings".equals(s.screen)) renderStandings(currentSeasonId);
        else if ("players".equals(s.screen)) renderPlayers();
        else if ("match".equals(s.screen)) renderMatch(s.arg);
    }

    @Override
    public void onBackPressed() {
        if (backStack.size() > 1) {
            backStack.remove(backStack.size() - 1);
            renderCurrent();
        } else {
            confirmExit();
        }
    }

    private void confirmExit() {
        new AlertDialog.Builder(this)
                .setTitle("Çıkmak istiyor musunuz?")
                .setNegativeButton("Hayır", null)
                .setPositiveButton("Evet", new DialogInterface.OnClickListener() { public void onClick(DialogInterface d, int w) { finish(); } })
                .show();
    }

    private void clear(String title) {
        content.removeAllViews();
        TextView h = new TextView(this);
        h.setText(title);
        h.setTextSize(23);
        h.setTypeface(Typeface.DEFAULT_BOLD);
        h.setTextColor(text);
        h.setPadding(dp(2), dp(2), dp(2), dp(12));
        content.addView(h);
    }

    private void renderHome() {
        clear("Ana Sayfa");
        loadJson("seasons/" + currentSeasonId + "/season.json", new JsonCallback() {
            public void ok(final Object seasonObj) {
                loadJson("seasons/" + currentSeasonId + "/matches_index.json", new JsonCallback() {
                    public void ok(Object matchesObj) { drawHome((JSONObject) seasonObj, (JSONArray) matchesObj); }
                    public void fail(String message) { showConnectionMessage(); }
                });
            }
            public void fail(String message) { showConnectionMessage(); }
        });
    }

    private void drawHome(JSONObject season, JSONArray matches) {
        JSONObject summary = season.optJSONObject("summary");
        LinearLayout hero = card();
        text(hero, season.optString("name") + " Sezonu", 20, true, text);
        text(hero, season.optString("competition", "TFF"), 13, false, muted);
        if (summary != null) {
            int total = summary.optInt("matches", summary.optInt("leagueMatches") + summary.optInt("playoffMatches") + summary.optInt("cupMatches"));
            text(hero, total + " maç", 16, true, text);
            text(hero, summary.optInt("wins") + "G  " + summary.optInt("draws") + "B  " + summary.optInt("losses") + "M", 18, true, text);
            text(hero, summary.optInt("goalsFor") + " - " + summary.optInt("goalsAgainst") + "  |  Av. " + summary.optInt("goalDifference"), 14, false, muted);
            if (summary.has("finalRank") && !summary.isNull("finalRank")) text(hero, "Lig sırası: " + summary.optInt("finalRank"), 14, true, red);
        }

        JSONObject last = null;
        for (int i = 0; i < matches.length(); i++) {
            JSONObject m = matches.optJSONObject(i);
            if (m != null && m.optJSONObject("score") != null && m.optJSONObject("score").optBoolean("played", false)) last = m;
        }
        if (last != null) {
            final JSONObject lm = last;
            LinearLayout c = card();
            text(c, "Son Maç", 18, true, text);
            text(c, lm.optString("dateDisplay"), 12, false, muted);
            scoreBoard(c, lm.optString("homeTeam"), score(lm), lm.optString("awayTeam"));
            JSONObject b = lm.optJSONObject("balkes");
            if (b != null) resultChip(c, b.optString("result"));
            c.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { go(new NavState("match", lm.optString("detailUrl"))); } });
        }

        LinearLayout actions = new LinearLayout(this);
        actions.setOrientation(LinearLayout.HORIZONTAL);
        content.addView(actions, new LinearLayout.LayoutParams(-1, -2));
        Button mbtn = redButton("Maçlar");
        mbtn.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { go(new NavState("matches", currentSeasonId)); } });
        Button pbtn = darkButton("Puan Durumu");
        pbtn.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { go(new NavState("standings", currentSeasonId)); } });
        LinearLayout.LayoutParams ap = new LinearLayout.LayoutParams(0, dp(50), 1);
        ap.setMargins(0, 0, dp(6), dp(10));
        actions.addView(mbtn, ap);
        LinearLayout.LayoutParams ap2 = new LinearLayout.LayoutParams(0, dp(50), 1);
        ap2.setMargins(dp(6), 0, 0, dp(10));
        actions.addView(pbtn, ap2);

        drawSeasonCards();
    }

    private void drawSeasonCards() {
        if (availableSeasons == null || availableSeasons.length() == 0) return;
        TextView h = sectionTitle("Sezonlar");
        content.addView(h);
        for (int i = 0; i < availableSeasons.length(); i++) {
            final JSONObject s = availableSeasons.optJSONObject(i);
            if (s == null) continue;
            LinearLayout c = compactCard();
            text(c, s.optString("name") + "  •  " + s.optInt("matchCount") + " maç", 16, true, text);
            text(c, s.optString("competition", "TFF"), 12, false, muted);
            c.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { currentSeasonId = s.optString("id", currentSeasonId); go(new NavState("matches", currentSeasonId)); } });
        }
    }

    private void renderMatches(final String seasonId) {
        clear("Maçlar");
        seasonChooser("matches");
        loadJson("seasons/" + seasonId + "/matches_index.json", new JsonCallback() {
            public void ok(Object json) {
                JSONArray arr = (JSONArray) json;
                for (int i = 0; i < arr.length(); i++) {
                    final JSONObject m = arr.optJSONObject(i);
                    if (m == null) continue;
                    LinearLayout c = card();
                    String stage = m.optString("stage");
                    text(c, stage + " • " + m.optString("dateDisplay"), 12, true, muted);
                    scoreBoard(c, m.optString("homeTeam"), score(m), m.optString("awayTeam"));
                    JSONObject b = m.optJSONObject("balkes");
                    if (b != null) resultChip(c, b.optString("result"));
                    c.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { go(new NavState("match", m.optString("detailUrl"))); } });
                }
            }
            public void fail(String message) { showConnectionMessage(); }
        });
    }

    private void renderMatch(final String detailPath) {
        clear("Maç Detayı");
        loadJson(detailPath, new JsonCallback() {
            public void ok(Object json) { drawMatch((JSONObject) json); }
            public void fail(String message) { showConnectionMessage(); }
        });
    }

    private void drawMatch(JSONObject m) {
        LinearLayout top = card();
        text(top, m.optString("stage") + " • " + m.optString("dateDisplay"), 13, false, muted);
        scoreBoard(top, m.optString("homeTeam"), score(m), m.optString("awayTeam"));
        JSONObject b = m.optJSONObject("balkes");
        if (b != null) resultChip(top, b.optString("result"));
        if (m.optString("venue", "").length() > 0) text(top, "Stat: " + m.optString("venue"), 13, false, muted);
        JSONArray refs = m.optJSONArray("referees");
        if (refs != null && refs.length() > 0) {
            JSONObject r = refs.optJSONObject(0);
            if (r != null) text(top, "Hakem: " + r.optString("name"), 13, false, muted);
        }

        JSONArray events = m.optJSONArray("events");
        if (events != null && events.length() > 0) {
            drawEvents("Goller", events, new String[]{"goal", "own_goal"});
            drawEvents("Kartlar", events, new String[]{"card", "yellow_card", "red_card"});
            drawEvents("Değişiklikler", events, new String[]{"substitution"});
        }
        JSONObject lineups = m.optJSONObject("lineups");
        if (lineups != null) {
            drawLineup(lineups.optJSONObject("home"));
            drawLineup(lineups.optJSONObject("away"));
        }
    }

    private void drawEvents(String title, JSONArray all, String[] types) {
        LinearLayout c = null;
        for (int i = 0; i < all.length(); i++) {
            JSONObject e = all.optJSONObject(i);
            if (e == null || !contains(types, e.optString("type"))) continue;
            if (c == null) { c = card(); text(c, title, 18, true, text); }
            text(c, eventLine(e), 14, false, text);
        }
    }

    private void drawLineup(JSONObject side) {
        if (side == null) return;
        JSONArray start = side.optJSONArray("starting11");
        JSONArray subs = side.optJSONArray("substitutes");
        if ((start == null || start.length() == 0) && (subs == null || subs.length() == 0)) return;
        LinearLayout c = card();
        text(c, side.optString("team"), 18, true, text);
        if (side.optString("coach", "").length() > 0) text(c, "Teknik sorumlu: " + side.optString("coach"), 12, false, muted);
        if (start != null && start.length() > 0) {
            text(c, "İlk 11", 15, true, red);
            for (int i = 0; i < start.length(); i++) {
                JSONObject p = start.optJSONObject(i);
                if (p != null) text(c, cleanNo(p.optString("shirt_no")) + "  " + p.optString("name"), 13, false, text);
            }
        }
        if (subs != null && subs.length() > 0) {
            text(c, "Yedekler", 15, true, red);
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < subs.length(); i++) {
                JSONObject p = subs.optJSONObject(i);
                if (p != null) {
                    if (sb.length() > 0) sb.append(" • ");
                    sb.append(cleanNo(p.optString("shirt_no"))).append(" ").append(p.optString("name"));
                }
            }
            text(c, sb.toString(), 12, false, muted);
        }
    }

    private void renderStandings(final String seasonId) {
        clear("Puan Durumu");
        seasonChooser("standings");
        standingsBaseChildren = content.getChildCount();
        loadJson("seasons/" + seasonId + "/standings_by_week.json", new JsonCallback() {
            public void ok(Object json) {
                JSONArray weeks = (JSONArray) json;
                if (weeks.length() == 0) {
                    LinearLayout c = card();
                    text(c, "Bu sezon için puan durumu yok.", 16, true, text);
                    text(c, "Maç listesi ve maç detayları kullanılabilir.", 13, false, muted);
                    return;
                }
                drawStandingsWeek(weeks, weeks.length() - 1);
            }
            public void fail(String message) { showConnectionMessage(); }
        });
    }

    private void drawStandingsWeek(final JSONArray weeks, final int idx) {
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
        text(c, "Hafta " + snap.optInt("week"), 17, true, text);
        JSONArray arr = snap.optJSONArray("standings");
        if (arr == null) return;
        for (int i = 0; i < arr.length(); i++) {
            JSONObject t = arr.optJSONObject(i);
            if (t == null) continue;
            TextView row = text(c, t.optInt("rank") + ". " + t.optString("team") + "   " + t.optInt("played") + "O  " + t.optInt("won") + "G  " + t.optInt("drawn") + "B  " + t.optInt("lost") + "M   " + t.optInt("points") + "P", t.optBoolean("isBalkes") ? 15 : 12, t.optBoolean("isBalkes"), t.optBoolean("isBalkes") ? red : text);
            row.setPadding(0, dp(5), 0, dp(5));
        }
    }

    private void renderPlayers() {
        clear("Oyuncular");
        loadJson("players_index.json", new JsonCallback() {
            public void ok(Object json) {
                JSONArray arr = (JSONArray) json;
                int limit = Math.min(arr.length(), 80);
                for (int i = 0; i < limit; i++) {
                    JSONObject p = arr.optJSONObject(i);
                    if (p == null) continue;
                    LinearLayout c = compactCard();
                    text(c, p.optString("name"), 16, true, text);
                    text(c, p.optInt("appearances") + " maç • " + p.optInt("starts") + " ilk 11 • " + p.optInt("goals") + " gol", 13, false, muted);
                }
            }
            public void fail(String message) { showConnectionMessage(); }
        });
    }

    private void seasonChooser(final String targetScreen) {
        if (availableSeasons == null || availableSeasons.length() <= 1) return;
        LinearLayout wrap = new LinearLayout(this);
        wrap.setOrientation(LinearLayout.HORIZONTAL);
        wrap.setPadding(0, 0, 0, dp(8));
        content.addView(wrap);
        for (int i = 0; i < Math.min(availableSeasons.length(), 4); i++) {
            final JSONObject s = availableSeasons.optJSONObject(i);
            if (s == null) continue;
            Button b = currentSeasonId.equals(s.optString("id")) ? redButton(s.optString("name")) : darkButton(s.optString("name"));
            b.setTextSize(11);
            b.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { currentSeasonId = s.optString("id", currentSeasonId); go(new NavState(targetScreen, currentSeasonId)); } });
            LinearLayout.LayoutParams bp = new LinearLayout.LayoutParams(0, dp(42), 1);
            bp.setMargins(dp(2), 0, dp(2), 0);
            wrap.addView(b, bp);
        }
    }

    private void showConnectionMessage() {
        content.removeAllViews();
        LinearLayout c = card();
        text(c, "Uygulama için internete bağlanın", 18, true, text);
        text(c, "Veri alınamadı. Bağlantınızı kontrol edip tekrar deneyin.", 13, false, muted);
        Button retry = redButton("Tekrar dene");
        retry.setOnClickListener(new View.OnClickListener() { public void onClick(View v) { showSplash(); startAppChecks(); } });
        c.addView(retry);
    }

    private void loadJson(final String path, final JsonCallback cb) {
        executor.execute(new Runnable() {
            public void run() {
                if (!isOnline()) {
                    ui.post(new Runnable() { public void run() { cb.fail("internet yok"); } });
                    return;
                }
                try {
                    String txt = fetchUrl(BASE_DATA_URL + path);
                    final Object json = txt.trim().startsWith("[") ? new JSONArray(txt) : new JSONObject(txt);
                    ui.post(new Runnable() { public void run() { cb.ok(json); } });
                } catch (Exception ex) {
                    ui.post(new Runnable() { public void run() { cb.fail("veri alınamadı"); } });
                }
            }
        });
    }

    private String fetchUrl(String urlText) throws Exception {
        URL url = new URL(urlText);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setConnectTimeout(7000);
        conn.setReadTimeout(12000);
        conn.setRequestProperty("User-Agent", "BalkesSkor-Android");
        int code = conn.getResponseCode();
        if (code < 200 || code >= 300) throw new RuntimeException("HTTP " + code);
        return readStream(conn.getInputStream());
    }

    private boolean isOnline() {
        try {
            ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
            if (cm == null) return false;
            if (android.os.Build.VERSION.SDK_INT >= 23) {
                Network n = cm.getActiveNetwork();
                if (n == null) return false;
                NetworkCapabilities nc = cm.getNetworkCapabilities(n);
                return nc != null && (nc.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) || nc.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR) || nc.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET));
            } else {
                NetworkInfo info = cm.getActiveNetworkInfo();
                return info != null && info.isConnected();
            }
        } catch (Exception ex) { return false; }
    }

    private String readStream(InputStream input) throws Exception {
        BufferedReader br = new BufferedReader(new InputStreamReader(input, StandardCharsets.UTF_8));
        StringBuilder sb = new StringBuilder();
        String line;
        while ((line = br.readLine()) != null) sb.append(line).append('\n');
        br.close();
        return sb.toString();
    }

    private void openUrl(String u) {
        try { startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(u))); } catch (Exception ignored) { }
    }

    private boolean contains(String[] arr, String v) {
        for (String a : arr) if (a.equals(v)) return true;
        return false;
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
        return "";
    }

    private void resultChip(LinearLayout parent, String code) {
        TextView tv = new TextView(this);
        tv.setText(resultText(code));
        tv.setTextColor(Color.WHITE);
        tv.setTextSize(12);
        tv.setTypeface(Typeface.DEFAULT_BOLD);
        tv.setGravity(Gravity.CENTER);
        int color = "W".equals(code) ? green : ("D".equals(code) ? yellow : redSoft);
        tv.setBackground(round(color, dp(14), color));
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(dp(116), dp(30));
        p.setMargins(0, dp(8), 0, 0);
        parent.addView(tv, p);
    }

    private void scoreBoard(LinearLayout parent, String home, String score, String away) {
        TextView h = text(parent, home, 15, true, text);
        h.setGravity(Gravity.CENTER);
        TextView s = text(parent, score, 28, true, Color.WHITE);
        s.setGravity(Gravity.CENTER);
        TextView a = text(parent, away, 15, true, text);
        a.setGravity(Gravity.CENTER);
    }

    private String eventLine(JSONObject e) {
        String min = e.optString("minute_text", "");
        if (min.length() == 0 && e.has("minute")) min = e.optString("minute") + ". dk";
        String type = e.optString("type");
        String team = e.optString("team");
        if ("goal".equals(type)) return min + "  ⚽  " + e.optString("player") + "  •  " + team;
        if ("own_goal".equals(type)) return min + "  ⚽  " + e.optString("player") + " (K.K.)  •  " + team;
        if ("card".equals(type) || "yellow_card".equals(type) || "red_card".equals(type)) return min + "  🟨  " + e.optString("player") + "  •  " + team;
        if ("substitution".equals(type)) return min + "  ⇄  " + e.optString("player_in") + " / " + e.optString("player_out") + "  •  " + team;
        return min + "  " + team;
    }

    private String cleanNo(String no) { return no == null ? "" : no.replace(".", ""); }

    private LinearLayout card() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(14), dp(12), dp(14), dp(12));
        box.setBackground(round(surface, dp(20), stroke));
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, -2);
        p.setMargins(0, 0, 0, dp(12));
        content.addView(box, p);
        return box;
    }

    private LinearLayout compactCard() {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(12), dp(10), dp(12), dp(10));
        box.setBackground(round(surface2, dp(16), stroke));
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, -2);
        p.setMargins(0, 0, 0, dp(8));
        content.addView(box, p);
        return box;
    }

    private LinearLayout row(LinearLayout parent) {
        LinearLayout r = new LinearLayout(this);
        r.setOrientation(LinearLayout.HORIZONTAL);
        r.setGravity(Gravity.CENTER_VERTICAL);
        parent.addView(r, new LinearLayout.LayoutParams(-1, -2));
        return r;
    }

    private TextView sectionTitle(String value) {
        TextView tv = new TextView(this);
        tv.setText(value);
        tv.setTextSize(18);
        tv.setTypeface(Typeface.DEFAULT_BOLD);
        tv.setTextColor(text);
        tv.setPadding(dp(2), dp(8), dp(2), dp(8));
        return tv;
    }

    private TextView text(LinearLayout parent, String value, int sp, boolean bold, int color) {
        TextView tv = new TextView(this);
        tv.setText(value == null ? "" : value);
        tv.setTextSize(sp);
        tv.setTextColor(color);
        tv.setPadding(0, dp(2), 0, dp(2));
        if (bold) tv.setTypeface(Typeface.DEFAULT_BOLD);
        parent.addView(tv);
        return tv;
    }

    private Button navButton(String label) {
        Button b = new Button(this);
        b.setText(label);
        b.setAllCaps(false);
        b.setTextSize(12);
        b.setTextColor(Color.WHITE);
        b.setTypeface(Typeface.DEFAULT_BOLD);
        b.setBackground(round(surface2, dp(14), stroke));
        return b;
    }

    private Button redButton(String value) {
        Button b = new Button(this);
        b.setText(value);
        b.setAllCaps(false);
        b.setTextColor(Color.WHITE);
        b.setTypeface(Typeface.DEFAULT_BOLD);
        b.setBackground(round(red, dp(14), red));
        return b;
    }

    private Button darkButton(String value) {
        Button b = new Button(this);
        b.setText(value);
        b.setAllCaps(false);
        b.setTextColor(Color.WHITE);
        b.setTypeface(Typeface.DEFAULT_BOLD);
        b.setBackground(round(surface2, dp(14), stroke));
        return b;
    }

    private GradientDrawable round(int color, int radius, int strokeColor) {
        GradientDrawable d = new GradientDrawable();
        d.setColor(color);
        d.setCornerRadius(radius);
        d.setStroke(dp(1), strokeColor);
        return d;
    }

    private GradientDrawable gradient(int c1, int c2) {
        GradientDrawable d = new GradientDrawable(GradientDrawable.Orientation.TL_BR, new int[]{c1, c2});
        return d;
    }

    private int dp(int v) { return (int) (v * getResources().getDisplayMetrics().density + 0.5f); }
}
