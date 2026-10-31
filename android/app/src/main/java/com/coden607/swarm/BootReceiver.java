package com.coden607.swarm;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** Restarts background swarm alerts after the phone reboots. */
public class BootReceiver extends BroadcastReceiver {
    @Override public void onReceive(Context c, Intent i) {
        if (Intent.ACTION_BOOT_COMPLETED.equals(i.getAction())) AlertService.start(c);
    }
}
