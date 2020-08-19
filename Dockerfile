FROM ubuntu:18.04

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
      python2.7 \
      python-wxgtk3.0 \
      python-setuptools \
      python-pip \
      python-gobject \
      python-dbus \
      dbus-x11 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/local/src/skyperious
COPY requirements.txt .

RUN pip install -r requirements.txt

COPY . .
RUN python setup.py install



CMD /usr/local/bin/skyperious
