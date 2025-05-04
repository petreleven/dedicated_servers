#!/bin/sh
set -e
echo "Installing/updating valheim server...."

INSTALL_DIR=/valheim
chmod +x  /home/steam/steamcmd/steamcmd.sh
/home/steam/steamcmd/steamcmd.sh  \
    +login anonymous \
    +force_install_dir "/home/steam/server/scripts" \
    +app_update 896660 validate \
    +quit

echo "Copying BepInEx into game folder..."
cp /home/steam/server/BepInEX/*  "$INSTALL_DIR"

echo "Launching Valheim server with BepInEx..."
exec /home/steam/server/scripts/start.sh
