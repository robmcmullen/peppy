# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Managing user config files and directories.
"""

import os, os.path, types
from ConfigParser import ConfigParser
import cPickle as pickle

import wx

from trac.core import *
from debug import *

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
                            print "Can't create configuration directory"
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


## Configuration extender interface for hooking into the load/save
## configuration file process

class IConfigurationExtender(Interface):
    """Interface to add new configuration options to the application.

    Implement L{loadConf} to add to the configuration settings before
    the first frame appears.  Could also be used to load additional
    settings not in the main configuration file.

    Implement L{saveConf} to adjust configuration settings before any
    are saved.  Could also be used to save additional settings not in
    the main configuration file.
    """

    def loadConf(app):
        """Load some configuration settings, possibly from an external
        source like a file.

        This is called after the application has loaded all the
        plugins and the main configuration file.
        """

    def saveConf(app):
        """Save configuration settings, possibly to an external file.

        This is called before the main configuration file is written,
        so additions to it are possible.
        """

class ConfigurationExtender(Component):
    """ExtensionPoint that loads L{IConfigurationExtenders}.

    Driver class that is used to call all the registered
    IConfigurationExtenders during application init and shutdown.
    """
    extensions=ExtensionPoint(IConfigurationExtender)

    def load(self,app):
        for ext in self.extensions:
            ext.loadConf(app)

    def save(self,app):
        for ext in self.extensions:
            ext.saveConf(app)


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
