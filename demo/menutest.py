#!/usr/bin/env python

import os,sys,time
up_one=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print up_one
sys.path[0:0] = [up_one]
import wx

from peppy.debug import *

from ngmenu import *

from actions import *


class MajorMode(object):
    keyword = None

class PythonMode(MajorMode):
    keyword = 'Python'

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
        self.mode = PythonMode()
        FrameList.append(self)
        
        # tell FrameManager to manage this frame        
        self._mgr = wx.aui.AuiManager()
        self._mgr.SetManagedWindow(self)

        self.CreateStatusBar()
        self.SetStatusText("This is the statusbar")

        self.win = wx.TextCtrl(self, -1, """
A bunch of bogus menus have been created for this frame.  You
can play around with them to see how they behave and then
check the source for this sample to see how to implement them.
""", style=wx.TE_READONLY|wx.TE_MULTILINE)
        self._mgr.AddPane(self.win, wx.aui.AuiPaneInfo().Name("text").
                          CenterPane())

        # Prepare the menu bar
        self.settings={'asteroids':False,
                       'inner planets':True,
                       'outer planets':True,
                       'major mode':'C++',
                       'toolbar': True,
                       }
        
        self.SetMenuBar(wx.MenuBar())
        self.menumap = None
        UserActionMap.setDefaultMenuBarWeights({'Edit': 10})
        self.setMenumap()
    
    def __del__(self):
        dprint("DELETING FRAME %s" % self.title)

    # Methods
    def OnClose(self, evt=None):
        dprint(evt)
        FrameList.remove(self)
        self.Destroy()

    def Raise(self):
        wx.Frame.Raise(self)
        self.win.SetFocus()
        
    def getActiveMajorMode(self):
        return self.mode
        
    def setMenumap(self):
        if self.menumap is not None:
            self.menumap.cleanupPrevious(self._mgr)
        actions = getActions()
        modes = [self.settings['major mode']]
        self.menumap = UserActionMap(self, actions, modes)
        self.menumap.updateMenuActions(self.GetMenuBar())
        if self.settings['toolbar']:
            self.menumap.updateToolbarActions(self._mgr)
        self._mgr.Update()
        
    def switchMode(self,mode):
        dprint("Switching to mode %s" % mode)
        self.settings['major mode']=mode
        self.setMenumap()

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

