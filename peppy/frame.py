# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
import os, re, threading
from cStringIO import StringIO

import wx
import wx.aui
import wx.stc

from peppy.menu import *
from peppy.lib.wxemacskeybindings import *
from peppy.lib.iconstorage import *
from peppy.lib.controls import *
from peppy.lib.userparams import *

from peppy.configprefs import *
from peppy.stcinterface import *
from peppy.iofilter import *
from peppy.major import *
from peppy.sidebar import *
from peppy.debug import *
from peppy.buffers import *

    
class FrameList(GlobalList):
    debuglevel=0
    name="Frames"

    storage=[]
    others=[]
    
    @classmethod
    def getFrames(self):
        return [frame for frame in FrameList.storage]

    def getItems(self):
        return [frame.getTitle() for frame in FrameList.storage]

    def action(self, index=0):
        assert self.dprint("top window to %d: %s" % (index,FrameList.storage[index]))
        wx.GetApp().SetTopWindow(FrameList.storage[index])
        wx.CallAfter(FrameList.storage[index].Raise)

class DeleteFrame(SelectAction):
    alias = _("delete-frame")
    name = _("&Delete Frame")
    tooltip = _("Delete current window")
    
    def action(self, index=-1):
        self.frame.closeWindow(None)

    def isEnabled(self):
        if len(FrameList.storage)>1:
            return True
        return False

class NewFrame(SelectAction):
    alias = _("new-frame")
    name = _("&New Frame")
    tooltip = _("Open a new window")
    key_bindings = {'emacs': "C-X 5 2",}
    
    def action(self, index=-1):
        frame=BufferFrame()
        frame.Show(True)


class MyNotebook(wx.aui.AuiNotebook,debugmixin):
    debuglevel = 0
    
    def __init__(self, parent, size=wx.DefaultSize):
        wx.aui.AuiNotebook.__init__(self, parent, size=size, style=wx.aui.AUI_NB_WINDOWLIST_BUTTON|wx.aui.AUI_NB_TAB_MOVE|wx.aui.AUI_NB_TAB_SPLIT|wx.aui.AUI_NB_CLOSE_BUTTON|wx.aui.AUI_NB_SCROLL_BUTTONS, pos=(9000,9000))
        
        self.frame=parent
        self.lastActivePage=None
        
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.OnTabChanged)
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.OnTabClosed)

    def OnTabChanged(self, evt):
        newpage = evt.GetSelection()
        oldpage = evt.GetOldSelection()
        assert self.dprint("changing from tab %s to %s" % (oldpage, newpage))
        if oldpage>0:
            self.lastActivePage=self.GetPage(oldpage)
        else:
            self.lastActivePage=None
        page=self.GetPage(newpage)
        wx.CallAfter(self.frame.switchMode)
        evt.Skip()

    def OnTabClosed(self, evt):
        index = evt.GetSelection()
        mode = self.GetPage(index)
        assert self.dprint("closing tab # %d: mode %s" % (index,mode))
        mode.deleteWindowPre()
        if self.GetPageCount() == 1:
            wx.CallAfter(self.frame.open, "about:blank")
        evt.Skip()

    def closeTab(self, mode):
        assert self.dprint("closing tab: mode %s" % mode)
        index=self.GetPageIndex(mode)
        self.RemovePage(index)
        mode.deleteWindow()
        if self.GetPageCount() == 0:
           self.frame.open("about:blank")

    def addTab(self,mode):
        before = self.GetPageCount()
        assert self.dprint("#tabs = %d.  Adding mode %s" % (before, mode))
        self.AddPage(mode, mode.getTabName(), bitmap=getIconBitmap(mode.icon))
        index=self.GetPageIndex(mode)
        self.SetSelection(index)
        if before==0:
            # If this is the first tab added, a tab changed event
            # won't be generated, so we have to call switchMode
            # ourselves.
            self.frame.switchMode()
        
    def replaceCurrentTab(self,mode):
        index=self.GetSelection()
        if index<0:
            self.addTab(mode)
        else:
            assert self.dprint("Replacing tab %s at %d with %s" % (self.GetPage(index), index, mode))
            self.InsertPage(index, mode, mode.getTabName(), bitmap=getIconBitmap(mode.icon))
            oldmode=self.GetPage(index+1)
            self.RemovePage(index+1)
            if oldmode:
                oldmode.deleteWindow()
                #del oldmode
            self.SetSelection(index)

    def replaceTab(self, oldmode, newmode):
        index = self.GetPageIndex(oldmode)
        if index == wx.NOT_FOUND:
            self.addTab(newmode)
        else:
            assert self.dprint("Replacing tab %s at %d with %s" % (self.GetPage(index), index, newmode))
            self.InsertPage(index, newmode, newmode.getTabName(), bitmap=getIconBitmap(newmode.icon))
            oldmode=self.GetPage(index+1)
            self.RemovePage(index+1)
            if oldmode:
                oldmode.deleteWindow()
                #del oldmode
            self.SetSelection(index)            
        
    def getCurrent(self):
        index = self.GetSelection()
        if index<0:
            return None
        return self.GetPage(index)

    def getPrevious(self):
        return self.lastActivePage

    def updateTitle(self,mode):
        index=self.GetPageIndex(mode)
        if index>=0:
            self.SetPageText(index,mode.getTabName())

    def getAll(self):
        pages = []
        for index in range(0, self.GetPageCount()):
            pages.append(self.GetPage(index))
        return pages


