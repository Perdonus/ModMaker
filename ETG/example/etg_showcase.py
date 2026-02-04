import asyncio
import json
import time
import typing

from herokutl.tl.types import Message

from .. import loader, utils
from ..inline.types import InlineCall


@loader.tds
class EtgShowcaseMod(loader.Module):
    """ETG API showcase with inline UI."""

    strings = {"name": "EtgShowcase"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "device_id",
                "last",
                "Default device id (use 'last' for last active)",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "timeout",
                30,
                "Wait timeout in seconds",
                validator=loader.validators.Integer(minimum=5, maximum=300),
            ),
            loader.ConfigValue(
                "wait_result",
                True,
                "Wait for action result by default",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "cover_url",
                "",
                "Optional cover image URL for the main screen",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "toast_text",
                "Hello from ETG",
                "Toast text",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "dialog_title",
                "Demo dialog",
                "Dialog title",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "dialog_text",
                "Pick an option",
                "Dialog body text",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "dialog_buttons",
                "OK|Cancel",
                "Dialog buttons separated by |",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "menu_title",
                "Menu demo",
                "Menu title",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "menu_message",
                "Choose an item",
                "Menu message",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "menu_items",
                "One|Two|Three",
                "Menu items separated by |",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "prompt_title",
                "Prompt demo",
                "Prompt title",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "prompt_text",
                "",
                "Prompt prefill text",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "prompt_hint",
                "Type here",
                "Prompt hint",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "prompt_multiline",
                True,
                "Prompt multiline",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "prompt_max_len",
                0,
                "Prompt max length (0 = unlimited)",
                validator=loader.validators.Integer(minimum=0, maximum=2000),
            ),
            loader.ConfigValue(
                "sheet_dsl",
                "<sheet title=\"ETG\" subtext=\"demo\" close_text=\"Close\">"
                "<content size=\"14\" align=\"left\">Hello from ETG</content>"
                "<actions><button id=\"ok\" text=\"OK\" />"
                "<button id=\"cancel\" text=\"Cancel\" /></actions>"
                "</sheet>",
                "Sheet DSL",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "sheet_actions",
                "ok|cancel",
                "Sheet actions separated by |",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "sheet_id",
                "demo_sheet",
                "Sheet id for open/update/close",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "editor_title",
                "Editor demo",
                "Editor title",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "editor_filename",
                "demo.txt",
                "Editor filename",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "editor_content",
                "Hello from editor",
                "Editor content",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "editor_readonly",
                False,
                "Editor readonly",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "ripple_intensity",
                1.0,
                "Ripple intensity",
                validator=loader.validators.Float(minimum=0.1, maximum=5.0),
            ),
            loader.ConfigValue(
                "ripple_vibrate",
                True,
                "Ripple vibrate",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "select_chat_title",
                "Select chat",
                "Select chat title",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "open_url",
                "https://example.com",
                "Open URL",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "clipboard_text",
                "Clipboard sample",
                "Clipboard text",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "notify_title",
                "ETG notification",
                "Notify title",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "notify_text",
                "Hello from ETG notification",
                "Notify text",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "notify_sender",
                "ETG",
                "Notify dialog sender",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "notify_message",
                "This is a dialog notification",
                "Notify dialog message",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "notify_avatar_url",
                "https://raw.githubusercontent.com/coddrago/assets/refs/heads/main/heroku/unit_alpha.png",
                "Notify dialog avatar URL",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "tts_text",
                "Hello from ETG",
                "TTS text",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "share_text",
                "Share text from ETG",
                "Share text",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "share_title",
                "Share",
                "Share title",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "share_path",
                "/sdcard/Download/demo.txt",
                "Share file path",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "png_url",
                "https://raw.githubusercontent.com/coddrago/assets/refs/heads/main/heroku/unit_alpha.png",
                "PNG URL",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "png_caption",
                "ETG image",
                "PNG caption",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "render_html",
                "<html><body style='background:#111;color:#0f0;"
                "font-family:monospace;padding:24px'>ETG render</body></html>",
                "HTML to render",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "render_width",
                1024,
                "Render width",
                validator=loader.validators.Integer(minimum=128, maximum=4096),
            ),
            loader.ConfigValue(
                "render_height",
                768,
                "Render height",
                validator=loader.validators.Integer(minimum=128, maximum=4096),
            ),
            loader.ConfigValue(
                "render_bg",
                "26,30,36",
                "Render background color (R,G,B)",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "render_send",
                False,
                "Send rendered file to chat",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "render_caption",
                "ETG render",
                "Render caption",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "net_test_url",
                "https://example.com",
                "Net test URL (optional)",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "net_test_timeout",
                5,
                "Net test timeout",
                validator=loader.validators.Integer(minimum=1, maximum=30),
            ),
            loader.ConfigValue(
                "recent_dialog_id",
                0,
                "Dialog ID for recent messages (0 = not set)",
                validator=loader.validators.Integer(minimum=0),
            ),
            loader.ConfigValue(
                "recent_limit",
                20,
                "Recent messages limit",
                validator=loader.validators.Integer(minimum=1, maximum=200),
            ),
            loader.ConfigValue(
                "data_filename",
                "demo.txt",
                "Data filename",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "data_value",
                "Hello data",
                "Data payload",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "kv_table",
                "etg_bridge",
                "KV table",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "kv_key",
                "demo",
                "KV key",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "kv_value",
                "value",
                "KV value",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "kv_default_int",
                0,
                "KV default int",
                validator=loader.validators.Integer(),
            ),
            loader.ConfigValue(
                "pip_packages",
                "requests",
                "pip packages (space or comma separated)",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "exec_code",
                "print('hello from etg')",
                "Exec code",
                validator=loader.validators.String(),
            ),
        )
        self._state = None

    async def client_ready(self):
        self._state = self.pointer("state", {})

    @loader.command(aliases=["etgapi"], ru_doc="Open ETG API showcase UI")
    async def etgshow(self, message: Message):
        bridge = self._get_bridge()
        if not bridge:
            await utils.answer(message, "EtgBridge module not found.")
            return

        state = self._get_state(message.sender_id)
        text = self._render_main_text(state, bridge)
        markup = self._build_main_markup()
        cover = self._get_cover_url()
        form = await self.inline.form(
            text=text,
            message=message,
            reply_markup=markup,
            ttl=10 * 60,
            photo=cover,
        )
        if not form:
            await utils.answer(message, "Inline form is not available.")

    def _get_bridge(self):
        return self.lookup("EtgBridge")

    def _get_state(self, user_id: int) -> dict:
        key = str(user_id)
        if self._state is None:
            self._state = {}
        state = self._state.get(key) if self._state is not None else None
        if not state:
            state = {
                "device_id": self.config["device_id"],
                "timeout": int(self.config["timeout"]),
                "wait_result": bool(self.config["wait_result"]),
                "last_action_id": "",
                "last_action": "",
                "last_result": "",
                "sheet_id": self.config["sheet_id"],
            }
            if self._state is not None:
                self._state[key] = state
        return state

    def _get_cover_url(self) -> typing.Optional[str]:
        url = (self.config["cover_url"] or "").strip()
        if url and utils.check_url(url):
            return url
        return None

    def _render_main_text(self, state: dict, bridge) -> str:
        device_id = state.get("device_id") or self.config["device_id"]
        resolved = bridge.api._resolve(device_id) if bridge else None
        timeout = state.get("timeout", self.config["timeout"])
        wait_flag = state.get("wait_result", True)
        last_action = state.get("last_action") or "none"
        last_action_id = state.get("last_action_id") or "none"
        last_result = state.get("last_result") or "none"
        lines = [
            "<b>ETG API Showcase</b>",
            f"Device: <code>{utils.escape_html(str(device_id))}</code>",
            f"Resolved: <code>{utils.escape_html(str(resolved or 'none'))}</code>",
            f"Timeout: <code>{timeout}s</code>",
            f"Wait result: <code>{'on' if wait_flag else 'off'}</code>",
            f"Last action: <code>{utils.escape_html(last_action)}</code>",
            f"Last action id: <code>{utils.escape_html(last_action_id)}</code>",
            f"Last result: <code>{utils.escape_html(last_result)}</code>",
            "",
            "Use .cfg EtgShowcase to change defaults.",
        ]
        return "\n".join(lines)

    def _build_main_markup(self) -> list:
        items = [
            {"text": "UI", "callback": self._open_category, "args": ("ui",)},
            {"text": "System", "callback": self._open_category, "args": ("system",)},
            {"text": "Media", "callback": self._open_category, "args": ("media",)},
            {"text": "Data", "callback": self._open_category, "args": ("data",)},
            {"text": "KV", "callback": self._open_category, "args": ("kv",)},
            {"text": "Exec", "callback": self._open_category, "args": ("exec",)},
            {"text": "Results", "callback": self._open_category, "args": ("results",)},
            {"text": "Devices", "callback": self._open_devices, "args": ()},
            {"text": "Settings", "callback": self._open_settings, "args": ()},
            {"text": "Refresh", "callback": self._open_main, "args": ()},
            {"text": "Close", "callback": self._close_form, "args": ()},
        ]
        return utils.chunks(items, 2)

    async def _open_main(self, call: InlineCall):
        bridge = self._get_bridge()
        state = self._get_state(call.from_user.id)
        text = self._render_main_text(state, bridge)
        await call.edit(text, reply_markup=self._build_main_markup())

    async def _close_form(self, call: InlineCall):
        await call.delete()

    async def _open_category(self, call: InlineCall, category: str):
        state = self._get_state(call.from_user.id)
        text = self._render_category_text(category, state)
        markup = self._build_category_markup(category)
        await call.edit(text, reply_markup=markup)

    def _render_category_text(self, category: str, state: dict) -> str:
        timeout = state.get("timeout", self.config["timeout"])
        wait_flag = state.get("wait_result", True)
        header = f"<b>{category.upper()} tests</b>"
        info = f"Timeout: <code>{timeout}s</code> | Wait result: <code>{'on' if wait_flag else 'off'}</code>"
        return f"{header}\n{info}\nSelect an action:"

    def _build_category_markup(self, category: str) -> list:
        actions = self._category_actions(category)
        buttons = [
            {"text": label, "callback": self._run_action, "args": (category, key)}
            for key, label in actions
        ]
        rows = utils.chunks(buttons, 2)
        rows.append(
            [
                {"text": "Back", "callback": self._open_main, "args": ()},
                {"text": "Settings", "callback": self._open_settings, "args": ()},
            ]
        )
        return rows

    async def _open_devices(self, call: InlineCall):
        bridge = self._get_bridge()
        state = self._get_state(call.from_user.id)
        if not bridge:
            await call.edit("EtgBridge module not found.", reply_markup=self._build_main_markup())
            return
        devices, last_id, error = self._collect_devices(bridge)
        lines = ["<b>Devices</b>"]
        if error:
            lines.append(f"Error: <code>{utils.escape_html(error)}</code>")
        if not devices:
            lines.append("No devices found.")
        else:
            for dev in devices:
                label = self._device_label(dev)
                marker = " *" if dev.get("id") == last_id else ""
                lines.append(f"- {utils.escape_html(label)}{marker}")
        lines.append("")
        lines.append(f"Current device: <code>{utils.escape_html(state.get('device_id') or 'last')}</code>")
        markup = []
        if devices:
            markup = utils.chunks(
                [
                    {
                        "text": self._device_button_label(dev, last_id),
                        "callback": self._set_device,
                        "args": (str(dev.get("id") or ""),),
                    }
                    for dev in devices
                ],
                2,
            )
        markup.append(
            [
                {"text": "Use last", "callback": self._set_device, "args": ("last",)},
                {"text": "Back", "callback": self._open_main, "args": ()},
            ]
        )
        await call.edit("\n".join(lines), reply_markup=markup)

    async def _set_device(self, call: InlineCall, device_id: str):
        state = self._get_state(call.from_user.id)
        state["device_id"] = device_id or "last"
        await self._open_devices(call)

    async def _open_settings(self, call: InlineCall):
        state = self._get_state(call.from_user.id)
        lines = [
            "<b>Settings</b>",
            f"Device: <code>{utils.escape_html(state.get('device_id') or 'last')}</code>",
            f"Timeout: <code>{state.get('timeout', self.config['timeout'])}s</code>",
            f"Wait result: <code>{'on' if state.get('wait_result', True) else 'off'}</code>",
            "",
            "Use .cfg EtgShowcase for full config.",
        ]
        markup = [
            [
                {"text": "Wait toggle", "callback": self._toggle_wait, "args": ()},
                {"text": "Set device", "callback": self._open_devices, "args": ()},
            ],
            [
                {"text": "Timeout -5", "callback": self._adjust_timeout, "args": (-5,)},
                {"text": "Timeout +5", "callback": self._adjust_timeout, "args": (5,)},
            ],
            [
                {"text": "Timeout -10", "callback": self._adjust_timeout, "args": (-10,)},
                {"text": "Timeout +10", "callback": self._adjust_timeout, "args": (10,)},
            ],
            [
                {"text": "Reset state", "callback": self._reset_state, "args": ()},
                {"text": "Back", "callback": self._open_main, "args": ()},
            ],
        ]
        await call.edit("\n".join(lines), reply_markup=markup)

    async def _toggle_wait(self, call: InlineCall):
        state = self._get_state(call.from_user.id)
        state["wait_result"] = not bool(state.get("wait_result", True))
        await self._open_settings(call)

    async def _adjust_timeout(self, call: InlineCall, delta: int):
        state = self._get_state(call.from_user.id)
        timeout = int(state.get("timeout", self.config["timeout"])) + int(delta)
        timeout = max(5, min(300, timeout))
        state["timeout"] = timeout
        await self._open_settings(call)

    async def _reset_state(self, call: InlineCall):
        state = self._get_state(call.from_user.id)
        state["device_id"] = self.config["device_id"]
        state["timeout"] = int(self.config["timeout"])
        state["wait_result"] = bool(self.config["wait_result"])
        state["last_action_id"] = ""
        state["last_action"] = ""
        state["last_result"] = ""
        state["sheet_id"] = self.config["sheet_id"]
        await self._open_settings(call)

    async def _run_action(self, call: InlineCall, category: str, action_key: str):
        bridge = self._get_bridge()
        if not bridge:
            await call.edit("EtgBridge module not found.", reply_markup=self._build_main_markup())
            return
        state = self._get_state(call.from_user.id)
        await call.edit("Sending action...", reply_markup=self._build_category_markup(category))
        action_id, result, error = await self._dispatch_action(bridge, state, action_key)
        text = self._render_action_result(action_key, state, action_id, result, error)
        await call.edit(text, reply_markup=self._build_category_markup(category))

    async def _dispatch_action(
        self, bridge, state: dict, action_key: str
    ) -> typing.Tuple[typing.Optional[str], typing.Optional[dict], str]:
        device_id = state.get("device_id") or self.config["device_id"]
        wait_flag = bool(state.get("wait_result", True))
        if action_key == "get_last":
            return self._get_last_result(bridge, device_id, state)
        if action_key == "wait_last":
            return await self._wait_last_result(bridge, device_id, state)
        if action_key == "clear_last":
            state["last_action_id"] = ""
            state["last_action"] = ""
            state["last_result"] = ""
            return None, {"ok": True, "action": "clear_last", "data": "cleared"}, ""

        send_call, err = self._build_action_callable(
            action_key, bridge, device_id, state
        )
        if send_call is None:
            return None, None, err or "Unsupported action"
        action_id = send_call()
        if not action_id:
            return None, None, "No device online"
        state["last_action_id"] = action_id
        state["last_action"] = action_key
        if not wait_flag:
            state["last_result"] = "sent"
            return action_id, {"ok": True, "action": action_key, "data": "sent"}, ""
        result = await bridge.api.wait_result(
            device_id, action_id, timeout=int(state.get("timeout", 30))
        )
        if result is None:
            state["last_result"] = "timeout"
            return action_id, None, "Timeout or no result"
        state["last_result"] = self._short_json(result)
        return action_id, result, ""

    def _get_last_result(self, bridge, device_id: str, state: dict):
        action_id = state.get("last_action_id")
        if not action_id:
            return None, None, "No last action id"
        result = bridge.api.get_result(device_id, action_id, pop=False)
        if result is None:
            return action_id, None, "No result yet"
        state["last_result"] = self._short_json(result)
        return action_id, result, ""

    async def _wait_last_result(self, bridge, device_id: str, state: dict):
        action_id = state.get("last_action_id")
        if not action_id:
            return None, None, "No last action id"
        result = await bridge.api.wait_result(
            device_id, action_id, timeout=int(state.get("timeout", 30))
        )
        if result is None:
            return action_id, None, "Timeout or no result"
        state["last_result"] = self._short_json(result)
        return action_id, result, ""

    def _build_action_callable(self, action_key: str, bridge, device_id: str, state: dict):
        error = ""
        if action_key == "toast":
            return lambda: bridge.api.toast(device_id, self.config["toast_text"]), error
        if action_key == "dialog":
            return lambda: bridge.api.dialog(
                device_id,
                self.config["dialog_title"],
                self.config["dialog_text"],
                buttons=self._split_list(self.config["dialog_buttons"]),
                callback_id="dialog_demo",
            ), error
        if action_key == "menu":
            return lambda: bridge.api.menu(
                device_id,
                self.config["menu_title"],
                self.config["menu_message"],
                items=self._split_list(self.config["menu_items"]),
                callback_id="menu_demo",
            ), error
        if action_key == "prompt":
            return lambda: bridge.api.prompt(
                device_id,
                self.config["prompt_title"],
                text=self.config["prompt_text"],
                hint=self.config["prompt_hint"],
                multiline=bool(self.config["prompt_multiline"]),
                max_len=int(self.config["prompt_max_len"]),
                callback_id="prompt_demo",
            ), error
        if action_key == "sheet":
            return lambda: bridge.api.sheet(
                device_id,
                self.config["sheet_dsl"],
                actions=self._split_list(self.config["sheet_actions"]),
                callback_id="sheet_demo",
            ), error
        if action_key == "sheet_open":
            sheet_id = self._sheet_id(state)
            return lambda: bridge.api.sheet_open(
                device_id,
                self.config["sheet_dsl"],
                actions=self._split_list(self.config["sheet_actions"]),
                callback_id="sheet_open_demo",
                sheet_id=sheet_id,
            ), error
        if action_key == "sheet_update":
            sheet_id = self._sheet_id(state)
            return lambda: bridge.api.sheet_update(
                device_id,
                sheet_id,
                self.config["sheet_dsl"],
                actions=self._split_list(self.config["sheet_actions"]),
                callback_id="sheet_update_demo",
            ), error
        if action_key == "sheet_close":
            sheet_id = self._sheet_id(state)
            return lambda: bridge.api.sheet_close(device_id, sheet_id), error
        if action_key == "open_editor":
            return lambda: bridge.api.open_editor(
                device_id,
                self.config["editor_title"],
                self.config["editor_content"],
                filename=self.config["editor_filename"],
                readonly=bool(self.config["editor_readonly"]),
                callback_id="editor_demo",
            ), error
        if action_key == "ripple":
            return lambda: bridge.api.ripple(
                device_id,
                intensity=float(self.config["ripple_intensity"]),
                vibrate=bool(self.config["ripple_vibrate"]),
            ), error
        if action_key == "select_chat":
            return lambda: bridge.api.select_chat(
                device_id,
                title=self.config["select_chat_title"],
                callback_id="select_chat_demo",
            ), error
        if action_key == "open_url":
            return lambda: bridge.api.open_url(device_id, self.config["open_url"]), error
        if action_key == "clipboard_set":
            return (
                lambda: bridge.api.clipboard_set(device_id, self.config["clipboard_text"]),
                error,
            )
        if action_key == "clipboard_get":
            return lambda: bridge.api.clipboard_get(device_id), error
        if action_key == "notify":
            return lambda: bridge.api.notify(
                device_id, self.config["notify_title"], self.config["notify_text"]
            ), error
        if action_key == "notify_dialog":
            return lambda: bridge.api.notify_dialog(
                device_id,
                self.config["notify_sender"],
                self.config["notify_message"],
                avatar_url=self.config["notify_avatar_url"],
            ), error
        if action_key == "tts":
            return lambda: bridge.api.tts(device_id, self.config["tts_text"]), error
        if action_key == "share_text":
            return lambda: bridge.api.share_text(
                device_id,
                self.config["share_text"],
                title=self.config["share_title"],
            ), error
        if action_key == "share_file":
            return lambda: bridge.api.share_file(
                device_id,
                self.config["share_path"],
                title=self.config["share_title"],
            ), error
        if action_key == "send_png":
            return lambda: bridge.api.send_png(
                device_id,
                self.config["png_url"],
                caption=self.config["png_caption"],
            ), error
        if action_key == "render_html":
            bg = self._parse_rgb(self.config["render_bg"])
            return lambda: bridge.api.render_html(
                device_id,
                self.config["render_html"],
                width=int(self.config["render_width"]),
                height=int(self.config["render_height"]),
                bg_color=bg,
                file_prefix="etg_",
                send=bool(self.config["render_send"]),
                caption=self.config["render_caption"],
            ), error
        if action_key == "net_test":
            url = (self.config["net_test_url"] or "").strip()
            return lambda: bridge.api.net_test(
                device_id,
                url=url,
                timeout=int(self.config["net_test_timeout"]),
            ), error
        if action_key == "device_info":
            return lambda: bridge.api.device_info(device_id), error
        if action_key == "recent_messages":
            dialog_id = int(self.config["recent_dialog_id"])
            if dialog_id <= 0:
                return None, "recent_dialog_id is not set"
            return lambda: bridge.api.recent_messages(
                device_id, dialog_id, limit=int(self.config["recent_limit"])
            ), error
        if action_key == "data_write":
            payload = self._maybe_json(self.config["data_value"])
            return lambda: bridge.api.data_write(
                device_id, self.config["data_filename"], payload
            ), error
        if action_key == "data_read":
            return lambda: bridge.api.data_read(device_id, self.config["data_filename"]), error
        if action_key == "data_list":
            return lambda: bridge.api.data_list(device_id), error
        if action_key == "data_delete":
            return lambda: bridge.api.data_delete(device_id), error
        if action_key == "kv_set":
            payload = self._maybe_json(self.config["kv_value"])
            return lambda: bridge.api.kv_set(
                device_id,
                self.config["kv_key"],
                payload,
                table=self.config["kv_table"],
            ), error
        if action_key == "kv_get":
            return lambda: bridge.api.kv_get(
                device_id,
                self.config["kv_key"],
                table=self.config["kv_table"],
            ), error
        if action_key == "kv_get_int":
            return lambda: bridge.api.kv_get_int(
                device_id,
                self.config["kv_key"],
                default=int(self.config["kv_default_int"]),
                table=self.config["kv_table"],
            ), error
        if action_key == "kv_delete_prefix":
            return lambda: bridge.api.kv_delete_prefix(
                device_id,
                self.config["kv_key"],
                table=self.config["kv_table"],
            ), error
        if action_key == "pip_install":
            packages = self._split_packages(self.config["pip_packages"])
            if not packages:
                return None, "pip_packages is empty"
            return lambda: bridge.api.pip_install(device_id, packages), error
        if action_key == "exec":
            return lambda: bridge.api.exec(device_id, self.config["exec_code"]), error
        return None, "Unsupported action"

    def _render_action_result(
        self,
        action_key: str,
        state: dict,
        action_id: typing.Optional[str],
        result: typing.Optional[dict],
        error: str,
    ) -> str:
        lines = [f"<b>Action result</b>", f"Action: <code>{utils.escape_html(action_key)}</code>"]
        if action_id:
            lines.append(f"Action id: <code>{utils.escape_html(action_id)}</code>")
        if error:
            lines.append(f"Error: <code>{utils.escape_html(error)}</code>")
        if result is None:
            lines.append("Result: <code>none</code>")
            return "\n".join(lines)
        ok = result.get("ok")
        action = result.get("action")
        data = result.get("data")
        err = result.get("error")
        lines.append(f"OK: <code>{utils.escape_html(str(ok))}</code>")
        if action:
            lines.append(f"Result action: <code>{utils.escape_html(str(action))}</code>")
        if err:
            lines.append(f"Result error: <code>{utils.escape_html(str(err))}</code>")
        if data is not None:
            lines.append(f"Result data: <code>{utils.escape_html(self._short_json(data))}</code>")
        return "\n".join(lines)

    def _category_actions(self, category: str) -> typing.List[typing.Tuple[str, str]]:
        if category == "ui":
            return [
                ("toast", "Toast"),
                ("dialog", "Dialog"),
                ("menu", "Menu"),
                ("prompt", "Prompt"),
                ("sheet", "Sheet"),
                ("sheet_open", "Sheet open"),
                ("sheet_update", "Sheet update"),
                ("sheet_close", "Sheet close"),
                ("open_editor", "Open editor"),
                ("ripple", "Ripple"),
                ("select_chat", "Select chat"),
            ]
        if category == "system":
            return [
                ("open_url", "Open URL"),
                ("clipboard_set", "Clipboard set"),
                ("clipboard_get", "Clipboard get"),
                ("notify", "Notify"),
                ("notify_dialog", "Notify dialog"),
                ("tts", "TTS"),
                ("share_text", "Share text"),
                ("share_file", "Share file"),
            ]
        if category == "media":
            return [
                ("send_png", "Send PNG"),
                ("render_html", "Render HTML"),
            ]
        if category == "data":
            return [
                ("device_info", "Device info"),
                ("recent_messages", "Recent messages"),
                ("data_write", "Data write"),
                ("data_read", "Data read"),
                ("data_list", "Data list"),
                ("data_delete", "Data delete"),
            ]
        if category == "kv":
            return [
                ("kv_set", "KV set"),
                ("kv_get", "KV get"),
                ("kv_get_int", "KV get int"),
                ("kv_delete_prefix", "KV delete prefix"),
            ]
        if category == "exec":
            return [
                ("pip_install", "Pip install"),
                ("exec", "Exec"),
                ("net_test", "Net test"),
            ]
        if category == "results":
            return [
                ("get_last", "Get last result"),
                ("wait_last", "Wait last result"),
                ("clear_last", "Clear last"),
            ]
        return []

    def _collect_devices(self, bridge):
        devices = []
        last_id = ""
        error = ""
        if getattr(bridge, "_use_external", None) and bridge._use_external():
            data, err = bridge._fetch_status()
            if err:
                error = err
            if data and data.get("ok"):
                last_id = str(data.get("last_device_id") or "").strip()
                devices = data.get("devices") or []
        if not devices and hasattr(bridge, "_devices"):
            try:
                with bridge._lock:
                    devices = list(bridge._devices.values())
            except Exception:
                devices = list(bridge._devices.values())
        return devices, last_id, error

    @staticmethod
    def _format_age(seconds: float) -> str:
        seconds = int(max(0, seconds))
        if seconds < 60:
            return f"{seconds}s"
        minutes, sec = divmod(seconds, 60)
        if minutes < 60:
            return f"{minutes}m {sec}s"
        hours, minutes = divmod(minutes, 60)
        if hours < 24:
            return f"{hours}h {minutes}m"
        days, hours = divmod(hours, 24)
        return f"{days}d {hours}h"

    def _device_label(self, device: dict) -> str:
        info = device.get("info") or {}
        name = info.get("device_name") or info.get("name") or device.get("id") or "unknown"
        last_seen = device.get("last_seen") or 0
        age = self._format_age(time.time() - float(last_seen)) if last_seen else "never"
        return f"{name} ({device.get('id')}) | seen {age}"

    @staticmethod
    def _device_button_label(device: dict, last_id: str) -> str:
        info = device.get("info") or {}
        name = info.get("device_name") or info.get("name") or device.get("id") or "unknown"
        label = f"{name}"
        if last_id and str(device.get("id")) == last_id:
            label = f"{label} (last)"
        return label

    def _sheet_id(self, state: dict) -> str:
        return state.get("sheet_id") or self.config["sheet_id"]

    @staticmethod
    def _split_list(value: str) -> typing.List[str]:
        items = [item.strip() for item in (value or "").split("|")]
        return [item for item in items if item]

    @staticmethod
    def _split_packages(value: str) -> typing.Union[str, list, None]:
        text = (value or "").strip()
        if not text:
            return None
        parts = [item for item in text.replace(",", " ").split() if item]
        if len(parts) == 1:
            return parts[0]
        return parts

    @staticmethod
    def _maybe_json(value: str) -> typing.Any:
        text = (value or "").strip()
        if not text:
            return ""
        if (text.startswith("{") and text.endswith("}")) or (
            text.startswith("[") and text.endswith("]")
        ):
            try:
                return json.loads(text)
            except Exception:
                return text
        return text

    @staticmethod
    def _parse_rgb(value: str) -> typing.Tuple[int, int, int]:
        parts = [p.strip() for p in (value or "").split(",")]
        if len(parts) != 3:
            return (26, 30, 36)
        try:
            r, g, b = [int(p) for p in parts]
            return (max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
        except Exception:
            return (26, 30, 36)

    @staticmethod
    def _short_json(data: typing.Any, limit: int = 700) -> str:
        try:
            raw = json.dumps(data, ensure_ascii=True)
        except Exception:
            raw = str(data)
        if len(raw) > limit:
            return f"{raw[:limit]}...truncated"
        return raw
