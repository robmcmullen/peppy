# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Definition and storage of the 'about:' protocol.

This provides the about: protocol handling (a read-only protocol) for
built-in storage of data.  It also provides some global user interface
elements for the help menu and other testing menu items.
"""

import os,os.path,sys,re,time,commands,glob,random
import urllib2

import wx

from peppy.yapsy.plugins import *
from peppy.debug import *
from peppy.menu import *
from peppy.major import *
from peppy.about import SetAbout, credits, substitutes, gpl_text

# if you import from peppy instead of main here, the ExtensionPoints
# in peppy will get loaded twice.
from peppy import __url__

class HelpAbout(SelectAction):
    name = _("&About...")
    tooltip = _("About this program")
    stock_id = wx.ID_ABOUT

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


SetAbout('User Manual',"""\
<!-- -*- HTMLView -*- -->
<h2>User Manual for %(prog)s %(version)s</h2>
<p>Copyright (c) %(yearrange)s %(author)s (%(author_email)s)</p>

<p>Well, not so much a user's manual as a placeholder for one.
""")
class HelpManual(SelectAction):
    name = _("&Help...")
    tooltip = _("User manual")
    stock_id = wx.ID_HELP
    key_bindings = {'default': "F1",}
    
    def action(self, index=-1, multiplier=1):
        self.frame.open("about:User Manual")
        

class HelpPlugin(IPeppyPlugin):
    default_menu=((None,None,Menu(_("&Help")).last()),
                  (None,_("&Help"),MenuItem(HelpAbout).first()),
                  (None,_("&Help"),Separator(_("manual")).first()),
                  (None,_("&Help"),MenuItem(HelpManual).first()),
                  (None,_("&Help"),Separator(_("debug")).first()),
                  )
    def getMenuItems(self):
        for mode,menu,item in self.default_menu:
            yield (mode,menu,item)

