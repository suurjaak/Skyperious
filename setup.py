# -*- coding: utf-8 -*-
"""
Setup.py for Skyperious. 

------------------------------------------------------------------------------
This file is part of Skyperious - Skype chat history tool.
Released under the MIT License.

@author      Erki Suurjaak
@created     10.12.2014
@modified    26.03.2022
------------------------------------------------------------------------------
"""
import os
import sys
import setuptools

ROOTPATH  = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, os.path.join(ROOTPATH, "src"))

from skyperious import conf

setuptools.setup(
    name=conf.Title,
    version=conf.Version,
    description="Skype chat history tool",
    url="https://github.com/suurjaak/Skyperious",

    author="Erki Suurjaak",
    author_email="erki@lap.ee",
    license="MIT",
    platforms=["any"],
    keywords="skype sqlite merge export",

    install_requires=["appdirs", "beautifulsoup4", "ijson", "pyparsing", "Pillow",
                      "six", "SkPy", "wxPython>=4.0", "XlsxWriter"],
    entry_points={"gui_scripts": ["skyperious = skyperious.main:run"]},

    package_dir={"": "src"},
    packages=[conf.Title.lower()],
    include_package_data=True, # Use MANIFEST.in for data files
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
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
    ],

    long_description_content_type="text/markdown",
    long_description=
"""Skyperious is a Skype chat history tool, written in Python.

You can open Skype SQLite databases and work with their contents:

- import messages from Skype online service and Skype export archives
- search across all messages and contacts
- read chat history in full, see chat statistics and word clouds
- export chats as HTML, text or spreadsheet
- view any database table and export their data, fix database corruption
- change, add or delete data in any table
- execute direct SQL queries

and

- synchronize messages in two Skype databases, merging their differences
""",
)
