# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""setuptools_utils -- utilities for use with setuptools.  Er, duh.

"""
USE_SETUPTOOLS = False
try:
    import pkg_resources
    USE_SETUPTOOLS = True
except:
    print """Failed loading pkg_resources from the setuptools package.
    setuptools plugins will not be loaded."""
    
try:
    from peppy.debug import *
except:
    def dprint(txt=""):
        print txt
        return True

    class debugmixin(object):
        debuglevel = 0
        def dprint(self, txt):
            if self.debuglevel > 0:
                dprint(txt)
            return True

def load_plugins(entry_point):
    if USE_SETUPTOOLS:
        for entrypoint in pkg_resources.iter_entry_points(entry_point):
            plugin_class = entrypoint.load()
            dprint("setuptools plugin loaded: %s, class=%s" % (entrypoint.name, plugin_class))
