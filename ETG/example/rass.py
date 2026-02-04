import asyncio
import base64
import datetime
import io
import mimetypes
import typing

from herokutl.tl.types import Channel, Chat, Message, User

from .. import loader, utils


MAX_TIMER_MEDIA = 5 * 1024 * 1024


@loader.tds
class RassMod(loader.Module):
    """Broadcast messages to saved users and chats"""

    strings = {"name": "Rass"}

    def __init__(self):
        self._users = None
        self._chats = None
        self._tasks = None
        self._running_tasks: typing.Dict[str, asyncio.Task] = {}

    async def client_ready(self):
        self._users = self.pointer("users", [])
        self._chats = self.pointer("chats", [])
        self._tasks = self.pointer("tasks", [])
        self._restore_tasks()

    async def on_unload(self):
        for task in self._running_tasks.values():
            task.cancel()
        self._running_tasks.clear()

    def _restore_tasks(self):
        if not self._tasks:
            return
        for item in list(self._tasks):
            if not isinstance(item, dict):
                continue
            task_id = item.get("id")
            ts = item.get("ts")
            if not task_id or not ts:
                continue
            if task_id in self._running_tasks:
                continue
            self._running_tasks[task_id] = asyncio.create_task(self._run_task(item))

    @staticmethod
    def _parse_target(arg: str) -> typing.Optional[int]:
        if not arg:
            return None
        arg = arg.strip()
        if arg.lstrip("-").isdigit():
            return int(arg)
        return None

    async def _resolve_entity(self, arg: str):
        value = self._parse_target(arg)
        try:
            return await self._client.get_entity(value if value is not None else arg)
        except Exception:
            return None

    def _add_target(self, collection: list, peer_id: int) -> bool:
        if peer_id in collection:
            return False
        collection.append(peer_id)
        return True

    def _remove_target(self, collection: list, peer_id: int) -> bool:
        if peer_id not in collection:
            return False
        collection.remove(peer_id)
        return True

    def _targets(self) -> typing.List[int]:
        users = list(self._users or [])
        chats = list(self._chats or [])
        return users + chats

    @staticmethod
    def _parse_datetime(args: str) -> typing.Tuple[typing.Optional[int], str, str]:
        if not args:
            return None, "", "Нужна дата/время."
        parts = args.split()
        date_part = ""
        time_part = ""
        tail = ""

        if len(parts) >= 2 and (("-" in parts[0]) or ("." in parts[0])) and ":" in parts[1]:
            date_part = parts[0]
            time_part = parts[1]
            tail = " ".join(parts[2:])
        elif ":" in parts[0]:
            time_part = parts[0]
            tail = " ".join(parts[1:])
        else:
            return None, "", "Неверный формат времени."

        try:
            if date_part:
                if "-" in date_part:
                    date_obj = datetime.datetime.strptime(date_part, "%Y-%m-%d").date()
                else:
                    date_obj = datetime.datetime.strptime(date_part, "%d.%m.%Y").date()
            else:
                date_obj = datetime.datetime.now().date()
            if len(time_part.split(":")) == 2:
                time_obj = datetime.datetime.strptime(time_part, "%H:%M").time()
            else:
                time_obj = datetime.datetime.strptime(time_part, "%H:%M:%S").time()
        except ValueError:
            return None, "", "Неверный формат даты/времени."

        dt = datetime.datetime.combine(date_obj, time_obj)
        now = datetime.datetime.now()
        if not date_part and dt <= now:
            dt = dt + datetime.timedelta(days=1)
        return int(dt.timestamp()), tail, ""

    async def _forward_to_targets(self, reply: Message) -> typing.Tuple[int, int]:
        targets = self._targets()
        if not targets:
            return 0, 0
        ok = 0
        err = 0
        for peer_id in targets:
            try:
                await self._client.forward_messages(peer_id, reply)
                ok += 1
            except Exception:
                err += 1
        return ok, err

    async def _send_payload_to_targets(
        self,
        text: str,
        media: typing.Optional[dict],
    ) -> typing.Tuple[int, int]:
        targets = self._targets()
        if not targets:
            return 0, 0
        ok = 0
        err = 0
        for peer_id in targets:
            try:
                if media:
                    data = base64.b64decode(media["data_b64"])
                    file = io.BytesIO(data)
                    file.name = media.get("name") or "file.bin"
                    mime = media.get("mime") or mimetypes.guess_type(file.name)[0]
                    force_document = media.get("force_document")
                    await self._client.send_file(
                        peer_id,
                        file,
                        caption=text or None,
                        link_preview=False,
                        force_document=force_document,
                        mime_type=mime,
                    )
                else:
                    await self._client.send_message(peer_id, text)
                ok += 1
            except Exception:
                err += 1
        return ok, err

    @staticmethod
    def _sniff_image_bytes(raw: bytes) -> typing.Tuple[str, str]:
        try:
            from PIL import Image

            image = Image.open(io.BytesIO(raw))
            fmt = (image.format or "").upper()
        except Exception:
            return "", ""
        mapping = {
            "JPEG": ("image/jpeg", ".jpg"),
            "JPG": ("image/jpeg", ".jpg"),
            "PNG": ("image/png", ".png"),
            "WEBP": ("image/webp", ".webp"),
            "GIF": ("image/gif", ".gif"),
        }
        return mapping.get(fmt, ("", ""))

    def _guess_media_name(self, message: Message) -> str:
        file = getattr(message, "file", None)
        name = file.name if file and file.name else ""
        if name and name.lower().endswith(".bin"):
            name = ""
        if not name:
            ext = getattr(file, "ext", "") if file else ""
            if ext:
                name = "file" + ext
        if not name and file and file.mime_type:
            ext = mimetypes.guess_extension(file.mime_type) or ""
            if ext:
                name = "file" + ext
        if not name:
            if message.photo:
                name = "photo.jpg"
            elif message.video or message.gif:
                name = "video.mp4"
            elif message.audio:
                name = "audio.mp3"
            elif message.voice:
                name = "voice.ogg"
            elif message.sticker:
                name = "sticker.webp"
            else:
                name = "file.bin"
        return name

    @staticmethod
    def _detect_media_kind(message: Message) -> str:
        if message.photo:
            return "photo"
        if message.video or message.gif:
            return "video"
        if message.audio or message.voice:
            return "audio"
        if message.sticker:
            return "sticker"
        return "document"

    async def _prepare_command_media(
        self, message: Message, size_limit: typing.Optional[int] = MAX_TIMER_MEDIA
    ) -> typing.Optional[dict]:
        if not message.media:
            return None
        size = getattr(getattr(message, "file", None), "size", None)
        if size_limit and size and size > size_limit:
            raise ValueError("Файл слишком большой для таймера.")
        raw = await message.download_media(bytes)
        if not raw:
            return None
        name = self._guess_media_name(message)
        mime = getattr(getattr(message, "file", None), "mime_type", "") or ""
        kind = self._detect_media_kind(message)
        force_document = kind not in {"photo", "video", "audio"}

        sniff_mime, sniff_ext = self._sniff_image_bytes(raw)
        if sniff_mime:
            if not mime or mime == "application/octet-stream":
                mime = sniff_mime
            if not name or "." not in name:
                name = "photo" + sniff_ext
            force_document = False
        return {
            "name": name,
            "mime": mime,
            "force_document": force_document,
            "data_b64": base64.b64encode(raw).decode("ascii"),
        }

    async def _run_task(self, task: dict):
        try:
            ts = int(task.get("ts") or 0)
        except Exception:
            ts = 0
        delay = max(0, ts - int(datetime.datetime.now().timestamp()))
        if delay:
            await asyncio.sleep(delay)

        reply_chat = task.get("source_chat")
        reply_id = task.get("source_msg")
        text = task.get("text") or ""
        media = task.get("media")

        if reply_chat and reply_id:
            try:
                src = await self._client.get_messages(reply_chat, ids=reply_id)
            except Exception:
                src = None
            if src:
                await self._forward_to_targets(src)
            elif text or media:
                await self._send_payload_to_targets(text, media)
        elif text or media:
            await self._send_payload_to_targets(text, media)

        task_id = task.get("id")
        if task_id in self._running_tasks:
            self._running_tasks.pop(task_id, None)
        if self._tasks is not None and task in self._tasks:
            self._tasks.remove(task)

    @loader.command(ru_doc="Добавить пользователя для рассылки")
    async def adduser(self, message: Message):
        args = utils.get_args_raw(message).strip()
        if not args:
            await utils.answer(message, "Нужен ID или @username.")
            return
        entity = await self._resolve_entity(args)
        if not isinstance(entity, User):
            await utils.answer(message, "Это не пользователь.")
            return
        peer_id = utils.get_entity_id(entity)
        if self._users is None:
            self._users = self.pointer("users", [])
        if self._add_target(self._users, peer_id):
            await utils.answer(message, f"Добавлен пользователь: {peer_id}")
        else:
            await utils.answer(message, "Пользователь уже в списке.")

    @loader.command(ru_doc="Удалить пользователя из рассылки")
    async def deluser(self, message: Message):
        args = utils.get_args_raw(message).strip()
        if not args:
            await utils.answer(message, "Нужен ID или @username.")
            return
        entity = await self._resolve_entity(args)
        if not entity:
            await utils.answer(message, "Не удалось найти.")
            return
        peer_id = utils.get_entity_id(entity)
        if self._users is None:
            self._users = self.pointer("users", [])
        if self._remove_target(self._users, peer_id):
            await utils.answer(message, f"Удален пользователь: {peer_id}")
        else:
            await utils.answer(message, "Пользователя нет в списке.")

    @loader.command(ru_doc="Добавить чат для рассылки")
    async def addchat(self, message: Message):
        args = utils.get_args_raw(message).strip()
        if not args:
            await utils.answer(message, "Нужен ID или @username.")
            return
        entity = await self._resolve_entity(args)
        if not isinstance(entity, (Chat, Channel)):
            await utils.answer(message, "Это не чат.")
            return
        peer_id = utils.get_entity_id(entity)
        if self._chats is None:
            self._chats = self.pointer("chats", [])
        if self._add_target(self._chats, peer_id):
            await utils.answer(message, f"Добавлен чат: {peer_id}")
        else:
            await utils.answer(message, "Чат уже в списке.")

    @loader.command(ru_doc="Удалить чат из рассылки")
    async def delchat(self, message: Message):
        args = utils.get_args_raw(message).strip()
        if not args:
            await utils.answer(message, "Нужен ID или @username.")
            return
        entity = await self._resolve_entity(args)
        if not entity:
            await utils.answer(message, "Не удалось найти.")
            return
        peer_id = utils.get_entity_id(entity)
        if self._chats is None:
            self._chats = self.pointer("chats", [])
        if self._remove_target(self._chats, peer_id):
            await utils.answer(message, f"Удален чат: {peer_id}")
        else:
            await utils.answer(message, "Чата нет в списке.")

    @loader.command(ru_doc="Список всех получателей")
    async def list(self, message: Message):
        users = list(self._users or [])
        chats = list(self._chats or [])
        if not users and not chats:
            await utils.answer(message, "Список пуст.")
            return
        lines = []
        for uid in users:
            lines.append(f"user: {uid}")
        for cid in chats:
            lines.append(f"chat: {cid}")
        await utils.answer(message, "\n".join(lines))

    @loader.command(ru_doc="Рассылка сейчас")
    async def rass(self, message: Message):
        reply = await message.get_reply_message() if message.is_reply else None
        if reply:
            reply_file = getattr(reply, "file", None)
            needs_repack = False
            if reply_file:
                name = (reply_file.name or "").lower()
                mime = (reply_file.mime_type or "").lower()
                if name.endswith(".bin") or mime in {"", "application/octet-stream"}:
                    needs_repack = True
            if reply.media and needs_repack:
                try:
                    media = await self._prepare_command_media(reply, size_limit=None)
                except ValueError as exc:
                    await utils.answer(message, str(exc))
                    return
                ok, err = await self._send_payload_to_targets(reply.raw_text or "", media)
                await utils.answer(message, f"Готово. Отправлено: {ok}, ошибок: {err}.")
                return

            ok, err = await self._forward_to_targets(reply)
            await utils.answer(message, f"Готово. Отправлено: {ok}, ошибок: {err}.")
            return

        text = utils.get_args_raw(message).strip()
        if message.media:
            msg_file = getattr(message, "file", None)
            needs_repack = False
            if msg_file:
                name = (msg_file.name or "").lower()
                mime = (msg_file.mime_type or "").lower()
                if name.endswith(".bin") or mime in {"", "application/octet-stream"}:
                    needs_repack = True
            if needs_repack:
                try:
                    media = await self._prepare_command_media(message, size_limit=None)
                except ValueError as exc:
                    await utils.answer(message, str(exc))
                    return
                ok, err = await self._send_payload_to_targets(text, media)
                await utils.answer(message, f"Готово. Отправлено: {ok}, ошибок: {err}.")
                return

            targets = self._targets()
            if not targets:
                await utils.answer(message, "Список пуст.")
                return
            ok = 0
            err = 0
            for peer_id in targets:
                try:
                    await self._client.send_file(
                        peer_id,
                        message,
                        caption=text or None,
                        link_preview=False,
                    )
                    ok += 1
                except Exception:
                    err += 1
            await utils.answer(message, f"Готово. Отправлено: {ok}, ошибок: {err}.")
            return

        media = None
        if not text and not media:
            await utils.answer(message, "Нужен текст, медиа или ответ на сообщение.")
            return

        ok, err = await self._send_payload_to_targets(text, media)
        await utils.answer(message, f"Готово. Отправлено: {ok}, ошибок: {err}.")

    @loader.command(ru_doc="Рассылка по времени")
    async def timerass(self, message: Message):
        args = utils.get_args_raw(message).strip()
        ts, tail, error = self._parse_datetime(args)
        if error:
            await utils.answer(message, error)
            return
        reply = await message.get_reply_message() if message.is_reply else None

        payload = {
            "id": f"{ts}-{int(datetime.datetime.now().timestamp() * 1000)}",
            "ts": ts,
            "source_chat": None,
            "source_msg": None,
            "text": "",
            "media": None,
        }

        if reply:
            reply_file = getattr(reply, "file", None)
            needs_repack = False
            if reply_file:
                name = (reply_file.name or "").lower()
                mime = (reply_file.mime_type or "").lower()
                if name.endswith(".bin") or mime in {"", "application/octet-stream"}:
                    needs_repack = True
            if reply.media and needs_repack:
                try:
                    payload["media"] = await self._prepare_command_media(
                        reply, size_limit=MAX_TIMER_MEDIA
                    )
                except ValueError as exc:
                    await utils.answer(message, str(exc))
                    return
                payload["text"] = reply.raw_text or ""
            else:
                payload["source_chat"] = utils.get_chat_id(reply)
                payload["source_msg"] = reply.id
        else:
            if message.media:
                try:
                    payload["media"] = await self._prepare_command_media(message)
                except ValueError as exc:
                    await utils.answer(message, str(exc))
                    return
            payload["text"] = tail.strip()

        if not payload["source_msg"] and not payload["text"] and not payload["media"]:
            await utils.answer(message, "Нужен текст, медиа или ответ на сообщение.")
            return

        if self._tasks is None:
            self._tasks = self.pointer("tasks", [])
        self._tasks.append(payload)
        self._running_tasks[payload["id"]] = asyncio.create_task(self._run_task(payload))
        when = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
        await utils.answer(message, f"Запланировано на {when}.")
