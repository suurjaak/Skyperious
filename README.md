Skyperious
===========

Skyperious is a Skype database viewer and merger, written in Python.

You can open local Skype SQLite databases and look at their contents:

- search across all messages and contacts
- browse chat history and export as HTML, see chat statistics
- import contacts from a CSV file to your Skype contacts
- view any database table and export their data
- change, add or delete data in any table
- execute direct SQL queries

You can also compare two Skype databases, scan for differences in chats and 
contacts, and copy them from one database to another. As Skype uses local files
to store conversation history, older messages tend to be lost when computers
get upgraded or changed; and message history can even differ on currently
active computers. Skyperious can restore the missing conversations into your
current message database.

Making a backup of the database file is recommended before making any changes.

Screenshots and Windows binaries at http://suurjaak.github.com/Skyperious.


Using The Program
-----------------

Skyperious can look through user directories and detect Skype databases
automatically, or you can select files yourself from any folder.

If running from source code, launch skyperious.bat under Windows, or
skyperious.sh where shell scripts are supported, or execute 'python main.py'

Skyperious has been tested under Windows XP, Windows Vista, Windows 7 and
Ubuntu Linux, its core functionality should work wherever Python and required
Python packages are installed.


Dependencies
------------

If running from source code, Skyperious needs Python 2.7 and the following
3rd-party Python packages:
* wxPython 2.9 (http://wxpython.org/)
* Python Imaging Library, required by wxPython
  (http://www.pythonware.com/products/pil/)

The following 3rd-party Python packages are used for convenient date period
choices in chat history, and for importing contacts, not strictly required:

* dateutil (http://pypi.python.org/pypi/python-dateutil)
* Skype4Py (https://github.com/awahlig/skype4py)

Skyperious can also run under Python 2.6 and wxPython 2.8, with some
layout quirks.


Attribution
-----------

Skyperious includes source from the following 3rd-party Python libraries:
* BeautifulSoup 3.2.1
  (http://www.crummy.com/software/BeautifulSoup)
* step, Simple Template Engine for Python
  (https://github.com/dotpy/step)

Emoticon images in HTML export are property of Skype Limited, (c) 2004-2006,
released under the Skype Component License 1.0.

Default avatar icon from:
  Fancy Avatars, (c) 2009 Brandon Mathis,
  http://brandonmathis.com/projects/fancy-avatars/

Several toolbar icons from:
  Fugue Icons, (c) 2010 Yusuke Kamiyamane,
  http://p.yusukekamiyamane.com/


License
-------

Copyright (C) 2011-2013 by Erki Suurjaak.
Released under the MIT License (see LICENSE.txt for details).
