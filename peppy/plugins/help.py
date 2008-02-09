# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Help text and convenience functions for the help menu.

This provides the About dialog box and the user manual.
"""

import os,os.path,sys,re,time,commands,glob,random
import urllib2

import wx

from peppy.yapsy.plugins import *
from peppy.debug import *
from peppy.actions import *
from peppy.major import *
from peppy.about import credits, copyrights, substitutes, gpl_text

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
        people = {}
        for author in credits.keys():
            people[author] = 1
        for copyright in copyrights.values():
            dprint(copyright)
            people[copyright['author']] = 1
        #dprint(people.keys())
        devs.extend(people.keys())
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
    
    # mac should be cmd-?, but wx doesn't understand shifted keys as a target
    # for keybindings, so have to specify shift-/, which on standard keyboard
    # is the same as ?
    key_bindings = {'default': "F1", 'mac': "C-S-/"}
    
    def action(self, index=-1, multiplier=1):
        self.frame.open("about:User Manual")
        

class ProjectHome(SelectAction):
    """Go to the project homepage.
    
    Load the project homepage in the default webbrowser.
    """
    name = "Project Homepage"
    default_menu = ("&Help", 101)
    icon = "icons/peppy.png"
    default_toolbar = False
    
    def action(self, index=-1, multiplier=1):
        from peppy import __url__
        import webbrowser
        webbrowser.open(__url__)
        

class BugReport(SelectAction):
    """Report a bug.
    
    Report a bug using the web-based bug tracking system.
    """
    name = "Report a bug"
    default_menu = ("&Help", 102)
    
    def action(self, index=-1, multiplier=1):
        import webbrowser
        webbrowser.open("http://trac.flipturn.org/newticket")
        

class HelpPlugin(IPeppyPlugin):
    def aboutFiles(self):
        return {'User Manual': _user_manual}

    def getActions(self):
        return [HelpAbout, HelpManual, ProjectHome, BugReport]

