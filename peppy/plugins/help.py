# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Help text and convenience functions for the help menu.

This provides the About dialog box and the user manual.
"""

import os,os.path,sys,re,time,commands,glob,random
import urllib2

import wx

from peppy.yapsy.plugins import *
from peppy.debug import *
from peppy.menu import *
from peppy.major import *
from peppy.about import credits, substitutes, gpl_text

# if you import from peppy instead of main here, the ExtensionPoints
# in peppy will get loaded twice.
from peppy import __url__

_user_manual = """<!-- -*- HTMLView -*- -->
<h2>User Manual for %(prog)s %(version)s</h2>
<p>Copyright (c) %(yearrange)s %(author)s (%(author_email)s)</p>

<p>Well, not so much a user's manual as a placeholder for one.
"""

class HelpAbout(SelectAction):
    name = "&About..."
    tooltip = "About this program"
    stock_id = wx.ID_ABOUT
    default_menu = ("&Help", 0)

    about = "Test program"
    title = "Test program title"
    
    def action(self, index=-1, multiplier=1):
        from wx.lib.wordwrap import wordwrap
        
        info = wx.AboutDialogInfo()
        info.Name = substitutes['prog']
        info.Version = substitutes['version']
        info.Copyright = substitutes['copyright']
        info.Description = wordwrap(substitutes['description'],
            350, wx.ClientDC(self.frame))
        info.WebSite = (__url__, "%(prog)s home page" % substitutes)
        devs = [ substitutes['author'],
                 "",
                 _("Contributions by:"),
                 ]
        dprint([a for a,c in credits])
        devs.extend([a for a,c in credits])
        devs.extend(("", _("See the file THANKS for more credits")))
        info.Developers = devs
        dprint(info.Developers)

        info.License = wordwrap(gpl_text, 500, wx.ClientDC(self.frame))

        # Then we call wx.AboutBox giving it that info object
        wx.AboutBox(info)

class HelpManual(SelectAction):
    name = "&Help..."
    tooltip = "User manual"
    stock_id = wx.ID_HELP
    default_menu = ("&Help", -100)
    key_bindings = {'default': "F1",}
    
    def action(self, index=-1, multiplier=1):
        self.frame.open("about:User Manual")
        

class HelpPlugin(IPeppyPlugin):
    def aboutFiles(self):
        return {'User Manual': _user_manual}

    def getActions(self):
        return [HelpAbout, HelpManual]