## BufferFrames

class FrameDropTarget(wx.FileDropTarget, debugmixin):
    def __init__(self, frame):
        wx.FileDropTarget.__init__(self)
        self.frame = frame

    def OnDropFiles(self, x, y, filenames):
        assert self.dprint("%d file(s) dropped at %d,%d:" % (len(filenames),
                                                             x, y))

        for filename in filenames:
            assert self.dprint("filename='%s'" % filename)
            self.frame.open(filename)


class BufferFrame(wx.Frame, ClassPrefs, debugmixin):
    debuglevel=0
    frameid=0
    
    perspectives={}

    default_classprefs = (
        IntParam('width', 800),
        IntParam('height', 600),
        StrParam('sidebars', ''),
        BoolParam('show_toolbar', True),
        )

    def __init__(self, urls=[], id=-1):
        BufferFrame.frameid+=1
        self.name="peppy: Frame #%d" % BufferFrame.frameid

        size=(int(self.classprefs.width),int(self.classprefs.height))
        wx.Frame.__init__(self, None, id=-1, title=self.name, pos=wx.DefaultPosition, size=size, style=wx.DEFAULT_FRAME_STYLE|wx.CLIP_CHILDREN)
        icon = wx.EmptyIcon()
        icon.CopyFromBitmap(getIconBitmap('icons/peppy.png'))
        self.SetIcon(icon)

        FrameList.append(self)
        
        self.Bind(wx.EVT_CLOSE,self.OnClose)
        
        self.CreateStatusBar()
        self.SetStatusText("This is the statusbar")

        # tell FrameManager to manage this frame        
        self._mgr = wx.aui.AuiManager()
        self._mgr.SetManagedWindow(self)

        self.tabs = MyNotebook(self)
        self._mgr.AddPane(self.tabs, wx.aui.AuiPaneInfo().Name("notebook").
                          CenterPane())
        self.sidebar_panes = []
        
        self.SetMenuBar(wx.MenuBar())
        self.menumap=None
        self.toolmap=None
        self.show_toolbar = self.classprefs.show_toolbar
        
        self.keys=KeyProcessor(self)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)

        self.loadSidebars()

        self.dropTarget=FrameDropTarget(self)
        self.SetDropTarget(self.dropTarget)        
        
        Publisher().subscribe(self.pluginsChanged, 'peppy.plugins.changed')
        wx.GetApp().SetTopWindow(self)

        dprint(urls)
        
        # counter to make sure the title buffer is shown if we attempt
        # to load files and they all fail.
        self.initial_load = 0
        self.loadList(urls)

    def loadList(self, urls):
        if urls:
            for url in urls:
                dprint("Opening %s" % url)
                wx.CallAfter(self.open, url)
                self.initial_load += 1
        else:
            wx.CallAfter(self.titleBuffer)
        
    def addPane(self, win, paneinfo):
        self._mgr.AddPane(win, paneinfo)

    def loadSidebars(self):
        sidebar_list = self.classprefs.sidebars
        assert self.dprint(sidebar_list)
        if sidebar_list is not None:
            sidebar_names = sidebar_list.split(',')
            assert self.dprint("loading %s" % sidebar_names)
            sidebars = Sidebar.getClasses(self,sidebar_names)
            for sidebarcls in sidebars:
                self.createSidebar(sidebarcls)
            self.createSidebarList()

    def createSidebar(self, sidebarcls):
        """Create the sidebar and register it with the frame's AUI
        Manager."""

        sidebar = sidebarcls(self)
        paneinfo = sidebar.getPaneInfo()
        self._mgr.AddPane(sidebar, paneinfo)
        sidebar.paneinfo = self._mgr.GetPane(sidebar)

    def createSidebarList(self):
        self.sidebar_panes = []
        sidebars = self._mgr.GetAllPanes()
        for sidebar in sidebars:
            assert self.dprint("name=%s caption=%s window=%s state=%s" % (sidebar.name, sidebar.caption, sidebar.window, sidebar.state))
            if sidebar.name != "notebook":
                self.sidebar_panes.append(sidebar)
        self.sidebar_panes.sort(key=lambda s:s.caption)


    # Overrides of wx methods
    def OnClose(self, evt=None):
        assert self.dprint(evt)
        if len(FrameList.storage)==1:
            wx.CallAfter(Publisher().sendMessage, 'peppy.request.quit')
        else:
            FrameList.remove(self)
            self.Destroy()

    def OnKeyPressed(self, evt):
        self.keys.process(evt)
