#!/usr/bin/env python

import os,sys,time
up_one=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(up_one)

from cStringIO import StringIO
import wx
import wx.aui

from orderer import *
from trac.core import *
from debug import *

from menu import *

from demos.actions import *


text = """\
Hello!

Welcome to this little demo of draggable tabs using the wx.aui module.

To try it out, drag a tab from the top of the window all the way to
the bottom. After releasing the mouse, the tab will dock at the hinted
position.  Then try it again with the remaining tabs in various other
positions.  Finally, try dragg ing a tab to an existing tab ctrl.
You'll soon see that very complex tab layout s may be achieved.
"""


class MyNotebook(wx.aui.AuiNotebook,debugmixin):
    def __init__(self, parent, size=wx.DefaultSize):
        wx.aui.AuiNotebook.__init__(self, parent, size=size, style=wx.aui.AUI_NB_WINDOWLIST_BUTTON|wx.aui.AUI_NB_TAB_MOVE|wx.aui.AUI_NB_TAB_SPLIT|wx.aui.AUI_NB_CLOSE_BUTTON|wx.aui.AUI_NB_SCROLL_BUTTONS)
        
        page = wx.TextCtrl(self, -1, text, style=wx.TE_MULTILINE)
        self.AddPage(page, "Welcome", bitmap=self.getBitmap())

        for num in range(1, 8):
            page = wx.TextCtrl(self, -1, "This is page %d" % num ,
                               style=wx.TE_MULTILINE)
            self.addTab(page, "Page %d" % num)
            
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.OnTabChanged)

    def getBitmap(self):
        img=wx.ImageFromBitmap(wx.Bitmap("icons/py.ico"))
        img.Rescale(16,16)
        bitmap=wx.BitmapFromImage(img)
        return bitmap

    def addTab(self,win,title):
        self.AddPage(win, title, bitmap=self.getBitmap())

    def OnTabChanged(self, evt):
        newpage=evt.GetSelection()
        dprint("changing to %s" % newpage)
        page=self.GetPage(newpage)
        dprint("page: %s" % page)
        evt.Skip()

class DemoTree(wx.TreeCtrl):
    def __init__(self, parent, size=wx.DefaultSize):
        wx.TreeCtrl.__init__(self, parent, -1, wx.Point(0, 0), size=size, style=wx.TR_DEFAULT_STYLE | wx.NO_BORDER)
        
        root = self.AddRoot("AUI Project")
        items = []
        self.SetFont(wx.Font(8, wx.SWISS, wx.NORMAL, wx.NORMAL))

        imglist = wx.ImageList(16, 16, True, 2)
        imglist.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, wx.Size(16,16)))
        imglist.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, wx.Size(16,16)))
        self.AssignImageList(imglist)

        items.append(self.AppendItem(root, "Item 1", 0))
        items.append(self.AppendItem(root, "Item 2", 0))
        items.append(self.AppendItem(root, "Item 3", 0))
        items.append(self.AppendItem(root, "Item 4", 0))
        items.append(self.AppendItem(root, "Item 5", 0))

        for ii in xrange(len(items)):
        
            id = items[ii]
            self.AppendItem(id, "Subitem 1", 1)
            self.AppendItem(id, "Subitem 2", 1)
            self.AppendItem(id, "Subitem 3", 1)
            self.AppendItem(id, "Subitem 4", 1)
            self.AppendItem(id, "Subitem 5", 1)
        
        self.Expand(root)

