package com.exteragram.messenger.plugins.models;

import android.text.TextUtils;
import com.chaquo.python.PyObject;

/* loaded from: classes.dex */
public abstract class SettingItem {
    public String icon;
    public String linkAlias;
    public PyObject onLongClickCallback;
    public String type;

    /* JADX INFO: Access modifiers changed from: protected */
    public SettingItem(String str) {
        this(str, null, null, null);
    }

    /* JADX INFO: Access modifiers changed from: protected */
    public SettingItem(String str, String str2, PyObject pyObject, String str3) {
        this.type = str;
        this.icon = str2;
        this.onLongClickCallback = pyObject;
        this.linkAlias = str3;
    }

    public String getLink(String str, String str2) {
        String str3;
        if (TextUtils.isEmpty(this.linkAlias) || TextUtils.isEmpty(str)) {
            return null;
        }
        if (str2 == null) {
            str3 = this.linkAlias;
        } else {
            str3 = str2 + ":" + this.linkAlias;
        }
        return String.format("https://t.me/%s?%s=%s&%s=%s", "exteraSettings", "p", str, "s", str3);
    }
}
