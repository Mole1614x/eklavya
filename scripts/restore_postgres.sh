#!/usr/bin/env bash
set -euo pipefail

: "${RESTORE_DATABASE_URL:?Set RESTORE_DATABASE_URL to a disposable restore target}"
: "${BACKUP_FILE:?Set BACKUP_FILE to a pg_dump custom archive}"

if [[ ${EKLAVYA_CONFIRM_RESTORE:-} != RESTORE_DISPOSABLE_ONLY ]]; then
  printf 'Set EKLAVYA_CONFIRM_RESTORE=RESTORE_DISPOSABLE_ONLY to acknowledge target replacement.\n' >&2
  exit 2
fi
[[ -f "$BACKUP_FILE" ]] || { printf 'Backup file does not exist: %s\n' "$BACKUP_FILE" >&2; exit 2; }
if [[ -n ${PRODUCTION_DATABASE_URL:-} && "$RESTORE_DATABASE_URL" == "$PRODUCTION_DATABASE_URL" ]]; then
  printf 'Refusing to restore over PRODUCTION_DATABASE_URL.\n' >&2
  exit 2
fi

restore_url=${RESTORE_DATABASE_URL/postgresql+psycopg:/postgresql:}
target_database=$(psql "$restore_url" --no-psqlrc --tuples-only --no-align --command 'select current_database()')
case "$target_database" in
  *_restore_test) ;;
  *) printf 'Restore target database must end with _restore_test; got %s\n' "$target_database" >&2; exit 2 ;;
esac

if [[ -f "$BACKUP_FILE.sha256" ]]; then
  backup_directory=$(dirname "$BACKUP_FILE")
  checksum_name=$(basename "$BACKUP_FILE.sha256")
  (
    cd "$backup_directory"
    sha256sum -c "$checksum_name"
  )
fi
pg_restore --clean --if-exists --exit-on-error --no-owner --no-privileges --dbname "$restore_url" "$BACKUP_FILE"
psql "$restore_url" --no-psqlrc --set ON_ERROR_STOP=1 --command 'select count(*) as restored_problems from problems;'
printf 'Restore verification completed for %s\n' "$target_database"
