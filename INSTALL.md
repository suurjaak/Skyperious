Installing Skyperious
=====================

### Windows ###

Download and launch the latest setup from
https://suurjaak.github.io/Skyperious/downloads.html.

or, to run from source code:
* install [Python](https://www.python.org/downloads/)
* Install [pip](https://pip.pypa.io/en/latest/installing/) if not installed
* run `pip install skyperious`
* run `skyperious`


### Mac ###

* install [Homebrew](http://brew.sh)
* install Python: open a terminal and run `brew install python`
* install wxPython: run `brew install wxpython`
  (or use a suitable binary from http://wxpython.org/download.php)
* run `sudo easy_install pip`
* run `pip install skyperious`
* run `skyperious`


### Linux ###

#### snap ####

* install Snap if not installed: `sudo apt-get install snap`
* install Skyperious from the Snap Store, or run `snap install skyperious`
* launch Skyperious from OS menu, or run `skyperious`


#### source ####

The graphical interface needs wxPython, best installed with one of the prepared
Python wheels available at https://extras.wxpython.org/wxPython4/extras/linux.

E.g. installing Skyperious for Ubuntu 20.04:

* run `sudo apt-get install libgtk-3-0 libsdl2-2.0 libsm6 libwebkit2gtk-4.0-37
                            libxtst6 python3 python3-pip`
* run `sudo pip install wxPython --find-links
                        https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-20.04`
* run `sudo pip install skyperious`
* run `skyperious`

Another option is to have wxPython built locally, e.g. for Ubuntu 20.04:

* run `sudo apt-get install build-essential libgtk-3-dev libsdl2-dev 
       libwebkit2gtk-4.0-dev python3 python3-pip`
* run `pip install skyperious`
* run `skyperious`

If pip scripts-folder is not yet in path, run before reopening terminal:

`echo "export PATH=\$PATH:\$HOME/.local/bin" >> $HOME/.profile`

If wxPython installation fails, consult https://wxpython.org/pages/downloads/.


### Docker ###

Skyperious has a [Dockerfile](Dockerfile), see
[build/README for Docker.md](build/README%20for%20Docker.md).


### General remarks ###

If running from source code, Skyperious needs Python 3.5+ or Python 2.7.

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
    # or: cd src && python -m skyperious
```
