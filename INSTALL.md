Installing Skyperious
=====================

### Windows ###

Download and launch the latest setup from
http://suurjaak.github.com/Skyperious/downloads.html.

or, to run from source code:
* install [Python 2](https://www.python.org/downloads/)
* install [wxPython](http://wxpython.org/download.php)
* Install [pip](https://pip.pypa.io/en/latest/installing/)
* run `pip install skyperious`
* run `skyperious`


### Mac ###

* install [Homebrew](http://brew.sh)
* install Python 2: open a terminal and run `brew install python`
* install wxPython: run `brew install wxpython`
  (or use a suitable binary from http://wxpython.org/download.php)
* run `sudo easy_install pip`
* run `pip install skyperious`
* run `skyperious`


### Linux ###

Easiest to get wxPython installed for the graphical interface, is to use one of
the prepared wheels available at https://extras.wxpython.org/wxPython4/extras/linux.

E.g. installing Skyperious for Ubuntu 18.04:

* run `sudo apt-get install python python-pip libsdl2-2.0`
* run `sudo pip install -U -f --no-cache-dir https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-18.04 wxPython`
* run `sudo pip install skyperious`
* run `skyperious`

Another option is to have wxPython built locally, e.g. for Ubuntu 20.04:

* run `sudo apt-get install build-essential libgtk-3-dev libwxgtk3.0-dev python`
* run `wget https://bootstrap.pypa.io/get-pip.py`
* run `sudo python get-pip.py`
* run `sudo pip install skyperious`
* run `skyperious`

If pip scripts-folder is not yet in path, run before reopening terminal:

`echo "export PATH=\$PATH:\$HOME/.local/bin" >> $HOME/.profile`

If wxPython installation fails, consult https://wxpython.org/pages/downloads/.


### Docker ###

Skyperious has a [Dockerfile](Dockerfile), see
[dist/README for Docker.md](dist/README%20for%20Docker.md).


### Vagrant ###

Skyperious has a [Vagrantfile](Vagrantfile), see
[dist/README for Vagrant.md](dist/README%20for%20Vagrant.md).


### General remarks ###

If running from source code, Skyperious needs Python 2.7.
Python 3 is yet unsupported.

The graphical user interface needs wxPython 4.0 or later.

If wxPython is not available, the command line interface will function regardless.
If the other Python libraries are not available, the program will function 
regardless, only with lesser service - like lacking Excel export.

To run from source if Python, pip and git are installed:

```
    git clone https://github.com/suurjaak/Skyperious
    cd Skyperious
    pip install -r requirements.txt
    ./skyperious.sh
    # or: python -m skyperious
```
