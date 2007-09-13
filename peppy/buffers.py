# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
import os,re

import wx
import wx.aui
import wx.stc

from menu import *
from lib.wxemacskeybindings import *
from lib.iconstorage import *
from lib.controls import *

from cStringIO import StringIO

from configprefs import *
from stcinterface import *
from iofilter import *
from major import *
from sidebar import SidebarLoader
from debug import *
from trac.core import *
from dialogs import *

class BufferList(GlobalList):
    debuglevel=0
    name="Buffers"

    storage=[]
    others=[]
    
    def getItems(self):
        return [buf.name for buf in BufferList.storage]

    def action(self,state=None,index=0):
        assert self.dprint("top window to %d: %s" % (index,BufferList.storage[index]))
        self.frame.setBuffer(BufferList.storage[index])
    
class FrameList(GlobalList):
    debuglevel=0
    name="Frames"

    storage=[]
    others=[]
    
    def getItems(self):
        return [frame.getTitle() for frame in FrameList.storage]

    def action(self,state=None,index=0):
        assert self.dprint("top window to %d: %s" % (index,FrameList.storage[index]))
        self.frame.app.SetTopWindow(FrameList.storage[index])
        wx.CallAfter(FrameList.storage[index].Raise)
    


class DeleteFrame(SelectAction):
    name = "&Delete Frame"
    tooltip = "Delete current window"
    
    def action(self, pos=-1):
        self.frame.closeWindow(None)

    def isEnabled(self):
        if len(FrameList.storage)>1:
            return True
        return False

class NewFrame(SelectAction):
    name = "&New Frame"
    tooltip = "Open a new window"
    key_bindings = {'emacs': "C-X 5 2",}
    
    def action(self, pos=-1):
        frame=self.frame.app.newFrame(callingFrame=self.frame)
        frame.titleBuffer()
        frame.Show(True)

#### Buffers


class IBufferOpenPostHook(Interface):
    """
    Used to add new hook after a buffer has been successfully opened
    and the data read in..
    """

    def openPostHook(buffer):
        """
        Method to manipulate the buffer after the buffer has been
        loaded.
        """

class BufferHooks(Component):
    openPostHooks=ExtensionPoint(IBufferOpenPostHook)

    def openPostHook(self,buffer):
        for hook in self.openPostHooks:
            hook.openPostHook(buffer)



