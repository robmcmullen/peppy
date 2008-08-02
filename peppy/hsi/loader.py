# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Reading and writing raw HSI cubes.

This class supports reading HSI data cubes (that are stored in raw,
uncompressed formats) using memory mapped file access.
"""

import os, sys, re, glob

import peppy.vfs as vfs
import peppy.hsi.datasetfs

from peppy.debug import *
from peppy.stcinterface import *


class HyperspectralSTC(NonResidentSTC):
    """Combination of STC and proxy for a hyperspectral dataset"""
    
    def open(self, buffer, message=None):
        self.url = buffer.raw_url
        self.message = message
        self.dataset = HyperspectralFileFormat.load(self.url, progress=self.updateGauge)

    def updateGauge(self, current, length=-1):
        # Delay importing pubsub until here so that loader can be used without
        # wx installed.
        import wx.lib.pubsub.Publisher
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
    
    def getCube(self, url=None, index=0, progress=None):
        try:
            return self.dataset.getCube(filename=url, index=index, progress=progress)
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
                return self.dataset.getCube(filename=url, index=index, progress=progress)
            dprint("Caught OSError; most likely out-of-memory error due to mmap.  Alternate loaders failed.")
            raise
    
    def GetLength(self):
        return vfs.get_size(self.url)
        
    def Destroy(self):
        self.dataset = None


class HyperspectralFileFormat(debugmixin):
    loaded = False

    default_handlers = []
    handlers = []

    plugin_manager = None

    @classmethod
    def addDefaultHandler(cls, handler):
        cls.default_handlers.append(handler)

    @classmethod
    def removeHandler(cls, handler):
        cls.default_handlers.remove(handler)
    
    @classmethod
    def getHandlerByName(cls, name):
        for handler in cls.handlers:
            if handler.format_id == name:
                return handler
        return None

    @classmethod
    def setPluginManager(cls, pm):
        cls.plugin_manager = pm
        
    @classmethod
    def discover(cls):
        if HyperspectralFileFormat.loaded:
            return
        import ENVI
        import FITS
        import subcube
        
        cls.handlers = [h for h in cls.default_handlers]
        
        HyperspectralFileFormat.loaded = True

    @classmethod
    def identifyall(cls, url):
        cls.discover()
        
        cls.dprint("handlers: %s" % cls.handlers)
        matches = []
        for format in cls.handlers:
            cls.dprint("checking %s for %s format" % (url, format.format_name))
            if format.identify(url):
                cls.dprint("Possible match for %s format" % format.format_name)
                matches.append(format)
        order = []
        for match in matches:
            # It is possible that the file can be loaded as more than
            # one format.  For instance, GDAL supports a bunch of
            # formats, but custom classes can be written to be more
            # efficient than GDAL.  So, loop through the matches and
            # see if there is a specific class that should be used
            # instead of a generic one.
            cls.dprint("Checking %s for specific support of %s" % (match, url))
            name, ext = os.path.splitext(url.path.get_name())
            ext.lower()
            if ext in match.extensions:
                cls.dprint("Found specific support for %s in %s" % (ext, match))
                order.append(match)
                matches.remove(match)
        if len(matches)>0:
            order.extend(matches)
        return order

    @classmethod
    def identify(cls, url):
        fh = vfs.open(url)
        assert cls.dprint("checking for cube handler: %s" % dir(fh))
        if fh and hasattr(fh, 'metadata') and hasattr(fh.metadata, 'getCube'):
            return fh.metadata
            
        url = vfs.normalize(url)
        matches = cls.identifyall(url)
        if len(matches)>0:
            return matches[0]
        return None

    @classmethod
    def load(cls, url, bad=None, progress=None):
        """Find an HSI dataset instance corresponding to the url
        
        @param url: url to load
        
        @param bad: subclass of HSI.MetadataMixin that should be avoided.  This
        is used to select a different dataset reader if an error occurs with
        the one specified here.
        
        @param progress: (optional) progress bar callback
        
        @return: instance of HSI.MetadataMixin that can read the file, or None
        if nothing is found.
        """
        cls.discover()
        url = vfs.normalize(url)
        
        if bad:
            cls.dprint("EXCLUDING %s" % bad)
        
        # Check to see if there's a specific handler provided in the vfs
        fh = vfs.open(url)
        cls.dprint("checking for cube handler: %s" % dir(fh))
        if fh and hasattr(fh, 'metadata') and hasattr(fh.metadata, 'getCube'):
            dataset = fh.metadata
            # Only return the dataset if it's not the same class we're trying
            # to avoid
            if dataset.__class__ != bad:
                return dataset
        
        # OK, that didn't return a result, so see if there's a HSI handler 
        matches = cls.identifyall(url)
        for format in matches:
            if format == bad:
                cls.dprint("Skipping format %s" % format.format_name)
                continue
            cls.dprint("Loading %s format cube" % format.format_name)
            dataset = format(url, progress=progress)
            return dataset
        return None

    def wildcards(self):
        pairs={}
        for loader in self.handlers:
            for format in loader.supportedFormats():
                pairs[format.format_name]=format.extensions
                
        names=pairs.keys()
        names.sort()
        wildcards=""
        for name in names:
            dprint("%s: %s" % (name,pairs[name]))
            shown=';'.join("*"+ext for ext in pairs[name])
            expandedexts=list(pairs[name])
            expandedexts.extend(ext.upper() for ext in pairs[name])
            dprint(expandedexts)
            expanded=';'.join("*"+ext for ext in expandedexts)
            wildcards+="%s (%s)|%s|" % (name,shown,expanded)

        wildcards+="All files (*.*)|*.*"
        dprint(wildcards)
        return wildcards

