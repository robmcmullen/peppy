#!/bin/bash

# Windows can't seem to use the VirtualBox shared drive when sshing into it,
# so the calling script on the unix side must have performed an rsync to get a
# copy of the build environment onto the VirtualBox home directory.
cd ~/peppy

# Need to convert end of line characters to unix style instead of CR LF
VERSION=`python make-changelog.py  --version| sed s/\r//g`
echo $VERSION

# creates source distribution in ~/peppy/peppy-$VERSION
bash make-dist.sh
echo $PWD
cd peppy-$VERSION

# Creates peppy-$VERSION-win32.exe in ~/peppy/peppy-$VERSION/py2exe directory
bash py2exe.sh
