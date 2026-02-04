import base64
import io
import math
import os
import platform
import re
import subprocess
import tempfile
import time
import typing
import uuid

import psutil
import requests
from PIL import Image, ImageDraw, ImageFont, ImageStat
from herokutl.tl.types import Message
from herokutl.types import InputMediaWebPage

from .. import loader, utils


DEFAULT_BACKGROUND_B64 = ""
ASSETS_BASE_URL = "https://sosiskibot.ru/assets"
FONT_ASSET_NAME = "Unbounded-ExtraBold.ttf"

GPU_NAME_OVERRIDE = "AMD RS880M"
VIDEO_EXTS = {".mp4", ".mov", ".webm", ".mkv", ".gif"}
CARD_BASE_SIDE = 900

@loader.tds
class ServMod(loader.Module):
    """Render a server status card"""

    strings = {"name": "Serv"}
    _cpu_cache: typing.Optional[typing.Tuple[float, float]] = None
    _font_ready: bool = False
    _last_video_log: typing.Optional[str] = None

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "background_url",
                "",
                "Background image URL or asset filename",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "server_name",
                "",
                "Override server name (optional)",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "label_server",
                "SERVER NAME",
                "Label for server name",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "label_status",
                "STATUS",
                "Label for status block",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "label_components",
                "COMPONENTS",
                "Label for components block",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "label_cpu",
                "CPU",
                "CPU label",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "label_gpu",
                "GPU",
                "GPU label",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "label_ram",
                "RAM",
                "RAM label",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "label_ping",
                "PING",
                "Ping label",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "label_uptime",
                "UPTIME",
                "Uptime label",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "label_disk",
                "MEMORY",
                "Disk label",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "video_audio_url",
                "",
                "Optional audio URL or asset filename for video background",
                validator=loader.validators.String(),
            ),
        )

    @staticmethod
    def _clamp(value: int, min_value: int, max_value: int) -> int:
        return max(min_value, min(max_value, value))

    @staticmethod
    def _assets_dir() -> str:
        return os.path.normpath(os.path.join(utils.get_base_dir(), "..", "assets"))

    @staticmethod
    def _target_side() -> int:
        return CARD_BASE_SIDE

    @staticmethod
    def _shorten_log(text: str, limit: int = 1200) -> str:
        if not text:
            return ""
        text = text.strip()
        if len(text) <= limit:
            return text
        head = text[: max(0, limit - 120)].rstrip()
        tail = text[-80:].rstrip()
        return f"{head}\n...\n{tail}"

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
    def _get_greeting(now: time.struct_time) -> str:
        hour = now.tm_hour + now.tm_min / 60.0
        if 5 <= hour < 12:
            return "Доброе утро"
        if 12 <= hour < 18:
            return "Добрый день"
        if 18 <= hour < 23:
            return "Добрый вечер"
        return "Доброй ночи"

    def _build_sky_icon(self, size: int, now: time.struct_time) -> Image.Image:
        hour = now.tm_hour + now.tm_min / 60.0
        is_day = 6 <= hour < 18
        if is_day:
            t = (hour - 6) / 12.0
            warm = abs(t - 0.5) * 2.0
            sky_top = self._lerp_color((100, 170, 255), (255, 170, 120), warm * 0.8)
            sky_bottom = self._lerp_color((210, 230, 255), (255, 130, 90), warm)
            body_color = self._lerp_color((255, 230, 160), (255, 200, 120), warm)
            glow_color = None
        else:
            t = (hour - 18) / 12.0 if hour >= 18 else (hour + 6) / 12.0
            sky_top = (18, 28, 60)
            sky_bottom = (60, 80, 120)
            body_color = (220, 230, 255)
            glow_color = (160, 190, 255, 70)

        t = max(0.0, min(1.0, t))
        bg = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        bg_draw = ImageDraw.Draw(bg)
        for y in range(size):
            line_t = y / max(size - 1, 1)
            color = self._lerp_color(sky_top, sky_bottom, line_t)
            bg_draw.line((0, y, size, y), fill=color)

        radius = max(8, int(size * 0.2))
        arc_x = int(size * 0.12 + t * size * 0.76)
        arc_y = int(size * 0.75 - math.sin(t * math.pi) * size * 0.45)

        if glow_color:
            glow_r = int(radius * 1.7)
            bg_draw.ellipse(
                (arc_x - glow_r, arc_y - glow_r, arc_x + glow_r, arc_y + glow_r),
                fill=glow_color,
            )

        if is_day:
            ray_len = int(radius * 0.9)
            ray_width = max(4, int(radius * 0.35))
            rays = 10
            for idx in range(rays):
                angle = (2 * math.pi / rays) * idx
                outer = (
                    arc_x + math.cos(angle) * (radius + ray_len),
                    arc_y + math.sin(angle) * (radius + ray_len),
                )
                left = (
                    arc_x + math.cos(angle - 0.25) * (radius + ray_width),
                    arc_y + math.sin(angle - 0.25) * (radius + ray_width),
                )
                right = (
                    arc_x + math.cos(angle + 0.25) * (radius + ray_width),
                    arc_y + math.sin(angle + 0.25) * (radius + ray_width),
                )
                bg_draw.polygon([left, outer, right], fill=body_color)

        bg_draw.ellipse(
            (arc_x - radius, arc_y - radius, arc_x + radius, arc_y + radius),
            fill=body_color,
        )

        if is_day:
            cloud_color = (255, 255, 255, 190)
            for offset in (0.15, 0.55):
                cx = int(size * (0.2 + offset))
                cy = int(size * 0.58)
                w = int(size * 0.28)
                h = int(size * 0.16)
                bg_draw.ellipse((cx, cy, cx + w, cy + h), fill=cloud_color)
                bg_draw.ellipse(
                    (cx + int(w * 0.2), cy - int(h * 0.4), cx + int(w * 0.7), cy + int(h * 0.6)),
                    fill=cloud_color,
                )
        else:
            for idx in range(12):
                sx = int((idx * 17 + 13) % size)
                sy = int((idx * 29 + 7) % int(size * 0.6))
                bg_draw.ellipse((sx, sy, sx + 2, sy + 2), fill=(230, 240, 255, 180))

        fg_color = (20, 26, 36, 140) if is_day else (10, 14, 24, 180)
        horizon = int(size * 0.72)
        bg_draw.rounded_rectangle(
            (int(size * 0.08), horizon, size, size),
            radius=int(size * 0.25),
            fill=fg_color,
        )

        mask = Image.new("L", (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle(
            (0, 0, size - 1, size - 1), radius=int(size * 0.28), fill=255
        )
        icon = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        icon.paste(bg, (0, 0), mask)
        border = ImageDraw.Draw(icon)
        border.rounded_rectangle(
            (0, 0, size - 1, size - 1),
            radius=int(size * 0.28),
            outline=(255, 255, 255, 150),
            width=max(1, int(size * 0.03)),
        )
        return icon

    @classmethod
    def _assets_path(cls, filename: str) -> str:
        return os.path.join(cls._assets_dir(), filename)

    @staticmethod
    def _asset_url(filename: str) -> str:
        base = ASSETS_BASE_URL.rstrip("/")
        name = filename.lstrip("/")
        return f"{base}/{name}"

    def _resolve_media_url(self, value: str) -> str:
        if not value:
            return ""
        return value if re.match(r"^https?://", value, flags=re.IGNORECASE) else self._asset_url(value)

    @staticmethod
    def _is_video_name(value: str) -> bool:
        if not value:
            return False
        clean = value.split("?", 1)[0].split("#", 1)[0]
        ext = os.path.splitext(clean)[1].lower()
        return ext in VIDEO_EXTS

    @staticmethod
    def _is_video_message(source: Message) -> bool:
        if not source:
            return False
        if getattr(source, "video", None):
            return True
        file = getattr(source, "file", None)
        mime = getattr(file, "mime_type", "") if file else ""
        if mime.startswith("video/"):
            return True
        ext = (getattr(file, "ext", "") or "").lower() if file else ""
        if ext and ext in VIDEO_EXTS:
            return True
        name = getattr(file, "name", "") if file else ""
        if name and ServMod._is_video_name(name):
            return True
        return False

    async def _answer_text(self, message: Message, text: str):
        if getattr(message, "out", False) and not message.via_bot_id and not message.fwd_from:
            try:
                return await message.edit(text, link_preview=False)
            except Exception:
                pass
        return await message.respond(text, link_preview=False)

    @classmethod
    def _ensure_font_asset(cls) -> typing.Optional[str]:
        path = cls._assets_path(FONT_ASSET_NAME)
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

            raw = DEFAULT_FONT_B64.strip()
            if raw:
                try:
                    data = base64.b64decode("".join(raw.split()))
                except Exception:
                    data = None
                if data:
                    os.makedirs(cls._assets_dir(), exist_ok=True)
                    with open(path, "wb") as handle:
                        handle.write(data)
                    return path

        return path if os.path.isfile(path) else None

    @classmethod
    def _save_background_asset(cls, raw: bytes, filename: str) -> str:
        image = Image.open(io.BytesIO(raw)).convert("RGB")
        max_side = 1200
        if max(image.width, image.height) > max_side:
            scale = max_side / max(image.width, image.height)
            image = image.resize(
                (int(image.width * scale), int(image.height * scale)), Image.LANCZOS
            )
        os.makedirs(cls._assets_dir(), exist_ok=True)
        path = cls._assets_path(filename)
        image.save(path, format="JPEG", quality=80, optimize=True, progressive=True)
        return path

    @classmethod
    def _save_background_video(cls, input_path: str, filename: str) -> str:
        os.makedirs(cls._assets_dir(), exist_ok=True)
        path = cls._assets_path(filename)
        cmd = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-i",
            input_path,
            "-an",
            "-vf",
            "scale='min(720,iw)':-2",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "28",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            path,
        ]
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            err = proc.stderr.decode(errors="ignore").strip() or "ffmpeg failed"
            raise RuntimeError(ServMod._shorten_log(err))
        return path

    @staticmethod
    async def _pick_media_source(
        message: Message, reply: typing.Optional[Message]
    ) -> typing.Optional[Message]:
        for source in (message, reply):
            if source and source.media:
                return source
        return None

    @staticmethod
    async def _download_media_to_path(source: Message) -> typing.Optional[str]:
        if not source:
            return None
        tmp_handle = None
        try:
            tmp_handle = tempfile.NamedTemporaryFile(prefix="serv_", delete=False)
            tmp_path = tmp_handle.name
            tmp_handle.close()
            result = await source.download_media(file=tmp_path)
            if isinstance(result, (bytes, bytearray)):
                with open(tmp_path, "wb") as handle:
                    handle.write(result)
            elif isinstance(result, str) and result != tmp_path:
                if os.path.exists(result):
                    os.replace(result, tmp_path)
            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                return tmp_path
        except Exception:
            pass
        finally:
            if tmp_handle:
                try:
                    tmp_handle.close()
                except Exception:
                    pass
        return None

    @staticmethod
    def _get_os_name() -> str:
        try:
            with open("/etc/os-release", "r", encoding="utf-8") as handle:
                for line in handle:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=", 1)[1].strip().strip('"')
        except Exception:
            pass
        return platform.system() or "Unknown OS"

    @staticmethod
    def _clean_cpu_name(name: str) -> str:
        cleaned = re.sub(r"\(tm\)", "", name, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bprocessor\b", "", cleaned, flags=re.IGNORECASE)
        return " ".join(cleaned.split()).strip()

    @staticmethod
    def _get_cpu_name() -> str:
        try:
            with open("/proc/cpuinfo", "r", encoding="utf-8") as handle:
                for line in handle:
                    if line.lower().startswith("model name"):
                        return ServMod._clean_cpu_name(line.split(":", 1)[1].strip())
        except Exception:
            pass
        return ServMod._clean_cpu_name(
            platform.processor() or platform.machine() or "Unknown CPU"
        )

    @staticmethod
    def _format_bytes(value: float) -> str:
        size = float(value)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if size < 1024 or unit == "TB":
                if unit == "B":
                    return f"{int(size)} {unit}"
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    @staticmethod
    def _read_proc_stat() -> typing.Optional[typing.Tuple[int, int]]:
        try:
            with open("/proc/stat", "r", encoding="utf-8") as handle:
                line = handle.readline()
            if not line.startswith("cpu"):
                return None
            parts = line.split()
            values = []
            for val in parts[1:]:
                try:
                    values.append(int(val))
                except ValueError:
                    return None
            if len(values) < 4:
                return None
            idle = values[3] + (values[4] if len(values) > 4 else 0)
            total = sum(values)
            return total, idle
        except Exception:
            return None

    @classmethod
    def _get_cpu_percent(cls) -> float:
        value: typing.Optional[float] = None
        try:
            value = psutil.cpu_percent(interval=0.3)
        except Exception:
            value = None

        if value is None or value <= 0:
            stat1 = cls._read_proc_stat()
            if stat1:
                time.sleep(0.2)
                stat2 = cls._read_proc_stat()
                if stat2:
                    total_delta = stat2[0] - stat1[0]
                    idle_delta = stat2[1] - stat1[1]
                    if total_delta > 0:
                        value = (total_delta - idle_delta) / total_delta * 100.0

        if value is None:
            value = 0.0

        value = max(0.0, min(100.0, value))
        now = time.time()
        if value <= 0.0:
            if cls._cpu_cache:
                ts, cached = cls._cpu_cache
                if cached > 0 and now - ts < 5:
                    return cached
        else:
            cls._cpu_cache = (now, value)
        return value

    @staticmethod
    def _text_size(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> typing.Tuple[int, int]:
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
        path = ServMod._ensure_font_asset()
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
        name = f"serv_card_{uuid.uuid4().hex}{ext}"
        path = self._assets_path(name)
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

    def _get_gpu_info(self) -> typing.Tuple[str, str]:
        if GPU_NAME_OVERRIDE:
            return GPU_NAME_OVERRIDE, "N/A"

        cmd = [
            "nvidia-smi",
            "--query-gpu=name,utilization.gpu,memory.used,memory.total",
            "--format=csv,noheader,nounits",
        ]
        try:
            output = subprocess.check_output(
                cmd,
                stderr=subprocess.DEVNULL,
                timeout=1,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            try:
                output = subprocess.check_output(
                    ["lspci"],
                    stderr=subprocess.DEVNULL,
                    timeout=1,
                )
                for line in output.decode(errors="ignore").splitlines():
                    if re.search(r"(vga|3d|display)", line, re.IGNORECASE):
                        return line.split(":", 1)[1].strip(), "N/A"
            except Exception:
                pass
            return "N/A", "N/A"

        lines = output.decode(errors="ignore").strip().splitlines()
        if not lines:
            return "N/A", "N/A"

        parts = [part.strip() for part in lines[0].split(",")]
        name = parts[0] if parts else "N/A"
        usage = "N/A"
        if len(parts) >= 4:
            util, mem_used, mem_total = parts[1:4]
            usage = f"{util}% ({mem_used}/{mem_total} MB)"
        elif len(parts) >= 2:
            usage = f"{parts[1]}%"

        return name, usage

    def _load_background(self) -> Image.Image:
        source = (self.config["background_url"] or "").strip()
        if not source:
            raise ValueError("background_url is empty")
        if self._is_video_name(source):
            raise ValueError("background_url points to video")

        data = None
        is_url = bool(re.match(r"^https?://", source, flags=re.IGNORECASE))
        url = source if is_url else self._asset_url(source)
        asset_name = ""
        asset_path = ""
        if is_url:
            base = ASSETS_BASE_URL.rstrip("/")
            if url.startswith(base + "/"):
                asset_name = url[len(base) + 1 :]
                asset_path = self._assets_path(asset_name)
                if os.path.isfile(asset_path):
                    with open(asset_path, "rb") as handle:
                        data = handle.read()
                    return Image.open(io.BytesIO(data)).convert("RGBA")
        try:
            response = requests.get(url, timeout=20)
            response.raise_for_status()
            data = response.content
        except Exception as exc:
            if not is_url:
                path = self._assets_path(source)
                if not os.path.isfile(path):
                    raise ValueError(f"background asset not found: {path}") from exc
                with open(path, "rb") as handle:
                    data = handle.read()
            else:
                if asset_path and os.path.isfile(asset_path):
                    with open(asset_path, "rb") as handle:
                        data = handle.read()
                else:
                    raise ValueError(f"background_url fetch failed: {exc}") from exc

        return Image.open(io.BytesIO(data)).convert("RGBA")

    def _load_background_video(self, source: str) -> typing.Tuple[str, bool]:
        is_url = bool(re.match(r"^https?://", source, flags=re.IGNORECASE))
        if not is_url:
            return self._assets_path(source), False
        base = ASSETS_BASE_URL.rstrip("/")
        if source.startswith(base + "/"):
            name = source[len(base) + 1 :]
            path = self._assets_path(name)
            if os.path.isfile(path):
                return path, False

        tmp = tempfile.NamedTemporaryFile(prefix="serv_video_", delete=False)
        tmp_path = tmp.name
        tmp.close()
        try:
            response = requests.get(source, stream=True, timeout=30)
            response.raise_for_status()
            with open(tmp_path, "wb") as handle:
                for chunk in response.iter_content(chunk_size=1024 * 256):
                    if chunk:
                        handle.write(chunk)
        except Exception as exc:
            self._last_video_log = self._shorten_log(f"video download failed: {exc}")
            raise
        return tmp_path, True

    def _extract_video_frame(self, path: str) -> Image.Image:
        proc = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-y",
                "-i",
                path,
                "-frames:v",
                "1",
                "-f",
                "image2pipe",
                "-vcodec",
                "png",
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if proc.returncode != 0:
            err = proc.stderr.decode(errors="ignore").strip() or "ffmpeg failed"
            err = self._shorten_log(err)
            self._last_video_log = f"frame extract failed: {err}"
            raise RuntimeError("ffmpeg failed")
        return Image.open(io.BytesIO(proc.stdout)).convert("RGBA")

    def _draw_kv_list(
        self,
        draw: ImageDraw.ImageDraw,
        items: typing.List[typing.Tuple[str, str]],
        font: ImageFont.ImageFont,
        x: int,
        y: int,
        max_width: int,
        line_gap: int,
        label_color: typing.Tuple[int, int, int, int],
        value_color: typing.Tuple[int, int, int, int],
        pill_color: typing.Optional[typing.Tuple[int, int, int, int]] = None,
        pill_radius: typing.Optional[int] = None,
        pill_pad_x: int = 0,
        pill_pad_y: int = 0,
    ) -> int:
        if not items:
            return y

        label_width = max(
            self._text_size(draw, f"{label}:", font)[0] for label, _ in items
        )
        label_pad = int(font.size * 0.4)
        value_x = x + label_width + label_pad
        value_max = max_width - (value_x - x)
        row_step = font.size + line_gap + (pill_pad_y * 2 if pill_color else 0)

        for label, value in items:
            label_text = f"{label}:"
            lines = self._wrap_lines(draw, value, font, value_max)
            for index, line in enumerate(lines):
                if pill_color:
                    pill_top = y
                    pill_bottom = y + font.size + pill_pad_y * 2
                    pill_left = x - pill_pad_x
                    pill_right = x + max_width + pill_pad_x
                    radius = pill_radius or max(8, int((pill_bottom - pill_top) * 0.45))
                    self._draw_pill(
                        draw,
                        (pill_left, pill_top, pill_right, pill_bottom),
                        pill_color,
                        radius,
                    )
                text_y = y + (pill_pad_y if pill_color else 0)
                if index == 0:
                    draw.text(
                        (x, text_y),
                        label_text,
                        font=font,
                        fill=label_color,
                        anchor="lt",
                        stroke_width=1,
                        stroke_fill=(0, 0, 0, 160),
                    )
                draw.text(
                    (value_x, text_y),
                    line,
                    font=font,
                    fill=value_color,
                    anchor="lt",
                    stroke_width=1,
                    stroke_fill=(0, 0, 0, 160),
                )
                y += row_step

        return y

    def _estimate_list_height(
        self,
        draw: ImageDraw.ImageDraw,
        items: typing.List[typing.Tuple[str, str]],
        font: ImageFont.ImageFont,
        max_width: int,
        line_gap: int,
        pill_pad_y: int = 0,
    ) -> int:
        if not items:
            return 0

        label_width = max(
            self._text_size(draw, f"{label}:", font)[0] for label, _ in items
        )
        label_pad = int(font.size * 0.4)
        value_x = label_width + label_pad
        value_max = max(1, max_width - value_x)

        total = 0
        row_step = font.size + line_gap + (pill_pad_y * 2 if pill_pad_y else 0)
        for _, value in items:
            lines = self._wrap_lines(draw, value, font, value_max)
            count = max(1, len(lines))
            total += count * row_step
        return total

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
            output.name = "serv.jpg"
            output.seek(0)
            return output
        except Exception:
            output = io.BytesIO()
            rgb.save(output, format="JPEG", quality=82, optimize=True, progressive=True)
            output.name = "serv.jpg"
            output.seek(0)
            return output

    def _build_card(self, ping_ms: float) -> io.BytesIO:
        source = self._load_background()
        photo = self._center_crop_square(source)
        photo_side = self._target_side()
        if photo.width != photo_side:
            photo = photo.resize((photo_side, photo_side), Image.LANCZOS)

        panel_width = int(photo_side * 1.15)
        total_width = panel_width + photo_side
        total_height = photo_side

        palette = self._md3_palette(photo)
        panel_color = palette["surface_mid"]
        accent_color = palette["primary"]
        text_color = palette["text"]
        muted_color = palette["muted"]
        pill_color = palette["surface_hi"]

        image = Image.new("RGBA", (total_width, total_height), panel_color)
        image.paste(photo, (panel_width, 0))

        transition = self._clamp(int(photo_side * 0.12), 28, 140)
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        for idx in range(transition):
            alpha = int(panel_color[3] * (1 - idx / max(transition - 1, 1)))
            x = panel_width + idx
            if x >= total_width:
                break
            overlay_draw.line(
                (x, 0, x, total_height),
                fill=(panel_color[0], panel_color[1], panel_color[2], alpha),
            )
        image = Image.alpha_composite(image, overlay)
        draw = ImageDraw.Draw(image)

        margin = int(photo_side * 0.08)
        title_font = self._load_font(self._clamp(int(photo_side * 0.12), 30, 92))
        label_font = self._load_font(self._clamp(int(photo_side * 0.04), 12, 36))
        value_font = self._load_font(self._clamp(int(photo_side * 0.052), 13, 40))
        line_gap = int(value_font.size * 0.32)
        pill_pad_x = int(value_font.size * 0.5)
        pill_pad_y = int(value_font.size * 0.22)
        pill_radius = int(value_font.size * 0.9)
        label_pad_x = int(label_font.size * 0.6)
        label_pad_y = int(label_font.size * 0.32)
        label_radius = int(label_font.size * 0.9)

        now = time.localtime()
        greeting = self._get_greeting(now)
        base_name = (self.config["server_name"] or "").strip() or "Server"
        server_name = f"{base_name} | {ping_ms:.0f}ms"
        status_label = self.config["label_status"].strip() or "STATUS"

        cpu_percent = self._get_cpu_percent()
        gpu_name, _ = self._get_gpu_info()
        mem = psutil.virtual_memory()

        items = [
            (self.config["label_cpu"], f"{cpu_percent:.2f}%"),
            (
                self.config["label_ram"],
                f"{self._format_bytes(mem.used)} / {self._format_bytes(mem.total)}",
            ),
            (self.config["label_uptime"], self._format_uptime(utils.uptime())),
        ]
        component_items = [
            (self.config["label_cpu"], self._get_cpu_name()),
            (self.config["label_gpu"], gpu_name),
        ]

        greeting_font_size = self._clamp(int(photo_side * 0.075), 22, 62)
        greeting_font = self._load_font(greeting_font_size)
        icon_size = self._clamp(int(greeting_font_size * 1.35), 40, 86)
        icon = self._build_sky_icon(icon_size, now)
        gap = int(icon_size * 0.18)
        max_width = panel_width - margin * 2 - icon_size - gap
        text_w, text_h = self._text_size(draw, greeting, greeting_font)
        while text_w > max_width and greeting_font_size > 16:
            greeting_font_size -= 1
            greeting_font = self._load_font(greeting_font_size)
            text_w, text_h = self._text_size(draw, greeting, greeting_font)

        greeting_pad_x = int(greeting_font.size * 0.5)
        greeting_pad_y = int(greeting_font.size * 0.3)
        greeting_pill_h = text_h + greeting_pad_y * 2
        greeting_block_h = max(icon_size, greeting_pill_h)
        name_pad_x = int(title_font.size * 0.5)
        name_pad_y = int(title_font.size * 0.25)
        name_pill_h = title_font.size + name_pad_y * 2

        content_height = 0
        content_height += greeting_block_h
        content_height += int(label_font.size * 0.6)
        content_height += name_pill_h + int(title_font.size * 0.4)
        content_height += label_font.size + label_pad_y * 2 + int(label_font.size * 0.4)
        content_height += self._estimate_list_height(
            draw,
            items,
            value_font,
            panel_width - margin * 2,
            line_gap,
            pill_pad_y,
        )
        content_height += int(value_font.size * 0.4)
        content_height += label_font.size + label_pad_y * 2 + int(label_font.size * 0.4)
        content_height += self._estimate_list_height(
            draw,
            component_items,
            value_font,
            panel_width - margin * 2,
            line_gap,
            pill_pad_y,
        )

        y = max(margin, (total_height - content_height) // 2)
        icon_y = y + max(0, (greeting_block_h - icon_size) // 2)
        image.paste(icon, (margin, icon_y), icon)
        text_x = margin + icon_size + gap
        greeting_pill_y = y + max(0, (greeting_block_h - greeting_pill_h) // 2)
        greeting_pill_right = panel_width - margin
        self._draw_pill(
            draw,
            (text_x, greeting_pill_y, greeting_pill_right, greeting_pill_y + greeting_pill_h),
            palette["surface_hi"],
            max(10, int(greeting_pill_h * 0.5)),
        )
        draw.text(
            (text_x + greeting_pad_x, greeting_pill_y + greeting_pad_y),
            greeting,
            font=greeting_font,
            fill=text_color,
            anchor="lt",
            stroke_width=2,
            stroke_fill=(0, 0, 0, 180),
        )
        y += greeting_block_h + int(label_font.size * 0.6)
        self._draw_pill(
            draw,
            (margin, y, panel_width - margin, y + name_pill_h),
            pill_color,
            max(12, int(name_pill_h * 0.5)),
        )
        draw.text(
            (margin + name_pad_x, y + name_pad_y),
            server_name,
            font=title_font,
            fill=text_color,
            anchor="lt",
            stroke_width=2,
            stroke_fill=(0, 0, 0, 180),
        )
        y += name_pill_h + int(title_font.size * 0.4)
        status_w, status_h = self._text_size(draw, status_label, label_font)
        status_pill_right = min(
            panel_width - margin,
            margin + status_w + label_pad_x * 2,
        )
        status_pill_h = status_h + label_pad_y * 2
        self._draw_pill(
            draw,
            (
                margin,
                y,
                status_pill_right,
                y + status_pill_h,
            ),
            palette["surface_hi"],
            label_radius,
        )
        draw.text(
            (margin + label_pad_x, y + label_pad_y),
            status_label,
            font=label_font,
            fill=accent_color,
            anchor="lt",
            stroke_width=1,
            stroke_fill=(0, 0, 0, 140),
        )
        y += status_pill_h + int(label_font.size * 0.4)

        y = self._draw_kv_list(
            draw,
            items,
            value_font,
            margin,
            y,
            panel_width - margin * 2,
            line_gap,
            muted_color,
            text_color,
            pill_color,
            pill_radius,
            pill_pad_x,
            pill_pad_y,
        )

        y += int(value_font.size * 0.4)
        components_label = self.config["label_components"].strip() or "COMPONENTS"
        comp_w, comp_h = self._text_size(draw, components_label, label_font)
        comp_pill_right = min(
            panel_width - margin,
            margin + comp_w + label_pad_x * 2,
        )
        comp_pill_h = comp_h + label_pad_y * 2
        self._draw_pill(
            draw,
            (
                margin,
                y,
                comp_pill_right,
                y + comp_pill_h,
            ),
            palette["surface_hi"],
            label_radius,
        )
        draw.text(
            (margin + label_pad_x, y + label_pad_y),
            components_label,
            font=label_font,
            fill=accent_color,
            anchor="lt",
            stroke_width=1,
            stroke_fill=(0, 0, 0, 140),
        )
        y += comp_pill_h + int(label_font.size * 0.4)
        self._draw_kv_list(
            draw,
            component_items,
            value_font,
            margin,
            y,
            panel_width - margin * 2,
            line_gap,
            muted_color,
            text_color,
            pill_color,
            pill_radius,
            pill_pad_x,
            pill_pad_y,
        )

        return self._encode_output(image)

    def _build_video_card(self, source: str, ping_ms: float) -> io.BytesIO:
        video_path, cleanup = self._load_background_video(source)
        overlay_path = None
        try:
            frame = self._extract_video_frame(video_path)
            photo = self._center_crop_square(frame)
            photo_side = self._target_side()
            if photo.width != photo_side:
                photo = photo.resize((photo_side, photo_side), Image.LANCZOS)

            if photo_side % 2:
                photo_side -= 1
            panel_width = int(photo_side * 1.15)
            if panel_width % 2:
                panel_width += 1
            total_width = panel_width + photo_side
            if total_width % 2:
                total_width += 1
            total_height = photo_side

            palette = self._md3_palette(photo)
            panel_color = palette["surface_mid"]
            accent_color = palette["primary"]
            text_color = palette["text"]
            muted_color = palette["muted"]
            pill_color = palette["surface_hi"]

            overlay = Image.new("RGBA", (total_width, total_height), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle((0, 0, panel_width, total_height), fill=panel_color)
            transition = self._clamp(int(photo_side * 0.12), 28, 140)
            for idx in range(transition):
                alpha = int(panel_color[3] * (1 - idx / max(transition - 1, 1)))
                x = panel_width + idx
                if x >= total_width:
                    break
                overlay_draw.line(
                    (x, 0, x, total_height),
                    fill=(panel_color[0], panel_color[1], panel_color[2], alpha),
                )

            margin = int(photo_side * 0.08)
            title_font = self._load_font(self._clamp(int(photo_side * 0.12), 30, 92))
            label_font = self._load_font(self._clamp(int(photo_side * 0.04), 12, 36))
            value_font = self._load_font(self._clamp(int(photo_side * 0.052), 13, 40))
            line_gap = int(value_font.size * 0.32)
            pill_pad_x = int(value_font.size * 0.5)
            pill_pad_y = int(value_font.size * 0.22)
            pill_radius = int(value_font.size * 0.9)
            label_pad_x = int(label_font.size * 0.6)
            label_pad_y = int(label_font.size * 0.32)
            label_radius = int(label_font.size * 0.9)

            now = time.localtime()
            greeting = self._get_greeting(now)
            base_name = (self.config["server_name"] or "").strip() or "Server"
            server_name = f"{base_name} | {ping_ms:.0f}ms"
            status_label = self.config["label_status"].strip() or "STATUS"

            cpu_percent = self._get_cpu_percent()
            gpu_name, _ = self._get_gpu_info()
            mem = psutil.virtual_memory()

            items = [
                (self.config["label_cpu"], f"{cpu_percent:.2f}%"),
                (
                    self.config["label_ram"],
                    f"{self._format_bytes(mem.used)} / {self._format_bytes(mem.total)}",
                ),
                (self.config["label_uptime"], self._format_uptime(utils.uptime())),
            ]
            component_items = [
                (self.config["label_cpu"], self._get_cpu_name()),
                (self.config["label_gpu"], gpu_name),
            ]

            greeting_font_size = self._clamp(int(photo_side * 0.075), 22, 62)
            greeting_font = self._load_font(greeting_font_size)
            icon_size = self._clamp(int(greeting_font_size * 1.35), 40, 86)
            icon = self._build_sky_icon(icon_size, now)
            gap = int(icon_size * 0.18)
            max_width = panel_width - margin * 2 - icon_size - gap
            text_w, text_h = self._text_size(overlay_draw, greeting, greeting_font)
            while text_w > max_width and greeting_font_size > 16:
                greeting_font_size -= 1
                greeting_font = self._load_font(greeting_font_size)
                text_w, text_h = self._text_size(overlay_draw, greeting, greeting_font)

            greeting_pad_x = int(greeting_font.size * 0.5)
            greeting_pad_y = int(greeting_font.size * 0.3)
            greeting_pill_h = text_h + greeting_pad_y * 2
            greeting_block_h = max(icon_size, greeting_pill_h)
            name_pad_x = int(title_font.size * 0.5)
            name_pad_y = int(title_font.size * 0.25)
            name_pill_h = title_font.size + name_pad_y * 2

            content_height = 0
            content_height += greeting_block_h
            content_height += int(label_font.size * 0.6)
            content_height += name_pill_h + int(title_font.size * 0.4)
            content_height += label_font.size + label_pad_y * 2 + int(label_font.size * 0.4)
            content_height += self._estimate_list_height(
                overlay_draw,
                items,
                value_font,
                panel_width - margin * 2,
                line_gap,
                pill_pad_y,
            )
            content_height += int(value_font.size * 0.4)
            content_height += label_font.size + label_pad_y * 2 + int(label_font.size * 0.4)
            content_height += self._estimate_list_height(
                overlay_draw,
                component_items,
                value_font,
                panel_width - margin * 2,
                line_gap,
                pill_pad_y,
            )

            y = max(margin, (total_height - content_height) // 2)
            icon_y = y + max(0, (greeting_block_h - icon_size) // 2)
            overlay.paste(icon, (margin, icon_y), icon)
            text_x = margin + icon_size + gap
            greeting_pill_y = y + max(0, (greeting_block_h - greeting_pill_h) // 2)
            greeting_pill_right = panel_width - margin
            self._draw_pill(
                overlay_draw,
                (
                    text_x,
                    greeting_pill_y,
                    greeting_pill_right,
                    greeting_pill_y + greeting_pill_h,
                ),
                palette["surface_hi"],
                max(10, int(greeting_pill_h * 0.5)),
            )
            overlay_draw.text(
                (text_x + greeting_pad_x, greeting_pill_y + greeting_pad_y),
                greeting,
                font=greeting_font,
                fill=text_color,
                anchor="lt",
                stroke_width=2,
                stroke_fill=(0, 0, 0, 180),
            )
            y += greeting_block_h + int(label_font.size * 0.6)
            self._draw_pill(
                overlay_draw,
                (margin, y, panel_width - margin, y + name_pill_h),
                pill_color,
                max(12, int(name_pill_h * 0.5)),
            )
            overlay_draw.text(
                (margin + name_pad_x, y + name_pad_y),
                server_name,
                font=title_font,
                fill=text_color,
                anchor="lt",
                stroke_width=2,
                stroke_fill=(0, 0, 0, 180),
            )
            y += name_pill_h + int(title_font.size * 0.4)
            status_w, status_h = self._text_size(overlay_draw, status_label, label_font)
            status_pill_right = min(
                panel_width - margin,
                margin + status_w + label_pad_x * 2,
            )
            status_pill_h = status_h + label_pad_y * 2
            self._draw_pill(
                overlay_draw,
                (
                    margin,
                    y,
                    status_pill_right,
                    y + status_pill_h,
                ),
                palette["surface_hi"],
                label_radius,
            )
            overlay_draw.text(
                (margin + label_pad_x, y + label_pad_y),
                status_label,
                font=label_font,
                fill=accent_color,
                anchor="lt",
                stroke_width=1,
                stroke_fill=(0, 0, 0, 140),
            )
            y += status_pill_h + int(label_font.size * 0.4)

            y = self._draw_kv_list(
                overlay_draw,
                items,
                value_font,
                margin,
                y,
                panel_width - margin * 2,
                line_gap,
                muted_color,
                text_color,
                pill_color,
                pill_radius,
                pill_pad_x,
                pill_pad_y,
            )

            y += int(value_font.size * 0.4)
            components_label = self.config["label_components"].strip() or "COMPONENTS"
            comp_w, comp_h = self._text_size(overlay_draw, components_label, label_font)
            comp_pill_right = min(
                panel_width - margin,
                margin + comp_w + label_pad_x * 2,
            )
            comp_pill_h = comp_h + label_pad_y * 2
            self._draw_pill(
                overlay_draw,
                (
                    margin,
                    y,
                    comp_pill_right,
                    y + comp_pill_h,
                ),
                palette["surface_hi"],
                label_radius,
            )
            overlay_draw.text(
                (margin + label_pad_x, y + label_pad_y),
                components_label,
                font=label_font,
                fill=accent_color,
                anchor="lt",
                stroke_width=1,
                stroke_fill=(0, 0, 0, 140),
            )
            y += comp_pill_h + int(label_font.size * 0.4)
            self._draw_kv_list(
                overlay_draw,
                component_items,
                value_font,
                margin,
                y,
                panel_width - margin * 2,
                line_gap,
                muted_color,
                text_color,
                pill_color,
                pill_radius,
                pill_pad_x,
                pill_pad_y,
            )

            overlay_tmp = tempfile.NamedTemporaryFile(prefix="serv_overlay_", suffix=".png", delete=False)
            overlay_path = overlay_tmp.name
            overlay_tmp.close()
            overlay.save(overlay_path, format="PNG")

            audio_url = (self.config["video_audio_url"] or "").strip()
            audio_path = None
            audio_cleanup = False
            audio_specs: typing.List[typing.Tuple[str, str, typing.Optional[str]]] = []
            if audio_url:
                try:
                    resolved = self._resolve_media_url(audio_url)
                    tmp_audio = tempfile.NamedTemporaryFile(prefix="serv_audio_", delete=False)
                    audio_path = tmp_audio.name
                    tmp_audio.close()
                    response = requests.get(resolved, stream=True, timeout=30)
                    response.raise_for_status()
                    with open(audio_path, "wb") as handle:
                        for chunk in response.iter_content(chunk_size=1024 * 256):
                            if chunk:
                                handle.write(chunk)
                    audio_cleanup = True
                    audio_specs.append(("file", audio_path, None))
                except Exception as exc:
                    self._last_video_log = self._shorten_log(f"audio download failed: {exc}")

            if not audio_specs:
                audio_specs = [
                    ("lavfi", "anoisesrc=color=white:amplitude=0.001:sample_rate=44100", "volume=0.01"),
                    ("lavfi", "anullsrc=channel_layout=stereo:sample_rate=44100", None),
                ]

            filter_complex = (
                f"[0:v]scale={photo_side}:{photo_side}:force_original_aspect_ratio=increase,"
                f"crop={photo_side}:{photo_side},setsar=1[vid];"
                f"[vid]pad={total_width}:{total_height}:{panel_width}:0:color=0x00000000[base];"
                f"[base][1:v]overlay=0:0:format=auto[v]"
            )

            last_error = None
            for kind, spec, afilter in audio_specs:
                cmd = [
                    "ffmpeg",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-y",
                    "-i",
                    video_path,
                    "-i",
                    overlay_path,
                ]
                if kind == "file":
                    cmd += ["-stream_loop", "-1", "-i", spec]
                else:
                    cmd += ["-f", "lavfi", "-i", spec]

                cmd += [
                    "-filter_complex",
                    filter_complex,
                    "-map",
                    "[v]",
                    "-map",
                    "2:a",
                    "-shortest",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "26",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "64k",
                    "-ac",
                    "2",
                    "-ar",
                    "44100",
                ]
                if afilter:
                    cmd += ["-af", afilter]
                cmd += [
                    "-movflags",
                    "+frag_keyframe+empty_moov+default_base_moof",
                    "-f",
                    "mp4",
                    "pipe:1",
                ]

                proc = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                if proc.returncode == 0:
                    output = io.BytesIO(proc.stdout)
                    output.name = "serv.mp4"
                    output.seek(0)
                    return output

                err = proc.stderr.decode(errors="ignore").strip() or "ffmpeg failed"
                last_error = self._shorten_log(err)

            self._last_video_log = f"render failed: {last_error or 'ffmpeg failed'}"
            raise RuntimeError("ffmpeg failed")
        except Exception as exc:
            if not self._last_video_log:
                self._last_video_log = self._shorten_log(f"{type(exc).__name__}: {exc}")
            raise
        finally:
            if overlay_path:
                try:
                    os.remove(overlay_path)
                except Exception:
                    pass
            if "audio_cleanup" in locals() and audio_cleanup and audio_path:
                try:
                    os.remove(audio_path)
                except Exception:
                    pass
            if cleanup:
                try:
                    os.remove(video_path)
                except Exception:
                    pass

    @staticmethod
    def _format_uptime(seconds: int) -> str:
        days, rem = divmod(seconds, 86400)
        hours, rem = divmod(rem, 3600)
        minutes, secs = divmod(rem, 60)
        parts = []
        if days:
            parts.append(f"{days}d")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}m")
        if secs or not parts:
            parts.append(f"{secs}s")
        return " ".join(parts)

    @loader.command(ru_doc="Render a server status card")
    async def serv(self, message: Message):
        args = utils.get_args_raw(message).strip().lower()
        if args == "set":
            reply = await message.get_reply_message() if message.is_reply else None
            source = await self._pick_media_source(message, reply)
            if not source:
                await self._answer_text(message, "Ответь на фото или приложи фото.")
                return
            tmp_path = None
            try:
                tmp_path = await self._download_media_to_path(source)
                if not tmp_path:
                    raise ValueError("no media")
                is_video = self._is_video_message(source)
                if is_video:
                    filename = f"serv_{uuid.uuid4().hex}.mp4"
                    self._save_background_video(tmp_path, filename)
                else:
                    filename = f"serv_{uuid.uuid4().hex}.jpg"
                    with open(tmp_path, "rb") as handle:
                        raw = handle.read()
                    self._save_background_asset(raw, filename)
            except Exception as exc:
                err_text = self._shorten_log(str(exc)) if exc else ""
                err_text = utils.escape_html(err_text) if err_text else ""
                await self._answer_text(
                    message,
                    "Не удалось обработать медиа."
                    + (f"\nLogs:\n{err_text}" if err_text else ""),
                )
                return
            finally:
                try:
                    if tmp_path:
                        os.remove(tmp_path)
                except Exception:
                    pass
            url = self._asset_url(filename)
            self.config["background_url"] = url
            await self._answer_text(
                message,
                f"Фон обновлен: {utils.escape_html(filename)}",
            )
            return

        start = time.perf_counter()
        message = await utils.answer(message, "❤️")
        ping_ms = (time.perf_counter() - start) * 1000
        source = (self.config["background_url"] or "").strip()
        self._last_video_log = None
        try:
            if source and self._is_video_name(source):
                image = self._build_video_card(source, ping_ms)
            else:
                image = self._build_card(ping_ms)
        except ValueError as exc:
            err_text = str(exc).strip()
            if err_text in ("background_url is empty", "background_url points to video"):
                await self._answer_text(
                    message,
                    "Set background_url in config first.",
                )
            else:
                safe = utils.escape_html(self._shorten_log(err_text)) if err_text else ""
                await self._answer_text(
                    message,
                    "Failed to render card."
                    + (f"\nLogs:\n{safe}" if safe else ""),
                )
            return
        except Exception:
            if source and self._is_video_name(source) and self._last_video_log:
                await self._answer_text(
                    message,
                    "Failed to render card."
                    f"\nLogs:\n{utils.escape_html(self._last_video_log)}",
                )
            else:
                await self._answer_text(message, "Failed to render card.")
            return

        await self._send_card(message, image, None)
