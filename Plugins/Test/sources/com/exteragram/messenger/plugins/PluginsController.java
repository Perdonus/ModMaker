package com.exteragram.messenger.plugins;

import android.content.SharedPreferences;
import android.os.Build;
import android.text.TextUtils;
import com.chaquo.python.PyObject;
import com.exteragram.messenger.ExteraConfig;
import com.exteragram.messenger.plugins.PluginsController;
import com.exteragram.messenger.plugins.hooks.EventHookRecord;
import com.exteragram.messenger.plugins.hooks.HookRecord;
import com.exteragram.messenger.plugins.hooks.MenuItemRecord;
import com.exteragram.messenger.plugins.hooks.PluginsHooks;
import com.exteragram.messenger.plugins.hooks.XposedHookRecord;
import com.exteragram.messenger.plugins.models.SettingItem;
import com.exteragram.messenger.plugins.ui.PluginsActivity;
import com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet;
import com.exteragram.messenger.plugins.ui.components.SafeModeBottomSheet;
import com.exteragram.messenger.plugins.utils.MenuContextBuilder;
import com.exteragram.messenger.plugins.utils.NativeCrashHandler;
import com.exteragram.messenger.utils.ChatUtils;
import de.robv.android.xposed.XC_MethodHook;
import j$.lang.Iterable$EL;
import j$.util.Collection;
import j$.util.Comparator;
import j$.util.List;
import j$.util.Map;
import j$.util.Objects;
import j$.util.concurrent.ConcurrentHashMap;
import j$.util.concurrent.ConcurrentMap$EL;
import j$.util.function.BiFunction$CC;
import j$.util.function.Consumer$CC;
import j$.util.function.Function$CC;
import j$.util.function.Predicate$CC;
import j$.util.stream.Collectors;
import java.io.File;
import java.util.AbstractMap;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.concurrent.CopyOnWriteArraySet;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.function.BiFunction;
import java.util.function.Consumer;
import java.util.function.Function;
import java.util.function.Predicate;
import java.util.function.ToIntFunction;
import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.ApplicationLoader;
import org.telegram.messenger.DispatchQueue;
import org.telegram.messenger.FileLog;
import org.telegram.messenger.LocaleController;
import org.telegram.messenger.MessageObject;
import org.telegram.messenger.NotificationCenter;
import org.telegram.messenger.R;
import org.telegram.messenger.SendMessagesHelper;
import org.telegram.messenger.Utilities;
import org.telegram.tgnet.TLObject;
import org.telegram.tgnet.TLRPC;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.Components.BulletinFactory;
import org.telegram.ui.LaunchActivity;

