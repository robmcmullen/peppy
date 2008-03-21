#!/usr/bin/env python

import os, sys, glob
from optparse import OptionParser


def process(path, destdir, cmd):
    if os.path.isfile(os.path.join(path, "setup.py")):
        print("processing %s in %s with %s" % (path, destdir, cmd))
        os.chdir(path)
        args = cmd % destdir
        run = "python setup.py %s" % args
        print(run)
        os.system(run)
    else:
        print("skipping non-plugin dir %s" % path)

if __name__ == "__main__":
    usage="usage: %prog [-d dir] [develop|egg]"
    parser=OptionParser(usage=usage)
    parser.add_option("-d", action="store", dest="destdir", default="", help="destination directory for egg")
    (options, args) = parser.parse_args()

    if args[0].startswith('d'):
        cmd = "develop --install-dir %s"
    elif args[0].startswith('e'):
        cmd = "bdist_egg --exclude-source-files -d %s"
    else:
        parser.print_usage()
    
    topdir = os.path.abspath(os.path.dirname(__file__))
    print topdir
    if not topdir:
        topdir = os.getcwd()
    # Put the plugin directory in the environment so that setuptools won't barf
    # when placing the eggs into a non-syntem directory
    os.environ['PYTHONPATH'] = topdir

    if options.destdir:
        destdir = os.path.abspath(options.destdir)
    else:
        destdir = topdir

    dirs = os.listdir(topdir)
    for d in dirs:
        os.chdir(topdir)
        if os.path.isdir(d):
            print("\n-----")
            process(os.path.join(topdir, d), destdir, cmd)
