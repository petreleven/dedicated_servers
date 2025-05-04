#!/bin/sh
set -e

echo "Installing/updating Valheim server...."

INSTALL_DIR=/valheim

steamcmd \
  +login anonymous \
  +force_install_dir "$INSTALL_DIR" \
  +app_update 896660 validate \
  +quit

echo "Copying BepInEx into game folder..."
cp -r /home/steam/server/BepInEX/. "$INSTALL_DIR"

echo "Launching Valheim server with BepInEx..."
exec /home/steam/server/scripts/start.sh