/* loaded from: classes.dex */
public class PluginsController implements PluginsHooks {
    static final String PREF_PLUGIN_ENABLED_KEY_PREFIX = "plugin_enabled_";
    public static final ConcurrentHashMap<String, PluginsEngine> engines;
    private volatile Map<String, List<EventHookRecord>> exactMatchEventHooksCache;
    public File pluginsDir;
    private volatile List<EventHookRecord> substringMatchEventHooksCache;
    public final ConcurrentHashMap<String, Plugin> plugins = new ConcurrentHashMap<>();
    public final ConcurrentHashMap<String, List<SettingItem>> settings = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, MenuItemRecord> menuItemsById = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, CopyOnWriteArrayList<MenuItemRecord>> menuItemsByMenuType = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, Set<HookRecord>> hooks = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, List<String>> interestedPluginsCache = new ConcurrentHashMap<>();
    private final Object hooksCacheLock = new Object();
    private volatile boolean hooksCacheDirty = true;
    public SharedPreferences preferences = ApplicationLoader.applicationContext.getSharedPreferences("plugin_settings", 0);
    private final Runnable updateNotificationRunnable = new Runnable() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda13
        @Override // java.lang.Runnable
        public final void run() {
            PluginsController.m555$r8$lambda$b4UZpx3nWzNShmhdIX8ST6qcpc();
        }
    };

    /* loaded from: classes.dex */
    public interface PluginsEngine {
        boolean canOpenInExternalApp();

        void checkDevServer();

        void clearPluginSettings(String str);

        void deletePlugin(String str, Utilities.Callback<String> callback);

        void executeOnAppEvent(String str);

        HookResult<PluginsHooks.PostRequestResult> executePostRequestHook(String str, int i, TLObject tLObject, TLRPC.TL_error tL_error, String str2);

        HookResult<TLObject> executePreRequestHook(String str, int i, TLObject tLObject, String str2);

        HookResult<SendMessagesHelper.SendMessageParams> executeSendMessageHook(int i, SendMessagesHelper.SendMessageParams sendMessageParams, String str);

        HookResult<TLRPC.Update> executeUpdateHook(String str, int i, TLRPC.Update update, String str2);

        HookResult<TLRPC.Updates> executeUpdatesHook(String str, int i, TLRPC.Updates updates, String str2);

        Map<String, ?> getAllPluginSettings(String str);

        String getPluginPath(String str);

        Object getPluginSetting(String str, String str2, Object obj);

        void init(Runnable runnable);

        boolean isEngineAvailable();

        boolean isPlugin(File file);

        List<SettingItem> loadPluginSettings(String str);

        void openInExternalApp(String str);

        void openPluginSetting(Plugin plugin, String str, BaseFragment baseFragment);

        void openPluginSetting(String str, String str2, BaseFragment baseFragment);

        void openPluginSettings(Plugin plugin, BaseFragment baseFragment);

        void openPluginSettings(String str, BaseFragment baseFragment);

        void setPluginEnabled(String str, boolean z, Utilities.Callback<String> callback);

        void setPluginSetting(String str, String str2, Object obj);

        void sharePlugin(String str);

        void showInstallDialog(BaseFragment baseFragment, InstallPluginBottomSheet.PluginInstallParams pluginInstallParams);

        void shutdown(Runnable runnable);
    }

    public static /* synthetic */ void $r8$lambda$QHAWdjg_nos3ztw400vtKLSsL5c() {
    }

    static {
        Map m;
        m = PluginsController$$ExternalSyntheticBackport1.m(new Map.Entry[]{new AbstractMap.SimpleEntry(PluginsConstants.PYTHON, new PythonPluginsEngine())});
        engines = new ConcurrentHashMap<>(m);
    }

    public static PluginsController getInstance() {
        return SingletonHolder.INSTANCE;
    }

    public static boolean isPluginEngineSupported() {
        return Build.VERSION.SDK_INT >= 24;
    }

    public static boolean isPluginEngineAvailable() {
        if (isPluginEngineSupported() && ExteraConfig.pluginsEngine && !ExteraConfig.pluginsSafeMode) {
            for (PluginsEngine pluginsEngine : engines.values()) {
                if (pluginsEngine != null) {
                    try {
                        if (pluginsEngine.isEngineAvailable()) {
                            return true;
                        }
                    } catch (Throwable th) {
                        FileLog.e("Error checking engine availability.", th);
                    }
                }
            }
        }
        return false;
    }

    public static boolean isPlugin(MessageObject messageObject) {
        String pathToMessage = ChatUtils.getInstance().getPathToMessage(messageObject);
        return (messageObject == null || messageObject.getDocumentName() == null || TextUtils.isEmpty(pathToMessage) || !isPlugin(new File(pathToMessage)) || !isPluginEngineSupported()) ? false : true;
    }

    public static boolean isPlugin(File file) {
        if (file == null) {
            return false;
        }
        Iterator<PluginsEngine> it = engines.values().iterator();
        while (it.hasNext()) {
            if (it.next().isPlugin(file)) {
                return true;
            }
        }
        return false;
    }

    public static PluginsEngine getPluginEngine(File file) {
        if (file == null) {
            return null;
        }
        for (PluginsEngine pluginsEngine : engines.values()) {
            if (pluginsEngine.isPlugin(file)) {
                return pluginsEngine;
            }
        }
        return null;
    }

    public static void openPluginSettings(String str) {
        openPluginSettings(str, null);
    }

    public static void openPluginSettings(String str, String str2) {
        final BaseFragment lastFragment;
        if (TextUtils.isEmpty(str) || (lastFragment = LaunchActivity.getLastFragment()) == null) {
            return;
        }
        if (!ExteraConfig.pluginsEngine) {
            BulletinFactory.of(lastFragment).createSimpleBulletin(R.raw.error, LocaleController.formatString(R.string.PluginEngineNotEnabled, str), LocaleController.getString(R.string.Enable), 2750, new Runnable() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda17
                @Override // java.lang.Runnable
                public final void run() {
                    BaseFragment.this.presentFragment(new PluginsActivity());
                }
            }).show();
            return;
        }
        Plugin plugin = getInstance().plugins.get(str);
        if (plugin == null) {
            BulletinFactory.of(lastFragment).createEmojiBulletin("🤷\u200d♂️", LocaleController.formatString(R.string.PluginNotFound, str)).show();
            return;
        }
        if (!getInstance().hasPluginSettings(str)) {
            BulletinFactory.of(lastFragment).createEmojiBulletin("🤷\u200d♂️", LocaleController.formatString(R.string.PluginHasNoSettings, plugin.getName())).show();
            return;
        }
        PluginsEngine pluginEngine = getInstance().getPluginEngine(str);
        if (pluginEngine != null) {
            if (str2 == null) {
                pluginEngine.openPluginSettings(str, lastFragment);
            } else {
                pluginEngine.openPluginSetting(str, str2, lastFragment);
            }
        }
    }

    public PluginsEngine getPluginEngine(String str) {
        PluginsEngine pluginsEngine = null;
        if (str != null && !TextUtils.isEmpty(str)) {
            Plugin plugin = this.plugins.get(str);
            if (plugin == null) {
                return null;
            }
            PluginsEngine pluginsEngine2 = plugin.cachedEngine;
            if (pluginsEngine2 != null) {
                return pluginsEngine2;
            }
            String engine = plugin.getEngine();
            if (engine == null) {
                return null;
            }
            pluginsEngine = engines.get(engine);
            if (pluginsEngine != null) {
                plugin.cachedEngine = pluginsEngine;
            }
        }
        return pluginsEngine;
    }

    public static boolean isPluginPinned(String str) {
        return !TextUtils.isEmpty(str) && ExteraConfig.pinnedPlugins.contains(str);
    }

    public static void setPluginPinned(String str, boolean z) {
        if (TextUtils.isEmpty(str)) {
            return;
        }
        HashSet hashSet = new HashSet(ExteraConfig.pinnedPlugins);
        if (!z) {
            hashSet.remove(str);
        } else {
            hashSet.add(str);
        }
        ExteraConfig.pinnedPlugins = hashSet;
        ExteraConfig.editor.putStringSet("pinnedPlugins", hashSet).apply();
        getInstance().notifyPluginsChanged();
    }

    public void init() {
        init(null);
    }

    public static void runOnPluginsQueue(Runnable runnable) {
        if (!Utilities.pluginsQueue.isAlive()) {
            synchronized (PluginsController.class) {
                try {
                    if (!Utilities.pluginsQueue.isAlive()) {
                        Utilities.pluginsQueue = new DispatchQueue("pluginsQueue");
                    }
                } finally {
                }
            }
        }
        Utilities.pluginsQueue.postRunnable(runnable);
    }

    public void init(final Runnable runnable) {
        if (!isPluginEngineSupported() || !ExteraConfig.pluginsEngine) {
            if (runnable != null) {
                runnable.run();
                return;
            }
            return;
        }
        NativeCrashHandler.checkAndHandleNativeCrash();
        runOnPluginsQueue(new Runnable() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda14
            @Override // java.lang.Runnable
            public final void run() {
                PluginsController.$r8$lambda$QHAWdjg_nos3ztw400vtKLSsL5c();
            }
        });
        if (this.preferences == null) {
            this.preferences = ApplicationLoader.applicationContext.getSharedPreferences("plugin_settings", 0);
        }
        try {
            boolean z = this.preferences.getBoolean("had_crash", false);
            String string = this.preferences.getString("crashed_plugin_id", null);
            boolean z2 = string != null && string.equals("manual!");
            this.preferences.edit().remove("had_crash").remove("crashed_plugin_id").apply();
            if (z) {
                if (string != null && !z2) {
                    this.preferences.edit().putBoolean(PREF_PLUGIN_ENABLED_KEY_PREFIX + string, false).apply();
                } else {
                    SharedPreferences.Editor editor = ExteraConfig.editor;
                    ExteraConfig.pluginsSafeMode = true;
                    editor.putBoolean("pluginsSafeMode", true).apply();
                }
                if (!z2) {
                    AndroidUtilities.runOnUIThread(new Runnable() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda15
                        @Override // java.lang.Runnable
                        public final void run() {
                            PluginsController.$r8$lambda$_Eg9DLlVzcL2GapKmkTt3lrGdxY();
                        }
                    }, 800L);
                }
            } else {
                SharedPreferences.Editor editor2 = ExteraConfig.editor;
                ExteraConfig.pluginsSafeMode = false;
                editor2.putBoolean("pluginsSafeMode", false).apply();
            }
        } catch (Exception unused) {
        }
        File file = new File(ApplicationLoader.getFilesDirFixed(), PluginsConstants.PLUGINS);
        this.pluginsDir = file;
        if (!file.exists()) {
            this.pluginsDir.mkdirs();
        }
        final AtomicInteger atomicInteger = new AtomicInteger(0);
        Runnable runnable2 = new Runnable() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda16
            @Override // java.lang.Runnable
            public final void run() {
                PluginsController.$r8$lambda$GxNqH3Tn3T0wowPL10edJkONHf4(atomicInteger, runnable);
            }
        };
        Iterator<PluginsEngine> it = engines.values().iterator();
        while (it.hasNext()) {
            it.next().init(runnable2);
        }
    }

    public static /* synthetic */ void $r8$lambda$_Eg9DLlVzcL2GapKmkTt3lrGdxY() {
        BaseFragment lastFragment = LaunchActivity.getLastFragment();
        if (lastFragment != null) {
            new SafeModeBottomSheet(lastFragment).show();
        }
    }

    public static /* synthetic */ void $r8$lambda$GxNqH3Tn3T0wowPL10edJkONHf4(AtomicInteger atomicInteger, Runnable runnable) {
        if (atomicInteger.addAndGet(1) < engines.size() || runnable == null) {
            return;
        }
        runnable.run();
    }

    public void checkDevServers() {
        Iterator<PluginsEngine> it = engines.values().iterator();
        while (it.hasNext()) {
            it.next().checkDevServer();
        }
    }

    public void shutdown(final Runnable runnable) {
        runOnPluginsQueue(new Runnable() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda23
            @Override // java.lang.Runnable
            public final void run() {
                PluginsController.this.lambda$shutdown$5(runnable);
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$shutdown$5(final Runnable runnable) {
        final AtomicInteger atomicInteger = new AtomicInteger(0);
        Runnable runnable2 = new Runnable() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda4
            @Override // java.lang.Runnable
            public final void run() {
                PluginsController.this.lambda$shutdown$4(atomicInteger, runnable);
            }
        };
        Iterator<PluginsEngine> it = engines.values().iterator();
        while (it.hasNext()) {
            it.next().shutdown(runnable2);
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$shutdown$4(AtomicInteger atomicInteger, Runnable runnable) {
        if (atomicInteger.addAndGet(1) >= engines.size()) {
            this.plugins.clear();
            this.settings.clear();
            FileLog.d("Plugin system shut down.");
            if (runnable != null) {
                runnable.run();
            }
        }
    }

    public void restart() {
        FileLog.d("Restarting plugins engine...");
        shutdown(new Runnable() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda8
            @Override // java.lang.Runnable
            public final void run() {
                PluginsController.this.lambda$restart$7();
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$restart$7() {
        if (ExteraConfig.pluginsEngine) {
            init(new Runnable() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda5
                @Override // java.lang.Runnable
                public final void run() {
                    FileLog.d("Plugins engine restarted.");
                }
            });
        }
    }

    public List<SettingItem> getPluginSettingsList(String str) {
        if (TextUtils.isEmpty(str)) {
            return null;
        }
        return this.settings.get(str);
    }

    public void setPluginEnabled(final String str, final boolean z, final Utilities.Callback<String> callback) {
        runOnPluginsQueue(new Runnable() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda10
            @Override // java.lang.Runnable
            public final void run() {
                PluginsController.this.lambda$setPluginEnabled$8(str, z, callback);
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$setPluginEnabled$8(String str, boolean z, Utilities.Callback callback) {
        PluginsEngine pluginEngine = getPluginEngine(str);
        if (pluginEngine != null) {
            pluginEngine.setPluginEnabled(str, z, callback);
            this.interestedPluginsCache.clear();
        }
    }

    public void deletePlugin(final String str, final Utilities.Callback<String> callback) {
        runOnPluginsQueue(new Runnable() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda31
            @Override // java.lang.Runnable
            public final void run() {
                PluginsController.this.lambda$deletePlugin$9(str, callback);
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$deletePlugin$9(String str, Utilities.Callback callback) {
        PluginsEngine pluginEngine = getPluginEngine(str);
        if (pluginEngine != null) {
            pluginEngine.deletePlugin(str, callback);
        }
    }

    /* JADX INFO: Access modifiers changed from: package-private */
    public void cleanupPlugin(String str) {
        removeHooksByPluginId(str);
        invalidatePluginSettings(str);
        removeMenuItemsByPluginId(str);
    }

    public String getPluginPath(String str) {
        PluginsEngine pluginEngine;
        if (str == null || TextUtils.isEmpty(str) || (pluginEngine = getPluginEngine(str)) == null) {
            return null;
        }
        return pluginEngine.getPluginPath(str);
    }

    public void showInstallDialog(BaseFragment baseFragment, MessageObject messageObject) {
        showInstallDialog(baseFragment, InstallPluginBottomSheet.PluginInstallParams.of(messageObject));
    }

    public void showInstallDialog(BaseFragment baseFragment, String str, boolean z) {
        showInstallDialog(baseFragment, new InstallPluginBottomSheet.PluginInstallParams(str, z));
    }

    private void showInstallDialog(final BaseFragment baseFragment, InstallPluginBottomSheet.PluginInstallParams pluginInstallParams) {
        if (baseFragment == null || !AndroidUtilities.isActivityRunning(baseFragment.getParentActivity()) || TextUtils.isEmpty(pluginInstallParams.filePath)) {
            return;
        }
        File file = new File(pluginInstallParams.filePath);
        if (!ExteraConfig.pluginsEngine) {
            BulletinFactory.of(baseFragment).createSimpleBulletin(R.raw.error, LocaleController.formatString(R.string.PluginNotEnabled, file.getName()), LocaleController.getString(R.string.Enable), 2750, new Runnable() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda9
                @Override // java.lang.Runnable
                public final void run() {
                    BaseFragment.this.presentFragment(new PluginsActivity());
                }
            }).show();
            return;
        }
        PluginsEngine pluginEngine = getPluginEngine(file);
        if (pluginEngine == null) {
            return;
        }
        pluginEngine.showInstallDialog(baseFragment, pluginInstallParams);
    }

    public void loadPluginSettings() {
        loadPluginSettings(null);
    }

    /* JADX WARN: Code restructure failed: missing block: B:15:0x0038, code lost:
    
        invalidatePluginSettings(r0);
     */
    /*
        Code decompiled incorrectly, please refer to instructions dump.
        To view partially-correct add '--show-bad-code' argument
    */
    public void loadPluginSettings(final java.lang.String r4) {
        /*
            r3 = this;
            boolean r0 = android.text.TextUtils.isEmpty(r4)
            if (r0 == 0) goto L3d
            j$.util.concurrent.ConcurrentHashMap<java.lang.String, com.exteragram.messenger.plugins.Plugin> r4 = r3.plugins
            java.util.Set r4 = r4.keySet()
            java.util.Iterator r4 = r4.iterator()
        L10:
            boolean r0 = r4.hasNext()
            if (r0 == 0) goto L3c
            java.lang.Object r0 = r4.next()
            java.lang.String r0 = (java.lang.String) r0
            j$.util.concurrent.ConcurrentHashMap<java.lang.String, com.exteragram.messenger.plugins.Plugin> r1 = r3.plugins
            java.lang.Object r1 = r1.get(r0)
            com.exteragram.messenger.plugins.Plugin r1 = (com.exteragram.messenger.plugins.Plugin) r1
            if (r1 == 0) goto L36
            boolean r2 = r1.isEnabled()
            if (r2 == 0) goto L36
            java.lang.Throwable r2 = r1.getError()
            if (r2 != 0) goto L36
            r3.loadPluginSettings(r0)
            goto L10
        L36:
            if (r1 == 0) goto L10
            r3.invalidatePluginSettings(r0)
            goto L10
        L3c:
            return
        L3d:
            com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda11 r0 = new com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda11
            r0.<init>()
            runOnPluginsQueue(r0)
            return
        */
        throw new UnsupportedOperationException("Method not decompiled: com.exteragram.messenger.plugins.PluginsController.loadPluginSettings(java.lang.String):void");
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$loadPluginSettings$12(final String str) {
        try {
            PluginsEngine pluginEngine = getPluginEngine(str);
            if (pluginEngine == null) {
                return;
            }
            List<SettingItem> loadPluginSettings = pluginEngine.loadPluginSettings(str);
            if (loadPluginSettings == null) {
                invalidatePluginSettings(str);
                return;
            }
            this.settings.put(str, loadPluginSettings);
            FileLog.d("Registered settings for plugin " + str);
            AndroidUtilities.runOnUIThread(new Runnable() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda32
                @Override // java.lang.Runnable
                public final void run() {
                    NotificationCenter.getGlobalInstance().lambda$postNotificationNameOnUIThread$1(NotificationCenter.pluginSettingsRegistered, str);
                }
            });
        } catch (Throwable th) {
            FileLog.e(th);
            invalidatePluginSettings(str);
        }
    }

    public boolean hasPluginSettings(String str) {
        return !TextUtils.isEmpty(str) && this.settings.containsKey(str);
    }

    public void invalidatePluginSettings(final String str) {
        if (TextUtils.isEmpty(str)) {
            return;
        }
        this.settings.remove(str);
        AndroidUtilities.runOnUIThread(new Runnable() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda12
            @Override // java.lang.Runnable
            public final void run() {
                NotificationCenter.getGlobalInstance().lambda$postNotificationNameOnUIThread$1(NotificationCenter.pluginSettingsUnregistered, str);
            }
        });
    }

    public void clearPluginSettingsPreferences(String str) {
        if (TextUtils.isEmpty(str)) {
            return;
        }
        PluginsEngine pluginEngine = getPluginEngine(str);
        if (pluginEngine != null) {
            pluginEngine.clearPluginSettings(str);
        }
        if (this.preferences == null) {
            return;
        }
        String str2 = PREF_PLUGIN_ENABLED_KEY_PREFIX + str;
        if (this.preferences.contains(str2)) {
            this.preferences.edit().remove(str2).apply();
        }
    }

    public Map<String, ?> getPluginSettingsPreferences(String str) {
        PluginsEngine pluginEngine = getPluginEngine(str);
        if (pluginEngine != null) {
            return pluginEngine.getAllPluginSettings(str);
        }
        return null;
    }

    public boolean hasPluginSettingsPreferences(String str) {
        Map<String, ?> pluginSettingsPreferences = getPluginSettingsPreferences(str);
        return (pluginSettingsPreferences == null || pluginSettingsPreferences.isEmpty()) ? false : true;
    }

    public boolean getPluginSettingBoolean(String str, String str2, boolean z) {
        PluginsEngine pluginEngine = getPluginEngine(str);
        if (pluginEngine != null) {
            Object pluginSetting = pluginEngine.getPluginSetting(str, str2, Boolean.valueOf(z));
            if (pluginSetting instanceof Boolean) {
                return ((Boolean) pluginSetting).booleanValue();
            }
        }
        return z;
    }

    public String getPluginSettingString(String str, String str2, String str3) {
        Object pluginSetting;
        PluginsEngine pluginEngine = getPluginEngine(str);
        return (pluginEngine == null || (pluginSetting = pluginEngine.getPluginSetting(str, str2, str3)) == null) ? str3 : pluginSetting.toString();
    }

    public int getPluginSettingInt(String str, String str2, int i) {
        PluginsEngine pluginEngine = getPluginEngine(str);
        if (pluginEngine != null) {
            Object pluginSetting = pluginEngine.getPluginSetting(str, str2, Integer.valueOf(i));
            if (pluginSetting instanceof Number) {
                return ((Number) pluginSetting).intValue();
            }
        }
        return i;
    }

    public void setPluginSetting(String str, String str2, Object obj) {
        PluginsEngine pluginEngine = getPluginEngine(str);
        if (pluginEngine != null) {
            pluginEngine.setPluginSetting(str, str2, obj);
            loadPluginSettings(str);
        }
    }

    private void addHook(String str, HookRecord hookRecord, String str2) {
        if (TextUtils.isEmpty(str) || hookRecord == null || !((Set) ConcurrentMap$EL.computeIfAbsent(this.hooks, str, new Function() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda20
            public /* synthetic */ Function andThen(Function function) {
                return Function$CC.$default$andThen(this, function);
            }

            @Override // java.util.function.Function
            public final Object apply(Object obj) {
                return PluginsController.m553$r8$lambda$FYukywYKGo_wPdhFkDnrIRWDhw((String) obj);
            }

            public /* synthetic */ Function compose(Function function) {
                return Function$CC.$default$compose(this, function);
            }
        })).add(hookRecord)) {
            return;
        }
        FileLog.d(str2);
        this.interestedPluginsCache.clear();
        this.hooksCacheDirty = true;
    }

    /* renamed from: $r8$lambda$FYukyw-YKGo_wPdhFkDnrIRWDhw, reason: not valid java name */
    public static /* synthetic */ Set m553$r8$lambda$FYukywYKGo_wPdhFkDnrIRWDhw(String str) {
        return new CopyOnWriteArraySet();
    }

    public void addEventHook(String str, String str2, boolean z, int i) {
        addHook(str, new EventHookRecord(str, str2, z, i), "Added event hook '" + str2 + "' for plugin " + str);
    }

    private void removeHook(String str, Predicate<HookRecord> predicate, String str2) {
        Set<HookRecord> set;
        if (TextUtils.isEmpty(str) || (set = this.hooks.get(str)) == null || set.isEmpty()) {
            return;
        }
        ArrayList arrayList = new ArrayList();
        ArrayList arrayList2 = new ArrayList();
        for (HookRecord hookRecord : set) {
            if (predicate.test(hookRecord)) {
                arrayList2.add(hookRecord);
            } else {
                arrayList.add(hookRecord);
            }
        }
        if (arrayList2.isEmpty()) {
            return;
        }
        Iterable$EL.forEach(arrayList2, new Consumer() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda18
            @Override // java.util.function.Consumer
            /* renamed from: accept */
            public final void v(Object obj) {
                ((HookRecord) obj).cleanup();
            }

            public /* synthetic */ Consumer andThen(Consumer consumer) {
                return Consumer$CC.$default$andThen(this, consumer);
            }
        });
        if (arrayList.isEmpty()) {
            this.hooks.remove(str);
        } else {
            this.hooks.put(str, new CopyOnWriteArraySet(arrayList));
        }
        FileLog.d(str2);
        this.interestedPluginsCache.clear();
        this.hooksCacheDirty = true;
    }

    /* renamed from: $r8$lambda$0MKBwYBnp1INQdsep3RmAg-7Dyg, reason: not valid java name */
    public static /* synthetic */ boolean m551$r8$lambda$0MKBwYBnp1INQdsep3RmAg7Dyg(String str, HookRecord hookRecord) {
        return (hookRecord instanceof EventHookRecord) && Objects.equals(((EventHookRecord) hookRecord).getHookName(), str);
    }

    public void removeEventHook(String str, final String str2) {
        removeHook(str, new Predicate() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda19
            public /* synthetic */ Predicate and(Predicate predicate) {
                return Predicate$CC.$default$and(this, predicate);
            }

            public /* synthetic */ Predicate negate() {
                return Predicate$CC.$default$negate(this);
            }

            public /* synthetic */ Predicate or(Predicate predicate) {
                return Predicate$CC.$default$or(this, predicate);
            }

            @Override // java.util.function.Predicate
            public final boolean test(Object obj) {
                return PluginsController.m551$r8$lambda$0MKBwYBnp1INQdsep3RmAg7Dyg(str2, (HookRecord) obj);
            }
        }, "Removed event hook(s) matching name '" + str2 + "' for plugin " + str);
    }

    public void addXposedHook(String str, XC_MethodHook.Unhook unhook) {
        addHook(str, new XposedHookRecord(unhook), "Added Xposed hook for plugin " + str);
    }

    public void addXposedHooks(String str, ArrayList<XC_MethodHook.Unhook> arrayList) {
        if (arrayList == null) {
            return;
        }
        int size = arrayList.size();
        int i = 0;
        while (i < size) {
            XC_MethodHook.Unhook unhook = arrayList.get(i);
            i++;
            addXposedHook(str, unhook);
        }
    }

    public static /* synthetic */ boolean $r8$lambda$D7iuh79ccD5yYXeFej0RROjlm5A(XC_MethodHook.Unhook unhook, HookRecord hookRecord) {
        return (hookRecord instanceof XposedHookRecord) && hookRecord.matches(unhook);
    }

    public void removeXposedHook(String str, final XC_MethodHook.Unhook unhook) {
        removeHook(str, new Predicate() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda7
            public /* synthetic */ Predicate and(Predicate predicate) {
                return Predicate$CC.$default$and(this, predicate);
            }

            public /* synthetic */ Predicate negate() {
                return Predicate$CC.$default$negate(this);
            }

            public /* synthetic */ Predicate or(Predicate predicate) {
                return Predicate$CC.$default$or(this, predicate);
            }

            @Override // java.util.function.Predicate
            public final boolean test(Object obj) {
                return PluginsController.$r8$lambda$D7iuh79ccD5yYXeFej0RROjlm5A(XC_MethodHook.Unhook.this, (HookRecord) obj);
            }
        }, "Removed Xposed hook for plugin " + str);
    }

    public void removeHooksByPluginId(String str) {
        Set<HookRecord> remove;
        if (TextUtils.isEmpty(str) || (remove = this.hooks.remove(str)) == null) {
            return;
        }
        Iterator<HookRecord> it = remove.iterator();
        while (it.hasNext()) {
            it.next().cleanup();
        }
        FileLog.d("Removed all (" + remove.size() + ") hooks for plugin " + str);
        this.interestedPluginsCache.clear();
        this.hooksCacheDirty = true;
    }

    public String addMenuItem(String str, PyObject pyObject) {
        if (isPluginEngineAvailable() && pyObject != null) {
            try {
                final MenuItemRecord menuItemRecord = new MenuItemRecord(str, pyObject);
                if (menuItemRecord.menuType == null) {
                    return null;
                }
                MenuItemRecord menuItemRecord2 = this.menuItemsById.get(menuItemRecord.itemId);
                if (menuItemRecord2 != null && !menuItemRecord2.pluginId.equals(str)) {
                    FileLog.w(String.format("Plugin %s tried to add a menu item: %s, which is already used by plugin %s", str, menuItemRecord.itemId, menuItemRecord2.pluginId));
                    return null;
                }
                this.menuItemsById.put(menuItemRecord.itemId, menuItemRecord);
                ConcurrentMap$EL.compute(this.menuItemsByMenuType, menuItemRecord.menuType, new BiFunction() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda2
                    public /* synthetic */ BiFunction andThen(Function function) {
                        return BiFunction$CC.$default$andThen(this, function);
                    }

                    @Override // java.util.function.BiFunction
                    public final Object apply(Object obj, Object obj2) {
                        return PluginsController.$r8$lambda$Rghq_G_pJLYBjuuBNY5w2Zx4URE(MenuItemRecord.this, (String) obj, (CopyOnWriteArrayList) obj2);
                    }
                });
                FileLog.d("Added menu item: " + menuItemRecord.itemId + " for plugin " + str + " in type " + menuItemRecord.menuType);
                AndroidUtilities.runOnUIThread(new Runnable() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda3
                    @Override // java.lang.Runnable
                    public final void run() {
                        NotificationCenter.getGlobalInstance().lambda$postNotificationNameOnUIThread$1(NotificationCenter.pluginMenuItemsUpdated, new Object[0]);
                    }
                });
                return menuItemRecord.itemId;
            } catch (Exception unused) {
            }
        }
        return null;
    }

    public static /* synthetic */ CopyOnWriteArrayList $r8$lambda$Rghq_G_pJLYBjuuBNY5w2Zx4URE(final MenuItemRecord menuItemRecord, String str, CopyOnWriteArrayList copyOnWriteArrayList) {
        ArrayList arrayList;
        if (copyOnWriteArrayList == null) {
            arrayList = new ArrayList();
        } else {
            arrayList = new ArrayList(copyOnWriteArrayList);
            Collection.EL.removeIf(arrayList, new Predicate() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda24
                public /* synthetic */ Predicate and(Predicate predicate) {
                    return Predicate$CC.$default$and(this, predicate);
                }

                public /* synthetic */ Predicate negate() {
                    return Predicate$CC.$default$negate(this);
                }

                public /* synthetic */ Predicate or(Predicate predicate) {
                    return Predicate$CC.$default$or(this, predicate);
                }

                @Override // java.util.function.Predicate
                public final boolean test(Object obj) {
                    boolean equals;
                    equals = ((MenuItemRecord) obj).itemId.equals(MenuItemRecord.this.itemId);
                    return equals;
                }
            });
        }
        arrayList.add(menuItemRecord);
        List.EL.sort(arrayList, Comparator.EL.reversed(Comparator.CC.comparingInt(new ToIntFunction() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda25
            @Override // java.util.function.ToIntFunction
            public final int applyAsInt(Object obj) {
                int i;
                i = ((MenuItemRecord) obj).priority;
                return i;
            }
        })));
        return new CopyOnWriteArrayList(arrayList);
    }

    public boolean removeMenuItem(String str, String str2) {
        MenuItemRecord remove;
        if (TextUtils.isEmpty(str2) || (remove = this.menuItemsById.remove(str2)) == null || remove.menuType == null) {
            return false;
        }
        if (!remove.pluginId.equals(str)) {
            this.menuItemsById.put(str2, remove);
            return false;
        }
        CopyOnWriteArrayList<MenuItemRecord> copyOnWriteArrayList = this.menuItemsByMenuType.get(remove.menuType);
        if (copyOnWriteArrayList != null) {
            copyOnWriteArrayList.remove(remove);
        }
        FileLog.d("Removed menu item: " + str2 + " for plugin " + str);
        AndroidUtilities.runOnUIThread(new Runnable() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda21
            @Override // java.lang.Runnable
            public final void run() {
                NotificationCenter.getGlobalInstance().lambda$postNotificationNameOnUIThread$1(NotificationCenter.pluginMenuItemsUpdated, new Object[0]);
            }
        });
        return true;
    }

    public void removeMenuItemsByPluginId(String str) {
        if (TextUtils.isEmpty(str)) {
            return;
        }
        ArrayList arrayList = new ArrayList();
        for (MenuItemRecord menuItemRecord : this.menuItemsById.values()) {
            if (menuItemRecord.pluginId.equals(str)) {
                arrayList.add(menuItemRecord.itemId);
            }
        }
        int size = arrayList.size();
        int i = 0;
        while (i < size) {
            Object obj = arrayList.get(i);
            i++;
            removeMenuItem(str, (String) obj);
        }
        FileLog.d("Removed all menu items for plugin: " + str);
    }

    public java.util.List<MenuItemRecord> getMenuItemsForLocation(String str, MenuContextBuilder menuContextBuilder) {
        if (menuContextBuilder == null) {
            return getMenuItemsForLocation(str, new HashMap());
        }
        return getMenuItemsForLocation(str, menuContextBuilder.build());
    }

    public java.util.List<MenuItemRecord> getMenuItemsForLocation(String str, Map<String, Object> map) {
        if (!isPluginEngineAvailable() || TextUtils.isEmpty(str)) {
            return Collections.EMPTY_LIST;
        }
        CopyOnWriteArrayList<MenuItemRecord> copyOnWriteArrayList = this.menuItemsByMenuType.get(str);
        if (copyOnWriteArrayList == null || copyOnWriteArrayList.isEmpty()) {
            return Collections.EMPTY_LIST;
        }
        ArrayList arrayList = new ArrayList();
        Iterator<MenuItemRecord> it = copyOnWriteArrayList.iterator();
        while (it.hasNext()) {
            MenuItemRecord next = it.next();
            Plugin plugin = this.plugins.get(next.pluginId);
            if (plugin != null && plugin.isEnabled() && !plugin.hasError() && next.checkCondition(map)) {
                arrayList.add(next);
            }
        }
        return arrayList;
    }

    /* renamed from: $r8$lambda$b4-UZpx3nWzNShmhdIX8ST6qcpc, reason: not valid java name */
    public static /* synthetic */ void m555$r8$lambda$b4UZpx3nWzNShmhdIX8ST6qcpc() {
        NotificationCenter.getGlobalInstance().lambda$postNotificationNameOnUIThread$1(NotificationCenter.pluginsUpdated, new Object[0]);
        NotificationCenter.getGlobalInstance().lambda$postNotificationNameOnUIThread$1(NotificationCenter.pluginMenuItemsUpdated, new Object[0]);
    }

    /* JADX INFO: Access modifiers changed from: package-private */
    public void notifyPluginsChanged() {
        AndroidUtilities.cancelRunOnUIThread(this.updateNotificationRunnable);
        AndroidUtilities.runOnUIThread(this.updateNotificationRunnable, 150L);
    }

    public void executeOnAppEvent(final String str) {
        if (isPluginEngineAvailable()) {
            FileLog.d("Execute scripts on app event " + str);
            Iterable$EL.forEach(engines.values(), new Consumer() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda6
                @Override // java.util.function.Consumer
                /* renamed from: accept */
                public final void v(Object obj) {
                    PluginsController.$r8$lambda$fkOEc2l7S3Khbq5IvdTb1K9rydw(str, (PluginsController.PluginsEngine) obj);
                }

                public /* synthetic */ Consumer andThen(Consumer consumer) {
                    return Consumer$CC.$default$andThen(this, consumer);
                }
            });
        }
    }

    public static /* synthetic */ void $r8$lambda$fkOEc2l7S3Khbq5IvdTb1K9rydw(String str, PluginsEngine pluginsEngine) {
        if (pluginsEngine != null) {
            pluginsEngine.executeOnAppEvent(str);
        }
    }

    java.util.List<String> getInterestedPluginIds(String str) {
        if (TextUtils.isEmpty(str)) {
            return Collections.EMPTY_LIST;
        }
        java.util.List<String> list = this.interestedPluginsCache.get(str);
        if (list == null) {
            rebuildHooksCacheIfNeeded();
            HashMap hashMap = new HashMap();
            java.util.List<EventHookRecord> list2 = this.exactMatchEventHooksCache.get(str);
            if (list2 != null) {
                for (final EventHookRecord eventHookRecord : list2) {
                    Map.EL.compute(hashMap, eventHookRecord.getPluginId(), new BiFunction() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda26
                        public /* synthetic */ BiFunction andThen(Function function) {
                            return BiFunction$CC.$default$andThen(this, function);
                        }

                        @Override // java.util.function.BiFunction
                        public final Object apply(Object obj, Object obj2) {
                            Integer valueOf;
                            valueOf = Integer.valueOf(r2 == null ? r0.getPriority() : Math.max(((Integer) obj2).intValue(), EventHookRecord.this.getPriority()));
                            return valueOf;
                        }
                    });
                }
            }
            for (final EventHookRecord eventHookRecord2 : this.substringMatchEventHooksCache) {
                if (eventHookRecord2.matches(str)) {
                    Map.EL.compute(hashMap, eventHookRecord2.getPluginId(), new BiFunction() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda27
                        public /* synthetic */ BiFunction andThen(Function function) {
                            return BiFunction$CC.$default$andThen(this, function);
                        }

                        @Override // java.util.function.BiFunction
                        public final Object apply(Object obj, Object obj2) {
                            Integer valueOf;
                            valueOf = Integer.valueOf(r2 == null ? r0.getPriority() : Math.max(((Integer) obj2).intValue(), EventHookRecord.this.getPriority()));
                            return valueOf;
                        }
                    });
                }
            }
            if (hashMap.isEmpty()) {
                list = Collections.EMPTY_LIST;
            } else {
                ArrayList arrayList = new ArrayList(hashMap.entrySet());
                List.EL.sort(arrayList, new java.util.Comparator() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda28
                    @Override // java.util.Comparator
                    public final int compare(Object obj, Object obj2) {
                        return PluginsController.$r8$lambda$oBZHDd32O9sFqH2KwjebyzDHZxw((Map.Entry) obj, (Map.Entry) obj2);
                    }
                });
                list = (java.util.List) Collection.EL.stream(arrayList).map(new Function() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda29
                    public /* synthetic */ Function andThen(Function function) {
                        return Function$CC.$default$andThen(this, function);
                    }

                    @Override // java.util.function.Function
                    public final Object apply(Object obj) {
                        return (String) ((Map.Entry) obj).getKey();
                    }

                    public /* synthetic */ Function compose(Function function) {
                        return Function$CC.$default$compose(this, function);
                    }
                }).filter(new Predicate() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda30
                    public /* synthetic */ Predicate and(Predicate predicate) {
                        return Predicate$CC.$default$and(this, predicate);
                    }

                    public /* synthetic */ Predicate negate() {
                        return Predicate$CC.$default$negate(this);
                    }

                    public /* synthetic */ Predicate or(Predicate predicate) {
                        return Predicate$CC.$default$or(this, predicate);
                    }

                    @Override // java.util.function.Predicate
                    public final boolean test(Object obj) {
                        boolean lambda$getInterestedPluginIds$27;
                        lambda$getInterestedPluginIds$27 = PluginsController.this.lambda$getInterestedPluginIds$27((String) obj);
                        return lambda$getInterestedPluginIds$27;
                    }
                }).collect(Collectors.toList());
            }
            this.interestedPluginsCache.put(str, list);
            if (!list.isEmpty()) {
                FileLog.d("Calculated and cached potential plugins for '" + str + "': " + list);
            }
        }
        return list;
    }

    public static /* synthetic */ int $r8$lambda$oBZHDd32O9sFqH2KwjebyzDHZxw(Map.Entry entry, Map.Entry entry2) {
        int compare = Integer.compare(((Integer) entry2.getValue()).intValue(), ((Integer) entry.getValue()).intValue());
        return compare == 0 ? ((String) entry.getKey()).compareTo((String) entry2.getKey()) : compare;
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ boolean lambda$getInterestedPluginIds$27(String str) {
        Plugin plugin = this.plugins.get(str);
        return (plugin == null || !plugin.isEnabled() || plugin.hasError()) ? false : true;
    }

    private void rebuildHooksCacheIfNeeded() {
        if (this.hooksCacheDirty) {
            synchronized (this.hooksCacheLock) {
                try {
                    if (this.hooksCacheDirty) {
                        HashMap hashMap = new HashMap();
                        ArrayList arrayList = new ArrayList();
                        Iterator<Set<HookRecord>> it = this.hooks.values().iterator();
                        while (it.hasNext()) {
                            for (HookRecord hookRecord : it.next()) {
                                if (hookRecord instanceof EventHookRecord) {
                                    EventHookRecord eventHookRecord = (EventHookRecord) hookRecord;
                                    if (eventHookRecord.isMatchSubstring()) {
                                        arrayList.add(eventHookRecord);
                                    } else {
                                        ((java.util.List) Map.EL.computeIfAbsent(hashMap, eventHookRecord.getHookName(), new Function() { // from class: com.exteragram.messenger.plugins.PluginsController$$ExternalSyntheticLambda22
                                            public /* synthetic */ Function andThen(Function function) {
                                                return Function$CC.$default$andThen(this, function);
                                            }

                                            @Override // java.util.function.Function
                                            public final Object apply(Object obj) {
                                                return PluginsController.$r8$lambda$J4Q7oAMZibqdYmPlqB0gtk5ZZs0((String) obj);
                                            }

                                            public /* synthetic */ Function compose(Function function) {
                                                return Function$CC.$default$compose(this, function);
                                            }
                                        })).add(eventHookRecord);
                                    }
                                }
                            }
                        }
                        this.exactMatchEventHooksCache = hashMap;
                        this.substringMatchEventHooksCache = arrayList;
                        this.hooksCacheDirty = false;
                    }
                } catch (Throwable th) {
                    throw th;
                }
            }
        }
    }

    public static /* synthetic */ java.util.List $r8$lambda$J4Q7oAMZibqdYmPlqB0gtk5ZZs0(String str) {
        return new ArrayList();
    }

    @Override // com.exteragram.messenger.plugins.hooks.PluginsHooks
    public TLObject executePreRequestHook(String str, int i, TLObject tLObject) {
        if (isPluginEngineAvailable()) {
            java.util.List<String> interestedPluginIds = getInterestedPluginIds(str);
            if (!interestedPluginIds.isEmpty()) {
                for (String str2 : interestedPluginIds) {
                    PluginsEngine pluginEngine = getPluginEngine(str2);
                    if (pluginEngine != null) {
                        HookResult<TLObject> executePreRequestHook = pluginEngine.executePreRequestHook(str, i, tLObject, str2);
                        TLObject tLObject2 = executePreRequestHook.result;
                        if (executePreRequestHook.cancel) {
                            return null;
                        }
                        if (executePreRequestHook.isFinal) {
                            return tLObject2;
                        }
                        tLObject = tLObject2;
                    }
                }
                return tLObject;
            }
        }
        return tLObject;
    }

    @Override // com.exteragram.messenger.plugins.hooks.PluginsHooks
    public PluginsHooks.PostRequestResult executePostRequestHook(String str, int i, TLObject tLObject, TLRPC.TL_error tL_error) {
        if (!isPluginEngineAvailable()) {
            return new PluginsHooks.PostRequestResult(tLObject, tL_error);
        }
        java.util.List<String> interestedPluginIds = getInterestedPluginIds(str);
        if (interestedPluginIds.isEmpty()) {
            return new PluginsHooks.PostRequestResult(tLObject, tL_error);
        }
        TLObject tLObject2 = tLObject;
        TLRPC.TL_error tL_error2 = tL_error;
        for (String str2 : interestedPluginIds) {
            PluginsEngine pluginEngine = getPluginEngine(str2);
            String str3 = str;
            int i2 = i;
            if (pluginEngine != null) {
                HookResult<PluginsHooks.PostRequestResult> executePostRequestHook = pluginEngine.executePostRequestHook(str3, i2, tLObject2, tL_error2, str2);
                PluginsHooks.PostRequestResult postRequestResult = executePostRequestHook.result;
                TLObject tLObject3 = postRequestResult.response;
                TLRPC.TL_error tL_error3 = postRequestResult.error;
                if (executePostRequestHook.cancel) {
                    return null;
                }
                if (executePostRequestHook.isFinal) {
                    return new PluginsHooks.PostRequestResult(tLObject3, tL_error3);
                }
                tL_error2 = tL_error3;
                tLObject2 = tLObject3;
            }
            str = str3;
            i = i2;
        }
        return new PluginsHooks.PostRequestResult(tLObject2, tL_error2);
    }

    @Override // com.exteragram.messenger.plugins.hooks.PluginsHooks
    public TLRPC.Update executeUpdateHook(String str, int i, TLRPC.Update update) {
        if (isPluginEngineAvailable()) {
            java.util.List<String> interestedPluginIds = getInterestedPluginIds(str);
            if (!interestedPluginIds.isEmpty()) {
                for (String str2 : interestedPluginIds) {
                    PluginsEngine pluginEngine = getPluginEngine(str2);
                    if (pluginEngine != null) {
                        HookResult<TLRPC.Update> executeUpdateHook = pluginEngine.executeUpdateHook(str, i, update, str2);
                        TLRPC.Update update2 = executeUpdateHook.result;
                        if (executeUpdateHook.cancel) {
                            return null;
                        }
                        if (executeUpdateHook.isFinal) {
                            return update2;
                        }
                        update = update2;
                    }
                }
                return update;
            }
        }
        return update;
    }

    @Override // com.exteragram.messenger.plugins.hooks.PluginsHooks
    public TLRPC.Updates executeUpdatesHook(String str, int i, TLRPC.Updates updates) {
        if (isPluginEngineAvailable()) {
            java.util.List<String> interestedPluginIds = getInterestedPluginIds(str);
            if (!interestedPluginIds.isEmpty()) {
                for (String str2 : interestedPluginIds) {
                    PluginsEngine pluginEngine = getPluginEngine(str2);
                    if (pluginEngine != null) {
                        HookResult<TLRPC.Updates> executeUpdatesHook = pluginEngine.executeUpdatesHook(str, i, updates, str2);
                        TLRPC.Updates updates2 = executeUpdatesHook.result;
                        if (executeUpdatesHook.cancel) {
                            return null;
                        }
                        if (executeUpdatesHook.isFinal) {
                            return updates2;
                        }
                        updates = updates2;
                    }
                }
                return updates;
            }
        }
        return updates;
    }

    @Override // com.exteragram.messenger.plugins.hooks.PluginsHooks
    public SendMessagesHelper.SendMessageParams executeSendMessageHook(int i, SendMessagesHelper.SendMessageParams sendMessageParams) {
        if (isPluginEngineAvailable()) {
            java.util.List<String> interestedPluginIds = getInterestedPluginIds(PluginsConstants.SEND_MESSAGE_HOOK);
            if (!interestedPluginIds.isEmpty()) {
                for (String str : interestedPluginIds) {
                    PluginsEngine pluginEngine = getPluginEngine(str);
                    if (pluginEngine != null) {
                        HookResult<SendMessagesHelper.SendMessageParams> executeSendMessageHook = pluginEngine.executeSendMessageHook(i, sendMessageParams, str);
                        SendMessagesHelper.SendMessageParams sendMessageParams2 = executeSendMessageHook.result;
                        if (executeSendMessageHook.cancel) {
                            return null;
                        }
                        if (executeSendMessageHook.isFinal) {
                            return sendMessageParams2;
                        }
                        sendMessageParams = sendMessageParams2;
                    }
                }
                return sendMessageParams;
            }
        }
        return sendMessageParams;
    }

    /* JADX INFO: Access modifiers changed from: private */
    /* loaded from: classes.dex */
    public static class SingletonHolder {
        private static final PluginsController INSTANCE = new PluginsController();

        private SingletonHolder() {
        }
    }

    /* loaded from: classes4.dex */
    public static class HookResult<T> {
        public boolean cancel;
        public boolean isFinal;
        public T result;

        public HookResult(T t, boolean z, boolean z2) {
            this.result = t;
            this.cancel = z;
            this.isFinal = z2;
        }
    }

    /* loaded from: classes.dex */
    public static class PluginValidationResult {
        public String error;
        public Plugin plugin;

        public PluginValidationResult(Plugin plugin, String str) {
            this.plugin = plugin;
            this.error = str;
        }
    }
}
