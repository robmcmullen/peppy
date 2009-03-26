# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""STC interface for accessing data in hyperspectral cubes

Hyperspectral images are very large and need a special implementation of the
STC interface to prevent the entire cube from being loaded into memory at once.
"""

import os, sys, re, glob

import peppy.vfs as vfs

from peppy.debug import *
from peppy.stcinterface import *

from peppy.hsi.loader import *


class HyperspectralSTC(NonResidentSTC, debugmixin):
    """Combination of STC and proxy for a hyperspectral dataset"""
    
    def open(self, buffer, message=None):
        self.url = buffer.raw_url
        self.message = message
        self.dprint("Loading %s" % str(self.url))
        self.dataset = HyperspectralFileFormat.load(self.url, progress=self.updateGauge)

    def updateGauge(self, current, length=-1):
        # Delay importing pubsub until here so that loader can be used without
        # wx installed.
        import wx.lib.pubsub
        dprint(current)
        if length < 0:
            wx.lib.pubsub.Publisher().sendMessage(self.message, -1)
        else:
            wx.lib.pubsub.Publisher().sendMessage(self.message, (current*100)/length)

    def CanSave(self):
        return False
    
    def getShortDisplayName(self, url):
        """Return a short name for display in tabs or other context without
        needing a pathname.
        """
        if url.fragment:
            return "%s#%s" % (url.path.get_name(), url.fragment)
        return url.path.get_name()

    def getHandler(self):
        return self.dataset.__class__
    
    def getNumCubes(self):
        return self.dataset.getNumCubes()
    
    def getCube(self, url=None, index=0, progress=None, options=None):
        try:
            return self.dataset.getCube(filename=url, index=index, progress=progress, options=options)
        except OSError:
            # WindowsError here means that we couldn't memmap the file
            # (although we can't actually specify WindowsError here because
            # it's not cross-platform.  Use OSError instead, which is the
            # superclass of WindowsError).  Try to load the file using another
            # loader (for example, instead of ENVI, use GDAL)
            dprint("Caught what is most likely an out-of-memory error.  Trying to load with a different handler")
            dataset = HyperspectralFileFormat.load(self.url, bad=self.dataset.__class__)
            if dataset:
                #dprint("Using %s instead" % dataset.__class__)
                self.dataset = dataset
                return self.dataset.getCube(filename=url, index=index, progress=progress, options=options)
            dprint("Caught OSError; most likely out-of-memory error due to mmap.  Alternate loaders failed.")
            raise
    
    def GetLength(self):
        return vfs.get_size(self.url)
        
    def Destroy(self):
        self.dataset = None
