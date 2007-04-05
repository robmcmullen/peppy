#!/usr/bin/env python

import os,sys,re,os.path,time
from optparse import OptionParser


def directory(verbose=False):
    files = []

    # find packages to be installed
    path = os.getcwd()
    if verbose: print path
    check = os.path.join('.svn','text-base')
    def addsvn(arg, dirname, names):
        if verbose: print "checking %s" % (dirname)
        if dirname.find(check)>0:
            dirname = dirname.replace(check, '')[len(path)+1:]
            for name in names:
                if name.find('.svn-base')>0:
                    actualname = name.replace('.svn-base', '')
                    if verbose: print "found %s" % actualname
                    files.append(os.path.join(dirname, actualname))
    os.path.walk(path, addsvn, None)

    filelist = (" ".join(files)).replace(os.sep, '/')
    print filelist
    
if __name__=='__main__':
    usage="usage: %prog"
    parser=OptionParser(usage=usage)
    (options, args) = parser.parse_args()

    directory()
    
