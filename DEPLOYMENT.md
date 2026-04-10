# Deployment

Target: Alpine/OpenRC VPS. Runs as user `frog` under cron.

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) — install as `frog`, not via package manager:
  ```sh
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- Google service account JSON with Calendar API enabled and editor access to the target calendar

## Install

Pack and transfer the source from your local machine, then install dependencies on the VPS.

```sh
# On local machine — create archive excluding .git, venv, and cache:
tar -czf /tmp/pk-timetable.tar.gz \
    --exclude='.git' \
    --exclude='.venv' \
    --exclude='__pycache__' \
    -C /path/to/workspace pk-timetable

# Transfer (adjust port and host):
scp -P <port> /tmp/pk-timetable.tar.gz frog@<vps>:/tmp/
```

Then on the VPS:

```sh
mkdir -p /home/frog/pk-timetable
tar -xzf /tmp/pk-timetable.tar.gz -C /home/frog/
uv sync
```

## Update

To push a newer version, repeat the pack+transfer step above, then on the VPS:

```sh
tar -xzf /tmp/pk-timetable.tar.gz -C /home/frog/
cp deploy/pk-timetable-sync.sh ~/bin/pk-timetable-sync
chmod +x ~/bin/pk-timetable-sync
uv sync
```

`tar -x` overwrites existing files but never deletes files not in the archive, so `.env`, `credentials/`, and `state/` are safe.

## Configure

```sh
cp .env.example .env
# Set GOOGLE_CALENDAR_ID and optionally DISCORD_WEBHOOK_URL in .env
nano .env

# Adjust group_col and other layout fields if needed
nano config.yaml

mkdir -p credentials
cp /path/to/service_account.json credentials/service_account.json
chmod 600 credentials/service_account.json
```

### Discord notifications (optional)

Uncomment and fill in `DISCORD_WEBHOOK_URL` in `.env`:

```sh
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

When set, the Python sync process sends a message to Discord after each successful sync that produces changes. The message lists every created, updated, and deleted event with its title, date, and time. The cron wrapper (`pk-timetable-sync.sh`) sends a separate failure-only notification via `curl` if the sync process exits non-zero — this covers cases where Python itself cannot start.

## Verify

```sh
uv run pk-timetable --dry-run
```

## Automate (cron)

```sh
mkdir -p ~/bin
cp deploy/pk-timetable-sync.sh ~/bin/pk-timetable-sync
chmod +x ~/bin/pk-timetable-sync
crontab deploy/crontab.txt   # runs at 06:00 and 18:00 daily
```

Logs: `logread | grep pk-timetable`

## Optional: OpenRC service (manual one-shot runs)

Requires root to install the init script:

```sh
sudo cp deploy/pk-timetable.openrc /etc/init.d/pk-timetable
sudo chmod +x /etc/init.d/pk-timetable
sudo rc-service pk-timetable start
```
