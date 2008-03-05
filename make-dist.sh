#!/bin/bash

make distdir

distdir=`make print-distdir|cut -c11-`
echo $distdir
mkdir -p $distdir/peppy/builtins
mv $distdir/peppy/plugins/* $distdir/peppy/builtins
mv $distdir/peppy/hsi/hsi_major_mode_proxy.py $distdir/peppy/builtins
rm $distdir/peppy/hsi/hsi_major_mode.peppy-plugin
rmdir $distdir/peppy/plugins

./make-py2exe-plugin-list.py -i $distdir/peppy -d builtins

cat > $distdir/py2exe.sh <<EOF
#!/bin/bash
python setup.py py2exe

# The following DLLs are needed for Vista support
cp c:/python25/lib/site-packages/wx-2.8-msw-unicode/wx/MSVCP71.dll dist
cp c:/python25/lib/site-packages/wx-2.8-msw-unicode/wx/gdiplus.dll dist

/program-files/NSIS/makensis win-installer.nsi
EOF
chmod 755 $distdir/py2exe.sh

# Have to add these packages explicitly here, otherwise it tries to
# pull packages from site-packages and won't look in the peppy
# directory even if the packages exist.
chpat.pl "'peppy.plugins', 'peppy.plugins.games'" "'peppy.builtins', 'peppy.builtins.games'" $distdir/setup.py
rm $distdir/setup.py.orig
