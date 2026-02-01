package com.exteragram.messenger.plugins.models;

import com.exteragram.messenger.plugins.PluginsConstants;

/* loaded from: classes.dex */
public class DividerSetting extends SettingItem {
    public String text;

    public DividerSetting(String str) {
        super(PluginsConstants.Settings.TYPE_DIVIDER);
        this.text = str;
    }
}
