#!/bin/bash
# sleep.sh — init container wait script for kopia-operator
# Usage: sleep.sh <interval_seconds> <max_retries>
# Sleeps for the given interval, up to max_retries times.
# Used as an init container to add a brief delay before the snapshot runs.

INTERVAL="${1:-1}"
MAX_RETRIES="${2:-10}"

echo "Waiting ${INTERVAL}s x ${MAX_RETRIES} before starting..."
for i in $(seq 1 "$MAX_RETRIES"); do
  sleep "$INTERVAL"
done
echo "Wait complete, proceeding."
