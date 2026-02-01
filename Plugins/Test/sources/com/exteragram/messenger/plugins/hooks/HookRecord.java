package com.exteragram.messenger.plugins.hooks;

/* loaded from: classes.dex */
public interface HookRecord {
    void cleanup();

    boolean matches(Object obj);
}
