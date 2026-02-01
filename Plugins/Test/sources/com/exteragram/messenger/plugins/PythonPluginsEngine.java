package com.exteragram.messenger.plugins;

import android.content.Intent;
import android.content.SharedPreferences;
import android.net.Uri;
import android.text.TextUtils;
import androidx.core.content.FileProvider;
import com.chaquo.python.PyException;
import com.chaquo.python.PyObject;
import com.chaquo.python.Python;
import com.chaquo.python.android.AndroidPlatform;
import com.exteragram.messenger.ExteraConfig;
import com.exteragram.messenger.adblock.AdBlockClient$$ExternalSyntheticBackport0;
import com.exteragram.messenger.plugins.PluginsConstants;
import com.exteragram.messenger.plugins.PluginsController;
import com.exteragram.messenger.plugins.hooks.PluginsHooks;
import com.exteragram.messenger.plugins.models.DividerSetting;
import com.exteragram.messenger.plugins.models.EditTextSetting;
import com.exteragram.messenger.plugins.models.HeaderSetting;
import com.exteragram.messenger.plugins.models.InputSetting;
import com.exteragram.messenger.plugins.models.SelectorSetting;
import com.exteragram.messenger.plugins.models.SettingItem;
import com.exteragram.messenger.plugins.models.SwitchSetting;
import com.exteragram.messenger.plugins.models.TextSetting;
import com.exteragram.messenger.plugins.ui.PluginSettingsActivity;
import com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet;
import com.exteragram.messenger.plugins.utils.PyObjectUtils;
import com.exteragram.messenger.preferences.utils.SettingsRegistry;
import com.exteragram.messenger.utils.AppUtils;
import com.exteragram.messenger.utils.text.LocaleUtils;
import j$.util.Collection;
import j$.util.Map;
import j$.util.Objects;
import j$.util.concurrent.ConcurrentHashMap;
import j$.util.concurrent.ConcurrentMap$EL;
import j$.util.function.Function$CC;
import j$.util.function.Predicate$CC;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.FilenameFilter;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.function.Predicate;
import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.ApplicationLoader;
import org.telegram.messenger.BuildVars;
import org.telegram.messenger.FileLog;
import org.telegram.messenger.LocaleController;
import org.telegram.messenger.R;
import org.telegram.messenger.SendMessagesHelper;
import org.telegram.messenger.SharedConfig;
import org.telegram.messenger.Utilities;
import org.telegram.tgnet.TLObject;
import org.telegram.tgnet.TLRPC;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.Components.BulletinFactory;
import org.telegram.ui.LaunchActivity;

/* loaded from: classes.dex */
public class PythonPluginsEngine implements PluginsController.PluginsEngine {
    public PyObject basePluginClass;
    public PyObject debuggerListener;
    private PyObject devServerClass;
    private volatile Python python;
    public final ConcurrentHashMap<String, PyObject> pluginInstances = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, ConcurrentHashMap<String, Object>> settingsCache = new ConcurrentHashMap<>();

    /* JADX INFO: Access modifiers changed from: private */
    @FunctionalInterface
    /* loaded from: classes4.dex */
    public interface PyMethodCaller<T> {
        PyObject call(PyObject pyObject, T t);
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public boolean canOpenInExternalApp() {
        return true;
    }

    private PluginsController getPluginsController() {
        return PluginsController.getInstance();
    }

    private synchronized Python getPython() {
        if (this.python == null) {
            initPython();
            if (this.python == null) {
                FileLog.e("Python initialization failed, unable to proceed.");
                return null;
            }
        }
        if (this.basePluginClass == null) {
            try {
                this.basePluginClass = this.python.getModule("base_plugin").get((Object) "BasePlugin");
            } catch (PyException e) {
                FileLog.e("Failed to load BasePlugin class", e);
            }
        }
        return this.python;
    }

