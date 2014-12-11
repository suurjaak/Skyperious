# -*- coding: utf-8 -*-
"""
Setup.py for Skyperious. 

------------------------------------------------------------------------------
This file is part of Skyperious - a Skype database viewer and merger.
Released under the MIT License.

@author      Erki Suurjaak
@created     10.12.2014
@modified    11.12.2014
------------------------------------------------------------------------------
"""
import setuptools
import os
import sys

here = os.path.abspath(os.path.dirname(__file__))
os.chdir(here)
sys.path.append(os.path.join(here, "src"))

import conf

setuptools.setup(
    name=conf.Title,
    version=conf.Version,
    description="Skype SQLite database viewer, merger and exporter",
    url="https://github.com/suurjaak/Skyperious",

    author="Erki Suurjaak",
    author_email="erki@lap.ee",
    license="MIT",
    platforms=["any"],
    keywords="skype sqlite merge export",

    install_requires=["pyparsing", "XlsxWriter", "Pillow", "python-dateutil", "Skype4Py"],
    entry_points={"gui_scripts": ["skyperious=src.main:run"],
                  "console_scripts": ["skyperious-cli=src.main:run"]},

    packages=setuptools.find_packages(exclude=["dist", "res"]),
    data_files=[("res", [os.path.join("res", "Carlito.ttf"), 
                         os.path.join("res", "CarlitoBold.ttf")]), ],

    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: Unix",
        "Operating System :: MacOS",
        "Topic :: Communications :: Chat",
        "Topic :: Database",
        "Topic :: Utilities",
        "Topic :: Desktop Environment",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
    ],

    long_description=
"""You can open Skype SQLite databases and look at their contents:
- search across all messages and contacts
- browse chat history and export as HTML or spreadsheet, see chat statistics
- import contacts from a CSV file to your Skype contacts
- view any database table and export their data, fix database corruption
- change, add or delete data in any table
- execute direct SQL queries
and
- synchronize messages in two Skype databases: keep chat history up-to-date on
  different computers, or restore missing messages from older files into the
  current one""",
)
