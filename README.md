Skyperious 4.0
==============


Important Notice
----------------

Around 2017, starting from Skype version 8, Skype moved away from its famous
peer-to-peer architecture to a client-server system, and started to store 
conversation history on its own servers only.

Formerly, it used a local SQLite `main.db` database to store chats and messages,
which is what Skyperious was originally created to work with - merging chat 
histories from different computers into one.

Skyperious still works with existing `main.db` files, and can also download
newer messages from Skype online service. But any changes done to the database
no longer affect what is visible in the official Skype program.


---


Skyperious is a Skype database viewer and merger, written in Python.

You can open Skype SQLite databases and work with their contents:

- search across all messages and contacts
- read chat history in full, see chat statistics and word clouds
- export chats as HTML, text or spreadsheet
- synchronize messages from Skype online service
- view any database table and export their data, fix database corruption
- change, add or delete data in any table
- execute direct SQL queries

and

- synchronize messages in two Skype databases, merging their differences


Additionally, it doubles as a useful database tool for any SQLite file.
Also, a [command line interface](https://suurjaak.github.io/Skyperious/help.html#commandline)
is available with key functions like exporting, searching, syncing, and merging.
The graphical version includes a Python console window.

Downloads, help texts, and more screenshots at
https://suurjaak.github.io/Skyperious.

[![Screenshots](https://raw.github.com/suurjaak/Skyperious/gh-pages/img/th_collage.png)](https://raw.github.com/suurjaak/Skyperious/gh-pages/img/collage.png)


Using The Program
-----------------

Skyperious can look through user directories and detect Skype databases
automatically, or you can select specific files or folders.
Once added to the database list, a file can be opened for reading, searching 
and exporting, or compared with another database for merging.

Searching an opened database supports a simple Google-like
[query syntax](https://suurjaak.github.io/Skyperious/help.html).
You can use keywords to search among specific authors or chats only
(`from:john`, `chat:links`), or from certain dates only 
(`date:2012`, `date:2010..2013-06`). Search supports 
wildcards, exact phrases, grouping, excluding, and either-or queries.

Skyperious can log into Skype online service and download and save new messages
int the local database file. It can also create a new `main.db` database from 
scratch, by downloading all available history.

HTML export can download shared photos and embed them in the resulting HTML,
if password for the Skype account has been entered in online-page.
This can be disabled in File -> Advanced Options -> SharedImageAutoDownload.
Image download is also supported in the command-line interface.

In database comparison, you can scan one database for messages not found in
the other, and merge all detected messages to the other database. Or you can
read and copy specific chats and contacts.

Skyperious offers a number of options from the
[command line](https://suurjaak.github.io/Skyperious/help.html#commandline):
```
  export FILE [-t format]    export Skype databases as HTML, text or spreadsheet
  search "query" FILE        search Skype databases for messages or data
  sync FILE                  download new messages from Skype online service
  merge FILE1 FILE2          merge two or more Skype databases into a new database
  diff FILE1 FILE2           compare chat history in two Skype databases
  gui [FILE]                 launch Skyperious graphical program (default option)
```

Skyperious can be minimized to tray, clicking the tray icon opens 
a search popup.

The program itself is stand-alone, can work from any directory, and does not 
need additional installation, Windows installers have been provided for 
convenience. The installed program can be copied to a USB stick and used
elsewhere, same goes for the source code. The command line interface only needs
Python to run.

Skyperious has been tested under Windows 7, Windows Vista, Windows XP and
Ubuntu Linux, and reported to work under OS X and Windows 8. In source code
form, it should run wherever Python and the required Python packages are
installed.

If running from pip installation, run `skyperious` from the command-line. 
If running from straight source code, launch `skyperious.sh` where shell 
scripts are supported, or launch `skyperious.bat` under Windows, or open 
a terminal and run `python -m skyperious` in Skyperious directory.


Installation
------------

Windows: download and launch the latest setup from
https://suurjaak.github.io/Skyperious/downloads.html.

Mac/Linux/other: install Python, wxPython, pip, and run
`pip install skyperious`

The pip installation will add the `skyperious` command to path.
For more thorough instructions, see [INSTALL.md](INSTALL.md).

Skyperious has a Vagrantfile, see
[dist/README for Vagrant.md](dist/README for Vagrant.md).


Source Dependencies
-------------------

If running from source code, Skyperious needs Python 2.7,
and the following 3rd-party Python packages:
* wxPython 4.0+ (https://wxpython.org/)
The following are also listed in `requirements.txt` for pip:
* beautifulsoup4 (https://pypi.org/project/beautifulsoup4)
* dateutil (https://pypi.org/project/python-dateutil)
* Pillow (https://pypi.org/project/Pillow)
* pyparsing (https://pypi.org/project/pyparsing)
* SkPy (https://pypi.org/project/SkPy)
* XlsxWriter (https://pypi.org/project/XlsxWriter)

If wxPython is not available, the command line interface will function
regardless.
If other Python libraries are not available, the program will function 
regardless, only with lesser service - like lacking Excel export or full 
search syntax.

Python 3 is not supported.


Attribution
-----------

Skyperious includes step, Simple Template Engine for Python,
(c) 2012, Daniele Mazzocchio (https://github.com/dotpy/step).

Shared images slideshow in HTML export implemented with jsOnlyLightbox, 
(c) 2014, Felix Hagspiel (https://github.com/felixhagspiel/jsOnlyLightbox).

Emoticon images in HTML export are property of Skype Limited, (c) 2004-2006,
released under the [Skype Component License 1.0](res/emoticons/Skype Component License.txt).

Default avatar icon from:
  Fancy Avatars, (c) 2009 Brandon Mathis,
  https://github.com/imathis/fancy-avatars

Several icons from:
  Fugue Icons, (c) 2010 Yusuke Kamiyamane,
  https://p.yusukekamiyamane.com

Includes fonts Carlito Regular and Carlito bold,
https://fedoraproject.org/wiki/Google_Crosextra_Carlito_fonts

Binaries compiled with PyInstaller, https://www.pyinstaller.org

Installers created with Nullsoft Scriptable Install System,
https://nsis.sourceforge.io


License
-------

Copyright (c) by Erki Suurjaak.
Released as free open source software under the MIT License,
see [LICENSE.md](LICENSE.md) for full details.
