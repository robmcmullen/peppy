#!/usr/bin/env python

import os, shutil, sys, glob
import __builtin__
from cStringIO import StringIO
from optparse import OptionParser

__builtin__._ = str

plugin_count = 0

lastfake = False

def entry(filename, out=None, copythese=None, fake=False, pyc=False):
    print "Processing filename %s" % filename
    if filename.endswith(".py") and 'EGG-INFO' not in filename:
        if copythese is not None and not fake:
            copythese.append(filename)
        if not filename.endswith("__init__.py"):
            module = filename[:-3].replace('/', '.').replace('\\', '.')
            if out:
                if fake:
                    global lastfake
                    if not lastfake:
                        out.write("if False: # fake the import so py2exe will include the file\n")
                        lastfake = True
                    out.write("    import %s\n" % (module))
                else:
                    global lastfake
                    lastfake = False
                    global plugin_count
                    name = module.split('.')[-1]
                    
                    # Don't print any __init__ modules in the splash screen
                    if name != "__init__":
                        plugin_count += 1
                        out.write("app.gaugeCallback('%s')\n" % name)
                    print "importing %s" % module
                    out.write("try:\n    import %s\nexcept:\n    pass\n" % (module))

def process(path, out=None, copythese=None, fake=False, pyc=False):
    files = glob.glob('%s/*' % path)
    for path in files:
        if os.path.isdir(path):
            process(path, out, fake=fake, pyc=pyc)
        else:
            entry(path, out, copythese, fake, pyc)

if __name__ == "__main__":
    usage="usage: %prog [-s dir] [-o file]"
    parser=OptionParser(usage=usage)
    parser.add_option("-i", action="store", dest="input",
                      default="peppy", help="base input directory")
    parser.add_option("-d", action="store", dest="importdir",
                      default="builtins", help="import directory within base directory")
    parser.add_option("-o", action="store", dest="output",
                      default="peppy/py2exe_plugins.py", help="output filename")
    parser.add_option("-e", action="store", dest="eggs",
                      default="", help="process unpacked eggs")
    (options, args) = parser.parse_args()

    out = StringIO()
    out.write("# Automatically generated, and only used when creating a py2exe distribution\n")

    os.chdir(options.input)
    savepath = os.getcwd()
    destdir = os.path.join(savepath, options.importdir)
    print destdir

    process(options.importdir, out)
    # Need to fake the importing of all the library modules and the editra style
    # definition files so py2exe will include them
    process('peppy/lib', out, fake=True)
    process('peppy/editra/syntax', out, fake=True)
    
    if options.eggs:
        process(options.eggs, out, pyc=True)

    filename = os.path.join(savepath, options.output)
    fh = open(filename, 'w')
    fh.write("import wx\napp = wx.GetApp()\n")
    fh.write(out.getvalue())
    fh.close()
    
    countname = filename.replace(".py", "_count.py")
    fh = open(countname, 'w')
    fh.write("count = %d\n" % plugin_count)
    fh.close()
