#!/bin/bash

### every exit != 0 fails the script
set -e

# Load environment variables from .env if present (for local dev or Docker ENV sync)
if [ -f "$(dirname "$0")/.env" ]; then
  set -a
  . "$(dirname "$0")/.env"
  set +a
fi

echo -e "\n\n------------------ APPUSER PASSWORD ------------------"
# use random generated if not set in ENV APPUSER_PASSWORD not defined
# + save password in /home/appuser/password.txt
if [ -z "$APPUSER_PASSWORD" ]; then
    APPUSER_PASSWORD=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 20)
    echo "$APPUSER_PASSWORD" > /home/appuser/password.txt
    chown appuser:users /home/appuser/password.txt
    echo -e "\n... generated random password and save in /home/appuser/password.txt"
else
    # Set password for appuser from ENV
    echo -e "\n... using password from ENV APPUSER_PASSWORD"
    echo "appuser:$APPUSER_PASSWORD" | chpasswd
fi



echo -e "\n\n------------------ APT INSTALL ------------------"
if [ -n "$APT_INSTALL" ]; then
    echo -e "\n... installing APT packages: $APT_INSTALL"
    export DEBIAN_FRONTEND=noninteractive
    apt update
    apt install -y $APT_INSTALL
else
    echo -e "\n... no APT packages to install"
fi

exit 0