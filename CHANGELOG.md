CHANGELOG
=========


5.0, 2022-03-26
---------------
- full Python2 / Python3 compatibility;
- move to src-layout;
- fixed error on opening chat with linefeeds in participant name (issue #103);
- ensure database has required tables and fields before starting live sync (issue #106).


4.8.1, 2021-08-05
---------------
- fixed audio/video messages imported from live as simple file transfers (issue #102).


4.8, 2021-08-01
---------------
- added shared files download for HTML export with subfolder;
- fixed chats not being shown on importing Skype export (issue #100);
- fixed export on Linux not using selected format (issue #101);
- fixed certain save-dialog overwrite prompts not working on Linux;
- fixed feedback screenshot not updating on Linux;
- fixed help texts in advanced options dialog showing ampersands as accelerators;
- show selection of chats to sync on online-page in case-insensitive order;
- upgraded ijson from 3.1.3 to 3.1.4;
- upgraded skpy from 0.10.2 to 0.10.4;
- upgraded XlsxWriter from 1.3.7 to 1.4.5.


4.7, 2021-03-15
---------------
- added command-line flag --no-terminal (issue #97);
- improved detecting existing messages during online sync;
- improved querying Skype online service for more messages to sync (issue #93);
- fixed data grid export ignoring current filter;
- fixed parsing parts of HTML entities into emoticons;
- fixed command-line create overwriting existing file, and not creating file if password not given.


4.6, 2021-03-04
---------------
- update existing contact information in database on live sync;
- added flag to not update contact information in database from live;
- sync older chats from live not just recent ones (issue #93);
- added flag to not sync older chats from live;
- show `<pre>`-tag content in chat reader;
- show @-taggings in chat reader and style them bold in reader and HTML;
- ask for confirmation when exporting HTML with media in subfolder, but login unavailable for downloading media (issue #93);
- fixed error on creating chat date links during the month of March;
- fixed "Go to previous [period]" not working in chat history if history starts with previous period;
- fixed merge not showing correct diff in individual chats view;
- fixed duplicates in syncing bot contacts and messages from live (issue #93);
- fixed not retaining the order of command-line FILE arguments (issue #93);
- fixed displaying shared media with duplicate filenames in HTML export with subfolder (issue #93);
- add detected media type extension to shared media exported in HTML if lacking one (issue #93).


4.5, 2021-02-06
---------------
- added option to change Skype online account username;
- added option to delete chats from the database;
- improved detection of duplicate messages on merging (issue #93);
- fixed new contacts not being inserted on merge (issue #93);
- fixed inserting duplicate chats on command-line merge with 2+ databases (issue #93).


4.4, 2021-01-18
---------------
- added support for shared audio & video in HTML export;
- import chats and contacts from Skype online only if they have messages (issue #89).
- fixed loading and saving user-specific configuration file (issue #90);
- fixed handling unexpected data on importing Skype export (issue #92);
- fixed not focusing search result message in chat history on first click;
- fixed issues on Linux with wxPython 4.1.1;
- upgraded beautifulsoup4 from 4.9.1 to 4.9.3;
- upgraded ijson from 3.1 to 3.1.3;
- upgraded skpy from 0.10 to 0.10.2;
- upgraded XlsxWriter from 1.2.9 to 1.3.7.


4.3.1, 2020-10-04
-----------------
- fixed export errors (issue #86).


4.3, 2020-09-22
---------------
- added dark mode toggle to HTML export (issue #81);
- added support for single-user install.


4.2, 2020-08-29
---------------
- added option to create a blank Skype database;
- added option to create a database from Skype export;
- added option to export HTML with shared images in subfolder;
- added chat history timeline for time period quick-selection;
- added option to go to next/previous message from author in chat history;
- added option to go to next/previous day/week/month in chat history;
- added option to filter chat history by day/week/month/year of clicked message;
- added option to scroll back more messages in chat history;
- added calendar popup to chat time period filter;
- import account/contact gender, homepage and e-mails from live sync;
- improved message parsing from Skype live and export;
- upgraded skpy from 0.9.1 to 0.10;
- dropped dateutil dependency;
- dropped Vagrant support.


4.1, 2020-08-03
---------------
- added option to merge from Skype chat history export;
- added option to rename chats and contacts;
- added option to delete database;
- use OS- and user-specific config and data directories where necessary;
- improved error handling and reporting.


4.0.1, 2020-07-30
-----------------
- fixed live sync failing on unexpected errors.


4.0, 2020-07-29
---------------
- added support for syncing chat history from Skype online service;
- added 400+ more emoticon images;
- added date range option to chat export;
- restored shared image download functionality;
- restored support functionality;
- made database list sortable and filterable, added date and size columns;
- increased default font size for chat history, made it configurable;
- updated emoticon parsing;
- removed obsolescence notice.


3.6, 2020-07-06
---------------
- marked program as obsolete;
- dropped support functionality;
- dropped contacts search and import functionality as unavailable;
- dropped shared image download functionality as unavailable;
- fixed some remaining stability issues;
- upgraded wxPython to v4.


3.5.1c, 2015-12-21
---------------
- added support for updated Skype chat structure (issue #40);
- added "Remove by type" button to start page (issue #47);
- fixed escaping bolded words in search chat title and participants link;
- fixed command-line interface requiring wx (issue #45);
- fixed potential error message on long sessions;
- added "Send feedback" button to About-box;
- added --version flag to command-line interface.


3.5, 2015-07-16
---------------
- added emoticons to chat statistics;
- added shared image download for HTML export;
- added chat and author filters to command-line export;
- applying or resetting message filter will scroll to last selection;
- added support for copying selected list items to clipboard;
- stopped caching messages on export to avoid memory shortage;
- fixed parsing messages with deeply nested HTML (issue #38);
- fixed chat date range component error when switching to empty chat;
- fixed a potential error with unexpected data in quoted messages;
- fixed a potential error message on filtering chat messages;
- made database comparison report window retain scroll position at the bottom;
- increased size of message search bar button image;
- upgraded Python from 2.7.9 to 2.7.10;
- upgraded dateutil from 2.4.1 to 2.4.2;
- upgraded Pillow from 2.8.0 to 2.8.1;
- upgraded SQLite from 3.6.21 to 3.8.10.2 (issue #39);
- upgraded XlsxWriter from 0.6.7 to 0.7.3;
- upgraded Nullsoft Scriptable Install System from 3.0a2 to 3.0b1;


3.4.1, 2015-04-29
-----------------
- fixed missing content in text/Excel/CSV export (issue #37);
- rolled back using Skype account timezone setting for message timestamps (issue #33);
- added 40x40 and 256x256 application icons;
- minor UI tweak: added focus-on-click to Advanced Options dialog labels;


3.4, 2015-04-15
---------------
- added links to earliest messages in chat statistics histogram sectors;
- fixed showing wrong author in transfer statistics for certain messages;
- fixed a parsing issue with certain Skype messages;
- fixed HTML output for photo/video sharing messages (issue #33);
- fixed getting encoding errors on Excel export;
- fixed potential error on chat date histogram analysis;
- fixed showing database statistics on information page;
- use Skype account timezone setting for message timestamps;
- added message links to file transfers in chat statistics;
- added table links to result sections in searching over tables;
- optimized memory usage in chat word-cloud analysis (issue #35);
- added opened file name to application title;
- avoid "Broken pipe" errors if command-line output is piped and interrupted;
- fixed error on opening databases with invalid SkypeOut values in account (issue #35);
- fixed possible invalid HTML in export;
- command-line output encoded on all platforms, to avoid Unicode errors;
- avoid stack trace on command-line keyboard interrupt;
- stop worker threads instead of using daemons, to avoid zombie messages in CLI;
- command-line progress bar clears previously printed bar text;
- small UI tweaks;
- added __main__.py: pip-installed Skyperious can run as `python -m skyperious`;
- upgraded Pillow from 2.7.0 to 2.8.0.

3.3, 2015-03-15
---------------
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
