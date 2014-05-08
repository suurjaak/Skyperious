Skyperious 3.1
==============

Skyperious is a Skype database viewer and merger, written in Python.

You can open local Skype SQLite databases and look at their contents:

- search across all messages and contacts
- browse chat history and export as HTML, see chat statistics
- import contacts from a CSV file to your Skype contacts
- view any database table and export their data, fix database corruption
- change, add or delete data in any table
- execute direct SQL queries
and
- synchronize messages in two Skype databases: keep chat history up-to-date on
  different computers, or restore missing messages from older files into the
  current one

Additionally, it doubles as a useful database browser for any SQLite file.
Also, a command line interface is available with key functions like
exporting, searching, and merging. 

Making a backup of the database file is recommended before making any changes.

Screenshots and Windows binaries at http://suurjaak.github.com/Skyperious/screens.html.


Using The Program
-----------------

Skyperious can look through user directories and detect Skype databases
automatically, or you can select files yourself from any folder.
A database file can be opened for browsing, searching and exporting, or
compared with another database for merging.

Searching an opened database supports a simple Google-like query syntax. 
You can use keywords to search among specific authors or chats only
(`from:john chat:links`), or from certain dates only (`date:2010..2013`).
Search supports wildcards, exact phrases, grouping, excluding,
and either-or queries.

In database comparison, you can scan one database for messages not found in
the other, and merge all detected messages to the other database. Or you can
browse and copy specific chats and contacts.

Skyperious offers a number of options from the command line:
```
  export FILE [-t format]    export Skype databases as HTML, text or spreadsheet
  search "query" FILE        search Skype databases for messages or data
  merge FILE1 FILE2          merge two or more Skype databases into a new database
  diff FILE1 FILE2           compare chat history in two Skype databases
  gui [FILE]                 launch Skyperious graphical program (default option)
```

Skyperious has been tested under Windows 7, Windows Vista, Windows XP and
Ubuntu Linux, and reported to work under OS X and Windows 8. In source code
form, it should run wherever Python and the required Python packages are
installed.

If running from source code, launch skyperious.bat under Windows,
or skyperious.sh where shell scripts are supported,
or execute 'python src\main.py'.


Dependencies
------------

If running from source code, Skyperious needs Python 2.7 or 2.6,
and the following 3rd-party Python packages:
* Pillow (https://pypi.python.org/pypi/Pillow)
  or PIL, the Python Imaging Library (http://www.pythonware.com/products/pil/)
* pyparsing (http://pyparsing.wikispaces.com/)
* wxPython 2.9+ (http://wxpython.org/)

If wxPython is not available, the command line interface will function
regardless.

The following 3rd-party Python packages are not strictly required,
but provide additional functionality like Excel export,
contact import, and convenient date period choices in chat history:

* XlsxWriter (https://github.com/jmcnamara/XlsxWriter)
* Skype4Py (https://github.com/awahlig/skype4py)
* dateutil (http://pypi.python.org/pypi/python-dateutil)

Skyperious can also run under wxPython 2.8.12+, with some layout quirks.
Python 2.6 will need the argparse library. Python 3 is not currently supported.


Installation
------------

### Windows ###

Download and launch the latest setup from
http://suurjaak.github.com/Skyperious/downloads.html.

### Mac ###

* install [Homebrew](brew.sh)
* install Python: open a terminal and run `brew install python2`
* install wxPython: run `brew install --python wxmac --devel`
  (or use a suitable binary from http://wxpython.org/download.php)
* run `brew install PIL` (or `brew install Pillow`)
* run `brew install pyparsing`
* run `brew install python-dateutil`
* run `brew install Skype4Py`
* run `brew install XlsxWriter`

Download and extract the Skyperious source, launch skyperious.sh.

### Ubuntu/Debian ###

* run `sudo aptitude install wx2.8-i18n libwxgtk2.8-dev libgtk2.0-dev`
* run `sudo aptitude install python-wxgtk2.8 python-wxtools`
* run `sudo aptitude install python-pip`
* download and extract the Skyperious source
* open a terminal in the extracted directory
* run `sudo pip install -r requirements`

Launch skyperious.sh.

### Vagrant ###

If you have problems using above methods, you can try using Vagrant.

Pre-requisites:

- [Virtualbox][1] 4.0 or greater.
- [Vagrant][2] 1.5 or greater.

Clone this project and get it running!

```
git clone https://github.com/suurjaak/Skyperious
cd Skyperious/packaging
vagrant up
```

A `vagrant up` will do the following:

- download a default vagrant box with Ubuntu precise32 (no GUI)
- install Skyperious' dependencies
- install Ubuntu desktop environment

#### Steps for using the Vagrantfile:

1. `vagrant up`
2. A VirtuaBox window will appear
3. Wait until `vagrant up` finishes setting up the VM
4. Log into the console as the user `vagrant`, password `vagrant`
5. Run `startx -- :1`
6. Now you are in ubuntu desktop env
7. Open a terminal
8. `cd /vagrant`
9. `./skyperious.sh &`
10. et voilà

You'd need to place your skype DB files in the root of the project so that they are accessible within the VM in `/vagrant`.

Attribution
-----------

Skyperious includes step, Simple Template Engine for Python,
(c) 2012, Daniele Mazzocchio (https://github.com/dotpy/step).

Emoticon images in HTML export are property of Skype Limited, (c) 2004-2006,
released under the Skype Component License 1.0.

Default avatar icon from:
  Fancy Avatars, (c) 2009 Brandon Mathis,
  http://brandonmathis.com/projects/fancy-avatars/

Several icons from:
  Fugue Icons, (c) 2010 Yusuke Kamiyamane,
  http://p.yusukekamiyamane.com/

Includes fonts Carlito Regular and Carlito bold,
https://fedoraproject.org/wiki/Google_Crosextra_Carlito_fonts

Binaries compiled with PyInstaller 2.1, http://www.pyinstaller.org

Installers created with Nullsoft Scriptable Install System 3.0a2,
http://nsis.sourceforge.net/


License
-------

Copyright (C) 2011-2014 by Erki Suurjaak.
Released under the MIT License (see [LICENSE.md](LICENSE.md) for details).


  [1]: https://www.virtualbox.org/wiki/Downloads
  [2]: http://www.vagrantup.com/downloads.html
