#!/bin/bash


print_err() {
  echo $@ 2>&1
}

E_BADLOGGEDUSR=10

[ "$(id -u)" = "0" ] || exit $E_BADLOGGEDUSR


sudo apt-get update
sudo apt-get -y install xinit
sudo apt-get -y install python-dev python-wxgtk2.8 python-wxtools wx2.8-i18n
sudo apt-get -y install libwxgtk2.8-dev libgtk2.0-dev
sudo apt-get -y install python-pip
sudo apt-get -y --without-recommends install ubuntu-desktop


PIP_BIN=$(which pip)
sudo $PIP_BIN install -U pip==1.4 distribute setuptools

PIP_BIN=$(which pip)
sudo $PIP_BIN install skyperious

exit 0
