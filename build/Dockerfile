# Run Skyperious in a container. Building the image:
#
#     docker build . -t skyperious
#
# and running afterwards:
#
#     xhost +
#     docker run -it --rm --net=host --mount source=/,target=/mnt/host,type=bind -e DISPLAY -v /tmp/.X11-unix/:/tmp/.X11-unix/ skyperious
#
# Add 'sudo' before docker commands if current user does not have rights for Docker.
#
# Add '--mount source="path to host directory",target=/etc/skyperious' after 'docker run'
# to retain Skyperious configuration in a host directory between runs,
# e.g. '--mount source=~/.config/skyperious,target=/etc/skyperious'.
#
# Host filesystem is made available under /mnt/host.

FROM ubuntu:20.04

RUN DEBIAN_FRONTEND=noninteractive DEBCONF_NONINTERACTIVE_SEEN=true \
 apt-get update \
 && apt-get install --assume-yes --no-install-recommends \
    libgtk-3-0 \
    libsm6 \
    libsdl2-2.0 \
    libwebkit2gtk-4.0-37 \
    libxtst6 \
    python3 \
    python3-pip \
 && rm -rf /var/lib/apt/lists/*

ENV LC_ALL   en_US.UTF-8
ENV LANG     en_US.UTF-8
ENV LANGUAGE en_US.UTF-8

RUN pip install wxPython==4.1.1 --no-cache-dir \
    --find-links https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-20.04

RUN pip install skyperious --no-cache-dir

VOLUME /etc/skyperious

CMD /usr/local/bin/skyperious --config-file /etc/skyperious/skyperious.ini
