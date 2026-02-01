package com.exteragram.messenger.plugins.utils;

import java.io.File;
import org.telegram.messenger.ApplicationLoader;
import org.telegram.messenger.FileLog;

/* loaded from: classes.dex */
public class NativeCrashHandler {
    private static final String CRASH_FLAG_FILENAME = "native_crash.flag";

    public static native void init(String str);

    public static void checkAndHandleNativeCrash() {
        File file = new File(ApplicationLoader.getFilesDirFixed(), CRASH_FLAG_FILENAME);
        if (file.exists()) {
            FileLog.e("Native crash detected. Enabling safe mode for plugins.");
            ApplicationLoader.applicationContext.getSharedPreferences("plugin_settings", 0).edit().putBoolean("had_crash", true).apply();
            file.delete();
        }
    }

    public static String getCrashFlagPath() {
        return new File(ApplicationLoader.getFilesDirFixed(), CRASH_FLAG_FILENAME).getAbsolutePath();
    }
}
