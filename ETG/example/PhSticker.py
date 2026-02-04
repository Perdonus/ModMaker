# -*- coding: utf-8 -*-
import io
import os
import requests
from PIL import Image, ImageDraw, ImageFont
from telethon.tl.types import Message
from .. import loader, utils


@loader.tds
class PhStickerMod(loader.Module):
    """Creates a PornHub style logo sticker."""

    strings = {
        "name": "PhSticker",
        "processing": "<b>⏳ Processing...</b>",
        "no_args": "<b>✖️ You must provide two words.</b>\n<b>Example:</b> <code>.phl Porn Hub</code>",
        "font_error": "<b>✖️ Failed to load font. Check your internet connection or URL accessibility.</b>",
    }

    strings_ru = {
        "_cls_doc": "Создает стикер в стиле логотипа PornHub.",
        "processing": "<b>⏳ Обработка...</b>",
        "no_args": "<b>✖️ Нужно указать два слова.</b>\n<b>Пример:</b> <code>.phl Porn Hub</code>",
        "font_error": "<b>✖️ Не удалось загрузить шрифт. Проверьте интернет-соединение или доступность URL.</b>",
    }

    def __init__(self):
        self.font = None  # can be BytesIO or str (path)
        self.font_size = 120
        self._loaded_font_url = None
        self._assets_dir = "/root/Heroku/assets"

        # Config: URL to the font and optional font size
        default_font_url = "http://91.233.168.135:5000/Unbounded-ExtraBold.ttf"
        try:
            # New-style config (Hikka)
            self.config = loader.ModuleConfig(
                loader.ConfigValue(
                    "FONT_URL",
                    default_font_url,
                    lambda: "URL шрифта (TTF/OTF), поддерживающего кириллицу",
                    validator=getattr(loader, "validators", None).Link()
                    if hasattr(loader, "validators")
                    else None,
                ),
                loader.ConfigValue(
                    "FONT_SIZE",
                    120,
                    lambda: "Размер шрифта",
                    validator=getattr(loader, "validators", None).Integer(minimum=20, maximum=300)
                    if hasattr(loader, "validators")
                    else None,
                ),
            )
        except Exception:
            # Fallback for very old loaders
            self.config = loader.ModuleConfig(
                "FONT_URL",
                default_font_url,
                "URL шрифта (TTF/OTF), поддерживающего кириллицу",
                "FONT_SIZE",
                120,
                "Размер шрифта",
            )

    def _alt_font_urls(self, url: str):
        urls = []
        if url:
            urls.append(url)

        # If it's a github.com URL, add raw.githubusercontent and jsDelivr alternatives
        try:
            if "github.com" in url:
                # To raw.githubusercontent.com
                # https://github.com/user/repo/raw/branch/path -> https://raw.githubusercontent.com/user/repo/branch/path
                parts = url.split("github.com/", 1)[1]
                parts = parts.split("/", 4)  # user, repo, 'raw', branch, path...
                if len(parts) >= 5 and parts[2] == "raw":
                    user, repo, _, branch, rest = parts[0], parts[1], parts[2], parts[3], parts[4]
                    urls.append(f"https://raw.githubusercontent.com/{user}/{repo}/{branch}/{rest}")
                    urls.append(f"https://cdn.jsdelivr.net/gh/{user}/{repo}@{branch}/{rest}")
        except Exception:
            pass

        # Deduplicate while preserving order
        seen = set()
        ordered = []
        for u in urls:
            if u and u not in seen:
                seen.add(u)
                ordered.append(u)
        return ordered

    def _local_asset_font(self, url: str) -> str:
        if not url:
            return ""
        name = os.path.basename(url)
        if not name:
            return ""
        path = os.path.join(self._assets_dir, name)
        return path if os.path.isfile(path) else ""

    def _local_fallback_fonts(self):
        names = ["Unbounded-ExtraBold.ttf", "font.ttf"]
        for name in names:
            path = os.path.join(self._assets_dir, name)
            if os.path.isfile(path):
                return path
        return ""

    async def _load_fallback_font_local(self) -> bool:
        asset_font = self._local_fallback_fonts()
        if asset_font:
            self.font = asset_font
            self._loaded_font_url = f"local:{os.path.basename(asset_font)}"
            return True

        # Try Pillow bundled DejaVu fonts (supports Cyrillic)
        try:
            pil_dir = os.path.dirname(ImageFont.__file__)  # .../PIL
            candidates = [
                os.path.join(pil_dir, "DejaVuSans-Bold.ttf"),
                os.path.join(pil_dir, "DejaVuSans.ttf"),
            ]
            for path in candidates:
                if os.path.isfile(path):
                    self.font = path  # keep as path string
                    self._loaded_font_url = f"local:{os.path.basename(path)}"
                    return True
        except Exception:
            pass

        # Last resort: PIL default bitmap font (not ideal, but avoids failure)
        try:
            # Keep a sentinel that indicates using load_default in generator
            self.font = "PIL_DEFAULT_FONT"
            self._loaded_font_url = "local:PIL_DEFAULT_FONT"
            return True
        except Exception:
            pass

        self.font = None
        self._loaded_font_url = None
        return False

    @staticmethod
    def _http_get(url: str, timeout: int = 20) -> bytes:
        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) PhSticker/1.0 (+https://github.com/)",
            "Accept": "*/*",
        }
        r = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        return r.content

    async def _load_font_from_url(self, url: str):
        local_asset = self._local_asset_font(url)
        if local_asset:
            self.font = local_asset
            self._loaded_font_url = f"asset:{os.path.basename(local_asset)}"
            return

        candidates = self._alt_font_urls(url)
        for candidate in candidates:
            try:
                content = await utils.run_sync(self._http_get, candidate, 25)
                buf = io.BytesIO(content)
                # Validate font by trying to load with PIL
                try:
                    test = io.BytesIO(content)
                    ImageFont.truetype(test, size=12)
                except Exception:
                    continue
                buf.seek(0)
                self.font = buf
                self._loaded_font_url = candidate
                return
            except Exception:
                continue

        # If all remote attempts failed, load local fallback
        await self._load_fallback_font_local()

    async def _ensure_font_loaded(self):
        # Get config values safely for both config styles
        try:
            font_url = self.config["FONT_URL"]
        except Exception:
            font_url = "https://raw.githubusercontent.com/google/fonts/main/ofl/notosans/NotoSans-Bold.ttf"

        # Update font size from config if available
        try:
            self.font_size = int(self.config["FONT_SIZE"])
        except Exception:
            pass

        if not font_url and self.font is None:
            await self._load_fallback_font_local()
            return

        if self.font is None or self._loaded_font_url != font_url:
            await self._load_font_from_url(font_url)
            if self.font is None:
                await self._load_fallback_font_local()

    async def client_ready(self, client, db):
        """Loads the font when the userbot starts."""
        await self._ensure_font_loaded()

    def _get_font_instance(self):
        # Returns a PIL ImageFont instance or None
        try:
            if self.font is None:
                return None

            if isinstance(self.font, io.BytesIO):
                try:
                    self.font.seek(0)
                except Exception:
                    pass
                return ImageFont.truetype(self.font, size=self.font_size)

            if isinstance(self.font, str):
                if self.font == "PIL_DEFAULT_FONT":
                    return ImageFont.load_default()
                # Path to a TTF
                return ImageFont.truetype(self.font, size=self.font_size)

            # Unknown type
            return None
        except Exception:
            return None

    def _generate_logo(self, text1: str, text2: str):
        """Synchronous function to create the image."""
        font = self._get_font_instance()
        if font is None:
            return None

        # Measure text with precise bbox
        bbox1 = font.getbbox(text1)
        width1 = bbox1[2] - bbox1[0]
        height1 = bbox1[3] - bbox1[1]

        bbox2 = font.getbbox(text2)
        width2 = bbox2[2] - bbox2[0]
        height2 = bbox2[3] - bbox2[1]

        text_height = max(height1, height2)
        padding_x = 30
        padding_y = 30
        rect_padding = 20
        extra_vertical = 20  # extra vertical padding around the rectangle

        # Compute final image size
        img_width = int(width1 + width2 + (padding_x * 2) + (rect_padding * 3))
        img_height = int(text_height + padding_y * 2 + extra_vertical)

        image = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Top position for text block (real top, not baseline)
        text_top = (img_height - text_height) // 2

        # Draw first word (white), adjust for glyph bbox offset
        text1_x = padding_x - bbox1[0]
        text1_y = text_top - bbox1[1]
        draw.text((text1_x, text1_y), text1, font=font, fill=(255, 255, 255))

        # Orange rectangle behind second word (full height cover)
        rect_x0 = padding_x + width1 + rect_padding
        rect_y0 = text_top - 10
        rect_x1 = rect_x0 + width2 + rect_padding * 2
        rect_y1 = text_top + text_height + 10
        draw.rectangle((rect_x0, rect_y0, rect_x1, rect_y1), fill="#F7971D")

        # Second word (black), centered within rectangle with left padding, adjust for bbox offset
        text2_x = rect_x0 + rect_padding - bbox2[0]
        text2_y = text_top - bbox2[1]
        draw.text((text2_x, text2_y), text2, font=font, fill=(0, 0, 0))

        bbox = image.getbbox()
        if bbox:
            image = image.crop(bbox)

        output = io.BytesIO()
        output.name = "phlogo.webp"
        image.save(output, "WEBP")
        output.seek(0)

        return output

    @loader.command(ru_doc="<текст1> <текст2> - Создать лого в стиле PornHub")
    async def phl(self, message: Message):
        """<text1> <text2> - Create a PornHub style logo"""
        await self._ensure_font_loaded()

        args = utils.get_args_raw(message)
        parts = args.split() if args else []
        if not parts or len(parts) < 2:
            await utils.answer(message, self.strings["no_args"])
            return

        text1 = parts[0]
        text2 = " ".join(parts[1:])

        status_message = await message.reply(self.strings["processing"])

        try:
            logo_buffer = await utils.run_sync(self._generate_logo, text1, text2)

            if logo_buffer:
                await message.client.send_file(
                    message.to_id,
                    logo_buffer,
                    reply_to=message.id,
                )
                if message.out:
                    await message.delete()
                await status_message.delete()
            else:
                await utils.answer(status_message, self.strings["font_error"])

        except Exception as e:
            await utils.answer(status_message, f"<b>Error creating logo:</b>\n<code>{e}</code>")
            return
