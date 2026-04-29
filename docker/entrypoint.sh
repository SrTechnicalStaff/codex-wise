#!/bin/bash
set -e

# Start the FastAPI backend
echo "Starting Codex Wise API server on port ${PORT_BACKEND}..."
uvicorn codex_wise.server.app:create_app \
  --factory \
  --host 0.0.0.0 \
  --port "${PORT_BACKEND}" &

# Start the Next.js frontend
echo "Starting Codex Wise Web UI on port ${PORT_FRONTEND}..."
cd /app/web
CODEX_WISE_API_URL="http://localhost:${PORT_BACKEND}" \
HOSTNAME="0.0.0.0" \
PORT="${PORT_FRONTEND}" \
  node server.js &

# Wait for either process to exit
wait -n
exit $?
