#!/bin/bash
for user_home in /home/* ; do
  if [ -d "$user_home" ]; then
    username=`basename $user_home`
    echo "Setup $user_home/valheim folder for $username"
    mkdir -p $user_home/valheim
    chown -R $username:users $user_home/valheim
  fi
done
