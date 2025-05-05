#!/bin/sh
set -e
echo "Installing/updating Valheim server..."
INSTALL_DIR=/valheim

# Use the system steamcmd provided by the base image
 ./steamcmd.sh   +force_install_dir "$INSTALL_DIR" \
    +login anonymous \
    +app_update 896660 validate \
    +quit

# Merge in the BepInEx files
echo "Copying BepInEx into game folder..."
cp -r /home/steam/server/BepInEx/. "$INSTALL_DIR"


