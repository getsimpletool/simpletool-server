#!/bin/bash

### every exit != 0 fails the script
set -e


# If port SSHD_PORT not defined, use default one
if [ -z "$SSHD_PORT" ]; then
    SSHD_PORT=22
fi

# Start SSHD only when env SSHD_ENABLED is set to true
echo "SSHD_ENABLED: $SSHD_ENABLED"
if [ "$SSHD_ENABLED" = true ]; then
    # Check if ./etc/ssh/ssh_host_* files exist
    if [ ! -f "/etc/ssh/ssh_host_rsa_key" ]; then
        rm /etc/ssh/ssh_host_*
        ssh-keygen -A
    fi
    mkdir -p /run/sshd
    /usr/sbin/sshd -D -d -p $SSHD_PORT
elif [ "$SSHD_ENABLED" = false ] || [ "$SSHD_ENABLED" = False ]; then
    echo "SSHD is disabled. Emulating running container with sleep..."
    sleep infinity
fi

# Wait for the process to exit
wait