#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DATA_DIR="${POSTGRES_DATA_DIR:-$PROJECT_ROOT/.postgres-data}"
PORT="${POSTGRES_PORT:-55432}"
HOST="127.0.0.1"
SOCKET_DIR="$DATA_DIR"
APP_USER="${POSTGRES_USER:-faro_politico_app}"
DEV_DB="${POSTGRES_DB:-faro_politico_dev}"
TEST_DB="${POSTGRES_TEST_DB:-faro_politico_test}"
ADMIN_USER="${POSTGRES_ADMIN_USER:-faro_cluster_admin}"

if [[ -x "$PROJECT_ROOT/.local/postgresql/usr/bin/postgres" ]]; then
  PG_BIN="$PROJECT_ROOT/.local/postgresql/usr/bin"
  export LD_LIBRARY_PATH="$PROJECT_ROOT/.local/postgresql/usr/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
  PG_SHARE="$PROJECT_ROOT/.local/postgresql/usr/share/postgresql"
elif command -v postgres >/dev/null 2>&1; then
  PG_BIN="$(dirname "$(command -v postgres)")"
  PG_SHARE="$("$PG_BIN/pg_config" --sharedir)"
else
  echo "PostgreSQL no está instalado. En Arch: sudo pacman -S postgresql" >&2
  exit 1
fi

init_cluster() {
  if [[ ! -f "$DATA_DIR/PG_VERSION" ]]; then
    mkdir -p "$DATA_DIR"
    "$PG_BIN/initdb" -D "$DATA_DIR" -L "$PG_SHARE" \
      --username="$ADMIN_USER" --auth-local=trust --auth-host=trust \
      --encoding=UTF8 --locale=C.UTF-8
  fi
}

is_ready() {
  "$PG_BIN/pg_isready" -h "$HOST" -p "$PORT" >/dev/null 2>&1
}

start_server() {
  init_cluster
  if ! is_ready; then
    "$PG_BIN/pg_ctl" -D "$DATA_DIR" -l "$DATA_DIR/postgres.log" \
      -o "-h $HOST -p $PORT -k $SOCKET_DIR" start
  fi
}

create_databases() {
  start_server
  "$PG_BIN/psql" -h "$SOCKET_DIR" -p "$PORT" -U "$ADMIN_USER" -d postgres \
    -v ON_ERROR_STOP=1 -v app_user="$APP_USER" <<'SQL'
SELECT format(
  'CREATE ROLE %I LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT',
  :'app_user'
)
WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname = :'app_user') \gexec
SQL
  for database in "$DEV_DB" "$TEST_DB"; do
    if ! "$PG_BIN/psql" -h "$SOCKET_DIR" -p "$PORT" -U "$ADMIN_USER" \
      -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='$database'" \
      | grep -q 1; then
      "$PG_BIN/createdb" -h "$SOCKET_DIR" -p "$PORT" -U "$ADMIN_USER" \
        -O "$APP_USER" "$database"
    fi
  done
}

case "${1:-}" in
  up)
    create_databases
    "$PG_BIN/pg_isready" -h "$HOST" -p "$PORT"
    ;;
  down)
    if [[ -f "$DATA_DIR/PG_VERSION" ]]; then
      "$PG_BIN/pg_ctl" -D "$DATA_DIR" stop
    else
      echo "La instancia local no está inicializada."
    fi
    ;;
  status)
    if is_ready; then
      "$PG_BIN/psql" -h "$HOST" -p "$PORT" -U "$APP_USER" -d "$DEV_DB" \
        -c "SELECT version(), current_database(), current_user;"
    else
      echo "PostgreSQL no está disponible en $HOST:$PORT" >&2
      exit 1
    fi
    ;;
  create)
    create_databases
    ;;
  reset)
    read -r -p "Esto eliminará las bases $DEV_DB y $TEST_DB. Escriba RESET: " answer
    if [[ "$answer" != "RESET" ]]; then
      echo "Operación cancelada."
      exit 1
    fi
    start_server
    "$PG_BIN/dropdb" -h "$SOCKET_DIR" -p "$PORT" -U "$ADMIN_USER" \
      --if-exists "$DEV_DB"
    "$PG_BIN/dropdb" -h "$SOCKET_DIR" -p "$PORT" -U "$ADMIN_USER" \
      --if-exists "$TEST_DB"
    create_databases
    ;;
  *)
    echo "Uso: $0 {up|down|status|create|reset}" >&2
    exit 2
    ;;
esac
