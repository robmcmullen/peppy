#!/bin/bash

# Make distribution in preparation for creating a py2exe executable

make distdir

distdir=`make print-distdir|cut -c11-`
echo $distdir
mv $distdir/peppy/hsi/hsi_major_mode_proxy.py $distdir/peppy/plugins
mv $distdir/peppy/hsi/hsi_major_mode.peppy-plugin $distdir/peppy/plugins

# Create the eggs that are normally used for standalone plugins, but include
# the source
mkdir $distdir/eggs
./plugins/egg-utils.py -d $distdir/eggs -k egg

# prevent duplicate plugins -- if plugins dir exists, they will also be pulled
# from there.  Had a problem with rm -rf in a script once, so just rename it. :)
mv $distdir/plugins $distdir/plugins-src

# Unzip them into the eggs directory so we can search for plugins
touch $distdir/eggs/__init__.py
ls -1 $distdir/eggs/*.egg | while read EGG; do
    unzip -o $EGG -d $distdir/eggs
done

./make-py2exe-plugin-list.py -i $distdir -d peppy/plugins -e eggs

cat > $distdir/py2exe.sh <<EOF
#!/bin/bash
python setup.py py2exe

# The following DLLs are needed for Vista support
cp c:/python25/lib/site-packages/wx-2.8-msw-unicode/wx/MSVCP71.dll dist
cp c:/python25/lib/site-packages/wx-2.8-msw-unicode/wx/gdiplus.dll dist

/program-files/NSIS/makensis win-installer.nsi
EOF
chmod 755 $distdir/py2exe.sh
