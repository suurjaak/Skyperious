Skyperious
===========

Skyperious is a Skype database viewer and merger, written in Python.

It can open local Skype SQLite databases and look at their contents:

- search across all messages and contacts
- browse, filter and export chat histories, see chat statistics
- view any database table and export their data
- change, add or delete data in any table
- execute direct SQL queries

Skyperious can also compare two Skype databases, show the differences in chats
and contacts, and copy any spotted differences from one database to another.
Skype uses local database files to keep its chat history, and older messages
tend to get lost as computers get upgraded or changed. Skyperious was initially
written to import old chat messages from such files.

It is recommended to make a backup of the database file before making any
changes, as merging has not been extensively tested and might have issues.

Screenshots at http://suurjaak.github.com/Skyperious/screens.html.
Windows binaries at http://suurjaak.github.com/Skyperious/downloads.html.


Using The Program
-----------------

Run skyperious.bat under Windows, or skyperious.sh where shell scripts are
supported, or execute 'python main.py'. Or launch skyperious.exe if
using the precompiled Windows executable.

Skyperious can look through user directories and detect Skype databases
automatically, or you can select files yourself.

Skyperious has been tested under Windows XP, Windows Vista and Ubuntu Linux,
its core functionality should work wherever Python and required Python
packages are installed.


Dependencies
------------

If running as a Python script, Skyperious requires Python 2.7 and uses
these 3rd-party Python packages:

* wxPython 2.9 (http://wxpython.org/)
* Python Imaging Library, required by wxPython
  (http://www.pythonware.com/products/pil/)
* dateutil (http://pypi.python.org/pypi/python-dateutil)
* BeautifulSoup 3.2.0, already included
  (http://www.crummy.com/software/BeautifulSoup)
* pywin32, not required: used for launching/shutting down Skype
  (https://sourceforge.net/projects/pywin32/)

Skyperious also runs under Python 2.6 and wxPython 2.8, but with some quirks.


Attribution
-----------

Default avatar icon from:
  Fancy Avatars, (c) 2009 Brandon Mathis,
  http://brandonmathis.com/projects/fancy-avatars/


License
-------

(The MIT License)

Copyright (C) 2011-2013 by Erki Suurjaak

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
