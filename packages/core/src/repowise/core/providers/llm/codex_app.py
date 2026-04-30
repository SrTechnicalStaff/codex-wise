"""Codex app-server provider for internal Codex Wise synthesis.

This provider talks to Codex's experimental app-server protocol and exposes it
through the normal BaseProvider interface. The protocol is intentionally isolated
here so get_answer and future tools do not need Codex-specific synthesis branches.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import subprocess
import sys
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

from repowise.core.providers.llm.base import (
    BaseProvider,
    GeneratedResponse,
    ProviderError,
)

_PROVIDER = "codex_app"
_DEFAULT_TIMEOUT_SECONDS = 60.0
_DEFAULT_MODEL = "gpt-5.5"
_DEFAULT_REASONING_EFFORT = "medium"
_CURRENT_MODEL_SENTINELS = {"codex-current", "current", "default", "active"}
_APP_PROTOCOL_NOTE = (
    "Codex app-server protocol support is experimental and isolated to "
    "repowise.core.providers.llm.codex_app."
)


class _CodexAppClient(Protocol):
    async def request(
        self, method: str, params: dict[str, Any] | None, timeout: float
    ) -> dict[str, Any]:
        ...

    async def receive(self, timeout: float) -> dict[str, Any]:
        ...

    async def close(self) -> None:
        ...


ClientFactory = Callable[[], _CodexAppClient | Awaitable[_CodexAppClient]]


@dataclass
class _TurnState:
    text_parts: list[str] = field(default_factory=list)
    item_texts: list[str] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)


class _JsonLineClient:
    """Line-delimited JSON-RPC client used by `codex app-server proxy`."""

    def __init__(self, command: list[str], timeout_seconds: float) -> None:
        self._command = command
        self._timeout_seconds = timeout_seconds
        self._process: asyncio.subprocess.Process | None = None
        self._next_id = 1
        self._queued: deque[dict[str, Any]] = deque()
        self._stderr_tail: deque[str] = deque(maxlen=12)
        self._stderr_task: asyncio.Task[None] | None = None

    async def __aenter__(self) -> _JsonLineClient:
        self._process = await self._start_process()
        if self._process.stderr is not None:
            self._stderr_task = asyncio.create_task(self._drain_stderr())
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    async def _start_process(self) -> asyncio.subprocess.Process:
        try:
            return await asyncio.create_subprocess_exec(
                *self._command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
        except (FileNotFoundError, PermissionError) as exc:
            if sys.platform != "win32":
                raise ProviderError(
                    _PROVIDER, f"Could not start {' '.join(self._command)!r}: {exc}"
                ) from exc
            # Windows Store app execution aliases can fail through execve but
            # still work through cmd.exe. Keep this fallback local to transport.
            shell_command = subprocess.list2cmdline(self._command)
            return await asyncio.create_subprocess_shell(
                shell_command,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

    async def _drain_stderr(self) -> None:
        proc = self._require_process()
        assert proc.stderr is not None
        while True:
            line = await proc.stderr.readline()
            if not line:
                return
            self._stderr_tail.append(line.decode("utf-8", errors="replace").strip())

    def _require_process(self) -> asyncio.subprocess.Process:
        if self._process is None:
            raise ProviderError(_PROVIDER, "Codex app-server transport is not open.")
        return self._process

    async def request(
        self, method: str, params: dict[str, Any] | None, timeout: float
    ) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        await self._send(
            {
                "id": request_id,
                "method": method,
                "params": params or {},
            }
        )

        deadline = time.monotonic() + timeout
        while True:
            msg = await self._receive_raw(_remaining(deadline))
            if msg.get("id") == request_id:
                if "error" in msg:
                    raise ProviderError(
                        _PROVIDER,
                        f"app-server request {method!r} failed: {msg['error']}",
                    )
                result = msg.get("result")
                return result if isinstance(result, dict) else {}
            self._queued.append(msg)

    async def receive(self, timeout: float) -> dict[str, Any]:
        if self._queued:
            return self._queued.popleft()
        return await self._receive_raw(timeout)

    async def _receive_raw(self, timeout: float) -> dict[str, Any]:
        proc = self._require_process()
        if proc.stdout is None:
            raise ProviderError(_PROVIDER, "Codex app-server stdout is unavailable.")

        line = await asyncio.wait_for(proc.stdout.readline(), timeout=timeout)
        if not line:
            code = await self._poll_returncode(proc)
            detail = f" process exited with code {code}." if code is not None else "."
            stderr = self._stderr_summary()
            raise ProviderError(
                _PROVIDER,
                f"Codex app-server closed stdout{detail}{stderr}",
            )
        try:
            msg = json.loads(line.decode("utf-8"))
        except json.JSONDecodeError as exc:
            raise ProviderError(
                _PROVIDER,
                f"Invalid app-server JSON message: {line[:200]!r}",
            ) from exc

        # The server can theoretically ask the client for approval or tool-side
        # work. This provider is deliberately synthesis-only, so reject such
        # requests instead of doing hidden work.
        if "id" in msg and "method" in msg and "result" not in msg and "error" not in msg:
            await self._send(
                {
                    "id": msg["id"],
                    "error": {
                        "code": -32601,
                        "message": "Codex Wise codex_app provider does not handle server requests.",
                    },
                }
            )
            return await self._receive_raw(timeout)

        return msg

    async def _poll_returncode(self, proc: asyncio.subprocess.Process) -> int | None:
        with contextlib.suppress(asyncio.TimeoutError):
            await asyncio.wait_for(proc.wait(), timeout=0.05)
        return proc.returncode

    async def _send(self, obj: dict[str, Any]) -> None:
        proc = self._require_process()
        if proc.stdin is None:
            raise ProviderError(_PROVIDER, "Codex app-server stdin is unavailable.")
        payload = json.dumps(obj, separators=(",", ":")).encode("utf-8") + b"\n"
        proc.stdin.write(payload)
        await proc.stdin.drain()

    def _stderr_summary(self) -> str:
        if not self._stderr_tail:
            return ""
        return " stderr: " + " | ".join(x for x in self._stderr_tail if x)

    async def close(self) -> None:
        proc = self._process
        self._process = None
        if proc is None:
            return
        if proc.stdin is not None:
            with contextlib.suppress(Exception):
                proc.stdin.close()
                await proc.stdin.wait_closed()
        if proc.returncode is None:
            with contextlib.suppress(ProcessLookupError):
                proc.terminate()
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(proc.wait(), timeout=2.0)
            if proc.returncode is None:
                with contextlib.suppress(ProcessLookupError):
                    proc.kill()
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
        if self._stderr_task is not None:
            self._stderr_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._stderr_task


class _WebSocketJsonRpcClient:
    """JSON-RPC client for explicitly configured app-server websocket URLs."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._next_id = 1
        self._queued: deque[dict[str, Any]] = deque()
        self._ws: Any = None

    async def __aenter__(self) -> _WebSocketJsonRpcClient:
        try:
            import websockets  # type: ignore[import-not-found]
        except ImportError as exc:
            raise ProviderError(
                _PROVIDER,
                "CODEX_WISE_CODEX_TRANSPORT=websocket requires the 'websockets' package.",
            ) from exc
        self._ws = await websockets.connect(self._url)
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.close()

    async def request(
        self, method: str, params: dict[str, Any] | None, timeout: float
    ) -> dict[str, Any]:
        request_id = self._next_id
        self._next_id += 1
        await self._send({"id": request_id, "method": method, "params": params or {}})
        deadline = time.monotonic() + timeout
        while True:
            msg = await self._receive_raw(_remaining(deadline))
            if msg.get("id") == request_id:
                if "error" in msg:
                    raise ProviderError(
                        _PROVIDER,
                        f"app-server request {method!r} failed: {msg['error']}",
                    )
                result = msg.get("result")
                return result if isinstance(result, dict) else {}
            self._queued.append(msg)

    async def receive(self, timeout: float) -> dict[str, Any]:
        if self._queued:
            return self._queued.popleft()
        return await self._receive_raw(timeout)

    async def _send(self, obj: dict[str, Any]) -> None:
        if self._ws is None:
            raise ProviderError(_PROVIDER, "Codex app-server websocket is not open.")
        await self._ws.send(json.dumps(obj, separators=(",", ":")))

    async def _receive_raw(self, timeout: float) -> dict[str, Any]:
        if self._ws is None:
            raise ProviderError(_PROVIDER, "Codex app-server websocket is not open.")
        raw = await asyncio.wait_for(self._ws.recv(), timeout=timeout)
        msg = json.loads(raw)
        if "id" in msg and "method" in msg and "result" not in msg and "error" not in msg:
            await self._send(
                {
                    "id": msg["id"],
                    "error": {
                        "code": -32601,
                        "message": "Codex Wise codex_app provider does not handle server requests.",
                    },
                }
            )
            return await self._receive_raw(timeout)
        return msg

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None


