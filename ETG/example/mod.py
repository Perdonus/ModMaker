# requires: gitpython git
__version__ = (1, 2, 1)
# meta developer: @etopizdesblin

import io
import json
import mimetypes
import os
import re
import secrets
import shlex
import shutil
import tarfile
import tempfile
import time
import typing
import zipfile
import subprocess

import requests
from git import GitCommandError, InvalidGitRepositoryError, Repo
from herokutl.extensions import html
from herokutl.tl.types import Message

from .. import loader, utils


MODELS_URL = "https://api.onlysq.ru/ai/models"
CHAT_URL_OPENAI = "https://api.onlysq.ru/ai/openai/chat/completions"
DEFAULT_TEXT_MODEL = "deepseek-r1"
DEFAULT_API_KEY = "openai"
AI_DIR_NAME = "ai_plug"
MODULE_FILENAME = "module.py"
PLUGIN_FILENAME = "plugin.plugin"
CHANGELOG_FILENAME = "changelog.txt"
FILENAME_FILENAME = "filename.txt"
KIND_FILENAME = "kind.txt"
PROMPT_DIR_NAME = "prompts"
REPO_ROOT_NAME = "ModMaker"
REPO_URL = "https://github.com/Perdonus/ModMaker.git"
REPO_BASE_URL = "https://sosiskibot.ru/assets/ModRepo"
REPO_UPDATE_TTL = 3600
AIMAKER_ROOT_NAME = "aimaker"
CHECK_DIR_NAME = "check"
MODULE_DOC_DIR = "Heroku"
PLUGIN_DOC_DIR = "Plugins"
ETG_DOC_DIR = "ETG"
MODULE_DOC_NAME = "Heroku.md"
PLUGIN_DOC_NAME = "Plugins.md"
ETG_DOC_NAME = "Heroku.md"
ETG_LIB_NAME = "EtgBridge.md"
MODULE_EXAMPLES_DIR = "example"
PLUGIN_EXAMPLES_DIR = "example"
ETG_EXAMPLES_DIR = "example"
MANDRE_DOC_NAME = "mandrelib.md"
BUILTIN_PROMPTS = {}
MAX_ATTACH_BYTES = 200_000
MAX_ATTACH_FILES = 8
MAX_EXAMPLE_BYTES = 40_000
MAX_EXAMPLES_TOTAL = 220_000
INLINE_PAGE_LEN = 3800
INLINE_MAX_PAGES = 50
ALLOWED_MODELS = [
    "deepseek-r1",
    "deepseek-v3",
    "gemini-3-pro",
    "gpt-5.2-chat",
    "zai-glm-4.6",
    "qwen3-coder-plus",
    "qwen3-max",
]

SERVICE_ERROR_TEXT = "Тех. работы со стороны сервиса или пролучите/обновите апи на my.onlysq.ru"


