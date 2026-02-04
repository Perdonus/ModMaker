import asyncio
import datetime
import io
import json
import os
import subprocess
import time
import typing
import uuid

import requests
from PIL import Image, ImageDraw, ImageFont, ImageStat
from herokutl.tl.types import Message
from herokutl.types import InputMediaWebPage

from .. import loader, utils

PHONE_CPU_NAME = "Helio G85"
ASSETS_BASE_URL = "https://sosiskibot.ru/assets"
SCREEN_BASE_URL = "https://sosiskibot.ru/phone"
FONT_ASSET_NAME = "Unbounded-ExtraBold.ttf"
PHONE_FRAME_FILE = "phone1.png"
SCREEN_BOX = (340, 53, 628, 700)
SCREEN_REQUEST_TTL = 25
SCREEN_WAIT_SECONDS = 20


@loader.tds
class NtfMod(loader.Module):
    """Receive phone notifications and show them on demand"""

    strings = {"name": "Ntf"}
    _font_ready: bool = False

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "listen_host",
                "0.0.0.0",
                "Host to listen for notifications",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "listen_port",
                8934,
                "Port to listen for notifications",
                validator=loader.validators.Integer(minimum=1, maximum=65535),
            ),
            loader.ConfigValue(
                "max_items",
                50,
                "How many notifications to keep from the phone snapshot",
                validator=loader.validators.Integer(minimum=1, maximum=500),
            ),
            loader.ConfigValue(
                "max_logs",
                200,
                "How many log entries to keep",
                validator=loader.validators.Integer(minimum=10, maximum=2000),
            ),
            loader.ConfigValue(
                "phone_timeout",
                180,
                "Seconds to consider phone reachable since last contact",
                validator=loader.validators.Integer(minimum=10, maximum=86400),
            ),
            loader.ConfigValue(
                "phone_name_override",
                "Redmi 13C",
                "Override phone name in .phone (empty = use device name)",
                validator=loader.validators.String(),
            ),
        )
        self._notifications: typing.Optional[typing.List[dict]] = None
        self._log: typing.Optional[typing.List[dict]] = None
        self._last_seen: typing.Optional[dict] = None
        self._phone_state: typing.Optional[dict] = None
        self._screen_state: typing.Optional[dict] = None
        self._screen_request: typing.Optional[dict] = None
        self._server: typing.Optional[asyncio.AbstractServer] = None
        self._server_task: typing.Optional[asyncio.Task] = None
        self._last_error: typing.Optional[str] = None

    async def client_ready(self):
        self._notifications = self.pointer("notifications", [])
        self._log = self.pointer("log", [])
        self._last_seen = self.pointer("last_seen", {})
        self._phone_state = self.pointer("phone_state", {})
        self._screen_state = self.pointer("screen_state", {})
        self._screen_request = self.pointer("screen_request", {})
        await self._start_server()

    async def on_unload(self):
        await self._stop_server()

    @staticmethod
    def _assets_dir() -> str:
        return os.path.normpath(os.path.join(utils.get_base_dir(), "..", "assets"))

    @staticmethod
    def _modules_dir() -> str:
        return os.path.normpath(os.path.join(utils.get_base_dir(), "..", "modules"))

    @classmethod
    def _frame_path(cls) -> str:
        return os.path.join(cls._modules_dir(), PHONE_FRAME_FILE)

    @staticmethod
    def _asset_url(filename: str) -> str:
        base = ASSETS_BASE_URL.rstrip("/")
        name = filename.lstrip("/")
        return f"{base}/{name}"

    @classmethod
    def _ensure_font_asset(cls) -> typing.Optional[str]:
        path = os.path.join(cls._assets_dir(), FONT_ASSET_NAME)
        if os.path.isfile(path):
            cls._font_ready = True
            return path

        if not cls._font_ready:
            cls._font_ready = True
            try:
                response = requests.get(cls._asset_url(FONT_ASSET_NAME), timeout=20)
                response.raise_for_status()
                os.makedirs(cls._assets_dir(), exist_ok=True)
                with open(path, "wb") as handle:
                    handle.write(response.content)
                return path
            except Exception:
                pass

        return path if os.path.isfile(path) else None

    async def _stop_server(self):
        if self._server_task:
            self._server_task.cancel()
            self._server_task = None
        if self._server:
            self._server.close()
            try:
                await self._server.wait_closed()
            except Exception:
                pass
            self._server = None
            self._log_event("Server stopped")

    async def _start_server(self):
        await self._stop_server()
        host = self.config["listen_host"]
        port = self.config["listen_port"]
        try:
            self._server = await asyncio.start_server(self._handle_client, host, port)
            self._server_task = asyncio.create_task(self._server.serve_forever())
            self._last_error = None
            self._log_event(f"Server listening on {host}:{port}")
        except Exception as exc:
            self._last_error = str(exc)
            self._log_event(f"Server start error: {self._last_error}")

    def _get_screen_state(self) -> dict:
        if self._screen_state is None:
            self._screen_state = self.pointer("screen_state", {})
        return self._screen_state

    def _get_screen_request(self) -> dict:
        if self._screen_request is None:
            self._screen_request = self.pointer("screen_request", {})
        return self._screen_request

    def _clear_screen_request(self) -> None:
        req = self._get_screen_request()
        req.clear()

    def _screen_request_active(self) -> bool:
        req = self._get_screen_request()
        ts = req.get("ts")
        if not ts:
            return False
        if time.time() - float(ts) > SCREEN_REQUEST_TTL:
            req.clear()
            return False
        return True

    def _screen_request_response(self) -> typing.Optional[str]:
        if not self._screen_request_active():
            return None
        req = self._get_screen_request()
        last_sent = req.get("last_sent")
        if last_sent and time.time() - float(last_sent) < 2:
            return None
        req["last_sent"] = time.time()
        req_id = req.get("id") or ""
        response = f"SCREEN {req_id}".strip()
        self._log_event(f"Screen request sent: {response}")
        return response

    def _update_screen_state(self, payload: dict) -> None:
        state = self._get_screen_state()
        url = self._coerce_str(payload.get("screen_url"))
        if not url:
            return
        state["url"] = url
        ts = self._coerce_int(payload.get("screen_ts"))
        if ts is None:
            ts = int(time.time() * 1000)
        state["ts"] = ts
        req_id = self._coerce_str(payload.get("screen_req_id") or payload.get("screen_id"))
        if req_id:
            state["req_id"] = req_id
        self._log_event(f"Screen uploaded: {url}")
        self._clear_screen_request()

    async def _request_screen_image(
        self,
        message: Message,
        delay: int,
    ) -> typing.Optional[Image.Image]:
        if delay > 0:
            try:
                await message.edit(f"Скрин через {delay}s...")
            except Exception:
                pass
            await asyncio.sleep(delay)
        try:
            await message.edit("Запрашиваю скрин...")
        except Exception:
            pass

        req = self._get_screen_request()
        req_id = uuid.uuid4().hex
        req.clear()
        req["id"] = req_id
        req["ts"] = time.time()
        req["last_sent"] = 0.0
        self._log_event(f"Screen request queued: {req_id}")

        state = self._get_screen_state()
        last_url = state.get("url")
        start_ts = time.time()
        deadline = start_ts + SCREEN_WAIT_SECONDS

        while time.time() < deadline:
            await asyncio.sleep(1)
            state = self._get_screen_state()
            url = self._coerce_str(state.get("url"))
            ts_raw = state.get("ts")
            req_state = self._coerce_str(state.get("req_id"))
            ts = None
            if ts_raw is not None:
                try:
                    ts = float(ts_raw) / 1000.0
                except Exception:
                    ts = None
            if not url or url == last_url:
                continue
            if ts is not None and ts < start_ts:
                continue
            if req_state and req_state != req_id:
                continue
            try:
                response = requests.get(url, timeout=20)
                response.raise_for_status()
                data = response.content
            except Exception:
                continue
            if not data:
                continue
            try:
                image = Image.open(io.BytesIO(data)).convert("RGBA")
            except Exception:
                continue
            self._log_event(f"Screen fetched: {url}")
            return image

        self._clear_screen_request()
        self._log_event("Screen request timeout")
        return None

    async def _handle_client(
        self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        try:
            peer = writer.get_extra_info("peername")
            peer_ip = None
            peer_port = None
            if isinstance(peer, (list, tuple)) and len(peer) >= 2:
                peer_ip, peer_port = peer[0], peer[1]
                self._update_last_seen(peer_ip, peer_port)

            data = await reader.readline()
            if not data:
                writer.close()
                await writer.wait_closed()
                return
            payload_raw = data.decode("utf-8", "ignore").strip()
            if not payload_raw:
                writer.write(b"ERR empty\n")
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                return
            try:
                payload = json.loads(payload_raw)
            except json.JSONDecodeError:
                writer.write(b"ERR json\n")
                await writer.drain()
                self._log_event("Bad JSON payload received")
                writer.close()
                await writer.wait_closed()
                return

            self._log_payload(payload, peer_ip, peer_port)
            if payload.get("app_log_clear"):
                self._clear_app_log()
                self._log_event("App log cleared by client")
            app_log_batch = payload.get("app_log_batch")
            if isinstance(app_log_batch, str) and app_log_batch:
                self._append_app_log(app_log_batch)
                self._log_event(
                    f"App log batch received: {len(app_log_batch.encode('utf-8'))} bytes"
                )

            if payload.get("heartbeat") or payload.get("phone_state"):
                self._update_phone_state(payload, peer_ip, peer_port)
                self._update_notifications(payload.get("notifications"))
                self._update_screen_state(payload)
                response_line = self._screen_request_response()
                if response_line:
                    writer.write((response_line + "\n").encode("utf-8"))
                else:
                    writer.write(b"PONG\n" if payload.get("ping") else b"OK\n")
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                return
            if payload.get("ping"):
                response_line = self._screen_request_response()
                if response_line:
                    writer.write((response_line + "\n").encode("utf-8"))
                else:
                    writer.write(b"PONG\n")
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                return

            if payload.get("notifications") is not None:
                self._update_notifications(payload.get("notifications"))
                self._update_screen_state(payload)
                response_line = self._screen_request_response()
                if response_line:
                    writer.write((response_line + "\n").encode("utf-8"))
                else:
                    writer.write(b"OK\n")
                await writer.drain()
                writer.close()
                await writer.wait_closed()
                return
            self._update_screen_state(payload)
            response_line = self._screen_request_response()
            if response_line:
                writer.write((response_line + "\n").encode("utf-8"))
            else:
                writer.write(b"OK\n")
            await writer.drain()
        except Exception:
            try:
                writer.write(b"ERR\n")
                await writer.drain()
            except Exception:
                pass
            self._log_event("Client handling error")
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    def _update_last_seen(
        self, ip: typing.Optional[str], port: typing.Optional[int]
    ) -> None:
        if self._last_seen is None:
            self._last_seen = self.pointer("last_seen", {})
        self._last_seen["ts"] = time.time()
        if ip:
            self._last_seen["ip"] = str(ip)
        if port:
            self._last_seen["port"] = int(port)

    def _update_phone_state(
        self,
        payload: dict,
        peer_ip: typing.Optional[str],
        peer_port: typing.Optional[int],
    ) -> None:
        if self._phone_state is None:
            self._phone_state = self.pointer("phone_state", {})
        state = self._phone_state
        state["ts"] = time.time()
        if peer_ip:
            state["peer_ip"] = str(peer_ip)
        if peer_port:
            state["peer_port"] = int(peer_port)

        device_name = self._coerce_str(payload.get("device_name"))
        if not device_name:
            device_name = (
                self._coerce_str(payload.get("device_model"))
                or self._coerce_str(payload.get("device"))
            )
        if device_name:
            state["device_name"] = device_name
        for key in ("device_model", "device_manufacturer", "device_brand", "device"):
            value = self._coerce_str(payload.get(key))
            if value:
                state[key] = value

        battery_pct = self._coerce_float(payload.get("battery_pct"))
        if battery_pct is not None:
            state["battery_pct"] = battery_pct
        charging = self._coerce_bool(payload.get("charging"))
        if charging is not None:
            state["charging"] = charging

        uptime_ms = self._coerce_int(payload.get("uptime_ms"))
        if uptime_ms is not None:
            state["uptime_ms"] = uptime_ms

        cpu_percent = self._coerce_float(payload.get("cpu_percent"))
        if cpu_percent is not None:
            state["cpu_percent"] = cpu_percent

        ram_used = self._coerce_int(payload.get("ram_used"))
        ram_total = self._coerce_int(payload.get("ram_total"))
        if ram_used is not None:
            state["ram_used"] = ram_used
        if ram_total is not None:
            state["ram_total"] = ram_total

    def _build_item(self, payload: typing.Any) -> typing.Optional[dict]:
        if not isinstance(payload, dict):
            return None
        title = str(payload.get("title") or "")
        text = str(payload.get("text") or "")
        package = str(payload.get("package") or "")
        app = str(payload.get("app") or "")
        timestamp = payload.get("post_time") or payload.get("timestamp")
        return {
            "title": title,
            "text": text,
            "package": package,
            "app": app,
            "timestamp": timestamp,
            "received_at": time.time(),
        }

    def _update_notifications(self, raw: typing.Any) -> None:
        if raw is None:
            return
        items = []
        if isinstance(raw, list):
            for entry in raw:
                item = self._build_item(entry)
                if item is not None:
                    items.append(item)
        elif isinstance(raw, dict):
            item = self._build_item(raw)
            if item is not None:
                items.append(item)
        else:
            return
        if self._notifications is None:
            self._notifications = self.pointer("notifications", [])
        max_items = self.config["max_items"]
        if len(items) > max_items:
            items = items[:max_items]
        self._notifications.clear()
        self._notifications.extend(items)
        apps = []
        for item in items:
            name = (item.get("app") or item.get("package") or "").strip()
            if name and name not in apps:
                apps.append(name)
            if len(apps) >= 3:
                break
        apps_text = ", ".join(apps) if apps else "none"
        self._log_event(f"Notifications snapshot: {len(items)} apps={apps_text}")

    def _log_event(self, text: str) -> None:
        if self._log is None:
            self._log = self.pointer("log", [])
        ts = time.time()
        self._log.append({"ts": ts, "text": text})
        max_logs = self.config["max_logs"]
        if len(self._log) > max_logs:
            del self._log[:-max_logs]
        if self._is_screen_log(text):
            dt = datetime.datetime.fromtimestamp(ts)
            stamp = dt.strftime("%Y-%m-%d %H:%M:%S")
            ms = int((ts - int(ts)) * 1000)
            line = f"{stamp}.{ms:03d} NtfMod {text}"
            self._append_module_log(line)

    @staticmethod
    def _is_screen_log(text: str) -> bool:
        return "screen" in text.lower()

    def _log_payload(
        self,
        payload: dict,
        peer_ip: typing.Optional[str],
        peer_port: typing.Optional[int],
    ) -> None:
        parts = []
        addr = f"{peer_ip}:{peer_port}" if peer_ip and peer_port else "unknown"
        parts.append(f"from={addr}")

        types = []
        if payload.get("heartbeat"):
            types.append("heartbeat")
        if payload.get("ping"):
            types.append("ping")
        if payload.get("notifications") is not None:
            types.append("notifications")
        if types:
            parts.append(f"type={'+'.join(types)}")

        raw_notif = payload.get("notifications")
        if isinstance(raw_notif, list):
            parts.append(f"notif={len(raw_notif)}")
        elif isinstance(raw_notif, dict):
            parts.append("notif=1")

        screen_url = self._coerce_str(payload.get("screen_url"))
        if screen_url:
            parts.append("screen_url=yes")
        screen_req_id = self._coerce_str(payload.get("screen_req_id"))
        if screen_req_id:
            parts.append(f"screen_req_id={screen_req_id}")
        if payload.get("app_log_clear"):
            parts.append("app_log_clear=yes")
        app_log_batch = payload.get("app_log_batch")
        if isinstance(app_log_batch, str) and app_log_batch:
            parts.append(f"app_log_bytes={len(app_log_batch.encode('utf-8'))}")

        device = self._coerce_str(payload.get("device_name") or payload.get("device_model"))
        if device:
            parts.append(f"device={device[:40]}")
        battery = self._coerce_float(payload.get("battery_pct"))
        if battery is not None:
            parts.append(f"bat={battery:.0f}%")
        charging = self._coerce_bool(payload.get("charging"))
        if charging is not None:
            parts.append(f"chg={charging}")
        cpu_pct = self._coerce_float(payload.get("cpu_percent"))
        if cpu_pct is not None:
            parts.append(f"cpu={cpu_pct:.1f}%")
        ram_used = self._coerce_int(payload.get("ram_used"))
        ram_total = self._coerce_int(payload.get("ram_total"))
        if ram_used is not None and ram_total:
            parts.append(
                f"ram={self._format_bytes(ram_used)}/{self._format_bytes(ram_total)}"
            )
        uptime_ms = self._coerce_int(payload.get("uptime_ms"))
        if uptime_ms is not None:
            parts.append(f"uptime={self._format_age(uptime_ms / 1000)}")

        last_app = self._coerce_str(payload.get("last_app"))
        if last_app:
            parts.append(f"last_app={last_app[:40]}")
        last_title = self._coerce_str(payload.get("last_title"))
        if last_title:
            parts.append(f"last_title={last_title[:60]}")

        if self._screen_request_active():
            req_id = self._get_screen_request().get("id")
            if req_id:
                parts.append(f"screen_req_pending={req_id}")

        self._log_event("Payload " + " ".join(parts))

    def _append_app_log(self, text: str) -> None:
        if not text:
            return
        path = os.path.join(self._modules_dir(), "log.txt")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as handle:
                if not text.endswith("\n"):
                    text += "\n"
                handle.write(text)
        except Exception:
            self._log_event("Failed to write app log batch")

    def _append_module_log(self, text: str) -> None:
        if not text:
            return
        path = os.path.join(self._modules_dir(), "log.txt")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(text + "\n")
        except Exception:
            pass

    def _clear_app_log(self) -> None:
        path = os.path.join(self._modules_dir(), "log.txt")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8"):
                pass
        except Exception:
            self._log_event("Failed to clear app log")

    @staticmethod
    def _format_age(seconds: float) -> str:
        total = max(0, int(seconds))
        minutes, sec = divmod(total, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours or parts:
            parts.append(f"{hours}h")
        if minutes or parts:
            parts.append(f"{minutes}m")
        parts.append(f"{sec}s")
        return " ".join(parts)

    @staticmethod
    def _format_bytes(value: typing.Optional[int]) -> str:
        if value is None:
            return "N/A"
        size = float(value)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                if unit == "B":
                    return f"{int(size)} {unit}"
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @staticmethod
    def _coerce_float(value: typing.Any) -> typing.Optional[float]:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_int(value: typing.Any) -> typing.Optional[int]:
        try:
            if value is None:
                return None
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_str(value: typing.Any) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @staticmethod
    def _coerce_bool(value: typing.Any) -> typing.Optional[bool]:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        text = str(value).strip().lower()
        if text in {"1", "true", "yes", "y", "on"}:
            return True
        if text in {"0", "false", "no", "n", "off"}:
            return False
        return None

    @staticmethod
    def _clamp(value: int, min_value: int, max_value: int) -> int:
        return max(min_value, min(max_value, value))

    @staticmethod
    def _lerp_color(
        a: typing.Tuple[int, int, int],
        b: typing.Tuple[int, int, int],
        t: float,
    ) -> typing.Tuple[int, int, int]:
        t = max(0.0, min(1.0, t))
        return (
            int(a[0] + (b[0] - a[0]) * t),
            int(a[1] + (b[1] - a[1]) * t),
            int(a[2] + (b[2] - a[2]) * t),
        )

    @staticmethod
    def _with_alpha(
        color: typing.Tuple[int, int, int],
        alpha: int,
    ) -> typing.Tuple[int, int, int, int]:
        return (color[0], color[1], color[2], alpha)

    def _md3_palette(self, photo: Image.Image) -> dict:
        seed = self._accent_from_photo(photo)[:3]
        base = (12, 16, 22)
        surface = self._lerp_color(base, seed, 0.18)
        surface_mid = self._lerp_color(base, seed, 0.26)
        surface_hi = self._lerp_color(base, seed, 0.34)
        primary = self._lerp_color(seed, (255, 255, 255), 0.14)
        muted = self._lerp_color((245, 246, 250), surface, 0.4)
        return {
            "surface": self._with_alpha(surface, 235),
            "surface_mid": self._with_alpha(surface_mid, 225),
            "surface_hi": self._with_alpha(surface_hi, 210),
            "pill": self._with_alpha(surface_mid, 210),
            "primary": self._with_alpha(primary, 255),
            "text": (245, 246, 250, 255),
            "muted": self._with_alpha(muted, 255),
        }

    @staticmethod
    def _draw_pill(
        draw: ImageDraw.ImageDraw,
        box: typing.Tuple[int, int, int, int],
        fill: typing.Tuple[int, int, int, int],
        radius: int,
    ) -> None:
        draw.rounded_rectangle(box, radius=radius, fill=fill)

    @staticmethod
    def _text_size(
        draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont
    ) -> typing.Tuple[int, int]:
        box = draw.textbbox((0, 0), text, font=font)
        return box[2] - box[0], box[3] - box[1]

    def _wrap_lines(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        font: ImageFont.ImageFont,
        max_width: int,
    ) -> typing.List[str]:
        words = text.split()
        if not words:
            return [""]
        lines = []
        current = words[0]
        for word in words[1:]:
            candidate = f"{current} {word}"
            if self._text_size(draw, candidate, font)[0] <= max_width:
                current = candidate
            else:
                lines.append(current)
                current = word
        lines.append(current)
        return lines

    @staticmethod
    def _load_font(size: int) -> ImageFont.ImageFont:
        path = NtfMod._ensure_font_asset()
        if path:
            try:
                return ImageFont.truetype(path, size=size)
            except Exception:
                pass
        return ImageFont.load_default()

    def _save_card_asset(self, data: bytes, ext: str) -> typing.Optional[str]:
        if not data:
            return None
        ext = ext.lower() if ext else ""
        if ext and not ext.startswith("."):
            ext = f".{ext}"
        if not ext:
            ext = ".jpg"
        name = f"phone_card_{uuid.uuid4().hex}{ext}"
        path = os.path.join(self._assets_dir(), name)
        try:
            os.makedirs(self._assets_dir(), exist_ok=True)
            with open(path, "wb") as handle:
                handle.write(data)
        except Exception:
            return None
        return self._asset_url(name)

    async def _send_card_url(
        self,
        message: Message,
        url: str,
        caption: typing.Optional[str],
    ):
        media: typing.Union[str, InputMediaWebPage] = (
            InputMediaWebPage(url, optional=True) if url.startswith("https://") else url
        )
        try:
            if getattr(message, "out", False) and not message.via_bot_id and not message.fwd_from:
                return await message.edit(caption or "", file=media)
            return await message.client.send_file(
                message.peer_id,
                media,
                caption=caption,
                reply_to=getattr(message, "reply_to_msg_id", None),
            )
        except Exception:
            return None

    async def _answer_text(self, message: Message, text: str):
        if getattr(message, "out", False) and not message.via_bot_id and not message.fwd_from:
            try:
                return await message.edit(text, link_preview=False)
            except Exception:
                pass
        return await message.respond(text, link_preview=False)

    async def _send_card(
        self,
        message: Message,
        file: io.BytesIO,
        caption: typing.Optional[str],
    ):
        if isinstance(file, io.BytesIO):
            data = file.getvalue()
            ext = os.path.splitext(getattr(file, "name", "") or "")[1]
            url = self._save_card_asset(data, ext)
            if url:
                sent = await self._send_card_url(message, url, caption)
                if sent is not None:
                    return sent
            try:
                file.seek(0)
            except Exception:
                pass

        if getattr(message, "out", False) and not message.via_bot_id and not message.fwd_from:
            try:
                return await message.edit(caption or "", file=file)
            except Exception:
                pass

        return await message.client.send_file(
            message.peer_id,
            file,
            caption=caption,
            reply_to=getattr(message, "reply_to_msg_id", None),
        )

    async def _send_document(
        self,
        message: Message,
        file: io.BytesIO,
        caption: typing.Optional[str] = None,
    ):
        return await message.client.send_file(
            message.peer_id,
            file,
            caption=caption,
            reply_to=getattr(message, "reply_to_msg_id", None),
            force_document=True,
        )

    @staticmethod
    def _center_crop_square(image: Image.Image) -> Image.Image:
        size = min(image.width, image.height)
        left = (image.width - size) // 2
        top = (image.height - size) // 2
        return image.crop((left, top, left + size, top + size))

    @staticmethod
    def _accent_from_photo(photo: Image.Image) -> typing.Tuple[int, int, int, int]:
        stat = ImageStat.Stat(photo.convert("RGB"))
        r, g, b = [int(x) for x in stat.mean[:3]]
        brightness = 0.2126 * r + 0.7152 * g + 0.0722 * b
        if brightness < 90:
            scale = 90 / max(brightness, 1)
            r = min(int(r * scale), 255)
            g = min(int(g * scale), 255)
            b = min(int(b * scale), 255)
        elif brightness > 210:
            scale = 210 / brightness
            r = int(r * scale)
            g = int(g * scale)
            b = int(b * scale)
        return (r, g, b, 255)

    def _load_phone_frame(self) -> Image.Image:
        path = self._frame_path()
        if not os.path.isfile(path):
            raise FileNotFoundError(f"phone frame not found: {path}")
        return Image.open(path).convert("RGBA")

    @staticmethod
    def _resize_cover(image: Image.Image, width: int, height: int) -> Image.Image:
        if width <= 0 or height <= 0:
            return image
        scale = max(width / image.width, height / image.height)
        new_size = (max(1, int(image.width * scale)), max(1, int(image.height * scale)))
        image = image.resize(new_size, Image.LANCZOS)
        left = (image.width - width) // 2
        top = (image.height - height) // 2
        return image.crop((left, top, left + width, top + height))

    @classmethod
    def _screen_box_scaled(cls, frame: Image.Image) -> typing.Tuple[int, int, int, int]:
        base_w = 768
        base_h = 768
        if frame.width == base_w and frame.height == base_h:
            return SCREEN_BOX
        sx = frame.width / base_w
        sy = frame.height / base_h
        x1, y1, x2, y2 = SCREEN_BOX
        return (
            int(x1 * sx),
            int(y1 * sy),
            int(x2 * sx),
            int(y2 * sy),
        )

    def _load_screen_image(self) -> typing.Optional[Image.Image]:
        state = self._get_screen_state()
        url = self._coerce_str(state.get("url"))
        if not url:
            return None
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            data = response.content
        except Exception:
            return None
        try:
            return Image.open(io.BytesIO(data)).convert("RGBA")
        except Exception:
            return None

    def _compose_phone_frame(
        self,
        frame: Image.Image,
        screen: typing.Optional[Image.Image],
    ) -> Image.Image:
        if not screen:
            return frame
        x1, y1, x2, y2 = self._screen_box_scaled(frame)
        width = max(1, x2 - x1 + 1)
        height = max(1, y2 - y1 + 1)
        screen = self._resize_cover(screen, width, height)
        base = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        base.paste(screen, (x1, y1))
        return Image.alpha_composite(base, frame)

    def _encode_output(self, image: Image.Image) -> io.BytesIO:
        rgb = image.convert("RGB")
        max_width = 1024
        if rgb.width > max_width:
            new_height = int(rgb.height * (max_width / rgb.width))
            rgb = rgb.resize((max_width, new_height), Image.LANCZOS)

        png_buffer = io.BytesIO()
        rgb.save(png_buffer, format="PNG", optimize=True)
        png_buffer.seek(0)

        try:
            proc = subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    "pipe:0",
                    "-vf",
                    "scale=trunc(iw/2)*2:trunc(ih/2)*2",
                    "-q:v",
                    "6",
                    "-f",
                    "image2pipe",
                    "-vcodec",
                    "mjpeg",
                    "pipe:1",
                ],
                input=png_buffer.getvalue(),
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                check=True,
            )
            output = io.BytesIO(proc.stdout)
            output.name = "phone.jpg"
            output.seek(0)
            return output
        except Exception:
            output = io.BytesIO()
            rgb.save(output, format="JPEG", quality=82, optimize=True, progressive=True)
            output.name = "phone.jpg"
            output.seek(0)
            return output

    def _get_phone_state(self) -> dict:
        if self._phone_state is None:
            self._phone_state = self.pointer("phone_state", {})
        return self._phone_state

    def _get_notifications(self) -> typing.List[dict]:
        if self._notifications is None:
            self._notifications = self.pointer("notifications", [])
        return list(self._notifications) if self._notifications else []

    @staticmethod
    def _draw_battery_icon(
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        width: int,
        height: int,
        percent: typing.Optional[float],
        charging: typing.Optional[bool],
        outline: typing.Tuple[int, int, int, int],
        fill: typing.Tuple[int, int, int, int],
        bolt_color: typing.Tuple[int, int, int, int],
    ) -> None:
        cap_w = max(2, int(width * 0.12))
        body_w = max(4, width - cap_w - 2)
        body_box = (x, y, x + body_w, y + height)
        cap_x = x + body_w + 1
        cap_box = (
            cap_x,
            y + max(1, int(height * 0.25)),
            cap_x + cap_w,
            y + height - max(1, int(height * 0.25)),
        )
        draw.rectangle(body_box, outline=outline, width=2)
        draw.rectangle(cap_box, fill=outline)
        if percent is not None:
            fill_w = int((body_w - 4) * max(0.0, min(percent, 100.0)) / 100.0)
            if fill_w > 0:
                fill_box = (x + 2, y + 2, x + 2 + fill_w, y + height - 2)
                draw.rectangle(fill_box, fill=fill)
        if not charging:
            return
        bolt_w = max(6, int(width * 0.6))
        bolt_h = max(10, int(height * 1.6))
        bolt_x = x + width + max(4, int(width * 0.2))
        bolt_y = y + max(0, int((height - bolt_h) / 2))
        bolt = [
            (bolt_x + int(bolt_w * 0.45), bolt_y),
            (bolt_x, bolt_y + int(bolt_h * 0.55)),
            (bolt_x + int(bolt_w * 0.38), bolt_y + int(bolt_h * 0.55)),
            (bolt_x + int(bolt_w * 0.1), bolt_y + bolt_h),
            (bolt_x + bolt_w, bolt_y + int(bolt_h * 0.4)),
            (bolt_x + int(bolt_w * 0.55), bolt_y + int(bolt_h * 0.4)),
        ]
        draw.polygon(bolt, fill=bolt_color)

    def _build_phone_card(
        self,
        screen: typing.Optional[Image.Image] = None,
    ) -> io.BytesIO:
        frame = self._load_phone_frame()
        if screen is None:
            screen = self._load_screen_image()
        frame = self._compose_phone_frame(frame, screen)
        photo = self._center_crop_square(frame)
        photo_side = min(photo.width, photo.height)
        photo_side = min(photo_side, 900)
        if photo_side != photo.width:
            photo = photo.resize((photo_side, photo_side), Image.LANCZOS)

        panel_width = int(photo_side * 1.1)
        total_width = photo_side + panel_width
        total_height = photo_side

        palette_source = screen if screen is not None else photo
        palette = self._md3_palette(palette_source)
        panel_color = palette["surface"]
        accent_color = palette["primary"]
        text_color = palette["text"]
        muted_color = palette["muted"]
        pill_color = palette["pill"]

        image = Image.new("RGBA", (total_width, total_height), panel_color)
        image.paste(photo, (0, 0), photo)

        transition = self._clamp(int(photo_side * 0.12), 24, 140)
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        start_x = photo_side - transition
        for idx in range(transition):
            alpha = int(panel_color[3] * (idx / max(transition - 1, 1)))
            x = start_x + idx
            if x < 0 or x >= photo_side:
                continue
            overlay_draw.line(
                (x, 0, x, total_height),
                fill=(panel_color[0], panel_color[1], panel_color[2], alpha),
            )
        image = Image.alpha_composite(image, overlay)
        draw = ImageDraw.Draw(image)

        margin = int(photo_side * 0.08)
        title_font = self._load_font(self._clamp(int(photo_side * 0.11), 26, 86))
        label_font = self._load_font(self._clamp(int(photo_side * 0.045), 14, 36))
        value_font = self._load_font(self._clamp(int(photo_side * 0.055), 16, 40))
        line_gap = int(value_font.size * 0.32)
        pill_pad_x = int(value_font.size * 0.55)
        pill_pad_y = int(value_font.size * 0.28)
        pill_radius = int(value_font.size * 0.9)

        state = self._get_phone_state()
        override_name = (self.config["phone_name_override"] or "").strip()
        if override_name:
            name = override_name
        else:
            name = (
                state.get("device_name")
                or state.get("device_model")
                or state.get("device")
                or "Phone"
            )
            name = str(name).strip() or "Phone"
        battery_pct = self._coerce_float(state.get("battery_pct"))
        charging = self._coerce_bool(state.get("charging"))
        cpu_pct = self._coerce_float(state.get("cpu_percent"))
        ram_used = self._coerce_int(state.get("ram_used"))
        ram_total = self._coerce_int(state.get("ram_total"))
        uptime_ms = self._coerce_int(state.get("uptime_ms"))

        data_x = photo_side + margin
        max_width = total_width - margin - data_x
        y = margin

        tag_text = "PHONE"
        tag_pad_x = int(label_font.size * 0.6)
        tag_pad_y = int(label_font.size * 0.3)
        tag_w, tag_h = self._text_size(draw, tag_text, label_font)
        tag_pill_h = tag_h + tag_pad_y * 2
        self._draw_pill(
            draw,
            (
                data_x,
                y,
                data_x + tag_w + tag_pad_x * 2,
                y + tag_pill_h,
            ),
            palette["surface_hi"],
            max(8, int(tag_pill_h * 0.5)),
        )
        draw.text(
            (data_x + tag_pad_x, y + max(0, (tag_pill_h - tag_h) // 2)),
            tag_text,
            font=label_font,
            fill=muted_color,
            stroke_width=1,
            stroke_fill=(0, 0, 0, 140),
        )
        y += tag_pill_h + int(label_font.size * 0.4)

        name_height = title_font.size + pill_pad_y * 2
        self._draw_pill(
            draw,
            (data_x, y, data_x + max_width, y + name_height),
            pill_color,
            max(12, int(name_height * 0.5)),
        )
        draw.text(
            (data_x + pill_pad_x, y + max(0, (name_height - title_font.size) // 2)),
            name,
            font=title_font,
            fill=text_color,
            stroke_width=2,
            stroke_fill=(0, 0, 0, 180),
        )
        y += name_height + int(pill_pad_y * 0.8)

        cpu_line = f"CPU: {PHONE_CPU_NAME}"
        cpu_height = label_font.size + pill_pad_y * 2
        self._draw_pill(
            draw,
            (data_x, y, data_x + max_width, y + cpu_height),
            palette["surface_hi"],
            max(10, int(cpu_height * 0.5)),
        )
        draw.text(
            (data_x + pill_pad_x, y + max(0, (cpu_height - label_font.size) // 2)),
            cpu_line,
            font=label_font,
            fill=muted_color,
            stroke_width=1,
            stroke_fill=(0, 0, 0, 140),
        )
        y += cpu_height + int(label_font.size * 0.6)

        labels = ["BATTERY", "CPU", "RAM", "UPTIME"]
        label_width = max(
            self._text_size(draw, f"{label}:", label_font)[0] for label in labels
        )
        label_pad = int(label_font.size * 0.6)
        value_x = data_x + pill_pad_x + label_width + label_pad
        value_max = max_width - (value_x - data_x) - pill_pad_x
        row_height = max(value_font.size, label_font.size) + pill_pad_y * 2
        row_step = row_height + line_gap

        battery_text = f"{battery_pct:.0f}%" if battery_pct is not None else "N/A"
        battery_fill = accent_color
        if charging:
            battery_fill = (70, 220, 120, 255)
        elif battery_pct is not None:
            if battery_pct < 5:
                battery_fill = (230, 70, 70, 255)
            elif battery_pct < 20:
                battery_fill = (245, 165, 40, 255)
        battery_outline = (255, 255, 255, 220)

        def draw_row(label: str, value: str, with_battery: bool = False) -> None:
            nonlocal y
            lines = self._wrap_lines(draw, value, value_font, value_max)
            for idx, line in enumerate(lines):
                row_top = y
                row_bottom = y + row_height
                self._draw_pill(
                    draw,
                    (data_x, row_top, data_x + max_width, row_bottom),
                    pill_color,
                    pill_radius,
                )
                label_y = row_top + (row_height - label_font.size) // 2
                value_y = row_top + (row_height - value_font.size) // 2
                if idx == 0:
                    draw.text(
                        (data_x + pill_pad_x, label_y),
                        f"{label}:",
                        font=label_font,
                        fill=muted_color,
                        stroke_width=1,
                        stroke_fill=(0, 0, 0, 160),
                    )
                draw.text(
                    (value_x, value_y),
                    line,
                    font=value_font,
                    fill=text_color,
                    stroke_width=1,
                    stroke_fill=(0, 0, 0, 160),
                )
                if with_battery and idx == 0:
                    text_w, _ = self._text_size(draw, line, value_font)
                    icon_w = int(value_font.size * 1.6)
                    icon_h = int(value_font.size * 0.6)
                    icon_x = value_x + text_w + int(value_font.size * 0.4)
                    icon_y = value_y + max(0, int((value_font.size - icon_h) / 2))
                    self._draw_battery_icon(
                        draw,
                        icon_x,
                        icon_y,
                        icon_w,
                        icon_h,
                        battery_pct,
                        charging,
                        battery_outline,
                        battery_fill,
                        battery_outline,
                    )
                y += row_step

        draw_row("BATTERY", battery_text, with_battery=True)

        cpu_text = f"{cpu_pct:.2f}%" if cpu_pct is not None else "N/A"
        ram_text = (
            f"{self._format_bytes(ram_used)} / {self._format_bytes(ram_total)}"
            if ram_used is not None and ram_total
            else "N/A"
        )
        uptime_text = (
            self._format_age(uptime_ms / 1000) if uptime_ms is not None else "N/A"
        )
        draw_row("CPU", cpu_text)
        draw_row("RAM", ram_text)
        draw_row("UPTIME", uptime_text)

        return self._encode_output(image)

    @staticmethod
    def _format_item(item: dict) -> str:
        app = item.get("app") or item.get("package") or "Unknown"
        title = item.get("title") or ""
        text = item.get("text") or ""
        package = item.get("package") or ""
        timestamp = item.get("timestamp")
        if isinstance(timestamp, (int, float)):
            dt = datetime.datetime.fromtimestamp(timestamp / 1000)
        else:
            dt = datetime.datetime.fromtimestamp(item.get("received_at", time.time()))
        stamp = dt.strftime("%H:%M:%S")
        lines = [f"<b>{utils.escape_html(str(app))}</b> / <code>{stamp}</code>"]
        details = []
        if title:
            details.append(f"<i>{utils.escape_html(str(title))}</i>")
        if text:
            details.append(utils.escape_html(str(text)))
        if details:
            lines.append(
                "<blockquote expandable>" + "\n".join(details) + "</blockquote>"
            )
        return "\n".join(lines)

    def _format_notifications(self) -> str:
        if self._last_seen is None:
            self._last_seen = self.pointer("last_seen", {})
        last_ts = self._last_seen.get("ts")
        if not last_ts:
            return "Нет уведомлений"
        try:
            age = time.time() - float(last_ts)
        except Exception:
            age = 0
        if age > self.config["phone_timeout"]:
            return "Нет уведомлений"
        items = self._get_notifications()
        if not items:
            return "Нет уведомлений"
        return "\n\n".join(self._format_item(item) for item in items)

    @staticmethod
    def _format_log_item(item: dict) -> str:
        ts = item.get("ts") or time.time()
        dt = datetime.datetime.fromtimestamp(ts)
        stamp = dt.strftime("%H:%M:%S")
        text = utils.escape_html(str(item.get("text") or "")) 
        return f"<code>{stamp}</code> {text}"

    @loader.command(ru_doc="Данные телефона и уведомления")
    async def phone(self, message: Message):
        args_raw = utils.get_args_raw(message).strip()
        args = args_raw.lower()
        if args in {"restart", "start"}:
            await self._start_server()
            if self._last_error:
                await self._answer_text(message, f"Server error: {self._last_error}")
            else:
                await self._answer_text(
                    message,
                    f"Server listening on {self.config['listen_host']}:{self.config['listen_port']}",
                )
            return
        if args in {"check", "ping"}:
            if self._last_seen is None:
                self._last_seen = self.pointer("last_seen", {})
            now = time.time()
            last_ts = self._last_seen.get("ts")
            ip = self._last_seen.get("ip")
            port = self._last_seen.get("port")
            timeout = self.config["phone_timeout"]

            if self._last_error:
                server_line = f"Server error: {self._last_error}"
            elif self._server:
                server_line = (
                    f"Server listening on {self.config['listen_host']}:{self.config['listen_port']}"
                )
            else:
                server_line = "Server not running"

            if not last_ts:
                phone_line = "Phone unreachable: no incoming connections yet"
                self._log_event("Phone check failed: no incoming connections")
            else:
                age = now - float(last_ts)
                age_text = self._format_age(age)
                source = f"{ip}:{port}" if ip and port else "unknown"
                if age <= timeout:
                    phone_line = f"Phone reachable: last seen {age_text} ago from {source}"
                    self._log_event(f"Phone check ok: {source} {age_text} ago")
                else:
                    phone_line = (
                        f"Phone unreachable: last seen {age_text} ago from {source}"
                    )
                    self._log_event(f"Phone check stale: {source} {age_text} ago")
            await self._answer_text(message, f"{server_line}\n{phone_line}")
            return
        if args in {"log", "logs"}:
            if self._log is None:
                self._log = self.pointer("log", [])
            screen_items = [
                item
                for item in self._log
                if self._is_screen_log(str(item.get("text") or ""))
            ]
            sent_any = False
            if screen_items:
                text = "\n".join(self._format_log_item(item) for item in screen_items)
                file = io.BytesIO(text.encode("utf-8"))
                file.name = "phone_screen_log.txt"
                await self._send_document(message, file, "Phone screen logs")
                sent_any = True
            app_log_path = os.path.join(self._modules_dir(), "log.txt")
            if os.path.isfile(app_log_path):
                try:
                    with open(app_log_path, "rb") as handle:
                        data = handle.read()
                except Exception:
                    data = b""
                if data:
                    lines = data.decode("utf-8", "ignore").splitlines()
                    filtered = [line for line in lines if self._is_screen_log(line)]
                    if filtered:
                        payload = "\n".join(filtered) + "\n"
                        app_file = io.BytesIO(payload.encode("utf-8"))
                        app_file.name = "app_screen_log.txt"
                        await self._send_document(message, app_file, "App screen logs")
                        sent_any = True
            if not sent_any:
                await self._answer_text(message, "No screen logs yet")
            return
        if args in {"clear", "clr", "clean"}:
            if self._log is None:
                self._log = self.pointer("log", [])
            self._log.clear()
            self._clear_app_log()
            await self._answer_text(message, "Logs cleared")
            return

        delay = 0
        if args_raw:
            try:
                delay = int(float(args_raw))
            except ValueError:
                delay = 0
        msg = await self._answer_text(message, "Запрашиваю скрин...")
        screen = await self._request_screen_image(msg, max(0, delay))
        try:
            image = self._build_phone_card(screen)
        except FileNotFoundError:
            await self._answer_text(msg, "phone1.png not found in modules.")
            return
        except Exception:
            await self._answer_text(msg, "Failed to render phone card.")
            return

        await self._send_card(msg, image, None)

    @loader.command(ru_doc="Скрин экрана телефона")
    async def screen(self, message: Message):
        msg = await self._answer_text(message, "Запрашиваю скрин...")
        req = self._get_screen_request()
        req_id = uuid.uuid4().hex
        req.clear()
        req["id"] = req_id
        req["ts"] = time.time()
        req["last_sent"] = 0.0
        self._log_event(f"Screen request queued: {req_id}")

        state = self._get_screen_state()
        last_url = state.get("url")
        start_ts = time.time()
        deadline = start_ts + SCREEN_WAIT_SECONDS

        while time.time() < deadline:
            await asyncio.sleep(1)
            state = self._get_screen_state()
            url = self._coerce_str(state.get("url"))
            ts_raw = state.get("ts")
            req_state = self._coerce_str(state.get("req_id"))
            ts = None
            if ts_raw is not None:
                try:
                    ts = float(ts_raw) / 1000.0
                except Exception:
                    ts = None
            if not url or url == last_url:
                continue
            if ts is not None and ts < start_ts:
                continue
            if req_state and req_state != req_id:
                continue
            try:
                response = requests.get(url, timeout=20)
                response.raise_for_status()
                data = response.content
            except Exception:
                continue
            if not data:
                continue
            file = io.BytesIO(data)
            file.name = "screen.jpg"
            await self._send_card(msg, file, None)
            return

        self._clear_screen_request()
        self._log_event("Screen request timeout")
        await self._answer_text(msg, "Скрин не получен.")

    @loader.command(ru_doc="Только уведомления телефона")
    async def ntf(self, message: Message):
        text = self._format_notifications()
        if len(text) > 4096:
            text = "Слишком много уведомлений, сократи список."
        await self._answer_text(message, text)
