package com.omni.mangiafuoco;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.IBinder;
import android.Manifest;

import androidx.core.app.NotificationCompat;
import androidx.core.content.ContextCompat;

import org.vosk.Model;
import org.vosk.Recognizer;
import org.vosk.android.RecognitionListener;
import org.vosk.android.SpeechService;
import org.vosk.android.StorageService;

import java.io.IOException;

public class MangiafuocoHotwordService extends Service implements RecognitionListener {

    public static final String ACTION_START = "com.omni.mangiafuoco.START_HOTWORD";
    public static final String ACTION_STOP = "com.omni.mangiafuoco.STOP_HOTWORD";
    public static final String ACTION_HOTWORD = "com.omni.mangiafuoco.HOTWORD_DETECTED";

    private static final int NOTIFICATION_ID = 1001;
    private static final String CHANNEL_ID = "mangiafuoco_hotword";

    private Model model;
    private SpeechService speechService;
    private String keyword = "mangiafuoco";

    @Override
    public void onCreate() {
        super.onCreate();
        createNotificationChannel();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_STOP.equals(intent.getAction())) {
            stopSelf();
            return START_NOT_STICKY;
        }

        if (intent != null && intent.hasExtra("keyword")) {
            keyword = intent.getStringExtra("keyword");
        }

        startForeground(NOTIFICATION_ID, buildNotification("In ascolto per \"" + keyword + "\""));

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            stopSelf();
            return START_NOT_STICKY;
        }

        initModel();
        return START_STICKY;
    }

    private void initModel() {
        StorageService.unpack(this, "vosk-model-it", "model",
            (model) -> {
                this.model = model;
                startListening();
            },
            (exception) -> {
                stopSelf();
            });
    }

    private void startListening() {
        if (model == null) return;
        try {
            String grammar = "[\"" + keyword + "\"]";
            Recognizer recognizer = new Recognizer(model, 16000.0f, grammar);
            speechService = new SpeechService(recognizer, 16000.0f);
            speechService.startListening(this);
        } catch (IOException e) {
            stopSelf();
        }
    }

    @Override
    public void onPartialResult(String hypothesis) {
        if (hypothesis != null && hypothesis.toLowerCase().contains(keyword.toLowerCase())) {
            sendHotwordEvent();
        }
    }

    @Override
    public void onResult(String hypothesis) {
        if (hypothesis != null && hypothesis.toLowerCase().contains(keyword.toLowerCase())) {
            sendHotwordEvent();
        }
    }

    @Override
    public void onFinalResult(String hypothesis) {
        restartListening();
    }

    @Override
    public void onError(Exception e) {
        restartListening();
    }

    @Override
    public void onTimeout() {
        restartListening();
    }

    private void restartListening() {
        if (speechService != null) {
            try {
                speechService.startListening(this);
            } catch (IOException e) {
                stopSelf();
            }
        }
    }

    private void sendHotwordEvent() {
        Intent broadcast = new Intent(ACTION_HOTWORD);
        broadcast.putExtra("keyword", keyword);
        sendBroadcast(broadcast);

        Intent appIntent = new Intent(this, MainActivity.class);
        appIntent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        startActivity(appIntent);
    }

    @Override
    public void onDestroy() {
        if (speechService != null) {
            speechService.stop();
            speechService.shutdown();
            speechService = null;
        }
        if (model != null) {
            model.close();
            model = null;
        }
        super.onDestroy();
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    private void createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationChannel channel = new NotificationChannel(
                    CHANNEL_ID,
                    "Mangiafuoco hotword",
                    NotificationManager.IMPORTANCE_LOW);
            channel.setDescription("Ascolto continuo per la parola chiave Mangiafuoco");
            NotificationManager manager = getSystemService(NotificationManager.class);
            if (manager != null) manager.createNotificationChannel(channel);
        }
    }

    private Notification buildNotification(String text) {
        Intent intent = new Intent(this, MainActivity.class);
        intent.addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent pendingIntent = PendingIntent.getActivity(
                this, 0, intent,
                PendingIntent.FLAG_IMMUTABLE | PendingIntent.FLAG_UPDATE_CURRENT);

        return new NotificationCompat.Builder(this, CHANNEL_ID)
                .setContentTitle("Mangiafuoco in ascolto")
                .setContentText(text)
                .setSmallIcon(android.R.drawable.ic_btn_speak_now)
                .setContentIntent(pendingIntent)
                .setOngoing(true)
                .build();
    }
}
