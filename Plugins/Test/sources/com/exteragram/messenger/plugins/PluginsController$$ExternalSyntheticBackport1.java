package com.exteragram.messenger.plugins;

import j$.util.DesugarCollections;
import j$.util.Objects;
import java.util.HashMap;
import java.util.Map;

/* loaded from: classes.dex */
public abstract /* synthetic */ class PluginsController$$ExternalSyntheticBackport1 {
    public static /* synthetic */ Map m(Map.Entry[] entryArr) {
        HashMap hashMap = new HashMap(entryArr.length);
        for (Map.Entry entry : entryArr) {
            Object key = entry.getKey();
            Objects.requireNonNull(key);
            Object value = entry.getValue();
            Objects.requireNonNull(value);
            if (hashMap.put(key, value) != null) {
                throw new IllegalArgumentException("duplicate key: " + key);
            }
        }
        return DesugarCollections.unmodifiableMap(hashMap);
    }
}