@loader.tds
class AIMakerMod(loader.Module):
    """Generate Heroku modules/plugins via OnlySq"""

    strings = {"name": "AIMaker"}

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "api_key",
                "",
                "OnlySq API key (empty = use env ONLYSQ_API_KEY or 'openai')",
                validator=loader.validators.Hidden(loader.validators.String()),
            ),
            loader.ConfigValue(
                "api_endpoint",
                CHAT_URL_OPENAI,
                "OpenAI-compatible endpoint for chat completions",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "models_url",
                MODELS_URL,
                "Models list URL (OnlySq compatible)",
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
                "model",
                DEFAULT_TEXT_MODEL,
                "Text model for .mod",
                validator=loader.validators.String(),
            ),
            loader.ConfigValue(
                "prompt_enabled",
                False,
                "Enable extra system prompts for .mod/.editmod/.plug/.editplug",
                validator=loader.validators.Boolean(),
            ),
            loader.ConfigValue(
                "prompt_entries",
                [],
                "Selected system prompts (builtin/file list)",
                validator=loader.validators.Series(loader.validators.String()),
            ),
        )
        self._dialogs = None
        self._last_patch_error = ""
        self._repo_checked_at = 0.0

    def _get_api_key(self) -> str:
        key = (self.config["api_key"] or "").strip()
        if key:
            return key
        return (os.environ.get("ONLYSQ_API_KEY") or DEFAULT_API_KEY).strip()

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
    def _base_root() -> str:
        return os.path.normpath(os.path.join(utils.get_base_dir(), ".."))

    def _aimaker_root(self) -> str:
        root = os.path.join(os.path.expanduser("~"), AIMAKER_ROOT_NAME)
        os.makedirs(root, exist_ok=True)
        return root

    def _repo_dir(self) -> str:
        return os.path.join(self._aimaker_root(), REPO_ROOT_NAME)

    def _check_root(self) -> str:
        root = os.path.join(self._aimaker_root(), CHECK_DIR_NAME)
        os.makedirs(root, exist_ok=True)
        return root

    def _check_dir(self, dialog_id: str) -> str:
        path = os.path.join(self._check_root(), dialog_id)
        os.makedirs(path, exist_ok=True)
        return path

    def _repo_base_url(self) -> str:
        return REPO_BASE_URL.rstrip("/")

    def _repo_urls(self) -> typing.Tuple[str, str, str, str]:
        base = self._repo_base_url()
        return (
            f"{base}/manifest.json",
            f"{base}/ModRepo.zip",
            f"{base}/ModRepo.tar.gz",
            f"{base}/repo",
        )

    def _store_repo_log(self, logs: typing.List[str]) -> None:
        self.set("repo_log", logs)

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

    @staticmethod
    def _hash_file(path: str) -> str:
        import hashlib

        hasher = hashlib.sha256()
        with open(path, "rb") as handle:
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    break
                hasher.update(chunk)
        return hasher.hexdigest()

    @staticmethod
    def _safe_relpath(path: str) -> str:
        clean = path.replace("\\", "/").lstrip("/")
        if not clean or clean.startswith("../") or "/../" in clean:
            return ""
        return clean

    @staticmethod
    def _extract_pip_command(changelog: str) -> str:
        for raw_line in changelog.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if line[:1] in "+~-":
                line = line[1:].strip()
            if line.lower().startswith("pip:"):
                line = line[4:].strip()
            if "pip install" not in line.lower():
                continue
            match = re.search(r"pip\\s+install\\s+(.+)", line, flags=re.IGNORECASE)
            if not match:
                continue
            tail = match.group(1).strip()
            if not tail or tail.lower() in {"none", "no", "нет"}:
                return ""
            return f"pip install {tail}"
        return ""

    @staticmethod
    def _strip_versions(tokens: typing.List[str]) -> typing.List[str]:
        cleaned = []
        for token in tokens:
            if token.startswith("-"):
                cleaned.append(token)
                continue
            value = token
            for op in ("==", ">=", "<=", "~=", "!=", ">", "<"):
                if op in value:
                    value = value.split(op, 1)[0]
                    break
            if value:
                cleaned.append(value)
        return cleaned

    def _parse_pip_args(self, changelog: str) -> typing.List[str]:
        command = self._extract_pip_command(changelog)
        if not command:
            return []
        parts = shlex.split(command)
        try:
            idx = parts.index("install")
        except ValueError:
            return []
        args = parts[idx + 1 :]
        return self._strip_versions(args)

    @staticmethod
    def _venv_python(venv_dir: str) -> str:
        return os.path.join(venv_dir, "bin", "python")

    def _ensure_venv(self, check_dir: str, logs: typing.List[str]) -> str:
        venv_dir = os.path.join(check_dir, "venv")
        python_path = self._venv_python(venv_dir)
        if os.path.isfile(python_path):
            logs.append(f"venv: exists ({python_path})")
            return python_path

        candidates = [
            "python",
            "py",
            "python3",
            "python3.14",
            "python3.13",
            "python3.12",
            "python3.11",
        ]
        logs.append("venv: create")
        found = False
        for cmd in candidates:
            if not shutil.which(cmd):
                logs.append(f"venv {cmd}: not found")
                continue
            found = True
            try:
                proc = subprocess.run(
                    [cmd, "-m", "venv", venv_dir],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
            except FileNotFoundError:
                logs.append(f"venv {cmd}: not found")
                continue
            if proc.returncode == 0 and os.path.isfile(python_path):
                logs.append(f"venv: ok ({cmd})")
                return python_path
            if proc.stderr:
                logs.append(
                    f"venv {cmd} stderr: {self._clip_text(proc.stderr.decode(errors='ignore'), 800)}"
                )

        if not found:
            raise RuntimeError("python_not_found")
        raise RuntimeError("Не удалось создать venv")

    def _compile_check(
        self,
        dialog_id: str,
        filename: str,
        code: str,
        changelog: str,
    ) -> typing.Tuple[bool, str]:
        logs: typing.List[str] = []
        check_dir = self._check_dir(dialog_id)
        rel = self._safe_relpath(filename) or os.path.basename(filename)
        file_path = os.path.join(check_dir, rel)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as handle:
            handle.write(code)
        logs.append(f"file: {file_path}")

        try:
            python_path = self._ensure_venv(check_dir, logs)
        except Exception as exc:
            if str(exc) == "python_not_found":
                logs.append("venv: skip (python not found)")
                logs.append("compile: skipped")
                return True, "\n".join(logs)
            logs.append(f"venv error: {exc}")
            return False, "\n".join(logs)

        pip_args = self._parse_pip_args(changelog)
        if pip_args:
            logs.append("pip: install " + " ".join(pip_args))
            proc = subprocess.run(
                [python_path, "-m", "pip", "install", *pip_args],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            logs.append(f"pip exit: {proc.returncode}")
            if proc.stdout:
                logs.append(self._clip_text(proc.stdout.decode(errors="ignore"), 800))
            if proc.stderr:
                logs.append(self._clip_text(proc.stderr.decode(errors="ignore"), 800))
            if proc.returncode != 0:
                return False, "\n".join(logs)
        else:
            logs.append("pip: none")

        proc = subprocess.run(
            [python_path, "-m", "py_compile", file_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        logs.append(f"compile exit: {proc.returncode}")
        if proc.stdout:
            logs.append(self._clip_text(proc.stdout.decode(errors="ignore"), 800))
        if proc.stderr:
            logs.append(self._clip_text(proc.stderr.decode(errors="ignore"), 800))
        return proc.returncode == 0, "\n".join(logs)

    def _download_to_path(self, url: str, path: str, logs: typing.Optional[typing.List[str]] = None) -> int:
        size = 0
        proxies = self._proxy_config()
        try:
            response = requests.get(url, stream=True, timeout=None, proxies=proxies)
            response.raise_for_status()
        except requests.exceptions.SSLError:
            if logs is not None:
                logs.append("ssl verify failed, retrying insecure")
            response = requests.get(
                url, stream=True, timeout=None, verify=False, proxies=proxies
            )
            response.raise_for_status()

        with open(path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 256):
                if chunk:
                    handle.write(chunk)
                    size += len(chunk)
        return size

    def _load_manifest(self, url: str, logs: typing.Optional[typing.List[str]] = None) -> typing.Optional[dict]:
        proxies = self._proxy_config()
        try:
            response = requests.get(url, timeout=None, proxies=proxies)
            response.raise_for_status()
        except requests.exceptions.SSLError:
            if logs is not None:
                logs.append("manifest ssl verify failed, retrying insecure")
            response = requests.get(url, timeout=None, verify=False, proxies=proxies)
            response.raise_for_status()
        return response.json()

    def _install_from_archive_url(
        self,
        url: str,
        repo_dir: str,
        logs: typing.Optional[typing.List[str]] = None,
    ) -> None:
        tmp_dir = tempfile.mkdtemp(prefix="aimaker_repo_")
        archive_path = os.path.join(tmp_dir, "repo.bin")
        extract_dir = os.path.join(tmp_dir, "extract")
        os.makedirs(extract_dir, exist_ok=True)
        try:
            if logs is not None:
                logs.append(f"archive_url: {url}")
            size = self._download_to_path(url, archive_path, logs=logs)
            if logs is not None:
                logs.append(f"downloaded: {size} bytes")

            if zipfile.is_zipfile(archive_path):
                if logs is not None:
                    logs.append("archive type: zip")
                with zipfile.ZipFile(archive_path) as zf:
                    zf.extractall(extract_dir)
            elif tarfile.is_tarfile(archive_path):
                if logs is not None:
                    logs.append("archive type: tar")
                with tarfile.open(archive_path) as tf:
                    tf.extractall(extract_dir)
            else:
                raise RuntimeError("Unknown archive format (expected zip/tar)")

            entries = [name for name in os.listdir(extract_dir) if not name.startswith(".")]
            root = extract_dir
            if len(entries) == 1:
                candidate = os.path.join(extract_dir, entries[0])
                if os.path.isdir(candidate):
                    root = candidate

            if os.path.isdir(repo_dir):
                shutil.rmtree(repo_dir, ignore_errors=True)
            shutil.copytree(root, repo_dir)
            if logs is not None:
                logs.append("install: ok")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    def _sync_from_manifest(
        self,
        manifest: dict,
        files_base: str,
        repo_dir: str,
        logs: typing.Optional[typing.List[str]] = None,
    ) -> None:
        files = manifest.get("files", [])
        if not isinstance(files, list) or not files:
            raise RuntimeError("manifest has no files")
        if logs is not None:
            logs.append(f"manifest files: {len(files)}")

        os.makedirs(repo_dir, exist_ok=True)
        updated = 0
        for entry in files:
            if not isinstance(entry, dict):
                continue
            rel = self._safe_relpath(str(entry.get("path", "")).strip())
            if not rel:
                continue
            dest = os.path.join(repo_dir, rel)
            expected = str(entry.get("sha256", "")).strip()
            if os.path.isfile(dest) and expected:
                try:
                    if self._hash_file(dest) == expected:
                        continue
                except Exception:
                    pass
            url = f"{files_base}/{rel}"
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            tmp_path = dest + ".tmp"
            size = self._download_to_path(url, tmp_path, logs=logs)
            if expected:
                actual = self._hash_file(tmp_path)
                if actual != expected:
                    os.remove(tmp_path)
                    raise RuntimeError(f"hash mismatch for {rel}")
            os.replace(tmp_path, dest)
            updated += 1
        if logs is not None:
            logs.append(f"updated files: {updated}")

    def _ensure_repo(self, *, logs: typing.Optional[typing.List[str]] = None, force: bool = False) -> None:
        if logs is None:
            logs = []

        repo_dir = self._repo_dir()
        logs.append(f"repo_dir: {repo_dir}")
        if os.path.exists(repo_dir) and not os.path.isdir(repo_dir):
            raise RuntimeError(f"Путь занят файлом: {repo_dir}")

        now = time.time()
        repo_exists = os.path.isdir(repo_dir)
        logs.append(f"repo exists: {'yes' if repo_exists else 'no'}")

        manifest_url, zip_url, tar_url, files_base = self._repo_urls()
        logs.append(f"manifest: {manifest_url}")

        manifest = None
        try:
            manifest = self._load_manifest(manifest_url, logs=logs)
            logs.append("manifest: ok")
        except Exception as exc:
            logs.append(f"manifest failed: {exc}")

        commit = ""
        if isinstance(manifest, dict):
            commit = str(manifest.get("commit", "")).strip()
            if commit:
                logs.append(f"commit: {commit}")

        stored_commit = self.get("repo_commit", "")
        if (
            repo_exists
            and commit
            and commit == stored_commit
            and not force
            and self._repo_checked_at
            and now - self._repo_checked_at < REPO_UPDATE_TTL
        ):
            logs.append("skip update: commit up-to-date")
            self._store_repo_log(logs)
            return

        has_unzip = bool(shutil.which("unzip"))
        has_tar = bool(shutil.which("tar"))
        logs.append(f"unzip: {'yes' if has_unzip else 'no'}")
        logs.append(f"tar: {'yes' if has_tar else 'no'}")

        update_ok = False
        if has_unzip:
            try:
                self._install_from_archive_url(zip_url, repo_dir, logs=logs)
                update_ok = True
            except Exception as exc:
                logs.append(f"zip failed: {exc}")

        if not update_ok and has_tar:
            try:
                self._install_from_archive_url(tar_url, repo_dir, logs=logs)
                update_ok = True
            except Exception as exc:
                logs.append(f"tar failed: {exc}")

        if not update_ok and manifest:
            try:
                self._sync_from_manifest(manifest, files_base, repo_dir, logs=logs)
                update_ok = True
            except Exception as exc:
                logs.append(f"direct failed: {exc}")

        if update_ok:
            if commit:
                self.set("repo_commit", commit)
            self._repo_checked_at = now
            logs.append("update: ok")
            self._store_repo_log(logs)
            return

        if repo_exists:
            try:
                repo = Repo(repo_dir)
            except InvalidGitRepositoryError as exc:
                raise RuntimeError(f"Папка не является git-репозиторием: {repo_dir}") from exc
            origin = repo.remotes.origin if repo.remotes else None
            if not origin:
                raise RuntimeError("git remote origin не найден.")
            if not shutil.which("git"):
                raise RuntimeError("git не установлен. Установи git для работы AIMaker.")
            try:
                logs.append("git pull origin")
                origin.pull()
                logs.append("pull: ok")
                self._repo_checked_at = now
                self._store_repo_log(logs)
                return
            except GitCommandError as exc:
                logs.append(f"git pull failed: {exc}")
                self._store_repo_log(logs)
                raise RuntimeError(f"git pull failed: {exc}") from exc

        os.makedirs(os.path.dirname(repo_dir), exist_ok=True)
        if not shutil.which("git"):
            self._store_repo_log(logs)
            raise RuntimeError("git не установлен. Установи git для работы AIMaker.")
        try:
            logs.append(f"git clone {REPO_URL}")
            Repo.clone_from(REPO_URL, repo_dir)
            logs.append("clone: ok")
        except GitCommandError as exc:
            logs.append(f"git clone failed: {exc}")
            self._store_repo_log(logs)
            raise RuntimeError(f"git clone failed: {exc}") from exc
        self._repo_checked_at = now
        self._store_repo_log(logs)

    def _mandre_path(self) -> str:
        return os.path.join(self._repo_dir(), PLUGIN_DOC_DIR, "mandre_lib.plugin")

    @staticmethod
    def _prompts_dir() -> str:
        return os.path.normpath(
            os.path.join(utils.get_base_dir(), "..", "modules", PROMPT_DIR_NAME)
        )

    def _load_repo_prompt(
        self,
        kind: str,
        extra_doc_dirs: typing.Optional[typing.List[str]] = None,
    ) -> str:
        self._ensure_repo()
        repo_dir = self._repo_dir()
        parts: typing.List[str] = []

        doc_dirs = [PLUGIN_DOC_DIR] if self._is_plugin(kind) else [MODULE_DOC_DIR]
        if extra_doc_dirs:
            doc_dirs.extend(extra_doc_dirs)

        for doc_dir in doc_dirs:
            if doc_dir == PLUGIN_DOC_DIR:
                doc_name = PLUGIN_DOC_NAME
            elif doc_dir == ETG_DOC_DIR:
                doc_name = ETG_DOC_NAME
            else:
                doc_name = MODULE_DOC_NAME

            doc_path = os.path.join(repo_dir, doc_dir, doc_name)
            if os.path.isfile(doc_path):
                try:
                    doc = open(doc_path, "r", encoding="utf-8").read().strip()
                except Exception:
                    doc = ""
                if doc:
                    parts.append("=== DOC ===\n" + doc + "\n=== END_DOC ===")

            if doc_dir == ETG_DOC_DIR:
                etg_lib = os.path.join(repo_dir, doc_dir, ETG_LIB_NAME)
                if os.path.isfile(etg_lib):
                    try:
                        lib_text = open(etg_lib, "r", encoding="utf-8").read().strip()
                    except Exception:
                        lib_text = ""
                    if lib_text:
                        parts.append(
                            "=== ETG_LIB ===\n" + lib_text + "\n=== END_ETG_LIB ==="
                        )

        if kind == "plugin":
            mandre_path = os.path.join(repo_dir, PLUGIN_DOC_DIR, MANDRE_DOC_NAME)
            if os.path.isfile(mandre_path):
                try:
                    mandre = open(mandre_path, "r", encoding="utf-8").read().strip()
                except Exception:
                    mandre = ""
                if mandre:
                    parts.append("=== MANDRELIB ===\n" + mandre + "\n=== END_MANDRELIB ===")

        for doc_dir in doc_dirs:
            if doc_dir == PLUGIN_DOC_DIR:
                example_dir_name = PLUGIN_EXAMPLES_DIR
            elif doc_dir == ETG_DOC_DIR:
                example_dir_name = ETG_EXAMPLES_DIR
            else:
                example_dir_name = MODULE_EXAMPLES_DIR

            example_dir = os.path.join(repo_dir, doc_dir, example_dir_name)
            if os.path.isdir(example_dir):
                example_parts = []
                total_size = 0
                for root, _dirs, files in os.walk(example_dir):
                    for fname in sorted(files, key=str.lower):
                        path = os.path.join(root, fname)
                        rel = os.path.relpath(path, example_dir)
                        try:
                            content = open(path, "r", encoding="utf-8").read().strip()
                        except Exception:
                            content = ""
                        if not content:
                            continue
                        if len(content) > MAX_EXAMPLE_BYTES:
                            continue
                        ext = os.path.splitext(fname)[1].lower()
                        lang = "text"
                        if ext in {".py", ".pyi", ".plugin"}:
                            lang = "python"
                        elif ext in {".md", ".markdown"}:
                            lang = "markdown"
                        snippet = f"FILE: {rel}\n```{lang}\n{content}\n```"
                        if total_size + len(snippet) > MAX_EXAMPLES_TOTAL:
                            break
                        example_parts.append(snippet)
                        total_size += len(snippet)
                    if total_size >= MAX_EXAMPLES_TOTAL:
                        break
                if example_parts:
                    parts.append(
                        "=== EXAMPLES ===\n"
                        + "\n\n".join(example_parts)
                        + "\n=== END_EXAMPLES ==="
                    )

        return "\n\n".join(parts).strip()

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
            entries.append((f"builtin:{name}", f"{name} (builtin)"))
        for filename in self._list_prompt_files():
            entries.append((f"file:{filename}", filename))
        return entries

    def _selected_prompt_entries(self) -> typing.List[str]:
        return list(self.config["prompt_entries"] or [])

    def _resolve_prompt_entry(self, entry: str) -> str:
        if entry.startswith("builtin:"):
            name = entry.split(":", 1)[1].strip()
            return BUILTIN_PROMPTS.get(name, "")
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

    def _read_prompt_file(self, filename: str) -> str:
        path = os.path.join(self._prompts_dir(), filename)
        if not os.path.isfile(path):
            raise FileNotFoundError(filename)
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read().strip()

    @staticmethod
    def _guess_mime(filename: str, mime: str) -> str:
        if mime:
            return mime
        guess = mimetypes.guess_type(filename)[0]
        return guess or "application/octet-stream"

    @staticmethod
    def _looks_like_text(text: str) -> bool:
        if not text:
            return False
        printable = sum(1 for ch in text if ch.isprintable() or ch in "\n\r\t")
        return printable / max(len(text), 1) > 0.85

    async def _collect_attachments(
        self,
        message: typing.Optional[Message],
        reply: typing.Optional[Message],
        *,
        exclude_names: typing.Optional[typing.Set[str]] = None,
    ) -> typing.List[dict]:
        items: typing.List[dict] = []
        exclude_names = exclude_names or set()
        for msg in (message, reply):
            if not msg or not msg.media:
                continue
            if len(items) >= MAX_ATTACH_FILES:
                break
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
            if filename in exclude_names:
                continue
            mime = self._guess_mime(filename, mime)
            size = len(raw)

            is_binary = True
            text = ""
            truncated = False
            if msg.photo or mime.startswith(("image/", "video/", "audio/")):
                is_binary = True
            else:
                snippet = raw[:MAX_ATTACH_BYTES]
                truncated = size > MAX_ATTACH_BYTES
                if b"\x00" not in snippet:
                    decoded = snippet.decode("utf-8", errors="replace")
                    if self._looks_like_text(decoded):
                        text = decoded
                        is_binary = False

            items.append(
                {
                    "name": filename,
                    "mime": mime,
                    "size": size,
                    "binary": is_binary,
                    "text": text,
                    "truncated": truncated,
                }
            )
        return items

    @staticmethod
    def _format_attachments(items: typing.List[dict]) -> str:
        parts = []
        for info in items:
            header = f"{info['name']} ({info['mime']}, {info['size']} bytes)"
            if info.get("binary"):
                parts.append(f"Файл: {header}\n[БИНАРНОЕ ВЛОЖЕНИЕ]")
                continue
            body = info.get("text", "")
            if info.get("truncated"):
                body = (body + "\n...[truncated]").strip()
            parts.append(f"Файл: {header}\n{body}".strip())
        return "\n\n".join(parts)

    def _ai_root(self) -> str:
        root = os.path.join(self._base_root(), AI_DIR_NAME)
        os.makedirs(root, exist_ok=True)
        return root

    def _dialogs_list(self) -> typing.List[str]:
        if self._dialogs is None:
            self._dialogs = self.pointer("dialogs", [])
        return list(self._dialogs)

    def _add_dialog(self, dialog_id: str) -> None:
        if self._dialogs is None:
            self._dialogs = self.pointer("dialogs", [])
        if dialog_id not in self._dialogs:
            self._dialogs.append(dialog_id)

    def _remove_dialog(self, dialog_id: str) -> None:
        if self._dialogs is None:
            self._dialogs = self.pointer("dialogs", [])
        if dialog_id in self._dialogs:
            self._dialogs.remove(dialog_id)

    def _active_dialog(self) -> str:
        return (self.get("active_dialog") or "").strip()

    def _set_active_dialog(self, dialog_id: str) -> None:
        self.set("active_dialog", dialog_id)

    def _clear_active_dialog(self) -> None:
        self.set("active_dialog", "")

    def _dialog_dir(self, dialog_id: str) -> str:
        return os.path.join(self._ai_root(), dialog_id)

    def _module_path(self, dialog_id: str) -> str:
        return os.path.join(self._dialog_dir(dialog_id), MODULE_FILENAME)

    def _changelog_path(self, dialog_id: str) -> str:
        return os.path.join(self._dialog_dir(dialog_id), CHANGELOG_FILENAME)

    def _filename_path(self, dialog_id: str) -> str:
        return os.path.join(self._dialog_dir(dialog_id), FILENAME_FILENAME)

    def _kind_path(self, dialog_id: str) -> str:
        return os.path.join(self._dialog_dir(dialog_id), KIND_FILENAME)

    def _read_kind(self, dialog_id: str) -> str:
        value = self._read_text(self._kind_path(dialog_id)).strip().lower()
        return value if value in ("module", "plugin") else "module"

    @staticmethod
    def _normalize_kind(kind: str) -> str:
        return "plugin" if kind == "plugin" else "module"

    @classmethod
    def _is_plugin(cls, kind: str) -> bool:
        return cls._normalize_kind(kind) == "plugin"

    def _write_kind(self, dialog_id: str, kind: str) -> None:
        self._write_text(self._kind_path(dialog_id), self._normalize_kind(kind))

    def _dialog_exists(self, dialog_id: str) -> bool:
        return os.path.isdir(self._dialog_dir(dialog_id))

    def _new_dialog_id(self) -> str:
        while True:
            dialog_id = secrets.token_hex(4)
            if not self._dialog_exists(dialog_id):
                return dialog_id

    def _create_dialog(self, kind: str) -> str:
        dialog_id = self._new_dialog_id()
        path = self._dialog_dir(dialog_id)
        os.makedirs(path, exist_ok=True)
        module_path = self._module_path(dialog_id)
        changelog_path = self._changelog_path(dialog_id)
        filename_path = self._filename_path(dialog_id)
        normalized = self._normalize_kind(kind)
        if not os.path.exists(module_path):
            with open(module_path, "w", encoding="utf-8") as handle:
                handle.write("")
        if not os.path.exists(changelog_path):
            with open(changelog_path, "w", encoding="utf-8") as handle:
                handle.write("")
        if not os.path.exists(filename_path):
            with open(filename_path, "w", encoding="utf-8") as handle:
                handle.write(MODULE_FILENAME if normalized == "module" else PLUGIN_FILENAME)
        self._write_kind(dialog_id, normalized)
        self._add_dialog(dialog_id)
        self._set_active_dialog(dialog_id)
        return dialog_id

    def _ensure_dialog(self, kind: str) -> str:
        dialog_id = self._active_dialog()
        if dialog_id and self._dialog_exists(dialog_id):
            if self._read_kind(dialog_id) == self._normalize_kind(kind):
                return dialog_id
        return self._create_dialog(kind)

    def _read_text(self, path: str) -> str:
        if not os.path.isfile(path):
            return ""
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return handle.read().strip()
        except Exception:
            return ""

    def _write_text(self, path: str, text: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text.strip() + "\n")

    def _read_filename(self, dialog_id: str) -> str:
        name = self._read_text(self._filename_path(dialog_id)).strip()
        if name and name.endswith((".py", ".plugin")):
            return name
        return MODULE_FILENAME if self._read_kind(dialog_id) == "module" else PLUGIN_FILENAME

    def _write_filename(self, dialog_id: str, name: str) -> None:
        if not name or not name.endswith((".py", ".plugin")):
            return
        self._write_text(self._filename_path(dialog_id), name)

    def _append_changelog(self, path: str, text: str) -> None:
        if not text.strip():
            return
        existing = self._read_text(path)
        combined = text.strip() if not existing else existing.rstrip() + "\n\n" + text.strip()
        self._write_text(path, combined)

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

    @staticmethod
    def _looks_like_code(text: str) -> bool:
        markers = ("import ", "from ", "@loader.", "class ", "async def ")
        return any(marker in text for marker in markers)

    @staticmethod
    def _extract_filename(text: str, exts: typing.Sequence[str]) -> typing.Optional[str]:
        ext_pattern = "|".join(re.escape(ext.lstrip(".")) for ext in exts)
        patterns = (
            rf"(?im)^\s*filename\s*[:=]\s*([\w.-]+\.({ext_pattern}))\s*$",
            rf"(?im)^\s*file\s*[:=]\s*([\w.-]+\.({ext_pattern}))\s*$",
            rf"(?im)^\s*имя\s*файла\s*[:=]\s*([\w.-]+\.({ext_pattern}))\s*$",
        )
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def _strip_filename_line(code: str, exts: typing.Sequence[str]) -> str:
        lines = code.splitlines()
        if not lines:
            return code
        ext_pattern = "|".join(re.escape(ext.lstrip(".")) for ext in exts)
        if re.match(
            rf"(?im)^\s*(filename|file|имя\s*файла)\s*[:=]\s*[\w.-]+\.({ext_pattern})\s*$",
            lines[0],
        ):
            return "\n".join(lines[1:]).strip()
        return code.strip()

    def _extract_blocks(
        self, text: str, exts: typing.Sequence[str]
    ) -> typing.Optional[typing.Tuple[str, str, str]]:
        filename = self._extract_filename(text, exts) or ""
        blocks = list(
            re.finditer(r"```(?:[a-zA-Z0-9_-]+)?\n(.*?)```", text, re.S)
        )
        if len(blocks) >= 2:
            code = self._strip_filename_line(blocks[0].group(1).strip(), exts)
            changelog = blocks[1].group(1).strip()
            if code and changelog:
                return code, changelog, filename

        if len(blocks) == 1:
            block = blocks[0]
            before = text[: block.start()].strip()
            inside = self._strip_filename_line(block.group(1).strip(), exts)
            after = text[block.end() :].strip()
            if before and inside:
                if self._looks_like_code(before) and not self._looks_like_code(inside):
                    return before, inside, filename
                if self._looks_like_code(inside) and after:
                    return inside, after, filename
                if not after:
                    return before, inside, filename

        markers = ("CHANGELOG:", "Changelog:", "Изменения:", "ИЗМЕНЕНИЯ:")
        for marker in markers:
            if marker in text:
                before, _, after = text.partition(marker)
                code = before.strip()
                changelog = after.strip()
                if code and changelog:
                    return code, changelog, filename

        return None

    @staticmethod
    def _extract_patch_filename(patch_text: str) -> str:
        for line in patch_text.splitlines():
            if line.startswith("*** Update File:"):
                return line.split(":", 1)[1].strip()
            if line.startswith("*** Add File:"):
                return line.split(":", 1)[1].strip()
        return ""

    def _extract_patch_blocks(self, text: str) -> typing.Optional[typing.Tuple[str, str, str]]:
        blocks = list(
            re.finditer(r"```(?:[a-zA-Z0-9_-]+)?\n(.*?)```", text, re.S)
        )
        if len(blocks) >= 2:
            patch = blocks[0].group(1).strip()
            changelog = blocks[1].group(1).strip()
            filename = self._extract_patch_filename(patch)
            if patch and changelog:
                return patch, changelog, filename

        lines = text.splitlines()
        start_idx = None
        end_idx = None
        for idx, line in enumerate(lines):
            if line.strip().startswith("*** Begin Patch"):
                start_idx = idx
                break
        if start_idx is None:
            for idx, line in enumerate(lines):
                if line.strip().startswith("*** Update File:"):
                    start_idx = idx
                    break
        if start_idx is not None:
            for idx in range(start_idx + 1, len(lines)):
                if lines[idx].strip().startswith("*** End Patch"):
                    end_idx = idx
                    break
        if start_idx is not None and end_idx is not None:
            patch = "\n".join(lines[start_idx : end_idx + 1]).strip()
            filename = self._extract_patch_filename(patch)

            changelog = ""
            begin_ch = None
            end_ch = None
            for idx, line in enumerate(lines):
                if re.match(r"(?i)^\\*\\*\\*\\s*begin\\s+changelog", line.strip()):
                    begin_ch = idx + 1
                    continue
                if re.match(r"(?i)^\\*\\*\\*\\s*end\\s+changelog", line.strip()):
                    end_ch = idx
                    break
            if begin_ch is not None:
                if end_ch is None:
                    end_ch = len(lines)
                changelog = "\n".join(lines[begin_ch:end_ch]).strip()
            else:
                for idx, line in enumerate(lines[end_idx + 1 :], start=end_idx + 1):
                    if re.match(r"(?i)^\\s*changelog\\s*[:=]", line.strip()):
                        changelog = "\n".join(lines[idx + 1 :]).strip()
                        break
                if not changelog:
                    tail_lines = lines[end_idx + 1 :]
                    if tail_lines:
                        filtered = [ln for ln in tail_lines if ln.strip().startswith(("+", "~", "-"))]
                        if filtered:
                            changelog = "\n".join(filtered).strip()
                        else:
                            tail = "\n".join(tail_lines).strip()
                            if tail:
                                changelog = tail

            if patch and changelog:
                return patch, changelog, filename
        return None

    @staticmethod
    def _find_subsequence(
        haystack: typing.List[str],
        needle: typing.List[str],
        start: int,
    ) -> typing.Optional[int]:
        if not needle:
            return start
        end = len(haystack) - len(needle) + 1
        for idx in range(start, max(end, start)):
            if haystack[idx : idx + len(needle)] == needle:
                return idx
        return None

    def _apply_patch_text(
        self, original: str, patch_text: str, expected_filename: str = ""
    ) -> typing.Optional[str]:
        self._last_patch_error = ""
        lines = original.splitlines()
        patch_lines = patch_text.splitlines()
        if not patch_lines:
            self._last_patch_error = "Пустой patch."
            return None

        if patch_lines[0].strip() != "*** Begin Patch":
            if any(line.startswith("*** Update File:") for line in patch_lines):
                patch_lines = ["*** Begin Patch"] + patch_lines + ["*** End Patch"]
            else:
                self._last_patch_error = "Patch должен начинаться с *** Begin Patch."
                return None

        i = 1
        search_start = 0
        update_file = ""

        def parse_hunk(hunk_lines: typing.List[str], *, lenient: bool) -> typing.Tuple[typing.List[str], typing.List[str]]:
            old_lines: typing.List[str] = []
            new_lines: typing.List[str] = []
            for hunk_line in hunk_lines:
                if not hunk_line:
                    old_lines.append("")
                    new_lines.append("")
                    continue
                prefix = hunk_line[0]
                if prefix == "+":
                    new_lines.append(hunk_line[1:])
                elif prefix == "-":
                    old_lines.append(hunk_line[1:])
                elif prefix == " ":
                    if lenient:
                        old_lines.append(hunk_line)
                        new_lines.append(hunk_line)
                    else:
                        old_lines.append(hunk_line[1:])
                        new_lines.append(hunk_line[1:])
                else:
                    old_lines.append(hunk_line)
                    new_lines.append(hunk_line)
            return old_lines, new_lines

        while i < len(patch_lines):
            line = patch_lines[i]
            if line.startswith("*** End Patch"):
                break
            if line.startswith("*** Update File:") or line.startswith("*** Add File:"):
                if line.startswith("*** Update File:"):
                    update_file = line.split(":", 1)[1].strip()
                i += 1
                continue
            if line.startswith("*** Delete File:"):
                self._last_patch_error = "Delete File запрещён без запроса."
                return ""
            if line.startswith("@@"):
                i += 1
                hunk_lines = []
                while i < len(patch_lines):
                    marker = patch_lines[i]
                    if marker.startswith(("@@", "*** End Patch", "*** Update File:", "*** Add File:", "*** Delete File:")):
                        break
                    if marker.startswith("\\"):
                        i += 1
                        continue
                    hunk_lines.append(marker)
                    i += 1

                old, new = parse_hunk(hunk_lines, lenient=False)
                idx = self._find_subsequence(lines, old, search_start)
                if idx is None:
                    old, new = parse_hunk(hunk_lines, lenient=True)
                    idx = self._find_subsequence(lines, old, search_start)
                if idx is None:
                    snippet = "\n".join(old[:5]).strip()
                    if snippet:
                        self._last_patch_error = (
                            "Контекст хунка не найден в файле.\n" + snippet
                        )
                    else:
                        self._last_patch_error = "Контекст хунка не найден в файле."
                    return None
                lines = lines[:idx] + new + lines[idx + len(old) :]
                search_start = idx + len(new)
                continue

            i += 1

        if expected_filename and update_file and update_file != expected_filename:
            self._last_patch_error = (
                f"Файл в patch: {update_file} (ожидался {expected_filename})"
            )
            return None

        return "\n".join(lines)

    @staticmethod
    def _format_changelog(changelog: str) -> str:
        lines = [line.strip() for line in changelog.splitlines() if line.strip()]
        if not lines:
            return "<blockquote expandable>(пусто)</blockquote>"
        safe_lines = [utils.escape_html(line) for line in lines]
        return "<blockquote expandable>\n" + "\n".join(safe_lines) + "\n</blockquote>"

    @staticmethod
    def _decorate_caption(caption: str, kind: str) -> str:
        if kind != "plugin":
            return caption
        note = "Не забудьте о библиотеке! <code>.mandre</code>"
        return caption + "\n" + note if caption else note

    @staticmethod
    def _raw_block(text: str) -> str:
        safe = utils.escape_html(text or "")
        return f"<blockquote expandable>{safe}</blockquote>"

    @staticmethod
    def _clip_text(text: str, limit: int = 3500) -> str:
        if not text:
            return ""
        if len(text) <= limit:
            return text
        head = text[: max(0, limit - 200)].rstrip()
        tail = text[-120:].rstrip()
        return f"{head}\n...\n{tail}"

    def _split_pages(self, text: str) -> typing.List[str]:
        pages = list(utils.smart_split(*html.parse(text), length=INLINE_PAGE_LEN))
        return pages or [text]

    async def _send_long_edit(
        self,
        message: Message,
        text: str,
        filename: str,
        note: str = "Ответ слишком длинный — открыл список.",
    ) -> None:
        pages = self._split_pages(text)
        if len(pages) == 1 and len(pages[0]) <= 4096:
            try:
                await message.edit(pages[0])
                return
            except Exception:
                pass
        if len(pages) > INLINE_MAX_PAGES:
            file = io.BytesIO(text.encode("utf-8"))
            file.name = filename
            await utils.answer_file(message, file, caption="Слишком большой вывод.")
            pages = pages[:INLINE_MAX_PAGES]
        try:
            await self.inline.list(message, pages, ttl=10 * 60, silent=True)
        except Exception:
            file = io.BytesIO(text.encode("utf-8"))
            file.name = filename
            await utils.answer_file(message, file, caption="Слишком большой вывод.")
            return
        try:
            await message.edit(note)
        except Exception:
            pass

    async def _send_long_answer(
        self,
        message: Message,
        text: str,
        filename: str,
        note: str = "Слишком большой вывод.",
    ) -> None:
        pages = self._split_pages(text)
        if len(pages) == 1 and len(pages[0]) <= 4096:
            await utils.answer(message, pages[0])
            return
        if len(pages) > INLINE_MAX_PAGES:
            file = io.BytesIO(text.encode("utf-8"))
            file.name = filename
            await utils.answer_file(message, file, caption=note)
            pages = pages[:INLINE_MAX_PAGES]
        try:
            await self.inline.list(message, pages, ttl=10 * 60, silent=True)
        except Exception:
            file = io.BytesIO(text.encode("utf-8"))
            file.name = filename
            await utils.answer_file(message, file, caption=note)
            return

    @staticmethod
    def _find_bad_patch_lines(patch_text: str) -> typing.List[str]:
        bad = []
        markers = ("todo", "здесь", "пример", "placeholder", "часть кода")
        for line in patch_text.splitlines():
            if not line.startswith("+"):
                continue
            content = line[1:].strip()
            if not content:
                continue
            lowered = content.lower()
            if content == "pass" or content == "...":
                bad.append(line)
                continue
            if lowered.startswith("#") and any(m in lowered for m in markers):
                bad.append(line)
                continue
            if "todo" in lowered and lowered.startswith("#"):
                bad.append(line)
                continue
        return bad

    def _get_extra_prompts(self) -> str:
        if not self.config["prompt_enabled"]:
            return ""
        entries = self._selected_prompt_entries()
        if not entries:
            return ""
        parts = []
        for entry in entries:
            text = self._resolve_prompt_entry(entry)
            if text:
                parts.append(text)
        return "\n\n".join(parts).strip()

    def _compose_system_prompt(self, kind: str, patch_mode: bool) -> str:
        base = self._system_prompt_patch(kind) if patch_mode else self._system_prompt(kind)
        extra_dirs = [ETG_DOC_DIR] if kind == "module_ui" else None
        repo_prompt = self._load_repo_prompt(kind, extra_doc_dirs=extra_dirs)
        extra = self._get_extra_prompts()
        parts = []
        if repo_prompt:
            parts.append(repo_prompt)
        if extra:
            parts.append(extra)
        parts.append(base)
        return "\n\n".join(parts)

    def _system_prompt(self, kind: str) -> str:
        if self._is_plugin(kind):
            return (
                "ТЫ ПИШЕШЬ КОД ПЛАГИНОВ EXTERAGRAM. "
                "ОТВЕЧАЙ СТРОГО ДВУМЯ CODE-БЛОКАМИ И БОЛЬШЕ НИЧЕМ.\n"
                "БЛОК 1: ПОЛНЫЙ КОД ПЛАГИНА (Python). ПЕРВАЯ строка: FILENAME: <имя_файла>.plugin\n"
                "БЛОК 2: CHANGELOG текущих изменений (добавления/изменения/удаления).\n"
                "CHANGELOG: КАЖДАЯ строка начинается с + (добавлено), ~ (изменено), - (удалено).\n"
                "CHANGELOG ТОЛЬКО ЗА ЭТОТ ЗАПРОС, БЕЗ ЗАГОЛОВКОВ.\n"
                "НИКАКИХ вступлений, пояснений, итогов, просьб, благодарностей.\n"
                "Используй mandrelib и BasePlugin, когда это упрощает код или даёт очевидную пользу.\n"
                "ВСЕГДА указывай мета-поля __id__, __name__, __description__, __author__, __version__, __icon__, __min_version__.\n"
                "ЕСЛИ плагин уже существует, делай МИНИМАЛЬНЫЕ правки и сохраняй стиль.\n"
                "НЕ переписывай всё с нуля, только точечные изменения.\n"
                "НЕ добавляй медиа/тесты/комментарии без необходимости.\n"
                "НЕ используй заглушки и placeholders (например: '...','часть кода','TODO').\n"
                "ЗАПРЕЩЕНЫ 'pass' и комментарии вместо реализации. Если нужна функция — пиши полный код.\n"
                "КОД должен быть рабочим и самодостаточным.\n"
                "В CHANGELOG ОБЯЗАТЕЛЬНА строка с зависимостями: '+ PIP: pip install <пакеты>'.\n"
                "Без версий (без ==, >= и т.д.). Если зависимостей нет: '+ PIP: none'.\n"
            )
        return (
            "ТЫ ПИШЕШЬ КОД МОДУЛЕЙ HEROKU USERBOT. "
            "ОТВЕЧАЙ СТРОГО ДВУМЯ CODE-БЛОКАМИ И БОЛЬШЕ НИЧЕМ.\n"
            "БЛОК 1: ПОЛНЫЙ КОД МОДУЛЯ (Python). ПЕРВАЯ строка: FILENAME: <имя_файла>.py\n"
            "БЛОК 2: CHANGELOG текущих изменений (добавления/изменения/удаления).\n"
            "CHANGELOG: КАЖДАЯ строка начинается с + (добавлено), ~ (изменено), - (удалено).\n"
            "CHANGELOG ТОЛЬКО ЗА ЭТОТ ЗАПРОС, БЕЗ ЗАГОЛОВКОВ.\n"
            "НИКАКИХ вступлений, пояснений, итогов, просьб, благодарностей.\n"
            "НЕ используй слово 'плагин', только 'модуль'.\n"
            "ВСЕГДА используй @loader.tds и структуру модулей Heroku.\n"
            "ЕСЛИ модуль уже существует, делай МИНИМАЛЬНЫЕ правки и сохраняй стиль.\n"
            "НЕ переписывай всё с нуля, только точечные изменения.\n"
            "НЕ добавляй медиа/тесты/комментарии без необходимости.\n"
            "НЕ используй заглушки и placeholders (например: '...','часть кода','TODO').\n"
            "ЗАПРЕЩЕНЫ 'pass' и комментарии вместо реализации. Если нужна функция — пиши полный код.\n"
            "КОД должен быть рабочим и самодостаточным.\n"
            "В CHANGELOG ОБЯЗАТЕЛЬНА строка с зависимостями: '+ PIP: pip install <пакеты>'.\n"
            "Без версий (без ==, >= и т.д.). Если зависимостей нет: '+ PIP: none'.\n"
        )

    def _system_prompt_patch(self, kind: str) -> str:
        filename = MODULE_FILENAME if not self._is_plugin(kind) else PLUGIN_FILENAME
        return (
            "Ты редактор кода.\n"
            "Отвечай СТРОГО двумя code-блоками и больше ничем.\n"
            "Блок 1: PATCH в формате apply_patch.\n"
            "Блок 2: CHANGELOG (только строки, каждая начинается с +, ~, -).\n"
            "НИКАКИХ заголовков, пояснений, итогов, просьб.\n"
            "НЕ сокращай, НЕ опускай строки, НЕ используй '...'.\n"
            "Пиши ВСЕ строки полностью и точно, без пропусков.\n"
            "PATCH ДОЛЖЕН ПРИМЕНЯТЬСЯ БЕЗ ОШИБОК.\n"
            "ИСПОЛЬЗУЙ ТОЛЬКО СТРОКИ ИЗ ТЕКУЩЕГО ФАЙЛА КАК КОНТЕКСТ.\n"
            "НЕ ДОБАВЛЯЙ НОВЫЕ ФУНКЦИИ/ПОЛЯ, ЕСЛИ ЭТО НЕ ТРЕБУЕТСЯ ЗАДАНИЕМ.\n"
            "ЗАПРЕЩЕНЫ 'pass', 'TODO', 'здесь будет код', 'пример', '...'.\n"
            "ЗАПРЕЩЕНЫ КОММЕНТАРИИ ВМЕСТО КОДА. ПИШИ ПОЛНУЮ РЕАЛИЗАЦИЮ.\n"
            "PATCH ОБЯЗАТЕЛЬНО:\n"
            "- Начинается '*** Begin Patch'\n"
            f"- Содержит '*** Update File: {filename}' (имя строго из поля ИМЯ ФАЙЛА)\n"
            "- Ханки с @@ и строки только с префиксом ' ', '+', '-'\n"
            "- Заканчивается '*** End Patch'\n"
            "В CHANGELOG ОБЯЗАТЕЛЬНА строка: '+ PIP: pip install <пакеты>' или '+ PIP: none'.\n"
            "Без версий (без ==, >= и т.д.).\n"
            "ЗАПРЕЩЕНО:\n"
            "- 'Begin Changelog', 'End Changelog'\n"
            "- любые заглушки/комментарии про части кода\n"
            "- 'TODO', '...'\n"
            "- любой текст вне двух code-блоков\n"
            "\nФОРМАТ ОТВЕТА (строго):\n"
            "```patch\n"
            "*** Begin Patch\n"
            f"*** Update File: {filename}\n"
            "@@\n"
            " ...\n"
            "*** End Patch\n"
            "```\n"
            "```text\n"
            "+ ...\n"
            "```\n"
        )

    def _build_user_prompt(
        self, request: str, code: str, changelog: str, filename: str, kind: str
    ) -> str:
        label = "МОДУЛЬ" if not self._is_plugin(kind) else "ПЛАГИН"
        return (
            "ЗАДАНИЕ:\n"
            f"{request.strip()}\n\n"
            f"ИМЯ ФАЙЛА: {filename}\n\n"
            f"ТЕКУЩИЙ {label} ({filename}):\n"
            "```python\n"
            f"{code.strip()}\n"
            "```\n\n"
            "ТЕКУЩИЙ CHANGELOG (changelog.txt):\n"
            "```text\n"
            f"{changelog.strip()}\n"
            "```\n"
        )

    def _build_patch_prompt(
        self, request: str, code: str, changelog: str, filename: str, kind: str
    ) -> str:
        label = "МОДУЛЬ" if not self._is_plugin(kind) else "ПЛАГИН"
        return (
            "ЗАДАНИЕ:\n"
            f"{request.strip()}\n\n"
            f"ИМЯ ФАЙЛА: {filename}\n\n"
            f"ТЕКУЩИЙ {label}:\n"
            "```python\n"
            f"{code.strip()}\n"
            "```\n\n"
            "ТЕКУЩИЙ CHANGELOG:\n"
            "```text\n"
            f"{changelog.strip()}\n"
            "```\n"
        )

    def _build_patch_retry_prompt(
        self,
        request: str,
        code: str,
        changelog: str,
        filename: str,
        error: str,
        kind: str,
    ) -> str:
        return (
            "ПРЕДЫДУЩИЙ PATCH НЕ ПОДХОДИТ.\n"
            f"ОШИБКА:\n{error.strip()}\n"
            "ИСПРАВЬ PATCH. НЕ ПОВТОРЯЙ ОШИБКУ.\n"
            "ИСПОЛЬЗУЙ ТОЧНЫЕ СТРОКИ ИЗ ТЕКУЩЕГО ФАЙЛА КАК КОНТЕКСТ.\n\n"
            + self._build_patch_prompt(request, code, changelog, filename, kind)
        )

    async def _run_patch_flow(
        self,
        msg: Message,
        request: str,
        current_code: str,
        current_changelog: str,
        current_filename: str,
        model: str,
        kind: str,
    ) -> typing.Optional[typing.Tuple[str, str, str, str]]:
        prompt = self._build_patch_prompt(
            request, current_code, current_changelog, current_filename, kind
        )
        last_raw = ""
        last_error = ""
        for attempt in range(2):
            try:
                answer = await self._request_chat(prompt, model, kind, patch_mode=True)
            except Exception as exc:
                await self._send_long_edit(
                    msg,
                    "Ошибка запроса:\n" + self._raw_block(str(exc)),
                    "aimaker_error.txt",
                )
                return None

            raw_answer = answer
            last_raw = raw_answer
            answer = self._strip_reasoning(answer)
            blocks = self._extract_patch_blocks(answer)
            if not blocks:
                last_error = "Ответ должен содержать PATCH и changelog."
                if attempt == 0:
                    prompt = self._build_patch_retry_prompt(
                        request,
                        current_code,
                        current_changelog,
                        current_filename,
                        last_error,
                        kind,
                    )
                    continue
                await self._send_long_edit(
                    msg,
                    self._raw_block("Ошибка: ответ должен содержать PATCH и changelog.")
                    + "\n"
                    + self._raw_block(last_raw),
                    "aimaker_error.txt",
                )
                return None

            patch, changelog, filename = blocks
            bad_lines = self._find_bad_patch_lines(patch)
            if bad_lines:
                last_error = "Запрещённые заглушки:\n" + "\n".join(bad_lines[:10])
                if attempt == 0:
                    prompt = self._build_patch_retry_prompt(
                        request,
                        current_code,
                        current_changelog,
                        current_filename,
                        last_error,
                        kind,
                    )
                    continue
                await self._send_long_edit(
                    msg,
                    self._raw_block("Ошибка: в PATCH есть заглушки.")
                    + "\n"
                    + self._raw_block(last_raw)
                    + "\n"
                    + self._raw_block(last_error),
                    "aimaker_error.txt",
                )
                return None

            updated = self._apply_patch_text(
                current_code, patch, expected_filename=current_filename
            )
            if updated is None:
                last_error = self._last_patch_error or "Patch не применился."
                if attempt == 0:
                    prompt = self._build_patch_retry_prompt(
                        request,
                        current_code,
                        current_changelog,
                        current_filename,
                        last_error,
                        kind,
                    )
                    continue
                await self._send_long_edit(
                    msg,
                    self._raw_block("Ошибка: не удалось применить patch.")
                    + "\n"
                    + self._raw_block(last_raw)
                    + ("\n" + self._raw_block(last_error) if last_error else ""),
                    "aimaker_error.txt",
                )
                return None

            filename = filename or current_filename or (
                MODULE_FILENAME if not self._is_plugin(kind) else PLUGIN_FILENAME
            )
            return updated, changelog, filename, raw_answer
        return None

    def _build_compile_request(self, request: str, report: str, kind: str) -> str:
        label = "МОДУЛЬ" if not self._is_plugin(kind) else "ПЛАГИН"
        return (
            f"ИСПРАВЬ ОШИБКИ КОМПИЛЯЦИИ {label}.\n"
            f"ЗАДАНИЕ:\n{request.strip()}\n\n"
            "ОТЧЁТ КОМПИЛЯЦИИ:\n"
            f"{self._clip_text(report, 3000)}\n"
        )

    async def _validate_and_fix(
        self,
        msg: Message,
        request: str,
        code: str,
        changelog: str,
        filename: str,
        model: str,
        kind: str,
        dialog_id: str,
    ) -> typing.Tuple[str, str, str, bool, str]:
        current_code = code
        current_changelog = changelog
        current_filename = filename
        session_changes = [changelog] if changelog.strip() else []
        last_report = ""

        for attempt in range(1, 6):
            try:
                await msg.edit(f"Проверяю ({attempt}/5)...")
            except Exception:
                pass
            ok, report = self._compile_check(
                dialog_id, current_filename, current_code, current_changelog
            )
            last_report = report
            if ok:
                combined = "\n\n".join([c for c in session_changes if c.strip()])
                return current_code, combined, current_filename, True, report

            if attempt >= 5:
                combined = "\n\n".join([c for c in session_changes if c.strip()])
                return current_code, combined, current_filename, False, report

            fix_request = self._build_compile_request(request, report, kind)
            result = await self._run_patch_flow(
                msg,
                fix_request,
                current_code,
                current_changelog,
                current_filename,
                model,
                kind,
            )
            if not result:
                combined = "\n\n".join([c for c in session_changes if c.strip()])
                return current_code, combined, current_filename, False, report

            current_code, delta_changelog, current_filename, _raw = result
            if delta_changelog.strip():
                session_changes.append(delta_changelog)
                current_changelog = (
                    current_changelog.rstrip() + "\n\n" + delta_changelog.strip()
                    if current_changelog.strip()
                    else delta_changelog.strip()
                )

        combined = "\n\n".join([c for c in session_changes if c.strip()])
        return current_code, combined, current_filename, False, last_report

    def _models_url(self) -> str:
        value = (self.config["models_url"] or "").strip()
        return value or MODELS_URL

    @staticmethod
    def _is_default_models_url(url: str) -> bool:
        return url.rstrip("/") == MODELS_URL.rstrip("/")

    @staticmethod
    def _dedupe_models(items: typing.Iterable[typing.Any]) -> typing.List[str]:
        seen = set()
        result = []
        for item in items:
            name = str(item).strip()
            if not name or name in seen:
                continue
            seen.add(name)
            result.append(name)
        return result

    def _extract_models(self, data: typing.Any) -> typing.List[str]:
        if isinstance(data, dict):
            classified = data.get("classified")
            if isinstance(classified, dict):
                text_models = classified.get("text")
                if isinstance(text_models, list):
                    return self._dedupe_models(text_models)
            for key in ("models", "model_list"):
                models = data.get(key)
                if isinstance(models, list):
                    return self._dedupe_models(models)
            raw_data = data.get("data")
            if isinstance(raw_data, list):
                names = []
                for item in raw_data:
                    if isinstance(item, str):
                        names.append(item)
                        continue
                    if isinstance(item, dict):
                        for field in ("id", "name", "model"):
                            value = item.get(field)
                            if value:
                                names.append(value)
                                break
                return self._dedupe_models(names)
        if isinstance(data, list):
            return self._dedupe_models(data)
        return []

    async def _fetch_models(self) -> typing.Tuple[typing.Any, str]:
        url = self._models_url()
        response = await self._request("GET", url, timeout=None)
        if response.status_code in (500, 502):
            raise RuntimeError(SERVICE_ERROR_TEXT)
        response.raise_for_status()
        return response.json(), url

    async def _get_model_list(self) -> typing.List[str]:
        data, url = await self._fetch_models()
        models = self._extract_models(data)
        if self._is_default_models_url(url):
            allowed = [name for name in ALLOWED_MODELS if name in models]
            return allowed or [name for name in ALLOWED_MODELS]
        return models

    def _pick_model(self) -> str:
        model = (self.config["model"] or "").strip()
        if model:
            return model
        fallback = ALLOWED_MODELS[0] if ALLOWED_MODELS else DEFAULT_TEXT_MODEL
        self.config["model"] = fallback
        return fallback

    @staticmethod
    def _format_model_list(models: typing.List[str]) -> str:
        return "\n".join(f"{idx + 1}. {name}" for idx, name in enumerate(models))

    @staticmethod
    def _extract_api_error(response: requests.Response) -> str:
        raw = response.text.strip()
        if not raw:
            try:
                raw = response.content.decode("utf-8", errors="replace").strip()
            except Exception:
                raw = ""
        return raw or f"HTTP {response.status_code}"

    async def _request_chat(
        self, prompt: str, model: str, kind: str, *, patch_mode: bool = False
    ) -> str:
        key = self._get_api_key()
        headers = {"Authorization": f"Bearer {key}"}
        messages = [
            {"role": "system", "content": self._compose_system_prompt(kind, patch_mode)},
            {"role": "user", "content": prompt},
        ]

        endpoint = (self.config["api_endpoint"] or CHAT_URL_OPENAI).strip() or CHAT_URL_OPENAI
        payload = {"model": model, "messages": messages, "stream": False}

        response = await self._request(
            "POST",
            endpoint,
            headers=headers,
            json=payload,
            timeout=None,
        )
        if response.status_code in (500, 502):
            raise RuntimeError(SERVICE_ERROR_TEXT)
        if response.status_code in (401, 403):
            raise RuntimeError("Токен API истёк или неверный. Обнови api_key в конфиге.")
        if response.status_code >= 400:
            raise RuntimeError(self._extract_api_error(response))
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

    @staticmethod
    def _extract_prompt(message: Message, reply: typing.Optional[Message]) -> str:
        args = utils.get_args_raw(message).strip()
        reply_text = reply.raw_text.strip() if reply and reply.raw_text else ""
        if args and reply_text:
            return f"{args}\n\nКонтекст: {reply_text}"
        if reply_text:
            return reply_text
        if args:
            return args
        return ""

    @staticmethod
    def _kind_labels(kind: str) -> typing.Tuple[str, str]:
        if AIMakerMod._is_plugin(kind):
            return "плагин", "плагина"
        return "модуль", "модуля"

    async def _run_generate(self, message: Message, kind: str):
        reply = await message.get_reply_message() if message.is_reply else None
        request = self._extract_prompt(message, reply)
        attachments = await self._collect_attachments(message, reply)
        if attachments:
            att_text = self._format_attachments(attachments)
            request = (request or "").strip()
            request = f"{request}\n\nВЛОЖЕНИЯ:\n{att_text}".strip()

        label, label_gen = self._kind_labels(kind)
        if not request:
            await utils.answer(message, f"Нужен текст запроса для {label_gen}.")
            return

        dialog_id = self._ensure_dialog(kind)
        module_path = self._module_path(dialog_id)
        changelog_path = self._changelog_path(dialog_id)
        current_code = self._read_text(module_path)
        current_changelog = self._read_text(changelog_path)
        current_filename = self._read_filename(dialog_id)

        exts = (".py",) if not self._is_plugin(kind) else (".plugin",)
        model = self._pick_model()
        msg = await utils.answer(message, "Думаю...")

        if current_code.strip():
            result = await self._run_patch_flow(
                msg,
                request,
                current_code,
                current_changelog,
                current_filename,
                model,
                kind,
            )
            if not result:
                return
            updated, changelog, filename, _raw = result
            updated, session_changelog, filename, ok, report = await self._validate_and_fix(
                msg,
                request,
                updated,
                changelog,
                filename,
                model,
                kind,
                dialog_id,
            )

            self._write_text(module_path, updated)
            if session_changelog.strip():
                self._append_changelog(changelog_path, session_changelog)
            self._write_filename(dialog_id, filename)

            file = io.BytesIO(updated.encode("utf-8"))
            file.name = filename
            await utils.answer_file(
                msg,
                file,
                caption=self._decorate_caption(self._format_changelog(session_changelog or changelog), kind),
            )
            if not ok and report:
                await self._send_long_answer(
                    message,
                    "Проверка не пройдена после 5 попыток.\n"
                    + self._raw_block(report),
                    "aimaker_report.txt",
                )
            return

        prompt = self._build_user_prompt(
            request, current_code, current_changelog, current_filename, kind
        )
        answer = None
        raw_answer = ""
        for attempt in range(2):
            try:
                answer = await self._request_chat(prompt, model, kind)
            except Exception as exc:
                await self._send_long_edit(
                    msg,
                    "Ошибка запроса:\n" + self._raw_block(str(exc)),
                    "aimaker_error.txt",
                )
                return

            raw_answer = answer or ""
            answer = self._strip_reasoning(answer or "")
            blocks = self._extract_blocks(answer, exts)
            if blocks:
                break
            if attempt == 0:
                prompt = (
                    "Ответ некорректен. НУЖНЫ ДВА code-блока: код и changelog.\n"
                    "Повтори ответ строго по формату.\n\n" + prompt
                )
        else:
            await self._send_long_edit(
                msg,
                "Ошибка: ответ должен содержать два code-блока.\n"
                + self._raw_block(raw_answer),
                "aimaker_error.txt",
            )
            return

        code, changelog, filename = blocks
        filename = filename or current_filename or (
            MODULE_FILENAME if not self._is_plugin(kind) else PLUGIN_FILENAME
        )

        code, session_changelog, filename, ok, report = await self._validate_and_fix(
            msg,
            request,
            code,
            changelog,
            filename,
            model,
            kind,
            dialog_id,
        )

        self._write_text(module_path, code)
        if session_changelog.strip():
            self._append_changelog(changelog_path, session_changelog)
        self._write_filename(dialog_id, filename)

        file = io.BytesIO(code.encode("utf-8"))
        file.name = filename
        await utils.answer_file(
            msg,
            file,
            caption=self._decorate_caption(self._format_changelog(session_changelog or changelog), kind),
        )
        if not ok and report:
            await self._send_long_answer(
                message,
                "Проверка не пройдена после 5 попыток.\n"
                + self._raw_block(report),
                "aimaker_report.txt",
            )

    @staticmethod
    async def _get_attached_file(
        message: Message, reply: typing.Optional[Message], default_name: str
    ) -> typing.Optional[typing.Tuple[str, bytes]]:
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
                name = default_name
            return name, data
        return None

    @loader.command(ru_doc="Создать/обновить модуль через AI")
    async def mod(self, message: Message):
        args = utils.get_args_raw(message).strip().lower()
        if args == "log":
            logs: typing.List[str] = []
            ok = True
            try:
                self._ensure_repo(logs=logs, force=True)
            except Exception as exc:
                ok = False
                logs.append(f"error: {exc}")
            status = "OK" if ok else "Ошибка"
            log_text = "\n".join(logs).strip() or "логов нет"
            await utils.answer(
                message,
                f"Repo log: {utils.escape_html(status)}\n{self._raw_block(log_text)}",
            )
            return
        await self._run_generate(message, "module")

    @loader.command(ru_doc="Создать/обновить модуль с ETG UI через AI")
    async def modui(self, message: Message):
        await self._run_generate(message, "module_ui")

    @loader.command(ru_doc="Создать/обновить плагин через AI")
    async def plug(self, message: Message):
        await self._run_generate(message, "plugin")

    @loader.command(ru_doc="Системные промпты для AIMaker")
    async def modprompt(self, message: Message):
        args_raw = utils.get_args_raw(message).strip()
        if not args_raw:
            enabled = self.config["prompt_enabled"]
            selected = set(self._selected_prompt_entries())
            labels = []
            for key, label in self._list_prompt_entries():
                if key in selected:
                    labels.append(label)
            current = ", ".join(labels) if labels else "—"
            await utils.answer(
                message,
                "Системные промпты: {state}\nВыбрано: {name}\nПапка: {folder}\nДействуют для .mod/.modui/.editmod/.plug/.editplug".format(
                    state="ON" if enabled else "OFF",
                    name=utils.escape_html(current),
                    folder=utils.escape_html(self._prompts_dir()),
                ),
            )
            return

        parts = args_raw.split(maxsplit=1)
        action = parts[0].lower()
        tail = parts[1].strip() if len(parts) > 1 else ""

        if action == "on":
            self.config["prompt_enabled"] = True
            await utils.answer(message, "Системные промпты включены.")
            return

        if action == "off":
            self.config["prompt_enabled"] = False
            await utils.answer(message, "Системные промпты выключены.")
            return

        if action == "send":
            reply = await message.get_reply_message() if message.is_reply else None
            attached = await self._get_prompt_attachment(message, reply)
            if attached:
                filename, text = attached
                if tail and tail.strip().endswith((".txt", ".md", ".prompt")):
                    filename = tail.strip()
                saved = self._save_prompt_text(filename, text)
                await utils.answer(
                    message,
                    f"Промпт сохранен: {utils.escape_html(saved)}",
                )
                return

            reply_text = reply.raw_text.strip() if reply and reply.raw_text else ""
            content = tail or reply_text
            if not content:
                await utils.answer(message, "Нужен текст промпта или файл.")
                return

            filename = ""
            lines = content.splitlines()
            if (
                lines
                and lines[0].strip().endswith((".txt", ".md", ".prompt"))
                and len(lines) > 1
            ):
                filename = lines[0].strip()
                content = "\n".join(lines[1:]).strip()
            saved = self._save_prompt_text(filename, content)
            await utils.answer(
                message,
                f"Промпт сохранен: {utils.escape_html(saved)}",
            )
            return

        if action == "get":
            files = self._list_prompt_files()
            if not files:
                await utils.answer(message, "Промптов нет.")
                return
            if not tail:
                listing = "\n".join(
                    f"{idx + 1}. {utils.escape_html(name)}"
                    for idx, name in enumerate(files)
                )
                await utils.answer(message, "Промпты:\n" + listing)
                return
            filename = ""
            try:
                index = int(tail)
            except ValueError:
                filename = os.path.basename(tail.strip())
            else:
                if index < 1 or index > len(files):
                    await utils.answer(message, "Неверный номер промпта.")
                    return
                filename = files[index - 1]
            if filename not in files:
                await utils.answer(message, "Промпт не найден.")
                return
            path = os.path.join(self._prompts_dir(), filename)
            await utils.answer_file(message, path)
            return

        if action == "del":
            files = self._list_prompt_files()
            if not files:
                await utils.answer(message, "Промптов нет.")
                return
            if not tail:
                listing = "\n".join(
                    f"{idx + 1}. {utils.escape_html(name)}"
                    for idx, name in enumerate(files)
                )
                await utils.answer(message, "Промпты:\n" + listing)
                return
            filename = ""
            try:
                index = int(tail)
            except ValueError:
                filename = os.path.basename(tail.strip())
            else:
                if index < 1 or index > len(files):
                    await utils.answer(message, "Неверный номер промпта.")
                    return
                filename = files[index - 1]
            if filename not in files:
                await utils.answer(message, "Промпт не найден.")
                return
            try:
                os.remove(os.path.join(self._prompts_dir(), filename))
            except Exception:
                await utils.answer(message, "Не удалось удалить промпт.")
                return
            await utils.answer(
                message,
                f"Промпт удален: {utils.escape_html(filename)}",
            )
            return

        if action == "remote":
            entries = self._list_prompt_entries()
            if not entries:
                await utils.answer(
                    message,
                    f"Промптов нет. Положи файлы в {utils.escape_html(self._prompts_dir())}",
                )
                return

            if not tail:
                selected = set(self._selected_prompt_entries())
                listing = []
                for idx, (key, label) in enumerate(entries, start=1):
                    mark = "[x]" if key in selected else "[ ]"
                    listing.append(f"{mark} {idx}. {utils.escape_html(label)}")
                await utils.answer(message, "Доступные промпты:\n" + "\n".join(listing))
                return

            try:
                index = int(tail)
            except ValueError:
                await utils.answer(message, "Нужен номер промпта.")
                return

            if index < 1 or index > len(entries):
                await utils.answer(message, "Неверный номер промпта.")
                return

            selected_key, selected_label = entries[index - 1]
            selected = self._selected_prompt_entries()
            if selected_key in selected:
                selected = [item for item in selected if item != selected_key]
                state = "выключен"
            else:
                selected.append(selected_key)
                state = "включен"
            self.config["prompt_entries"] = selected
            self.config["prompt_enabled"] = True if selected else False
            await utils.answer(
                message,
                f"Промпт {state}: {utils.escape_html(selected_label)}",
            )
            return

        await utils.answer(
            message,
            "Используй: .modprompt on | .modprompt off | .modprompt remote [номер] | .modprompt send | .modprompt get | .modprompt del",
        )

    @loader.command(ru_doc="Редактировать модуль через AI (patch-режим)")
    async def editmod(self, message: Message):
        reply = await message.get_reply_message() if message.is_reply else None
        request = self._extract_prompt(message, reply)
        if not request:
            await utils.answer(message, "Нужен текст запроса.")
            return

        kind = "module"
        dialog_id = self._ensure_dialog(kind)
        module_path = self._module_path(dialog_id)
        changelog_path = self._changelog_path(dialog_id)
        current_changelog = self._read_text(changelog_path)
        current_filename = self._read_filename(dialog_id)

        attached = await self._get_attached_file(message, reply, MODULE_FILENAME)
        if attached:
            filename, data = attached
            if not filename.endswith(".py"):
                await utils.answer(message, "Нужен .py файл.")
                return
            if b"\x00" in data:
                await utils.answer(message, "Файл должен быть текстовым.")
                return
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                text = data.decode("utf-8", errors="replace")
            self._write_text(module_path, text)
            self._write_filename(dialog_id, filename)
            current_filename = filename

        exclude_names = {current_filename} if current_filename else set()
        attachments = await self._collect_attachments(
            message, reply, exclude_names=exclude_names
        )
        if attachments:
            att_text = self._format_attachments(attachments)
            request = f"{request}\n\nВЛОЖЕНИЯ:\n{att_text}".strip()

        current_code = self._read_text(module_path)
        if not current_code:
            await utils.answer(message, "Файл пустой или не найден.")
            return

        model = (self.config["model"] or DEFAULT_TEXT_MODEL).strip()
        msg = await utils.answer(message, "Думаю...")
        result = await self._run_patch_flow(
            msg,
            request,
            current_code,
            current_changelog,
            current_filename,
            model,
            kind,
        )
        if not result:
            return
        updated, changelog, filename, _raw = result
        updated, session_changelog, filename, ok, report = await self._validate_and_fix(
            msg,
            request,
            updated,
            changelog,
            filename,
            model,
            kind,
            dialog_id,
        )

        self._write_text(module_path, updated)
        self._write_filename(dialog_id, filename)
        if session_changelog.strip():
            self._append_changelog(changelog_path, session_changelog)

        file = io.BytesIO(updated.encode("utf-8"))
        file.name = filename
        await utils.answer_file(
            msg,
            file,
            caption=self._decorate_caption(
                self._format_changelog(session_changelog or changelog),
                kind,
            ),
        )
        if not ok and report:
            await self._send_long_answer(
                message,
                "Проверка не пройдена после 5 попыток.\n"
                + self._raw_block(report),
                "aimaker_report.txt",
            )

    @loader.command(ru_doc="Редактировать плагин через AI (patch-режим)")
    async def editplug(self, message: Message):
        reply = await message.get_reply_message() if message.is_reply else None
        request = self._extract_prompt(message, reply)
        if not request:
            await utils.answer(message, "Нужен текст запроса.")
            return

        kind = "plugin"
        dialog_id = self._ensure_dialog(kind)
        module_path = self._module_path(dialog_id)
        changelog_path = self._changelog_path(dialog_id)
        current_changelog = self._read_text(changelog_path)
        current_filename = self._read_filename(dialog_id)

        attached = await self._get_attached_file(message, reply, PLUGIN_FILENAME)
        if attached:
            filename, data = attached
            if not filename.endswith(".plugin"):
                await utils.answer(message, "Нужен .plugin файл.")
                return
            if b"\x00" in data:
                await utils.answer(message, "Файл должен быть текстовым.")
                return
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                text = data.decode("utf-8", errors="replace")
            self._write_text(module_path, text)
            self._write_filename(dialog_id, filename)
            current_filename = filename

        exclude_names = {current_filename} if current_filename else set()
        attachments = await self._collect_attachments(
            message, reply, exclude_names=exclude_names
        )
        if attachments:
            att_text = self._format_attachments(attachments)
            request = f"{request}\n\nВЛОЖЕНИЯ:\n{att_text}".strip()

        current_code = self._read_text(module_path)
        if not current_code:
            await utils.answer(message, "Файл пустой или не найден.")
            return

        model = self._pick_model()
        msg = await utils.answer(message, "Думаю...")
        result = await self._run_patch_flow(
            msg,
            request,
            current_code,
            current_changelog,
            current_filename,
            model,
            kind,
        )
        if not result:
            return
        updated, changelog, filename, _raw = result
        updated, session_changelog, filename, ok, report = await self._validate_and_fix(
            msg,
            request,
            updated,
            changelog,
            filename,
            model,
            kind,
            dialog_id,
        )

        self._write_text(module_path, updated)
        self._write_filename(dialog_id, filename)
        if session_changelog.strip():
            self._append_changelog(changelog_path, session_changelog)

        file = io.BytesIO(updated.encode("utf-8"))
        file.name = filename
        await utils.answer_file(
            msg,
            file,
            caption=self._decorate_caption(
                self._format_changelog(session_changelog or changelog),
                kind,
            ),
        )
        if not ok and report:
            await self._send_long_answer(
                message,
                "Проверка не пройдена после 5 попыток.\n"
                + self._raw_block(report),
                "aimaker_report.txt",
            )

    @loader.command(aliases=["modmodel"], ru_doc="Список моделей или выбор модели для AIMaker")
    async def models(self, message: Message):
        args = utils.get_args_raw(message).strip()
        try:
            models = await self._get_model_list()
        except Exception as exc:
            await utils.answer(message, f"Ошибка списка моделей: {utils.escape_html(str(exc))}")
            return
        if not models:
            await utils.answer(message, "Список моделей пуст.")
            return

        if not args:
            await utils.answer(message, self._format_model_list(models))
            return

        try:
            index = int(args)
        except ValueError:
            await utils.answer(message, "Нужен номер модели.")
            return

        if index < 1 or index > len(models):
            await utils.answer(message, "Неверный номер модели.")
            return

        model = models[index - 1]
        self.config["model"] = model
        await utils.answer(message, f"Текущая модель: {utils.escape_html(model)}")

    @loader.command(ru_doc="Выдать MandreLib для плагинов")
    async def mandre(self, message: Message):
        try:
            self._ensure_repo()
        except Exception as exc:
            await utils.answer(message, f"Ошибка репозитория: {utils.escape_html(str(exc))}")
            return
        path = self._mandre_path()
        if not os.path.isfile(path):
            await utils.answer(message, "Файл mandre_lib.plugin не найден.")
            return
        try:
            with open(path, "rb") as handle:
                data = handle.read()
        except Exception:
            await utils.answer(message, "Не удалось прочитать mandre_lib.plugin.")
            return
        file = io.BytesIO(data)
        file.name = "mandre_lib.plugin"
        await utils.answer_file(message, file)

    @loader.command(ru_doc="Переключить/показать диалоги")
    async def dial(self, message: Message):
        args = utils.get_args_raw(message).strip()
        dialogs = self._dialogs_list()
        active = self._active_dialog()

        if not args:
            if not dialogs:
                await utils.answer(message, "Диалоги отсутствуют.")
                return
            active_kind = self._read_kind(active) if active else "—"
            lines = [
                f"Активный: <code>{utils.escape_html(active or '—')}</code> ({utils.escape_html(active_kind)})"
            ]
            for idx, dialog_id in enumerate(dialogs, start=1):
                kind = self._read_kind(dialog_id)
                lines.append(f"{idx}. <code>{utils.escape_html(dialog_id)}</code> ({utils.escape_html(kind)})")
            await utils.answer(message, "\n".join(lines))
            return

        dialog_id = args
        if dialog_id not in dialogs and not self._dialog_exists(dialog_id):
            await utils.answer(message, "Диалог не найден.")
            return

        if dialog_id not in dialogs:
            self._add_dialog(dialog_id)
        self._set_active_dialog(dialog_id)
        await utils.answer(
            message,
            "Активный диалог: <code>{}</code> ({})".format(
                utils.escape_html(dialog_id),
                utils.escape_html(self._read_kind(dialog_id)),
            ),
        )

    @loader.command(ru_doc="Выйти из текущего диалога")
    async def exitdial(self, message: Message):
        self._clear_active_dialog()
        await utils.answer(message, "Диалог сброшен.")

    @loader.command(ru_doc="Удалить активный диалог")
    async def deldial(self, message: Message):
        args = utils.get_args_raw(message).strip()
        dialog_id = args or self._active_dialog()
        if not dialog_id:
            await utils.answer(message, "Нет выбранного диалога.")
            return
        if not self._dialog_exists(dialog_id):
            await utils.answer(message, "Диалог не найден.")
            return

        try:
            import shutil

            shutil.rmtree(self._dialog_dir(dialog_id))
        except Exception:
            await utils.answer(message, "Не удалось удалить диалог.")
            return

        self._remove_dialog(dialog_id)
        if self._active_dialog() == dialog_id:
            self._clear_active_dialog()
        await utils.answer(message, f"Диалог удален: <code>{utils.escape_html(dialog_id)}</code>")

    @loader.command(ru_doc="Удалить все диалоги и модули")
    async def delalldial(self, message: Message):
        try:
            import shutil

            root = self._ai_root()
            if os.path.isdir(root):
                shutil.rmtree(root)
            os.makedirs(root, exist_ok=True)
        except Exception:
            await utils.answer(message, "Не удалось удалить диалоги.")
            return

        if self._dialogs is None:
            self._dialogs = self.pointer("dialogs", [])
        self._dialogs.clear()
        self._clear_active_dialog()
        await utils.answer(message, "Все диалоги удалены.")
