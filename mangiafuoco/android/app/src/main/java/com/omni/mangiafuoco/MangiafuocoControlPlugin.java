package com.omni.mangiafuoco;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.provider.Settings;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

@CapacitorPlugin(name = "MangiafuocoControl")
public class MangiafuocoControlPlugin extends Plugin {

    private HotwordReceiver hotwordReceiver;

    @Override
    protected void handleOnDestroy() {
        if (hotwordReceiver != null) {
            try {
                getContext().unregisterReceiver(hotwordReceiver);
            } catch (IllegalArgumentException ignored) {}
            hotwordReceiver = null;
        }
        super.handleOnDestroy();
    }

    @PluginMethod
    public void openApp(PluginCall call) {
        String packageName = call.getString("packageName");
        if (packageName == null) {
            call.reject("packageName is required");
            return;
        }
        PackageManager pm = getContext().getPackageManager();
        Intent launchIntent = pm.getLaunchIntentForPackage(packageName);
        if (launchIntent != null) {
            launchIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            getContext().startActivity(launchIntent);
            call.resolve();
        } else {
            call.reject("App not installed: " + packageName);
        }
    }

    @PluginMethod
    public void openSettings(PluginCall call) {
        String action = call.getString("action", Settings.ACTION_SETTINGS);
        Intent intent = new Intent(action);
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        try {
            getContext().startActivity(intent);
            call.resolve();
        } catch (Exception e) {
            call.reject("Cannot open settings: " + e.getMessage());
        }
    }

    @PluginMethod
    public void uninstallApp(PluginCall call) {
        String packageName = call.getString("packageName");
        if (packageName == null) {
            call.reject("packageName is required");
            return;
        }
        Intent intent = new Intent(Intent.ACTION_UNINSTALL_PACKAGE);
        intent.setData(Uri.parse("package:" + packageName));
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
        getContext().startActivity(intent);
        call.resolve();
    }

    @PluginMethod
    public void startHotword(PluginCall call) {
        String keyword = call.getString("keyword", "mangiafuoco");
        Context ctx = getContext();
        Intent intent = new Intent(ctx, MangiafuocoHotwordService.class);
        intent.setAction(MangiafuocoHotwordService.ACTION_START);
        intent.putExtra("keyword", keyword);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            ctx.startForegroundService(intent);
        } else {
            ctx.startService(intent);
        }

        if (hotwordReceiver == null) {
            hotwordReceiver = new HotwordReceiver();
            IntentFilter filter = new IntentFilter(MangiafuocoHotwordService.ACTION_HOTWORD);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                ctx.registerReceiver(hotwordReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
            } else {
                ctx.registerReceiver(hotwordReceiver, filter);
            }
        }
        call.resolve();
    }

    @PluginMethod
    public void stopHotword(PluginCall call) {
        Context ctx = getContext();
        Intent intent = new Intent(ctx, MangiafuocoHotwordService.class);
        intent.setAction(MangiafuocoHotwordService.ACTION_STOP);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            ctx.startForegroundService(intent);
        } else {
            ctx.startService(intent);
        }
        call.resolve();
    }

    private class HotwordReceiver extends BroadcastReceiver {
        @Override
        public void onReceive(Context context, Intent intent) {
            if (MangiafuocoHotwordService.ACTION_HOTWORD.equals(intent.getAction())) {
                JSObject data = new JSObject();
                data.put("keyword", intent.getStringExtra("keyword"));
                notifyListeners("hotword", data);
            }
        }
    }
}
