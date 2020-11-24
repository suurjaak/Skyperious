Skyperious
==========


Important notice
----------------

Around 2017, starting from Skype version 8, Skype moved away from its famous
peer-to-peer architecture to a client-server system, and started to store 
conversation history on its own servers only.

Formerly, it used a local SQLite main.db database to store chats and messages,
which is what Skyperious was originally created to work with - merging chat 
histories from different computers into one.

Skyperious still works with existing main.db files, and can also download
newer messages from Skype online service. But any changes done to the database
no longer affect what is visible in the official Skype program.


---


Skyperious is a Skype chat history tool, written in Python.

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


Additionally, it doubles as a useful database browser for any SQLite file.
Also, a command line interface is available with key functions like
exporting, searching, syncing, and merging. 
The graphical version includes a Python console window.

Downloads, help texts, and more screenshots at
https://suurjaak.github.io/Skyperious.


Using The Program
-----------------

Skyperious can look through user directories and detect Skype databases
automatically, or you can select specific files or folders.
Once added to the database list, a file can be opened for reading, searching 
and exporting, or compared with another database for merging.

Searching an opened database supports a simple Google-like query syntax. 
You can use keywords to search among specific authors or chats only
(from:john chat:links), or from certain dates only (date:2012, date:2010..2013).
Search supports wildcards, exact phrases, grouping, excluding,
and either-or queries.

Skyperious can log into Skype online service and download and save new messages
into the local database file. It can also create a new main.db database from
scratch, by downloading all available history.

Skyperious can read chat history archives exported from Skype, and merge their
contents into an existing database, or create a new database from their contents.

(Skype export is available in Skype client v8.5 under
 Settings -> Messaging -> Export chat history from Skype 7.x;
 and in Skype web interface under My account -> Export files and chat history.
 The result is a .tar archive containing a messages.json file.)

HTML export can download shared photos and embed them in the resulting HTML,
if password for the Skype account has been entered in online-page.
This can be disabled in File -> Advanced Options -> SharedImageAutoDownload.
Image download is also supported in the command-line interface.

In database comparison, you can scan one database for messages not found in
the other, and merge all detected messages to the other database. Or you can
read and copy specific chats and contacts. You can also merge chat history 
archives exported from Skype, via Compare and merge -> 
Select a Skype chat history export archive from your computer.

Skyperious offers a number of options from the command line:
  export FILE [-t format]    export Skype databases as HTML, text or spreadsheet
  search "query" FILE        search Skype databases for messages or data
  sync FILE                  download new messages from Skype online service
  create FILE [-u user]      create new Skype database, blank or from a Skype source
  merge FILE1 FILE2          merge two or more Skype databases into a new database
  diff FILE1 FILE2           compare chat history in two Skype databases
  gui [FILE]                 launch Skyperious graphical program (default option)
  -h [option]                show command line help, for option if specified

More at https://suurjaak.github.io/Skyperious/help.html#commandline


Skyperious can be minimized to tray, clicking the tray icon opens 
a search popup.

The program itself is stand-alone, can work from any directory, and does not 
need additional installation, Windows installers have been provided for 
convenience. The installed program can be copied to a USB stick and used
elsewhere.

Skyperious has been tested under Windows 10, Windows 7, Windows Vista,
Windows XP, and reported to work under Windows 8.


Attribution
-----------

Skyperious has been built using the following open-source software:
- Python 2.7.18 (http://www.python.org)
- wxPython 4.1.0 (http://www.wxpython.org)
- appdirs 1.4.4 (https://pypi.org/project/appdirs)
- beautifulsoup4 4.9.1 (https://pypi.org/project/beautifulsoup4)
- ijson 3.1 (https://pypi.org/project/ijson)
- Pillow 6.2.2 (https://pypi.org/project/Pillow)
- pyparsing 2.4.7 (https://pypi.org/project/pyparsing)
- SkPy 0.10.1 (https://pypi.org/project/SkPy)
- step, Simple Template Engine for Python (https://github.com/dotpy/step)
- XlsxWriter 1.2.9 (https://pypi.org/project/XlsxWriter)


Shared images slideshow in HTML export implemented with jsOnlyLightbox, 
(c) 2014, Felix Hagspiel (https://github.com/felixhagspiel/jsOnlyLightbox).

Emoticon images in HTML export are property of Skype Limited, (c) 2004-2006,
released under the Skype Component License 1.0.

Default avatar icon from:
  Fancy Avatars, (c) 2009 Brandon Mathis,
  https://github.com/imathis/fancy-avatars

Several icons from:
  Fugue Icons, (c) 2010 Yusuke Kamiyamane,
  https://p.yusukekamiyamane.com/

Includes fonts Carlito Regular and Carlito bold,
https://fedoraproject.org/wiki/Google_Crosextra_Carlito_fonts

Binaries compiled with PyInstaller, https://www.pyinstaller.org

Installer created with Nullsoft Scriptable Install System,
https://nsis.sourceforge.io/


License
-------

(The MIT License)

Copyright (C) 2011 by Erki Suurjaak

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

The software is provided "as is", without warranty of any kind, express or
implied, including but not limited to the warranties of merchantability,
fitness for a particular purpose and noninfringement. In no event shall the
authors or copyright holders be liable for any claim, damages or other
liability, whether in an action of contract, tort or otherwise, arising from,
out of or in connection with the software or the use or other dealings in
the software.


For licenses of included libraries, see "3rd-party licenses.txt".
