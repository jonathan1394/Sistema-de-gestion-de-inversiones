#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"
SERVICES=(api web)

usage() {
  cat <<'EOF'
Usage: scripts/run_web_stack.sh [command] [options]

Commands:
  up          Build and start api + web (default)
  down        Stop and remove compose services
  logs        Follow api + web logs
  ps          Show api + web container status

Options:
  -d, --detached   Run containers in background (up only)
  --rebuild        Force image rebuild before start (up only)
  -h, --help       Show this help message

Examples:
  scripts/run_web_stack.sh
  scripts/run_web_stack.sh up --detached
  scripts/run_web_stack.sh logs
  scripts/run_web_stack.sh down
EOF
}

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf 'Error: required command not found: %s\n' "$1" >&2
    exit 1
  fi
}

require_command docker

if ! docker compose version >/dev/null 2>&1; then
  printf 'Error: docker compose is not available.\n' >&2
  exit 1
fi

if [[ ! -f "$COMPOSE_FILE" ]]; then
  printf 'Error: compose file not found at %s\n' "$COMPOSE_FILE" >&2
  exit 1
fi

if [[ ! -f "$ROOT_DIR/.env" ]]; then
  printf 'Warning: .env not found at %s/.env\n' "$ROOT_DIR" >&2
fi

command_name="up"
if [[ $# -gt 0 ]]; then
  case "$1" in
    up|down|logs|ps)
      command_name="$1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
  esac
fi

detached=false
rebuild=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    -d|--detached)
      detached=true
      ;;
    --rebuild)
      rebuild=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Error: unknown option: %s\n\n' "$1" >&2
      usage >&2
      exit 1
      ;;
  esac
  shift
done

compose_cmd=(docker compose -f "$COMPOSE_FILE")

case "$command_name" in
  up)
    up_args=(up)
    if [[ "$detached" == true ]]; then
      up_args+=(-d)
    fi
    if [[ "$rebuild" == true ]]; then
      up_args+=(--build)
    else
      up_args+=(--build)
    fi
    exec "${compose_cmd[@]}" "${up_args[@]}" "${SERVICES[@]}"
    ;;
  down)
    exec "${compose_cmd[@]}" down
    ;;
  logs)
    exec "${compose_cmd[@]}" logs -f "${SERVICES[@]}"
    ;;
  ps)
    exec "${compose_cmd[@]}" ps "${SERVICES[@]}"
    ;;
esac
