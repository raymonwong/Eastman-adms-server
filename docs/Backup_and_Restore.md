# ADMS Backup and Restore

This document describes the first backup workflow for Eastman ADMS Server.

## What Is Backed Up

- MySQL database dump.
- `.env` configuration.
- Docker Compose and Dockerfile.
- Python requirements.
- Backup and restore guide.

The backup package is named:

```text
eastman-adms-backup-YYYYMMDD_HHMMSS.tar.gz
```

## Backup Locations

The backup script writes to:

- Host server: `/opt/eastman/Eastman-adms-server/backups`
- API container download directory: `/app/backup`

The Console page reads `/app/backup`, so the latest backup packages can be downloaded from:

```text
/settings/backup
```

## Manual Backup

Run on the server:

```bash
cd /opt/eastman/Eastman-adms-server
bash scripts/DT015_backup_create.sh
```

## Automatic Backup

Configure the schedule in Console:

```text
System Settings -> Backup Settings
```

Then install or refresh the cron job:

```bash
cd /opt/eastman/Eastman-adms-server
bash scripts/DT015_backup_cron_install.sh
```

The cron installer reads the latest backup time from the ADMS `integration_setting` table, so changes saved in Console are used when the schedule is reinstalled.

## Restore

Restore should be performed on a clean replacement server or after confirming the current database can be overwritten.

```bash
cd /opt/eastman/Eastman-adms-server
bash scripts/DT015_backup_restore.sh /path/to/eastman-adms-backup-YYYYMMDD_HHMMSS.tar.gz
```

The restore script imports `mysql.sql` from the backup package and restarts the Docker services.

## Recommended Routine

- Run automatic backup once per day during low traffic, for example 03:30 Dubai time.
- Keep 14 backup packages by default.
- Download important backup packages from Console to a local computer or network drive.
- Before major upgrades, run a manual backup first.