##        if function:
##            print "num=%d function=%s" % (num,function)
##        else:
##            print "unprocessed by KeyProcessor"

    def Raise(self):
        wx.Frame.Raise(self)
        major=self.getActiveMajorMode()
        if major is not None:
            major.SetFocus()
        
    def CreateStatusBar(self):
        self.statusbar=PeppyStatusBar(self)
        self.SetStatusBar(self.statusbar)

    # non-wx methods

    def setStatusBar(self):
        #self.statusbar.reset()
        oldbar = self.GetStatusBar()
        oldbar.Hide()
        mode=self.getActiveMajorMode()
        if mode is not None:
            bar = mode.getStatusBar()
        else:
            bar = self.statusbar
        self.SetStatusBar(bar)
        bar.Show()
    
    def setKeys(self,majormodes=[],minormodes=[]):
        keymap=UserInterfaceLoader.loadKeys(self,majormodes,minormodes)
        self.keys.setGlobalKeyMap(keymap)
        self.keys.clearMinorKeyMaps()
        
    def setMenumap(self,majormodes=[],minormodes=[]):
        #MenuItemLoader.debuglevel=1
        #MenuBarActionMap.debuglevel=1
        self.menumap=UserInterfaceLoader.loadMenu(self,majormodes,minormodes)
        self.keys.addMinorKeyMap(self.menumap.keymap)
        #get_all_referrers(SelectAction)

    enablecount = 0
    def enableTools(self):
        """Enable toolbar buttons.

        Fixed bug?  Originally, the enabling of individual toolbar
        buttons was accomplished using the EVT_UPDATE_UI event on the
        toolbar button itself.  When deleting toolbars, that caused a
        crash because one toolbar button was getting its enable method
        called after the toolbar was destroyed.  By moving the toolbar
        enabling out of there and into here, the crash was eliminated.
        This is called using the STC_UPDATEUI event now.  I think this
        is more efficient, anyway.
        """
        if not self.show_toolbar:
            return
        
        BufferFrame.enablecount += 1
        count = BufferFrame.enablecount
        #print
        #print
        #print
        assert self.dprint("---------- %d id=%s" % (count, id(self.toolmap)))

        current = self.getActiveMajorMode()
        if len(self.toolmap.actions) > 0:
            if self.toolmap.actions[0].mode != current:
                # Now that I'm saving the major mode in each action,
                # it's possible that some old actions can be hanging
                # around before the next event is processed that
                # creates the new major mode.
                #dprint("FOUND OLD MODE!!!! ABORTING!!!")
                return
            
            for action in self.toolmap.actions:
                assert self.dprint("%d action=%s action.tool=%s" % (count, action,action.tool))
                action.Enable()

    def setToolmap(self,majormodes=[],minormodes=[]):
        if self.toolmap is not None:
            for action in self.toolmap.actions:
                action.remove()
            assert self.dprint(self.toolmap.actions)
            for tb in self.toolmap.toolbars:
                self._mgr.DetachPane(tb)
                tb.Destroy()

        if self.show_toolbar:
            self.toolmap=UserInterfaceLoader.loadToolbar(self,majormodes,minormodes)
            self.keys.addMinorKeyMap(self.toolmap.keymap)

            for tb in self.toolmap.toolbars:
                tb.Realize()
                self._mgr.AddPane(tb, wx.aui.AuiPaneInfo().
                                  Name(tb.label).Caption(tb.label).
                                  ToolbarPane().Top().
                                  LeftDockable(False).RightDockable(False))
        else:
            self.toolmap = None
        
    def getActiveMajorMode(self):
        major=self.tabs.getCurrent()
        return major

    def getAllMajorModes(self):
        modes = self.tabs.getAll()
        return modes
    
    def isOpen(self):
        major=self.getActiveMajorMode()
            #assert self.dprint("major=%s isOpen=%s" % (str(major),str(major!=None)))
        return major is not None

    def isTopWindow(self):
        return wx.GetApp().GetTopWindow()==self

    def close(self):
        major=self.getActiveMajorMode()
        if major:
            buffer=major.buffer
            if buffer.permanent:
                self.tabs.closeTab(major)
            else:
                wx.GetApp().close(buffer)

    def setTitle(self):
        major=self.getActiveMajorMode()
        if major:
            self.SetTitle("peppy: %s" % major.getTabName())
        else:
            self.SetTitle("peppy")

    def showModified(self,major):
        current=self.getActiveMajorMode()
        if current:
            self.setTitle()
        self.tabs.updateTitle(major)

    def createMajorMode(self, buffer, requested=None):
        if not requested:
            requested = buffer.defaultmode
        mode = requested(buffer, self)
        buffer.addViewer(mode)
        return mode

    def setBuffer(self,buffer):
        # this gets a default view for the selected buffer
        mode=self.createMajorMode(buffer)
        assert self.dprint("setting buffer to new view %s" % mode)
        self.tabs.replaceCurrentTab(mode)

    def changeMajorMode(self, requested):
        mode = self.getActiveMajorMode()
        if mode:
            newmode = self.createMajorMode(mode.buffer, requested)
            assert self.dprint("new mode=%s" % newmode)
            self.tabs.replaceCurrentTab(newmode)

    def newBuffer(self,buffer):
        mode=self.createMajorMode(buffer)
        assert self.dprint("major mode=%s" % mode)
        current = self.getActiveMajorMode()
        if current and current.temporary:
            self.tabs.replaceCurrentTab(mode)
        else:
            self.tabs.addTab(mode)
        assert self.dprint("after addViewer")

    def titleBuffer(self):
        self.open(wx.GetApp().classprefs.title_page)

    def isTitleBufferOnly(self):
        if len(self.getAllMajorModes()) > 1:
            return False
        mode = self.getActiveMajorMode()
        url = URLInfo(wx.GetApp().classprefs.title_page)
        dprint("%s == %s => %s" % (url, mode.buffer.url, mode.buffer.url == url))
        if mode.buffer.url == url:
            return True
        return False

    def open(self, url):
        buffer = BufferList.findBufferByURL(url)
        if buffer is not None and buffer.permanent:
            #dprint("found permanent buffer")
            self.newBuffer(buffer)
        else:
            if not isinstance(url, URLInfo):
                url = URLInfo(url)
            try:
                modecls = MajorModeMatcherDriver.match(url)
            except Exception, e:
                self.openFailure(url, str(e))
                return
            
            if modecls.allow_threaded_loading:
                buffer = LoadingBuffer(url, modecls)
                self.newBuffer(buffer)
            else:
                self.openStart(url, modecls, threaded=False)

    def openStart(self, url, modecls, mode_to_replace=None, threaded=True):
        buffer = Buffer(url, modecls)
        buffer.openGUIThreadStart()
        if threaded and wx.GetApp().classprefs.load_threaded:
            statusbar = mode_to_replace.getStatusBar()
            statusbar.startProgress("Loading %s" % url, message=str(mode_to_replace))
            thread = BufferLoadThread(self, buffer, mode_to_replace, statusbar)
        else:
            wx.SetCursor(wx.StockCursor(wx.CURSOR_WATCH))
            try:
                buffer.openBackgroundThread()
                self.openSuccess(buffer, mode_to_replace)
            except Exception, e:
                self.openFailure(buffer.url, str(e))
            wx.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))

    def openSuccess(self, buffer, mode_to_replace=None, progress=None):
        buffer.openGUIThreadSuccess()
        BufferList.addBuffer(buffer)
        mode = self.createMajorMode(buffer)
        assert self.dprint("major mode=%s" % mode)
        if mode_to_replace:
            self.tabs.replaceTab(mode_to_replace, mode)
        else:
            current = self.getActiveMajorMode()
            if current and current.temporary:
                self.tabs.replaceCurrentTab(mode)
            else:
                self.tabs.addTab(mode)
        assert self.dprint("after addViewer")
        msg = mode.getWelcomeMessage()
        if progress:
            progress.stopProgress(msg)
        else:
            self.SetStatusText(msg)

    def openFailure(self, url, error, progress=None):
        msg = "Failed opening %s.\n" % url
        Publisher().sendMessage('peppy.log.error', msg)
        Publisher().sendMessage('peppy.log.error', error + "\n")
        if progress:
            progress.stopProgress(msg)
        else:
            self.SetStatusText(msg)

        if self.initial_load > 0:
            self.initial_load -= 1
            if self.initial_load == 0:
                self.titleBuffer()

    def save(self):        
        mode=self.getActiveMajorMode()
        if mode and mode.buffer:
            mode.buffer.save()

    def cwd(self):
        """Get working filesystem directory for current mode.

        Convenience function to get working directory of the current
        mode.
        """
        mode = self.getActiveMajorMode()
        if mode and mode.buffer:
            cwd = mode.buffer.cwd()
        else:
            cwd=os.getcwd()
        return cwd
            
    def switchMode(self):
        last=self.tabs.getPrevious()
        mode=self.getActiveMajorMode()
        if mode is None:
            # If there were multiple tabs open and they were all the
            # same, they will go away when the buffer is closed.  In
            # this case, don't try to do anything more because there
            # isn't a mode that's left associated with this frame
            return

        assert self.dprint("Switching from mode %s to mode %s" % (last,mode))

        hierarchy=getSubclassHierarchy(mode,MajorMode)
        assert self.dprint("Mode hierarchy: %s" % hierarchy)
        # Get the major mode names for the hierarchy (but don't
        # include the last one which is the abstract MajorMode)
        majors=[m.keyword for m in hierarchy[:-1]]
        assert self.dprint("Major mode names: %s" % majors)
        
