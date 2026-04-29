---
layout: default
title: Self Hosting
nav_order: 8
---

# Self Hosting

For local or shared API use:

```bash
codex-wise serve --host 127.0.0.1 --port 7337
codex-wise serve --no-ui
```

For network-exposed deployments, set an API key and bind explicitly:

```bash
export CODEX_WISE_API_KEY="..."
codex-wise serve --host 0.0.0.0
```

Use PostgreSQL by setting the database URL before initialization and server startup.
