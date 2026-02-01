package com.exteragram.messenger.plugins.ui;

import android.content.SharedPreferences;
import android.os.Build;
import android.text.Html;
import android.text.SpannableString;
import android.view.View;
import com.exteragram.messenger.ExteraConfig;
import com.exteragram.messenger.plugins.PluginsController;
import com.exteragram.messenger.preferences.BasePreferencesActivity;
import com.exteragram.messenger.utils.text.LocaleUtils;
import com.google.android.exoplayer2.util.Consumer;
import java.util.ArrayList;
import org.telegram.messenger.LocaleController;
import org.telegram.messenger.NotificationCenter;
import org.telegram.messenger.R;
import org.telegram.messenger.browser.Browser;
import org.telegram.ui.Cells.TextCheckCell;
import org.telegram.ui.Components.BulletinFactory;
import org.telegram.ui.Components.UItem;
import org.telegram.ui.Components.UniversalAdapter;

/* loaded from: classes.dex */
public class PluginsInfoActivity extends BasePreferencesActivity {

    /* loaded from: classes.dex */
    public enum PreferenceItem {
        DEVELOPER_MODE,
        COMPACT_VIEW,
        SAFE_MODE,
        DOCUMENTATION,
        TRUSTED_PLUGINS;

        public int getId() {
            return ordinal() + 1;
        }
    }

    @Override // com.exteragram.messenger.preferences.BasePreferencesActivity
    public String getTitle() {
        return LocaleController.getString(R.string.PluginsEngine);
    }

    /* JADX INFO: Access modifiers changed from: protected */
    @Override // com.exteragram.messenger.preferences.BasePreferencesActivity
    public void fillItems(ArrayList<UItem> arrayList, UniversalAdapter universalAdapter) {
        SpannableString spannableString;
        arrayList.add(UItem.asHeader(LocaleController.getString(R.string.Settings)));
        arrayList.add(UItem.asCheck(PreferenceItem.DEVELOPER_MODE.getId(), LocaleController.getString(R.string.PluginsDevMode), R.drawable.msg_settings).setChecked(ExteraConfig.pluginsDevMode).setEnabled(ExteraConfig.pluginsEngine).setSearchable(this).setLinkAlias("pluginsDeveloperMode", this));
        arrayList.add(UItem.asCheck(PreferenceItem.COMPACT_VIEW.getId(), LocaleController.getString(R.string.PluginsCompactView), R.drawable.msg_topics).setChecked(ExteraConfig.pluginsCompactView).setEnabled(ExteraConfig.pluginsEngine).setSearchable(this).setLinkAlias("pluginsCompactView", this));
        arrayList.add(UItem.asCheck(PreferenceItem.SAFE_MODE.getId(), LocaleController.getString(R.string.PluginsSafeMode), R.drawable.msg2_secret).setChecked(ExteraConfig.pluginsSafeMode).setSearchable(this).setLinkAlias("pluginsSafeMode", this));
        arrayList.add(UItem.asShadow(LocaleController.getString(R.string.PluginsSafeModeInfo2)));
        arrayList.add(UItem.asHeader(LocaleController.getString(R.string.Links)));
        UItem linkAlias = UItem.asButton(PreferenceItem.DOCUMENTATION.getId(), LocaleController.getString(R.string.PluginsDocumentation)).setSearchable(this).setLinkAlias("pluginsDocumentation", this);
        linkAlias.iconResId = R.drawable.menu_intro;
        arrayList.add(linkAlias);
        UItem linkAlias2 = UItem.asButton(PreferenceItem.TRUSTED_PLUGINS.getId(), LocaleController.getString(R.string.PluginsTrusted)).accent().setSearchable(this).setLinkAlias("trustedPlugins", this);
        linkAlias2.iconResId = R.drawable.msg2_policy;
        arrayList.add(linkAlias2);
        String string = LocaleController.getString(R.string.PluginsPoweredBy);
        if (Build.VERSION.SDK_INT >= 24) {
            spannableString = new SpannableString(Html.fromHtml(string, 0));
        } else {
            spannableString = new SpannableString(Html.fromHtml(string));
        }
        arrayList.add(UItem.asShadow(LocaleUtils.formatWithHtmlURLs(spannableString)));
    }

