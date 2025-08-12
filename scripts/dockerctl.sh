#!/usr/bin/env bash
set -euo pipefail

# PingBrief Docker control utility
# Usage:
#   scripts/dockerctl.sh up [--build]
#   scripts/dockerctl.sh down
#   scripts/dockerctl.sh restart [service]
#   scripts/dockerctl.sh rebuild [service|all]
#   scripts/dockerctl.sh logs [service] [-f]
#   scripts/dockerctl.sh ps
#   scripts/dockerctl.sh exec service cmd...
#   scripts/dockerctl.sh sh service
#   scripts/dockerctl.sh bash service

PROJECT_ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE_PATH="${PROJECT_ROOT_DIR}/docker-compose.yml"
CORE_SERVICES=(api bot celery-worker celery-beat)

cd "${PROJECT_ROOT_DIR}"

compose() {
  docker compose \
    -f "${COMPOSE_FILE_PATH}" \
    "$@"
}

usage() {
  cat <<EOF
PingBrief docker control

Commands:
  up [--build]          Start all services (optionally build)
  down                  Stop and remove containers, networks
  restart [services..]  Restart all or specific services (space-separated)
  rebuild [all|svc..]   Rebuild images (all or specific services) and restart
  logs [-f] [svc..]     Show logs (all or specific), -f to follow
  ps                    Show container status
  exec service cmd...   Execute a command in a running service container
  sh service            Open /bin/sh in a service
  bash service          Open /bin/bash in a service
  restart-all           Restart core services: api, bot, celery-worker, celery-beat
  logs-core [-f]        Logs for core services (optionally follow)
  quick                 Restart core services and follow logs

Services defined:
  postgres, redis, api, celery-worker, celery-beat, bot
EOF
}

cmd_up() {
  local build_flag="${1:-}"
  if [[ "${build_flag}" == "--build" ]]; then
    compose up \
      -d \
      --build
  else
    compose up \
      -d
  fi
}

cmd_down() {
  compose down \
    --remove-orphans \
    --volumes
}

cmd_restart() {
  if [[ $# -eq 0 ]]; then
    compose restart
  else
    compose restart "$@"
  fi
}

cmd_rebuild() {
  if [[ $# -eq 0 || "$1" == "all" ]]; then
    compose build
    compose up -d
  else
    compose build "$@"
    compose up -d "$@"
  fi
}

cmd_logs() {
  local follow=""
  local services=()
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -f|--follow)
        follow="-f"; shift ;;
      *)
        services+=("$1"); shift ;;
    esac
  done
  if [[ ${#services[@]} -gt 0 ]]; then
    compose logs ${follow} "${services[@]}"
  else
    compose logs ${follow}
  fi
}

cmd_ps() {
  compose ps
}

cmd_exec() {
  local service="${1:-}"
  if [[ -z "${service}" ]]; then
    echo "Service name is required" >&2
    exit 1
  fi
  shift
  compose exec \
    -e COLUMNS="${COLUMNS:-120}" \
    -e LINES="${LINES:-40}" \
    "${service}" \
    "$@"
}

cmd_shell() {
  local shell_bin="${1}"
  shift
  local service="${1:-}"
  if [[ -z "${service}" ]]; then
    echo "Service name is required" >&2
    exit 1
  fi
  compose exec \
    -it \
    "${service}" \
    "${shell_bin}"
}

cmd_restart_all() {
  compose restart "${CORE_SERVICES[@]}"
}

cmd_logs_core() {
  local follow=""
  if [[ "${1:-}" == "-f" || "${1:-}" == "--follow" ]]; then
    follow="-f"
  fi
  compose logs ${follow} "${CORE_SERVICES[@]}"
}

cmd_quick() {
  cmd_restart_all
  cmd_logs_core -f
}

main() {
  local cmd="${1:-}"
  shift || true
  case "${cmd}" in
    up)           cmd_up "$@" ;;
    down)         cmd_down ;;
    restart)      cmd_restart "$@" ;;
    rebuild)      cmd_rebuild "$@" ;;
    logs)         cmd_logs "$@" ;;
    ps)           cmd_ps ;;
    exec)         cmd_exec "$@" ;;
    sh)           cmd_shell "/bin/sh" "$@" ;;
    bash)         cmd_shell "/bin/bash" "$@" ;;
    restart-all)  cmd_restart_all ;;
    logs-core)    cmd_logs_core "$@" ;;
    quick)        cmd_quick ;;
    -h|--help|help|"" ) usage ;;
    *) echo "Unknown command: ${cmd}" >&2; usage; exit 1 ;;
  esac
}

main "$@"

