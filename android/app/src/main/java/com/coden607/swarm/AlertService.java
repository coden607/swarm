package com.coden607.swarm;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.ServiceInfo;
import android.os.Build;
import android.os.IBinder;
import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import org.json.JSONArray;
import org.json.JSONObject;

/** Polls the Swarm server and raises a phone notification when a swarm starts, even with the app closed. */
public class AlertService extends Service {
    private static final String RUN = "swarm_run", ALERT = "swarm_alert";
    private volatile boolean running;
    private boolean lastAlarm;
    private int failures;

    static void start(Context c) {
        SharedPreferences p = c.getSharedPreferences("swarm", MODE_PRIVATE);
        if (!p.getBoolean("alerts", true) || p.getString("token", "").isEmpty() || p.getString("server", "").isEmpty()) return;
        Intent i = new Intent(c, AlertService.class);
        try {
            if (Build.VERSION.SDK_INT >= 26) c.startForegroundService(i); else c.startService(i);
        } catch (Exception ignored) { }
    }

    @Override public void onCreate() {
        super.onCreate();
        if (Build.VERSION.SDK_INT >= 26) {
            NotificationManager nm = getSystemService(NotificationManager.class);
            nm.createNotificationChannel(new NotificationChannel(RUN, "Swarm watching", NotificationManager.IMPORTANCE_MIN));
            NotificationChannel a = new NotificationChannel(ALERT, "Swarm alerts", NotificationManager.IMPORTANCE_HIGH);
            a.enableVibration(true);
            a.setVibrationPattern(new long[]{0, 400, 200, 400, 200, 800});
            nm.createNotificationChannel(a);
        }
    }

    private Notification.Builder builder(String ch) {
        Notification.Builder b = Build.VERSION.SDK_INT >= 26 ? new Notification.Builder(this, ch) : new Notification.Builder(this);
        Intent open = new Intent(this, MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        return b.setContentIntent(PendingIntent.getActivity(this, 0, open, PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT));
    }

    @Override public int onStartCommand(Intent intent, int flags, int startId) {
        Notification n = builder(RUN).setSmallIcon(android.R.drawable.ic_menu_view)
            .setContentTitle("Swarm is watching your cameras").setContentText("You'll be alerted if a swarm is detected").setOngoing(true).build();
        if (Build.VERSION.SDK_INT >= 29) startForeground(1, n, ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC); else startForeground(1, n);
        if (!running) { running = true; new Thread(this::loop, "swarm-alerts").start(); }
        return START_STICKY;
    }

    private void loop() {
        while (running) {
            try { poll(); } catch (Exception e) { failures++; }
            try { Thread.sleep(15000); } catch (InterruptedException e) { return; }
        }
    }

    private void poll() throws Exception {
        SharedPreferences p = getSharedPreferences("swarm", MODE_PRIVATE);
        String server = p.getString("server", ""), token = p.getString("token", "");
        if (server.isEmpty() || token.isEmpty() || !p.getBoolean("alerts", true)) { stopSelf(); running = false; return; }
        HttpURLConnection c = (HttpURLConnection) new URL(server.replaceAll("/+$", "") + "/status").openConnection();
        c.setConnectTimeout(5000); c.setReadTimeout(8000);
        c.setRequestProperty("Authorization", "Bearer " + token);
        if (c.getResponseCode() == 401) { p.edit().remove("token").apply(); return; }  // signed out: open the app to sign in again
        InputStream in = c.getInputStream();
        ByteArrayOutputStream buf = new ByteArrayOutputStream();
        byte[] b = new byte[4096]; int n;
        while ((n = in.read(b)) > 0) buf.write(b, 0, n);
        JSONObject j = new JSONObject(buf.toString("UTF-8"));
        failures = 0;
        boolean alarm = j.optBoolean("alarm");
        if (alarm && !lastAlarm) {
            StringBuilder where = new StringBuilder();
            JSONArray cams = j.optJSONArray("cameras");
            for (int i = 0; cams != null && i < cams.length(); i++) {
                JSONObject cam = cams.getJSONObject(i);
                if (cam.optBoolean("alarm")) where.append(where.length() > 0 ? ", " : "").append(cam.optString("id")).append(" (").append(cam.optInt("count")).append(")");
            }
            String text = j.optInt("total") + " people" + (where.length() > 0 ? " - " + where : " across all cameras");
            Notification a = builder(ALERT).setSmallIcon(android.R.drawable.ic_dialog_alert)
                .setContentTitle("Swarm detected").setContentText(text).setAutoCancel(true)
                .setPriority(Notification.PRIORITY_MAX).setCategory(Notification.CATEGORY_ALARM).build();
            getSystemService(NotificationManager.class).notify(2, a);
        }
        lastAlarm = alarm;
    }

    @Override public void onDestroy() { running = false; super.onDestroy(); }
    @Override public IBinder onBind(Intent i) { return null; }
}
