# Deployment

Target: Alpine/OpenRC VPS. Runs as user `frog` under cron.

## Prerequisites

- [uv](https://docs.astral.sh/uv/getting-started/installation/) — install as `frog`, not via package manager:
  ```sh
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- Google service account JSON with Calendar API enabled and editor access to the target calendar

## Install

Transfer the source (without `.git`) from your local machine, then install dependencies on the VPS.

```sh
# On local machine:
git archive HEAD | ssh frog@<vps> 'mkdir -p /home/frog/pk-timetable && tar -x -C /home/frog/pk-timetable'
```

Then on the VPS:

```sh
cd /home/frog/pk-timetable
uv sync
```

## Configure

```sh
cp .env.example .env
# Set GOOGLE_CALENDAR_ID in .env
nano .env

# Adjust group_col and other layout fields if needed
nano config.yaml

mkdir -p credentials
cp /path/to/service_account.json credentials/service_account.json
chmod 600 credentials/service_account.json
```

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
