package com.exteragram.messenger.plugins.ui.components;

import android.text.Layout;
import android.text.SpannableStringBuilder;
import android.view.View;
import android.widget.LinearLayout;
import com.exteragram.messenger.ExteraConfig;
import com.exteragram.messenger.plugins.Plugin;
import com.exteragram.messenger.plugins.PluginsConstants;
import com.exteragram.messenger.plugins.PluginsController;
import com.exteragram.messenger.plugins.PythonPluginsEngine;
import com.exteragram.messenger.utils.text.LocaleUtils;
import java.io.File;
import java.util.ArrayList;
import java.util.concurrent.atomic.AtomicBoolean;
import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.LocaleController;
import org.telegram.messenger.MediaDataController;
import org.telegram.messenger.R;
import org.telegram.messenger.UserConfig;
import org.telegram.messenger.Utilities;
import org.telegram.tgnet.TLRPC;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.ActionBar.BottomSheet;
import org.telegram.ui.ActionBar.Theme;
import org.telegram.ui.Components.Bulletin;
import org.telegram.ui.Components.BulletinFactory;
import org.telegram.ui.Components.CheckBox2;
import org.telegram.ui.Components.LayoutHelper;
import org.telegram.ui.Stories.recorder.HintView2;

/* loaded from: classes4.dex */
public class InstallPluginBottomSheet extends BottomSheet {
    private HintView2 currentHint;
    private boolean enableAfterInstallation;

    @Override // org.telegram.ui.ActionBar.BottomSheet, org.telegram.ui.ActionBar.BaseFragment.AttachedSheet
    public /* bridge */ /* synthetic */ void setLastVisible(boolean z) {
        BaseFragment.AttachedSheet.CC.$default$setLastVisible(this, z);
    }

