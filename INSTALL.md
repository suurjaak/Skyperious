Installing Skyperious
=====================

### Windows ###

Download and launch the latest setup from
http://suurjaak.github.com/Skyperious/downloads.html.

or, to run from source code:
* install [Python 2](https://www.python.org/downloads/)
* install [wxPython](http://wxpython.org/download.php)
* Install [pip](https://pip.pypa.io/en/latest/installing.html)
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


### Ubuntu/Debian ###

* run `sudo apt-get install wx3.0 libwxgtk3.0-dev python-wxtools python-dev python-pip`
* run `pip install skyperious`
* run `skyperious`

For an older system not supporting wx 3:
* run `sudo apt-get install wx2.8-i18n libwxgtk2.8-dev libgtk2.0-dev python-wxgtk2.8 python-wxtools python-pip`

If pip scripts-folder is not yet in path, run before reopening terminal:

`echo "export PATH=\$PATH:\$HOME/.local/bin" >> $HOME/.profile`


### Vagrant ###

Skyperious has a Vagrantfile, see
[dist/README for Vagrant.md](dist/README for Vagrant.md).


### General remarks ###

If running from source code, Skyperious needs Python 2.7 or 2.6.
Python 2.6 will need the argparse library. Python 3 is yet unsupported.

The graphical user interface needs wxPython, preferably version 2.9 or later.
wxPython 2.8 is also supported (2.8.12+), with some layout quirks.

If wxPython is not available, the command line interface will function regardless.
if the other Python libraries are not available, the program will function 
regardless, only with lesser service - like lacking Excel export.

To run from source if Python, pip and git are installed:

```
    git clone https://github.com/suurjaak/Skyperious
    cd Skyperious
    pip install -r requirements.txt
    ./skyperious.sh
```
