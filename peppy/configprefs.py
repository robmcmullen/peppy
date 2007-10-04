# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Managing user config files and directories.
"""

import os, os.path, types
from ConfigParser import ConfigParser
import cPickle as pickle

import wx

from peppy.debug import *

class HomeConfigDir:
    """Simple loader for config files in the home directory.

    Wrapper around home directory files.  Load and save files or
    pickled objects in the home directory.
    """
    
    def __init__(self, dirname, create=True, debug=False):
        if dirname:
            self.dir = os.path.normpath(dirname)
        else:
            self.dir = wx.StandardPaths.Get().GetUserDataDir()
            
        if not self.exists():
            if create:
                try:
                    self.create()
                except:
                    d = wx.StandardPaths.Get().GetUserDataDir()
                    if d != self.dir:
                        self.dir = d
                        try:
                            self.create()
                        except:
                            eprint("Can't create configuration directory %s" % self.dir)
                            self.dir = None

    def create(self):
        try:
            os.mkdir(self.dir)
            return True
        except:
            return False

    def fullpath(self, name):
        return os.path.join(self.dir, name)

    def exists(self, name=None):
        if name is not None:
            d = self.fullpath(name)
        else:
            d = self.dir
        return os.path.exists(d)

    def open(self, name, mode='r'):
        path = self.fullpath(name)
        fd = open(path,mode)
        return fd

    def loadObject(self, name):
        item = None
        if self.exists(name):
            fd = self.open(name, 'rb')
            item = pickle.load(fd)
            fd.close()
        return item

    def saveObject(self, name, item):
        fd = self.open(name, 'wb')
        pickle.dump(item, fd)
        fd.close()


if __name__=='__main__':
    # Testing stuff that creates a directory in the user's homedir.
    # Don't perform this in the standard unit tests.

    def testHomeDir():
        print "for platform %s:" % os.sys.platform
        c=HomeConfigDir(".configprefs",debug=True)
        print "found home dir=%s" % c.dir
        fd=c.open("test.cfg",'w')
        fd.write('blah!!!')
        fd.close()
        nums=[0,1,2,4,6,99]
        c.saveObject("stuff.bin",nums)
        print c.loadObject("stuff.bin")
    
    testHomeDir()
