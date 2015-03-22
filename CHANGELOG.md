CHANGELOG
=========

3.3.1d, 2015-03-21
------------------
- fixed showing wrong author in transfer statistics for certain messages;
- fixed a parsing issue with certain Skype messages;
- fixed HTML output for photo/video sharing messages (#33);
- fixed showing database statistics on information page;
- added message links to file transfers in chat statistics;
- add opened file name to application title;
- avoid "Broken pipe" errors if command-line output is piped and interrupted;
- command-line output encoded on all platforms, to avoid Unicode errors;
- avoid stack trace on command-line keyboard interrupt;
- stop worker threads instead of using daemons, to avoid zombie messages in CLI;
- command-line progress bar clears previously printed bar text;
- small UI tweaks;
- added __main__.py: pip-installed Skyperious can run as `python -m skyperious`;

3.3, 2015-03-15
------------------
- added per-contact word clouds to chat statistics;
- added 24h and date activity histograms to chat statistics;
- added support for bold, italic and strike-through formatting in Skype 7 (issue #31);
- fixed duplicate transfer rows in consecutive merges;
- added start-end editboxes for chat date filter;
- made contact avatar images in HTML export easily saveable;
- made database comparison progress-bar advance by message count instead of chat count;
- fixed creating duplicates in merge where contact names differ in databases;
- fixed parsing errors for certain Skype messages;
- fixed case-sensitive name sorting in chat statistics;
- fixed using Unicode command-line arguments;
- fixed possible wx error for shortcut keys when lots of windows open;
- changed skypename text colour in chat Excel export from transparent to gray;
- number of UI tweaks and fixes;
- made Pillow/PIL an optional requirement for both GUI and command-line (issue #28);
- made pyparsing optional;
- added setup.py script;
- upgraded Python from 2.7.6 to 2.7.9;
- upgraded wxPython from 3.0.0 to 3.0.2;
- upgraded dateutil from 2.2 to 2.4.1;
- upgraded Pillow from 2.3.0 to 2.7.0;
- upgraded pyparsing from 2.0.1 to 2.0.3;
- upgraded XlsxWriter from 0.5.3 to 0.6.7.

3.2, 2014-05-08
---------------
- added menu item to configure advanced options;
- added refresh button to database tables page;
- made chat and database export filenames configuration-based;
- fixed highlighting links in search results;
- fixed filename encoding problems under Linux with no locale (issue #18);
- fixed keeping export filename length in filesystem limit (issue #20);
- added scroll support to decrease required minimum window size (issue #21);
- added 24x24 icon for Linux system tray (issue #21);
- fixed database opening crash in PLD Linux (issue #23);
- fixed search results falsely highlighting negated query words;
- fixed errors on searching over tables in non-Skype databases;
- made entire application window a target for dragged-dropped files;
- update notification no longer shown when program minimized to tray;
- "Execute SQL" button in SQL window uses selected text, if any;
- word cloud text not longer includes wholly numeric words;
- dropped "Total time spent in calls" from chat statistics as duplicating "Calls";
- dropped alert messages on opening a non-Skype database;
- dropped alert messages on failing to open an export file;
- auto-added console history no longer saved on exit.

3.1, 2014-03-02
---------------
- fixed a bug in showing merge results;
- file arguments opened on start-up are added to database list;
- better Unicode support in command line interface;
- fixed command line progress bar display under Linux.

3.0, 2014-02-24
---------------
- added tray quick-search popup;
- added command-line interface, not requiring wxPython;
- database comparison now works in one direction;
- made database comparison run significantly faster;
- started using system theme colours;
- added option to merge only selected chats;
- added date selection links and initial limit to chat comparison view;
- added export option to chat comparison view;
- added filters to all chat and contact lists;
- added automatic update check option;
- added drag-drop reordering to database list;
- enlarged feedback screenshot from window to full screen;
- avatars in export now PNG instead of JPG;
- better handling for malformed databases;
- number of minor bugfixes and UI changes;
- added hotkeys Ctrl-F4 and Ctrl-W for closing a tab;
- changed console hotkey from Ctrl-W to Ctrl-E;
- moved packaging scripts to public repository;
- upgraded Python from 2.7.5 to 2.7.6;
- upgraded wxPython from 2.9.5 to 3.0.0;
- upgraded XlsxWriter from 0.4.8 to 0.5.3;
- upgraded dateutil from 1.5 to 2.2;
- upgraded NSIS from 2.4.6 to 3.0a2;
- made pyparsing a required library and dropped it from source.

2.3, 2013-11-17
---------------
- added Excel export;
- added option to export multiple chats to a single Excel workbook;
- added database corruption detection and recovery;
- added more statistics to database information page;
- fixed exporting from MSN Live accounts;
- fixed handling file transfer messages with unsupported filenames;
- fixed concurrency errors during merging (issue #11);
- improved emoticon parsing;
- improved Linux compatibility;
- a number of minor bugfixes and UI changes;
- increased error reporting;
- upgraded wxPython from 2.9.4 to 2.9.5;
- upgraded PyInstaller from 2.0 to 2.1;
- dropped BeautifulSoup dependency.

2.2, 2013-09-25
---------------
- fixed errors in exporting larger chats as HTML (issue #10);
- fixed an error in exporting selected database chats (issue #9);
- improved parsing exotic emoticons;
- made SQL editor auto-complete drop-down disappear on deleting text;
- tweak to disable dragging in database list;
- improved error reporting on export.

2.1.2, 2013-09-20
-----------------
- Fixed bugs on error reporting (issue #9);
- fixed an annoyance with SQL window auto-complete popup remaining on top of other windows;
- minor UI tweaks.

2.1.1, 2013-09-19
-----------------
- fixed a bug in merging large chats.

2.1, 2013-09-18
---------------
- support for exporting and comparing very large chats;
- fixed errors on selecting chat participants in chat history;
- fixed errors for chats with empty names;
- fixed data grids freezing if moving mouse over certain BLOB fields;
- added partner skypename to chat lists' People column for 1:1 chats;
- started remembering last active page in database tabs;
- improved exporting binary data as SQL from database tables;
- improved wxMac compatibility.

2.0, 2013-09-08
---------------
- added a Google-like query syntax to message search;
- redesigned application front page as a separate list and detail view;
- redesigned "Merge all" page, added progress bars, set as first in merge tab;
- fixed memory problems on comparing very large databases;
- added auto-complete and drop-down history to search;
- added option for searching over all database tables;
- added date:from..to keyword to search syntax;
- added option to exclude search results with -"dash in front";
- started remembering last search results on reopening database;
- set search as the first page in database tab;
- added welcome text and detailed search help to database tab;
- added message edited/removed flags to HTML export;
- started showing "/me" messages;
- started using * as a wildcard in search queries;
- highlighted wildcard matches in search results;
- added skypenames to repeating new contact names in merge results;
- added number of contact groups to merge results list;
- added recognizing PRAGMA and EXPLAIN queries in SQL window;
- fixed merging all file transfers;
- fixed showing "Removed X from this conversation" messages;
- started escaping SQLite wildcards % and _ in search;
- improved accessing corrupt SQLite databases;
- update check scheduled to run in the background;
- removed single instance functionality as unnecessary;
- improved message parsing;
- improved Linux and wx 2.8 compatibility;
- moved third-party libraries to separate directory.

1.5.1, 2013-06-21
-----------------
- fixed showing Facebook/MSN avatar images in chat HTML export;
- not showing author name for consecutive messages in chat HTML export;
- emoticon texts shown transparently over icon in chat HTML export;
- fixed message times in chat HTML/TXT export (was showing hour:second);
- improved message and emoticon parsing;
- fixed wrong items shown in file transfers under chat statistics;
- minor changes in UI layout and logic.

1.5, 2013-06-17
---------------
- animated emoticons in HTML export;
- highlight multiple word cloud items in HTML export;
- install option to associate Skyperious with *.db files;
- search results limit raised from 400 to 1000;
- SQL window last text reloaded on opening same database;
- option to hide log window;
- improved support for Python 2.6 + wx 2.8;
- dateutil and Skype4Py modules included optionally when running from source;
- fixed issues with formatting emoticons in older message texts;
- fixed opening corrupt SQLite databases;
- fixed word cloud calculation failing under certain odds;
- fixed bug with disabling multiple instances;
- moved source files under src/.

1.4, 2013-06-09
---------------
- added statistics and word cloud to chat HTML exports;
- added option to export selected chats only;
- added calls to chat statistics;
- added support for automatic updates;
- added possibility to send feedback;
- added option for automatic error reporting;
- statistics for chat text collected from text messages only;
- rearranged program menus;
- started using templates for generating content;
- updated license information for used and included software;
- upgraded BeautifulSoup from 3.2.0 to 3.2.1;
- updated 48x48 and 64x64 icons;
- multiple minor fixes and re-factorings.

1.3.2, 2013-04-28
-----------------
- updated support for wx 2.8 (issue #6);
- fixed a bug in comparing databases where messages have no author;
- fixed a bug in generating chat statistics for databases with exotic Unicode pathnames;
- fixed showing database labels with exotic Unicode pathnames in database comparison;
- fixed a problem where chat history could remain stuck in text selection mode after clicking a hyperlink;
- disabled "Merge selected contacts" buttons after swapping left-right databases.

1.3.1, 2013-04-14
-----------------
- fixed going from search results to a message in longer chat histories;
- removed shortcut keys from search options.

1.3, 2013-04-10
---------------
- added sorting options to statistics;
- search for all entered words instead of exact phrase;
- fixed opening databases with 1000+ conversations;
- fixed problems with search keyword order;
- middle button closes pages;
- better error handling on opening databases;
- fixed chat history showing wrong date range at the top.

1.2, 2013-03-27
---------------
- better search interface;
- option to search from specific chats and contacts;
- support for multiple tabs in search results;
- maximize chat button in chat page;
- changed icon;
- updated main notebook control to FlatNotebook;
- more toolbars in UI;
- rearranged tab order in database page;
- fixed a bug on opening a database with no account image;
- fixed showing contacts with no full name or display name;
- fixed a minor layout issue in chat statistics;
- fixed formatting very first search results;
- file drag-drop works on entire application window.

1.1, 2013-03-09
---------------
- added contacts import page and file info page;
- small changes in user interface and internal logic.

1.0, 2013-01-13
---------------
- added links like "Show: 30 days | 6 months | 2 years" etc to current chat history top;
- added percentages to chat statistics;
- started showing the chat filter panel from the start, in disabled state;
- added full message date-time as hovertext in HTML exports;
- made chat list ordering case-insensitive;
- small UI logic changes;
- started restoring previous window size and position on load;
- upgraded RangeSlider logic for single-selection range and disabled state;
- enlarged the search icon in the lower right corner of chat history;
- removed the wx.inspection tool;
- added 64-bit installer script.

0.10.7a, 2012-12-30
-------------------
- made whole application window target for file drop;
- added "Open a database.." button;
- made "Open selected" button to open all selected instead of first;
- added a confirmation to "Clear list" button;
- fixed a small logic error in menu items when toggling console;
- changed infotext slightly;
- created an installer package.

0.10.6a, 2012-11-20
-------------------
- handle defective avatar images;
- fix database list date sort;
- refresh database list columns after change;
- added participant count to chat list.

0.10.5a, 2012-11-01
-------------------
- a minor Unicode issue;
- updated binaries to using PyInstaller 2

0.10.4a, 2012-08-20
-------------------
- started showing "This message has been removed." for deleted messages.

0.10.3a, 2012-06-28
-------------------
- removed possible duplicate paths in database detection.

0.10.2a, 2012-06-22
-------------------
- fixed overwriting files in batch export for chats with identical names.

0.10.1a, 2012-06-18
-------------------
- added multiple database export functionality;
- tweaked export formatting.

0.10.0a, 2012-05-29
-------------------
- refactored application modules;
- made message decoding more robust.

0.9.8a, 2012-05-28
------------------
- added option to batch-export all database chats;
- fixed rare encoding errors in TXT export.

0.9.7a, 2012-04-30
------------------
- fixed problems when using an empty database;
- fixed inserting BLOB fields during merge.

0.9.6a, 2012-04-18
------------------
- fixed error messages on application exit under certain conditions;
- excluded conversations with no name from views and merging;
- changed results of diff scanning;
- cosmetic changes in code.

0.9.5a, 2012-04-17
------------------
- increased number of tries to access a Skype database after closing Skype;
- fixed some concurrency issues when using one database in multiple diffs;
- fixed releasing memory for closed pages.

0.9.4a, 2012-04-15
------------------
- added embedded favicons to HTML exports;
- added embedded application icon to precompiled exe;
- filenames assembled with os.path.join;
- converted images_to_py.py to using double quotation marks;
- started using Ultimate Packer for Executables;
- started sorting chat participants by name in lists.

0.9.3a, 2012-04-15
------------------
- first public release.