##        if last:
##            assert self.dprint("saving settings for mode %s" % last)
##            BufferFrame.perspectives[last.buffer.filename] = self._mgr.SavePerspective()
        
        mode.focus()
        self.setTitle()
        self.setKeys(majors)
        self.setMenumap(majors)
        self.setToolmap(majors)
        self.setStatusBar()

##        if mode.buffer.filename in BufferFrame.perspectives:
##            self._mgr.LoadPerspective(BufferFrame.perspectives[mode.buffer.filename])
##            assert self.dprint(BufferFrame.perspectives[mode.buffer.filename])
##        else:
##            if 'default perspective' in self.tempsettings:
##                # This doesn't exactly work because anything not named in
##                # the default perspective listing won't be shown.  Need to
##                # find a way to determine which panes are new and show
##                # them.
##                self._mgr.LoadPerspective(self.tempsettings['default perspective'])
##                all_panes = self._mgr.GetAllPanes()
##                for pane in xrange(len(all_panes)):
##                    all_panes[pane].Show()
##            else:
##                self.tempsettings['default perspective'] = self._mgr.SavePerspective()
        
        # "commit" all changes made to FrameManager   
        self._mgr.Update()
        wx.CallAfter(self.enableTools)

    def getAllModes(self):
        modes = []
        for index in range(self.tabs.GetPageCount()):
            page = self.tabs.GetPage(index)
            modes.append(page.__class__)
        return modes

    def pluginsChanged(self, msg):
        """Update the display after plugins changed, because it might
        affect the menu or toolbar if new plugins were activated or
        existing ones were deactivated.
        """
        # FIXME: check to make sure that any major modes currently in
        # use haven't been deactivated.  If so, force them to be
        # enabled again.  Or, perhaps check before disabling.

        # FIXME: what to do in the case of a classpref changing that
        # affects an attribute?  E.g. if classpref.show_toolbar
        # changes, should self.show_toolbar also change?  Or, prompt
        # the user to say "global setting <blah> has changed.  Update
        # all instances?"
        self.switchMode()

    def getTitle(self):
        return self.name
