"""Codex app-server backed provider for Codex Wise.

This provider delegates generation to the user's installed Codex CLI instead of
asking Codex Wise users to configure a separate LLM API key.  It uses the
`codex app-server` JSON-RPC interface for ChatGPT auth, live model discovery,
turn streaming, and token/rate-limit telemetry.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import shlex
import shutil
import sys
import webbrowser
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from codex_wise.core.providers.llm.base import (
    BaseProvider,
    ChatStreamEvent,
    GeneratedResponse,
    ProviderError,
)
from codex_wise.core.rate_limiter import RateLimiter

if TYPE_CHECKING:
    from codex_wise.core.generation.cost_tracker import CostTracker

log = structlog.get_logger(__name__)

_DEFAULT_REQUEST_TIMEOUT = 120.0
_DEFAULT_TURN_TIMEOUT = 1_800.0
_DEFAULT_LOGIN_TIMEOUT = 300.0
_DEFAULT_CODEX_MODEL = "gpt-5.5"
_DEFAULT_REASONING_EFFORT = "medium"
_CLIENT_NAME = "codex_wise"
_CLIENT_TITLE = "Codex Wise"
_CODEX_MODEL_PREFIX = "codex:"

_TURN_NOTIFICATION_METHODS = {
    "turn/started",
    "turn/completed",
    "item/agentMessage/delta",
    "item/completed",
    "thread/tokenUsage/updated",
}


@dataclass(frozen=True)
class CodexModelSelection:
    """Resolved Codex model and reasoning effort."""

    model: str
    reasoning_effort: str | None
    model_info: dict[str, Any]


def _package_version() -> str:
    try:
        return metadata.version("codex-wise")
    except metadata.PackageNotFoundError:
        return "0.0.0"


def _as_bool_env(name: str, default: bool = True) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def resolve_codex_command(command: str | list[str] | tuple[str, ...] | None = None) -> list[str]:
    """Resolve the executable used to start `codex app-server`.

    On Windows, invoking ``codex`` directly can resolve to a launcher shim that
    Python cannot execute.  Prefer ``codex.cmd`` / ``codex.exe`` there.
    """
    configured = command or os.environ.get("CODEX_WISE_CODEX_COMMAND")
    if configured:
        if isinstance(configured, str):
            return shlex.split(configured, posix=os.name != "nt")
        return list(configured)

    candidates = (
        ("codex.cmd", "codex.exe", "codex")
        if sys.platform.startswith("win")
        else ("codex",)
    )
    for candidate in candidates:
        path = shutil.which(candidate)
        if path:
            return [path]

    raise ProviderError(
        "codex",
        "Codex CLI not found. Install Codex or set CODEX_WISE_CODEX_COMMAND.",
    )


def is_codex_cli_available() -> bool:
    """Return True when a runnable Codex CLI command can be resolved."""
    try:
        resolve_codex_command()
    except ProviderError:
        return False
    return True


def choose_codex_model(
    models: list[dict[str, Any]],
    requested_model: str | None = None,
    requested_effort: str | None = None,
) -> CodexModelSelection:
    """Choose a model from app-server's live `model/list` response.

    If the caller does not request a model, the app-server default visible
    model wins.  Reasoning effort follows the selected model's default so the
    recommendation stays controlled by Codex's model catalog.
    """
    visible = [m for m in models if not m.get("hidden")]

    def _model_id(model_info: dict[str, Any]) -> str:
        return str(model_info.get("model") or model_info.get("id") or "")

    selected: dict[str, Any] | None = None
    if requested_model:
        for model_info in models:
            if requested_model in {model_info.get("id"), model_info.get("model")}:
                selected = model_info
                break
        if selected is None:
            available = ", ".join(_model_id(m) for m in visible[:10] if _model_id(m))
            suffix = f" Available models: {available}" if available else ""
            raise ProviderError(
                "codex",
                f"Requested Codex model {requested_model!r} is not available.{suffix}",
            )
    else:
        selected = next((m for m in visible if m.get("isDefault")), None)
        selected = selected or (visible[0] if visible else None)
        selected = selected or (models[0] if models else None)

    if selected is None:
        if requested_model:
            return CodexModelSelection(requested_model, requested_effort, {})
        raise ProviderError("codex", "Codex app-server returned no available models.")

    supported_efforts = _supported_efforts(selected)
    default_effort = selected.get("defaultReasoningEffort")

    if requested_effort:
        if supported_efforts and requested_effort not in supported_efforts:
            raise ProviderError(
                "codex",
                (
                    f"Reasoning effort {requested_effort!r} is not supported by "
                    f"{_model_id(selected)!r}. Supported efforts: {supported_efforts}"
                ),
            )
        effort = requested_effort
    elif isinstance(default_effort, str) and (
        not supported_efforts or default_effort in supported_efforts
    ):
        effort = default_effort
    elif "medium" in supported_efforts:
        effort = "medium"
    elif supported_efforts:
        effort = supported_efforts[0]
    else:
        effort = None

    return CodexModelSelection(_model_id(selected), effort, selected)


def _supported_efforts(model_info: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for effort_info in model_info.get("supportedReasoningEfforts") or []:
        value = (
            effort_info.get("reasoningEffort")
            if isinstance(effort_info, dict)
            else effort_info
        )
        if isinstance(value, str):
            values.append(value)
    return values


def format_codex_model_label(model_info: dict[str, Any]) -> str:
    """Human-readable model label for CLI/server presentation."""
    display = model_info.get("displayName") or model_info.get("model") or model_info.get("id")
    model = model_info.get("model") or model_info.get("id")
    if display and model and display != model:
        return f"{display} ({model})"
    return str(display or model or "unknown")


def _build_developer_instructions(system_prompt: str, max_tokens: int) -> str:
    return (
        "You are the documentation-generation model inside Codex Wise.\n"
        "Return only the requested documentation text. Do not edit files, run shell "
        "commands, ask for approvals, or perform repository mutations. Use the "
        "provided prompt context as the source of truth. If context is insufficient, "
        "say so briefly in the generated documentation rather than inventing details. "
        f"Keep the response within roughly {max_tokens} tokens.\n\n"
        f"{system_prompt}"
    )


def _extract_usage(token_usage: dict[str, Any] | None) -> dict[str, Any]:
    if not token_usage:
        return {}
    last = token_usage.get("last") or {}
    total = token_usage.get("total") or {}
    usage = {
        "input_tokens": int(last.get("inputTokens") or 0),
        "output_tokens": int(last.get("outputTokens") or 0),
        "cached_input_tokens": int(last.get("cachedInputTokens") or 0),
        "reasoning_output_tokens": int(last.get("reasoningOutputTokens") or 0),
        "total_tokens": int(last.get("totalTokens") or 0),
        "session_total_tokens": int(total.get("totalTokens") or 0),
        "raw": token_usage,
    }
    if usage["total_tokens"] == 0:
        usage["total_tokens"] = usage["input_tokens"] + usage["output_tokens"]
    return usage


class CodexAppServerClient:
    """Small async JSON-RPC client for `codex app-server` over stdio."""

    def __init__(
        self,
        command: str | list[str] | tuple[str, ...] | None = None,
        *,
        request_timeout: float = _DEFAULT_REQUEST_TIMEOUT,
    ) -> None:
        self._command = resolve_codex_command(command)
        self._request_timeout = request_timeout
        self._proc: asyncio.subprocess.Process | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._stderr_task: asyncio.Task[None] | None = None
        self._send_lock = asyncio.Lock()
        self._pending: dict[int, asyncio.Future[Any]] = {}
        self._next_id = 0
        self._turn_queues: dict[tuple[str, str], asyncio.Queue[dict[str, Any]]] = {}
        self._turn_backlog: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
        self._notifications: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._stderr_tail: deque[str] = deque(maxlen=20)
        self._initialized = False

    async def connect(self) -> None:
        """Start app-server and perform the initialize handshake."""
        if self._initialized:
            return

        self._proc = await asyncio.create_subprocess_exec(
            *self._command,
            "app-server",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._reader_task = asyncio.create_task(self._reader_loop())
        self._stderr_task = asyncio.create_task(self._stderr_loop())

        await self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": _CLIENT_NAME,
                    "title": _CLIENT_TITLE,
                    "version": _package_version(),
                },
                "capabilities": {"experimentalApi": True},
            },
            timeout=30,
        )
        await self.notify("initialized", {})
        self._initialized = True

    async def close(self) -> None:
        """Terminate the app-server child process."""
        if self._proc and self._proc.returncode is None:
            if self._proc.stdin is not None:
                self._proc.stdin.close()
                with contextlib.suppress(Exception):
                    await self._proc.stdin.wait_closed()
            self._proc.terminate()
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=5)
            except TimeoutError:
                self._proc.kill()
                await self._proc.wait()

        for task in (self._reader_task, self._stderr_task):
            if not task:
                continue
            try:
                await asyncio.wait_for(task, timeout=2)
            except TimeoutError:
                task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await task

        for future in self._pending.values():
            if not future.done():
                future.set_exception(ProviderError("codex", "Codex app-server closed."))
        self._pending.clear()
        self._proc = None
        self._initialized = False

    async def ensure_authenticated(
        self,
        *,
        auto_login: bool = True,
        login_timeout: float = _DEFAULT_LOGIN_TIMEOUT,
    ) -> dict[str, Any]:
        """Ensure Codex has an authenticated account, opening browser auth if needed."""
        account = await self.request("account/read", {"refreshToken": False}, timeout=30)
        if account.get("account") or not account.get("requiresOpenaiAuth", False):
            return account

        if not auto_login:
            raise ProviderError(
                "codex",
                "Codex is not logged in. Run `codex login` or enable Codex Wise auto-login.",
            )

        login = await self.request("account/login/start", {"type": "chatgpt"}, timeout=30)
        login_id = login.get("loginId")
        auth_url = login.get("authUrl")
        if auth_url:
            opened = webbrowser.open(str(auth_url))
            if not opened:
                log.warning("codex.auth.browser_open_failed", auth_url=auth_url)

        notification = await self.wait_for_notification(
            "account/login/completed",
            lambda params: not login_id or params.get("loginId") == login_id,
            timeout=login_timeout,
        )
        params = notification.get("params") or {}
        if not params.get("success"):
            error = params.get("error") or "Codex login did not complete successfully."
            if auth_url:
                error = f"{error} Auth URL: {auth_url}"
            raise ProviderError("codex", str(error))

        return await self.request("account/read", {"refreshToken": True}, timeout=30)

    async def list_models(self, *, include_hidden: bool = False) -> list[dict[str, Any]]:
        """Read the current Codex model catalog from app-server."""
        data: list[dict[str, Any]] = []
        cursor: str | None = None
        while True:
            params: dict[str, Any] = {
                "limit": 100,
                "includeHidden": include_hidden,
            }
            if cursor:
                params["cursor"] = cursor
            result = await self.request("model/list", params, timeout=30)
            data.extend(result.get("data") or [])
            cursor = result.get("nextCursor")
            if not cursor:
                return data

    async def read_rate_limits(self) -> dict[str, Any] | None:
        """Best-effort ChatGPT rate-limit snapshot."""
        try:
            return await self.request("account/rateLimits/read", {}, timeout=15)
        except Exception as exc:
            log.debug("codex.rate_limits.unavailable", error=str(exc))
            return None

    async def generate_turn(
        self,
        *,
        model: str,
        reasoning_effort: str | None,
        cwd: str | None,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        request_id: str | None,
        timeout: float = _DEFAULT_TURN_TIMEOUT,
    ) -> GeneratedResponse:
        """Run a single app-server thread/turn and collect the final response."""
        thread_params: dict[str, Any] = {
            "model": model,
            "developerInstructions": _build_developer_instructions(system_prompt, max_tokens),
            "serviceName": _CLIENT_NAME,
            "ephemeral": True,
        }
        if cwd:
            thread_params["cwd"] = cwd

        thread_result = await self.request("thread/start", thread_params, timeout=60)
        thread_id = str(thread_result["thread"]["id"])

        turn_params: dict[str, Any] = {
            "threadId": thread_id,
            "input": [{"type": "text", "text": user_prompt}],
            "model": model,
            "approvalPolicy": "never",
            "sandboxPolicy": {"type": "readOnly", "access": {"type": "fullAccess"}},
        }
        if cwd:
            turn_params["cwd"] = cwd
        if reasoning_effort:
            turn_params["effort"] = reasoning_effort

        turn_result = await self.request("turn/start", turn_params, timeout=60)
        turn_id = str(turn_result["turn"]["id"])
        queue = self._register_turn(thread_id, turn_id)

        text_parts: list[str] = []
        final_text = ""
        token_usage: dict[str, Any] | None = None

        try:
            while True:
                message = await asyncio.wait_for(queue.get(), timeout=timeout)
                method = message.get("method")
                params = message.get("params") or {}

                if method == "item/agentMessage/delta":
                    delta = params.get("delta")
                    if isinstance(delta, str):
                        text_parts.append(delta)
                elif method == "item/completed":
                    item = params.get("item") or {}
                    if item.get("type") == "agentMessage":
                        final_text = str(item.get("text") or final_text)
                elif method == "thread/tokenUsage/updated":
                    token_usage = params.get("tokenUsage") or token_usage
                elif method == "turn/completed":
                    turn = params.get("turn") or {}
                    status = turn.get("status")
                    if status not in {"completed", None}:
                        error = turn.get("error") or {}
                        message_text = error.get("message") if isinstance(error, dict) else error
                        raise ProviderError(
                            "codex",
                            f"Turn finished with status {status}: {message_text}",
                        )
                    break
        finally:
            self._unregister_turn(thread_id, turn_id)
            with contextlib.suppress(Exception):
                await self.request(
                    "thread/unsubscribe",
                    {"threadId": thread_id},
                    timeout=10,
                )

        usage = _extract_usage(token_usage)
        content = final_text or "".join(text_parts)
        return GeneratedResponse(
            content=content,
            input_tokens=int(usage.get("input_tokens") or 0),
            output_tokens=int(usage.get("output_tokens") or 0),
            cached_tokens=int(usage.get("cached_input_tokens") or 0),
            usage=usage,
        )

    async def request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout: float | None = None,
    ) -> Any:
        """Send a JSON-RPC request and return its result."""
        await self._ensure_process_alive()
        request_id = self._next_id
        self._next_id += 1
        loop = asyncio.get_running_loop()
        future: asyncio.Future[Any] = loop.create_future()
        self._pending[request_id] = future

        message: dict[str, Any] = {"method": method, "id": request_id}
        if params is not None:
            message["params"] = params
        await self._send(message)

        try:
            return await asyncio.wait_for(
                future,
                timeout=timeout if timeout is not None else self._request_timeout,
            )
        except TimeoutError as exc:
            self._pending.pop(request_id, None)
            raise ProviderError("codex", f"Timed out waiting for {method}.") from exc

    async def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        message: dict[str, Any] = {"method": method}
        if params is not None:
            message["params"] = params
        await self._send(message)

    async def wait_for_notification(
        self,
        method: str,
        predicate: Any = None,
        *,
        timeout: float = _DEFAULT_REQUEST_TIMEOUT,
    ) -> dict[str, Any]:
        """Wait for a matching server notification."""
        while True:
            notification = await asyncio.wait_for(self._notifications.get(), timeout=timeout)
            if notification.get("method") != method:
                continue
            params = notification.get("params") or {}
            if predicate is None or predicate(params):
                return notification

    async def _ensure_process_alive(self) -> None:
        if self._proc is None:
            return
        if self._proc.returncode is not None:
            stderr = "\n".join(self._stderr_tail)
            suffix = f"\nRecent stderr:\n{stderr}" if stderr else ""
            raise ProviderError(
                "codex",
                f"Codex app-server exited with code {self._proc.returncode}.{suffix}",
            )

    async def _send(self, message: dict[str, Any]) -> None:
        await self._ensure_process_alive()
        if self._proc is None or self._proc.stdin is None:
            raise ProviderError("codex", "Codex app-server is not connected.")
        payload = json.dumps(message, separators=(",", ":")).encode("utf-8") + b"\n"
        async with self._send_lock:
            self._proc.stdin.write(payload)
            await self._proc.stdin.drain()

    async def _reader_loop(self) -> None:
        assert self._proc is not None and self._proc.stdout is not None
        try:
            while True:
                raw = await self._proc.stdout.readline()
                if not raw:
                    break
                try:
                    message = json.loads(raw.decode("utf-8"))
                except json.JSONDecodeError:
                    log.warning("codex.rpc.invalid_json", line=raw.decode("utf-8", "replace"))
                    continue
                await self._handle_message(message)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.debug("codex.rpc.reader_failed", error=str(exc))
        finally:
            for future in self._pending.values():
                if not future.done():
                    future.set_exception(ProviderError("codex", "Codex app-server stream closed."))

    async def _stderr_loop(self) -> None:
        assert self._proc is not None and self._proc.stderr is not None
        try:
            while True:
                raw = await self._proc.stderr.readline()
                if not raw:
                    break
                self._stderr_tail.append(raw.decode("utf-8", "replace").rstrip())
        except asyncio.CancelledError:
            raise

    async def _handle_message(self, message: dict[str, Any]) -> None:
        if "id" in message and ("result" in message or "error" in message):
            future = self._pending.pop(int(message["id"]), None)
            if future is None or future.done():
                return
            if "error" in message:
                error = message["error"] or {}
                text = error.get("message", error) if isinstance(error, dict) else error
                future.set_exception(ProviderError("codex", str(text)))
            else:
                future.set_result(message.get("result"))
            return

        if "id" in message and "method" in message:
            await self._handle_server_request(message)
            return

        if "method" in message:
            await self._handle_notification(message)

    async def _handle_server_request(self, message: dict[str, Any]) -> None:
        request_id = message.get("id")
        method = message.get("method")
        if method in {
            "item/commandExecution/requestApproval",
            "item/fileChange/requestApproval",
        }:
            await self._send({"id": request_id, "result": {"decision": "denied"}})
            return

        await self._send(
            {
                "id": request_id,
                "error": {
                    "code": -32601,
                    "message": f"Codex Wise cannot service app-server request {method!r}.",
                },
            }
        )

    async def _handle_notification(self, message: dict[str, Any]) -> None:
        await self._notifications.put(message)
        if message.get("method") not in _TURN_NOTIFICATION_METHODS:
            return

        params = message.get("params") or {}
        turn = params.get("turn") or {}
        thread_id = params.get("threadId") or params.get("thread_id")
        turn_id = params.get("turnId") or params.get("turn_id") or turn.get("id")
        if not turn_id:
            return

        if thread_id:
            key = (str(thread_id), str(turn_id))
            queue = self._turn_queues.get(key)
            if queue:
                await queue.put(message)
            else:
                self._turn_backlog[key].append(message)
            return

        matching = [key for key in self._turn_queues if key[1] == str(turn_id)]
        if len(matching) == 1:
            await self._turn_queues[matching[0]].put(message)
        else:
            self._turn_backlog[("", str(turn_id))].append(message)

    def _register_turn(self, thread_id: str, turn_id: str) -> asyncio.Queue[dict[str, Any]]:
        key = (thread_id, turn_id)
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._turn_queues[key] = queue
        for backlog_key in (key, ("", turn_id)):
            for message in self._turn_backlog.pop(backlog_key, []):
                queue.put_nowait(message)
        return queue

    def _unregister_turn(self, thread_id: str, turn_id: str) -> None:
        self._turn_queues.pop((thread_id, turn_id), None)


async def list_codex_models(
    *,
    include_hidden: bool = False,
    auto_login: bool = True,
    command: str | list[str] | tuple[str, ...] | None = None,
) -> list[dict[str, Any]]:
    """Convenience helper for CLI/server code that only needs model metadata."""
    client = CodexAppServerClient(command=command)
    await client.connect()
    try:
        await client.ensure_authenticated(auto_login=auto_login)
        return await client.list_models(include_hidden=include_hidden)
    finally:
        await client.close()


class CodexAppServerProvider(BaseProvider):
    """LLM provider that uses the installed Codex app-server."""

    def __init__(
        self,
        model: str | None = None,
        reasoning_effort: str | None = None,
        cwd: str | Path | None = None,
        codex_command: str | list[str] | tuple[str, ...] | None = None,
        auto_login: bool | None = None,
        login_timeout_seconds: float | None = None,
        rate_limiter: RateLimiter | None = None,
        cost_tracker: CostTracker | None = None,
        client_factory: Any | None = None,
    ) -> None:
        self._requested_model = (
            model
            or os.environ.get("CODEX_WISE_CODEX_MODEL")
            or os.environ.get("CODEX_WISE_MODEL")
            or os.environ.get("CODEX_WISE_DOC_MODEL")
            or _DEFAULT_CODEX_MODEL
        )
        self._requested_effort = (
            reasoning_effort or os.environ.get("CODEX_WISE_CODEX_REASONING_EFFORT")
            or os.environ.get("CODEX_WISE_REASONING_EFFORT")
            or _DEFAULT_REASONING_EFFORT
        )
        self._model = self._requested_model
        self._reasoning_effort = self._requested_effort
        self._cwd = str(Path(cwd).resolve()) if cwd else None
        self._codex_command = codex_command
        self._auto_login = _as_bool_env("CODEX_WISE_CODEX_AUTO_LOGIN", True) if auto_login is None else auto_login
        self._login_timeout = login_timeout_seconds or float(
            os.environ.get("CODEX_WISE_CODEX_LOGIN_TIMEOUT_SECONDS", _DEFAULT_LOGIN_TIMEOUT)
        )
        self._rate_limiter = rate_limiter
        self._cost_tracker = cost_tracker
        self._client_factory = client_factory
        self._client: Any | None = None
        self._connect_lock = asyncio.Lock()
        self._model_lock = asyncio.Lock()

    @property
    def provider_name(self) -> str:
        return "codex"

    @property
    def model_name(self) -> str:
        return self._model

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        request_id: str | None = None,
    ) -> GeneratedResponse:
        if self._rate_limiter:
            await self._rate_limiter.acquire(estimated_tokens=max_tokens)

        client = await self._ensure_client()
        await client.ensure_authenticated(
            auto_login=self._auto_login,
            login_timeout=self._login_timeout,
        )
        await self._refresh_model_selection(client)

        log.debug(
            "codex.generate.start",
            model=self._model,
            reasoning_effort=self._reasoning_effort,
            request_id=request_id,
        )
        result = await client.generate_turn(
            model=self._model,
            reasoning_effort=self._reasoning_effort,
            cwd=self._cwd,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            request_id=request_id,
        )

        rate_limits = await client.read_rate_limits()
        if rate_limits:
            result.usage["rate_limits"] = rate_limits

        if self._cost_tracker is not None:
            with contextlib.suppress(RuntimeError):
                asyncio.get_event_loop().create_task(
                    self._cost_tracker.record(
                        model=f"{_CODEX_MODEL_PREFIX}{self._model}",
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        operation="doc_generation",
                        file_path=None,
                    )
                )

        log.debug(
            "codex.generate.done",
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            request_id=request_id,
        )
        return result

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system_prompt: str,
        max_tokens: int = 8192,
        temperature: float = 0.7,
        request_id: str | None = None,
        tool_executor: Any | None = None,
    ) -> AsyncIterator[ChatStreamEvent]:
        """Minimal ChatProvider adapter for server chat.

        Codex app-server already owns its own tool/approval stream.  The Codex
        Wise chat route currently supplies provider-native tool schemas, so this
        fallback sends the conversation as text and streams the final response as
        a single delta.  Full app-server item streaming can be layered onto the
        server chat UI separately.
        """
        del tools, temperature, tool_executor
        prompt = _messages_to_prompt(messages)
        result = await self.generate(
            system_prompt=system_prompt,
            user_prompt=prompt,
            max_tokens=max_tokens,
            request_id=request_id,
        )
        if result.content:
            yield ChatStreamEvent(type="text_delta", text=result.content)
        yield ChatStreamEvent(
            type="usage",
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
        yield ChatStreamEvent(type="stop", stop_reason="end_turn")

    async def close(self) -> None:
        if self._client is not None and hasattr(self._client, "close"):
            await self._client.close()
        self._client = None

    async def _ensure_client(self) -> Any:
        async with self._connect_lock:
            if self._client is not None:
                return self._client
            if self._client_factory is not None:
                client = self._client_factory()
            else:
                client = CodexAppServerClient(command=self._codex_command)
            if hasattr(client, "connect"):
                await client.connect()
            self._client = client
            return client

    async def _refresh_model_selection(self, client: Any) -> None:
        async with self._model_lock:
            include_hidden = bool(self._requested_model)
            models = await client.list_models(include_hidden=include_hidden)
            selection = choose_codex_model(
                models,
                requested_model=self._requested_model,
                requested_effort=self._requested_effort,
            )
            self._model = selection.model
            self._reasoning_effort = selection.reasoning_effort


def _messages_to_prompt(messages: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for message in messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        if isinstance(content, list):
            text = " ".join(
                str(part.get("text", "")) if isinstance(part, dict) else str(part)
                for part in content
            )
        else:
            text = str(content)
        lines.append(f"{role}: {text}")
    return "\n\n".join(lines)
