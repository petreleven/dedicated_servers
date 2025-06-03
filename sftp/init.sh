#!/bin/bash
for user_home in /home/* ; do
  if [ -d "$user_home" ]; then
    username=`basename $user_home`
    echo "Setup $user_home/server folder for $username"
    mkdir -p $user_home/server
    chown -R $username:users $user_home/server

    # Start background ownership monitor
    (
      while true; do
        sleep 6000  # Fixed: removed parentheses, sleep takes seconds not function call
        # Fixed: added spaces around != for proper comparison
        if [ "$(stat -c %U "$user_home/server" 2>/dev/null)" != "$username" ]; then
          echo "$(date): Fixing permissions for $user_home/server"  # Added timestamp
          chown -R $username:users $user_home/server
        fi
      done
    ) &  # Run in background
  fi
done
