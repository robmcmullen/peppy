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
from peppy.about import authors, credits, copyrights, substitutes

# if you import from peppy instead of main here, the ExtensionPoints
# in peppy will get loaded twice.
from peppy import __url__, __bug_report_url__


class HelpAbout(SelectAction):
    name = "&About..."
    tooltip = "About this program"
    stock_id = wx.ID_ABOUT
    default_menu = ("&Help", 0)
    osx_minimal_menu = True

    about = "Test program"
    title = "Test program title"
    
    def action(self, index=-1, multiplier=1):
        from wx.lib.wordwrap import wordwrap
        
        info = wx.AboutDialogInfo()
        info.Name = substitutes['prog']
        info.Version = substitutes['version']
        info.Copyright = substitutes['copyright']
        info.Description = wordwrap("%s\n\nUsing wxPython %s" % (substitutes['description'], wx.version()), 350, wx.ClientDC(self.frame))
        info.WebSite = (__url__, "%(prog)s home page" % substitutes)
        devs = [ substitutes['author'],
                 "",
                 _("Contributions by:"),
                 ]
        people = {}
        for author in authors.keys():
            people[author] = 1
        for author in credits.keys():
            people[author] = 1
        for copyright in copyrights.values():
            people[copyright['author']] = 1
        #dprint(people.keys())
        devs.extend(people.keys())
        info.Developers = devs
        #dprint(info.Developers)

        info.License = wordwrap(substitutes['license_text'], 500, wx.ClientDC(self.frame))

        # Then we call wx.AboutBox giving it that info object
        wx.AboutBox(info)

class UserManual(SelectAction):
    """Display the user manual
    
    """
    name = "User Manual"
    stock_id = wx.ID_HELP
    default_menu = ("&Help", -100)
    osx_minimal_menu = True
    
    # mac should be cmd-?, but wx doesn't understand shifted keys as a target
    # for keybindings, so have to specify shift-/, which on standard keyboard
    # is the same as ?
    
    # emacs should be "M-S-/ i" but that results in two keybindings.  When we
    # use a stock ID and an emacs keybinding, the menu system puts the default
    # "Ctrl+H" in the menu item anyway.  I can't find a way to turn off the
    # default keybinding.
    key_bindings = {'win': "F1",
                    'emacs': "M-S-/ i",
                    #'mac': "M-S-/",
                    }
    
    def action(self, index=-1, multiplier=1):
        wx.GetApp().showHelp()


class MajorModeHelp(SelectAction):
    """Display the manual for the current major mode
    
    """
    name = "Help on Current Major Mode"
    default_menu = ("&Help", 101)
    osx_minimal_menu = False
    
    def action(self, index=-1, multiplier=1):
        wx.GetApp().showHelp(self.mode.keyword)


class ProjectHome(SelectAction):
    """Go to the project homepage.
    
    Load the project homepage in the default webbrowser.
    """
    name = "Project Homepage"
    default_menu = ("&Help", -150)
    icon = "icons/peppy.png"
    default_toolbar = False
    osx_minimal_menu = True
    
    def action(self, index=-1, multiplier=1):
        from peppy import __url__
        import webbrowser
        webbrowser.open(__url__, 2)


class LocateConfigDirectory(SelectAction):
    """Locate the configuration directory.
    
    Bring up the configuration directory in dired mode to show where the per-
    user configuration files are stored for peppy.
    """
    name = "Locate Config Dir"
    default_menu = ("&Help", -300)
    default_toolbar = False
    osx_minimal_menu = True
    
    def action(self, index=-1, multiplier=1):
        confdir = wx.GetApp().config.dir
        self.frame.open(confdir)


class BugReport(SelectAction):
    """Report a bug.
    
    Report a bug using the web-based bug tracking system.
    """
    name = "Report a bug"
    default_menu = ("&Help", 151)
    osx_minimal_menu = True
    
    def action(self, index=-1, multiplier=1):
        import webbrowser
        webbrowser.open(__bug_report_url__, 2)
        

class HelpPlugin(IPeppyPlugin):
    def getActions(self):
        return [HelpAbout,
                
                UserManual, MajorModeHelp,
                
                ProjectHome, BugReport,
                
                LocateConfigDirectory]
