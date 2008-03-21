#-----------------------------------------------------------------------------
# Name:        setuptools-utils.py
# Purpose:     utilities for the PEAK setuptools module
#
# Author:      Rob McMullen
#
# Created:     2007
# RCS-ID:      $Id: $
# Copyright:   (c) 2007 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""setuptools_utils -- utilities for use with setuptools.  Er, duh.

"""
import os

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

USE_SETUPTOOLS = False
try:
    import pkg_resources
    if hasattr(pkg_resources, 'iter_entry_points'):
        USE_SETUPTOOLS = True
    else:
        print "Need a newer version of setuptools to load setuptools plugins."
except:
    #dprint("Setuptools unavailable; setuptools plugins will not be loaded.")
    pass

def count_plugins(entry_point_name, plugin_dirs):
    if USE_SETUPTOOLS:
        global_plugins = tuple(pkg_resources.iter_entry_points(entry_point_name))
        #dprint(global_plugins)
        count = len(global_plugins)
        distributions, errors = pkg_resources.working_set.find_plugins(
            pkg_resources.Environment(plugin_dirs)
            )
        for dist in distributions:
            entries = dist.get_entry_map()
            #dprint("count_plugins: found entries %s" % entries)
            if entry_point_name in entries:
                for name, entrypoint in entries[entry_point_name].iteritems():
                    count += 1
        return count
    return 0

def load_local_plugins(entry_point_name, plugin_dirs, progress=None):
    #dprint("Searching for local plugins: %s" % plugin_dirs)
    
    # Create the environment used to search for plugins in a non-standard spot
    env = pkg_resources.Environment(plugin_dirs)
    distributions, errors = pkg_resources.working_set.find_plugins(env)
    for dist in distributions:
        #dprint(" name=%s version=%s" % (dist.project_name, dist.version))
        entries = dist.get_entry_map()
        
        # Only attempt to load plugins that have the correct entry point.
        if entry_point_name in entries:
            
            # In order to import the egg, have to call dist.activate to add the
            # egg's main directory into sys.path.
            dist.activate()
            for name, entrypoint in entries[entry_point_name].iteritems():
                try:
                    plugin_class = entrypoint.load(True, env)
                    #dprint("setuptools plugin loaded: %s, class=%s" % (entrypoint.name, plugin_class))
                    if progress:
                        progress(entrypoint.name)
                except ImportError, e:
                    import traceback
                    dprint(traceback.format_exc())

def load_plugins(entry_point_name, plugin_dirs, progress=None):
    if USE_SETUPTOOLS:
        # First load any eggs in the user path
        load_local_plugins(entry_point_name, plugin_dirs, progress)
        
        # Now load any eggs in sys.path
        for entrypoint in pkg_resources.iter_entry_points(entry_point_name):
            try:
                plugin_class = entrypoint.load()
                #dprint("setuptools plugin loaded: %s, class=%s" % (entrypoint.name, plugin_class))
                if progress:
                    progress(entrypoint.name)
            except ImportError, e:
                import traceback
                dprint(traceback.format_exc())
