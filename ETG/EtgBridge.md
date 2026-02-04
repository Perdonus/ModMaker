ETG Bridge (Heroku + Extera)

Интеграция ETG Bridge в Heroku‑модули
Перед началом

ВАЖНО: Любой модуль должен проверять наличие EtgBridge и корректно обрабатывать отсутствие устройства.
Всегда начинай так:

    bridge = self.lookup("EtgBridge")
    if not bridge:
        return await utils.answer(message, "ETG Bridge не найден")

Базовая схема

    device_id = "last"
    action_id = bridge.api.toast(device_id, "Привет")
    res = await bridge.api.wait_result(device_id, action_id, timeout=10)
    if not res or not res.get("ok"):
        return await utils.answer(message, "Нет ответа от ETG")

Основные понятия

• device_id — идентификатор устройства (обычно "last" или конкретный id).
• action_id — id команды, которую плагин получил и выполнит.
• result — ответ плагина: ok/error + data.
• timeout — время ожидания ответа в секундах.

Выбор устройства

• "last" — последнее активное устройство.
• Явный device_id — получай через .etg status.

Протокол сервера

HTTP
POST /sync

Запрос:

    {
      "device_id": "abc123",
      "token": "...",
      "info": { ... },
      "logs": [ ... ],
      "results": [ ... ],
      "ts": 1712345678901
    }

Ответ:

    {
      "ok": true,
      "actions": [
        {"id": "uuid", "action": "toast", "payload": {"text": "hi"}, "ttl": 300}
      ]
    }

WebSocket
/ws — тот же формат, но по WS в обе стороны.

API EtgBridgeAPI

UI / Диалоги

• toast(device_id, text)
• dialog(device_id, title, text, buttons=None, callback_id=None)
• menu(device_id, title, message, items, callback_id=None)
• prompt(device_id, title, text="", hint="", multiline=True, max_len=0, callback_id=None)
• sheet(device_id, dsl, actions=None, callback_id=None)
• sheet_update(device_id, sheet_id, dsl, actions=None, callback_id=None)
• sheet_close(device_id, sheet_id)
• open_editor(device_id, title, content, filename="", readonly=False, callback_id=None)
• ripple(device_id, intensity=1.0, vibrate=True)
• select_chat(device_id, title="Выберите чат", callback_id=None)

Система

• open_url(device_id, url)
• clipboard_set(device_id, text)
• clipboard_get(device_id)
• tts(device_id, text)
• notify(device_id, title, text)
• notify_dialog(device_id, sender_name, message, avatar_url="")
• share_text(device_id, text, title="Share")
• share_file(device_id, path, title="Share")

Медиа / Рендер

• send_png(device_id, url, caption="")
• render_html(device_id, html, width=1024, height=768, bg_color=(26,30,36), file_prefix="etg_", send=False, caption="")

Данные

• device_info(device_id)
• recent_messages(device_id, dialog_id, limit=20)
• data_write(device_id, filename, data)
• data_read(device_id, filename)
• data_list(device_id)
• data_delete(device_id)

KV‑хранилище

• kv_set(device_id, key, value, table="etg_bridge")
• kv_get(device_id, key, table="etg_bridge")
• kv_get_int(device_id, key, default=0, table="etg_bridge")
• kv_delete_prefix(device_id, prefix, table="etg_bridge")

Управление / Исполнение

• pip_install(device_id, packages)
• exec(device_id, code)

Результаты

• get_result(device_id, action_id, pop=False)
• wait_result(device_id, action_id, timeout=30, pop=True)

Обработка результата

    res = await bridge.api.wait_result(device_id, action_id, timeout=30)
    if not res:
        return await utils.answer(message, "Таймаут")
    if not res.get("ok"):
        err = res.get("error") or "Ошибка"
        return await utils.answer(message, f"ETG error: {err}")
    data = res.get("data") or {}

Sheet (UI DSL)

    <sheet title="ETG" subtext="hello" close_text="Закрыть">
      <tag text="model: gpt" color="#7C4DFF" size="12" />
      <content size="14" align="left">Текст</content>
      <actions>
        <button id="ok" text="OK" />
        <button id="cancel" text="Cancel" />
      </actions>
    </sheet>

    action_id = bridge.api.sheet("last", dsl, actions=["ok", "cancel"], callback_id="sheet1")
    res = await bridge.api.wait_result("last", action_id)

Типовые паттерны

Диалог

    action_id = bridge.api.dialog("last", "Заголовок", "Текст", buttons=["OK", "Cancel"], callback_id="d1")
    res = await bridge.api.wait_result("last", action_id, timeout=30)

Текстовый ввод

    action_id = bridge.api.prompt("last", title="Введите текст", hint="Пример", callback_id="p1")
    res = await bridge.api.wait_result("last", action_id)
    text = (res or {}).get("data", {}).get("text", "")

Открыть редактор

    action_id = bridge.api.open_editor("last", title="Код", content="print('hi')", filename="test.py")
    res = await bridge.api.wait_result("last", action_id)

Ошибки и таймауты

• Всегда проверяй res и res["ok"].
• Используй разумный timeout (10–40 сек).
• Для нестабильных действий делай повтор или показывай пользователю понятную ошибку.

Минимальный пример команды

    @loader.command()
    async def etgtest(self, message: Message):
        bridge = self.lookup("EtgBridge")
        if not bridge:
            return await utils.answer(message, "ETG Bridge не найден")

        action_id = bridge.api.toast("last", "Привет!")
        res = await bridge.api.wait_result("last", action_id, timeout=10)
        if not res or not res.get("ok"):
            return await utils.answer(message, "Нет ответа от ETG")

        await utils.answer(message, "OK")
