Skyperious
==========

Skyperious is a Skype chat history tool.

You can open and browse Skype's main.db databases from before Skype version 8,
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


Also, a command line interface is available with key functions like
exporting, searching, syncing, and merging. 
The graphical version includes a Python console window.

Downloads, help texts, and more screenshots at
https://suurjaak.github.io/Skyperious.


History
-------

Skyperious was initially written in 2012 to work with local Skype databases
(main.db files in user folders),
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
or by importing a Skype export archive (a .tar archive manually downloaded
from Skype website, containing a messages.json file).

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

(Skype export is available in Skype web interface under
 My account -> Export files and chat history.
 The result is a .tar archive containing a messages.json file.)

Skyperious stores shared files and media in a subfolder next to the database,
browsable by themselves, available as in-program links, and embedded in HTML exports.

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
  merge FILE FILE ...        merge two or more Skype databases into a new database
  diff FILE1 FILE2           compare chat history in two Skype databases
  gui [FILE]                 launch Skyperious graphical program (default option)
  -h [option]                show command line help, for option if specified

More at https://suurjaak.github.io/Skyperious/help.html#commandline


Skyperious can be minimized to tray, clicking the tray icon opens a search popup.

The program itself is stand-alone, can work from any directory, and does not 
need additional installation, Windows installers have been provided for 
convenience. The installed program can be copied to a USB stick and used
elsewhere.

Skyperious has been tested under Windows 11, Windows 10, Windows 7, Windows Vista,
Windows XP, and reported to work under Windows 8.


Attribution
-----------

Skyperious has been built using the following open-source software:
- Python (http://www.python.org)
- wxPython (http://www.wxpython.org)
- appdirs (https://pypi.org/project/appdirs)
- beautifulsoup4 (https://pypi.org/project/beautifulsoup4)
* filetype (https://pypi.org/project/filetype)
- ijson (https://pypi.org/project/ijson)
- Pillow (https://pypi.org/project/Pillow)
- pyparsing (https://pypi.org/project/pyparsing)
- six (https://pypi.org/project/six)
- SkPy (https://pypi.org/project/SkPy)
- step, Simple Template Engine for Python (https://github.com/dotpy/step)
- XlsxWriter (https://pypi.org/project/XlsxWriter)


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
