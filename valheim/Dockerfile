FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        apt-transport-https \
        ca-certificates \
        curl \
        wget \
        gnupg \
        unzip \
        libatomic1 \
        libpulse-dev \
        libpulse0 && \
    rm -rf /var/lib/apt/lists/*

# Create required directories
RUN mkdir -p /home/steam/server /home/steam/steamcmd

# Install SteamCMD
RUN curl -sL "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz" \
    | tar zxvf - -C /home/steam/steamcmd

# Add SteamCMD to PATH
ENV PATH="/home/steam/steamcmd/linux32:${PATH}"

# Copy install and start scripts
COPY scripts /home/steam/server/scripts
RUN chmod +x /home/steam/server/scripts/*.sh

# Download and extract BepInExPack
ENV BEPINEX_VERSION=5.4.2202
RUN wget -q -O /tmp/BepInExPack.zip \
    "https://gcdn.thunderstore.io/live/repository/packages/denikson-BepInExPack_Valheim-${BEPINEX_VERSION}.zip" && \
    unzip -q /tmp/BepInExPack.zip -d /home/steam/server/BepInEx && \
    rm /tmp/BepInExPack.zip

# Default environment variables (can be overridden)
ENV SERVER_NAME="My Server" \
    PORT=2456 \
    WORLD="Dedicated" \
    PASSWORD="secret" \
    PUBLIC=1 \
    SAVEINTERVAL=300 \
    BACKUPSHORT=20 \
    BACKUPLONG=12 \
    CROSSPLAY=1 \
    PRESET=default \
    MODIFIER=none \
    SAVEDIR="/valheim-saves" \
    NOMAP=0

# Run install and then start script
CMD ["/bin/bash", "-c", "/home/steam/server/scripts/install.sh && /home/steam/server/scripts/start.sh"]
