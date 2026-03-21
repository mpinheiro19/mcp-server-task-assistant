#!/usr/bin/env bash
set -euo pipefail

# Função para carregar arquivos .env se existirem
load_env_file() {
  local env_file="$1"
  if [ -f "$env_file" ]; then
    echo "Carregando variáveis de $env_file"
    set -a
    # shellcheck disable=SC1090
    . "$env_file"
    set +a
  fi
}

# Garante execução a partir do diretório do script
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
cd "$SCRIPT_DIR/.."

# Carrega arquivos de ambiente na ordem de precedência
load_env_file ".env"
load_env_file ".env.local"
load_env_file ".env.dev"

# Descobre o root do repositório
REPO_ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel)"

# Define variáveis essenciais com fallback
MCP_ASSISTANT_DIR="${MCP_ASSISTANT_DIR:-$REPO_ROOT}"
ASSISTANT_FLOW_ROOT="${ASSISTANT_FLOW_ROOT:-$HOME/Codes}"

# Valida se variáveis essenciais estão definidas
if [ -z "$MCP_ASSISTANT_DIR" ] || [ -z "$ASSISTANT_FLOW_ROOT" ]; then
  echo "Erro: MCP_ASSISTANT_DIR e ASSISTANT_FLOW_ROOT devem estar definidos."
  exit 1
fi

export MCP_ASSISTANT_DIR ASSISTANT_FLOW_ROOT

# Gera arquivos de configuração a partir dos templates
if ! ls "$REPO_ROOT/configs"/*.json.template 1> /dev/null 2>&1; then
  echo "Erro: Nenhum template .json.template encontrado em $REPO_ROOT/configs."
  exit 1
fi

for tpl in "$REPO_ROOT/configs"/*.json.template; do
  out="${tpl%.template}"
  envsubst < "$tpl" > "$out"
  echo "Generated: $out"
done

# Gera .vscode/mcp.json com valores reais (gitignored, específico por máquina)
VSCODE_DIR="$REPO_ROOT/.vscode"
mkdir -p "$VSCODE_DIR"
cat > "$VSCODE_DIR/mcp.json" <<EOF
{
  "servers": {
    "assistant-flow": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "$MCP_ASSISTANT_DIR",
        "mcp-assistant"
      ],
      "env": {
        "ASSISTANT_FLOW_ROOT": "$ASSISTANT_FLOW_ROOT"
      }
    }
  }
}
EOF
echo "Generated: $VSCODE_DIR/mcp.json"

echo ""
echo "MCP_ASSISTANT_DIR   = $MCP_ASSISTANT_DIR"
echo "ASSISTANT_FLOW_ROOT = $ASSISTANT_FLOW_ROOT"
