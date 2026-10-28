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

public class MainActivity extends Activity {
    private WebView web;
    private SharedPreferences prefs;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        prefs = getSharedPreferences("swarm", MODE_PRIVATE);
        requestPermissions(new String[]{Manifest.permission.CAMERA}, 1);

        FrameLayout root = new FrameLayout(this);
        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        web.setWebChromeClient(new WebChromeClient() {
            @Override public void onPermissionRequest(PermissionRequest r) { r.grant(r.getResources()); }
        });
        web.setWebViewClient(new WebViewClient() {
            @Override public void onReceivedError(WebView v, WebResourceRequest req, WebResourceError e) {
                if (req.isForMainFrame()) {
                    v.loadDataWithBaseURL(null,
                        "<body style='font-family:sans-serif;background:#111;color:#eee;padding:2rem;text-align:center'>"
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
        if (server.isEmpty()) ask(); else web.loadUrl(server);
    }

    private void ask() {
        EditText in = new EditText(this);
        in.setHint("192.168.1.20:8000 or https link");
        in.setText(prefs.getString("server", ""));
        new AlertDialog.Builder(this)
            .setTitle("Swarm server address")
            .setView(in)
            .setCancelable(false)
            .setPositiveButton("Connect", (d, w) -> {
                String v = in.getText().toString().trim();
                if (v.isEmpty()) return;
                if (!v.contains("://")) v = "http://" + v;
                prefs.edit().putString("server", v).apply();
                web.loadUrl(v);
            })
            .show();
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) web.goBack(); else super.onBackPressed();
    }
}
