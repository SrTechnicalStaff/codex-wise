# Codex Wise Web UI

Next.js dashboard for the local Codex Wise server. It exposes repository status, generated docs, search, graph views, risk signals, jobs, provider settings, and MCP setup without separate branding.

## Run

```bash
npm install
npm --workspace packages/web run dev
```

The app proxies `/api/*` to the local server on `http://localhost:7337` by default. Override with:

```bash
CODEX_WISE_API_URL=http://localhost:7337
NEXT_PUBLIC_CODEX_WISE_API_URL=http://localhost:7337
```

Compatibility env vars using the old prefix are still read as fallbacks.

## Checks

```bash
npm --workspace packages/web run type-check
npm --workspace packages/web run build
```
