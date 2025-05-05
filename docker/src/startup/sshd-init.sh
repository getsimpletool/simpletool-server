#!/bin/bash

### every exit != 0 fails the script
set -e

# Load environment variables from .env if present (for local dev or Docker ENV sync)
if [ -f "$(dirname "$0")/.env" ]; then
  set -a
  . "$(dirname "$0")/.env"
  set +a
fi

# If port SSHD_PORT not defined, use default one
if [ -z "$SSHD_PORT" ]; then
    SSHD_PORT=22
fi

# Start SSHD only when env SSHD_ENABLED is set to true
echo "SSHD_ENABLED: $SSHD_ENABLED"
echo "SSHD_PORT: $SSHD_PORT"

if [ "$SSHD_ENABLED" = true ]; then
    # Check if ./etc/ssh/ssh_host_* files exist
    if [ ! -f "/etc/ssh/ssh_host_rsa_key" ]; then
        rm /etc/ssh/ssh_host_*
        ssh-keygen -A
    fi
    mkdir -p /run/sshd
    /usr/sbin/sshd -D -p $SSHD_PORT
elif [ "$SSHD_ENABLED" = false ] || [ "$SSHD_ENABLED" = False ]; then
    echo "SSHD is disabled. Skipping SSHD startup."
    exit 0
fi
