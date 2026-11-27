#!/bin/sh
set -eu

media_dir="${ROOM_MEDIA_DIR:-/data/room-media}"
media_parent="$(dirname "$media_dir")"

# Railway mounts persistent volumes as root-owned directories. Prepare the
# writable media directory before dropping privileges to the unprivileged app user.
mkdir -p "$media_parent" "$media_dir"
chown app:app "$media_parent"
chown -R app:app "$media_dir"

exec gosu app:app "$@"