class Buffer(debugmixin):
    count=0
    debuglevel=0

    filenames={}
    
    def __init__(self,url=None,fh=None,mystc=None,stcparent=None,defaultmode=None):
        Buffer.count+=1
        self.busy = False
        self.readonly = False
        self.defaultmode=defaultmode

        self.guessBinary=False
        self.guessLength=1024
        self.guessPercentage=10

        self.viewer=None
        self.viewers=[]

        self.modified=False

        if mystc:
            self.initSTC(mystc,stcparent)
        else:
            # defer STC initialization until we know the subclass
            self.stc=None

        self.open(url, stcparent)

    def initSTC(self):
        self.stc.Bind(wx.stc.EVT_STC_CHANGE, self.OnChanged)

    def createMajorMode(self,frame,modeclass=None):
        if modeclass:
            viewer=modeclass(self,frame)
        else:
            viewer=self.defaultmode(self,frame) # create new view
        self.viewers.append(viewer) # keep track of views
        assert self.dprint("views of %s: %s" % (self,self.viewers))
        return viewer

    def remove(self,view):
        assert self.dprint("removing view %s of %s" % (view,self))
        if view in self.viewers:
            self.viewers.remove(view)
            if issubclass(view.stc.__class__, PeppySTC) and view.stc != self.stc:
                self.stc.removeSubordinate(view.stc)
        else:
            raise ValueError("Bug somewhere.  Major mode %s not found in Buffer %s" % (view,self))
        assert self.dprint("views remaining of %s: %s" % (self,self.viewers))

    def removeAllViews(self):
        # Have to make a copy of self.viewers, because when the viewer
        # closes itself, it removes itself from this list of viewers,
        # so unless you make a copy the for statement is operating on
        # a changing list.
        viewers=self.viewers[:]
        for viewer in viewers:
            assert self.dprint("count=%d" % len(self.viewers))
            assert self.dprint("removing view %s of %s" % (viewer,self))
            viewer.frame.tabs.closeTab(viewer)
        assert self.dprint("final count=%d" % len(self.viewers))

    def setURL(self, url):
        if not url:
            url=URLInfo("file://untitled")
        self.url = url
        basename=url.getBasename()
        if basename in self.filenames:
            count=self.filenames[basename]+1
            self.filenames[basename]=count
            self.displayname=basename+"<%d>"%count
        else:
            self.filenames[basename]=1
            self.displayname=basename
        self.readonly = url.readonly
        self.name="Buffer #%d: %s" % (self.count,str(self.url))

        # Update UI because the filename associated with this buffer
        # may have changed and that needs to be reflected in the menu.
        BufferList.update()
        
    def getFilename(self):
        return self.url.path

    def cwd(self):
        if self.url.protocol == 'file':
            path = os.path.dirname(self.url.path)
        else:
            path = os.getcwd()
        return path
            
    def getTabName(self):
        if self.modified:
            return "*"+self.displayname
        return self.displayname

    def open(self, urlstring, stcparent):
        url = URLInfo(urlstring)
        dprint("url: %s" % repr(url))
        self.defaultmode = MajorModeMatcherDriver.match(url)
        dprint("mode=%s" % (str(self.defaultmode)))

        self.stc = self.defaultmode.stc_class(stcparent)
        self.stc.open(url)

        # if no exceptions, it must have worked.
        self.setURL(url)

        if isinstance(self.stc,PeppySTC):
            self.initSTC()

        self.modified=False
        self.stc.EmptyUndoBuffer()

        BufferHooks(ComponentManager()).openPostHook(self)
    
    def revert(self):
        fh=self.url.getReader()
        self.stc.ClearAll()
        self.stc.readFrom(fh)
        self.modified=False
        self.stc.EmptyUndoBuffer()
        wx.CallAfter(self.showModifiedAll)  
        
    def save(self, url=None):
        assert self.dprint("Buffer: saving buffer %s" % (self.url))
        try:
            if url is None:
                saveas=self.url
            else:
                saveas=URLInfo(url)
            fh=saveas.getWriter()
            self.stc.writeTo(fh)
            fh.close()
            self.stc.SetSavePoint()
            self.modified=False
            self.readonly = False
            if url is not None and url!=self.url:
                self.setURL(saveas)
            self.showModifiedAll()
        except:
            print "Buffer: failed writing!"
            raise

    def showModifiedAll(self):
        for view in self.viewers:
            assert self.dprint("notifing: %s modified = %s" % (view, self.modified))
            view.showModified(self.modified)
        wx.GetApp().enableFrames()

    def setBusy(self, state):
        self.busy = state
        for view in self.viewers:
            assert self.dprint("notifing: %s busy = %s" % (view, self.busy))
            view.showBusy(self.busy)
        wx.GetApp().enableFrames()

    def OnChanged(self, evt):
        if self.stc.GetModify():
            assert self.dprint("modified!")
            changed=True
        else:
            assert self.dprint("clean!")
            changed=False
        if changed!=self.modified:
            self.modified=changed
            wx.CallAfter(self.showModifiedAll)
        



class MyNotebook(wx.aui.AuiNotebook,debugmixin):
    debuglevel = 0
    
    def __init__(self, parent, size=wx.DefaultSize):
        wx.aui.AuiNotebook.__init__(self, parent, size=size, style=wx.aui.AUI_NB_WINDOWLIST_BUTTON|wx.aui.AUI_NB_TAB_MOVE|wx.aui.AUI_NB_TAB_SPLIT|wx.aui.AUI_NB_CLOSE_BUTTON|wx.aui.AUI_NB_SCROLL_BUTTONS)
        
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
        evt.Skip()

    def closeTab(self, mode):
        assert self.dprint("closing tab: mode %s" % mode)
        index=self.GetPageIndex(mode)
        self.RemovePage(index)
        mode.deleteWindow()

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
        
    def replaceTab(self,mode):
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


