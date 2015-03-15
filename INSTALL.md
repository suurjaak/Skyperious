Installing Skyperious
=====================

### Windows ###

Download and launch the latest setup from
http://suurjaak.github.com/Skyperious/downloads.html.

or, to run from source code:
* install [Python 2](https://www.python.org/downloads/)
* install [wxPython](http://wxpython.org/download.php)
* Install [pip](https://pip.pypa.io/en/latest/installing.html)
* Download [Skyperious source](http://suurjaak.github.io/Skyperious/downloads.html)
* extract archive and open a command prompt in the extracted directory
* run `pip install -r requirements.txt`
* run `skyperious.bat`, or execute `python skyperious\main.py`


### Mac ###

* install [Homebrew](http://brew.sh)
* install Python 2: open a terminal and run `brew install python2`
* install wxPython: run `brew install wxpython`
  (or use a suitable binary from http://wxpython.org/download.php)
* run `sudo easy_install pip`
* download [Skyperious source](http://suurjaak.github.io/Skyperious/downloads.html)
* extract archive and open a terminal in the extracted directory
* run `sudo pip install -r requirements.txt`
* run `skyperious.sh`, or execute `python skyperious\main.py`


### Ubuntu/Debian ###

* run `sudo apt-get install wx2.8-i18n libwxgtk2.8-dev libgtk2.0-dev python-wxgtk2.8 python-wxtools python-pip`
* download [Skyperious source](http://suurjaak.github.io/Skyperious/downloads.html)
* extract archive and open a terminal in the extracted directory
* run `sudo pip install -r requirements.txt`
* run `skyperious.sh`, or execute `python skyperious\main.py`


### Vagrant ###

Skyperious has a Vagrantfile, see
[dist/README for Vagrant.md](dist/README for Vagrant.md).


### General remarks ###

If running from source code, Skyperious needs Python 2.7 or 2.6.
Python 2.6 will need the argparse library. Python 3 is yet unsupported.

The graphical user interface needs wxPython, preferably version 2.9+. 
wxPython 2.8 is also supported (2.8.12+), with some layout quirks.

If wxPython is not available, the command line interface will function regardless.
if XlsxWriter, Pillow, dateutil or Skype4Py are not available, the program
will function regardless, only with lesser service - like lacking XLSX export.

To use pip to install all Python dependencies (other than wxPython), execute
`pip install -r requirements.txt` in Skyperious directory.
