#!/usr/bin/env python

import os, shutil, sys, glob
import __builtin__
from cStringIO import StringIO
from optparse import OptionParser

__builtin__._ = str

def entry(filename, out, copythese=None):
    print "Processing filename %s" % filename
    if filename.endswith(".py"):
        if copythese is not None:
            copythese.append(filename)
        if not filename.endswith("__init__.py") or True:
            module = filename[:-3].replace('/', '.').replace('\\', '.')
            out.write("import %s\n" % (module))

def process(path, out, copythese=None):
    files = glob.glob('%s/*' % path)
    for path in files:
        if os.path.isdir(path):
            process(path, out)
        else:
            entry(path, out, copythese)

def load_setuptools_plugins(entry_point_name):
    for entrypoint in pkg_resources.iter_entry_points(entry_point_name):
        plugin_class = entrypoint.load()
        print entrypoint.module_name
        print entrypoint, entrypoint.name, plugin_class
        print entrypoint.name

        # find the parent of the loaded module
        moduleparent, module = entrypoint.module_name.rsplit('.', 1)
        print moduleparent

        # import that module (which, since it's a module, imports
        # its __init__.py)
        m = __import__(moduleparent)
        print m.__file__

        # from its file, get the directory that contains the __init__.py
        path = os.path.dirname(m.__file__)
        print path

        # go up one directory
        path = os.path.dirname(path)
        print path

        os.chdir(path)
        copythese = []
        process(moduleparent, out, copythese)
        os.chdir(savepath)

        print copythese
        for py in copythese:
            source = os.path.join(path, py)
            dest = os.path.join(options.setuptools, py)
            try:
                os.makedirs(os.path.dirname(dest))
            except:
                pass
            shutil.copy(source, dest)
            print "cp %s %s" % (os.path.join(path, py),
                                os.path.join(options.setuptools, py))
    

if __name__ == "__main__":
    usage="usage: %prog [-s dir] [-o file]"
    parser=OptionParser(usage=usage)
    parser.add_option("-s", action="store", dest="setuptools",
                      default = "",
                      help="copy and include setuptools plugins")
    parser.add_option("-o", action="store", dest="output",
                      default="peppy/py2exe_plugins.py", help="output filename")
    (options, args) = parser.parse_args()

    out = StringIO()
    out.write("# Automatically generated, and only used when creating a py2exe distribution\n")

    os.chdir('peppy')
    process('plugins', out)
    # Need to force the importing of the editra style definition files
    process('editra/syntax', out)
    os.chdir('..')

    savepath = os.getcwd()

    if options.setuptools:
        try:
            import pkg_resources
            load_setuptools_plugins('peppy.plugins')
            load_setuptools_plugins('peppy.hsi.plugins')
        except:
            raise

    os.chdir(savepath)

    fh = open(options.output, 'w')
    fh.write(out.getvalue())
