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

mv $distdir/eggs/*win32.egg $distdir

# Unzip them into the eggs directory so we can search for plugins
touch $distdir/eggs/__init__.py
ls -1 $distdir/eggs/*.egg | while read EGG; do
    unzip -o $EGG -d $distdir/eggs
done

./make-py2exe-plugin-list.py -i $distdir -d peppy/plugins -e eggs

# Handle eggs with compiled objects.  They don't seem to do well when placed in
# the eggs directory -- they need to be in the top level directory
ls -1 $distdir/*win32.egg | while read EGG; do
    unzip -o $EGG -d $distdir
    cat $distdir/EGG-INFO/top_level.txt | while read TOPLEVEL; do
        echo "import $TOPLEVEL" >> $distdir/peppy/py2exe_plugins.py
    done
done

cat > $distdir/py2exe.sh <<EOF
#!/bin/bash
python setup.py py2exe

# The following DLLs are needed for Vista support
cp c:/python25/lib/site-packages/wx-2.8-msw-unicode/wx/MSVCP71.dll dist
cp c:/python25/lib/site-packages/wx-2.8-msw-unicode/wx/gdiplus.dll dist

/program-files/NSIS/makensis win-installer.nsi
EOF
chmod 755 $distdir/py2exe.sh
