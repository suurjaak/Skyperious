Skyperious 3.3
==============

Skyperious is a Skype database viewer and merger, written in Python.

You can open Skype SQLite databases and look at their contents:

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

Additionally, it doubles as a useful database tool for any SQLite file.
Also, a [command line interface](http://suurjaak.github.io/Skyperious/help.html#commandline)
is available with key functions like exporting, searching, and merging.
The graphical version includes a Python console window.

Making a backup of the database file is recommended before making any changes.
There is an easy "Save as" button for that on the database index page.

Downloads, help texts, and more screenshots at
http://suurjaak.github.io/Skyperious.

[![Screenshots](https://raw.github.com/suurjaak/Skyperious/gh-pages/img/th_collage.png)](https://raw.github.com/suurjaak/Skyperious/gh-pages/img/collage.png)


Using The Program
-----------------

Skyperious can look through user directories and detect Skype databases
automatically, or you can select specific files or folders.
Once added to the database list, a file can be opened for browsing, searching 
and exporting, or compared with another database for merging.

Searching an opened database supports a simple Google-like
[query syntax](http://suurjaak.github.io/Skyperious/help.html).
You can use keywords to search among specific authors or chats only
(`from:john`, `chat:links`), or from certain dates only 
(`date:2012`, `date:2010..2013-06`). Search supports 
wildcards, exact phrases, grouping, excluding, and either-or queries.

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

Skyperious can be minimized to tray, clicking the tray icon opens 
a search popup.

Skyperious can usually read from the same file Skype is currently using, but
this can cause temporary program errors. Writing to such a file is ill-advised.

The program is stand-alone and does not need installation, Windows installers 
have been provided for convenience. The installed program itself can be copied
to a USB stick and used elsewhere, same goes for the source code. The command
line interface only needs Python and pyparsing to run.

Skyperious has been tested under Windows 7, Windows Vista, Windows XP and
Ubuntu Linux, and reported to work under OS X and Windows 8. In source code
form, it should run wherever Python and the required Python packages are
installed.

If running from source code, launch `skyperious.sh` where shell scripts are 
supported, or launch `skyperious.bat` under Windows, or open a terminal and run
`python src/main.py` in Skyperious directory.

If you encounter a bug in the Skyperious GUI, you can send a report from menu
Help -> Send feedback.


Installation
------------

Windows: download and launch the latest setup from
http://suurjaak.github.io/Skyperious/downloads.html.

Mac/Linux: see (INSTALL.md)[INSTALL.md].

Skyperious has a Vagrantfile, see
[dist/README for Vagrant.md](dist/README for Vagrant.md).


Source Dependencies
-------------------

If running from source code, Skyperious needs Python 2.7 or 2.6,
and the following 3rd-party Python packages:
* wxPython 2.9+ (http://wxpython.org/)
* pyparsing (http://pyparsing.wikispaces.com/)
* XlsxWriter (https://pypi.python.org/pypi/XlsxWriter)
* Pillow (https://pypi.python.org/pypi/Pillow)
* dateutil (http://pypi.python.org/pypi/python-dateutil)
* Skype4Py (https://pypi.python.org/pypi/Skype4Py)

If wxPython is not available, the command line interface will function
regardless.

Skyperious can also run under wxPython 2.8.12+, with some layout quirks.
Python 2.6 will need the argparse library. Python 3 is yet unsupported.


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

Copyright (C) 2011-2015 by Erki Suurjaak.
Released as free open source software under the MIT License,
see [LICENSE.md](LICENSE.md) for full details.
