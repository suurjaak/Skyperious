Skyperious
===========

Skyperious is a Skype database viewer and merger, written in Python.

You can open local Skype SQLite databases and look at their contents:

- search across all messages and contacts
- browse, filter and export chat histories, see chat statistics
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

If running from source code, Skyperious requires Python 2.7 and uses
these 3rd-party Python packages:

* wxPython 2.9 (http://wxpython.org/)
* Python Imaging Library, required by wxPython
  (http://www.pythonware.com/products/pil/)
* dateutil (http://pypi.python.org/pypi/python-dateutil)
* Skype4Py, (https://github.com/awahlig/skype4py)
* BeautifulSoup 3.2.0, already included in source
  (http://www.crummy.com/software/BeautifulSoup)

Skyperious also runs under Python 2.6 and wxPython 2.8, but with some quirks.


Attribution
-----------

Default avatar icon from:
  Fancy Avatars, (c) 2009 Brandon Mathis,
  http://brandonmathis.com/projects/fancy-avatars/

Several toolbar icons from:
  Fugue Icons, (c) 2010 Yusuke Kamiyamane,
  http://p.yusukekamiyamane.com/


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
