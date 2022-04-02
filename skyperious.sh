#!/bin/bash
cd src && exec >/dev/null 2>&1 python3 -m skyperious "$@"
