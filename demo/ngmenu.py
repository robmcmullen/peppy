#!/usr/bin/env python

import os,sys,time
up_one=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print up_one
sys.path[0:0] = [up_one]
import wx

from peppy.lib.orderer import *
from peppy.trac.core import *
from peppy.debug import *

from peppy.menu import *

from actions import *


class MyFrame(wx.Frame,debugmixin):
    debuglevel=0
    count=0
    
    def __init__(self, app, id=-1):
        MyFrame.count+=1
        self.count=MyFrame.count
        self.title="Frame #%d" % self.count
        wx.Frame.__init__(self, None, id, self.title, size=(600, 400))

        self.Bind(wx.EVT_CLOSE,self.OnClose)

        self.app=app
        FrameList.append(self)
        
        self.CreateStatusBar()
        self.SetStatusText("This is the statusbar")

        self.win = wx.TextCtrl(self, -1, """
A bunch of bogus menus have been created for this frame.  You
can play around with them to see how they behave and then
check the source for this sample to see how to implement them.
""", style=wx.TE_READONLY|wx.TE_MULTILINE)

        # Prepare the menu bar
        self.settings={'asteroids':False,
                       'inner planets':True,
                       'outer planets':True,
                       'major mode':'C++',
                       }
        
        self.SetMenuBar(wx.MenuBar())
        MenuBarActionMap.debuglevel = 1
        self.setMenumap()

    # Methods
    def OnClose(self, evt=None):
        dprint(evt)
        FrameList.remove(self)
        self.Destroy()

    def Raise(self):
        wx.Frame.Raise(self)
        self.win.SetFocus()
        
    def setMenumap(self,majormode=[None],minormodes=[]):
        comp_mgr=ComponentManager()
        menuloader=MenuItemLoader(comp_mgr)
        self.menumap=menuloader.load(self,majormode,minormodes)
        
    def switchMode(self,mode):
        self.dprint("Switching to mode %s" % mode)
        self.settings['major mode']=mode
        self.setMenumap([mode])

    def getTitle(self):
        return self.title



class TestApp(wx.App,debugmixin):
    def OnInit(self):
        self.settings={'elements':True,
                       }
        return True

    def NewFrame(self):
        frame=MyFrame(self)
        frame.Show(True)
    
    def CloseFrame(self, frame):
        frame.Close()

    def Exit(self):
        self.ExitMainLoop()

def run(options=None,args=None):
    if options is not None:
        if options.logfile:
            debuglog(options.logfile)
    app=TestApp(redirect=False)
    app.NewFrame()
    app.MainLoop()


if __name__ == '__main__':
    from optparse import OptionParser

    usage="usage: %prog file [files...]"
    parser=OptionParser(usage=usage)
    parser.add_option("-p", action="store_true", dest="profile", default=False)
    parser.add_option("-v", action="count", dest="verbose", default=0)
    parser.add_option("-l", action="store", dest="logfile", default=None)
    (options, args) = parser.parse_args()
    
    run(options)