class MinorNotebook(wx.aui.AuiNotebook,debugmixin):
    def __init__(self, parent, size=wx.DefaultSize):
        wx.aui.AuiNotebook.__init__(self, parent, size=size, style=wx.aui.AUI_NB_WINDOWLIST_BUTTON|wx.aui.AUI_NB_TAB_MOVE|wx.aui.AUI_NB_TAB_SPLIT|wx.aui.AUI_NB_CLOSE_BUTTON|wx.aui.AUI_NB_SCROLL_BUTTONS)
        
        page = DemoTree(self, size=(100,400))
        self.AddPage(page, "Stuff", bitmap=self.getBitmap())

        for num in range(1, 8):
            page = wx.TextCtrl(self, -1, "This is page %d" % num ,
                               style=wx.TE_MULTILINE)
            self.addTab(page, "Page %d" % num)
            
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.OnTabChanged)

    def getBitmap(self):
        img=wx.ImageFromBitmap(wx.Bitmap("icons/py.ico"))
        img.Rescale(16,16)
        bitmap=wx.BitmapFromImage(img)
        return bitmap

    def addTab(self,win,title):
        self.AddPage(win, title, bitmap=self.getBitmap())

    def OnTabChanged(self, evt):
        newpage=evt.GetSelection()
        dprint("changing to %s" % newpage)
        page=self.GetPage(newpage)
        dprint("page: %s" % page)
        evt.Skip()


#-------------------------------------------------------------------

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

        # tell FrameManager to manage this frame        
        self._mgr = wx.aui.AuiManager()
        self._mgr.SetManagedWindow(self)
        
        self.win = MyNotebook(self)
        self._mgr.AddPane(self.win, wx.aui.AuiPaneInfo().Name("notebook").
                          CenterPane())
        self.minortabs = MinorNotebook(self,size=(100,400))
        self._mgr.AddPane(self.minortabs, wx.aui.AuiPaneInfo().Name("minor").
                          Caption("Stuff").Right())
        self.tree = DemoTree(self,size=(100,400))
        self._mgr.AddPane(self.tree, wx.aui.AuiPaneInfo().Name("funclist").
                          Caption("Function List").Right())

        # Prepare the menu bar
        self.settings={'asteroids':False,
                       'inner planets':True,
                       'outer planets':True,
                       'major mode':'Fundamental',
                       'perspectives':{},
                       'default perspective':None
                       }
        
        self.SetMenuBar(wx.MenuBar())
        self.setMenumap()
        self.toolmap=None
        self.setToolmap()
        
        self.settings['default perspective'] = self._mgr.SavePerspective()
        
        # "commit" all changes made to FrameManager   
        self._mgr.Update()

    # Methods
    def OnClose(self, evt=None):
        dprint(evt)
        FrameList.remove(self)
        self.Destroy()

    def Raise(self):
        wx.Frame.Raise(self)
        self.win.SetFocus()
        
    def setMenumap(self,majormode=None,minormodes=[]):
        comp_mgr=ComponentManager()
        menuloader=MenuItemLoader(comp_mgr)
        self.menumap=menuloader.load(self,majormode,minormodes)

    def setToolmap(self,majormode=None,minormodes=[]):
        if self.toolmap is not None:
            for tb in self.toolmap.toolbars:
                self._mgr.DetachPane(tb)
                tb.Destroy()
                
        comp_mgr=ComponentManager()
        toolloader=ToolBarItemLoader(comp_mgr)
        self.toolmap=toolloader.load(self,majormode,minormodes)

        for tb in self.toolmap.toolbars:
            tb.Realize()
            self._mgr.AddPane(tb, wx.aui.AuiPaneInfo().
                              Name(tb.label).Caption(tb.label).
                              ToolbarPane().Top().
                              LeftDockable(False).RightDockable(False))
        
    def switchMode(self,mode,last):
        if last not in self.settings['perspectives']:
            dprint("saving settings for mode %s" % last)
            self.settings['perspectives'][last] = self._mgr.SavePerspective()
        
        self.dprint("Switching to mode %s" % mode)
        self.settings['major mode']=mode
        self.setMenumap(mode)
        self.setToolmap(mode)

        if mode in self.settings['perspectives']:
            self._mgr.LoadPerspective(self.settings['perspectives'][mode])
            dprint(self.settings['perspectives'][mode])
        else:
            # This doesn't exactly work because anything not named in
            # the default perspective listing won't be shown.  Need to
            # find a way to determine which panes are new and show
            # them.
            self._mgr.LoadPerspective(self.settings['default perspective'])
            all_panes = self._mgr.GetAllPanes()
            for pane in xrange(len(all_panes)):
                all_panes[pane].Show()
            self._mgr.Update()
            

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

