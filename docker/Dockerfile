FROM debian:trixie

LABEL MAINTAINER="Artur Zdolinski artur@zdolinski.com"
ENV VERSION=2025-04-26
ARG TZ=Etc/UTC
ARG USER=appuser
ARG UID=1000
ARG GID=100


USER root
### Envrionment config
ENV DISPLAY=:1 \
    VNC_ENABLED=true \
    VNC_PORT=5901 \
    VNC_COL_DEPTH=24 \
    VNC_RESOLUTION=1280x1024 \
    VNC_PW=vncpassword \
    VNC_VIEW_ONLY=false \
    NO_VNC_PORT=6901 \
    NO_VNC_HOME=/opt/noVNC \
    USER=${USER} \
    HOME=/home/${USER} \
    TERM=xterm \
    STARTUPDIR=/dockerstartup \
    DEBIAN_FRONTEND=noninteractive \
    APP_FOLDER=/app \
    NODE_VERSION=v23.6.0 \  
    SSHD_ENABLED=true \
    SSHD_PORT=22

WORKDIR /tmp

# Install dependencies
RUN apt-get update && \
    apt-get upgrade -y &&\
    apt-get install -y --no-install-recommends  \
    supervisor \
    libnss-wrapper \
    gettext \
    locales \
    tasksel \
    sudo \
    wget \
    curl \
    nano \
    htop \
    bzip2 \
    git \
    procps \
    net-tools \
    apt-utils \
    iputils-ping \
    psmisc \
    ttf-wqy-zenhei \
    fonts-liberation \
    python3-dotenv \
    python3-pip \
    python3-pip-whl \
    python3-venv \
    python3-dev \
    python3-numpy \
    npm \
    openssh-server \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

ENV LANG='en_US.UTF-8' LANGUAGE='en_US:en' LC_ALL='en_US.UTF-8'
RUN useradd -m -s /bin/bash -N -u $UID -g $GID $USER \
    && echo "${USER} ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers \
    && chmod 0440 /etc/sudoers \
    && chmod g+w /etc/passwd \
    && echo "${USER}:${USER}" | chpasswd \
    && mkdir -p $APP_FOLDER \
    && mkdir -p $STARTUPDIR \
    && chown -R $USER:$GID $APP_FOLDER \
    && chown -R appuser $STARTUPDIR \
    && mkdir -p $HOME/.npm \
    && chown -R $USER:$GID $HOME/.npm \
    && echo "en_US.UTF-8 UTF-8" > /etc/locale.gen \
    && locale-gen \
    && sed -i 's/^logfile=/user=root\nlogfile=/' /etc/supervisor/supervisord.conf \
    && sed -i 's/^chmod=0700/chmod=0777/' /etc/supervisor/supervisord.conf \
    && sed -i 's/run\//run\/supervisor\//g' /etc/supervisor/supervisord.conf  \
    && mkdir -p /var/log/supervisor/ \
    && mkdir -p /var/run/supervisor/ \
    && chown -R $USER /var/log/supervisor/ \
    && chown -R $USER /var/run/supervisor/

### Install xfce UI
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    xfce4 \
    xfce4-terminal \
    xterm \
    dbus-x11 \
    libdbus-glib-1-2 \
    && apt-get purge -y pm-utils *screensaver* \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

### Install chromium
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    chromium \
    && ln -sfn /usr/bin/chromium /usr/bin/chromium-browser \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

### Install xvnc-server & noVNC - HTML5 based VNC viewer
RUN apt-get update \
    && apt-get install -y \
    tigervnc-standalone-server \
    tigervnc-common \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

RUN printf '\n# docker-simpletoolserver-desktop-xfce4:\n$localhost = "no";\n1;\n' >>/etc/tigervnc/vncserver-config-defaults \
    && mkdir -p $NO_VNC_HOME/utils/websockify \
    && wget -qO- https://github.com/novnc/noVNC/archive/refs/tags/v1.6.0.tar.gz | tar xz --strip 1 -C $NO_VNC_HOME \
    && wget -qO- https://github.com/novnc/websockify/archive/refs/tags/v0.13.0.tar.gz | tar xz --strip 1 -C $NO_VNC_HOME/utils/websockify \
    && printf '<!DOCTYPE html>\n<html>\n  <head>\n    <meta http-equiv="refresh" content="0; url=vnc.html" />\n    <title>Redirecting...</title>\n  </head>\n  <body>\n    <p>Redirecting to <a href="vnc.html">VNC</a>...</p>\n  </body>\n</html>\n' > $NO_VNC_HOME/index.html

### For Python we will allow use PIP
RUN for f in /usr/lib/python3*/EXTERNALLY-MANAGED; do \
    if [ -f "$f" ]; then mv "$f" "${f}.disabled"; fi; \
    done

### Install nvm
RUN wget -qO- https://raw.githubusercontent.com/creationix/nvm/master/install.sh | bash && \
    /bin/bash -c "source $HOME/.nvm/nvm.sh && nvm install $NODE_VERSION && nvm use --delete-prefix $NODE_VERSION"

### Install python uvx
RUN PIP_BREAK_SYSTEM_PACKAGES=1 python3 -m pip install uvx && \
    pip3 install setuptools

# Switch to user
USER appuser
ADD --chown=$USER:$GID ./docker/src/home/ $HOME/
ADD ./docker/src/startup/ $STARTUPDIR
ENV PATH="/home/appuser/.local/bin:${PATH}"
RUN mkdir -p /app/server \
    && chmod +x $HOME/wm_startup.sh \
    && touch $HOME/.bashrc 

WORKDIR /home/appuser

### Install SimpleServer
ADD --chown=$USER:$GID ./src/server /app/server/
RUN rm -rf /app/server/data/config \
    && rm -rf /app/server/.env \
    && sudo pip3 install -r /app/server/requirements.txt

# Use supervisord to manage both VNC and Uvicorn
COPY ./docker/src/supervisor/conf.d/* /etc/supervisor/conf.d/
ENTRYPOINT ["sudo", "-E", "/usr/bin/supervisord", "--nodaemon", "-c", "/etc/supervisor/supervisord.conf"]

EXPOSE $VNC_PORT $NO_VNC_PORT