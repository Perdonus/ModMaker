package com.exteragram.messenger.plugins.ui;

import android.app.Dialog;
import android.content.Context;
import android.content.DialogInterface;
import android.text.TextUtils;
import android.view.View;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import androidx.recyclerview.widget.LinearLayoutManager;
import com.chaquo.python.PyObject;
import com.exteragram.messenger.plugins.Plugin;
import com.exteragram.messenger.plugins.PluginsConstants;
import com.exteragram.messenger.plugins.PluginsController;
import com.exteragram.messenger.plugins.PythonPluginsEngine;
import com.exteragram.messenger.plugins.models.DividerSetting;
import com.exteragram.messenger.plugins.models.EditTextSetting;
import com.exteragram.messenger.plugins.models.HeaderSetting;
import com.exteragram.messenger.plugins.models.InputSetting;
import com.exteragram.messenger.plugins.models.SelectorSetting;
import com.exteragram.messenger.plugins.models.SettingItem;
import com.exteragram.messenger.plugins.models.SwitchSetting;
import com.exteragram.messenger.plugins.models.TextSetting;
import com.exteragram.messenger.plugins.ui.components.PluginEditTextCell;
import com.exteragram.messenger.preferences.utils.SettingsRegistry;
import com.exteragram.messenger.utils.system.VibratorUtils;
import com.exteragram.messenger.utils.text.LocaleUtils;
import j$.util.Objects;
import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.atomic.AtomicReference;
import org.telegram.messenger.AndroidUtilities;
import org.telegram.messenger.ApplicationLoader;
import org.telegram.messenger.FileLog;
import org.telegram.messenger.LocaleController;
import org.telegram.messenger.NotificationCenter;
import org.telegram.messenger.R;
import org.telegram.messenger.Utilities;
import org.telegram.ui.ActionBar.ActionBar;
import org.telegram.ui.ActionBar.ActionBarMenuItem;
import org.telegram.ui.ActionBar.AlertDialog;
import org.telegram.ui.ActionBar.BaseFragment;
import org.telegram.ui.ActionBar.Theme;
import org.telegram.ui.Cells.NotificationsCheckCell;
import org.telegram.ui.Cells.RadioColorCell;
import org.telegram.ui.Cells.TextCell;
import org.telegram.ui.Cells.TextCheckCell;
import org.telegram.ui.Components.BulletinFactory;
import org.telegram.ui.Components.EditTextBoldCursor;
import org.telegram.ui.Components.ItemOptions;
import org.telegram.ui.Components.LayoutHelper;
import org.telegram.ui.Components.RecyclerListView;
import org.telegram.ui.Components.UItem;
import org.telegram.ui.Components.UniversalAdapter;
import org.telegram.ui.Components.UniversalRecyclerView;

/* loaded from: classes4.dex */
public class PluginSettingsActivity extends BaseFragment implements NotificationCenter.NotificationCenterDelegate {
    private final PyObject createSubFragmentCallback;
    private final String customTitle;
    protected LinearLayoutManager layoutManager;
    private UniversalRecyclerView listView;
    private final Plugin plugin;
    private ActionBarMenuItem resetItem;
    private List<SettingItem> settingItems;
    private String settingsLinkPrefix;
    private Integer targetSettingItemId;
    private String targetSettingName;

    public PluginSettingsActivity(Plugin plugin) {
        this.plugin = plugin;
        this.customTitle = null;
        this.settingItems = null;
        this.createSubFragmentCallback = null;
        this.targetSettingName = null;
        this.targetSettingItemId = null;
        this.settingsLinkPrefix = null;
    }

    public PluginSettingsActivity(Plugin plugin, String str) {
        this.plugin = plugin;
        this.customTitle = null;
        this.settingItems = null;
        this.createSubFragmentCallback = null;
        this.targetSettingName = str;
        this.targetSettingItemId = null;
        this.settingsLinkPrefix = null;
    }

    public PluginSettingsActivity(Plugin plugin, String str, List<SettingItem> list, PyObject pyObject) {
        this(plugin, str, list, pyObject, null);
    }

    public PluginSettingsActivity(Plugin plugin, String str, List<SettingItem> list, PyObject pyObject, String str2) {
        this.plugin = plugin;
        this.customTitle = str;
        this.settingItems = list;
        this.createSubFragmentCallback = pyObject;
        this.targetSettingName = str2;
        this.targetSettingItemId = null;
        this.settingsLinkPrefix = null;
    }

    public PluginSettingsActivity setSettingsLinkPrefix(String str) {
        this.settingsLinkPrefix = str;
        return this;
    }

    @Override // org.telegram.ui.ActionBar.BaseFragment
    public boolean onFragmentCreate() {
        NotificationCenter.getGlobalInstance().addObserver(this, NotificationCenter.pluginSettingsRegistered);
        NotificationCenter.getGlobalInstance().addObserver(this, NotificationCenter.pluginSettingsUnregistered);
        return super.onFragmentCreate();
    }

