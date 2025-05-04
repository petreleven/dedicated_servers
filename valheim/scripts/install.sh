#!/bin/sh
set -e
echo "Installing/updating Valheim server..."
INSTALL_DIR=/valheim

# Use the system steamcmd provided by the base image
 ./steamcmd.sh  +login anonymous \
    +force_install_dir "$INSTALL_DIR" \
    +app_update 896660 validate \
    +quit

# Merge in the BepInEx files
echo "Copying BepInEx into game folder..."
cp -r /home/steam/server/BepInEx/. "$INSTALL_DIR"

# Hand off to the start script
exec /home/steam/server/scripts/start.sh
