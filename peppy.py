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
__version__ = "0.0.1"
__author__ = "Rob McMullen"
__author_email__ = "robm@users.sourceforge.net"
__url__ = "http://www.flipturn.org/peppy/"
__download_url__ = "http://www.flipturn.org/peppy/archive/"
__description__ = "(ap)Proximated (X)Emacs Powered by Python"
__keywords__ = "text editor, wxwindows, scintilla"
__license__ = "Python"



class NewTab(Command):
    name = "New &Tab"
    tooltip = "Open a new Tab"
    icon = wx.ART_FILE_OPEN

    def runthis(self, state=None, pos=-1):
        print "exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos))
        self.frame.proxy.newTab(self.frame)

class OpenFile(Command):
    name = "&Open File..."
    tooltip = "Open a file"
    icon = wx.ART_FILE_OPEN

    def runthis(self, state=None, pos=-1):
        print "exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos))
        self.frame.openFileDialog()

class OpenAlpha(Command):
    name = "&Open Alpha..."
    tooltip = "Open an Alpha object"
    icon = wx.ART_FILE_OPEN

    def runthis(self, state=None, pos=-1):
        print "exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos))
        self.frame.proxy.open(self.frame,"alpha")

class OpenBravo(Command):
    name = "&Open Bravo..."
    tooltip = "Open a Bravo object"
    icon = wx.ART_FILE_OPEN

    def runthis(self, state=None, pos=-1):
        print "exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos))
        self.frame.proxy.open(self.frame,"bravo")

class Close(Command):
    name = "&Close"
    tooltip = "Close current file"
    icon = wx.ART_QUIT

    def isEnabled(self, state=None):
        return self.frame.isOpen()

    def runthis(self, state=None, pos=-1):
        print "exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos))
        self.frame.close()

class Save(Command):
    name = "&Save..."
    tooltip = "Save the current file"
    icon = wx.ART_FILE_SAVE

    def isEnabled(self, state=None):
        return self.frame.isOpen()

class SaveAs(Command):
    name = "Save &As..."
    tooltip = "Save as a new file"
    icon = wx.ART_FILE_SAVE_AS
    
    def isEnabled(self, state=None):
        return self.frame.isOpen()



class PrevBand(Command):
    name = "Prev"
    tooltip = "Previous Band"
    icon = wx.ART_GO_BACK
    
    def __init__(self, frame):
        Command.__init__(self, frame)

class NextBand(Command):
    name = "Next"
    tooltip = "Next Band"
    icon = wx.ART_GO_FORWARD
    
    def __init__(self, frame):
        Command.__init__(self, frame)


class TestImage(Command):
    name = "Open Test Image"
    tooltip = "Open a 128x128x16 test image"
    
    def run(self, state=None, pos=None):
        print "TestImage: id=%x name=%s" % (id(self),self.name)
        cube=self.frame.proxy.createTestCube()
        self.frame.setCube(cube)



class ToggleList(CommandList):
    name = "ToggleList"
    tooltip = "Some help for this group of toggle buttons"
    toggle = True

    # radio list shared
    itemlist = [
        {'item':1,'name':'toggle 1','icon':wx.ART_HARDDISK,'checked':False},
        {'item':2,'name':'toggle 2','icon':wx.ART_FLOPPY,'checked':True},
        {'item':3,'name':'toggle 3','icon':wx.ART_CDROM,'checked':True},
        ]
    
    def __init__(self, frame):
        CommandList.__init__(self, frame)
        self.itemlist = ToggleList.itemlist

        # initialize checked/unchecked status from defaults
        self.checked = [item['checked'] for item in self.itemlist]

    def isChecked(self, index):
        return self.checked[index]
    
    def run(self, state=None, pos=-1):
        print "exec: id=%x name=%s pos=%d" % (id(self),self.name,pos)
        self.checked[pos] = not self.checked[pos]

   
    
class HelpAbout(Command):
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
    ['main',[('&Buffers',0.8)],BufferList,0.0],
    ['main',[('&Windows',0.9)],NewWindow,0.0],
    [DeleteWindow,0.1],
    [None],
    [FrameList,0.2],
    ['main',[('&Help',1.0)],HelpAbout,1.0],
    ['alpha',[('&Bands',0.5)],PrevBand,0.0],
    [NextBand],
]

toolbar_plugins=[
    # toolbar plugins here...
    ['main',OpenFile,0.05],
    [None],
    [OpenAlpha,0.1],
    [OpenBravo],
    [Close,0.2],
    [Save],
    [SaveAs],
    [None],
    ['alpha',PrevBand,0.3],
    [NextBand],
    ['bravo',TestRadioList,0.3],
    [None],
    [ToggleList],
    ]





class AlphaView(View):
    pluginkey = 'alpha'
    keyword='Alpha'
    icon = 'icons/py.ico'
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




class testapp(BufferApp):
    def OnInit(self):
        BufferApp.OnInit(self)
        self.main.addMenuPlugins(menu_plugins)
        self.main.addToolbarPlugins(toolbar_plugins)
        self.main.registerViewer(AlphaView)
        self.main.registerViewer(BravoView)

        plugins=['test-plugin1','hexedit-plugin','fundamental']
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
    parser.add_option("-c", action="store", type="float", dest="stretch",
                      default=0.0)
    parser.add_option("-s", action="store", type="float", dest="filter",
                      default=.65)
    parser.add_option("-r", action="store", type="float", dest="red",
                      default=676.0)
    parser.add_option("-n", action="store", type="float", dest="nir",
                      default=788.0)
    parser.add_option("-b", action="store", type="float", dest="bluerange",
                      nargs=2, default=[400.0,500.0])
    parser.add_option("-o", action="store", dest="outputfile")
    (options, args) = parser.parse_args()
    print options

    app=testapp(0)
    proxy=app.getProxy()
    frame=BufferFrame(proxy)
    frame.Show(True)
    if args:
        for filename in args:
            proxy.open(frame,filename)
        
    app.MainLoop()

