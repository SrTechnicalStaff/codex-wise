# Roadmap

## Completed

### Phase 1: Codex-Native Foundation

- `codex-wise` CLI entrypoint
- `AGENTS.md` generation
- project-scoped `.codex/config.toml`
- init/update integration

### Phase 2: Codex-First UX And Diagnostics

- invocation-aware CLI output
- Codex setup checks in `doctor`
- concise generated `AGENTS.md`
- `AGENTS.md` API preview/write endpoints

### Phase 3: Apparatus-Focused Public Surface

- docs lead with `codex-wise`
- marketing imagery and old plugin surface removed
- operational setup/reference docs replace product-copy-first docs
- Codex project config uses `codex_wise` and the `codex-wise` command

### Phase 4: Codex Desktop App Compatibility

- project-local Codex Desktop MCP config
- stdio-safe MCP startup
- `codex-wise doctor --desktop`
- desktop setup documentation and stdio smoke tests

### Phase 5: Hard Cutover

- Python import namespace moved to `codex_wise`
- package metadata and lockfile moved to `codex-wise*`
- runtime storage moved to `.codex-wise` and `.codex-wise-workspace*`
- environment variables moved to `CODEX_WISE_*`
- Claude-era editor files and MCP registration removed
- legacy storage/import/env migration paths removed

## Remaining

### Phase 6: Release Hardening

Goal: ship the Codex-native apparatus with minimal surprises.

Planned work:

- install-from-clean-environment test
- CLI smoke tests on Windows, macOS, and Linux
- changelog and upgrade notes
- final docs link check
- package metadata review
