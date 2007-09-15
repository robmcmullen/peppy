# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Preferences dialog.

This plugin implements the preferences dialog that is used to modify
the default settings of objects that inherit from the ClassPrefs
class.
"""
import os

from wx.lib.pubsub import Publisher
import wx.grid

from peppy.menu import *
from peppy.trac.core import *
from peppy.configprefs import *
from peppy.lib.userparams import *
from peppy.lib.iconstorage import *

class Preferences(SelectAction):
    name = _("&Preferences...")
    tooltip = _("Preferences, settings, and configurations...")
    icon = "icons/wrench.png"
    stock_id = wx.ID_PREFERENCES

    def action(self, pos=-1):
        assert self.dprint("exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        dlg = PeppyPrefDialog(self.frame, self.frame.getActiveMajorMode())
        retval = dlg.ShowModal()
        if retval == wx.ID_OK:
            dlg.applyPreferences()
            Publisher().sendMessage('settingsChanged')
        dlg.Destroy()


class PeppyPrefClassTree(PrefClassTree):
    """Add icon support to PrefClassTree"""

    def setIconStorage(self):
        getIconStorage().assign(self)

    def setIconForItem(self, item, cls=None):
        icon = None
        if item == self.GetRootItem():
            icon = getIconStorage("icons/wrench.png")
        elif hasattr(cls, 'icon') and cls.icon is not None:
            icon = getIconStorage(cls.icon)
        
        if icon is not None:
            self.SetItemImage(item, icon)

class PeppyPrefDialog(PrefDialog):
    dialog_title = _("Peppy Global Preferences")
    static_title = ""

    def createTree(self, parent):
        tree = PeppyPrefClassTree(parent)
        return tree
    

class PreferencesPlugin(Component):
    implements(IMenuItemProvider)

    def getMenuItems(self):
        yield (None,_("Edit"),MenuItem(Preferences).after(_("lastsep")))
