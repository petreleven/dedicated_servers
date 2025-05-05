FROM cm2network/steamcmd:latest

# Switch to root to install additional dependencies
USER root

# Install additional runtime dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libatomic1 \
        libpulse-dev \
        wget \
        unzip \
        libpulse0 && \
    rm -rf /var/lib/apt/lists/*

# Create server directory
RUN mkdir -p /home/steam/server

# Copy and make scripts executable
COPY scripts /home/steam/server/scripts
RUN chmod +x /home/steam/server/scripts/*.sh

# Download and unpack BepInEx mod-loader pack
ENV BEPINEX_VERSION=5.4.2202
RUN wget -qO /tmp/BepInExPack.zip \
    "https://gcdn.thunderstore.io/live/repository/packages/denikson-BepInExPack_Valheim-${BEPINEX_VERSION}.zip" && \
    unzip -q /tmp/BepInExPack.zip -d /home/steam/server/BepInEx && \
    rm /tmp/BepInExPack.zip

# Revert to steam user
RUN chown -R steam:steam /home/steam
RUN /home/steam/server/scripts/install.sh
USER steam

# Default startup: install then launch
CMD ["/bin/bash", "-c", "/home/steam/server/scripts/start.sh"]