    private void initPython() {
        try {
            if (!Python.isStarted()) {
                Python.start(new AndroidPlatform(ApplicationLoader.applicationContext));
            }
            this.python = Python.getInstance();
        } catch (Exception e) {
            FileLog.e("Failed to initialize Python", e);
        }
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public boolean isPlugin(File file) {
        return file != null && file.getName().toLowerCase().endsWith(PluginsConstants.PLUGINS_EXT);
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public boolean isEngineAvailable() {
        return getPython() != null && Python.isStarted();
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public void init(Runnable runnable) {
        if (getPython() == null) {
            if (runnable != null) {
                runnable.run();
                return;
            }
            return;
        }
        try {
            String[] strArr = (String[]) getPython().getModule("plugin_settings").callAttr("init", getPluginsController().pluginsDir.getAbsolutePath(), getPluginsController().preferences.getAll()).toJava(String[].class);
            if (strArr.length > 0) {
                SharedPreferences.Editor edit = getPluginsController().preferences.edit();
                for (String str : strArr) {
                    edit.remove(str);
                }
                edit.apply();
                FileLog.d("Migrated " + strArr.length + " plugin settings from SharedPreferences to JSON.");
            }
        } catch (PyException e) {
            FileLog.e("Failed to initialize plugin_settings module", e);
        }
        loadPlugins(runnable);
        checkDevServer();
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public void checkDevServer() {
        if (ExteraConfig.pluginsDevMode) {
            runDevServer();
        } else {
            stopDevServer();
        }
    }

    private void runDevServer() {
        if (getPython() == null) {
            return;
        }
        if (this.devServerClass != null) {
            stopDevServer();
        }
        try {
            PyObject pyObject = getPython().getModule(PluginsConstants.DevServer.MODULE).get(PluginsConstants.DevServer.CLASS);
            this.devServerClass = pyObject;
            if (pyObject == null) {
                return;
            }
            pyObject.callAttrThrows(PluginsConstants.DevServer.START_SERVER, new Object[0]);
            FileLog.d("Dev server started successfully.");
        } catch (Throwable th) {
            FileLog.e("Failed to initialize dev server", th);
            this.devServerClass = null;
        }
    }

    private void stopDevServer() {
        PyObject pyObject = this.devServerClass;
        if (pyObject == null) {
            return;
        }
        try {
            pyObject.callAttrThrows(PluginsConstants.DevServer.STOP_SERVER, new Object[0]);
            FileLog.d("Dev server stopped successfully.");
        } catch (Throwable th) {
            try {
                FileLog.e("Failed to stop dev server", th);
            } finally {
                this.devServerClass = null;
            }
        }
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public void shutdown(Runnable runnable) {
        if (getPython() == null) {
            if (runnable != null) {
                runnable.run();
                return;
            }
            return;
        }
        try {
            Iterator<String> it = this.pluginInstances.keySet().iterator();
            while (it.hasNext()) {
                unloadPlugin(it.next());
            }
            PyObject pyObject = this.debuggerListener;
            if (pyObject != null) {
                pyObject.close();
                this.debuggerListener = null;
            }
            this.pluginInstances.clear();
            synchronized (this) {
                this.python = null;
                this.basePluginClass = null;
            }
            FileLog.d("Python plugin engine shut down.");
        } catch (Exception e) {
            FileLog.e(e);
        }
        if (runnable != null) {
            runnable.run();
        }
    }

    public void loadPlugins(final Runnable runnable) {
        PluginsController.runOnPluginsQueue(new Runnable() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda20
            @Override // java.lang.Runnable
            public final void run() {
                PythonPluginsEngine.this.lambda$loadPlugins$2(runnable);
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$loadPlugins$2(Runnable runnable) {
        Plugin plugin;
        if (getPython() == null) {
            if (runnable != null) {
                AndroidUtilities.runOnUIThread(runnable);
                return;
            }
            return;
        }
        try {
            PyObject module = getPython().getModule("sys");
            try {
                PyObject pyObject = module.get("path");
                if (pyObject != null) {
                    try {
                        pyObject.callAttr("append", getPluginsController().pluginsDir.getAbsolutePath());
                    } finally {
                    }
                }
                module.callAttr("setswitchinterval", Double.valueOf(0.001d));
                if (pyObject != null) {
                    pyObject.close();
                }
                module.close();
                File[] listFiles = getPluginsController().pluginsDir.listFiles(new FilenameFilter() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda8
                    @Override // java.io.FilenameFilter
                    public final boolean accept(File file, String str) {
                        boolean endsWith;
                        endsWith = str.toLowerCase().endsWith(".py");
                        return endsWith;
                    }
                });
                if (listFiles == null) {
                    getPluginsController().notifyPluginsChanged();
                    if (runnable != null) {
                        AndroidUtilities.runOnUIThread(runnable);
                        return;
                    }
                    return;
                }
                for (File file : listFiles) {
                    String substring = file.getName().substring(0, file.getName().length() - 3);
                    PluginsController.PluginValidationResult pluginValidationResult = null;
                    try {
                        pluginValidationResult = validatePluginFromFile(file.getAbsolutePath());
                    } catch (Throwable th) {
                        FileLog.e("Failed to load plugin " + file.getName() + ". Reason: " + th.getMessage(), th);
                        if (pluginValidationResult == null || (plugin = pluginValidationResult.plugin) == null) {
                            plugin = new Plugin(substring, substring);
                            plugin.setAuthor(LocaleController.getString(R.string.PluginNoAuthor));
                            plugin.setVersion("1.0");
                            plugin.setEngine(PluginsConstants.PYTHON);
                        }
                        plugin.setError(th);
                        plugin.setEnabled(false);
                        getPluginsController().plugins.put(substring, plugin);
                    }
                    if (pluginValidationResult.error != null) {
                        throw new Exception(pluginValidationResult.error);
                        break;
                    }
                    loadPlugin(substring, file.getAbsolutePath(), pluginValidationResult.plugin);
                }
                getPluginsController().notifyPluginsChanged();
                FileLog.d("Python plugin system initialized. Total: " + getPluginsController().plugins.size() + ", Enabled: " + Collection.EL.stream(getPluginsController().plugins.values()).filter(new Predicate() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda9
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
                        return PythonPluginsEngine.$r8$lambda$VvQ6Tr3bULe91kshg9QPBLt7pfk((Plugin) obj);
                    }
                }).count());
                if (runnable != null) {
                    AndroidUtilities.runOnUIThread(runnable);
                }
            } finally {
            }
        } catch (PyException e) {
            FileLog.e("Failed to setup Python environment for plugins", e);
            if (runnable != null) {
                AndroidUtilities.runOnUIThread(runnable);
            }
        }
    }

    public static /* synthetic */ boolean $r8$lambda$VvQ6Tr3bULe91kshg9QPBLt7pfk(Plugin plugin) {
        return plugin.isEnabled() && !plugin.hasError();
    }

    public void loadPlugin(String str, String str2) {
        loadPlugin(str, str2, null);
    }

    public void loadPlugin(String str, String str2, Plugin plugin) {
        boolean z = getPluginsController().preferences.getBoolean("plugin_enabled_" + str, false);
        File file = new File(str2);
        if (!file.exists() || !file.isFile()) {
            throw new Exception("Plugin file not found: " + str2);
        }
        if (plugin == null) {
            PluginsController.PluginValidationResult validatePluginFromFile = validatePluginFromFile(str2);
            if (validatePluginFromFile.error != null) {
                throw new Exception(validatePluginFromFile.error);
            }
            plugin = validatePluginFromFile.plugin;
        }
        if (!str.equals(plugin.getId())) {
            throw new Exception(String.format("Plugin ID mismatch. Expected: %s, but found: %s in metadata.", str, plugin.getId()));
        }
        if (this.pluginInstances.containsKey(str)) {
            unloadPlugin(str);
        }
        try {
            PyObject findPluginClass = findPluginClass(getPython().getModule(str));
            if (findPluginClass == null) {
                throw new Exception("Could not find a class inheriting from BasePlugin in " + str + ".py. Make sure your main plugin class extends BasePlugin.");
            }
            PyObject call = findPluginClass.call(new Object[0]);
            call.put("id", (Object) plugin.getId());
            call.put("name", (Object) plugin.getName());
            call.put("description", (Object) plugin.getDescription());
            call.put("author", (Object) plugin.getAuthor());
            call.put("version", (Object) plugin.getVersion());
            call.put("icon", (Object) plugin.getIcon());
            call.put("min_version", (Object) plugin.getMinVersion());
            Boolean bool = Boolean.FALSE;
            call.put("enabled", (Object) bool);
            call.put("initialized", (Object) bool);
            call.put("error_message", (PyObject) null);
            plugin.setHasSettings(call.get(PluginsConstants.CREATE_SETTINGS) != null);
            getPluginsController().plugins.put(str, plugin);
            this.pluginInstances.put(str, call);
            if (z) {
                setPluginEnabled(str, true, null);
            }
        } catch (PyException e) {
            throw new Exception("Failed to import plugin module: " + e.getMessage(), e);
        }
    }

    private PyObject findPluginClass(PyObject pyObject) {
        PyObject builtins;
        PyObject pyObject2;
        if (this.basePluginClass == null) {
            FileLog.e("BasePlugin class is not loaded, cannot find plugin class in " + pyObject.get("__name__"));
            return null;
        }
        try {
            builtins = getPython().getBuiltins();
            pyObject2 = pyObject.get("__dict__");
        } catch (PyException e) {
            FileLog.e("Error while searching for a BasePlugin subclass in module " + pyObject.get("__name__"), e);
        }
        if (pyObject2 == null) {
            return null;
        }
        for (PyObject pyObject3 : pyObject2.asMap().values()) {
            if (builtins.callAttr("isinstance", pyObject3, builtins.get((Object) PluginsConstants.Settings.TYPE)).toBoolean() && !pyObject3.equals(this.basePluginClass) && builtins.callAttr("issubclass", pyObject3, this.basePluginClass).toBoolean()) {
                return pyObject3;
            }
        }
        return null;
    }

    public void unloadPlugin(String str) {
        this.settingsCache.remove(str);
        try {
            PyObject remove = this.pluginInstances.remove(str);
            if (remove == null) {
                if (remove != null) {
                    remove.close();
                    return;
                }
                return;
            }
            try {
                if (PyObjectUtils.getBoolean(remove, "initialized", false)) {
                    try {
                        remove.callAttr(PluginsConstants.ON_PLUGIN_UNLOAD, new Object[0]);
                    } catch (Throwable th) {
                        FileLog.e("Error during on_plugin_unload for " + str, th);
                    }
                }
                getPluginsController().cleanupPlugin(str);
                PyObject pyObject = getPython().getModule("sys").get("modules");
                if (pyObject != null && pyObject.callAttr("get", str) != null) {
                    pyObject.callAttr("pop", str);
                }
                remove.close();
            } finally {
            }
        } catch (PyException e) {
            FileLog.e("Failed to remove module " + str + " from sys.modules", e);
        }
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public void setPluginEnabled(String str, boolean z, final Utilities.Callback<String> callback) {
        try {
            Plugin plugin = getPluginsController().plugins.get(str);
            PyObject pyObject = this.pluginInstances.get(str);
            if (plugin == null || pyObject == null) {
                throw new Exception("Plugin not found: " + str);
            }
            if (PyObjectUtils.getBoolean(pyObject, "initialized", false) == z && !plugin.hasError()) {
                if (callback != null) {
                    callback.run(null);
                    return;
                }
                return;
            }
            if (z) {
                getPluginsController().cleanupPlugin(str);
                pyObject.callAttr(PluginsConstants.ON_PLUGIN_LOAD, new Object[0]);
                pyObject.put("initialized", (Object) Boolean.TRUE);
                pyObject.put("error_message", (PyObject) null);
                plugin.setError(null);
            } else {
                if (PyObjectUtils.getBoolean(pyObject, "initialized", false)) {
                    try {
                        pyObject.callAttr(PluginsConstants.ON_PLUGIN_UNLOAD, new Object[0]);
                    } catch (Throwable th) {
                        FileLog.e("Error during on_plugin_unload for " + str, th);
                    }
                }
                pyObject.put("initialized", (Object) Boolean.FALSE);
                getPluginsController().cleanupPlugin(str);
            }
            plugin.setEnabled(z);
            pyObject.put("enabled", (Object) Boolean.valueOf(z));
            getPluginsController().preferences.edit().putBoolean("plugin_enabled_" + str, z).apply();
            if (z) {
                getPluginsController().loadPluginSettings(str);
            } else {
                getPluginsController().invalidatePluginSettings(str);
            }
            getPluginsController().notifyPluginsChanged();
            if (callback != null) {
                AndroidUtilities.runOnUIThread(new Runnable() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda15
                    @Override // java.lang.Runnable
                    public final void run() {
                        Utilities.Callback.this.run(null);
                    }
                });
            }
        } catch (Throwable th2) {
            FileLog.e("Unexpected error setting enabled state for " + str, th2);
            if (z) {
                Plugin plugin2 = getPluginsController().plugins.get(str);
                if (plugin2 != null) {
                    plugin2.setEnabled(false);
                    plugin2.setError(th2);
                }
                PyObject pyObject2 = this.pluginInstances.get(str);
                if (pyObject2 != null) {
                    pyObject2.put("enabled", (Object) Boolean.FALSE);
                    pyObject2.put("error_message", (Object) th2.getMessage());
                }
                getPluginsController().preferences.edit().putBoolean("plugin_enabled_" + str, false).apply();
                getPluginsController().cleanupPlugin(str);
            }
            if (callback != null) {
                AndroidUtilities.runOnUIThread(new Runnable() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda16
                    @Override // java.lang.Runnable
                    public final void run() {
                        Utilities.Callback.this.run(AppUtils.stackTraceToString(th2));
                    }
                });
            }
        }
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public void deletePlugin(String str, final Utilities.Callback<String> callback) {
        if (this.pluginInstances.containsKey(str)) {
            unloadPlugin(str);
        }
        getPluginsController().plugins.remove(str);
        File file = new File(getPluginsController().pluginsDir, str + ".py");
        if (file.exists()) {
            file.delete();
        }
        if (PluginsController.isPluginPinned(str)) {
            PluginsController.setPluginPinned(str, false);
        }
        getPluginsController().clearPluginSettingsPreferences(str);
        getPluginsController().notifyPluginsChanged();
        if (callback != null) {
            AndroidUtilities.runOnUIThread(new Runnable() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda14
                @Override // java.lang.Runnable
                public final void run() {
                    Utilities.Callback.this.run(null);
                }
            });
        }
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public String getPluginPath(String str) {
        return getPluginsController().pluginsDir.getAbsolutePath() + File.separator + str + ".py";
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public void openInExternalApp(String str) {
        BaseFragment safeLastFragment = LaunchActivity.getSafeLastFragment();
        if (safeLastFragment == null) {
            return;
        }
        File file = new File(getPluginPath(str));
        if (file.exists()) {
            AndroidUtilities.openForView(file, file.getName(), "text/plain", safeLastFragment.getParentActivity(), safeLastFragment.getResourceProvider(), false);
        }
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public void sharePlugin(String str) {
        BaseFragment safeLastFragment = LaunchActivity.getSafeLastFragment();
        if (safeLastFragment == null) {
            return;
        }
        String pluginPath = getPluginPath(str);
        File file = new File(ApplicationLoader.getFilesDirFixed(), "temp");
        if (!file.exists()) {
            file.mkdirs();
        }
        File file2 = new File(file, str + PluginsConstants.PLUGINS_EXT);
        try {
            FileInputStream fileInputStream = new FileInputStream(pluginPath);
            try {
                FileOutputStream fileOutputStream = new FileOutputStream(file2);
                try {
                    fileOutputStream.getChannel().transferFrom(fileInputStream.getChannel(), 0L, fileInputStream.getChannel().size());
                    fileOutputStream.close();
                    fileInputStream.close();
                    Uri uriForFile = FileProvider.getUriForFile(safeLastFragment.getContext(), ApplicationLoader.getApplicationId() + ".provider", file2);
                    Intent intent = new Intent("android.intent.action.SEND");
                    intent.setFlags(1);
                    intent.putExtra("android.intent.extra.STREAM", uriForFile);
                    intent.setType("application/x-plugin");
                    safeLastFragment.startActivityForResult(Intent.createChooser(intent, LocaleController.getString(R.string.ShareFile)), 500);
                    file2.deleteOnExit();
                } finally {
                }
            } finally {
            }
        } catch (IOException | IllegalArgumentException e) {
            FileLog.e(e);
        }
    }

    /* JADX WARN: Removed duplicated region for block: B:52:0x00fa  */
    /* JADX WARN: Removed duplicated region for block: B:70:0x0161  */
    /* JADX WARN: Removed duplicated region for block: B:78:0x017f  */
    /* JADX WARN: Removed duplicated region for block: B:80:? A[RETURN, SYNTHETIC] */
    /*
        Code decompiled incorrectly, please refer to instructions dump.
        To view partially-correct add '--show-bad-code' argument
    */
    public void loadPluginFromFile(java.lang.String r11, com.exteragram.messenger.plugins.Plugin r12, final org.telegram.messenger.Utilities.Callback<java.lang.String> r13) {
        /*
            Method dump skipped, instructions count: 392
            To view this dump add '--comments-level debug' option
        */
        throw new UnsupportedOperationException("Method not decompiled: com.exteragram.messenger.plugins.PythonPluginsEngine.loadPluginFromFile(java.lang.String, com.exteragram.messenger.plugins.Plugin, org.telegram.messenger.Utilities$Callback):void");
    }

    public PluginsController.PluginValidationResult validatePluginFromFile(String str) {
        if (!new File(str).exists()) {
            return new PluginsController.PluginValidationResult(null, "Plugin file not found.");
        }
        try {
            Map<String, String> parsePluginMetadata = parsePluginMetadata(str);
            String str2 = parsePluginMetadata.get("id");
            String str3 = parsePluginMetadata.get("name");
            if (!TextUtils.isEmpty(str2) && !TextUtils.isEmpty(str3)) {
                if (!str2.matches("^[a-zA-Z][a-zA-Z0-9_-]{1,31}$")) {
                    return new PluginsController.PluginValidationResult(null, "Plugin '__id__' must be 2-32 characters long, start with a letter, and contain only latin letters, numbers, dashes and underscores.");
                }
                String str4 = parsePluginMetadata.get("min_version");
                if (str4 != null && !SharedConfig.versionBiggerOrEqual(BuildVars.BUILD_VERSION_STRING, str4)) {
                    return new PluginsController.PluginValidationResult(null, "Plugin requires app version " + str4 + " or higher. Current is " + BuildVars.BUILD_VERSION_STRING);
                }
                Plugin plugin = new Plugin(str2, str3);
                plugin.setEngine(PluginsConstants.PYTHON);
                plugin.setAuthor((String) Map.EL.getOrDefault(parsePluginMetadata, "author", LocaleController.getString(R.string.PluginNoAuthor)));
                plugin.setDescription((String) Map.EL.getOrDefault(parsePluginMetadata, "description", LocaleController.getString(R.string.PluginNoDescription)));
                plugin.setIcon(parsePluginMetadata.get("icon"));
                plugin.setVersion((String) Map.EL.getOrDefault(parsePluginMetadata, "version", "1.0"));
                plugin.setMinVersion(str4);
                plugin.setEnabled(getPluginsController().preferences.getBoolean("plugin_enabled_" + str2, false));
                return new PluginsController.PluginValidationResult(plugin, null);
            }
            return new PluginsController.PluginValidationResult(null, "Plugin metadata must contain non-empty '__id__' and '__name__'.");
        } catch (PyException e) {
            FileLog.e("Failed to parse metadata from " + str + ". Error: " + e.getMessage(), e);
            return new PluginsController.PluginValidationResult(null, e.getMessage());
        } catch (Throwable th) {
            FileLog.e("Unexpected error validating plugin " + str, th);
            return new PluginsController.PluginValidationResult(null, th.getMessage());
        }
    }

    /* JADX WARN: Can't fix incorrect switch cases order, some code will duplicate */
    /* JADX WARN: Failed to find 'out' block for switch in B:11:0x0068. Please report as an issue. */
    public List<SettingItem> parsePySettingDefinitions(List<PyObject> list) {
        Object editTextSetting;
        ArrayList arrayList = new ArrayList(list.size());
        for (PyObject pyObject : list) {
            if (pyObject != null) {
                Object obj = null;
                String string = PyObjectUtils.getString(pyObject, PluginsConstants.Settings.TYPE, null);
                if (string == null) {
                    FileLog.w("A setting item in a plugin is missing its 'type'. Skipping.");
                } else {
                    String string2 = PyObjectUtils.getString(pyObject, PluginsConstants.Settings.KEY, null);
                    String string3 = PyObjectUtils.getString(pyObject, "text", null);
                    String string4 = PyObjectUtils.getString(pyObject, "subtext", null);
                    String string5 = PyObjectUtils.getString(pyObject, "icon", null);
                    PyObject pyObject2 = pyObject.get((Object) PluginsConstants.Settings.ON_CHANGE);
                    PyObject pyObject3 = pyObject.get((Object) PluginsConstants.Settings.ON_LONG_CLICK);
                    String string6 = PyObjectUtils.getString(pyObject, PluginsConstants.Settings.LINK_ALIAS, null);
                    PyObject pyObject4 = pyObject.get((Object) PluginsConstants.Settings.DEFAULT);
                    char c = 65535;
                    switch (string.hashCode()) {
                        case -1866021310:
                            if (string.equals(PluginsConstants.Settings.TYPE_EDIT_TEXT)) {
                                c = 0;
                                break;
                            }
                            break;
                        case -1221270899:
                            if (string.equals(PluginsConstants.Settings.TYPE_HEADER)) {
                                c = 1;
                                break;
                            }
                            break;
                        case -889473228:
                            if (string.equals(PluginsConstants.Settings.TYPE_SWITCH)) {
                                c = 2;
                                break;
                            }
                            break;
                        case 3556653:
                            if (string.equals("text")) {
                                c = 3;
                                break;
                            }
                            break;
                        case 100358090:
                            if (string.equals(PluginsConstants.Settings.TYPE_INPUT)) {
                                c = 4;
                                break;
                            }
                            break;
                        case 1191572447:
                            if (string.equals(PluginsConstants.Settings.TYPE_SELECTOR)) {
                                c = 5;
                                break;
                            }
                            break;
                        case 1674318617:
                            if (string.equals(PluginsConstants.Settings.TYPE_DIVIDER)) {
                                c = 6;
                                break;
                            }
                            break;
                    }
                    switch (c) {
                        case 0:
                            String string7 = PyObjectUtils.getString(pyObject, PluginsConstants.Settings.HINT, null);
                            boolean z = PyObjectUtils.getBoolean(pyObject, PluginsConstants.Settings.MULTILINE, false);
                            int i = PyObjectUtils.getInt(pyObject, PluginsConstants.Settings.MAX_LENGTH, 256);
                            String string8 = PyObjectUtils.getString(pyObject, PluginsConstants.Settings.MASK, null);
                            if (string2 != null && string7 != null) {
                                editTextSetting = new EditTextSetting(string2, string7, pyObject4 != null ? pyObject4.toString() : "", z, i, string8, pyObject2);
                                break;
                            }
                            break;
                        case 1:
                            if (string3 != null) {
                                obj = new HeaderSetting(string3);
                                break;
                            }
                            break;
                        case 2:
                            if (string2 != null && string3 != null && pyObject4 != null) {
                                editTextSetting = new SwitchSetting(string2, string3, pyObject4.toBoolean(), string4, string5, pyObject2, pyObject3, string6);
                                break;
                            }
                            break;
                        case 3:
                            boolean z2 = PyObjectUtils.getBoolean(pyObject, PluginsConstants.Settings.ACCENT, false);
                            boolean z3 = PyObjectUtils.getBoolean(pyObject, PluginsConstants.Settings.RED, false);
                            PyObject pyObject5 = pyObject.get((Object) "on_click");
                            PyObject pyObject6 = pyObject.get((Object) PluginsConstants.Settings.CREATE_SUB_FRAGMENT);
                            if (string3 != null) {
                                obj = new TextSetting(string3, string5, z2, z3, pyObject5, pyObject6, pyObject3, string6);
                                break;
                            }
                            break;
                        case 4:
                            if (string2 != null && string3 != null) {
                                editTextSetting = new InputSetting(string2, string3, pyObject4 != null ? pyObject4.toString() : "", string4, string5, pyObject2, pyObject3, string6);
                                break;
                            }
                            break;
                        case 5:
                            String[] stringArray = PyObjectUtils.getStringArray(pyObject, PluginsConstants.Settings.ITEMS, null);
                            if (string2 != null && string3 != null && stringArray != null && stringArray.length != 0 && pyObject4 != null) {
                                editTextSetting = new SelectorSetting(string2, string3, pyObject4.toInt(), stringArray, string5, pyObject2, pyObject3, string6);
                                break;
                            }
                            break;
                        case 6:
                            obj = new DividerSetting(string3);
                            break;
                    }
                    obj = editTextSetting;
                    if (obj != null) {
                        arrayList.add(obj);
                    } else {
                        continue;
                    }
                }
            }
        }
        return arrayList;
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public List<SettingItem> loadPluginSettings(String str) {
        try {
            Plugin plugin = getPluginsController().plugins.get(str);
            PyObject pyObject = this.pluginInstances.get(str);
            if (plugin != null && plugin.isEnabled() && !plugin.hasError() && pyObject != null) {
                PyObject callAttr = pyObject.callAttr(PluginsConstants.CREATE_SETTINGS, new Object[0]);
                if (callAttr == null) {
                    return null;
                }
                List<PyObject> asList = callAttr.asList();
                if (asList.isEmpty()) {
                    return null;
                }
                return parsePySettingDefinitions(asList);
            }
            getPluginsController().invalidatePluginSettings(str);
            return null;
        } catch (Exception e) {
            FileLog.e("Failed to load plugin settings", e);
            return null;
        }
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public void executeOnAppEvent(String str) {
        PyObject pyObject = getPython().getModule("base_plugin").get("AppEvent");
        if (pyObject == null) {
            return;
        }
        PyObject call = pyObject.call(str);
        try {
            PyObject pyObject2 = this.debuggerListener;
            if (pyObject2 != null) {
                try {
                    pyObject2.callAttr(PluginsConstants.ON_APP_EVENT, call);
                } catch (PyException e) {
                    FileLog.e("Failed to execute app event for debugger listener", e);
                }
            }
            for (PyObject pyObject3 : this.pluginInstances.values()) {
                if (PyObjectUtils.getBoolean(pyObject3, "enabled", false) && PyObjectUtils.getString(pyObject3, "error_message", null) == null) {
                    try {
                        pyObject3.callAttr(PluginsConstants.ON_APP_EVENT, call);
                    } catch (PyException e2) {
                        FileLog.e("Failed to execute app " + str + " for " + PyObjectUtils.getString(pyObject3, "id", null), e2);
                    }
                }
            }
            if (call != null) {
                call.close();
            }
        } catch (Throwable th) {
            if (call != null) {
                try {
                    call.close();
                } catch (Throwable th2) {
                    th.addSuppressed(th2);
                }
            }
            throw th;
        }
    }

    public <T> PluginsController.HookResult<T> executeHook(PyObject pyObject, T t, Class<T> cls, String str, PyMethodCaller<T> pyMethodCaller, Utilities.Callback<PyException> callback) {
        if (pyObject != null) {
            try {
                PyObject call = pyMethodCaller.call(pyObject, t);
                if (call != null) {
                    String string = PyObjectUtils.getString(call, PluginsConstants.STRATEGY, PluginsConstants.Strategy.DEFAULT);
                    if (string.endsWith(PluginsConstants.Strategy.CANCEL)) {
                        return new PluginsController.HookResult<>(null, true, false);
                    }
                    if (string.endsWith(PluginsConstants.Strategy.MODIFY) || string.endsWith(PluginsConstants.Strategy.MODIFY_FINAL)) {
                        PyObject pyObject2 = call.get((Object) str);
                        if (pyObject2 != null) {
                            t = (T) pyObject2.toJava(cls);
                        }
                        if (string.endsWith(PluginsConstants.Strategy.MODIFY_FINAL)) {
                            return new PluginsController.HookResult<>(t, false, true);
                        }
                    }
                }
            } catch (PyException e) {
                callback.run(e);
            }
        }
        return new PluginsController.HookResult<>(t, false, false);
    }

    private <T> PluginsController.HookResult<T> executeHook(String str, T t, Class<T> cls, String str2, PyMethodCaller<T> pyMethodCaller, Utilities.Callback<PyException> callback) {
        return executeHook(this.pluginInstances.get(str), (PyObject) t, (Class<PyObject>) cls, str2, (PyMethodCaller<PyObject>) pyMethodCaller, callback);
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public PluginsController.HookResult<TLObject> executePreRequestHook(final String str, final int i, TLObject tLObject, final String str2) {
        return executeHook(str2, (String) tLObject, (Class<String>) TLObject.class, PluginsConstants.REQUEST, (PyMethodCaller<String>) new PyMethodCaller() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda21
            @Override // com.exteragram.messenger.plugins.PythonPluginsEngine.PyMethodCaller
            public final PyObject call(PyObject pyObject, Object obj) {
                PyObject callAttr;
                callAttr = pyObject.callAttr("pre_request_hook", str, Integer.valueOf(i), (TLObject) obj);
                return callAttr;
            }
        }, new Utilities.Callback() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda22
            @Override // org.telegram.messenger.Utilities.Callback
            public final void run(Object obj) {
                FileLog.e("Failed to execute pre_request_hook in " + str2 + " for " + str, (PyException) obj);
            }
        });
    }

    public PluginsController.HookResult<PluginsHooks.PostRequestResult> executePostRequestHook(String str, int i, TLObject tLObject, TLRPC.TL_error tL_error, PyObject pyObject) {
        if (pyObject != null) {
            try {
                PyObject callAttr = pyObject.callAttr("post_request_hook", str, Integer.valueOf(i), tLObject, tL_error);
                if (callAttr != null) {
                    String string = PyObjectUtils.getString(callAttr, PluginsConstants.STRATEGY, "");
                    if (!string.endsWith(PluginsConstants.Strategy.MODIFY)) {
                        if (string.endsWith(PluginsConstants.Strategy.MODIFY_FINAL)) {
                        }
                    }
                    PyObject pyObject2 = callAttr.get(PluginsConstants.RESPONSE);
                    if (pyObject2 != null) {
                        tLObject = (TLObject) pyObject2.toJava(TLObject.class);
                    }
                    PyObject pyObject3 = callAttr.get(PluginsConstants.ERROR);
                    if (pyObject3 != null) {
                        tL_error = (TLRPC.TL_error) pyObject3.toJava(TLRPC.TL_error.class);
                    }
                    if (string.endsWith(PluginsConstants.Strategy.MODIFY_FINAL)) {
                        return new PluginsController.HookResult<>(new PluginsHooks.PostRequestResult(tLObject, tL_error), false, true);
                    }
                }
            } catch (PyException e) {
                FileLog.e("Failed to execute post_request_hook for " + str, e);
            }
        }
        return new PluginsController.HookResult<>(new PluginsHooks.PostRequestResult(tLObject, tL_error), false, false);
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public PluginsController.HookResult<PluginsHooks.PostRequestResult> executePostRequestHook(String str, int i, TLObject tLObject, TLRPC.TL_error tL_error, String str2) {
        return executePostRequestHook(str, i, tLObject, tL_error, this.pluginInstances.get(str2));
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public PluginsController.HookResult<TLRPC.Update> executeUpdateHook(final String str, final int i, TLRPC.Update update, String str2) {
        return executeHook(str2, (String) update, (Class<String>) TLRPC.Update.class, PluginsConstants.UPDATE, (PyMethodCaller<String>) new PyMethodCaller() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda1
            @Override // com.exteragram.messenger.plugins.PythonPluginsEngine.PyMethodCaller
            public final PyObject call(PyObject pyObject, Object obj) {
                PyObject callAttr;
                callAttr = pyObject.callAttr("on_update_hook", str, Integer.valueOf(i), (TLRPC.Update) obj);
                return callAttr;
            }
        }, new Utilities.Callback() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda2
            @Override // org.telegram.messenger.Utilities.Callback
            public final void run(Object obj) {
                FileLog.e("Failed to execute on_update_hook for " + str, (PyException) obj);
            }
        });
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public PluginsController.HookResult<TLRPC.Updates> executeUpdatesHook(final String str, final int i, TLRPC.Updates updates, String str2) {
        return executeHook(str2, (String) updates, (Class<String>) TLRPC.Updates.class, PluginsConstants.UPDATES, (PyMethodCaller<String>) new PyMethodCaller() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda10
            @Override // com.exteragram.messenger.plugins.PythonPluginsEngine.PyMethodCaller
            public final PyObject call(PyObject pyObject, Object obj) {
                PyObject callAttr;
                callAttr = pyObject.callAttr("on_updates_hook", str, Integer.valueOf(i), (TLRPC.Updates) obj);
                return callAttr;
            }
        }, new Utilities.Callback() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda11
            @Override // org.telegram.messenger.Utilities.Callback
            public final void run(Object obj) {
                FileLog.e("Failed to execute on_updates_hook for " + str, (PyException) obj);
            }
        });
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public PluginsController.HookResult<SendMessagesHelper.SendMessageParams> executeSendMessageHook(final int i, SendMessagesHelper.SendMessageParams sendMessageParams, final String str) {
        return executeHook(str, (String) sendMessageParams, (Class<String>) SendMessagesHelper.SendMessageParams.class, PluginsConstants.PARAMS, (PyMethodCaller<String>) new PyMethodCaller() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda18
            @Override // com.exteragram.messenger.plugins.PythonPluginsEngine.PyMethodCaller
            public final PyObject call(PyObject pyObject, Object obj) {
                PyObject callAttr;
                callAttr = pyObject.callAttr("on_send_message_hook", Integer.valueOf(i), (SendMessagesHelper.SendMessageParams) obj);
                return callAttr;
            }
        }, new Utilities.Callback() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda19
            @Override // org.telegram.messenger.Utilities.Callback
            public final void run(Object obj) {
                FileLog.e("Failed to execute on_send_message_hook for " + str, (PyException) obj);
            }
        });
    }

    public String fetchParameterValue(String str, String str2) {
        if (str == null) {
            return null;
        }
        try {
            File file = new File(str);
            if (file.exists() && file.isFile()) {
                return parsePluginMetadata(str).get(str2);
            }
        } catch (Exception unused) {
        }
        return null;
    }

    public java.util.Map<String, String> parsePluginMetadata(String str) {
        HashMap hashMap = new HashMap();
        if (str != null) {
            File file = new File(str);
            if (file.exists() && file.isFile()) {
                if (getPython() == null) {
                    FileLog.e("Python engine not initialized, cannot parse metadata for " + str);
                    return hashMap;
                }
                try {
                    PyObject callAttr = getPython().getModule("utils.metadata_parser").callAttr("get_metadata", str);
                    if (callAttr != null) {
                        for (Map.Entry<PyObject, PyObject> entry : callAttr.asMap().entrySet()) {
                            hashMap.put(entry.getKey().toString(), entry.getValue().toString());
                        }
                    }
                } catch (PyException e) {
                    FileLog.e("Failed to parse metadata from " + str + ". Error: " + e.getMessage(), e);
                    throw e;
                }
            }
        }
        return hashMap;
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public Object getPluginSetting(String str, String str2, Object obj) {
        Object java2;
        ConcurrentHashMap<String, Object> concurrentHashMap = this.settingsCache.get(str);
        if (concurrentHashMap != null && concurrentHashMap.containsKey(str2)) {
            return concurrentHashMap.get(str2);
        }
        if (getPython() != null) {
            try {
                PyObject callAttr = getPython().getModule("plugin_settings").callAttr("get_setting", str, str2, obj);
                if (callAttr != null) {
                    if (obj instanceof Boolean) {
                        java2 = Boolean.valueOf(callAttr.toBoolean());
                    } else if (obj instanceof Integer) {
                        java2 = Integer.valueOf(callAttr.toInt());
                    } else if (obj instanceof String) {
                        java2 = callAttr.toString();
                    } else if (obj instanceof Float) {
                        java2 = Float.valueOf(callAttr.toFloat());
                    } else if (obj instanceof Long) {
                        java2 = Long.valueOf(callAttr.toLong());
                    } else {
                        java2 = callAttr.toJava(obj.getClass());
                    }
                    ((ConcurrentHashMap) ConcurrentMap$EL.computeIfAbsent(this.settingsCache, str, new Function() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda23
                        public /* synthetic */ Function andThen(Function function) {
                            return Function$CC.$default$andThen(this, function);
                        }

                        @Override // java.util.function.Function
                        public final Object apply(Object obj2) {
                            return PythonPluginsEngine.$r8$lambda$miBpoLvvlN0Gzg9vlYgqNAQE_j8((String) obj2);
                        }

                        public /* synthetic */ Function compose(Function function) {
                            return Function$CC.$default$compose(this, function);
                        }
                    })).put(str2, java2);
                    return java2;
                }
            } catch (PyException e) {
                FileLog.e("Failed to get plugin setting " + str + "/" + str2, e);
                return obj;
            }
        }
        return obj;
    }

    public static /* synthetic */ ConcurrentHashMap $r8$lambda$miBpoLvvlN0Gzg9vlYgqNAQE_j8(String str) {
        return new ConcurrentHashMap();
    }

    public static /* synthetic */ ConcurrentHashMap $r8$lambda$KjvaB_SxOLvwOUGFZuvFnHgjqsY(String str) {
        return new ConcurrentHashMap();
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public void setPluginSetting(String str, String str2, Object obj) {
        ((ConcurrentHashMap) ConcurrentMap$EL.computeIfAbsent(this.settingsCache, str, new Function() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda0
            public /* synthetic */ Function andThen(Function function) {
                return Function$CC.$default$andThen(this, function);
            }

            @Override // java.util.function.Function
            public final Object apply(Object obj2) {
                return PythonPluginsEngine.$r8$lambda$KjvaB_SxOLvwOUGFZuvFnHgjqsY((String) obj2);
            }

            public /* synthetic */ Function compose(Function function) {
                return Function$CC.$default$compose(this, function);
            }
        })).put(str2, obj);
        if (getPython() == null) {
            return;
        }
        try {
            getPython().getModule("plugin_settings").callAttr("set_setting", str, str2, obj);
        } catch (PyException e) {
            FileLog.e("Failed to set plugin setting " + str + "/" + str2, e);
        }
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public void clearPluginSettings(String str) {
        this.settingsCache.remove(str);
        if (getPython() == null) {
            return;
        }
        try {
            getPython().getModule("plugin_settings").callAttr("clear_settings", str);
        } catch (PyException e) {
            FileLog.e("Failed to clear plugin settings for " + str, e);
        }
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public java.util.Map<String, ?> getAllPluginSettings(String str) {
        if (getPython() == null) {
            return null;
        }
        try {
            PyObject callAttr = getPython().getModule("plugin_settings").callAttr("get_all_settings", str);
            if (callAttr != null) {
                HashMap hashMap = new HashMap();
                for (Map.Entry<PyObject, PyObject> entry : callAttr.asMap().entrySet()) {
                    if (entry.getKey() != null) {
                        hashMap.put(entry.getKey().toString(), entry.getValue() != null ? entry.getValue().toJava(Object.class) : null);
                    }
                }
                this.settingsCache.put(str, new ConcurrentHashMap<>(hashMap));
                return hashMap;
            }
        } catch (PyException e) {
            FileLog.e("Failed to get all plugin settings for " + str, e);
        }
        return null;
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public void showInstallDialog(final BaseFragment baseFragment, InstallPluginBottomSheet.PluginInstallParams pluginInstallParams) {
        File file = new File(pluginInstallParams.filePath);
        final String fetchParameterValue = fetchParameterValue(pluginInstallParams.filePath, "name");
        if (TextUtils.isEmpty(fetchParameterValue) && file.exists()) {
            fetchParameterValue = file.getName();
        }
        final PluginsController.PluginValidationResult validatePluginFromFile = validatePluginFromFile(pluginInstallParams.filePath);
        if (validatePluginFromFile.plugin != null) {
            new InstallPluginBottomSheet(baseFragment, validatePluginFromFile, pluginInstallParams).show();
        } else {
            AndroidUtilities.runOnUIThread(new Runnable() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda17
                @Override // java.lang.Runnable
                public final void run() {
                    BulletinFactory.of(r0).createSimpleBulletin(R.raw.error, LocaleController.formatString(R.string.PluginInstallError, fetchParameterValue), LocaleUtils.createCopySpan(r0), new Runnable() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda12
                        @Override // java.lang.Runnable
                        public final void run() {
                            PythonPluginsEngine.m565$r8$lambda$Ewh_Se3E1IO3mCtnVWJN2C7B4(PluginsController.PluginValidationResult.this, r2);
                        }
                    }).show();
                }
            });
        }
    }

    /* renamed from: $r8$lambda$Ewh_Se3-E1IO3mCtnVW-JN2C7B4, reason: not valid java name */
    public static /* synthetic */ void m565$r8$lambda$Ewh_Se3E1IO3mCtnVWJN2C7B4(PluginsController.PluginValidationResult pluginValidationResult, BaseFragment baseFragment) {
        if (AndroidUtilities.addToClipboard(pluginValidationResult.error)) {
            BulletinFactory.of(baseFragment).createCopyBulletin(LocaleController.getString(R.string.TextCopied)).show();
        }
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public void openPluginSettings(String str, BaseFragment baseFragment) {
        Plugin plugin = getPluginsController().plugins.get(str);
        if (plugin != null) {
            openPluginSettings(plugin, baseFragment);
        }
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public void openPluginSettings(final Plugin plugin, final BaseFragment baseFragment) {
        if (plugin == null) {
            return;
        }
        AndroidUtilities.runOnUIThread(new Runnable() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda5
            @Override // java.lang.Runnable
            public final void run() {
                BaseFragment.this.presentFragment(new PluginSettingsActivity(plugin));
            }
        });
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public void openPluginSetting(final Plugin plugin, final String str, final BaseFragment baseFragment) {
        if (plugin == null) {
            return;
        }
        PluginsController.runOnPluginsQueue(new Runnable() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda13
            @Override // java.lang.Runnable
            public final void run() {
                PythonPluginsEngine.this.lambda$openPluginSetting$22(plugin, str, baseFragment);
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$openPluginSetting$22(Plugin plugin, String str, final BaseFragment baseFragment) {
        final PluginSettingsActivity pluginSettingsActivity;
        FileLog.d("Opening plugin setting: " + plugin.getId() + "/" + str);
        if (str == null || !str.contains(":")) {
            pluginSettingsActivity = new PluginSettingsActivity(plugin, str);
        } else {
            List<SettingItem> list = getPluginsController().settings.get(plugin.getId());
            if (list == null) {
                return;
            }
            String[] split = str.split(":");
            TextSetting textSetting = null;
            List<SettingItem> list2 = list;
            for (int i = 0; i < split.length - 1; i++) {
                String str2 = split[i];
                Iterator<SettingItem> it = list2.iterator();
                while (true) {
                    if (!it.hasNext()) {
                        break;
                    }
                    SettingItem next = it.next();
                    if (next instanceof TextSetting) {
                        TextSetting textSetting2 = (TextSetting) next;
                        if (str2.equals(textSetting2.linkAlias)) {
                            try {
                                PyObject call = textSetting2.createSubFragmentCallback.call(new Object[0]);
                                if (call != null) {
                                    list2 = parsePySettingDefinitions(call.asList());
                                }
                            } catch (Exception unused) {
                            }
                            textSetting = textSetting2;
                        }
                    }
                }
                if (textSetting == null && list2.isEmpty()) {
                    SettingsRegistry.getInstance().onSettingNotFound(baseFragment);
                    return;
                }
            }
            if (textSetting == null) {
                return;
            } else {
                pluginSettingsActivity = new PluginSettingsActivity(plugin, textSetting.text, list2, textSetting.createSubFragmentCallback, split[split.length - 1]).setSettingsLinkPrefix(AdBlockClient$$ExternalSyntheticBackport0.m(":", (CharSequence[]) Arrays.copyOf(split, split.length - 1)));
            }
        }
        AndroidUtilities.runOnUIThread(new Runnable() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda6
            @Override // java.lang.Runnable
            public final void run() {
                BaseFragment.this.presentFragment(pluginSettingsActivity);
            }
        });
        Objects.requireNonNull(pluginSettingsActivity);
        AndroidUtilities.runOnUIThread(new Runnable() { // from class: com.exteragram.messenger.plugins.PythonPluginsEngine$$ExternalSyntheticLambda7
            @Override // java.lang.Runnable
            public final void run() {
                PluginSettingsActivity.this.checkTargetSetting();
            }
        });
    }

    @Override // com.exteragram.messenger.plugins.PluginsController.PluginsEngine
    public void openPluginSetting(String str, String str2, BaseFragment baseFragment) {
        Plugin plugin = getPluginsController().plugins.get(str);
        if (plugin != null) {
            openPluginSetting(plugin, str2, baseFragment);
        }
    }

    public void setDebuggerListener(PyObject pyObject) {
        this.debuggerListener = pyObject;
    }
}
