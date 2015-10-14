#!/bin/sh
SUPPRESS="Gtk-WARNING|Gtk-CRITICAL|GLib-GObject-WARNING"
file=$(readlink -f "$0")
dir=$(dirname "$file")
exec python $dir/skyperious/main.py "$@" 2>&1 | tr -d '\r' | grep -v -E "$SUPPRESS"
