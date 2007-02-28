# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
import os,re

import wx
import wx.aui
import wx.stc as stc

from menu import *
from lib.wxemacskeybindings import *
from lib.iconstorage import *

from cStringIO import StringIO

from configprefs import *
from stcinterface import *
from iofilter import *
from major import *
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
    keyboard = "C-X 5 2"
    
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
    
    def __init__(self,filename=None,fh=None,mystc=None,stcparent=None,defaultmode=None):
        Buffer.count+=1
        self.fh=fh
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

        self.open(filename, stcparent)

    def initSTC(self):
        self.stc.Bind(stc.EVT_STC_CHANGE, self.OnChanged)

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

    def setFilename(self, url, path):
        if not url:
            filename="untitled"
        self.filename=url
        basename=os.path.basename(path)
        if basename in self.filenames:
            count=self.filenames[basename]+1
            self.filenames[basename]=count
            self.displayname=basename+"<%d>"%count
        else:
            self.filenames[basename]=1
            self.displayname=basename
        self.name="Buffer #%d: %s" % (self.count,str(self.filename))

        # Update UI because the filename associated with this buffer
        # may have changed and that needs to be reflected in the menu.
        BufferList.update()
        
    def getFilename(self):
        return self.filename

    def getTabName(self):
        if self.modified:
            return "*"+self.displayname
        return self.displayname

    def open(self, filename, stcparent):
        fh=GetReader(filename)

        # Need a two-stage opening process in order to support files
        # that are too large to fit in memory at once.  First, load
        # the first group of bytes into memory and use that to check
        # to see what type it is.
        
        self.stc = PeppySTC(stcparent)

        # Read the first thousand bytes
        self.stc.readFrom(fh, self.guessLength)
        # if no exceptions, it must have worked.
        self.readonly = fh.urlinfo.readonly
        self.setFilename(fh.urlinfo.url, fh.urlinfo.path)
        self.guessBinary=self.stc.GuessBinary(self.guessLength,
                                              self.guessPercentage)
        if self.defaultmode is None:
            self.defaultmode=GetMajorMode(self)

        if self.defaultmode.mmap_stc_class is not None:
            # we have a STC that allows files that are larger that
            # memory, so allow it to manage the file itself.
            self.stc = self.defaultmode.mmap_stc_class(stcparent, copy=self.stc)
        else:
            # Getting here means we've decided that we're using an
            # in-resident STC, so load the whole file.
            self.stc.readFrom(fh)

        if isinstance(self.stc,PeppySTC):
            # if no exceptions, it must have worked.
            self.initSTC()

        # let the stc get additional data from the file handle if it
        # needs to, and let it close the file.  Some stcs may be
        # interactive and need to keep the file open, so don't
        # explicitly close it here.
        self.stc.openPostHook(fh)
        
        self.modified=False
        self.stc.EmptyUndoBuffer()

        BufferHooks(ComponentManager()).openPostHook(self)
        
    def save(self,filename=None):
        assert self.dprint("Buffer: saving buffer %s" % (self.filename))
        try:
            if filename is None:
                saveas=self.filename
            else:
                saveas=filename
            fh=GetWriter(saveas)
            self.stc.writeTo(fh)
            self.stc.SetSavePoint()
            self.modified=False
            if filename is not None and filename!=self.filename:
                self.setFilename(filter.fh.geturl(), filter.fh.path)
            self.showModifiedAll()
        except:
            print "Buffer: failed writing!"
            raise

    def showModifiedAll(self):
        for view in self.viewers:
            assert self.dprint("notifing: %s" % view)
            view.showModified(self.modified)

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
        evt.Skip()

    def closeTab(self, mode):
        assert self.dprint("closing tab: mode %s" % mode)
        index=self.GetPageIndex(mode)
        self.RemovePage(index)
        mode.deleteWindow()

    def addTab(self,mode):
        assert self.dprint("Adding tab %s" % mode)
        self.AddPage(mode, mode.getTabName(), bitmap=getIconBitmap(mode.icon))
        index=self.GetPageIndex(mode)
        self.SetSelection(index)
        
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


## Sidebars

class Sidebar(ClassSettings):
    """
    Base class for all frame sidebars.  A frame sidebar is generally
    used to create a new UI window in a frame that is outside the
    purview of the major mode.  It is a constant regardless of which
    major mode is selected.
    """
    keyword=None

    default_settings = {
        'best_width': 100,
        'best_height': 200,
        'min_width': 100,
        'min_height': 100,
        }
    
    def __init__(self, frame):
        self.frame=frame
        if self.keyword is None:
            raise ValueError("keyword class attribute must be defined.")

        self.setup()

        self.createWindows(self.frame)
        
    def setup(self):
        pass

    def createWindows(self,parent):
        pass

