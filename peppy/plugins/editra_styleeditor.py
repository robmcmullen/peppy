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

class EditraStyles(SelectAction):
    name=_("Text Styles...")
    tooltip = _("Open the STC Style Editor to edit the current mode's text display.")
    default_menu = ("Format", 1000)
    icon = "icons/style_edit.png"

    def isEnabled(self):
        if hasattr(self.mode.classprefs, 'editra_style_sheet'):
            dprint(self.mode.classprefs.editra_style_sheet)
            return True
        return False

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



class EditraStylesMenuProvider(IPeppyPlugin):
    def geActions(self):
        return [EditraStyles]
