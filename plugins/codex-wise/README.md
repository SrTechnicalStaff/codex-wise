# Codex Wise Plugin

This plugin wires Repowise into Codex as an MCP context provider. Codex remains the host agent; Repowise supplies indexed repository context through tools and generated `AGENTS.md`.

Install the CLI in the same environment Codex uses:

```bash
pip install -e .
repowise init --index-only
repowise doctor
```

For project-scoped setup, prefer the generated `.codex/config.toml` from `repowise init`.
