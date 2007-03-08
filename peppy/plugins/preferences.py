# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Preferences dialog.

This plugin implements the preferences dialog that is used to modify
the default settings of objects that inherit from the ClassSettings
class.
"""
import os

from peppy import *
from peppy.menu import *
from peppy.trac.core import *
from peppy.configprefs import *


class Preferences(SelectAction):
    name = "&Preferences..."
    tooltip = "Preferences, settings, and configurations..."
    icon = "icons/wrench.png"
    stock_id = wx.ID_PREFERENCES

    def action(self, pos=-1):
        assert self.dprint("exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        dlg = PreferencesDialog(self.frame)
        retval = dlg.ShowModal()
        dlg.Destroy()


class PreferencesDialog(wx.Dialog):
    def __init__(self, parent, title="Preferences"):
        wx.Dialog.__init__(self, parent, -1, title,
                           size=wx.DefaultSize, pos=wx.DefaultPosition, 
                           style=wx.DEFAULT_DIALOG_STYLE)

        sizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self, -1, "This is a placeholder for the Preferences dialog")
        sizer.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        btnsizer = wx.StdDialogButtonSizer()
        
        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)


class PreferencesPlugin(Component):
    implements(IMenuItemProvider)

    def getMenuItems(self):
        yield (None,"Edit",MenuItem(Preferences).after("lastsep"))
