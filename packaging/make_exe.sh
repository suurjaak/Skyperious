# Goes through all .spec files in the directory and feeds them to PyInstaller,
# or selects files given in first argument.
#
# @author    Erki Suurjaak
# @created   03.09.2013
# @modified  28.02.2014
WILDCARD=*.spec
if [ "$1" ]; then
  WILDCARD="$1"
fi

for SPECFILE in $WILDCARD
do
  echo "Making EXE for $SPECFILE".
  pyinstaller "$SPECFILE"
  OUTFILE=$(ls dist | sort -n | head -1)
  if [ "$OUTFILE" ]; then
    OUTFILESIZE=$(stat --printf="%s" "dist/$OUTFILE")
    echo "Created $OUTFILE ($OUTFILESIZE bytes) for $SPECFILE"
    mv "dist/$OUTFILE" .
    rm -rf dist build > /dev/null
  fi
done
