package com.exteragram.messenger.plugins.models;

import com.exteragram.messenger.plugins.PluginsConstants;

/* loaded from: classes.dex */
public class HeaderSetting extends SettingItem {
    public String text;

    public HeaderSetting(String str) {
        super(PluginsConstants.Settings.TYPE_HEADER);
        this.text = str;
    }
}
