#!/usr/bin/env bash
set -euo pipefail

: "${DATABASE_URL:?Set DATABASE_URL to the PostgreSQL database to back up}"

backup_dir=${BACKUP_DIR:-"$(pwd)/backups"}
retention_days=${BACKUP_RETENTION_DAYS:-14}
case "$backup_dir" in
  ""|/) printf 'Refusing unsafe BACKUP_DIR: %s\n' "$backup_dir" >&2; exit 2 ;;
esac
[[ "$retention_days" =~ ^[0-9]+$ ]] || { printf 'BACKUP_RETENTION_DAYS must be a non-negative integer\n' >&2; exit 2; }

database_url=${DATABASE_URL/postgresql+psycopg:/postgresql:}
timestamp=$(date -u +%Y%m%dT%H%M%SZ)
archive_name="eklavya-$timestamp.dump"
mkdir -p "$backup_dir"
chmod 700 "$backup_dir"
umask 077
temporary="$backup_dir/.eklavya-$timestamp.dump.tmp"
archive="$backup_dir/$archive_name"

cleanup() { rm -f "$temporary"; }
trap cleanup EXIT
pg_dump --format=custom --no-owner --no-privileges --file "$temporary" "$database_url"
pg_restore --list "$temporary" >/dev/null
mv "$temporary" "$archive"
(
  cd "$backup_dir"
  sha256sum "$archive_name" > "$archive_name.sha256"
)
find "$backup_dir" -maxdepth 1 -type f \( -name 'eklavya-*.dump' -o -name 'eklavya-*.dump.sha256' \) -mtime "+$retention_days" -delete
printf '%s\n' "$archive"
