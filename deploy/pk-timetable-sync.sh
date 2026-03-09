#!/bin/sh
# Wrapper script called by crond.
# Logs go to syslog (readable via: logread -t pk-timetable)

WORKDIR="/home/frog/pk-timetable"
UV="/home/frog/.local/bin/uv"
TAG="pk-timetable"

log() { logger -t "$TAG" "$*"; }

log "Starting sync"
cd "$WORKDIR" || { log "ERROR: workdir not found: $WORKDIR"; exit 1; }

output=$("$UV" run pk-timetable 2>&1)
rc=$?

if [ $rc -eq 0 ]; then
    log "OK: $output"
else
    log "FAILED (exit $rc): $output"
fi

exit $rc
