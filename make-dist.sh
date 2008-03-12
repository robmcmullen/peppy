#!/bin/bash

make distdir

distdir=`make print-distdir|cut -c11-`
echo $distdir
mv $distdir/peppy/hsi/hsi_major_mode_proxy.py $distdir/peppy/plugins
mv $distdir/peppy/hsi/hsi_major_mode.peppy-plugin $distdir/peppy/plugins

./make-py2exe-plugin-list.py -i $distdir -d peppy/plugins

cat > $distdir/py2exe.sh <<EOF
#!/bin/bash
python setup.py py2exe

# The following DLLs are needed for Vista support
cp c:/python25/lib/site-packages/wx-2.8-msw-unicode/wx/MSVCP71.dll dist
cp c:/python25/lib/site-packages/wx-2.8-msw-unicode/wx/gdiplus.dll dist

/program-files/NSIS/makensis win-installer.nsi
EOF
chmod 755 $distdir/py2exe.sh
