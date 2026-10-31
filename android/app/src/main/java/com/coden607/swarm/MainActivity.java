package com.coden607.swarm;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.view.Gravity;
import android.view.ViewGroup;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageButton;
import android.widget.Toast;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import java.net.HttpURLConnection;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.net.URL;
import java.util.Collections;
import java.util.concurrent.ExecutorCompletionService;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;

public class MainActivity extends Activity {
    private WebView web;
    private SharedPreferences prefs;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        prefs = getSharedPreferences("swarm", MODE_PRIVATE);
        getWindow().setStatusBarColor(0xff05060f);
        getWindow().setNavigationBarColor(0xff05060f);
        if (Build.VERSION.SDK_INT >= 33) requestPermissions(new String[]{Manifest.permission.CAMERA, Manifest.permission.POST_NOTIFICATIONS}, 1);
        else requestPermissions(new String[]{Manifest.permission.CAMERA}, 1);

        FrameLayout root = new FrameLayout(this);
        web = new WebView(this);
        web.setBackgroundColor(0xff05060f);  // no white flash before the dark dashboard paints
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setSupportMultipleWindows(false);
        web.setWebChromeClient(new WebChromeClient() {
            @Override public void onPermissionRequest(PermissionRequest r) { r.grant(r.getResources()); }
        });
        web.setWebViewClient(new WebViewClient() {
            @Override public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request.getUrl();
                String scheme = uri.getScheme();
                if (scheme == null) return false;
                // Keep http/https inside the app. Everything else (intent:, market:, etc.) is ignored so nothing else opens.
                if ("http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme)) {
                    view.loadUrl(uri.toString());
                    return true;
                }
                return true; // swallow non-web schemes so no other app launches
            }
            @Override public void onPageFinished(WebView v, String url) { grabToken(); }
            @Override public void onReceivedError(WebView v, WebResourceRequest req, WebResourceError e) {
                if (req.isForMainFrame()) {
                    v.loadDataWithBaseURL(null,
                        "<body style='font-family:sans-serif;background:#05060f;color:#e8ecff;padding:2rem;text-align:center'>"
                        + "<h2>Swarm server unreachable</h2><p>Check Wi-Fi and the server address (gear button).</p>"
                        + "<button onclick='location.href=\"" + prefs.getString("server", "") + "\"' style='font-size:1.2rem;padding:.6rem 1.2rem'>Retry</button></body>",
                        "text/html", "utf-8", null);
                }
            }
        });
        root.addView(web, new FrameLayout.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT));

        ImageButton gear = new ImageButton(this);
        gear.setImageResource(android.R.drawable.ic_menu_manage);
        gear.setBackgroundColor(0x66000000);
        gear.setOnClickListener(v -> ask());
        FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(120, 120, Gravity.TOP | Gravity.END);
        root.addView(gear, lp);
        setContentView(root);

        String server = prefs.getString("server", "");
        if (server.isEmpty()) discover(); else web.loadUrl(server);
    }

    private void ask() {
        EditText in = new EditText(this);
        in.setHint("192.168.1.20:8000 or https link");
        in.setText(prefs.getString("server", ""));
        new AlertDialog.Builder(this)
            .setTitle("Swarm server address")
            .setView(in)
            .setCancelable(false)
            .setNeutralButton("Find automatically", (d, w) -> discover())
            .setNegativeButton(prefs.getBoolean("alerts", true) ? "Background alerts: ON" : "Background alerts: OFF", (d, w) -> {
                boolean on = !prefs.getBoolean("alerts", true);
                prefs.edit().putBoolean("alerts", on).apply();
                if (on) AlertService.start(this); else stopService(new Intent(this, AlertService.class));
                Toast.makeText(this, on ? "Swarm alerts on, even when the app is closed" : "Background alerts off", Toast.LENGTH_LONG).show();
            })
            .setPositiveButton("Connect", (d, w) -> {
                String v = in.getText().toString().trim();
                if (v.isEmpty()) return;
                if (!v.contains("://")) v = "http://" + v;
                prefs.edit().putString("server", v).apply();
                web.loadUrl(v);
            })
            .show();
    }

    private final Handler ui = new Handler(Looper.getMainLooper());

    /** Copies the dashboard's sign-in token so AlertService can watch for swarms while the app is closed. */
    private void grabToken() {
        web.evaluateJavascript("(function(){try{return localStorage.getItem('swarm_token')}catch(e){return null}})()", v -> {
            if (v != null && v.length() > 10 && !v.equals("null")) {
                String t = v.replace("\"", "");
                if (!t.equals(prefs.getString("token", ""))) prefs.edit().putString("token", t).apply();
                AlertService.start(this);
            }
        });
    }

    @Override protected void onResume() {
        super.onResume();
        ui.postDelayed(new Runnable() { @Override public void run() { if (!isFinishing()) { grabToken(); ui.postDelayed(this, 20000); } } }, 5000);
    }

    @Override protected void onPause() { super.onPause(); ui.removeCallbacksAndMessages(null); }

    /** Finds a Swarm server with no typing: this phone (Termux) first, then the Wi-Fi network (port 8000). */
    private void discover() {
        Toast.makeText(this, "Looking for your Swarm server...", Toast.LENGTH_LONG).show();
        new Thread(() -> {
            String found = probe("http://127.0.0.1:8000");
            if (found == null) found = scanLan();
            final String f = found;
            runOnUiThread(() -> {
                if (f != null) { prefs.edit().putString("server", f).apply(); web.loadUrl(f); }
                else { Toast.makeText(this, "No Swarm server found on this network.", Toast.LENGTH_LONG).show(); ask(); }
            });
        }).start();
    }

    private static String probe(String base) {
        try {
            HttpURLConnection c = (HttpURLConnection) new URL(base + "/health").openConnection();
            c.setConnectTimeout(700); c.setReadTimeout(1200);
            if (c.getResponseCode() != 200) return null;
            byte[] buf = new byte[256]; int n = c.getInputStream().read(buf);
            return n > 0 && new String(buf, 0, n).contains("status") ? base : null;
        } catch (Exception e) { return null; }
    }

    private static String scanLan() {
        try {
            String prefix = null;
            for (NetworkInterface ni : Collections.list(NetworkInterface.getNetworkInterfaces())) {
                for (InetAddress a : Collections.list(ni.getInetAddresses())) {
                    if (a instanceof Inet4Address && a.isSiteLocalAddress()) {
                        String ip = a.getHostAddress();
                        prefix = ip.substring(0, ip.lastIndexOf('.') + 1);
                    }
                }
            }
            if (prefix == null) return null;
            ExecutorService ex = Executors.newFixedThreadPool(64);
            ExecutorCompletionService<String> cs = new ExecutorCompletionService<>(ex);
            for (int i = 1; i < 255; i++) { final String base = "http://" + prefix + i + ":8000"; cs.submit(() -> probe(base)); }
            String hit = null;
            long end = System.currentTimeMillis() + 15000;
            for (int i = 0; i < 254 && hit == null; i++) {
                Future<String> f = cs.poll(Math.max(1, end - System.currentTimeMillis()), TimeUnit.MILLISECONDS);
                if (f == null) break;
                hit = f.get();
            }
            ex.shutdownNow();
            return hit;
        } catch (Exception e) { return null; }
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) web.goBack(); else super.onBackPressed();
    }
}