class CodexAppProvider(BaseProvider):
    """BaseProvider-compatible bridge to Codex's app-server protocol."""

    def __init__(
        self,
        model: str | None = None,
        transport: str | None = None,
        app_server_url: str | None = None,
        socket_path: str | None = None,
        timeout_seconds: float | str | None = None,
        reasoning_effort: str | None = None,
        command: str | None = None,
        client_factory: ClientFactory | None = None,
        **_: Any,
    ) -> None:
        requested_model = model or os.environ.get("CODEX_WISE_MODEL") or _DEFAULT_MODEL
        if requested_model.lower() in _CURRENT_MODEL_SENTINELS:
            self._configured_model = None
            self._model_display = "codex-current"
        else:
            self._configured_model = requested_model
            self._model_display = requested_model
        self._transport = (transport or os.environ.get("CODEX_WISE_CODEX_TRANSPORT") or "proxy").lower()
        self._app_server_url = app_server_url or os.environ.get("CODEX_WISE_CODEX_APP_SERVER_URL")
        self._socket_path = socket_path or os.environ.get("CODEX_WISE_CODEX_APP_SERVER_SOCKET")
        self._command = command or os.environ.get("CODEX_WISE_CODEX_COMMAND") or "codex"
        raw_timeout = timeout_seconds or os.environ.get("CODEX_WISE_CODEX_TIMEOUT_SECONDS")
        self._timeout_seconds = _parse_timeout(raw_timeout)
        self._reasoning_effort = (
            reasoning_effort
            or os.environ.get("CODEX_WISE_CODEX_REASONING_EFFORT")
            or os.environ.get("CODEX_WISE_REASONING_EFFORT")
            or _DEFAULT_REASONING_EFFORT
        )
        self._client_factory = client_factory

    @property
    def provider_name(self) -> str:
        return _PROVIDER

    @property
    def model_name(self) -> str:
        return self._model_display

    async def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        request_id: str | None = None,
    ) -> GeneratedResponse:
        del temperature  # Codex app-server does not currently expose sampling knobs here.
        client = await self._make_client()
        try:
            return await self._generate_with_client(
                client,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                max_tokens=max_tokens,
                request_id=request_id,
            )
        except TimeoutError as exc:
            raise ProviderError(
                _PROVIDER,
                f"Codex app-server request timed out after {self._timeout_seconds:g}s.",
            ) from exc
        finally:
            await client.close()

    async def _make_client(self) -> _CodexAppClient:
        if self._client_factory is not None:
            made = self._client_factory()
            return await made if hasattr(made, "__await__") else made

        transport = self._transport
        if transport in {"proxy", "unix", "socket"}:
            command = self._build_proxy_command(require_socket=transport in {"unix", "socket"})
            return await _JsonLineClient(command, self._timeout_seconds).__aenter__()
        if transport in {"stdio", "server"}:
            return await _JsonLineClient(
                [self._command, "app-server", "--listen", "stdio://"],
                self._timeout_seconds,
            ).__aenter__()
        if transport in {"ws", "websocket"}:
            if not self._app_server_url:
                raise ProviderError(
                    _PROVIDER,
                    "CODEX_WISE_CODEX_APP_SERVER_URL is required for websocket transport.",
                )
            return await _WebSocketJsonRpcClient(self._app_server_url).__aenter__()

        raise ProviderError(
            _PROVIDER,
            "Unsupported Codex app-server transport "
            f"{transport!r}; use proxy, websocket, unix, or stdio.",
        )

    def _build_proxy_command(self, *, require_socket: bool = False) -> list[str]:
        if require_socket and not self._socket_path:
            raise ProviderError(
                _PROVIDER,
                "CODEX_WISE_CODEX_APP_SERVER_SOCKET is required for unix/socket transport.",
            )
        command = [self._command, "app-server", "proxy"]
        if self._socket_path:
            command.extend(["--sock", self._socket_path])
        if self._configured_model:
            command.extend(["-c", f"model={_toml_string(self._configured_model)}"])
        return command

    async def _generate_with_client(
        self,
        client: _CodexAppClient,
        *,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
        request_id: str | None,
    ) -> GeneratedResponse:
        timeout = self._timeout_seconds
        deadline = time.monotonic() + timeout

        await client.request(
            "initialize",
            {
                "clientInfo": {"name": "codex-wise", "version": "0.4.0"},
                "capabilities": {
                    "experimentalApi": True,
                    "optOutNotificationMethods": [],
                },
            },
            timeout=_remaining(deadline),
        )

        thread_params = self._thread_start_params(system_prompt)
        thread_response = await client.request(
            "thread/start", thread_params, timeout=_remaining(deadline)
        )
        thread_id = _extract_thread_id(thread_response)
        if not thread_id:
            raise ProviderError(
                _PROVIDER,
                f"thread/start did not return a thread id. {_APP_PROTOCOL_NOTE}",
            )

        turn_params = self._turn_start_params(
            thread_id=thread_id,
            user_prompt=user_prompt,
            max_tokens=max_tokens,
            request_id=request_id,
        )
        await client.request("turn/start", turn_params, timeout=_remaining(deadline))

        state = _TurnState()
        while True:
            msg = await client.receive(timeout=_remaining(deadline))
            method = msg.get("method")
            params = msg.get("params") or {}
            if not isinstance(params, dict):
                continue

            if method == "item/agentMessage/delta":
                delta = params.get("delta")
                if isinstance(delta, str):
                    state.text_parts.append(delta)
            elif method == "item/completed":
                text = _extract_item_text(params.get("item"))
                if text:
                    state.item_texts.append(text)
            elif method == "thread/tokenUsage/updated":
                usage = _extract_usage(params)
                if usage:
                    state.usage = usage
            elif method == "error":
                raise ProviderError(_PROVIDER, _format_server_error(params))
            elif method == "turn/completed":
                turn = params.get("turn") if isinstance(params.get("turn"), dict) else {}
                status = turn.get("status")
                if status != "completed":
                    raise ProviderError(_PROVIDER, _format_turn_error(turn))
                content = "".join(state.text_parts).strip()
                if not content:
                    content = "\n\n".join(t.strip() for t in state.item_texts if t.strip()).strip()
                usage = state.usage or {"usage_unavailable": True}
                return GeneratedResponse(
                    content=content,
                    input_tokens=int(usage.get("input_tokens", 0) or 0),
                    output_tokens=int(usage.get("output_tokens", 0) or 0),
                    cached_tokens=int(usage.get("cached_tokens", 0) or 0),
                    usage=usage,
                )

    def _thread_start_params(self, system_prompt: str) -> dict[str, Any]:
        params: dict[str, Any] = {
            "baseInstructions": (
                "You are a bounded synthesis backend for Codex Wise. "
                "Do not use tools, inspect files, run commands, or modify state. "
                "Answer only from the provided prompt."
            ),
            "developerInstructions": system_prompt,
            "cwd": os.getcwd(),
            "serviceName": "codex-wise",
            "ephemeral": True,
            "approvalPolicy": "never",
            "sandbox": "read-only",
            "sessionStartSource": "clear",
            "personality": "none",
        }
        if self._configured_model:
            params["model"] = self._configured_model
        return params

    def _turn_start_params(
        self,
        *,
        thread_id: str,
        user_prompt: str,
        max_tokens: int,
        request_id: str | None,
    ) -> dict[str, Any]:
        bounded_prompt = (
            f"{user_prompt}\n\n"
            "Return only the final answer. Do not call tools. "
            f"Keep the response within approximately {max_tokens} output tokens."
        )
        if request_id:
            bounded_prompt += f"\nRequest id: {request_id}"

        params: dict[str, Any] = {
            "threadId": thread_id,
            "input": [{"type": "text", "text": bounded_prompt}],
            "approvalPolicy": "never",
            "sandboxPolicy": {
                "type": "readOnly",
                "networkAccess": False,
            },
            "personality": "none",
            "effort": self._reasoning_effort,
        }
        if self._configured_model:
            params["model"] = self._configured_model
        return params


