# Auto Sync

Codex Wise can refresh its local index through explicit updates, file watching, or git hooks.

## Manual Update

```bash
codex-wise update
codex-wise update --dry-run
codex-wise update --since main
codex-wise update --workspace
```

## Watch Mode

```bash
codex-wise watch
codex-wise watch --workspace
codex-wise watch --debounce 5000
```

Use watch mode during active local development.

## Git Hooks

```bash
codex-wise hook install
codex-wise hook install --workspace
codex-wise hook status
codex-wise hook uninstall
```

The hook runs an incremental update after commits so the index and generated `AGENTS.md` stay current.

## Webhooks

The server can also process repository webhooks for hosted or shared deployments. Configure the relevant secret/token environment variable and run:

```bash
codex-wise serve
```

## Troubleshooting

| Symptom | Fix |
|---|---|
| No previous sync found | Run `codex-wise init` |
| Watch is too noisy | Increase `--debounce` |
| Hook is missing | Run `codex-wise hook install` |
| Workspace repo is stale | Run `codex-wise update --workspace` |

