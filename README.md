Skyperious
===========

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

Additionally, Skyperious doubles as a useful database browser for any SQLite file.

Making a backup of the database file is recommended before making any changes.

Screenshots and Windows binaries at http://suurjaak.github.com/Skyperious.


## Setup

### On Windows

Just download and launch the latest setup.exe from http://suurjaak.github.io/Skyperious/downloads.html.

### On Linux/Mac

If you are on Ubuntu, you can run the Bash script `setup-ubuntu.sh` which can be found in the `packaging/` dir (needs `sudo`); it will install all the dependencies on your local system.

If you are not on Ubuntu, or prefer not to install the dependencies locally, there's a Vagrantfile (see http://www.vagrantup.com) for you.

Pre-requisites:

- VirtualBox (https://www.virtualbox.org/wiki/Downloads)
- Vagrant (http://www.vagrantup.com/downloads.html)

A `vagrant up` will do the following:

- download a default vagrant box with ubuntu precise32 (no GUI)
- install Skyperious' dependencies
- install ubuntu desktop environment

#### Steps for using the Vagrantfile:

1. `vagrant up`
2. A VirtuaBox window will appear
3. Wait until `vagrant up` finishes setting up the VM
4. Log into the console as the user 'vagrant', password 'vagrant'
5. Run `startx -- :1`
6. Now you are in ubuntu desktop env
7. Open a terminal
8. `cd /vagrant`
9. `./skyperious.sh &`
10. et voilà

You'd better place your skype DB files in the root of the project (where the Vagrantfile is)
so that they are accessible within the VM in `/vagrant`.


## Using The Program

Skyperious can look through user directories and detect Skype databases
automatically, or you can select files yourself from any folder.
A database file can be opened for browsing, searching and exporting, or
compared with another database for merging.

Searching an opened database supports a simple Google-like query syntax. 
You can use keywords to search among specific authors or chats only, or from
certain dates only. Search supports wildcards, exact phrases, grouping,
excluding, and either-or queries.

In database comparison, two databases can be scanned for differences,
and you can merge results from one to the other wholesale, or browse and
copy specific chats and contacts.

Skyperious has been tested under Windows 7, Windows Vista, Windows XP and
Ubuntu Linux, and reported to work under OS X. In source code form, it
should run wherever Python and the required Python packages are installed.

If running from source code, launch skyperious.bat under Windows,
or skyperious.sh where shell scripts are supported,
or execute 'python src\main.py'.


## Dependencies

If running from source code, Skyperious needs Python 2.6+ and the following
3rd-party Python packages:
* wxPython 2.9 (http://wxpython.org/)
* Python Imaging Library, required by wxPython
  (http://www.pythonware.com/products/pil/)

The following 3rd-party Python packages are not strictly required,
but provide additional functionality like Excel export,
contact import, and convenient date period choices in chat history:

* XlsxWriter (https://github.com/jmcnamara/XlsxWriter)
* Skype4Py (https://github.com/awahlig/skype4py)
* dateutil (http://pypi.python.org/pypi/python-dateutil)

Skyperious can also run under wxPython 2.8.12+, with some layout quirks.
Python 3 is not supported.


## Attribution

Skyperious includes source from the following 3rd-party Python libraries:
* pyparsing 2.0.1
  (http://pyparsing.wikispaces.com/)
* step, Simple Template Engine for Python
  (https://github.com/dotpy/step)

Emoticon images in HTML export are property of Skype Limited, (c) 2004-2006,
released under the Skype Component License 1.0.

Default avatar icon from:
  Fancy Avatars, (c) 2009 Brandon Mathis,
  http://brandonmathis.com/projects/fancy-avatars/

Several icons from:
  Fugue Icons, (c) 2010 Yusuke Kamiyamane,
  http://p.yusukekamiyamane.com/

Skyperious binaries are compiled with PyInstaller 2.1,
http://www.pyinstaller.org

Skyperious installers are created with Nullsoft Scriptable Install System 2.4.6,
http://nsis.sourceforge.net/


## License

Copyright (C) 2011-2013 by Erki Suurjaak.
Released under the MIT License (see LICENSE.txt for details).
