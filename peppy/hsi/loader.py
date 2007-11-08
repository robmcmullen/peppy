# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Reading and writing raw HSI cubes.

This class supports reading HSI data cubes (that are stored in raw,
uncompressed formats) using memory mapped file access.
"""

import os, sys, re, glob

from peppy.debug import *
from peppy.iofilter import *

class HyperspectralFileFormat(object):
    loaded = False

    default_handlers = []
    handlers = []

    plugin_manager = None

    @classmethod
    def addDefaultHandler(cls, handler):
        cls.default_handlers.append(handler)

    @classmethod
    def setPluginManager(cls, pm):
        cls.plugin_manager = pm
        
    @classmethod
    def discover(cls):
        if HyperspectralFileFormat.loaded:
            return
        import ENVI
        try:
            import GDAL
        except Exception, e:
            dprint("GDAL not available")

        import peppy.lib.setuptools_utils
        peppy.lib.setuptools_utils.load_plugins("peppy.hsi.plugins")

        cls.handlers = [h for h in cls.default_handlers]
        if cls.plugin_manager is not None:
            plugins = cls.plugin_manager.getActivePluginObjects()
            for plugin in plugins:
                cls.handlers.extend(plugin.supportedFormats())
        
        HyperspectralFileFormat.loaded = True

    @classmethod
    def identifyall(cls, urlinfo):
        cls.discover()
        if not isinstance(urlinfo, URLInfo):
            urlinfo = URLInfo(urlinfo)
        
        dprint("handlers: %s" % cls.handlers)
        matches = []
        for format in cls.handlers:
            dprint("checking %s for %s format" % (urlinfo, format.format_name))
            if format.identify(urlinfo):
                dprint("Possible match for %s format" % format.format_name)
                matches.append(format)
        order = []
        for match in matches:
            # It is possible that the file can be loaded as more than
            # one format.  For instance, GDAL supports a bunch of
            # formats, but custom classes can be written to be more
            # efficient than GDAL.  So, loop through the matches and
            # see if there is a specific class that should be used
            # instead of a generic one.
            dprint("Checking %s for specific support of %s" % (match, urlinfo))
            name, ext = os.path.splitext(urlinfo.path)
            ext.lower()
            if ext in match.extensions:
                dprint("Found specific support for %s in %s" % (ext, match))
                order.append(match)
                matches.remove(match)
        if len(matches)>0:
            order.extend(matches)
        return order

    @classmethod
    def identify(cls, urlinfo):
        matches = cls.identifyall(urlinfo)
        if len(matches)>0:
            return matches[0]
        return None

    @classmethod
    def load(cls, urlinfo):
        cls.discover()
        if not isinstance(urlinfo, URLInfo):
            urlinfo = URLInfo(urlinfo)
        matches = cls.identifyall(urlinfo)
        for format in matches:
            dprint("Loading %s format cube" % format.format_name)
            dataset = format(urlinfo)
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

