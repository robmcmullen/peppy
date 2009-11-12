#!/bin/bash

# Designed to be called from an ssh session.  An argument must be passed to the
# script indicating the root of the compressed archive.


ROOT=$1

if [ ! -f $ROOT.tar.* ]
then
    echo "Source archive for $ROOT doesn't exist.  Not building."
    exit -1
fi

if rm -rf $ROOT
then
    :
else
    echo "Failed removing $ROOT.  Someone using that directory?"
    exit -1
fi 

bzcat $ROOT.* | tar xf -
cd $ROOT
bash py2exe/prepare-distdir.sh
bash py2exe/build-py2exe.sh
