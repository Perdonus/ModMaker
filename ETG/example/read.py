__version__ = (1, 0, 2)
# meta developer: @etopizdesblin

import io
import os
import subprocess
import tempfile

from herokutl.tl.types import Message
from herokutl.extensions import html

from .. import loader, utils


MAX_FILE_SIZE = 5 * 1024 * 1024
INLINE_PAGE_LEN = 3800
INLINE_MAX_PAGES = 50


@loader.tds
class ReadMod(loader.Module):
    """Show replied file contents via cat"""

    strings = {"name": "Read"}

    @loader.command(ru_doc="Показать содержимое файла ответом")
    async def read(self, message: Message):
        reply = await message.get_reply_message() if message.is_reply else None
        if not reply or not reply.media:
            await utils.answer(message, "Ответь на файл.")
            return

        size = getattr(getattr(reply, "file", None), "size", None)
        if size and size > MAX_FILE_SIZE:
            await utils.answer(message, "Файл слишком большой.")
            return

        try:
            data = await reply.download_media(bytes)
        except Exception:
            await utils.answer(message, "Не удалось скачать файл.")
            return
        if not data:
            await utils.answer(message, "Файл пустой.")
            return

        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False) as temp:
                temp.write(data)
                temp_path = temp.name

            result = subprocess.run(
                ["cat", temp_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            output = result.stdout
            if result.stderr:
                output = output + b"\n" + result.stderr
            text = output.decode("utf-8", errors="replace")
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

        text = text.strip() or "(пусто)"
        wrapped = f"<blockquote expandable>{utils.escape_html(text)}</blockquote>"
        pages = list(utils.smart_split(*html.parse(wrapped), length=INLINE_PAGE_LEN))
        if len(pages) <= 1 and len(pages[0]) <= 4096:
            await utils.answer(message, pages[0])
            return
        if len(pages) > INLINE_MAX_PAGES:
            file = io.BytesIO(text.encode("utf-8"))
            file.name = "read.txt"
            await utils.answer_file(message, file, caption="Файл слишком большой.")
            pages = pages[:INLINE_MAX_PAGES]
        try:
            await self.inline.list(message, pages, ttl=10 * 60, silent=True)
        except Exception:
            file = io.BytesIO(text.encode("utf-8"))
            file.name = "read.txt"
            await utils.answer_file(message, file, caption="Файл слишком большой.")
