#!/bin/sh
# Wrapper script called by crond.
# Logs go to syslog (readable via: logread | grep pk-timetable)

WORKDIR="/home/frog/pk-timetable"
UV="/home/frog/.local/bin/uv"
TAG="pk-timetable"

log() { logger -t "$TAG" "$*"; }

notify() {
    [ -z "$DISCORD_WEBHOOK_URL" ] && return
    curl -s -X POST "$DISCORD_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{\"content\": \"$1\"}"
}

log "Starting sync"
cd "$WORKDIR" || { log "ERROR: workdir not found: $WORKDIR"; exit 1; }

# Load .env
[ -f "$WORKDIR/.env" ] && . "$WORKDIR/.env"

output=$("$UV" run pk-timetable 2>&1)
rc=$?

if [ $rc -eq 0 ]; then
    log "OK: $output"
    date -Iseconds > "$WORKDIR/state/last_success.txt"
    notify "pk-timetable: sync OK $(date -Iseconds)"
else
    log "FAILED (exit $rc): $output"
    notify "pk-timetable: FAILED (exit $rc)"
fi

exit $rc
