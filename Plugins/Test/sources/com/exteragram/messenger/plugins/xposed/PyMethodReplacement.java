package com.exteragram.messenger.plugins.xposed;

import com.chaquo.python.PyException;
import com.chaquo.python.PyObject;
import com.exteragram.messenger.plugins.PluginsConstants;
import de.robv.android.xposed.XC_MethodHook;
import de.robv.android.xposed.XC_MethodReplacement;
import org.telegram.messenger.FileLog;

/* loaded from: classes.dex */
public class PyMethodReplacement extends XC_MethodReplacement {
    private final String pluginId;
    private final PyObject pythonCallback;

    public PyMethodReplacement(String str, PyObject pyObject) {
        if (pyObject == null) {
            throw new IllegalArgumentException("Python callback object cannot be null");
        }
        if (!pyObject.containsKey(PluginsConstants.Xposed.REPLACE_HOOKED_METHOD)) {
            throw new IllegalArgumentException("Python callback object must contain a method named 'replaceHookedMethod'");
        }
        this.pluginId = str;
        this.pythonCallback = pyObject;
    }

    public PyMethodReplacement(String str, PyObject pyObject, int i) {
        super(i);
        if (pyObject == null) {
            throw new IllegalArgumentException("Python callback object cannot be null");
        }
        if (!pyObject.containsKey(PluginsConstants.Xposed.REPLACE_HOOKED_METHOD)) {
            throw new IllegalArgumentException("Python callback object must contain a method named 'replaceHookedMethod'");
        }
        this.pluginId = str;
        this.pythonCallback = pyObject;
    }

    @Override // de.robv.android.xposed.XC_MethodReplacement
    protected Object replaceHookedMethod(XC_MethodHook.MethodHookParam methodHookParam) {
        PyObject pyObject = this.pythonCallback;
        if (pyObject == null) {
            return null;
        }
        try {
            PyObject callAttr = pyObject.callAttr(PluginsConstants.Xposed.REPLACE_HOOKED_METHOD, methodHookParam);
            if (callAttr == null) {
                return null;
            }
            return callAttr.toJava(Object.class);
        } catch (Throwable th) {
            handleHookError(th);
            return null;
        }
    }

    private void handleHookError(Throwable th) {
        if ((th instanceof PyException) && th.getMessage() != null && th.getMessage().contains("closed")) {
            FileLog.e("Attempted to call a closed PyObject callback in " + this.pluginId);
            return;
        }
        FileLog.e("Plugin '" + this.pluginId + "' crashed in replaceHookedMethod: " + th.getMessage(), th);
    }
}
