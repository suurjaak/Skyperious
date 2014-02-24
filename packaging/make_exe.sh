# Goes through all .spec files in the directory and feeds them to PyInstaller,
# or selects files given in first argument.
#
# @author    Erki Suurjaak
# @created   03.09.2013
# @modified  03.09.2013
PYINSTALLERDIR=/home/user/src/pyinstaller
WILDCARD=*.spec
if [ "$1" ]; then
  WILDCARD="$1"
fi

if [ -f "makeexe.log" ]; then rm "makeexe.log"; fi

for SPECFILE in $WILDCARD
do
  echo "Making EXE for $SPECFILE".
  python "$PYINSTALLERDIR/pyinstaller.py" "$SPECFILE" >> "makeexe.log" 2>&1
  OUTFILE=$(ls "dist/" | sort -n | head -1)
  if [ "$OUTFILE" ]; then
    OUTFILESIZE=$(stat --printf="%s" "dist/$OUTFILE")
    echo "Found $OUTFILE ($OUTFILESIZE bytes) for $SPECFILE".
    mv "dist/$OUTFILE" .
    rm -rf "dist"
    rm "makeexe.log"
    if [ -f logdict*.final.*.log ]; then rm logdict*.final.*.log; fi
    #rm -rf build
  else
    echo "No new EXE found for $SPECFILE, check makeexe.log for errors".
  fi
done
