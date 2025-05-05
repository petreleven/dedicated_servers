#!/bin/bash
set -e

echo "Installing/updating Valheim server..."
INSTALL_DIR=/valheim

# Use the full path to steamcmd provided by the base image
/home/steam/steamcmd/steamcmd.sh +force_install_dir "$INSTALL_DIR" \
    +login anonymous \
    +app_update 896660 validate \
    +quit

# Merge in the BepInEx files
echo "Copying BepInEx into game folder..."
cp -r /home/steam/server/BepInEx/. "$INSTALL_DIR"

echo "Valheim server installation complete!"
