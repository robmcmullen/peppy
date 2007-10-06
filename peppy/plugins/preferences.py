# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Preferences dialog.

This plugin implements the preferences dialog that is used to modify
the default settings of objects that inherit from the ClassPrefs
class.
"""
import os, sys

from wx.lib.pubsub import Publisher
import wx.grid

from peppy.yapsy.plugins import *
from peppy.menu import *
from peppy.configprefs import *
from peppy.lib.userparams import *
from peppy.lib.iconstorage import *
from peppy.lib.pluginmanager import *

class Preferences(SelectAction):
    name = _("&Preferences...")
    tooltip = _("Preferences, settings, and configurations...")
    icon = "icons/wrench.png"
    stock_id = wx.ID_PREFERENCES

    @classmethod
    def showDialog(self, msg=None):
        frame = wx.GetApp().GetTopWindow()
        mode = frame.getActiveMajorMode()
        dlg = PeppyPrefDialog(frame, mode)
        retval = dlg.ShowModal()
        if retval == wx.ID_OK:
            dlg.applyPreferences()
            Publisher().sendMessage('peppy.preferences.changed')
        dlg.Destroy()

    def action(self, index=-1):
        self.showDialog()

# FIXME: this is probably not the standard way I want to set up
# messages, but it works for now.  Will refactor at some point.
Publisher().subscribe(Preferences.showDialog, 'peppy.preferences.show')

class PeppyPrefClassList(PrefClassList):
    """Add icon support to PrefClassTree"""

    def setIconStorage(self):
        getIconStorage().assignList(self)

    def getIcon(self, cls):
        icon = None
        if hasattr(cls, 'icon') and cls.icon is not None:
            icon = getIconStorage(cls.icon)
        return icon
    
    def appendItem(self, cls):
        icon = self.getIcon(cls)
        if icon is None:
            icon = -1
        self.InsertImageStringItem(sys.maxint, cls.__name__, icon)
            
    def setItem(self, index, cls):
        icon = self.getIcon(cls)
        if icon is None:
            icon = -1
        self.SetStringItem(sys.maxint, cls.__name__, icon)

class PeppyPrefDialog(PrefDialog):
    dialog_title = _("Peppy Global Preferences")
    static_title = ""

    def createList(self, parent):
        list = PeppyPrefClassList(parent)
        return list
    

class Plugins(SelectAction):
    name = _("&Plugins...")
    tooltip = _("Plugin configuration")
    icon = "icons/plugin.png"

    @classmethod
    def showDialog(self, msg=None):
        frame = wx.GetApp().GetTopWindow()
        dlg = PluginDialog(frame, wx.GetApp().plugin_manager)
        retval = dlg.ShowModal()
        if retval == wx.ID_OK:
            dlg.applyPreferences()
            Publisher().sendMessage('peppy.plugins.changed')
        dlg.Destroy()

    def action(self, index=-1):
        self.showDialog()


class PreferencesPlugin(IPeppyPlugin):
    def getMenuItems(self):
        yield (None,_("Edit"),MenuItem(Preferences).after(_("lastsep")))
        yield (None,_("Edit"),MenuItem(Plugins).after(_("lastsep")))
