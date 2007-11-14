# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""STCStyleEditor plugin.

This plugin provides access to a dialog used to configure the text
styles of the STC.
"""
import os

from wx.lib.pubsub import Publisher

from peppy.yapsy.plugins import *
from peppy.menu import *

from peppy.editra import *
import peppy.editra.style_editor as style_editor

from peppy.about import AddCopyright

AddCopyright("Editra", "http://www.editra.org", "Cody Precord", "2005-2007", "The styling dialog and syntax definitions for over 30 languages from")


class EditraStyles(SelectAction):
    name = "Text Styles..."
    tooltip = "Open the STC Style Editor to edit the current mode's text display."
    default_menu = ("Edit", -1000)
    
    def isEnabled(self):
        return hasattr(self.mode.classprefs, 'editra_style_sheet')

    def action(self, index=-1, multiplier=1):
        stylesheet = self.mode.getStyleFile()
        dprint(stylesheet)
        dlg = style_editor.StyleEditor(self.frame, -1)
        retval = dlg.ShowModal()
        if retval == wx.ID_OK:
            sheet = dlg.GenerateStyleSheet()
            dprint(sheet)
            fh = wx.GetApp().config.open(stylesheet, 'wb')
            fh.write(sheet)
        dlg.Destroy()
        Publisher().sendMessage('peppy.preferences.changed')



class EditraStylesPlugin(IPeppyPlugin):
    def getActions(self):
        return [EditraStyles]