class BufferFrame(wx.Frame,ClassSettings,debugmixin):
    debuglevel=0
    frameid=0
    perspectives={}

    default_settings = {}
    
    def __init__(self, app, id=-1):
        BufferFrame.frameid+=1
        self.name="peppy: Frame #%d" % BufferFrame.frameid

        size=(int(self.settings.width),int(self.settings.height))
        wx.Frame.__init__(self, None, id=-1, title=self.name, pos=wx.DefaultPosition, size=size, style=wx.DEFAULT_FRAME_STYLE|wx.CLIP_CHILDREN)
        icon = wx.EmptyIcon()
        icon.CopyFromBitmap(getIconBitmap('icons/peppy.png'))
        self.SetIcon(icon)
        self.app=app

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
        
        self.keys=KeyProcessor(self)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)

        self.loadSidebars()

        self.dropTarget=FrameDropTarget(self)
        self.SetDropTarget(self.dropTarget)        
        
        self.app.SetTopWindow(self)
        
    def addPane(self, win, paneinfo):
        self._mgr.AddPane(win, paneinfo)

    def loadSidebars(self):
        sidebar_list = self.settings.sidebars
        assert self.dprint(sidebar_list)
        if sidebar_list is not None:
            sidebar_names = sidebar_list.split(',')
            assert self.dprint("loading %s" % sidebar_names)
            sidebars = SidebarLoader(ComponentManager()).getClasses(self,sidebar_names)
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
            wx.CallAfter(self.app.quit)
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
        comp_mgr=ComponentManager()
        keyloader=KeyboardItemLoader(comp_mgr)
        keymap=keyloader.load(self,majormodes,minormodes)
        self.keys.setGlobalKeyMap(keymap)
        self.keys.clearMinorKeyMaps()
        
    def setMenumap(self,majormodes=[],minormodes=[]):
        comp_mgr=ComponentManager()
        menuloader=MenuItemLoader(comp_mgr)
        #MenuItemLoader.debuglevel=1
        #MenuBarActionMap.debuglevel=1
        self.menumap=menuloader.load(self,majormodes,minormodes)
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
        BufferFrame.enablecount += 1
        count = BufferFrame.enablecount
        #print
        #print
        #print
        assert self.dprint("---------- %d id=%s" % (count, id(self.toolmap)))
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
                
        comp_mgr=ComponentManager()
        toolloader=ToolBarItemLoader(comp_mgr)
        self.toolmap=toolloader.load(self,majormodes,minormodes)
        self.keys.addMinorKeyMap(self.toolmap.keymap)

        for tb in self.toolmap.toolbars:
            tb.Realize()
            self._mgr.AddPane(tb, wx.aui.AuiPaneInfo().
                              Name(tb.label).Caption(tb.label).
                              ToolbarPane().Top().
                              LeftDockable(False).RightDockable(False))
        
    def getActiveMajorMode(self):
        major=self.tabs.getCurrent()
        return major
    
    def isOpen(self):
        major=self.getActiveMajorMode()
            #assert self.dprint("major=%s isOpen=%s" % (str(major),str(major!=None)))
        return major is not None

    def isTopWindow(self):
        return self.app.GetTopWindow()==self

    def close(self):
        major=self.getActiveMajorMode()
        if major:
            buffer=major.buffer
            self.app.close(buffer)

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

    def setBuffer(self,buffer):
        # this gets a default view for the selected buffer
        mode=buffer.createMajorMode(self)
        assert self.dprint("setting buffer to new view %s" % mode)
        self.tabs.replaceTab(mode)

    def changeMajorMode(self,requested):
        mode=self.getActiveMajorMode()
        if mode:
            newmode=mode.buffer.createMajorMode(self,requested)
            assert self.dprint("new mode=%s" % newmode)
            self.tabs.replaceTab(newmode)

    def newBuffer(self,buffer):
        mode=buffer.createMajorMode(self)
        assert self.dprint("major mode=%s" % mode)
        self.tabs.addTab(mode)
        assert self.dprint("after addViewer")

    def titleBuffer(self):
        self.open('about:peppy')
        
    def open(self,url,newTab=True,mode=None):
        try:
            buffer=Buffer(url,stcparent=self.app.dummyframe,defaultmode=mode)
            # If we get an exception, it won't get added to the buffer list
        
            mode=self.getActiveMajorMode()
            self.app.addBuffer(buffer)
            if not newTab or (mode is not None and mode.temporary):
                self.setBuffer(buffer)
            else:
                self.newBuffer(buffer)
                mode=self.getActiveMajorMode()
                msg=mode.getWelcomeMessage()
        except Exception, e:
            import traceback
            traceback.print_exc()
            msg = "Failed opening %s" % url
            Publisher().sendMessage('peppy.log.error', msg)
        self.SetStatusText(msg)

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

    def getTitle(self):
        return self.name





