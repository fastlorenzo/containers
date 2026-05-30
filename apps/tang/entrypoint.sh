#!/usr/bin/env sh
# Ensure a Tang signing keypair exists in the (persisted) key directory,
# then run tangd in its built-in standalone listen mode. Mount a persistent
# volume at /var/db/tang so keys survive container recreation.
set -eu

KEYDIR="${TANG_DB:-/var/db/tang}"
PORT="${TANG_PORT:-8080}"

mkdir -p "$KEYDIR"
# tangd-keygen execs the jose CLI; only generate when no keys are present.
if [ -z "$(ls -A "$KEYDIR" 2>/dev/null)" ]; then
    /usr/libexec/tangd-keygen "$KEYDIR"
fi

exec /usr/libexec/tangd --listen --port "$PORT" "$KEYDIR"