    /* JADX INFO: Access modifiers changed from: protected */
    @Override // com.exteragram.messenger.preferences.BasePreferencesActivity
    public void onClick(UItem uItem, View view, int i, float f, float f2) {
        int i2 = uItem.id;
        if (i2 <= 0 || i2 > PreferenceItem.values().length) {
            return;
        }
        PreferenceItem preferenceItem = PreferenceItem.values()[uItem.id - 1];
        if ((view instanceof TextCheckCell) && (ExteraConfig.pluginsEngine || preferenceItem == PreferenceItem.SAFE_MODE)) {
            int ordinal = preferenceItem.ordinal();
            if (ordinal == 0) {
                toggleBooleanSettingAndRefresh("pluginsDevMode", uItem, new Consumer() { // from class: com.exteragram.messenger.plugins.ui.PluginsInfoActivity$$ExternalSyntheticLambda0
                    @Override // com.google.android.exoplayer2.util.Consumer
                    public final void accept(Object obj) {
                        PluginsInfoActivity.this.lambda$onClick$0((Boolean) obj);
                    }
                });
                return;
            }
            if (ordinal == 1) {
                toggleBooleanSettingAndRefresh("pluginsCompactView", uItem, new Consumer() { // from class: com.exteragram.messenger.plugins.ui.PluginsInfoActivity$$ExternalSyntheticLambda1
                    @Override // com.google.android.exoplayer2.util.Consumer
                    public final void accept(Object obj) {
                        PluginsInfoActivity.m583$r8$lambda$pWKtYTyPbBtRw4e0nvUkinwVnM((Boolean) obj);
                    }
                });
                return;
            } else {
                if (ordinal != 2) {
                    return;
                }
                final SharedPreferences sharedPreferences = PluginsController.getInstance().preferences;
                toggleBooleanSettingAndRefresh(sharedPreferences, "had_crash", uItem, new Consumer() { // from class: com.exteragram.messenger.plugins.ui.PluginsInfoActivity$$ExternalSyntheticLambda2
                    @Override // com.google.android.exoplayer2.util.Consumer
                    public final void accept(Object obj) {
                        PluginsInfoActivity.$r8$lambda$W4VL9MhcoPOWziaGyIvwfRWHxNQ(sharedPreferences, (Boolean) obj);
                    }
                });
                return;
            }
        }
        PreferenceItem preferenceItem2 = PreferenceItem.DOCUMENTATION;
        if (preferenceItem == preferenceItem2 || preferenceItem == PreferenceItem.TRUSTED_PLUGINS) {
            Browser.openUrl(getParentActivity(), preferenceItem == preferenceItem2 ? "http://plugins.exteragram.app/" : "https://t.me/addlist/pPhOtEq00KhjYTc6");
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$onClick$0(Boolean bool) {
        ExteraConfig.pluginsDevMode = bool.booleanValue();
        PluginsController.getInstance().checkDevServers();
        BulletinFactory of = BulletinFactory.of(this);
        boolean z = ExteraConfig.pluginsDevMode;
        of.createSimpleBulletin(z ? R.raw.contact_check : R.raw.error, LocaleController.getString(z ? R.string.PluginsDevServerLaunched : R.string.PluginsDevServerStopped)).show();
    }

    /* renamed from: $r8$lambda$pWKtYTy-PbBtRw4e0nvUkinwVnM, reason: not valid java name */
    public static /* synthetic */ void m583$r8$lambda$pWKtYTyPbBtRw4e0nvUkinwVnM(Boolean bool) {
        ExteraConfig.pluginsCompactView = bool.booleanValue();
        NotificationCenter.getGlobalInstance().lambda$postNotificationNameOnUIThread$1(NotificationCenter.reloadInterface, new Object[0]);
    }

    public static /* synthetic */ void $r8$lambda$W4VL9MhcoPOWziaGyIvwfRWHxNQ(SharedPreferences sharedPreferences, Boolean bool) {
        ExteraConfig.pluginsSafeMode = bool.booleanValue();
        if (bool.booleanValue()) {
            sharedPreferences.edit().putString("crashed_plugin_id", "manual!").apply();
        } else {
            sharedPreferences.edit().remove("crashed_plugin_id").apply();
        }
        PluginsController.getInstance().restart();
    }
}