def _extract_thread_id(response: dict[str, Any]) -> str | None:
    thread = response.get("thread")
    if isinstance(thread, dict) and isinstance(thread.get("id"), str):
        return thread["id"]
    if isinstance(response.get("threadId"), str):
        return response["threadId"]
    return None


def _extract_item_text(item: Any) -> str | None:
    if not isinstance(item, dict):
        return None
    if isinstance(item.get("text"), str):
        return item["text"]
    if item.get("type") == "agentMessage":
        fragments = item.get("fragments")
        if isinstance(fragments, list):
            texts = []
            for frag in fragments:
                if isinstance(frag, dict):
                    text = frag.get("text") or frag.get("content")
                    if isinstance(text, str):
                        texts.append(text)
                elif isinstance(frag, str):
                    texts.append(frag)
            if texts:
                return "".join(texts)
    content = item.get("content")
    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict) and isinstance(block.get("text"), str):
                texts.append(block["text"])
        if texts:
            return "".join(texts)
    return None


def _extract_usage(params: dict[str, Any]) -> dict[str, Any]:
    usage = params.get("tokenUsage") or params.get("usage") or {}
    if isinstance(usage, dict) and isinstance(usage.get("last"), dict):
        usage = usage["last"]
    if not isinstance(usage, dict):
        return {}
    return {
        "input_tokens": int(usage.get("inputTokens", usage.get("input_tokens", 0)) or 0),
        "output_tokens": int(usage.get("outputTokens", usage.get("output_tokens", 0)) or 0),
        "cached_tokens": int(
            usage.get("cachedInputTokens", usage.get("cached_tokens", 0)) or 0
        ),
        "total_tokens": int(usage.get("totalTokens", usage.get("total_tokens", 0)) or 0),
        "reasoning_output_tokens": int(
            usage.get("reasoningOutputTokens", usage.get("reasoning_output_tokens", 0)) or 0
        ),
        "source": "codex_app_server",
    }


def _format_turn_error(turn: dict[str, Any]) -> str:
    status = turn.get("status") or "unknown"
    error = turn.get("error")
    if isinstance(error, dict):
        message = error.get("message") or str(error)
        details = error.get("additionalDetails")
        if details:
            return f"Codex app-server turn {status}: {message} ({details})"
        return f"Codex app-server turn {status}: {message}"
    return f"Codex app-server turn ended with status {status!r}."


def _format_server_error(params: dict[str, Any]) -> str:
    if isinstance(params.get("message"), str):
        return params["message"]
    if isinstance(params.get("error"), dict) and isinstance(params["error"].get("message"), str):
        return params["error"]["message"]
    return f"Codex app-server error notification: {params}"


def _remaining(deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("Codex app-server request timed out.")
    return remaining


def _parse_timeout(raw: float | str | None) -> float:
    if raw is None:
        return _DEFAULT_TIMEOUT_SECONDS
    try:
        timeout = float(raw)
    except (TypeError, ValueError) as exc:
        raise ProviderError(_PROVIDER, "CODEX_WISE_CODEX_TIMEOUT_SECONDS must be numeric.") from exc
    return max(timeout, 1.0)


def _toml_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


__all__ = ["CodexAppProvider"]
