#!/usr/bin/env python

import os, sys, glob
from cStringIO import StringIO
from optparse import OptionParser

from wx.tools.img2py import *

def gen(filename):
    fh = open(filename, 'rb')
    data = fh.read()
    printable = crunch_data(data, False)
    return printable

def entry(filename, out):
    if filename.endswith('.py') or filename.endswith('.pyc'):
        return
    data = gen(filename)
    # Change all windows backslashes to forward slashes
    filename = filename.replace('\\', '/')
    out.write("'%s':\n%s,\n" % (filename, data))

def process(path, out):
    files = glob.glob('%s/*' % path)
    for path in files:
        if os.path.isdir(path):
            process(path, out)
        else:
            entry(path, out)

if __name__ == "__main__":
    usage="usage: %prog [-o file]"
    parser=OptionParser(usage=usage)
    parser.add_option("-o", action="store", dest="output",
                      default="peppy/iconmap.py", help="output filename")
    (options, args) = parser.parse_args()

    out = StringIO()
    out.write("""\
from peppy.lib.iconstorage import *

icondict = {
""")
    os.chdir('peppy')
    process('icons', out)
    out.write("""\
}

addIconsFromDict(icondict)
""")
    os.chdir('..')

    fh = open(options.output, 'w')
    fh.write(out.getvalue())
