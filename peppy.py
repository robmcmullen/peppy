#!/usr/bin/env python

"""
peppy - (ap)Proximated (X)Emacs Powered by Python.

This is a wxPython/Scintilla-based editor written in and extensible
through Python. It attempts to provide an XEmacs-like multi-window,
multi-tabbed interface.

Plugins
=======

There are currently two plugin types that can be used to extend peppy:
L{ProtocolPlugin<plugin.ProtocolPlugin>}s and
L{ViewPlugin<plugin.ViewPlugin>}s.

@author: $author
@version: $version
"""

import os,os.path,sys,re,time,commands,glob,random

import wx

from menudev import *
from buffers import *
from iofilter import SetAbout
from debug import *

# setup.py requires that these be defined, and the OnceAndOnlyOnce
# principle is used here.  This is the only place where these values
# are defined in the source distribution, and everything else that
# needs this should grab it from here.
__version__ = "0.3.0"
__author__ = "Rob McMullen"
__author_email__ = "robm@users.sourceforge.net"
__url__ = "http://www.flipturn.org/peppy/"
__download_url__ = "http://www.flipturn.org/peppy/archive/"
__description__ = "(ap)Proximated (X)Emacs Powered by Python"
__keywords__ = "text editor, wxwindows, scintilla"
__license__ = "Python"

SetAbout('title.txt',"%s %s\n%s" % ("peppy",__version__,__description__))
SetAbout('alpha','')
SetAbout('bravo','')

class NewTab(FrameAction):
    name = "New &Tab"
    tooltip = "Open a new Tab"
    icon = wx.ART_FILE_OPEN

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.newTab()

class New(FrameAction):
    name = "&New File..."
    tooltip = "New file"
    icon = "icons/page.png"


class OpenFile(FrameAction):
    name = "&Open File..."
    tooltip = "Open a file"
    icon = "icons/folder_page.png"
    keyboard = "C-X C-F"

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.openFileDialog()

class OpenAlpha(FrameAction):
    name = "&Open Alpha..."
    tooltip = "Open an Alpha object"
    icon = wx.ART_FILE_OPEN

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.open("about:alpha")

class OpenBravo(FrameAction):
    name = "&Open Bravo..."
    tooltip = "Open a Bravo object"
    icon = wx.ART_FILE_OPEN

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.open("about:bravo")

class Close(FrameAction):
    name = "&Close"
    tooltip = "Close current file"
    icon = "icons/cross.png"

    def isEnabled(self, state=None):
        return self.frame.isOpen()

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.close()

class Save(FrameAction):
    name = "&Save..."
    tooltip = "Save the current file"
    icon = "icons/disk.png"
    keyboard = "C-X C-S"

    def isEnabled(self, state=None):
        return self.frame.isOpen()

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.save()

class SaveAs(FrameAction):
    name = "Save &As..."
    tooltip = "Save as a new file"
    icon = "icons/disk_edit.png"
    keyboard = "C-X C-W"
    
    def isEnabled(self, state=None):
        return self.frame.isOpen()

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.saveFileDialog()


class Undo(FrameAction):
    name = "Undo"
    tooltip = "Undo"
    icon = "icons/arrow_turn_left.png"
    keyboard = "C-/"
    
    def __init__(self, frame):
        FrameAction.__init__(self, frame)

    def isEnabled(self, state=None):
        viewer=self.frame.getCurrentViewer()
        if viewer: return viewer.stc.CanUndo()
        return False

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        viewer=self.frame.getCurrentViewer()
        if viewer: return viewer.stc.Undo()


class Redo(FrameAction):
    name = "Redo"
    tooltip = "Redo"
    icon = "icons/arrow_turn_right.png"
    keyboard = "C-S-/"
    
    def __init__(self, frame):
        FrameAction.__init__(self, frame)
        
    def isEnabled(self, state=None):
        viewer=self.frame.getCurrentViewer()
        if viewer: return viewer.stc.CanRedo()
        return False

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        viewer=self.frame.getCurrentViewer()
        if viewer: return viewer.stc.Redo()



class Cut(FrameAction):
    name = "Cut"
    tooltip = "Cut"
    icon = "icons/cut.png"
    
    def __init__(self, frame):
        FrameAction.__init__(self, frame)

class Copy(FrameAction):
    name = "Copy"
    tooltip = "Copy"
    icon = "icons/page_copy.png"
    
    def __init__(self, frame):
        FrameAction.__init__(self, frame)

class Paste(FrameAction):
    name = "Paste"
    tooltip = "Paste"
    icon = "icons/paste_plain.png"
    
    def __init__(self, frame):
        FrameAction.__init__(self, frame)

   
    
class HelpAbout(FrameAction):
    name = "&About..."
    tooltip = "About this program"

    about = "Test program"
    title = "Test program title"
    
    def run(self, state=None, pos=None):
        cube=self.frame.showModalDialog(self.about,self.title)





