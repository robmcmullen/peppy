#!/usr/bin/env python

import os, shutil, sys, glob, imp
import __builtin__
from cStringIO import StringIO
from optparse import OptionParser

__builtin__._ = str

plugin_count = 0

lastfake = False

def entry(filename, out=None, copythese=None, fake=False, pyc=False, remove_prefix=None):
    print "Processing filename %s" % filename
    file_root, ext = os.path.splitext(filename)
    if ext in [".py", ".so", ".pyd"] and 'EGG-INFO' not in filename:
        if copythese is not None and not fake:
            copythese.append(filename)
        if not filename.endswith("__init__.py"):
            if remove_prefix and file_root.startswith(remove_prefix):
                file_root = file_root[len(remove_prefix):]
            module = file_root.replace('/', '.').replace('\\', '.')
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
                    out.write("try:\n    import %s\nexcept:\n    print('error importing %s')\n    import traceback\n    error = traceback.format_exc()\n    print(error)\n" % (module, module))

def process(path, out=None, copythese=None, fake=False, pyc=False, remove_prefix=None):
    files = glob.glob('%s/*' % path)
    for path in files:
        if os.path.isdir(path):
            process(path, out, fake=fake, pyc=pyc, remove_prefix=remove_prefix)
        else:
            entry(path, out, copythese, fake, pyc, remove_prefix=remove_prefix)

def processModuleListFromFile(filename, out=None, copythese=None, fake=False, pyc=False, remove_prefix=None):
    fh = open(filename)
    for line in fh:
        path = line.strip()
        entry(path, out, copythese, fake, pyc, remove_prefix=remove_prefix)

def process_modules(module_name, out=None):
    file, pathname, desc = imp.find_module(module_name)
    print(pathname)
    if pathname.endswith(module_name):
        prefix = pathname[:-len(module_name)]
        print(prefix)
    else:
        prefix = None
    print(desc)
    files = glob.glob('%s/*' % pathname)
    for path in files:
        if os.path.isdir(path):
            process(path, out, remove_prefix=prefix)
        else:
            entry(path, out, remove_prefix=prefix)

if __name__ == "__main__":
    usage="usage: %prog [-s dir] [-o file]"
    parser=OptionParser(usage=usage)
    parser.add_option("-i", action="store", dest="input",
                      default="", help="base input directory")
    parser.add_option("-d", action="append", dest="importdir",
                      default=[], help="import directory within base directory")
    parser.add_option("-o", action="store", dest="output",
                      default="peppy/py2exe_plugins.py", help="output filename")
    parser.add_option("-e", action="store", dest="eggs",
                      default="", help="process unpacked eggs")
    parser.add_option("-t", action="store", dest="toplevel",
                      default="", help="list of toplevel modules from file")
    parser.add_option("-m", action="append", dest="modules",
                      default=[], help="process global modules")
    parser.add_option("--alternate-include-path", action="store",
                      dest="include_path", default="", help="additional include path to search for modules if not found in system include path")
    (options, args) = parser.parse_args()

    out = StringIO()
    out.write("# Automatically generated, and only used when creating a py2exe distribution\n")

    os.chdir(options.input)
    savepath = os.getcwd()

    for importdir in options.importdir:
        destdir = os.path.join(savepath, importdir)
        print destdir
        process(importdir, out)
    # Need to fake the importing of all the library modules and the editra style
    # definition files so py2exe will include them
    process('peppy/lib', out, fake=True)
    process('peppy/editra/syntax', out, fake=True)
    
    if options.eggs:
        process(options.eggs, out, pyc=True)
    
    if options.toplevel:
        processModuleListFromFile(options.toplevel, out, pyc=True)
    
    if options.modules:
        for module in options.modules:
            try:
                process_modules(module, out)
            except ImportError:
                sys.path.append(options.include_path)
                process_modules(module, out)

    filename = os.path.join(savepath, options.output)
    fh = open(filename, 'w')
    fh.write("import wx\napp = wx.GetApp()\n")
    fh.write(out.getvalue())
    fh.close()
    
    countname = filename.replace(".py", "_count.py")
    fh = open(countname, 'w')
    fh.write("count = %d\n" % plugin_count)
    fh.close()
