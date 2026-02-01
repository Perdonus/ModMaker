package com.exteragram.messenger.plugins.hooks;

import android.content.Context;
import android.text.TextUtils;
import com.chaquo.python.PyObject;
import com.exteragram.messenger.plugins.PluginsConstants;
import com.exteragram.messenger.plugins.utils.PyObjectUtils;
import j$.util.Objects;
import j$.util.concurrent.ConcurrentHashMap;
import j$.util.concurrent.ConcurrentMap$EL;
import java.io.Serializable;
import java.util.Map;
import java.util.UUID;
import org.mvel2.MVEL;
import org.telegram.messenger.ApplicationLoader;

/* loaded from: classes.dex */
public class MenuItemRecord {
    private static final ConcurrentHashMap<String, Serializable> mvelExpressionCache = new ConcurrentHashMap<>();
    public final String conditionString;
    public final String iconName;
    public final int iconResId;
    public final String itemId;
    public final String menuType;
    public final PyObject onClickCallback;
    public final String pluginId;
    public final int priority;
    public final String subtext;
    public final String text;

    public MenuItemRecord(String str, PyObject pyObject) {
        this.pluginId = str;
        this.menuType = PyObjectUtils.getString(pyObject, PluginsConstants.MenuItemProperties.MENU_TYPE, null, true);
        this.text = PyObjectUtils.getString(pyObject, "text", null, true);
        int i = 0;
        this.onClickCallback = pyObject.callAttr("get", "on_click");
        String string = PyObjectUtils.getString(pyObject, PluginsConstants.MenuItemProperties.ITEM_ID, null, true);
        this.itemId = TextUtils.isEmpty(string) ? UUID.randomUUID().toString() : string;
        String string2 = PyObjectUtils.getString(pyObject, "icon", null, true);
        this.iconName = string2;
        this.subtext = PyObjectUtils.getString(pyObject, "subtext", null, true);
        this.conditionString = PyObjectUtils.getString(pyObject, "condition", null, true);
        this.priority = PyObjectUtils.getInt(pyObject, PluginsConstants.MenuItemProperties.PRIORITY, 0, true);
        if (!TextUtils.isEmpty(string2)) {
            try {
                Context context = ApplicationLoader.applicationContext;
                i = context.getResources().getIdentifier(string2, "drawable", context.getPackageName());
            } catch (Exception unused) {
            }
        }
        this.iconResId = i;
        if (TextUtils.isEmpty(this.menuType) || TextUtils.isEmpty(this.text) || this.onClickCallback == null) {
            throw new IllegalArgumentException("MenuItemRecord missing essential fields: menuType, text, or onClickCallback.");
        }
    }

    public boolean equals(Object obj) {
        if (this == obj) {
            return true;
        }
        if (obj != null && getClass() == obj.getClass()) {
            MenuItemRecord menuItemRecord = (MenuItemRecord) obj;
            if (this.itemId.equals(menuItemRecord.itemId) && this.pluginId.equals(menuItemRecord.pluginId)) {
                return true;
            }
        }
        return false;
    }

    public int hashCode() {
        return Objects.hash(this.itemId, this.pluginId);
    }

    public boolean checkCondition(Map<String, Object> map) {
        if (TextUtils.isEmpty(this.conditionString) || map == null) {
            return true;
        }
        try {
            return ((Boolean) Objects.requireNonNullElse((Boolean) MVEL.executeExpression(ConcurrentMap$EL.computeIfAbsent(mvelExpressionCache, this.conditionString, new HookFilter$$ExternalSyntheticLambda0()), (Map) map, Boolean.class), Boolean.FALSE)).booleanValue();
        } catch (Exception unused) {
            return false;
        }
    }
}