class BufferApp(wx.App,debugmixin):
    def OnInit(self):
        self.menu_actions=[]
        self.toolbar_actions=[]
        self.keyboard_actions=[]
        self.bufferhandlers=[]
        
        self.confdir=None
        self.cfgfile=None

        self.globalKeys=KeyMap()

        # the Buffer objects have an stc as the base, and they need a
        # frame in which to work.  So, we create a dummy frame here
        # that is never shown.
        self.dummyframe=wx.Frame(None)
        self.dummyframe.Show(False)

        self.errors=[]

    def addBuffer(self,buffer):
        BufferList.append(buffer)

    def removeBuffer(self,buffer):
        BufferList.remove(buffer)

    def deleteFrame(self,frame):
        #self.pendingframes.append((self.frames.getid(frame),frame))
        #self.frames.remove(frame)
        pass
    
    def newFrame(self,callingFrame=None):
        frame=BufferFrame(self)
        return frame
        
    def showFrame(self,frame):
        frame.Show(True)

    def getTopFrame(self):
        frame = self.GetTopWindow()
        if not isinstance(frame, BufferFrame):
            # FIXME: can this ever happen?
            dprint("Top window not a BufferFrame!")
            for frame in wx.GetTopLevelWindows():
                if isinstance(frame, BufferFrame):
                    return frame
            dprint("No top level BufferFrames found!")
        return frame
           
    def enableFrames(self):
        """Force all frames to update their enable status.

        Loop through each frame and force an update of the
        enable/disable state of ui items.  The menu does this in
        response to a user event, so this is really for the toolbar
        and other always-visible widgets that aren't automatically
        updated.
        """
        for frame in wx.GetTopLevelWindows():
            assert self.dprint(frame)
            try:
                frame.enableTools()
            except:
                # not all top level windows will be BufferFrame
                # subclasses, so just use the easy way out and catch
                # all exceptions.
                pass
            
    def close(self,buffer):
        if buffer.modified:
            dlg = wx.MessageDialog(self.GetTopWindow(), "%s\n\nhas unsaved changes.\n\nClose anyway?" % buffer.displayname, "Unsaved Changes", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION )
            retval=dlg.ShowModal()
            dlg.Destroy()
        else:
            retval=wx.ID_YES

        if retval==wx.ID_YES:
            buffer.removeAllViews()
            self.removeBuffer(buffer)

    def quit(self):
        assert self.dprint("prompt for unsaved changes...")
        unsaved=[]
        for buf in BufferList.storage:
            assert self.dprint("buf=%s modified=%s" % (buf,buf.modified))
            if buf.modified:
                unsaved.append(buf)
        if len(unsaved)>0:
            dlg = QuitDialog(self.GetTopWindow(), unsaved)
            retval=dlg.ShowModal()
            dlg.Destroy()
        else:
            retval=wx.ID_OK

        if retval==wx.ID_OK:
            doit=self.quitHook()
            if doit:
                self.ExitMainLoop()

    def quitHook(self):
        return True

    def loadPlugin(self, plugin, abort=True):
        """Import a plugin from a module name

        Given a module name (e.g. 'peppy.plugins.example_plugin',
        import the module and trap any import errors.

        @param: name of plugin to load
        """
        assert self.dprint("loading plugins from module=%s" % str(plugin))
        # FIXME: make abort's default state be dependent on some
        # configuration parameter
        if abort:
            mod=__import__(plugin)
        else:
            try:
                mod=__import__(plugin)
            except Exception,ex:
                print "couldn't load plugin %s" % plugin
                print ex
                self.errors.append("couldn't load plugin %s" % plugin)

    def loadPlugins(self,plugins):
        """Import a list of plugins.

        From either a list or a comma separated string, import a group
        of plugins.

        @param plugins: list or comma separated string of plugins to
        load
        """
        if not isinstance(plugins,list):
            plugins=[p.strip() for p in plugins.split(',')]
        for plugin in plugins:
            self.loadPlugin(plugin)

    def setConfigDir(self,dirname):
        self.confdir=dirname

    def getConfigFilePath(self,filename):
        c=HomeConfigDir(self.confdir)
        assert self.dprint("found home dir=%s" % c.dir)
        return os.path.join(c.dir,filename)

    def setInitialConfig(self,defaults={'Frame':{'width':400,
                                                 'height':400,
                                                 }
                                        }):
        GlobalSettings.setDefaults(defaults)

    def loadConfig(self,filename):
        self.setInitialConfig()
        filename=self.getConfigFilePath(filename)
        GlobalSettings.loadConfig(filename)

        self.loadConfigPostHook()
        
        ConfigurationExtender(ComponentManager()).load(self)

    def loadConfigPostHook(self):
        pass

    def saveConfigPreHook(self):
        pass

    def saveConfig(self,filename):
        self.saveConfigPreHook()
        
        ConfigurationExtender(ComponentManager()).save(self)

        GlobalSettings.saveConfig(filename)


if __name__ == "__main__":
    pass

