#!/bin/bash

# Find the version number
VERSION=`python make-changelog.py  --version`
echo $VERSION

# Make the source distribution of peppy
PEPPYSRC=peppy-$VERSION.tar.bz2
if [ -f archive/$PEPPYSRC ]
then
    echo FOUND $PEPPYSRC
else
    make dist
    mv $PEPPYSRC archive
fi


# Make the windows executable version of peppy.  For some unknown reason, when
# sshing into the virtual machine, the Z: drive is not available.  So, instead
# of building in place, I have to rsync the current source onto the C: drive
# and perform the build there.

# Virtual machine name
VM="Work VM"

RUNNING=`VBoxManage showvminfo "$VM"|grep State:`
echo $RUNNING
case $RUNNING in
    *running*)
    ;;
    
    *paused*)
    VBoxManage controlvm "$VM" resume
    ;;
    
    *)
    echo Virtual machine $VM must be running.
    exit 1
    ;;
esac

PEPPYWIN=peppy-$VERSION-win32.exe
if [ -f archive/$PEPPYWIN ]
then
    echo FOUND $PEPPYWIN
else
    scp -P 2222 archive/$PEPPYSRC py2exe/build-over-ssh.sh localhost:
    ssh -p 2222 localhost bash build-over-ssh.sh peppy-$VERSION
    scp -P 2222 localhost:peppy-$VERSION/py2exe/$PEPPYWIN archive
fi
