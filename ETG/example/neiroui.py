__version__ = (1, 0, 0)
# meta developer: @etopizdesblin

import base64
import io
import mimetypes
import os
import re
import time
import typing
import uuid

import requests
from PIL import Image
from herokutl.tl.types import Message

from .. import loader, utils

MODELS_URL = "https://api.onlysq.ru/ai/models"
CHAT_URL_OPENAI = "https://api.onlysq.ru/ai/openai/chat/completions"
CHAT_URL_V2 = "https://api.onlysq.ru/ai/v2"
IMAGE_URLS_OPENAI = (
    "https://api.onlysq.ru/ai/openai/images/generations",
    "https://api.onlysq.ru/ai/imagen",
    "https://api.onlysq.ru/ai/v2/imagen",
)
IMAGE_URLS_V2 = (
    "https://api.onlysq.ru/ai/v2/imagen",
    "https://api.onlysq.ru/ai/openai/images/generations",
    "https://api.onlysq.ru/ai/imagen",
)
DEFAULT_TEXT_MODEL = "gpt-4o-mini"
DEFAULT_IMAGE_MODEL = "gpt-image-1-mini"
DEFAULT_API_VERSION = "openai"
DEFAULT_API_KEY = "openai"
PROMPT_DIR_NAME = "prompts"
MAX_IMAGE_BYTES = 1_500_000
MAX_FILE_BYTES = 300_000
MAX_TEXT_CHARS = 400_000
MAX_DISPLAY_CHARS = 900
MAX_UI_CHARS = 3500
MAX_UI_PROMPT = 240
BUILTIN_PROMPTS = {
    "Short": (
        "Пиши максимально кратко и по делу. "
        "Используй форматирование: заголовки, списки, жирный/курсив, код. "
        "Если есть шаги — нумерованный список. "
        "Если есть данные — список или таблица. "
        "Не выдумывай факты и не добавляй воды."
    )
}


