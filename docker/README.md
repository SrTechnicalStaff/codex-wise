# Docker

Run the full Codex Wise stack (API + Web UI) in a single container.

## Prerequisites

- Docker installed
- A repository already indexed with `codex-wise init` (the `.codex-wise/` directory exists)

## Quick Start

```bash
# Run from the project root
docker build -t codex-wise -f docker/Dockerfile .

# Run with a mounted .codex-wise directory
docker run -p 7337:7337 -p 3000:3000 \
  -v /path/to/your-repo/.codex-wise:/data \
  -e GEMINI_API_KEY=your-key \
  -e CODEX_WISE_EMBEDDER=gemini \
  codex-wise
```

Open http://localhost:3000 for the Web UI, http://localhost:7337 for the API.

## Docker Compose

```bash
# Set the path to your .codex-wise directory
export CODEX_WISE_DATA=/path/to/your-repo/.codex-wise
export GEMINI_API_KEY=your-key

docker compose up
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CODEX_WISE_DB_URL` | `sqlite+aiosqlite:////data/wiki.db` | Database URL |
| `CODEX_WISE_EMBEDDER` | `mock` | Embedder: `gemini`, `openai`, `mock` |
| `ANTHROPIC_API_KEY` | — | Anthropic API key (for chat) |
| `OPENAI_API_KEY` | — | OpenAI API key (for chat) |
| `GEMINI_API_KEY` | — | Gemini API key (for chat + embeddings) |
| `PORT_BACKEND` | `7337` | API server port |
| `PORT_FRONTEND` | `3000` | Web UI port |
