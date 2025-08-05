#!/bin/sh
set -e

# This script allows for flexible container execution.
# - If the command starts with a '-', it's treated as arguments to the main kdf binary.
# - If the command is something else (like 'bash'), that command is run instead.
# - If no command is given, the kdf binary is run by default.

if [ "${1#-}" != "$1" ] || [ -z "$1" ]; then
  set -- /usr/local/bin/kdf "$@"
fi

exec "$@" 