@loader.tds
class NeiroUIMod(loader.Module):
    """OnlySq AI with ETG UI sheet"""

    strings = {"name": "NeiroUI"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                "",
                "OnlySq API key (empty = env ONLYSQ_API_KEY or 'openai')",
                validator=loader.validators.Hidden(loader.validators.String()),
            ),
            loader.ConfigValue(
                "text_model",
                DEFAULT_TEXT_MODEL,
                "Text model for .neiroui",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "image_model",
                DEFAULT_IMAGE_MODEL,
                "Image model for .neiroui",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "api_version",
                DEFAULT_API_VERSION,
                "API version: openai or v2",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "proxy_url",
                "",
                "Proxy URL (http/https/socks4/socks5)",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "proxy_http",
                "",
                "HTTP proxy (overrides proxy_url)",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "proxy_https",
                "",
                "HTTPS proxy (overrides proxy_url)",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "system_prompt_enabled",
                False,
                "Enable system prompt for .neiroui",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "system_prompt_file",
                "",
                "Selected system prompt (builtin:Short or file)",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "system_prompt_entries",
                [],
                "Selected system prompts (builtin/file list)",
                validator=loader.validators.Series(loader.validators.String()),
            ),
            loader.ConfigValue(
                "working_text_models",
                [],
                "Working text models found by UI check",
                validator=loader.validators.Series(loader.validators.String()),
            ),
            loader.ConfigValue(
                "text_models_checked",
                False,
                "Use working_text_models list for UI model menu",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "device_id",
                "last",
                "ETG device id (or 'last')",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "ui_timeout",
                300,
                "Seconds to keep UI session alive",
                validator=loader.validators.Integer(minimum=30, maximum=3600),
            ),
        )

    @staticmethod
    def _prompts_dir() -> str:
        return os.path.normpath(
            os.path.join(utils.get_base_dir(), "..", "modules", PROMPT_DIR_NAME)
        )

    def _list_prompt_files(self) -> typing.List[str]:
        path = self._prompts_dir()
        os.makedirs(path, exist_ok=True)
        files = []
        for entry in os.scandir(path):
            if not entry.is_file():
                continue
            if entry.name.startswith("."):
                continue
            files.append(entry.name)
        return sorted(files, key=str.lower)

    def _list_prompt_entries(self) -> typing.List[typing.Tuple[str, str]]:
        entries = []
        for name in BUILTIN_PROMPTS:
            entries.append((f"builtin:{name}", f"{name}"))
        for filename in self._list_prompt_files():
            entries.append((f"file:{filename}", filename))
        return entries

    @staticmethod
    def _builtin_filename(name: str) -> str:
        return f"{name}.txt"

    def _match_builtin(self, name: str) -> typing.Optional[str]:
        cleaned = name.strip()
        if cleaned.lower().startswith("builtin:"):
            cleaned = cleaned.split(":", 1)[1].strip()
        base = os.path.splitext(cleaned)[0].lower()
        for builtin in BUILTIN_PROMPTS:
            if base == builtin.lower():
                return builtin
        return None

    def _read_builtin_prompt(self, name: str) -> str:
        filename = self._builtin_filename(name)
        path = os.path.join(self._prompts_dir(), filename)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as handle:
                return handle.read().strip()
        return BUILTIN_PROMPTS.get(name, "")

    def _write_builtin_prompt(self, name: str, text: str) -> str:
        filename = self._builtin_filename(name)
        return self._save_prompt_text(filename, text)

    def _delete_builtin_prompt(self, name: str) -> None:
        filename = self._builtin_filename(name)
        path = os.path.join(self._prompts_dir(), filename)
        if os.path.isfile(path):
            os.remove(path)

    def _read_prompt_file(self, filename: str) -> str:
        path = os.path.join(self._prompts_dir(), filename)
        if not os.path.isfile(path):
            raise FileNotFoundError(filename)
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip()

    def _selected_prompt_entries(self) -> typing.List[str]:
        entries = list(self.config["system_prompt_entries"] or [])
        if not entries:
            legacy = (self.config["system_prompt_file"] or "").strip()
            if legacy:
                entries = [legacy]
        return entries

    def _resolve_prompt_entry(self, entry: str) -> str:
        if entry.startswith("builtin:"):
            name = entry.split(":", 1)[1].strip()
            return self._read_builtin_prompt(name)
        if entry.startswith("file:"):
            filename = entry.split(":", 1)[1].strip()
            try:
                return self._read_prompt_file(filename)
            except FileNotFoundError:
                return ""
        try:
            return self._read_prompt_file(entry)
        except FileNotFoundError:
            return ""

    def _get_system_prompt(self) -> str:
        if not self.config["system_prompt_enabled"]:
            return ""
        entries = self._selected_prompt_entries()
        if not entries:
            return ""
        prompts = []
        for entry in entries:
            text = self._resolve_prompt_entry(entry)
            if text:
                prompts.append(text)
        return "\n\n".join(prompts).strip()

    def _get_api_key(self) -> str:
        key = (self.config["api_key"] or "").strip()
        if key:
            return key
        return (os.environ.get("ONLYSQ_API_KEY") or DEFAULT_API_KEY).strip()

    def _proxy_config(self) -> typing.Optional[dict]:
        proxy = (self.config["proxy_url"] or "").strip()
        http = (self.config["proxy_http"] or "").strip()
        https = (self.config["proxy_https"] or "").strip()
        proxies: typing.Dict[str, str] = {}
        if proxy:
            proxies["http"] = proxy
            proxies["https"] = proxy
        if http:
            proxies["http"] = http
        if https:
            proxies["https"] = https
        return proxies or None

    async def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        def _run():
            session = requests.Session()
            session.trust_env = False
            proxies = self._proxy_config()
            if proxies:
                session.proxies.update(proxies)
            return session.request(method, url, **kwargs)

        return await utils.run_sync(_run)

    @staticmethod
    def _guess_mime(filename: str, mime: str) -> str:
        if mime:
            return mime
        guess = mimetypes.guess_type(filename)[0]
        return guess or "application/octet-stream"

    @staticmethod
    def _is_image_mime(mime: str) -> bool:
        return mime.startswith("image/")

    @staticmethod
    def _truncate_text(text: str, limit: int) -> str:
        if len(text) <= limit:
            return text
        return text[:limit].rstrip() + "\n...[truncated]"

    @staticmethod
    def _strip_reasoning(text: str) -> str:
        if not text:
            return ""
        cleaned = text
        while True:
            start = cleaned.find("<think>")
            if start == -1:
                break
            end = cleaned.find("</think>", start + 7)
            if end == -1:
                cleaned = cleaned[:start]
                break
            cleaned = cleaned[:start] + cleaned[end + 8 :]
        lines = cleaned.splitlines()
        if lines and lines[0].strip().lower().startswith("reasoning"):
            lines = lines[1:]
        return "\n".join(lines).strip()

    def _compress_image(self, raw: bytes, mime: str) -> typing.Tuple[bytes, str]:
        if len(raw) <= MAX_IMAGE_BYTES:
            return raw, mime
        try:
            image = Image.open(io.BytesIO(raw))
        except Exception:
            return raw, mime
        try:
            max_side = 1024
            width, height = image.size
            scale = min(1.0, max_side / max(width, height))
            if scale < 1.0:
                image = image.resize(
                    (int(width * scale), int(height * scale)), Image.LANCZOS
                )
            rgb = image.convert("RGB")
            out = io.BytesIO()
            rgb.save(out, format="JPEG", quality=70, optimize=True)
            return out.getvalue(), "image/jpeg"
        except Exception:
            return raw, mime

    async def _collect_attachments(
        self, message: typing.Optional[Message], reply: typing.Optional[Message]
    ) -> typing.Tuple[typing.List[dict], typing.List[dict]]:
        images = []
        files = []
        for msg in (message, reply):
            if not msg or not msg.media:
                continue
            try:
                raw = await msg.download_media(bytes)
            except Exception:
                continue
            if not raw:
                continue
            filename = ""
            mime = ""
            if getattr(msg, "file", None):
                filename = msg.file.name or ""
                mime = msg.file.mime_type or ""
            filename = filename or ("photo.jpg" if msg.photo else "file.bin")
            mime = self._guess_mime(filename, mime)
            size = len(raw)

            if msg.photo or self._is_image_mime(mime):
                raw, mime = self._compress_image(raw, mime)
                if not raw:
                    continue
                b64 = base64.b64encode(raw).decode("ascii")
                images.append(
                    {
                        "name": filename,
                        "mime": mime,
                        "size": len(raw),
                        "data_url": f"data:{mime};base64,{b64}",
                    }
                )
            else:
                snippet = raw[:MAX_FILE_BYTES]
                text = snippet.decode("utf-8", errors="replace")
                text = self._truncate_text(text, MAX_TEXT_CHARS)
                truncated = size > MAX_FILE_BYTES
                files.append(
                    {
                        "name": filename,
                        "mime": mime,
                        "size": size,
                        "text": text,
                        "truncated": truncated,
                    }
                )
        return images, files

    @staticmethod
    def _build_files_text(files: typing.List[dict]) -> str:
        parts = []
        for info in files:
            header = f"Файл: {info['name']} ({info['mime']}, {info['size']} bytes)"
            body = info["text"]
            if info.get("truncated"):
                body = body + "\n...[truncated]"
            parts.append(f"{header}\n{body}".strip())
        return "\n\n".join(parts)

    def _build_user_content(
        self,
        prompt: str,
        images: typing.List[dict],
        files: typing.List[dict],
    ) -> typing.Union[str, typing.List[dict]]:
        text = prompt.strip()
        files_text = self._build_files_text(files) if files else ""
        if files_text:
            text = f"{text}\n\n{files_text}".strip()
        if not images:
            return text
        parts = [{"type": "text", "text": text or "Опиши вложение."}]
        for image in images:
            parts.append({"type": "image_url", "image_url": {"url": image["data_url"]}})
        return parts

    @staticmethod
    def _extract_prompt(
        message: Message,
        reply: typing.Optional[Message],
    ) -> typing.Optional[typing.Tuple[str, str]]:
        args = utils.get_args_raw(message).strip()
        reply_text = reply.raw_text.strip() if reply and reply.raw_text else ""
        if args and reply_text:
            display_prompt = f"{args} | {reply_text}"
            model_prompt = f"{args}\n\nКонтекст: {reply_text}"
            return display_prompt, model_prompt
        if reply_text:
            return reply_text, reply_text
        if args:
            return args, args
        return None

    @staticmethod
    def _sanitize_prompt_filename(name: str) -> str:
        safe = os.path.basename(name.strip())
        if not safe:
            return ""
        if "." not in safe:
            safe = f"{safe}.txt"
        return safe

    def _save_prompt_text(self, filename: str, text: str) -> str:
        os.makedirs(self._prompts_dir(), exist_ok=True)
        safe_name = self._sanitize_prompt_filename(filename)
        if not safe_name:
            safe_name = f"prompt_{int(time.time())}.txt"
        path = os.path.join(self._prompts_dir(), safe_name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text.strip() + "\n")
        return safe_name

    async def _get_prompt_attachment(
        self, message: Message, reply: typing.Optional[Message]
    ) -> typing.Optional[typing.Tuple[str, str]]:
        for source in (message, reply):
            if not source or not source.media:
                continue
            try:
                data = await source.download_media(bytes)
            except Exception:
                data = None
            if not data:
                continue
            name = ""
            if getattr(source, "file", None) and getattr(source.file, "name", None):
                name = source.file.name
            else:
                doc = getattr(source, "document", None)
                if doc and getattr(doc, "attributes", None):
                    for attr in doc.attributes:
                        file_name = getattr(attr, "file_name", None)
                        if file_name:
                            name = file_name
                            break
            if not name:
                name = f"prompt_{int(time.time())}.txt"
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                text = data.decode("utf-8", errors="replace")
            return name, text
        return None

    def _format_request_block(
        self, prompt: str, images: typing.List[dict], files: typing.List[dict]
    ) -> str:
        safe_prompt = self._truncate_text(prompt.strip() or "—", MAX_DISPLAY_CHARS)
        safe_prompt = utils.escape_html(safe_prompt)
        return f"<blockquote expandable>{safe_prompt}</blockquote>"

    async def _build_photo_prompt(
        self,
        prompt: str,
        images: typing.List[dict],
        files: typing.List[dict],
    ) -> str:
        base = prompt.strip()
        files_text = self._build_files_text(files) if files else ""
        if files_text:
            base = f"{base}\n\n{files_text}".strip()
        if images:
            vision_content = self._build_user_content(
                "Опиши изображения кратко для генерации.", images, []
            )
            try:
                description = await self._request_chat(
                    vision_content,
                    (self.config["text_model"] or DEFAULT_TEXT_MODEL).strip(),
                    system_prompt="",
                )
            except Exception:
                description = ""
            description = self._strip_reasoning(description)
            if description:
                if base:
                    base = f"{base}\n\nРеференсы: {description}".strip()
                else:
                    base = description.strip()
        return base or "Сгенерируй изображение по описанию."

    async def _fetch_models(self) -> dict:
        response = await self._request("GET", MODELS_URL, timeout=30)
        response.raise_for_status()
        return response.json()

    async def _get_model_list(self, modality: str) -> typing.List[str]:
        data = await self._fetch_models()
        classified = data.get("classified", {})
        models = classified.get(modality, [])
        return sorted(models)

    async def _get_text_models(self) -> typing.List[str]:
        if self.config["text_models_checked"]:
            return list(self.config["working_text_models"] or [])
        return await self._get_model_list("text")

    @staticmethod
    def _format_progress_bar(current: int, total: int, width: int = 20) -> str:
        if total <= 0:
            return "[--------------------]"
        ratio = min(max(current / total, 0.0), 1.0)
        filled = int(round(ratio * width))
        return "[" + "#" * filled + "-" * (width - filled) + "]"

    async def _probe_text_model(self, model: str) -> bool:
        try:
            answer = await self._request_chat("ping", model, system_prompt="")
        except Exception:
            return False
        return bool(str(answer or "").strip())

    @staticmethod
    def _format_model_list(models: typing.List[str]) -> str:
        return "\n".join(f"{idx + 1}. {name}" for idx, name in enumerate(models))

    @staticmethod
    def _render_inline(text: str) -> str:
        links = []

        def _link_repl(match: re.Match) -> str:
            idx = len(links)
            links.append((match.group(1), match.group(2)))
            return f"@@LINK{idx}@@"

        text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", _link_repl, text)
        text = utils.escape_html(text)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
        text = re.sub(r"__([^_]+)__", r"<b>\1</b>", text)
        text = re.sub(r"~~([^~]+)~~", r"<s>\1</s>", text)
        text = re.sub(r"(?<!\\)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
        text = re.sub(r"(?<!\\)_([^_]+)_(?!_)", r"<i>\1</i>", text)
        text = re.sub(r"(?<!\\)'([^'\n]+)'(?!\w)", r"<i>\1</i>", text)

        for idx, (label, url) in enumerate(links):
            safe_label = utils.escape_html(label)
            safe_url = utils.escape_html(url)
            text = text.replace(f"@@LINK{idx}@@", f'<a href="{safe_url}">{safe_label}</a>')

        return text

    def _render_markdown(self, text: str) -> str:
        if not text:
            return ""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\[(?:\d+[,\s-]*)+\]", "", text)
        lines = text.split("\n")
        output = []
        in_code = False
        code_lines: typing.List[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if stripped.startswith("```"):
                if in_code:
                    output.append(
                        "<pre><code>"
                        + utils.escape_html("\n".join(code_lines))
                        + "</code></pre>"
                    )
                    code_lines = []
                    in_code = False
                else:
                    in_code = True
                i += 1
                continue
            if in_code:
                code_lines.append(line)
                i += 1
                continue

            if stripped in ("---", "***", "___"):
                output.append("<code>--------------------</code>")
                i += 1
                continue

            if (
                "|" in line
                and i + 1 < len(lines)
                and re.match(r"^\s*\|?\s*[:-]+\s*\|", lines[i + 1])
            ):
                table_lines = [line, lines[i + 1]]
                i += 2
                while i < len(lines) and "|" in lines[i]:
                    table_lines.append(lines[i])
                    i += 1
                output.append("<pre>" + utils.escape_html("\n".join(table_lines)) + "</pre>")
                continue

            heading_match = re.match(r"^\s*#{1,6}\s+(.*)$", line)
            if heading_match:
                output.append(f"<b>{self._render_inline(heading_match.group(1))}</b>")
                i += 1
                continue

            list_match = re.match(r"^\s*([-*•]|\d+[.)])\s+(.*)$", line)
            if list_match:
                output.append("• " + self._render_inline(list_match.group(2)))
            else:
                output.append(self._render_inline(line))
            i += 1

        if in_code and code_lines:
            output.append(
                "<pre><code>"
                + utils.escape_html("\n".join(code_lines))
                + "</code></pre>"
            )

        return "\n".join(output)

    @staticmethod
    def _strip_inline_md(text: str) -> str:
        text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1 (\2)", text)
        text = re.sub(r"`([^`]+)`", r"\1", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
        text = re.sub(r"__([^_]+)__", r"\1", text)
        text = re.sub(r"~~([^~]+)~~", r"\1", text)
        text = re.sub(r"(?<!\\)\*([^*]+)\*(?!\*)", r"\1", text)
        text = re.sub(r"(?<!\\)_([^_]+)_(?!_)", r"\1", text)
        text = re.sub(r"(?<!\\)'([^'\n]+)'(?!\w)", r"\1", text)
        return text

    def _render_markdown_ui(self, text: str) -> str:
        if not text:
            return ""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = re.sub(r"\[(?:\d+[,\s-]*)+\]", "", text)
        lines = text.split("\n")
        output: typing.List[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if stripped in ("---", "***", "___"):
                output.append("—" * 24)
                i += 1
                continue

            if (
                "|" in line
                and i + 1 < len(lines)
                and re.match(r"^\s*\|?\s*[:-]+\s*\|", lines[i + 1])
            ):
                table_lines = [line]
                i += 2
                while i < len(lines) and "|" in lines[i]:
                    table_lines.append(lines[i])
                    i += 1
                table = self._format_table(table_lines)
                output.extend(table)
                continue

            heading_match = re.match(r"^\s*#{1,6}\s+(.*)$", line)
            if heading_match:
                text_line = self._strip_inline_md(heading_match.group(1)).strip()
                output.append(text_line)
                i += 1
                continue

            list_match = re.match(r"^(\s*)([-*•]|\d+[.)])\s+(.*)$", line)
            if list_match:
                indent = len(list_match.group(1))
                level = max(0, indent // 2)
                prefix = ("  " * level) + "• "
                output.append(prefix + self._strip_inline_md(list_match.group(3)).strip())
            else:
                output.append(self._strip_inline_md(line))
            i += 1
        return "\n".join(output).strip()

    @staticmethod
    def _format_table(lines: typing.List[str]) -> typing.List[str]:
        def strip_md(text: str) -> str:
            text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1", text)
            text = re.sub(r"`([^`]+)`", r"\1", text)
            text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
            text = re.sub(r"__([^_]+)__", r"\1", text)
            text = re.sub(r"~~([^~]+)~~", r"\1", text)
            text = re.sub(r"(?<!\\)\*([^*]+)\*(?!\*)", r"\1", text)
            text = re.sub(r"(?<!\\)_([^_]+)_(?!_)", r"\1", text)
            text = re.sub(r"(?<!\\)'([^'\n]+)'(?!\w)", r"\1", text)
            return text

        def split_row(row: str) -> typing.List[str]:
            row = row.strip().strip("|")
            parts = [strip_md(part.strip()) for part in row.split("|")]
            return [p if p else " " for p in parts]

        rows = [split_row(line) for line in lines if line.strip()]
        if len(rows) < 2:
            return [line.strip() for line in lines]
        header = rows[0]
        body = rows[2:] if len(rows) > 2 else []
        all_rows = [header] + body
        widths = [0] * len(header)
        for row in all_rows:
            for idx, cell in enumerate(row):
                widths[idx] = max(widths[idx], len(cell))
        def fmt_row(row: typing.List[str]) -> str:
            padded = []
            for idx, cell in enumerate(row):
                padded.append(cell.ljust(widths[idx]))
            return "| " + " | ".join(padded) + " |"
        sep = "| " + " | ".join("-" * w for w in widths) + " |"
        output = [fmt_row(header), sep]
        for row in body:
            output.append(fmt_row(row))
        return output

    @staticmethod
    def _lang_to_ext(lang: str) -> str:
        lang = (lang or "").strip().lower()
        if not lang:
            return "txt"
        lang = lang.split()[0]
        mapping = {
            "python": "py",
            "py": "py",
            "python3": "py",
            "js": "js",
            "javascript": "js",
            "ts": "ts",
            "typescript": "ts",
            "json": "json",
            "bash": "sh",
            "sh": "sh",
            "shell": "sh",
            "html": "html",
            "css": "css",
            "java": "java",
            "kotlin": "kt",
            "kt": "kt",
            "c": "c",
            "cpp": "cpp",
            "c++": "cpp",
            "cs": "cs",
            "go": "go",
            "php": "php",
            "ruby": "rb",
            "rb": "rb",
            "rust": "rs",
            "rs": "rs",
            "yaml": "yaml",
            "yml": "yml",
            "toml": "toml",
            "ini": "ini",
            "md": "md",
            "sql": "sql",
            "xml": "xml",
            "dart": "dart",
            "swift": "swift",
        }
        return mapping.get(lang, "txt")

    def _extract_code_blocks(self, text: str) -> typing.Tuple[str, typing.List[dict]]:
        lines = text.split("\n")
        blocks = []
        out_lines = []
        in_code = False
        lang = ""
        buf: typing.List[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("```"):
                if in_code:
                    code = "\n".join(buf).rstrip()
                    if code:
                        ext = self._lang_to_ext(lang)
                        filename = f"code_{len(blocks) + 1}.{ext}"
                        blocks.append(
                            {
                                "filename": filename,
                                "lang": lang,
                                "content": code,
                                "lines": len(code.splitlines()),
                            }
                        )
                        out_lines.append(f"[файл: {filename}]")
                    buf = []
                    in_code = False
                    lang = ""
                else:
                    in_code = True
                    lang = stripped.strip("`").strip()
                continue
            if in_code:
                buf.append(line)
            else:
                out_lines.append(line)
        if in_code and buf:
            code = "\n".join(buf).rstrip()
            ext = self._lang_to_ext(lang)
            filename = f"code_{len(blocks) + 1}.{ext}"
            blocks.append(
                {
                    "filename": filename,
                    "lang": lang,
                    "content": code,
                    "lines": len(code.splitlines()),
                }
            )
            out_lines.append(f"[файл: {filename}]")
        return "\n".join(out_lines).strip(), blocks

    def _build_ui_answer(self, answer: str) -> typing.Tuple[str, typing.List[dict]]:
        clean = self._strip_reasoning(answer or "")
        without_code, blocks = self._extract_code_blocks(clean)
        rendered = self._render_markdown_ui(without_code)
        if blocks:
            files = "\n".join(f"• {item['filename']}" for item in blocks)
            rendered = f"{rendered}\n\nФайлы:\n{files}".strip()
        if not rendered:
            rendered = "Ответ пустой."
        rendered = self._truncate_text(rendered, MAX_UI_CHARS)
        return rendered, blocks

    async def _request_chat(
        self,
        content: typing.Union[str, typing.List[dict]],
        model: str,
        system_prompt: typing.Optional[str] = None,
    ) -> str:
        key = self._get_api_key()
        api_version = (self.config["api_version"] or DEFAULT_API_VERSION).lower().strip()
        headers = {"Authorization": f"Bearer {key}"}
        if system_prompt is None:
            system_prompt = self._get_system_prompt()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": content})

        if api_version == "v2":
            url = CHAT_URL_V2
            payload = {
                "model": model,
                "request": {"messages": messages},
            }
        else:
            url = CHAT_URL_OPENAI
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
            }

        response = await self._request(
            "POST",
            url,
            headers=headers,
            json=payload,
            timeout=180,
        )
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            choices = data.get("choices")
            if isinstance(choices, list) and choices:
                message = choices[0].get("message", {})
                content = message.get("content")
                if content is not None:
                    return content
            if data.get("answer"):
                return data["answer"]
        raise ValueError("Empty response")

    async def _generate_image(self, prompt: str, model: str) -> bytes:
        key = self._get_api_key()
        headers = {"Authorization": f"Bearer {key}"}
        api_version = (self.config["api_version"] or DEFAULT_API_VERSION).lower().strip()
        payload = {
            "model": model,
            "prompt": prompt,
            "size": "1024x1024",
            "n": 1,
            "response_format": "b64_json",
        }

        urls = IMAGE_URLS_V2 if api_version == "v2" else IMAGE_URLS_OPENAI
        last_error = None
        for url in urls:
            try:
                response = await self._request(
                    "POST",
                    url,
                    headers=headers,
                    json=payload,
                    timeout=180,
                )
                if response.status_code == 400 and "response_format" in response.text:
                    retry_payload = dict(payload)
                    retry_payload.pop("response_format", None)
                    response = await self._request(
                        "POST",
                        url,
                        headers=headers,
                        json=retry_payload,
                        timeout=180,
                    )
                response.raise_for_status()
                data = response.json()
                b64 = None
                if isinstance(data, dict):
                    if data.get("data"):
                        b64 = data["data"][0].get("b64_json") or data["data"][0].get("image")
                        if not b64 and data["data"][0].get("url"):
                            url = data["data"][0]["url"]
                            image_resp = await self._request("GET", url, timeout=60)
                            image_resp.raise_for_status()
                            return image_resp.content
                    if not b64 and data.get("image"):
                        b64 = data["image"]
                    if not b64 and data.get("images"):
                        item = data["images"][0]
                        b64 = item.get("b64_json") if isinstance(item, dict) else item
                if not b64:
                    raise ValueError("Empty image response")
                return base64.b64decode(b64)
            except Exception as exc:
                last_error = exc

        raise RuntimeError(str(last_error) if last_error else "Image generation failed")

    @staticmethod
    def _dsl_attr(text: str) -> str:
        safe = str(text or "")
        safe = safe.replace("\r", " ").replace("\n", " ")
        safe = safe.replace("\"", "'")
        safe = safe.replace("<", "").replace(">", "")
        return safe.strip()

    @staticmethod
    def _dsl_content(text: str) -> str:
        safe = str(text or "")
        safe = safe.replace("\r", "\n")
        safe = safe.replace("<", "[").replace(">", "]")
        return safe

    def _build_sheet_dsl(
        self,
        title: str,
        subtext: str,
        content: str,
        tags: typing.List[typing.Tuple[str, str]],
        has_codes: bool = False,
    ) -> str:
        tag_parts = []
        for text, color in tags:
            tag_text = self._dsl_attr(text)
            if color:
                tag_parts.append(f'<tag text="{tag_text}" color="{color}" size="12" />')
            else:
                tag_parts.append(f'<tag text="{tag_text}" size="12" />')
        tags_block = "\n".join(tag_parts)
        subtext_safe = self._dsl_attr(subtext)
        content_safe = self._dsl_content(content)
        actions = [
            '<button id="menu" text="Меню" />',
            '<button id="regen" text="Ещё раз" />',
            '<button id="copy" text="Копировать" />',
        ]
        if has_codes:
            actions.append('<button id="codes" text="Коды" />')
        actions.extend(
            [
                '<button id="send" text="В чат" />',
                '<button id="close" text="Закрыть" />',
            ]
        )
        actions_block = "".join(actions)
        return (
            f'<sheet title="{self._dsl_attr(title)}" subtext="{subtext_safe}" '
            f'sub_size="12" close_text="Закрыть">'
            f"{tags_block}"
            f'<content size="14" align="left">{content_safe}</content>'
            f"<actions>{actions_block}</actions>"
            "</sheet>"
        )

    def _format_ui_prompt(self, prompt: str) -> str:
        prompt = (prompt or "").strip()
        if not prompt:
            return "Запрос без текста"
        return self._truncate_text(prompt, MAX_UI_PROMPT)

    def _format_ui_answer(self, answer: str) -> str:
        clean = (answer or "").strip()
        if not clean:
            return "Ответ пустой."
        return self._truncate_text(clean, MAX_UI_CHARS)

    def _build_tags(
        self,
        model: str,
        api_version: str,
        images: typing.List[dict],
        files: typing.List[dict],
        image_model: typing.Optional[str] = None,
    ) -> typing.List[typing.Tuple[str, str]]:
        tags = [
            (f"model: {model}", "#7C4DFF"),
            (f"api: {api_version}", "#00BCD4"),
        ]
        if image_model:
            tags.append((f"image: {image_model}", "#FF9800"))
        if images:
            tags.append((f"images: {len(images)}", "#8BC34A"))
        if files:
            tags.append((f"files: {len(files)}", "#FFB300"))
        return tags

    @staticmethod
    def _sheet_actions(has_codes: bool) -> typing.List[str]:
        actions = ["menu", "regen", "copy", "send", "close"]
        if has_codes:
            actions.insert(3, "codes")
        return actions

    async def _menu_choice(
        self,
        bridge: typing.Any,
        device_id: str,
        title: str,
        message: str,
        items: typing.List[dict],
        timeout: int = 120,
    ) -> typing.Optional[dict]:
        callback_id = f"neiroui_menu_{uuid.uuid4().hex[:8]}"
        bridge.api.menu(device_id, title=title, message=message, items=items, callback_id=callback_id)
        result = await bridge.api.wait_result(device_id, callback_id, timeout=timeout, pop=True)
        if not result:
            return None
        return result.get("data") or None

    async def _prompt_input(
        self,
        bridge: typing.Any,
        device_id: str,
        title: str,
        text: str = "",
        hint: str = "",
        multiline: bool = True,
        max_len: int = 0,
        timeout: int = 300,
    ) -> typing.Optional[str]:
        callback_id = f"neiroui_prompt_{uuid.uuid4().hex[:8]}"
        bridge.api.prompt(
            device_id,
            title=title,
            text=text,
            hint=hint,
            multiline=multiline,
            max_len=max_len,
            callback_id=callback_id,
        )
        result = await bridge.api.wait_result(device_id, callback_id, timeout=timeout, pop=True)
        if not result:
            return None
        data = result.get("data") or {}
        if data.get("cancel"):
            return None
        return str(data.get("text") or "")

    def _update_sheet(
        self,
        bridge: typing.Any,
        device_id: str,
        sheet_id: str,
        callback_id: str,
        title: str,
        prompt_short: str,
        content: str,
        tags: typing.List[typing.Tuple[str, str]],
        has_codes: bool,
    ) -> None:
        dsl = self._build_sheet_dsl(title, prompt_short, content, tags, has_codes=has_codes)
        bridge.api.sheet_update(
            device_id,
            sheet_id,
            dsl,
            actions=self._sheet_actions(has_codes),
            callback_id=callback_id,
        )

    @loader.command(ru_doc="UI-запрос к OnlySq")
    async def neiroui(self, message: Message):
        reply = await message.get_reply_message() if message.is_reply else None
        images, files = await self._collect_attachments(message, reply)
        prompt_data = self._extract_prompt(message, reply)
        display_prompt, model_prompt = prompt_data or ("", "")

        bridge = self.lookup("EtgBridge")
        if not bridge:
            await utils.answer(message, "Модуль EtgBridge не загружен.")
            return

        device_id = (self.config["device_id"] or "last").strip() or "last"
        sheet_id = f"neiroui_{uuid.uuid4().hex[:10]}"
        callback_id = f"{sheet_id}:action"

        state = {
            "display_prompt": display_prompt,
            "model_prompt": model_prompt,
            "images": images,
            "files": files,
            "model": (self.config["text_model"] or DEFAULT_TEXT_MODEL).strip(),
            "image_model": (self.config["image_model"] or DEFAULT_IMAGE_MODEL).strip(),
            "api_version": (self.config["api_version"] or DEFAULT_API_VERSION).strip(),
            "answer": "",
            "ui_content": "",
            "code_blocks": [],
        }

        def tags() -> typing.List[typing.Tuple[str, str]]:
            return self._build_tags(
                state["model"],
                state["api_version"],
                state["images"],
                state["files"],
                state["image_model"],
            )

        def prompt_short() -> str:
            return self._format_ui_prompt(state["display_prompt"])

        def refresh_sheet() -> None:
            self._update_sheet(
                bridge,
                device_id,
                sheet_id,
                callback_id,
                "Neiro UI",
                prompt_short(),
                state["ui_content"],
                tags(),
                has_codes=bool(state["code_blocks"]),
            )

        initial_content = (
            "Думаю..." if (state["display_prompt"] or images or files) else "Нет запроса. Открой меню → Новый запрос."
        )
        state["ui_content"] = initial_content
        action_id = bridge.api.sheet_open(
            device_id,
            self._build_sheet_dsl("Neiro UI", prompt_short(), initial_content, tags(), has_codes=False),
            actions=self._sheet_actions(False),
            callback_id=callback_id,
            sheet_id=sheet_id,
        )
        if not action_id:
            await utils.answer(message, "Нет устройств ETG. Открой плагин ETG Bridge.")
            return

        status_msg = await utils.answer(message, "UI открыт.")

        async def run_request() -> None:
            if not state["model_prompt"] and not state["images"] and not state["files"]:
                return
            self._update_sheet(
                bridge,
                device_id,
                sheet_id,
                callback_id,
                "Neiro UI",
                prompt_short(),
                "Думаю...",
                tags(),
                has_codes=False,
            )
            content = self._build_user_content(
                state["model_prompt"], state["images"], state["files"]
            )
            try:
                answer = await self._request_chat(content, state["model"])
            except Exception as exc:
                error_text = f"Ошибка запроса: {str(exc)}"
                state["ui_content"] = self._truncate_text(error_text, MAX_UI_CHARS)
                state["code_blocks"] = []
                refresh_sheet()
                return

            answer = self._strip_reasoning(answer)
            state["answer"] = answer
            ui_answer, blocks = self._build_ui_answer(answer)
            state["ui_content"] = ui_answer
            state["code_blocks"] = blocks
            refresh_sheet()

        async def choose_text_model() -> None:
            try:
                models = await self._get_text_models()
            except Exception as exc:
                state["ui_content"] = self._truncate_text(
                    f"Ошибка списка моделей: {str(exc)}", MAX_UI_CHARS
                )
                state["code_blocks"] = []
                refresh_sheet()
                return
            if not models:
                bridge.api.toast(device_id, "Список моделей пуст.")
                return
            items = []
            for idx, model in enumerate(models, start=1):
                mark = "✅ " if model == state["model"] else ""
                items.append({"id": str(idx), "text": f"{mark}{idx}. {model}"})
            choice = await self._menu_choice(
                bridge, device_id, "Модели (текст)", "Выбери модель", items
            )
            if not choice:
                return
            index = choice.get("index")
            if index is None or index < 0 or index >= len(models):
                return
            state["model"] = models[index]
            self.config["text_model"] = state["model"]
            refresh_sheet()
            bridge.api.toast(device_id, f"Модель: {state['model']}")

        async def choose_image_model() -> None:
            try:
                models = await self._get_model_list("image")
            except Exception as exc:
                state["ui_content"] = self._truncate_text(
                    f"Ошибка списка моделей: {str(exc)}", MAX_UI_CHARS
                )
                state["code_blocks"] = []
                refresh_sheet()
                return
            if not models:
                bridge.api.toast(device_id, "Список моделей пуст.")
                return
            items = []
            for idx, model in enumerate(models, start=1):
                mark = "✅ " if model == state["image_model"] else ""
                items.append({"id": str(idx), "text": f"{mark}{idx}. {model}"})
            choice = await self._menu_choice(
                bridge, device_id, "Модели (фото)", "Выбери модель", items
            )
            if not choice:
                return
            index = choice.get("index")
            if index is None or index < 0 or index >= len(models):
                return
            state["image_model"] = models[index]
            self.config["image_model"] = state["image_model"]
            refresh_sheet()
            bridge.api.toast(device_id, f"Модель: {state['image_model']}")

        async def run_check_models() -> None:
            try:
                models = await self._get_model_list("text")
            except Exception as exc:
                state["ui_content"] = self._truncate_text(
                    f"Ошибка списка моделей: {str(exc)}", MAX_UI_CHARS
                )
                state["code_blocks"] = []
                refresh_sheet()
                return
            if not models:
                state["ui_content"] = "Список моделей пуст."
                state["code_blocks"] = []
                refresh_sheet()
                return
            prev_content = state["ui_content"]
            prev_blocks = list(state["code_blocks"])
            total = len(models)
            working = []
            last_update = 0.0
            for idx, model in enumerate(models, start=1):
                if await self._probe_text_model(model):
                    working.append(model)
                now = time.time()
                if idx == total or idx == 1 or now - last_update > 1.5:
                    last_update = now
                    bar = self._format_progress_bar(idx, total)
                    percent = int(round((idx / total) * 100))
                    state["ui_content"] = (
                        f"Проверяю модели: {bar} {idx}/{total} ({percent}%)\n"
                        f"Рабочих: {len(working)}"
                    )
                    state["code_blocks"] = []
                    refresh_sheet()
            self.config["working_text_models"] = working
            self.config["text_models_checked"] = True
            state["ui_content"] = (
                f"Готово: {self._format_progress_bar(total, total)} {total}/{total} (100%)\n"
                f"Рабочих: {len(working)}"
            )
            state["code_blocks"] = []
            refresh_sheet()
            state["ui_content"] = prev_content
            state["code_blocks"] = prev_blocks
            refresh_sheet()

        async def prompt_menu() -> None:
            items = [
                {
                    "id": "toggle",
                    "text": f"Системный промпт: {'ON' if self.config['system_prompt_enabled'] else 'OFF'}",
                },
                {"id": "select", "text": "Выбрать промпты"},
                {"id": "add", "text": "Добавить промпт"},
                {"id": "get", "text": "Скачать промпт"},
                {"id": "del", "text": "Удалить промпт"},
            ]
            choice = await self._menu_choice(
                bridge, device_id, "Промпты", "Управление промптами", items
            )
            if not choice:
                return
            action = choice.get("id") or ""
            if action == "toggle":
                self.config["system_prompt_enabled"] = not self.config["system_prompt_enabled"]
                bridge.api.toast(
                    device_id,
                    "Промпт ON" if self.config["system_prompt_enabled"] else "Промпт OFF",
                )
                return
            if action == "select":
                entries = self._list_prompt_entries()
                if not entries:
                    bridge.api.toast(device_id, "Промптов нет.")
                    return
                selected = set(self._selected_prompt_entries())
                items = []
                for idx, (key, label) in enumerate(entries, start=1):
                    mark = "[x]" if key in selected else "[ ]"
                    items.append({"id": str(idx), "text": f"{mark} {label}"})
                choice = await self._menu_choice(
                    bridge, device_id, "Выбор промпта", "Нажми для вкл/выкл", items
                )
                if not choice:
                    return
                index = choice.get("index")
                if index is None or index < 0 or index >= len(entries):
                    return
                key, label = entries[index]
                selected = list(selected)
                if key in selected:
                    selected = [item for item in selected if item != key]
                    state_txt = "выключен"
                else:
                    selected.append(key)
                    state_txt = "включен"
                self.config["system_prompt_entries"] = selected
                self.config["system_prompt_file"] = selected[0] if selected else ""
                self.config["system_prompt_enabled"] = True if selected else False
                bridge.api.toast(device_id, f"Промпт {state_txt}: {label}")
                return
            if action == "add":
                text = await self._prompt_input(
                    bridge,
                    device_id,
                    "Новый промпт",
                    text="",
                    hint="Первая строка может быть именем файла",
                    multiline=True,
                )
                if not text:
                    return
                filename = ""
                content = text
                lines = text.splitlines()
                if lines and len(lines) > 1:
                    first = lines[0].strip()
                    if first.endswith((".txt", ".md", ".prompt")) or self._match_builtin(first):
                        filename = first
                        content = "\n".join(lines[1:]).strip()
                builtin = self._match_builtin(filename or "")
                if builtin:
                    saved = self._write_builtin_prompt(builtin, content)
                else:
                    saved = self._save_prompt_text(filename, content)
                bridge.api.toast(device_id, f"Промпт сохранен: {saved}")
                return
            if action == "get":
                entries = self._list_prompt_entries()
                if not entries:
                    bridge.api.toast(device_id, "Промптов нет.")
                    return
                items = [
                    {"id": str(idx), "text": label}
                    for idx, (_, label) in enumerate(entries, start=1)
                ]
                choice = await self._menu_choice(
                    bridge, device_id, "Промпты", "Выбери промпт", items
                )
                if not choice:
                    return
                index = choice.get("index")
                if index is None or index < 0 or index >= len(entries):
                    return
                entry_key, label = entries[index]
                if entry_key.startswith("builtin:"):
                    name = entry_key.split(":", 1)[1].strip()
                    content = self._read_builtin_prompt(name)
                    file = io.BytesIO(content.encode("utf-8"))
                    file.name = self._builtin_filename(name)
                    await utils.answer_file(status_msg, file)
                    return
                filename = entry_key.split(":", 1)[1].strip()
                path = os.path.join(self._prompts_dir(), filename)
                if not os.path.isfile(path):
                    bridge.api.toast(device_id, "Промпт не найден.")
                    return
                await utils.answer_file(status_msg, path)
                return
            if action == "del":
                entries = self._list_prompt_entries()
                if not entries:
                    bridge.api.toast(device_id, "Промптов нет.")
                    return
                items = [
                    {"id": str(idx), "text": label}
                    for idx, (_, label) in enumerate(entries, start=1)
                ]
                choice = await self._menu_choice(
                    bridge, device_id, "Удалить промпт", "Выбери промпт", items
                )
                if not choice:
                    return
                index = choice.get("index")
                if index is None or index < 0 or index >= len(entries):
                    return
                entry_key, label = entries[index]
                selected = self._selected_prompt_entries()
                if entry_key.startswith("builtin:"):
                    name = entry_key.split(":", 1)[1].strip()
                    try:
                        self._delete_builtin_prompt(name)
                    except Exception:
                        bridge.api.toast(device_id, "Не удалось удалить.")
                        return
                    selected = [item for item in selected if item != entry_key]
                    self.config["system_prompt_entries"] = selected
                    if not selected:
                        self.config["system_prompt_enabled"] = False
                    bridge.api.toast(device_id, f"Промпт удален: {name}")
                    return
                filename = entry_key.split(":", 1)[1].strip()
                path = os.path.join(self._prompts_dir(), filename)
                if os.path.isfile(path):
                    try:
                        os.remove(path)
                    except Exception:
                        bridge.api.toast(device_id, "Не удалось удалить.")
                        return
                selected = [item for item in selected if item != entry_key]
                self.config["system_prompt_entries"] = selected
                if not selected:
                    self.config["system_prompt_enabled"] = False
                bridge.api.toast(device_id, f"Промпт удален: {filename}")

        async def codes_menu() -> None:
            if not state["code_blocks"]:
                bridge.api.toast(device_id, "Кодов нет.")
                return
            items = []
            for idx, item in enumerate(state["code_blocks"], start=1):
                items.append(
                    {
                        "id": f"code:{idx}",
                        "text": f"{idx}. {item['filename']} ({item['lines']} строк)",
                    }
                )
            items.append({"id": "send_all", "text": "Отправить все в чат"})
            choice = await self._menu_choice(
                bridge, device_id, "Коды", "Выбери файл", items
            )
            if not choice:
                return
            cid = choice.get("id") or ""
            if cid == "send_all":
                for block in state["code_blocks"]:
                    file = io.BytesIO(block["content"].encode("utf-8"))
                    file.name = block["filename"]
                    await utils.answer_file(status_msg, file)
                return
            if cid.startswith("code:"):
                try:
                    index = int(cid.split(":", 1)[1]) - 1
                except ValueError:
                    return
                if index < 0 or index >= len(state["code_blocks"]):
                    return
                block = state["code_blocks"][index]
                bridge.api.open_editor(
                    device_id,
                    title="Код",
                    content=block["content"],
                    filename=block["filename"],
                )

        async def main_menu() -> None:
            items = [
                {"id": "new_prompt", "text": "Новый запрос"},
                {"id": "image", "text": "Сгенерировать изображение"},
                {"id": "model_text", "text": "Модель (текст)"},
                {"id": "model_image", "text": "Модель (фото)"},
                {"id": "check_models", "text": "Проверка моделей"},
                {"id": "prompts", "text": "Системные промпты"},
                {"id": "api", "text": "API версия"},
                {"id": "proxy", "text": "Прокси"},
            ]
            choice = await self._menu_choice(
                bridge, device_id, "Меню", "Выбери действие", items
            )
            if not choice:
                return
            action = choice.get("id") or ""
            if action == "new_prompt":
                text = await self._prompt_input(
                    bridge,
                    device_id,
                    "Новый запрос",
                    text=state["display_prompt"],
                    hint="Текст запроса",
                    multiline=True,
                )
                if text is None:
                    return
                state["display_prompt"] = text.strip()
                state["model_prompt"] = text.strip()
                await run_request()
                return
            if action == "image":
                text = await self._prompt_input(
                    bridge,
                    device_id,
                    "Запрос для картинки",
                    text=state["display_prompt"],
                    hint="Что нарисовать",
                    multiline=True,
                )
                if text is None:
                    return
                prompt = text.strip()
                if not prompt and not state["images"] and not state["files"]:
                    bridge.api.toast(device_id, "Нужен текст или вложение.")
                    return
                msg = await utils.answer(status_msg, "Генерирую изображение...")
                try:
                    prompt_full = await self._build_photo_prompt(
                        prompt, state["images"], state["files"]
                    )
                    image_bytes = await self._generate_image(
                        prompt_full, state["image_model"]
                    )
                except Exception as exc:
                    await msg.edit(f"Ошибка запроса: {utils.escape_html(str(exc))}")
                    return
                file = io.BytesIO(image_bytes)
                file.name = "neiro.png"
                await utils.answer_file(
                    msg,
                    file,
                    caption=self._format_request_block(
                        prompt, state["images"], state["files"]
                    ),
                )
                return
            if action == "model_text":
                await choose_text_model()
                return
            if action == "model_image":
                await choose_image_model()
                return
            if action == "check_models":
                choice = await self._menu_choice(
                    bridge,
                    device_id,
                    "Проверка моделей",
                    "Запустить или сбросить список",
                    [
                        {"id": "start", "text": "Запустить проверку"},
                        {"id": "reset", "text": "Сбросить список"},
                    ],
                )
                if not choice:
                    return
                cid = choice.get("id") or ""
                if cid == "reset":
                    self.config["working_text_models"] = []
                    self.config["text_models_checked"] = False
                    bridge.api.toast(device_id, "Список сброшен.")
                    return
                await run_check_models()
                return
            if action == "prompts":
                await prompt_menu()
                return
            if action == "api":
                choice = await self._menu_choice(
                    bridge,
                    device_id,
                    "API версия",
                    "Выбери версию",
                    [{"id": "openai", "text": "openai"}, {"id": "v2", "text": "v2"}],
                )
                if not choice:
                    return
                cid = choice.get("id") or ""
                if cid in {"openai", "v2"}:
                    state["api_version"] = cid
                    self.config["api_version"] = cid
                    refresh_sheet()
                    bridge.api.toast(device_id, f"API: {cid}")
                return
            if action == "proxy":
                choice = await self._menu_choice(
                    bridge,
                    device_id,
                    "Прокси",
                    "Настройка прокси",
                    [
                        {"id": "set_url", "text": "Задать proxy_url"},
                        {"id": "set_http", "text": "Задать HTTP proxy"},
                        {"id": "set_https", "text": "Задать HTTPS proxy"},
                        {"id": "clear", "text": "Очистить прокси"},
                    ],
                )
                if not choice:
                    return
                cid = choice.get("id") or ""
                if cid == "clear":
                    self.config["proxy_url"] = ""
                    self.config["proxy_http"] = ""
                    self.config["proxy_https"] = ""
                    bridge.api.toast(device_id, "Прокси очищены.")
                    return
                title = {
                    "set_url": "proxy_url",
                    "set_http": "proxy_http",
                    "set_https": "proxy_https",
                }.get(cid)
                if not title:
                    return
                current = self.config[title] or ""
                text = await self._prompt_input(
                    bridge,
                    device_id,
                    f"Задать {title}",
                    text=current,
                    hint="http/https/socks4/socks5",
                    multiline=False,
                )
                if text is None:
                    return
                self.config[title] = text.strip()
                bridge.api.toast(device_id, f"{title} обновлен.")
                return

        if state["display_prompt"] or images or files:
            await run_request()

        timeout = int(self.config["ui_timeout"] or 300)
        end_ts = time.time() + max(30, timeout)
        while time.time() < end_ts:
            result = await bridge.api.wait_result(
                device_id,
                callback_id,
                timeout=10,
                pop=True,
            )
            if not result:
                continue
            data = result.get("data") or {}
            action = str(data.get("id") or "")
            if action == "menu":
                await main_menu()
            elif action == "regen":
                await run_request()
            elif action == "copy":
                if state["answer"]:
                    bridge.api.clipboard_set(device_id, state["answer"])
                else:
                    bridge.api.clipboard_set(device_id, state["ui_content"])
                bridge.api.toast(device_id, "Скопировано")
            elif action == "send":
                if state["answer"]:
                    await utils.answer(status_msg, self._render_markdown(state["answer"]))
                else:
                    await utils.answer(status_msg, state["ui_content"])
            elif action == "codes":
                await codes_menu()
            elif action == "close":
                bridge.api.sheet_close(device_id, sheet_id)
                return
