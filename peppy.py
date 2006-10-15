#!/usr/bin/env python

"""
peppy - (ap)Proximated (X)Emacs Powered by Python.

This is a wxPython/Scintilla-based editor written in and extensible
through Python. It attempts to provide an XEmacs-like multi-window,
multi-tabbed interface.

"""

import os,os.path,sys,re,time,commands,glob,random

import wx

from menudev import *
from buffers import *

# setup.py requires that these be defined, and the OnceAndOnlyOnce
# principle is used here.  This is the only place where these values
# are defined in the source distribution, and everything else that
# needs this should grab it from here.
__version__ = "0.1.0"
__author__ = "Rob McMullen"
__author_email__ = "robm@users.sourceforge.net"
__url__ = "http://www.flipturn.org/peppy/"
__download_url__ = "http://www.flipturn.org/peppy/archive/"
__description__ = "(ap)Proximated (X)Emacs Powered by Python"
__keywords__ = "text editor, wxwindows, scintilla"
__license__ = "Python"



class NewTab(FrameAction):
    name = "New &Tab"
    tooltip = "Open a new Tab"
    icon = wx.ART_FILE_OPEN

    def action(self, state=None, pos=-1):
        print "exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos))
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
        print "exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos))
        self.frame.openFileDialog()

class OpenAlpha(FrameAction):
    name = "&Open Alpha..."
    tooltip = "Open an Alpha object"
    icon = wx.ART_FILE_OPEN

    def action(self, state=None, pos=-1):
        print "exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos))
        self.frame.open("alpha")

class OpenBravo(FrameAction):
    name = "&Open Bravo..."
    tooltip = "Open a Bravo object"
    icon = wx.ART_FILE_OPEN

    def action(self, state=None, pos=-1):
        print "exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos))
        self.frame.open("bravo")

class Close(FrameAction):
    name = "&Close"
    tooltip = "Close current file"
    icon = "icons/cross.png"

    def isEnabled(self, state=None):
        return self.frame.isOpen()

    def action(self, state=None, pos=-1):
        print "exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos))
        self.frame.close()

class Save(FrameAction):
    name = "&Save..."
    tooltip = "Save the current file"
    icon = "icons/disk.png"
    keyboard = "C-X C-S"

    def isEnabled(self, state=None):
        return self.frame.isOpen()

    def action(self, state=None, pos=-1):
        print "exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos))
        self.frame.save()

class SaveAs(FrameAction):
    name = "Save &As..."
    tooltip = "Save as a new file"
    icon = "icons/disk_edit.png"
    keyboard = "C-X C-W"
    
    def isEnabled(self, state=None):
        return self.frame.isOpen()

    def action(self, state=None, pos=-1):
        print "exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos))
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
        print "exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos))
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
        print "exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos))
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
        print "HelpAbout: id=%x name=%s" % (id(self),self.name)
        cube=self.frame.showModalDialog(self.about,self.title)


menu_plugins=[
    ['main',[('&File',0.0)],NewTab,0.1],
    [OpenFile,0.1],
    [None,0.20],
    [OpenAlpha],
    [OpenBravo],
    [None,0.21], # separator
    [Save,0.8],
    [SaveAs],
    [Close],
    [None], # separator
    [Quit,1.0],
    ['main',[('&Edit',0.1)],ShowToolbar,0.1],
    [Undo],
    [Redo],
    [None],
    [Cut],
    [Copy],
    [Paste],
    ['main',[('&Buffers',0.2)],BufferList,0.0],
    ['main',[('&Windows',0.3)],NewWindow,0.0],
    [DeleteWindow,0.1],
    [None],
    [FrameList,0.2],
    ['main',[('&Help',1.0)],HelpAbout,1.0],
    ['alpha',[('&Bands',0.25)],PrevBand,0.0],
    [NextBand],
]

toolbar_plugins=[
    # toolbar plugins here...
    ['main',New,0.05],
    [OpenFile],
    [None],
#    [OpenAlpha,0.1],
#    [OpenBravo],
    [Save,0.2],
    [SaveAs],
    [Close],
    [None],
    [Cut],
    [Copy],
    [Paste],
    [None],
    [Undo],
    [Redo],
    [None],
    ]

keyboard_plugins=[]



class AlphaView(View):
    pluginkey = 'alpha'
    keyword='Alpha'
    icon = 'icons/world.png'
    regex = "alpha"

    def createWindow(self,parent):
        self.win=wx.Window(parent, -1)
        wx.StaticText(self.win, -1, self.buffer.name, (45, 45))


class BravoView(View):
    pluginkey = 'bravo'
    keyword='Bravo'
    icon='icons/bug_add.png'
    regex="bravo"

    def createWindow(self,parent):
        self.win=wx.Window(parent, -1)
        wx.StaticText(self.win, -1, self.buffer.name, (100,100))


class TitleView(View):
    pluginkey = 'title'
    keyword='Title'
    icon='icons/application.png'
    regex="title"

    def createWindow(self,parent):
        self.win=wx.Window(parent, -1)
        wx.StaticText(self.win, -1, self.buffer.name, (10,10))


class TitleBuffer(Buffer):
    def __init__(self,parent,filename=None,viewer=TitleView,fh=None):
        Buffer.__init__(self,parent,filename,viewer,fh,BlankSTC)
        self.name="%s %s\n%s" % ("peppy",__version__,__description__)



class Peppy(BufferApp):
    def OnInit(self):
        BufferApp.OnInit(self)
        self.addMenuPlugins(menu_plugins)
        self.addToolbarPlugins(toolbar_plugins)
        self.addKeyboardPlugins(keyboard_plugins)
        self.registerViewer(AlphaView)
        self.registerViewer(BravoView)

        plugins=['test-plugin','hexedit-plugin','python-plugin','fundamental']
        try:
            for plugin in plugins:
                mod=__import__(plugin)
                self.loadPlugin(mod)
        except:
            print "couldn't load plugins"
            raise
        return True


if __name__ == "__main__":
    from optparse import OptionParser

    usage="usage: %prog file [files...]"
    parser=OptionParser(usage=usage)
    (options, args) = parser.parse_args()
    print options

    app=Peppy()
    frame=BufferFrame(app)
    frame.Show(True)
    if args:
        for filename in args:
            frame.open(filename)
    else:
        buffer=TitleBuffer(frame)
        frame.newBuffer(buffer)
        
    app.MainLoop()

