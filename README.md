Skyperious
==========

Skyperious is a Skype chat history tool.

You can open and browse Skype's `main.db` databases from before Skype version 8,
or create such databases from Skype online service and Skype export archives.

With an opened database, you can:

- search across all messages and contacts
- read chat history in full, see chat statistics and word clouds
- export chats and contacts as HTML, text or spreadsheet
- compare and synchronize messages with another Skype database, merging their differences


Additionally, it doubles as a useful database tool for any SQLite file:

- view and filter database tables, fix database corruption
- change, add or delete data in tables
- execute direct SQL queries
- export tables and query results as HTML, SQL or spreadsheet


Also, a [command line interface](https://suurjaak.github.io/Skyperious/help.html#commandline)
is available with key functions like exporting, searching, syncing, and merging.
The graphical version includes a Python console window.

Downloads, help texts, and more screenshots at
https://suurjaak.github.io/Skyperious.

[![Screenshots](https://raw.github.com/suurjaak/Skyperious/gh-pages/img/th_collage.png)](https://raw.github.com/suurjaak/Skyperious/gh-pages/img/collage.png)


History
-------

Skyperious was initially written in 2012 to work with local Skype databases
(`main.db` files in user folders),
mostly in order to merge chat histories from different computers
with different slices of chat history.

Over time it grew into a more general tool to search and export Skype chat history,
and manage the local Skype database e.g. pruning unneeded contacts.
It could also communicate with a local running Skype instance, to add contacts
from a file exported from MSN / GMail and the like.

Around 2017, starting from Skype version 8, Skype moved away from its famous
peer-to-peer architecture to a client-server system, closed API access to local
running Skype instances, and started to store conversation history on its own servers only.

Skyperious was updated to be able to create new local Skype databases,
by downloading messages from Skype online service via login inside Skyperious,
or by importing a Skype export archive (a `.tar` archive manually downloaded
from Skype website, containing a `messages.json` file).

In 2025 May, Skype is shut down altogether, and its accounts migrated to Microsoft Teams.

Skyperious is still able to import Skype export archives, 
and work locally with the database as before,
but synchronizing messages from Skype online will no longer be possible
once the online service is terminated.


Using The Program
-----------------

Skyperious can look through user directories and detect Skype databases
automatically, or you can select specific files or folders.
Once added to the database list, a file can be opened for reading, searching 
and exporting, or compared with another database for merging.

Searching an opened database supports a simple
[query syntax](https://suurjaak.github.io/Skyperious/help.html).
You can use keywords to search among specific authors or chats only
(`from:john`, `chat:links`), or from certain dates only
(`date:2012`, `date:2010..2013-06`). Search supports
wildcards, exact phrases, grouping, excluding, and either-or queries.

Skyperious can log into Skype online service and download and save new messages
into the local database file. It can also create a new `main.db` database from
scratch, by downloading all available history.

Skyperious can read chat history archives exported from Skype, and merge their
contents into an existing database, or create a new database from their contents.

(Skype export is available in Skype web interface under 
 My account -> Export files and chat history.
 The result is a `.tar` archive containing a `messages.json` file.)

Skyperious stores shared files and media in a subfolder next to the database,
browsable by themselves, available as in-program links, and embedded in HTML exports.

In database comparison, you can scan one database for messages and shares not found in
the other, and merge all detected differences to the other database.
Or you can read and copy specific chats and contacts. You can also merge chat history 
archives exported from Skype, via Compare and merge -> 
Select a Skype chat history export archive from your computer.

Skyperious offers a number of options from the
[command line](https://suurjaak.github.io/Skyperious/help.html#commandline):
```
  export FILE [-t format]    export Skype databases as HTML, text or spreadsheet
  search "query" FILE        search Skype databases for messages or data
  sync FILE                  download new messages from Skype online service
  contacts FILE [-t format]  export Skype contacts as HTML, text or spreadsheet
  create FILE [-u user]      create new Skype database, blank or from a Skype source
  merge FILE FILE ...        merge two or more Skype databases into a new database
  diff FILE1 FILE2           compare chat history in two Skype databases
  gui [FILE]                 launch Skyperious graphical program (default option)
  -h [option]                show command line help, for option if specified
```

Skyperious can be minimized to tray, clicking the tray icon opens a search popup.

The program itself is stand-alone, can work from any directory, and does not 
need additional installation, Windows installers have been provided for 
convenience. The installed program can be copied to a USB stick and used
elsewhere, same goes for the source code. The command line interface only needs
Python to run.

Skyperious has been tested under Windows 11, Windows 10, Windows 7, Windows Vista,
Windows XP and Ubuntu Linux, and reported to work under Fedora, OS X and Windows 8.
In source code form, it should run wherever Python and the required 
Python packages are installed.


Installation
------------

Windows: download and launch the latest setup from
https://suurjaak.github.io/Skyperious/downloads.html.

Linux Snap Store: install Skyperious, or run
`snap install skyperious`.

Mac/Linux/other: install Python, wxPython, pip, and run
`pip install skyperious`.

The pip installation will add the `skyperious` command to path.
For more thorough instructions, see [INSTALL.md](INSTALL.md).

Skyperious has a [Dockerfile](build/Dockerfile), see
[build/README for Docker.md](build/README%20for%20Docker.md).

#### Note for pip installation from 2025 March ####

SkPy dependency needs to be from the special Teams migration branch:

`pip install git+https://github.com/Terrance/SkPy@teams-migration`


Source Dependencies
-------------------

If running from source code, Skyperious needs Python 3.5+ or Python 2.7,
and the following 3rd-party Python packages:
* wxPython 4.0+ (https://wxpython.org/)

The following are also listed in `requirements.txt` for pip:
* appdirs (https://pypi.org/project/appdirs)
* beautifulsoup4 (https://pypi.org/project/beautifulsoup4)
* filetype (https://pypi.org/project/filetype, Py3 only)
* ijson (https://pypi.org/project/ijson)
* Pillow (https://pypi.org/project/Pillow)
* pyparsing (https://pypi.org/project/pyparsing)
* six (https://pypi.org/project/six)
* SkPy (https://pypi.org/project/SkPy; requires the `teams-migration` branch)
* step (https://pypi.org/project/step-template/)
* XlsxWriter (https://pypi.org/project/XlsxWriter)

If wxPython is not available, the command line interface will function
regardless.

If other Python libraries are not available, the program will function 
regardless, only with lesser service - like lacking Excel export or full 
search syntax. `appdirs` and `six` are mandatory.


Attribution
-----------

Shared images slideshow in HTML export implemented with jsOnlyLightbox, 
(c) 2014, Felix Hagspiel (https://github.com/felixhagspiel/jsOnlyLightbox).

Emoticon images in HTML export are property of Skype Limited, (c) 2004-2006,
released under the [Skype Component License 1.0](res/emoticons/Skype%20Component%20License.txt).

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
