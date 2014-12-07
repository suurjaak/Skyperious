Installing Skyperious
=====================

### Windows ###

Download and launch the latest setup from
http://suurjaak.github.com/Skyperious/downloads.html.


### Mac ###

* install [Homebrew](http://brew.sh)
* install Python: open a terminal and run `brew install python2`
* install wxPython: run `brew install wxpython`
  (or use a suitable binary from http://wxpython.org/download.php)
* run `sudo easy_install pip`
* run `sudo pip install pyparsing`
* run `sudo pip install XlsxWriter`
* run `sudo pip install python-dateutil`
* run `sudo pip install Skype4Py`
* run `sudo pip install Pillow`

Download and extract the Skyperious source, launch `skyperious.sh` or
execute `python src\main.py`.


### Ubuntu/Debian ###

* run `sudo apt-get install wx2.8-i18n libwxgtk2.8-dev libgtk2.0-dev`
* run `sudo apt-get install python-wxgtk2.8 python-wxtools`
* run `sudo apt-get install python-pip`
* download and extract the Skyperious source
* open a terminal in the extracted directory
* run `sudo pip install -r requirements`

Launch `skyperious.sh`, or execute `python src\main.py`.