class AlphaView(View):
    pluginkey = 'alpha'
    keyword='Alpha'
    icon = 'icons/world.png'
    regex = "alpha"
    defaultsettings={
        'menu_actions':[
            [[('&Bands',0.25)],PrevBand,0.0],
            NextBand,
            ]
        }

    def createEditWindow(self,parent):
        win=wx.Window(parent, -1)
        wx.StaticText(win, -1, self.buffer.name, (45, 45))
        return win


class BravoView(View):
    pluginkey = 'bravo'
    keyword='Bravo'
    icon='icons/bug_add.png'
    regex="bravo"

    def createEditWindow(self,parent):
        win=wx.Window(parent, -1)
        wx.StaticText(win, -1, self.buffer.name, (100,100))
        return win


class TitleView(View):
    pluginkey = 'title'
    keyword='Title'
    icon='icons/application.png'
    regex="about:title.txt"
    temporary=True

    def createEditWindow(self,parent):
        win=wx.Window(parent, -1)
        text=self.buffer.stc.GetText()
        wx.StaticText(win, -1, text, (10,10))
        return win




class Peppy(BufferApp,ClassSettingsMixin):
    debuglevel=0
    initialconfig={'MenuFrame':{'width':600,
                                'height':500,
                                },
                   'Peppy':{'plugins':'hexedit-plugin,python-plugin,fundamental',
                            },
                   'View':{'linenumbers':True,
                           'wordwrap':False,
                           },
                   'PythonView':{'wordwrap':True,
                                 },
                   }
    
    def OnInit(self):
        BufferApp.OnInit(self)

        ClassSettingsMixin.__init__(self)
        self.setConfigDir("peppy")
        self.setInitialConfig(self.initialconfig)
        self.loadConfig("peppy.cfg")
        
        self.addGlobalMenu(global_menu_actions)
        self.addGlobalToolbar(global_toolbar_actions)
        self.addGlobalKeys(global_keyboard_actions)

        self.parseConfig()

        return True

    def parseConfig(self):
        self.parseConfigPlugins()
##        if cfg.has_section('debug'):
##            self.parseConfigDebug('debug',cfg)

    def parseConfigPlugins(self):
        mods=self.settings.plugins
        self.dprint(mods)
        if mods is not None:
            self.loadPlugins(mods)


    def quitHook(self):
        GlobalSettings.saveConfig("peppy.cfg")
        return True


def run(options={},args=None):
    app=Peppy()
    frame=BufferFrame(app)
    frame.Show(True)
    if args:
        for filename in args:
            frame.open(filename)
        
    app.MainLoop()


global_menu_actions=[
    [[('&File',0.0)],OpenFile,0.0],
    [[('&File',0.0),('Open Recent',0.1)],OpenRecent,0.1],
    [[('&File',0.0)],None,0.2], # separator
    OpenAlpha,
    OpenBravo,
    [None,0.21], # separator
    [Save,0.8],
    SaveAs,
    Close,
    None, # separator
    [Quit,1.0],
    [[('&Edit',0.1)],Undo,0.1],
    Redo,
    None,
    Cut,
    Copy,
    Paste,
    [[('&View',0.2)],NewTab,0.0],
    [NewWindow,0.1],
    DeleteWindow,
    None,
    [FrameList,0.2],
    None,
    [ShowToolbar,0.3],
    [[('&Buffers',0.3)],BufferList,0.0],
    [[('&Help',1.0)],HelpAbout,1.0],
]

global_toolbar_actions=[
    # toolbar plugins here...
    [New,0.05],
    OpenFile,
    None,
#    [OpenAlpha,0.1],
#    [OpenBravo,
    [Save,0.2],
    SaveAs,
    Close,
    None,
    Cut,
    Copy,
    Paste,
    None,
    Undo,
    Redo,
    None,
    ]

global_keyboard_actions=[]


class AboutPlugin(Component):
    implements(ViewPlugin)

    def scanEmacs(self,emacsmode,vars):
        return None

    def scanShell(self,bangpath):
        return None

    def scanFilename(self,filename):
        if filename=='about:alpha':
            return ViewMatch(AlphaView,exact=True)
        elif filename=='about:bravo':
            return ViewMatch(BravoView,exact=True)
        elif filename=='about:title.txt':
            return ViewMatch(TitleView,exact=True)
        else:
            return None

    def scanMagic(self,buffer):
        return None




if __name__ == "__main__":
    from optparse import OptionParser

    usage="usage: %prog file [files...]"
    parser=OptionParser(usage=usage)
    parser.add_option("-p", action="store_true", dest="profile", default=False)
    (options, args) = parser.parse_args()
    #print options

    if options.profile:
        import profile
        profile.run('run()','profile.out')
    else:
        run(options,args)

