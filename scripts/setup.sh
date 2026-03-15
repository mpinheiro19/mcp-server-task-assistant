#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(git -C "$(dirname "$0")" rev-parse --show-toplevel)"
MCP_ASSISTANT_DIR="${MCP_ASSISTANT_DIR:-$REPO_ROOT}"
ASSISTANT_FLOW_ROOT="${ASSISTANT_FLOW_ROOT:-$HOME/Codes}"

export MCP_ASSISTANT_DIR ASSISTANT_FLOW_ROOT

for tpl in "$REPO_ROOT/configs"/*.json.template; do
  out="${tpl%.template}"
  envsubst < "$tpl" > "$out"
  echo "Generated: $out"
done

echo ""
echo "MCP_ASSISTANT_DIR   = $MCP_ASSISTANT_DIR"
echo "ASSISTANT_FLOW_ROOT = $ASSISTANT_FLOW_ROOT"