    @Override // org.telegram.ui.ActionBar.BaseFragment
    public void onFragmentDestroy() {
        NotificationCenter.getGlobalInstance().removeObserver(this, NotificationCenter.pluginSettingsRegistered);
        NotificationCenter.getGlobalInstance().removeObserver(this, NotificationCenter.pluginSettingsUnregistered);
        super.onFragmentDestroy();
    }

    /* JADX WARN: Removed duplicated region for block: B:10:0x0016  */
    /* JADX WARN: Removed duplicated region for block: B:30:? A[RETURN, SYNTHETIC] */
    @Override // org.telegram.messenger.NotificationCenter.NotificationCenterDelegate
    /*
        Code decompiled incorrectly, please refer to instructions dump.
        To view partially-correct add '--show-bad-code' argument
    */
    public void didReceivedNotification(int r2, int r3, java.lang.Object... r4) {
        /*
            r1 = this;
            int r3 = org.telegram.messenger.NotificationCenter.pluginSettingsRegistered
            r0 = 0
            if (r2 != r3) goto L53
            int r2 = r4.length
            if (r2 <= 0) goto L11
            r2 = r4[r0]
            boolean r3 = r2 instanceof java.lang.String
            if (r3 == 0) goto L11
            java.lang.String r2 = (java.lang.String) r2
            goto L12
        L11:
            r2 = 0
        L12:
            com.exteragram.messenger.plugins.Plugin r3 = r1.plugin
            if (r3 == 0) goto L83
            if (r2 == 0) goto L22
            java.lang.String r3 = r3.getId()
            boolean r2 = r3.equals(r2)
            if (r2 == 0) goto L83
        L22:
            com.chaquo.python.PyObject r2 = r1.createSubFragmentCallback
            if (r2 == 0) goto L2f
            com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda7 r2 = new com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda7
            r2.<init>()
            com.exteragram.messenger.plugins.PluginsController.runOnPluginsQueue(r2)
            return
        L2f:
            org.telegram.ui.Components.UniversalRecyclerView r2 = r1.listView
            if (r2 == 0) goto L83
            org.telegram.ui.Components.UniversalAdapter r2 = r2.adapter
            if (r2 == 0) goto L83
            r3 = 1
            r2.update(r3)
            org.telegram.ui.ActionBar.ActionBarMenuItem r2 = r1.resetItem
            if (r2 == 0) goto L83
            com.exteragram.messenger.plugins.PluginsController r4 = com.exteragram.messenger.plugins.PluginsController.getInstance()
            com.exteragram.messenger.plugins.Plugin r0 = r1.plugin
            java.lang.String r0 = r0.getId()
            boolean r4 = r4.hasPluginSettingsPreferences(r0)
            r0 = 1056964608(0x3f000000, float:0.5)
            org.telegram.messenger.AndroidUtilities.updateViewVisibilityAnimated(r2, r4, r0, r3)
            return
        L53:
            int r3 = org.telegram.messenger.NotificationCenter.pluginSettingsUnregistered
            if (r2 != r3) goto L83
            int r2 = r4.length
            if (r2 <= 0) goto L83
            r2 = r4[r0]
            boolean r3 = r2 instanceof java.lang.String
            if (r3 == 0) goto L83
            java.lang.String r2 = (java.lang.String) r2
            com.exteragram.messenger.plugins.Plugin r3 = r1.plugin
            if (r3 == 0) goto L83
            java.lang.String r3 = r3.getId()
            boolean r2 = r3.equals(r2)
            if (r2 == 0) goto L83
            com.exteragram.messenger.plugins.PluginsController r2 = com.exteragram.messenger.plugins.PluginsController.getInstance()
            com.exteragram.messenger.plugins.Plugin r3 = r1.plugin
            java.lang.String r3 = r3.getId()
            boolean r2 = r2.hasPluginSettings(r3)
            if (r2 != 0) goto L83
            r1.finishFragment()
        L83:
            return
        */
        throw new UnsupportedOperationException("Method not decompiled: com.exteragram.messenger.plugins.ui.PluginSettingsActivity.didReceivedNotification(int, int, java.lang.Object[]):void");
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$didReceivedNotification$1() {
        final List<SettingItem> arrayList = new ArrayList<>();
        try {
            PyObject call = this.createSubFragmentCallback.call(new Object[0]);
            if (call != null) {
                PluginsController.PluginsEngine pluginsEngine = PluginsController.engines.get(PluginsConstants.PYTHON);
                Objects.requireNonNull(pluginsEngine);
                arrayList = ((PythonPluginsEngine) pluginsEngine).parsePySettingDefinitions(call.asList());
            }
            AndroidUtilities.runOnUIThread(new Runnable() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda6
                @Override // java.lang.Runnable
                public final void run() {
                    PluginSettingsActivity.this.lambda$didReceivedNotification$0(arrayList);
                }
            });
        } catch (Exception unused) {
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$didReceivedNotification$0(List list) {
        UniversalAdapter universalAdapter;
        this.settingItems = list;
        UniversalRecyclerView universalRecyclerView = this.listView;
        if (universalRecyclerView == null || (universalAdapter = universalRecyclerView.adapter) == null) {
            return;
        }
        universalAdapter.update(true);
    }

    @Override // org.telegram.ui.ActionBar.BaseFragment
    public View createView(Context context) {
        this.actionBar.setBackButtonImage(R.drawable.ic_ab_back);
        this.actionBar.setAllowOverlayTitle(true);
        ActionBar actionBar = this.actionBar;
        String str = this.customTitle;
        if (str == null) {
            str = this.plugin.getName();
        }
        actionBar.setTitle(str);
        this.actionBar.setActionBarMenuOnItemClick(new ActionBar.ActionBarMenuOnItemClick() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity.1
            @Override // org.telegram.ui.ActionBar.ActionBar.ActionBarMenuOnItemClick
            public void onItemClick(int i) {
                if (i == -1) {
                    PluginSettingsActivity.this.finishFragment();
                }
            }
        });
        if (this.createSubFragmentCallback == null && this.plugin != null) {
            ActionBarMenuItem addItem = this.actionBar.createMenu().addItem(0, R.drawable.msg_reset);
            this.resetItem = addItem;
            addItem.setContentDescription(LocaleController.getString(R.string.Reset));
            AndroidUtilities.updateViewVisibilityAnimated(this.resetItem, PluginsController.getInstance().hasPluginSettingsPreferences(this.plugin.getId()), 0.5f, false);
            this.resetItem.setTag(null);
            this.resetItem.setOnClickListener(new View.OnClickListener() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda15
                @Override // android.view.View.OnClickListener
                public final void onClick(View view) {
                    PluginSettingsActivity.this.lambda$createView$5(view);
                }
            });
        }
        FrameLayout frameLayout = new FrameLayout(context);
        frameLayout.setBackgroundColor(Theme.getColor(Theme.key_windowBackgroundGray));
        UniversalRecyclerView universalRecyclerView = new UniversalRecyclerView(this, new Utilities.Callback2() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda16
            @Override // org.telegram.messenger.Utilities.Callback2
            public final void run(Object obj, Object obj2) {
                PluginSettingsActivity.this.fillItems((ArrayList) obj, (UniversalAdapter) obj2);
            }
        }, new Utilities.Callback5() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda17
            @Override // org.telegram.messenger.Utilities.Callback5
            public final void run(Object obj, Object obj2, Object obj3, Object obj4, Object obj5) {
                PluginSettingsActivity.this.onClick((UItem) obj, (View) obj2, ((Integer) obj3).intValue(), ((Float) obj4).floatValue(), ((Float) obj5).floatValue());
            }
        }, new Utilities.Callback5Return() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda18
            @Override // org.telegram.messenger.Utilities.Callback5Return
            public final Object run(Object obj, Object obj2, Object obj3, Object obj4, Object obj5) {
                boolean onLongClick;
                onLongClick = PluginSettingsActivity.this.onLongClick((UItem) obj, (View) obj2, ((Integer) obj3).intValue(), ((Float) obj4).floatValue(), ((Float) obj5).floatValue());
                return Boolean.valueOf(onLongClick);
            }
        });
        this.listView = universalRecyclerView;
        universalRecyclerView.adapter.setUseSectionStyle(true);
        UniversalRecyclerView universalRecyclerView2 = this.listView;
        LinearLayoutManager linearLayoutManager = new LinearLayoutManager(context, 1, false);
        this.layoutManager = linearLayoutManager;
        universalRecyclerView2.setLayoutManager(linearLayoutManager);
        frameLayout.addView(this.listView, LayoutHelper.createFrame(-1, -1.0f));
        this.fragmentView = frameLayout;
        return frameLayout;
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$createView$5(View view) {
        AlertDialog.Builder builder = new AlertDialog.Builder(getContext(), getResourceProvider());
        builder.setTitle(LocaleController.getString(R.string.ResetSettings));
        builder.setMessage(AndroidUtilities.replaceTags(LocaleController.formatString(R.string.ResetPluginSettingsInfo, this.plugin.getName())));
        builder.setPositiveButton(LocaleController.getString(R.string.Reset), new AlertDialog.OnButtonClickListener() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda0
            @Override // org.telegram.ui.ActionBar.AlertDialog.OnButtonClickListener
            public final void onClick(AlertDialog alertDialog, int i) {
                PluginSettingsActivity.this.lambda$createView$4(alertDialog, i);
            }
        });
        builder.setNegativeButton(LocaleController.getString(R.string.Cancel), null);
        AlertDialog create = builder.create();
        showDialog(create);
        TextView textView = (TextView) create.getButton(-1);
        if (textView != null) {
            textView.setTextColor(Theme.getColor(Theme.key_text_RedBold));
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$createView$4(AlertDialog alertDialog, int i) {
        View findFocus;
        View view = this.fragmentView;
        if (view != null && (findFocus = view.findFocus()) != null) {
            findFocus.clearFocus();
        }
        AndroidUtilities.updateViewVisibilityAnimated(this.resetItem, false, 0.5f, true);
        PluginsController.runOnPluginsQueue(new Runnable() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda4
            @Override // java.lang.Runnable
            public final void run() {
                PluginSettingsActivity.this.lambda$createView$3();
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$createView$3() {
        PluginsController.getInstance().clearPluginSettingsPreferences(this.plugin.getId());
        PluginsController.getInstance().loadPluginSettings(this.plugin.getId());
        AndroidUtilities.runOnUIThread(new Runnable() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda23
            @Override // java.lang.Runnable
            public final void run() {
                PluginSettingsActivity.this.lambda$createView$2();
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$createView$2() {
        BulletinFactory.of(this).createSimpleBulletin(R.raw.info, LocaleController.formatString(R.string.ResetPluginSettings, this.plugin.getName())).show();
    }

    public void checkTargetSetting() {
        UniversalRecyclerView universalRecyclerView;
        Integer num = this.targetSettingItemId;
        if (num != null && (universalRecyclerView = this.listView) != null && universalRecyclerView.adapter != null) {
            final int findPositionByItemId = universalRecyclerView.findPositionByItemId(num.intValue());
            if (findPositionByItemId >= 0 && findPositionByItemId < this.listView.adapter.getItemCount()) {
                this.listView.highlightRow(new RecyclerListView.IntReturnCallback() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda14
                    @Override // org.telegram.ui.Components.RecyclerListView.IntReturnCallback
                    public final int run() {
                        int lambda$checkTargetSetting$6;
                        lambda$checkTargetSetting$6 = PluginSettingsActivity.this.lambda$checkTargetSetting$6(findPositionByItemId);
                        return lambda$checkTargetSetting$6;
                    }
                });
            }
            this.targetSettingItemId = null;
            return;
        }
        SettingsRegistry.getInstance().onSettingNotFound(this);
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ int lambda$checkTargetSetting$6(int i) {
        this.layoutManager.scrollToPositionWithOffset(i, AndroidUtilities.dp(60.0f));
        return i;
    }

    /* JADX INFO: Access modifiers changed from: private */
    /* JADX WARN: Failed to find 'out' block for switch in B:21:0x005c. Please report as an issue. */
    public void fillItems(ArrayList<UItem> arrayList, UniversalAdapter universalAdapter) {
        String str;
        int i;
        UItem uItem;
        String str2;
        String str3;
        String str4;
        HeaderSetting headerSetting;
        String str5;
        UItem asButtonCheck;
        UItem asButton;
        String[] strArr;
        if (this.plugin == null) {
            return;
        }
        List<SettingItem> list = this.settingItems;
        if (list == null) {
            list = PluginsController.getInstance().getPluginSettingsList(this.plugin.getId());
        }
        if (list == null || list.isEmpty()) {
            return;
        }
        boolean z = false;
        for (SettingItem settingItem : list) {
            if (settingItem != null) {
                if (TextUtils.isEmpty(settingItem.icon)) {
                    i = 0;
                } else {
                    Context context = ApplicationLoader.applicationContext;
                    i = context.getResources().getIdentifier(settingItem.icon, "drawable", context.getPackageName());
                }
                try {
                    str4 = settingItem.type;
                } catch (Exception unused) {
                }
                switch (str4.hashCode()) {
                    case -1866021310:
                        if (str4.equals(PluginsConstants.Settings.TYPE_EDIT_TEXT)) {
                            EditTextSetting editTextSetting = (EditTextSetting) settingItem;
                            if (editTextSetting.key != null && editTextSetting.hint != null) {
                                uItem = PluginEditTextCell.Factory.as(this.plugin, editTextSetting);
                                break;
                            }
                        }
                        uItem = null;
                        break;
                    case -1221270899:
                        if (str4.equals(PluginsConstants.Settings.TYPE_HEADER) && (str5 = (headerSetting = (HeaderSetting) settingItem).text) != null) {
                            UItem asHeader = UItem.asHeader(str5);
                            asHeader.settingItem = headerSetting;
                            uItem = asHeader;
                            break;
                        }
                        uItem = null;
                        break;
                    case -889473228:
                        if (str4.equals(PluginsConstants.Settings.TYPE_SWITCH)) {
                            SwitchSetting switchSetting = (SwitchSetting) settingItem;
                            if (switchSetting.key != null && switchSetting.text != null) {
                                boolean pluginSettingBoolean = PluginsController.getInstance().getPluginSettingBoolean(this.plugin.getId(), switchSetting.key, switchSetting.defaultValue);
                                String str6 = switchSetting.subtext;
                                asButtonCheck = str6 != null ? i != 0 ? UItem.asButtonCheck(0, switchSetting.text, str6, i) : UItem.asButtonCheck(0, switchSetting.text, str6) : UItem.asCheck(0, switchSetting.text, i);
                                asButtonCheck.setChecked(pluginSettingBoolean);
                                asButtonCheck.drawLine = false;
                                if (i != 0) {
                                    asButtonCheck.iconResId = i;
                                }
                                asButtonCheck.object2 = switchSetting.key;
                                asButtonCheck.settingItem = switchSetting;
                                uItem = asButtonCheck;
                                break;
                            }
                        }
                        uItem = null;
                        break;
                    case 3556653:
                        if (str4.equals("text")) {
                            TextSetting textSetting = (TextSetting) settingItem;
                            asButton = UItem.asButton(0, textSetting.text);
                            asButton.settingItem = textSetting;
                            if (i != 0) {
                                asButton.iconResId = i;
                            }
                            asButton.accent = textSetting.accent;
                            asButton.red = textSetting.red;
                            uItem = asButton;
                            break;
                        }
                        uItem = null;
                        break;
                    case 100358090:
                        if (str4.equals(PluginsConstants.Settings.TYPE_INPUT)) {
                            InputSetting inputSetting = (InputSetting) settingItem;
                            if (inputSetting.key != null && inputSetting.text != null) {
                                asButton = UItem.asButton(0, inputSetting.text, PluginsController.getInstance().getPluginSettingString(this.plugin.getId(), inputSetting.key, inputSetting.defaultValue));
                                if (i != 0) {
                                    asButton.iconResId = i;
                                }
                                asButton.object2 = inputSetting.key;
                                asButton.settingItem = inputSetting;
                                uItem = asButton;
                                break;
                            }
                        }
                        uItem = null;
                        break;
                    case 1191572447:
                        if (str4.equals(PluginsConstants.Settings.TYPE_SELECTOR)) {
                            SelectorSetting selectorSetting = (SelectorSetting) settingItem;
                            if (selectorSetting.key != null && selectorSetting.text != null && (strArr = selectorSetting.items) != null && strArr.length != 0) {
                                int pluginSettingInt = PluginsController.getInstance().getPluginSettingInt(this.plugin.getId(), selectorSetting.key, selectorSetting.defaultValue);
                                if (pluginSettingInt < 0 || pluginSettingInt >= selectorSetting.items.length) {
                                    pluginSettingInt = Math.max(0, Math.min(selectorSetting.defaultValue, selectorSetting.items.length - 1));
                                    PluginsController.getInstance().setPluginSetting(this.plugin.getId(), selectorSetting.key, Integer.valueOf(pluginSettingInt));
                                }
                                asButtonCheck = UItem.asButton(0, selectorSetting.text, selectorSetting.items[pluginSettingInt]);
                                asButtonCheck.texts = selectorSetting.items;
                                asButtonCheck.intValue = pluginSettingInt;
                                if (i != 0) {
                                    asButtonCheck.iconResId = i;
                                }
                                asButtonCheck.object2 = selectorSetting.key;
                                asButtonCheck.settingItem = selectorSetting;
                                uItem = asButtonCheck;
                                break;
                            }
                        }
                        uItem = null;
                        break;
                    case 1674318617:
                        if (str4.equals(PluginsConstants.Settings.TYPE_DIVIDER)) {
                            String str7 = ((DividerSetting) settingItem).text;
                            uItem = UItem.asShadow(str7 != null ? LocaleUtils.fullyFormatText(str7, this, null) : "");
                            break;
                        }
                        uItem = null;
                        break;
                    default:
                        uItem = null;
                        break;
                }
                if (uItem != null) {
                    uItem.id = getStableId(settingItem);
                    SettingItem settingItem2 = uItem.settingItem;
                    if (settingItem2 != null && (str2 = settingItem2.linkAlias) != null && !TextUtils.isEmpty(str2) && (str3 = this.targetSettingName) != null && !TextUtils.isEmpty(str3) && uItem.settingItem.linkAlias.equals(this.targetSettingName)) {
                        this.targetSettingItemId = Integer.valueOf(uItem.id);
                        this.targetSettingName = null;
                        z = true;
                    }
                    arrayList.add(uItem);
                }
            }
        }
        if (z || (str = this.targetSettingName) == null || TextUtils.isEmpty(str)) {
            return;
        }
        SettingsRegistry.getInstance().onSettingNotFound(this);
        this.targetSettingName = null;
    }

    /* JADX INFO: Access modifiers changed from: private */
    public void onClick(final UItem uItem, View view, int i, float f, float f2) {
        if (uItem == null || this.plugin == null) {
            return;
        }
        SettingItem settingItem = uItem.settingItem;
        if (settingItem instanceof TextSetting) {
            final TextSetting textSetting = (TextSetting) settingItem;
            if (textSetting.createSubFragmentCallback != null) {
                PluginsController.runOnPluginsQueue(new Runnable() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda20
                    @Override // java.lang.Runnable
                    public final void run() {
                        PluginSettingsActivity.this.lambda$onClick$8(textSetting, uItem);
                    }
                });
                return;
            }
            PyObject pyObject = textSetting.onClickCallback;
            if (pyObject != null) {
                try {
                    pyObject.call(view);
                    return;
                } catch (Exception unused) {
                    return;
                }
            }
        }
        Object obj = uItem.object2;
        if (obj instanceof String) {
            final String str = (String) obj;
            if (view instanceof TextCheckCell) {
                TextCheckCell textCheckCell = (TextCheckCell) view;
                final boolean z = !textCheckCell.isChecked();
                textCheckCell.setChecked(z);
                uItem.setChecked(z);
                PluginsController.runOnPluginsQueue(new Runnable() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda21
                    @Override // java.lang.Runnable
                    public final void run() {
                        PluginSettingsActivity.this.lambda$onClick$9(str, z, uItem);
                    }
                });
                return;
            }
            if (view instanceof NotificationsCheckCell) {
                NotificationsCheckCell notificationsCheckCell = (NotificationsCheckCell) view;
                final boolean z2 = !notificationsCheckCell.isChecked();
                notificationsCheckCell.setChecked(z2);
                uItem.setChecked(z2);
                PluginsController.runOnPluginsQueue(new Runnable() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda22
                    @Override // java.lang.Runnable
                    public final void run() {
                        PluginSettingsActivity.this.lambda$onClick$10(str, z2, uItem);
                    }
                });
                return;
            }
            if (view instanceof TextCell) {
                if (settingItem instanceof SelectorSetting) {
                    showSelectorDialog(uItem, view, str);
                } else if (settingItem instanceof InputSetting) {
                    showStringInputDialog(uItem, view, str);
                }
            }
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$onClick$8(final TextSetting textSetting, final UItem uItem) {
        final List<SettingItem> arrayList = new ArrayList<>();
        try {
            PyObject call = textSetting.createSubFragmentCallback.call(new Object[0]);
            if (call != null) {
                PluginsController.PluginsEngine pluginsEngine = PluginsController.engines.get(PluginsConstants.PYTHON);
                Objects.requireNonNull(pluginsEngine);
                arrayList = ((PythonPluginsEngine) pluginsEngine).parsePySettingDefinitions(call.asList());
            }
            AndroidUtilities.runOnUIThread(new Runnable() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda1
                @Override // java.lang.Runnable
                public final void run() {
                    PluginSettingsActivity.this.lambda$onClick$7(arrayList, uItem, textSetting);
                }
            });
        } catch (Exception unused) {
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$onClick$7(List list, UItem uItem, TextSetting textSetting) {
        String str;
        if (list.isEmpty()) {
            return;
        }
        PluginSettingsActivity pluginSettingsActivity = new PluginSettingsActivity(this.plugin, uItem.text.toString(), list, textSetting.createSubFragmentCallback);
        StringBuilder sb = new StringBuilder();
        if (this.settingsLinkPrefix == null) {
            str = "";
        } else {
            str = this.settingsLinkPrefix + ":";
        }
        sb.append(str);
        sb.append(uItem.settingItem.linkAlias);
        presentFragment(pluginSettingsActivity.setSettingsLinkPrefix(sb.toString()));
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$onClick$9(String str, boolean z, UItem uItem) {
        PluginsController.getInstance().setPluginSetting(this.plugin.getId(), str, Boolean.valueOf(z));
        SettingItem settingItem = uItem.settingItem;
        if (settingItem instanceof SwitchSetting) {
            triggerOnChange(((SwitchSetting) settingItem).onChangeCallback, str, Boolean.valueOf(z));
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$onClick$10(String str, boolean z, UItem uItem) {
        PluginsController.getInstance().setPluginSetting(this.plugin.getId(), str, Boolean.valueOf(z));
        SettingItem settingItem = uItem.settingItem;
        if (settingItem instanceof SwitchSetting) {
            triggerOnChange(((SwitchSetting) settingItem).onChangeCallback, str, Boolean.valueOf(z));
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public boolean onLongClick(final UItem uItem, View view, int i, float f, float f2) {
        if (uItem != null && this.plugin != null) {
            String str = uItem.settingItem.linkAlias;
            if (str != null && !TextUtils.isEmpty(str)) {
                view.performHapticFeedback(VibratorUtils.getType(3), 1);
                ItemOptions.makeOptions(this, view).add(R.drawable.msg_copy, LocaleController.getString(R.string.CopyLink), new Runnable() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda3
                    @Override // java.lang.Runnable
                    public final void run() {
                        PluginSettingsActivity.this.lambda$onLongClick$11(uItem);
                    }
                }).show();
                return true;
            }
            PyObject pyObject = uItem.settingItem.onLongClickCallback;
            if (pyObject != null) {
                try {
                    pyObject.call(view);
                } catch (Exception unused) {
                }
                return true;
            }
        }
        return false;
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$onLongClick$11(UItem uItem) {
        if (AndroidUtilities.addToClipboard(uItem.settingItem.getLink(this.plugin.getId(), this.settingsLinkPrefix))) {
            BulletinFactory.of(this).createCopyBulletin(LocaleController.getString(R.string.LinkCopied)).show();
        }
    }

    private void showStringInputDialog(UItem uItem, final View view, final String str) {
        if (getParentActivity() != null) {
            SettingItem settingItem = uItem.settingItem;
            if (settingItem instanceof InputSetting) {
                final InputSetting inputSetting = (InputSetting) settingItem;
                final AlertDialog[] alertDialogArr = new AlertDialog[1];
                AlertDialog.Builder builder = new AlertDialog.Builder(getContext(), getResourceProvider());
                builder.setTitle(uItem.text);
                LinearLayout linearLayout = new LinearLayout(getContext());
                linearLayout.setOrientation(1);
                if (inputSetting.subtext != null) {
                    TextView textView = new TextView(getContext());
                    textView.setTextColor(Theme.getColor(Theme.key_dialogTextBlack, getResourceProvider()));
                    textView.setTextSize(1, 16.0f);
                    textView.setText(inputSetting.subtext);
                    linearLayout.addView(textView, LayoutHelper.createLinear(-1, -2, 24.0f, 5.0f, 24.0f, 12.0f));
                }
                final EditTextBoldCursor editTextBoldCursor = new EditTextBoldCursor(getContext());
                editTextBoldCursor.lineYFix = true;
                final Runnable runnable = new Runnable() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda9
                    @Override // java.lang.Runnable
                    public final void run() {
                        PluginSettingsActivity.this.lambda$showStringInputDialog$13(editTextBoldCursor, alertDialogArr, view, str, inputSetting);
                    }
                };
                editTextBoldCursor.setTextSize(1, 18.0f);
                editTextBoldCursor.setText(PluginsController.getInstance().getPluginSettingString(this.plugin.getId(), str, inputSetting.defaultValue));
                editTextBoldCursor.setTextColor(Theme.getColor(Theme.key_dialogTextBlack, getResourceProvider()));
                editTextBoldCursor.setHintColor(Theme.getColor(Theme.key_groupcreate_hintText, getResourceProvider()));
                editTextBoldCursor.setHintText(LocaleController.getString(R.string.EnterValue));
                editTextBoldCursor.setFocusable(true);
                editTextBoldCursor.setInputType(147457);
                int i = Theme.key_windowBackgroundWhiteInputFieldActivated;
                editTextBoldCursor.setCursorColor(Theme.getColor(i, getResourceProvider()));
                editTextBoldCursor.setLineColors(Theme.getColor(Theme.key_windowBackgroundWhiteInputField, getResourceProvider()), Theme.getColor(i, getResourceProvider()), Theme.getColor(Theme.key_text_RedRegular, getResourceProvider()));
                editTextBoldCursor.setBackgroundDrawable(null);
                editTextBoldCursor.setPadding(0, AndroidUtilities.dp(6.0f), 0, AndroidUtilities.dp(6.0f));
                linearLayout.addView(editTextBoldCursor, LayoutHelper.createLinear(-1, -2, 24.0f, 0.0f, 24.0f, 10.0f));
                builder.makeCustomMaxHeight();
                builder.setView(linearLayout);
                builder.setWidth(AndroidUtilities.dp(292.0f));
                builder.setPositiveButton(LocaleController.getString(R.string.Done), new AlertDialog.OnButtonClickListener() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda10
                    @Override // org.telegram.ui.ActionBar.AlertDialog.OnButtonClickListener
                    public final void onClick(AlertDialog alertDialog, int i2) {
                        runnable.run();
                    }
                });
                builder.setNegativeButton(LocaleController.getString(R.string.Cancel), new AlertDialog.OnButtonClickListener() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda11
                    @Override // org.telegram.ui.ActionBar.AlertDialog.OnButtonClickListener
                    public final void onClick(AlertDialog alertDialog, int i2) {
                        alertDialog.dismiss();
                    }
                });
                AlertDialog create = builder.create();
                alertDialogArr[0] = create;
                create.setOnDismissListener(new DialogInterface.OnDismissListener() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda12
                    @Override // android.content.DialogInterface.OnDismissListener
                    public final void onDismiss(DialogInterface dialogInterface) {
                        AndroidUtilities.hideKeyboard(EditTextBoldCursor.this);
                    }
                });
                alertDialogArr[0].setOnShowListener(new DialogInterface.OnShowListener() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda13
                    @Override // android.content.DialogInterface.OnShowListener
                    public final void onShow(DialogInterface dialogInterface) {
                        PluginSettingsActivity.$r8$lambda$M8i9Tfi03snw3u97WfwnIT6rmn8(EditTextBoldCursor.this, dialogInterface);
                    }
                });
                alertDialogArr[0].setDismissDialogByButtons(false);
                showDialog(alertDialogArr[0]);
            }
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$showStringInputDialog$13(EditTextBoldCursor editTextBoldCursor, AlertDialog[] alertDialogArr, View view, final String str, final InputSetting inputSetting) {
        final String obj = editTextBoldCursor.getText().toString();
        AlertDialog alertDialog = alertDialogArr[0];
        if (alertDialog != null) {
            alertDialog.dismiss();
        }
        ((TextCell) view).setValue(obj, true);
        PluginsController.runOnPluginsQueue(new Runnable() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda2
            @Override // java.lang.Runnable
            public final void run() {
                PluginSettingsActivity.this.lambda$showStringInputDialog$12(str, obj, inputSetting);
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$showStringInputDialog$12(String str, String str2, InputSetting inputSetting) {
        PluginsController.getInstance().setPluginSetting(this.plugin.getId(), str, str2);
        triggerOnChange(inputSetting.onChangeCallback, str, str2);
    }

    public static /* synthetic */ void $r8$lambda$M8i9Tfi03snw3u97WfwnIT6rmn8(EditTextBoldCursor editTextBoldCursor, DialogInterface dialogInterface) {
        editTextBoldCursor.requestFocus();
        editTextBoldCursor.setSelection(editTextBoldCursor.length());
        AndroidUtilities.showKeyboard(editTextBoldCursor);
    }

    private void showSelectorDialog(UItem uItem, final View view, final String str) {
        if (getParentActivity() != null) {
            SettingItem settingItem = uItem.settingItem;
            if (settingItem instanceof SelectorSetting) {
                final SelectorSetting selectorSetting = (SelectorSetting) settingItem;
                final AtomicReference atomicReference = new AtomicReference();
                LinearLayout linearLayout = new LinearLayout(getContext());
                linearLayout.setOrientation(1);
                final String[] strArr = selectorSetting.items;
                final int i = 0;
                while (i < strArr.length) {
                    RadioColorCell radioColorCell = new RadioColorCell(getParentActivity());
                    radioColorCell.setPadding(AndroidUtilities.dp(4.0f), 0, AndroidUtilities.dp(4.0f), 0);
                    radioColorCell.setCheckColor(Theme.getColor(Theme.key_radioBackground), Theme.getColor(Theme.key_dialogRadioBackgroundChecked));
                    radioColorCell.setTextAndValue(strArr[i], PluginsController.getInstance().getPluginSettingInt(this.plugin.getId(), str, selectorSetting.defaultValue) == i);
                    radioColorCell.setBackground(Theme.createSelectorDrawable(Theme.getColor(Theme.key_listSelector), 2));
                    linearLayout.addView(radioColorCell);
                    radioColorCell.setOnClickListener(new View.OnClickListener() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda19
                        @Override // android.view.View.OnClickListener
                        public final void onClick(View view2) {
                            PluginSettingsActivity.this.lambda$showSelectorDialog$19(atomicReference, view, strArr, i, str, selectorSetting, view2);
                        }
                    });
                    i++;
                }
                AlertDialog create = new AlertDialog.Builder(getParentActivity()).setTitle(uItem.text).setView(linearLayout).setNegativeButton(LocaleController.getString(R.string.Cancel), null).create();
                atomicReference.set(create);
                showDialog(create);
            }
        }
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$showSelectorDialog$19(AtomicReference atomicReference, View view, String[] strArr, final int i, final String str, final SelectorSetting selectorSetting, View view2) {
        if (atomicReference.get() != null) {
            ((Dialog) atomicReference.get()).dismiss();
        }
        ((TextCell) view).setValue(strArr[i], true);
        PluginsController.runOnPluginsQueue(new Runnable() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda8
            @Override // java.lang.Runnable
            public final void run() {
                PluginSettingsActivity.this.lambda$showSelectorDialog$18(str, i, selectorSetting);
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$showSelectorDialog$18(String str, int i, SelectorSetting selectorSetting) {
        PluginsController.getInstance().setPluginSetting(this.plugin.getId(), str, Integer.valueOf(i));
        triggerOnChange(selectorSetting.onChangeCallback, str, Integer.valueOf(i));
    }

    private int getStableId(SettingItem settingItem) {
        return settingItem instanceof SwitchSetting ? Objects.hash(PluginsConstants.Settings.TYPE_SWITCH, ((SwitchSetting) settingItem).key) : settingItem instanceof InputSetting ? Objects.hash(PluginsConstants.Settings.TYPE_INPUT, ((InputSetting) settingItem).key) : settingItem instanceof EditTextSetting ? Objects.hash("edit", ((EditTextSetting) settingItem).key) : settingItem instanceof SelectorSetting ? Objects.hash(PluginsConstants.Settings.TYPE_SELECTOR, ((SelectorSetting) settingItem).key) : settingItem instanceof HeaderSetting ? Objects.hash(PluginsConstants.Settings.TYPE_HEADER, ((HeaderSetting) settingItem).text) : settingItem instanceof DividerSetting ? Objects.hash(PluginsConstants.Settings.TYPE_DIVIDER, ((DividerSetting) settingItem).text) : settingItem instanceof TextSetting ? Objects.hash("text", ((TextSetting) settingItem).text) : settingItem.hashCode();
    }

    private void triggerOnChange(final PyObject pyObject, final String str, final Object obj) {
        PluginsController.runOnPluginsQueue(new Runnable() { // from class: com.exteragram.messenger.plugins.ui.PluginSettingsActivity$$ExternalSyntheticLambda5
            @Override // java.lang.Runnable
            public final void run() {
                PluginSettingsActivity.this.lambda$triggerOnChange$20(pyObject, obj, str);
            }
        });
    }

    /* JADX INFO: Access modifiers changed from: private */
    public /* synthetic */ void lambda$triggerOnChange$20(PyObject pyObject, Object obj, String str) {
        if (pyObject != null) {
            try {
                pyObject.call(obj);
            } catch (Exception e) {
                FileLog.e("Error executing on_change callback for " + this.plugin.getId() + "/" + str, e);
            }
        }
    }
}
