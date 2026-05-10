#!/usr/bin/env bash
#
# Expose the local WhiteNote stack to the public internet via a free
# Cloudflare quick tunnel (no signup, random *.trycloudflare.com URL).
#
# Usage:
#   ./scripts/tunnel.sh                # tunnel Streamlit (default, safe)
#   ./scripts/tunnel.sh streamlit
#   ./scripts/tunnel.sh mcp            # ⚠ exposes MCP, has no auth
#   ./scripts/tunnel.sh both
#
# Requires `cloudflared` on PATH:
#   macOS:  brew install cloudflared
#   linux:  https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
#   docker: alias cloudflared='docker run --rm -it --network=host cloudflare/cloudflared:latest'

set -euo pipefail

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "cloudflared not found. See https://github.com/cloudflare/cloudflared#installing-cloudflared" >&2
  exit 1
fi

MODE="${1:-streamlit}"

tunnel_streamlit() {
  echo "→ Tunneling Streamlit  (http://localhost:8501)"
  echo "  When you're done, Ctrl-C to drop the tunnel."
  cloudflared tunnel --url http://localhost:8501
}

tunnel_mcp() {
  cat <<'WARN' >&2
⚠  About to expose the MCP server publicly.
   It has NO authentication. Anyone who learns the URL can:
     - read every paper in your DB
     - enqueue summary/comic jobs (burns LLM tokens)
     - call save_to_zotero against YOUR library
   Only do this for a brief test, and Ctrl-C as soon as you're done.
   For anything longer-lived, put Cloudflare Access in front of a named tunnel.
WARN
  echo
  echo "→ Tunneling MCP server  (http://localhost:8765)"
  cloudflared tunnel --url http://localhost:8765
}

case "$MODE" in
  streamlit) tunnel_streamlit ;;
  mcp)       tunnel_mcp ;;
  both)
    tunnel_streamlit &
    STREAMLIT_PID=$!
    trap 'kill $STREAMLIT_PID 2>/dev/null || true' EXIT
    tunnel_mcp
    ;;
  *)
    echo "Usage: $0 {streamlit|mcp|both}" >&2
    exit 1
    ;;
esac
