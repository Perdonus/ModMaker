package com.exteragram.messenger.plugins.utils;

import android.text.TextUtils;
import com.chaquo.python.PyException;
import com.chaquo.python.PyObject;

/* loaded from: classes.dex */
public final class PyObjectUtils {
    private PyObjectUtils() {
    }

    public static String getString(PyObject pyObject, String str, String str2) {
        return getString(pyObject, str, str2, false);
    }

    public static String getString(PyObject pyObject, String str, String str2, boolean z) {
        if (pyObject != null && !TextUtils.isEmpty(str)) {
            try {
                PyObject callAttr = z ? pyObject.callAttr("get", str) : pyObject.get((Object) str);
                if (callAttr != null) {
                    try {
                        String pyObject2 = callAttr.toString();
                        callAttr.close();
                        return pyObject2;
                    } catch (Throwable th) {
                        try {
                            callAttr.close();
                        } catch (Throwable th2) {
                            th.addSuppressed(th2);
                        }
                        throw th;
                    }
                }
                if (callAttr != null) {
                    callAttr.close();
                    return str2;
                }
            } catch (PyException | ClassCastException unused) {
            }
        }
        return str2;
    }

    public static boolean getBoolean(PyObject pyObject, String str, boolean z) {
        if (pyObject != null && !TextUtils.isEmpty(str)) {
            try {
                PyObject pyObject2 = pyObject.get((Object) str);
                if (pyObject2 != null) {
                    try {
                        boolean z2 = pyObject2.toBoolean();
                        pyObject2.close();
                        return z2;
                    } catch (Throwable th) {
                        try {
                            pyObject2.close();
                        } catch (Throwable th2) {
                            th.addSuppressed(th2);
                        }
                        throw th;
                    }
                }
                if (pyObject2 != null) {
                    pyObject2.close();
                    return z;
                }
            } catch (PyException | ClassCastException unused) {
            }
        }
        return z;
    }

    public static int getInt(PyObject pyObject, String str, int i) {
        return getInt(pyObject, str, i, false);
    }

    public static int getInt(PyObject pyObject, String str, int i, boolean z) {
        if (pyObject != null && !TextUtils.isEmpty(str)) {
            try {
                PyObject callAttr = z ? pyObject.callAttr("get", str) : pyObject.get((Object) str);
                if (callAttr != null) {
                    try {
                        int i2 = callAttr.toInt();
                        callAttr.close();
                        return i2;
                    } catch (Throwable th) {
                        try {
                            callAttr.close();
                        } catch (Throwable th2) {
                            th.addSuppressed(th2);
                        }
                        throw th;
                    }
                }
                if (callAttr != null) {
                    callAttr.close();
                    return i;
                }
            } catch (PyException | ClassCastException unused) {
            }
        }
        return i;
    }

    /* JADX WARN: Code restructure failed: missing block: B:7:0x000f, code lost:
    
        if (r1 != null) goto L9;
     */
    /*
        Code decompiled incorrectly, please refer to instructions dump.
        To view partially-correct add '--show-bad-code' argument
    */
    public static java.lang.String[] getStringArray(com.chaquo.python.PyObject r1, java.lang.String r2, java.lang.String[] r3) {
        /*
            if (r1 == 0) goto L2f
            boolean r0 = android.text.TextUtils.isEmpty(r2)
            if (r0 == 0) goto L9
            goto L2f
        L9:
            com.chaquo.python.PyObject r1 = r1.get(r2)     // Catch: java.lang.Throwable -> L2f
            if (r1 != 0) goto L15
            if (r1 == 0) goto L2f
        L11:
            r1.close()     // Catch: java.lang.Throwable -> L2f
            return r3
        L15:
            java.lang.Class<java.lang.String[]> r2 = java.lang.String[].class
            java.lang.Object r2 = r1.toJava(r2)     // Catch: java.lang.Throwable -> L25
            java.lang.String[] r2 = (java.lang.String[]) r2     // Catch: java.lang.Throwable -> L25
            int r0 = r2.length     // Catch: java.lang.Throwable -> L25
            if (r0 != 0) goto L21
            goto L11
        L21:
            r1.close()     // Catch: java.lang.Throwable -> L2f java.lang.Throwable -> L2f
            return r2
        L25:
            r2 = move-exception
            r1.close()     // Catch: java.lang.Throwable -> L2a
            goto L2e
        L2a:
            r1 = move-exception
            r2.addSuppressed(r1)     // Catch: java.lang.Throwable -> L2f java.lang.Throwable -> L2f
        L2e:
            throw r2     // Catch: java.lang.Throwable -> L2f java.lang.Throwable -> L2f
        L2f:
            return r3
        */
        throw new UnsupportedOperationException("Method not decompiled: com.exteragram.messenger.plugins.utils.PyObjectUtils.getStringArray(com.chaquo.python.PyObject, java.lang.String, java.lang.String[]):java.lang.String[]");
    }
}
