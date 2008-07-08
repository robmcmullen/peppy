#!/usr/bin/env python

import os, sys, glob
from cStringIO import StringIO
from optparse import OptionParser

import zlib

# crunch_data was removed from img2py as of wxPython 2.8.8
def crunch_data(data, compressed):
    # compress it?
    if compressed:
        data = zlib.compress(data, 9)

    # convert to a printable format, so it can be in a Python source file
    data = repr(data)

    # This next bit is borrowed from PIL.  It is used to wrap the text intelligently.
    fp = StringIO()
    data += " "  # buffer for the +1 test
    c = i = 0
    word = ""
    octdigits = "01234567"
    hexdigits = "0123456789abcdef"
    while i < len(data):
        if data[i] != "\\":
            word = data[i]
            i += 1
        else:
            if data[i+1] in octdigits:
                for n in xrange(2, 5):
                    if data[i+n] not in octdigits:
                        break
                word = data[i:i+n]
                i += n
            elif data[i+1] == 'x':
                for n in xrange(2, 5):
                    if data[i+n] not in hexdigits:
                        break
                word = data[i:i+n]
                i += n
            else:
                word = data[i:i+2]
                i += 2

        l = len(word)
        if c + l >= 78-1:
            fp.write("\\\n")
            c = 0
        fp.write(word)
        c += l

    # return the formatted compressed data
    return fp.getvalue()

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