class ISidebarProvider(Interface):
    """
    Add a frame sidebar to a new frame.
    """

    def getSidebars():
        """
        Return iterator containing list of frame sidebars.
        """

class SidebarLoader(Component,debugmixin):
    debuglevel=0
    
    extensions=ExtensionPoint(ISidebarProvider)

    def __init__(self):
        # Only call this once.
        if hasattr(SidebarLoader,'sidebarmap'):
            return self
        
        SidebarLoader.sidebarmap={}
        
        for ext in self.extensions:
            for sidebar in ext.getSidebars():
                assert self.dprint("Registering frame sidebar %s" % sidebar.keyword)
                SidebarLoader.sidebarmap[sidebar.keyword]=sidebar

    def load(self,frame,sidebarlist=[]):
        assert self.dprint("Loading sidebars %s for %s" % (str(sidebarlist),frame))
        for keyword in sidebarlist:
            if keyword in SidebarLoader.sidebarmap:
                assert self.dprint("found %s" % keyword)
                sidebar=SidebarLoader.sidebarmap[keyword]
                frame.createSidebar(sidebar)

class SidebarShow(ToggleListAction):
    name="Sidebars"
    inline=False
    tooltip="Show or hide sidebar windows"

    def getItems(self):
        return [m.caption for m in self.frame.sidebars]

    def isChecked(self, index):
        return self.frame.sidebars[index].IsShown()

    def action(self, index=0, old=-1):
        self.frame.sidebars[index].Show(not self.frame.sidebars[index].IsShown())
        self.frame._mgr.Update()


## BufferFrames

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
        self.sidebars = []
        
        self.SetMenuBar(wx.MenuBar())
        self.menumap=None
        self.toolmap=None
        
        self.keys=KeyProcessor(self)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)

        self.loadSidebars()
        
        self.app.SetTopWindow(self)
        
    def addPane(self, win, paneinfo):
        self._mgr.AddPane(win, paneinfo)

    def loadSidebars(self):
        sidebars=self.settings.sidebars
        assert self.dprint(sidebars)
        if sidebars is not None:
            sidebarlist=sidebars.split(',')
            assert self.dprint("loading %s" % sidebarlist)
            SidebarLoader(ComponentManager()).load(self,sidebarlist)
            self.createSidebarList()

    def createSidebar(self,sidebarcls):
        sidebar=sidebarcls(self)

    def createSidebarList(self):
        sidebars = self._mgr.GetAllPanes()
        for sidebar in sidebars:
            assert self.dprint("name=%s caption=%s window=%s state=%s" % (sidebar.name, sidebar.caption, sidebar.window, sidebar.state))
            if sidebar.name != "notebook":
                self.sidebars.append(sidebar)
        self.sidebars.sort(key=lambda s:s.caption)


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
        self.statusbar=wx.Frame.CreateStatusBar(self,number=2)
        self.statusbar.SetStatusWidths([-1,100])

    # non-wx methods
    
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

        # switchMode must be called here because no tabbed event is
        # generated when adding a new tab.
        self.switchMode()

    def titleBuffer(self):
        self.open('about:title.html')
        
    def open(self,filename,newTab=True,mode=None):
        buffer=Buffer(filename,stcparent=self.app.dummyframe,defaultmode=mode)
        # If we get an exception, it won't get added to the buffer list
        
        mode=self.getActiveMajorMode()
        self.app.addBuffer(buffer)
        if not newTab or (mode is not None and mode.temporary):
            self.setBuffer(buffer)
        else:
            self.newBuffer(buffer)
        mode=self.getActiveMajorMode()
        msg=mode.getWelcomeMessage()
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
            if mode.buffer.filename.startswith('file:'):
                cwd = os.path.dirname(mode.buffer.filename[5:])
            else:
                mode = None

        if mode is None:
            cwd=os.getcwd()
        return cwd
            
    def switchMode(self):
        last=self.tabs.getPrevious()
        mode=self.getActiveMajorMode()
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

    def loadPlugin(self, plugin):
        """Import a plugin from a module name

        Given a module name (e.g. 'peppy.plugins.example_plugin',
        import the module and trap any import errors.

        @param: name of plugin to load
        """
        assert self.dprint("loading plugins from module=%s" % str(plugin))
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

