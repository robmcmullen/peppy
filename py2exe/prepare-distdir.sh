#!/bin/bash
#
# Modify the distdir in preparation for a py2exe

# First, verify that we are being called in the root directory, not the py2exe
# directory.

if [ ! -f setup.py ]
then
    cd ..
    if [ ! -f setup.py ]
    then
        echo "Must be called from inside root peppy directory"
        exit 1
    fi
fi
echo "Found working directory $PWD"

# Don't run this on the version control directory; only run this on a directory
# that has a version number -- i.e. one that has been created by 'make distdir'

if [ -d .git -o -d .svn -o -d .peppy-project -o -d i18n.in ]
then
    echo
    echo "ERROR!  Don't call this from a version that you are editing!"
    echo "This is designed to modify an unzipped source distribution in place"
    echo "to create the directory structure needed to build a one-off py2exe"
    echo "installer."
    exit 2
fi

mv peppy/hsi/hsi_plugin.py peppy/plugins
mv peppy/hsi/hsi_plugin.peppy-plugin peppy/plugins
mv peppy/project/project_plugin.py peppy/plugins
mv peppy/project/project_plugin.peppy-plugin peppy/plugins

# Create the eggs directory that will be used to store plugins
mkdir eggs
touch eggs/__init__.py

# Unzip the platform independent eggs
ls -1 peppy/plugins/eggs/*py2.5.egg | while read EGG; do
    unzip -o $EGG -d eggs
done

# add the platform independent eggs to the py2exe include list
./py2exe/prepare-plugin-list.py -i . -d peppy/major_modes -d peppy/plugins -e eggs

# Handle eggs with compiled objects.  They don't seem to do well when placed in
# the eggs directory -- they need to be in the top level directory
ls -1 peppy/plugins/eggs/*win32.egg | while read EGG; do
    unzip -o $EGG
    cat EGG-INFO/top_level.txt | while read TOPLEVEL; do
        echo "import $TOPLEVEL" >> peppy/py2exe_plugins.py
    done
done
rm peppy/plugins/eggs/*.egg
