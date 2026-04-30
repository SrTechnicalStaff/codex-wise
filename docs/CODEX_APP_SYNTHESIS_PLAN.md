# Codex App-Server Synthesis Plan

## Status

Implemented as a real provider path: `CODEX_WISE_PROVIDER=codex_app`.

The Codex app-server protocol was inspected with `codex app-server generate-json-schema` and confirmed to expose the minimum generation route needed by Codex Wise:

1. `initialize`
2. `thread/start`
3. `turn/start`
4. `item/agentMessage/delta`, `item/completed`, `turn/completed`, and optional token-usage notifications

The protocol is experimental, so the dependency is isolated in `repowise.core.providers.llm.codex_app`.

## Default Codex Path

Codex plugin launches should set:

```bash
CODEX_WISE_PROVIDER=codex_app
CODEX_WISE_CODEX_TRANSPORT=proxy
```

Optional model and timeout overrides:

```bash
CODEX_WISE_MODEL=gpt-5.4-mini
CODEX_WISE_CODEX_TIMEOUT_SECONDS=60
```

When no model is configured, Codex Wise reports `codex-current` as the model name and lets the app-server use its active/default model.

## Provider Behavior

`CodexAppProvider` implements the normal `BaseProvider.generate()` interface, so `get_answer` does not need a Codex-specific synthesis branch.

Transport support:

- `proxy` (default): `codex app-server proxy` over stdio
- `websocket`: only when `CODEX_WISE_CODEX_APP_SERVER_URL` is set
- `unix` / `socket`: only when `CODEX_WISE_CODEX_APP_SERVER_SOCKET` is set
- `stdio`: local app-server process for testing/manual use

`codex exec` is intentionally not used because it can introduce nested-agent behavior, tool use, latency, and mutation risk.

## Resolver Behavior

Provider resolution lives in `repowise.core.providers.llm.config`.

Precedence:

1. Explicit `CODEX_WISE_PROVIDER`
2. Legacy `REPOWISE_PROVIDER`
3. Config dict provider, when a caller supplies one
4. API-key/local-provider auto-detection

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
- Finish the larger namespace migration separately if the internal `repowise` package name should become `codex_wise`.
- Continue cleaning stale user-facing “Repowise” references in long-form docs and website pages outside this provider change.
