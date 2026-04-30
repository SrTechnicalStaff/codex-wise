# Codex App-Server Synthesis Plan

## Status

Implemented as a real provider path: `CODEX_WISE_PROVIDER=codex_app`.

The Codex app-server protocol was inspected with `codex app-server generate-json-schema` and confirmed to expose the minimum generation route needed by Codex Wise:

1. `initialize`
2. `thread/start`
3. `turn/start`
4. `item/agentMessage/delta`, `item/completed`, `turn/completed`, and optional token-usage notifications

The protocol is experimental, so the dependency is isolated in `codex_wise.core.providers.llm.codex_app`.

## Default Codex Path

Codex plugin launches should set:

```bash
CODEX_WISE_PROVIDER=codex_app
CODEX_WISE_CODEX_TRANSPORT=proxy
```

Optional model and timeout overrides:

```bash
CODEX_WISE_DOC_MODEL=gpt-5.5
CODEX_WISE_CODEX_REASONING_EFFORT=medium
CODEX_WISE_CODEX_TIMEOUT_SECONDS=60
```

When no model is configured, Codex Wise defaults internal answer synthesis to `gpt-5.5` with `medium` reasoning. Set `CODEX_WISE_DOC_MODEL`, `CODEX_WISE_MODEL`, or `CODEX_WISE_CODEX_MODEL` to change the model. Set `CODEX_WISE_CODEX_REASONING_EFFORT` to change reasoning effort. Use `codex-current` only when you intentionally want the app-server active/default model.

## Provider Behavior

`CodexAppProvider` implements the normal `BaseProvider.generate()` interface, so `get_answer` does not need a Codex-specific synthesis branch.

Transport support:

- `proxy` (default): `codex app-server proxy` over stdio
- `websocket`: only when `CODEX_WISE_CODEX_APP_SERVER_URL` is set
- `unix` / `socket`: only when `CODEX_WISE_CODEX_APP_SERVER_SOCKET` is set
- `stdio`: local app-server process for testing/manual use

`codex exec` is intentionally not used because it can introduce nested-agent behavior, tool use, latency, and mutation risk.

## Resolver Behavior

Provider resolution lives in `codex_wise.core.providers.llm.config`.

Precedence:

1. Explicit `CODEX_WISE_PROVIDER`
2. Config dict provider, when a caller supplies one
3. API-key/local-provider auto-detection

Explicit provider failures do not fall through to other providers. If `CODEX_WISE_PROVIDER=codex_app` fails, `get_answer` returns retrieval hits plus an actionable app-server error.

## Cache Behavior

`answer_cache` is scoped by:

- repository
- question hash, including synthesis-affecting answer options such as `scope`
- provider
- model

This prevents stale synthesized answers from crossing provider or model changes.

## Remaining Development Gaps

- Keep monitoring Codex app-server schema changes; the protocol is still experimental.
- Add broader integration coverage against real Codex app-server when CI has a Codex runtime.
