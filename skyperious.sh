#!/bin/bash
cd $(dirname "${BASH_SOURCE[0]}")/src
exec >/dev/null 2>&1 python3 -m skyperious "$@"