    /* JADX WARN: Code restructure failed: missing block: B:29:0x0490, code lost:
    
        if (com.exteragram.messenger.ExteraConfig.preferences.getBoolean("trusted_source_hint", false) != false) goto L39;
     */
    /*
        Code decompiled incorrectly, please refer to instructions dump.
        To view partially-correct add '--show-bad-code' argument
    */
    public InstallPluginBottomSheet(final org.telegram.ui.ActionBar.BaseFragment r32, final com.exteragram.messenger.plugins.PluginsController.PluginValidationResult r33, final com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet.PluginInstallParams r34) {
        /*
            Method dump skipped, instructions count: 1197
            To view this dump add '--comments-level debug' option
        */
        throw new UnsupportedOperationException("Method not decompiled: com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet.<init>(org.telegram.ui.ActionBar.BaseFragment, com.exteragram.messenger.plugins.PluginsController$PluginValidationResult, com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet$PluginInstallParams):void");
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$new$1(PluginInstallParams pluginInstallParams, final View view) {
        HintView2 hintView2 = this.currentHint;
        if (hintView2 != null) {
            hintView2.hide();
            this.currentHint = null;
        }
        final HintView2 rounding = new HintView2(getContext(), 3).setMultilineText(true).setBgColor(getThemedColor(Theme.key_undo_background)).setTextColor(getThemedColor(Theme.key_undo_infoColor)).setText(AndroidUtilities.replaceTags(LocaleController.getString(pluginInstallParams.trusted ? R.string.PluginSourceTrustedInfo : R.string.PluginSourceUnknownInfo))).setTextAlign(Layout.Alignment.ALIGN_CENTER).allowBlur(true).setRounding(12.0f);
        rounding.setMaxWidthPx(HintView2.cutInFancyHalf(rounding.getText(), rounding.getTextPaint()));
        this.container.addView(rounding, LayoutHelper.createFrame(-1, 100.0f, 55, 32.0f, 0.0f, 32.0f, 0.0f));
        this.currentHint = rounding;
        this.container.post(new Runnable() { // from class: com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet$$ExternalSyntheticLambda1
            @Override // java.lang.Runnable
            public final void run() {
                InstallPluginBottomSheet.this.lambda$new$0(view, rounding);
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$new$0(View view, HintView2 hintView2) {
        view.getLocationInWindow(r1);
        int[] iArr = new int[2];
        this.container.getLocationInWindow(iArr);
        int i = r1[1] - iArr[1];
        int[] iArr2 = {iArr2[0] - iArr[0], i};
        hintView2.setTranslationY((i - AndroidUtilities.dp(100.0f)) - AndroidUtilities.dp(6.0f));
        hintView2.setJointPx(0.0f, (-AndroidUtilities.dp(32.0f)) + iArr2[0] + (view.getMeasuredWidth() / 2.0f));
        hintView2.setDuration(5500L);
        hintView2.show();
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$new$8(PluginInstallParams pluginInstallParams, final PluginsController.PluginValidationResult pluginValidationResult, final BaseFragment baseFragment, final boolean z, View view) {
        lambda$new$0();
        PythonPluginsEngine pythonPluginsEngine = (PythonPluginsEngine) PluginsController.engines.get(PluginsConstants.PYTHON);
        if (pythonPluginsEngine == null) {
            return;
        }
        pythonPluginsEngine.loadPluginFromFile(pluginInstallParams.filePath, pluginValidationResult.plugin, new Utilities.Callback() { // from class: com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet$$ExternalSyntheticLambda0
            @Override // org.telegram.messenger.Utilities.Callback
            public final void run(Object obj) {
                InstallPluginBottomSheet.this.lambda$new$7(baseFragment, pluginValidationResult, z, (String) obj);
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$new$7(final BaseFragment baseFragment, final PluginsController.PluginValidationResult pluginValidationResult, final boolean z, final String str) {
        if (str != null) {
            AndroidUtilities.runOnUIThread(new Runnable() { // from class: com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet$$ExternalSyntheticLambda14
                @Override // java.lang.Runnable
                public final void run() {
                    BulletinFactory.of(r0).createSimpleBulletin(R.raw.error, LocaleController.formatString(R.string.PluginInstallError, pluginValidationResult.plugin.getName()), LocaleUtils.createCopySpan(r0), new Runnable() { // from class: com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet$$ExternalSyntheticLambda13
                        @Override // java.lang.Runnable
                        public final void run() {
                            InstallPluginBottomSheet.m585$r8$lambda$A7aFGsHMGMa4HVzPbK7QOFrcVE(r1, r2);
                        }
                    }).show();
                }
            });
        } else if (this.enableAfterInstallation) {
            PluginsController.getInstance().setPluginEnabled(pluginValidationResult.plugin.getId(), true, new Utilities.Callback() { // from class: com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet$$ExternalSyntheticLambda15
                @Override // org.telegram.messenger.Utilities.Callback
                public final void run(Object obj) {
                    InstallPluginBottomSheet.this.lambda$new$5(baseFragment, pluginValidationResult, z, (String) obj);
                }
            });
        } else {
            AndroidUtilities.runOnUIThread(new Runnable() { // from class: com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet$$ExternalSyntheticLambda16
                @Override // java.lang.Runnable
                public final void run() {
                    InstallPluginBottomSheet.this.lambda$new$6(baseFragment, pluginValidationResult, z);
                }
            });
        }
    }

    /* renamed from: $r8$lambda$A7aFGsHMGMa4HVzPbK7Q-OFrcVE, reason: not valid java name */
    public static /* synthetic */ void m585$r8$lambda$A7aFGsHMGMa4HVzPbK7QOFrcVE(String str, BaseFragment baseFragment) {
        if (AndroidUtilities.addToClipboard(str)) {
            BulletinFactory.of(baseFragment).createCopyBulletin(LocaleController.getString(R.string.TextCopied)).show();
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$new$5(final BaseFragment baseFragment, PluginsController.PluginValidationResult pluginValidationResult, boolean z, final String str) {
        if (str == null) {
            showSuccessBulletin(baseFragment, pluginValidationResult.plugin, z);
        } else {
            BulletinFactory.of(baseFragment).createSimpleBulletin(R.raw.error, LocaleController.formatString(R.string.PluginInstalledButFailedToEnable, pluginValidationResult.plugin.getName()), LocaleUtils.createCopySpan(baseFragment), new Runnable() { // from class: com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet$$ExternalSyntheticLambda3
                @Override // java.lang.Runnable
                public final void run() {
                    InstallPluginBottomSheet.m589$r8$lambda$lvJDf0WVltZZt4leIihxTBEd94(str, baseFragment);
                }
            }).show();
        }
    }

    /* renamed from: $r8$lambda$lvJDf0W-VltZZt4leIihxTBEd94, reason: not valid java name */
    public static /* synthetic */ void m589$r8$lambda$lvJDf0WVltZZt4leIihxTBEd94(String str, BaseFragment baseFragment) {
        if (AndroidUtilities.addToClipboard(str)) {
            BulletinFactory.of(baseFragment).createCopyBulletin(LocaleController.getString(R.string.TextCopied)).show();
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$new$6(BaseFragment baseFragment, PluginsController.PluginValidationResult pluginValidationResult, boolean z) {
        showSuccessBulletin(baseFragment, pluginValidationResult.plugin, z);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$new$9(CheckBox2 checkBox2, View view) {
        checkBox2.setChecked(!checkBox2.isChecked(), true);
        this.enableAfterInstallation = checkBox2.isChecked();
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$new$10(PluginInstallParams pluginInstallParams, BaseFragment baseFragment, View view) {
        lambda$new$0();
        File file = new File(pluginInstallParams.filePath);
        if (file.exists()) {
            AndroidUtilities.openForView(file, file.getName(), "text/plain", baseFragment.getParentActivity(), baseFragment.getResourceProvider(), false);
        }
    }

    public static /* synthetic */ void $r8$lambda$NCk_PnzBOhorfCXboXcLY60hXac(LinearLayout linearLayout, PluginInstallParams pluginInstallParams) {
        linearLayout.performClick();
        ExteraConfig.editor.putBoolean(pluginInstallParams.trusted ? "trusted_source_hint" : "unknown_source_hint", true).apply();
    }

    private void showSuccessBulletin(BaseFragment baseFragment, final Plugin plugin, final boolean z) {
        final BulletinFactory of = BulletinFactory.of(baseFragment);
        final String name = plugin.getName();
        if (plugin.getPack() != null && plugin.getIndex() >= 0) {
            TLRPC.TL_inputStickerSetShortName tL_inputStickerSetShortName = new TLRPC.TL_inputStickerSetShortName();
            tL_inputStickerSetShortName.short_name = plugin.getPack();
            final AtomicBoolean atomicBoolean = new AtomicBoolean(false);
            final Runnable runnable = new Runnable() { // from class: com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet$$ExternalSyntheticLambda4
                @Override // java.lang.Runnable
                public final void run() {
                    InstallPluginBottomSheet.this.lambda$showSuccessBulletin$12(atomicBoolean, plugin, z, of);
                }
            };
            AndroidUtilities.runOnUIThread(runnable, 300L);
            MediaDataController.getInstance(UserConfig.selectedAccount).getStickerSet(tL_inputStickerSetShortName, 0, true, new Utilities.Callback() { // from class: com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet$$ExternalSyntheticLambda5
                @Override // org.telegram.messenger.Utilities.Callback
                public final void run(Object obj) {
                    AndroidUtilities.runOnUIThread(new Runnable() { // from class: com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet$$ExternalSyntheticLambda6
                        @Override // java.lang.Runnable
                        public final void run() {
                            InstallPluginBottomSheet.$r8$lambda$kMo5amo6SQXo92NGMU3_DxDvMOE(r1, r2, r3, r4, r5, r6, r7);
                        }
                    });
                }
            });
            return;
        }
        showSimpleSuccessBulletin(plugin, z, of);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$showSuccessBulletin$12(AtomicBoolean atomicBoolean, Plugin plugin, boolean z, BulletinFactory bulletinFactory) {
        if (atomicBoolean.getAndSet(true)) {
            return;
        }
        showSimpleSuccessBulletin(plugin, z, bulletinFactory);
    }

    public static /* synthetic */ void $r8$lambda$kMo5amo6SQXo92NGMU3_DxDvMOE(AtomicBoolean atomicBoolean, TLRPC.TL_messages_stickerSet tL_messages_stickerSet, final Plugin plugin, Runnable runnable, boolean z, String str, BulletinFactory bulletinFactory) {
        Bulletin createSimpleBulletin;
        ArrayList arrayList;
        int index;
        if (atomicBoolean.get()) {
            return;
        }
        TLRPC.Document document = (tL_messages_stickerSet == null || (arrayList = tL_messages_stickerSet.documents) == null || arrayList.isEmpty() || (index = plugin.getIndex()) < 0 || index >= tL_messages_stickerSet.documents.size()) ? null : (TLRPC.Document) tL_messages_stickerSet.documents.get(index);
        if (document == null || atomicBoolean.getAndSet(true)) {
            return;
        }
        AndroidUtilities.cancelRunOnUIThread(runnable);
        SpannableStringBuilder replaceTags = AndroidUtilities.replaceTags(LocaleController.formatString(z ? R.string.PluginUpdated : R.string.PluginInstalled, str));
        Plugin plugin2 = PluginsController.getInstance().plugins.get(plugin.getId());
        if (plugin2 != null && plugin2.hasSettings() && plugin2.isEnabled()) {
            createSimpleBulletin = bulletinFactory.createEmojiBulletin(document, replaceTags, LocaleController.getString(R.string.Settings), new Runnable() { // from class: com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet$$ExternalSyntheticLambda2
                @Override // java.lang.Runnable
                public final void run() {
                    PluginsController.openPluginSettings(Plugin.this.getId());
                }
            });
        } else {
            createSimpleBulletin = bulletinFactory.createSimpleBulletin(document, replaceTags);
        }
        createSimpleBulletin.show();
    }

    private void showSimpleSuccessBulletin(final Plugin plugin, boolean z, BulletinFactory bulletinFactory) {
        String formatString = LocaleController.formatString(z ? R.string.PluginUpdated : R.string.PluginInstalled, plugin.getName());
        Plugin plugin2 = PluginsController.getInstance().plugins.get(plugin.getId());
        if (plugin2 != null && plugin2.hasSettings() && plugin2.isEnabled()) {
            bulletinFactory.createSimpleBulletin(R.raw.contact_check, formatString, LocaleController.getString(R.string.Settings), new Runnable() { // from class: com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet$$ExternalSyntheticLambda17
                @Override // java.lang.Runnable
                public final void run() {
                    PluginsController.openPluginSettings(Plugin.this.getId());
                }
            }).show();
        } else {
            bulletinFactory.createSimpleBulletin(R.raw.contact_check, formatString).show();
        }
    }

    @Override // org.telegram.ui.ActionBar.BottomSheet, android.app.Dialog, android.content.DialogInterface, org.telegram.ui.ActionBar.BaseFragment.AttachedSheet
    /* renamed from: dismiss */
    public void lambda$new$0() {
        HintView2 hintView2 = this.currentHint;
        if (hintView2 != null) {
            hintView2.hide();
            this.currentHint = null;
        }
        super.lambda$new$0();
    }

    @Override // org.telegram.ui.ActionBar.BottomSheet
    protected void onSwipeStarts() {
        HintView2 hintView2 = this.currentHint;
        if (hintView2 != null) {
            hintView2.hide();
            this.currentHint = null;
        }
    }

    /* loaded from: classes.dex */
    public static class PluginInstallParams {
        public String filePath;
        public boolean trusted;

        public PluginInstallParams(String str, boolean z) {
            this.filePath = str;
            this.trusted = z;
        }

        /* JADX WARN: Code restructure failed: missing block: B:21:0x004c, code lost:
        
            if (r6.isExtera(r4) == false) goto L20;
         */
        /* JADX WARN: Code restructure failed: missing block: B:8:0x002c, code lost:
        
            if (r1.isExtera(-r6.longValue()) == false) goto L20;
         */
        /* JADX WARN: Code restructure failed: missing block: B:9:0x004f, code lost:
        
            r2 = false;
         */
        /*
            Code decompiled incorrectly, please refer to instructions dump.
            To view partially-correct add '--show-bad-code' argument
        */
        public static com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet.PluginInstallParams of(org.telegram.messenger.MessageObject r6) {
            /*
                com.exteragram.messenger.utils.ChatUtils r0 = com.exteragram.messenger.utils.ChatUtils.getInstance()
                java.lang.String r0 = r0.getPathToMessage(r6)
                boolean r1 = r6.isForwarded()
                r2 = 1
                r3 = 0
                if (r1 == 0) goto L2f
                java.lang.Long r6 = r6.getForwardedFromId()
                if (r6 == 0) goto L51
                com.exteragram.messenger.badges.BadgesController r1 = com.exteragram.messenger.badges.BadgesController.INSTANCE
                long r4 = r6.longValue()
                long r4 = -r4
                boolean r4 = r1.isTrusted(r4)
                if (r4 != 0) goto L50
                long r4 = r6.longValue()
                long r4 = -r4
                boolean r6 = r1.isExtera(r4)
                if (r6 == 0) goto L4f
                goto L50
            L2f:
                boolean r1 = r6.isFromChannel()
                if (r1 == 0) goto L51
                boolean r1 = r6.isFromChat()
                if (r1 != 0) goto L51
                long r4 = r6.getDialogId()
                long r4 = -r4
                com.exteragram.messenger.badges.BadgesController r6 = com.exteragram.messenger.badges.BadgesController.INSTANCE
                boolean r1 = r6.isTrusted(r4)
                if (r1 != 0) goto L50
                boolean r6 = r6.isExtera(r4)
                if (r6 == 0) goto L4f
                goto L50
            L4f:
                r2 = r3
            L50:
                r3 = r2
            L51:
                com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet$PluginInstallParams r6 = new com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet$PluginInstallParams
                r6.<init>(r0, r3)
                return r6
            */
            throw new UnsupportedOperationException("Method not decompiled: com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet.PluginInstallParams.of(org.telegram.messenger.MessageObject):com.exteragram.messenger.plugins.ui.components.InstallPluginBottomSheet$PluginInstallParams");
        }
    }
}
