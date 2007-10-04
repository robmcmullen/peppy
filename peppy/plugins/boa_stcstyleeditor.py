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
import peppy.boa as boa

from peppy.about import AddCopyright
AddCopyright("Boa Constructor", "http://boa-constructor.sourceforge.net/", "Riaan Booysen", "2001-2005", "for the STCStyleEditor dialog for the wxStyledTextCtrl")


class STCStyles(SelectAction):
    name=_("Text Styles...")
    tooltip = _("Open the STC Style Editor to edit the current mode's text display.")
    icon = "icons/style_edit.png"

    def isEnabled(self):
        mode=self.frame.getActiveMajorMode()
        if mode and hasattr(mode, 'has_stc_styling'):
            return mode.has_stc_styling
        return False

    def action(self, pos=-1):
        config=boa.getUserConfigFile(wx.GetApp())
        dprint(config)
        name = self.mode.keyword
        lang = self.mode.keyword.lower()
        dlg = boa.STCStyleEditDlg(self.frame, name, lang, config)

        # special case: the LexerDebug mode needs to set the
        # sample text to whatever is currently in the buffer.  It
        # also needs to set the lexer, so we have to break the
        # black-box model and poke around in the internals of the
        # boa dialog to do it.
        if self.mode.classprefs.stc_boa_use_current_text:
            dlg.stc.SetText(self.mode.stc.GetText())
            dlg.lexer = self.mode.stc.GetLexer()
            dlg._blockUpdate = False
            dlg.setStyles()

        try:
            dlg.ShowModal()
        finally:
            dlg.Destroy()
        Publisher().sendMessage('peppy.preferences.changed')



class STCStylesMenuProvider(IPeppyPlugin):
    def getMenuItems(self):
        yield (None,_("Format"),MenuItem(STCStyles).last())
