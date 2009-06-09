#!/usr/bin/python
# -*- coding: utf-8; tab-width: 4; indent-tabs-mode: t -*-

"""
Defines the basic interface for a plugin manager that also keeps track
of versions of plugins
"""

import sys, os

from peppy.lib.userparams import getAllSubclassesOf
from peppy.yapsy.VersionedPluginManager import VersionedPluginManager, VersionedPluginInfo
from peppy.yapsy.plugins import *
from peppy.debug import *

class PeppyPluginManager(VersionedPluginManager, debugmixin):
    """
    Manage several plugins by ordering them in several categories with
    versioning capabilities.
    """

    def getAllPlugins(self):
        if not hasattr(self, 'all_plugins'):
            all = []
            for categ, items in self.category_mapping.iteritems():
                for item in items:
                    all.append(item)
            self.all_plugins = all
        return self.all_plugins

    def activateBuiltins(self):
        """Activate any builtins.

        Builtins are yapsy plugins that are imported directly into the
        code, rather than loaded by searching through the filesystem.
        This also makes it possible to load yapsy plugins through
        other means, like through setuptools plugins.
        """
        #dprint("checking %s" % self.categories_interfaces)
        for cat, interface in self.categories_interfaces.iteritems():
            subclasses = getAllSubclassesOf(interface)
            #dprint("subclasses = %s" % subclasses)
            for element in subclasses:
                plugin_info = VersionedPluginInfo(element.__name__, "<builtin>")
                plugin_info.plugin_object = element()
                plugin_info.category = cat
                self.category_mapping[cat].append(plugin_info)

                plugin_info.plugin_object.activate()
    
    def startupCompleted(self):
        IPeppyPlugin.setStartupComplete()

    def getPluginInfo(self, interface=IPeppyPlugin):
        """Return the list of all plugin_info objects of the requested class
        """
        info = []
        all = self.getAllPlugins()
        for plugin in all:
            #print "checking plugin %s for interface %s" % (plugin.name, interface)
            obj = plugin.plugin_object
            if isinstance(obj, interface):
                info.append(plugin)
        return info
    
    def getActivePluginObjects(self, interface=IPeppyPlugin):
        """
        Return the list of all plugin objects.
        """
        active = []
        all = self.getAllPlugins()
        for plugin in all:
            #print "checking plugin %s for interface %s" % (plugin.name, interface)
            obj = plugin.plugin_object
            if obj.is_activated:
                #print "  plugin %s activated!: class=%s" % (obj, obj.__class__)
                #print "     mro=%s" % str(obj.__class__.__mro__)
                if interface is not None:
                    if isinstance(obj, interface):
                        active.append(obj)
                else:
                    active.append(obj)
        return active
