# Codex Wise Plugin

This plugin wires Codex Wise into Codex as an MCP context provider. Codex remains the host agent; Codex Wise supplies indexed repository context through tools and generated `AGENTS.md`.

Install the CLI in the same environment Codex uses:

```bash
pip install -e .
codex-wise init --index-only
codex-wise doctor
```

For project-scoped setup, prefer the generated `.codex/config.toml` from `codex-wise init`.
