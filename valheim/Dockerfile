FROM ubuntu:22.04

RUN apt-get update || true && \
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



RUN mkdir -p /home/steam/server   /home/steam/steamcmd

RUN curl -sL "https://steamcdn-a.akamaihd.net/client/installer/steamcmd_linux.tar.gz" \
    | tar zxvf - -C /home/steam/steamcmd

COPY scripts /home/steam/server/scripts
RUN chmod +x home/steam/server/scripts/*.sh

ENV BEPINEX_VERSION=5.4.2202
RUN wget -q -O /tmp/BepInExPack.zip \
    "https://gcdn.thunderstore.io/live/repository/packages/denikson-BepInExPack_Valheim-${BEPINEX_VERSION}.zip" && \
    unzip -q /tmp/BepInExPack.zip -d /home/steam/server/BepInEx && \
    rm /tmp/BepInExPack.zip

CMD ["/bin/bash", "-c", "/home/steam/server/scripts/install.sh && /home/steam/server/scripts/start.sh"]


