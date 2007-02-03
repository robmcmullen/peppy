import os,re

import wx
import wx.aui
import wx.stc as stc

from menu import *
from wxemacskeybindings import *

from cStringIO import StringIO

from configprefs import *
from stcinterface import *
from iofilter import *
from major import *
from iconstorage import *
from debug import *
from trac.core import *
from plugin import *
from dialogs import *

class BufferList(GlobalList):
    debuglevel=1
    name="Buffers"

    storage=[]
    others=[]
    
    def getItems(self):
        return [buf.name for buf in BufferList.storage]

    def action(self,state=None,index=0):
        self.dprint("top window to %d: %s" % (index,BufferList.storage[index]))
        self.frame.setBuffer(BufferList.storage[index])
    
class FrameList(GlobalList):
    debuglevel=1
    name="Frames"

    storage=[]
    others=[]
    
    def getItems(self):
        return [frame.getTitle() for frame in FrameList.storage]

    def action(self,state=None,index=0):
        self.dprint("top window to %d: %s" % (index,FrameList.storage[index]))
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
        self.defaultmode=defaultmode
        self.setFilename(filename)

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

        self.open(stcparent)

    def initSTC(self,mystc,stcparent=None):
        if mystc==None:
            self.stc=MySTC(stcparent)
        else:
            self.stc=mystc
        self.stc.Bind(stc.EVT_STC_CHANGE, self.OnChanged)

    def createMajorMode(self,frame,modeclass=None):
        if modeclass:
            viewer=modeclass(self,frame)
        else:
            viewer=self.defaultmode(self,frame) # create new view
        self.viewers.append(viewer) # keep track of views
        self.dprint("views of %s: %s" % (self,self.viewers))
        return viewer

    def remove(self,view):
        self.dprint("removing view %s of %s" % (view,self))
        if view in self.viewers:
            self.viewers.remove(view)
            if issubclass(view.stc.__class__,MySTC):
                self.stc.removeSubordinate(view.stc)
        else:
            raise ValueError("Bug somewhere.  Major mode %s not found in Buffer %s" % (view,self))
        self.dprint("views remaining of %s: %s" % (self,self.viewers))

    def removeAllViews(self):
        # Have to make a copy of self.viewers, because when the viewer
        # closes itself, it removes itself from this list of viewers,
        # so unless you make a copy the for statement is operating on
        # a changing list.
        viewers=self.viewers[:]
        for viewer in viewers:
            self.dprint("count=%d" % len(self.viewers))
            self.dprint("removing view %s of %s" % (viewer,self))
            viewer.frame.closeViewer(viewer)
        self.dprint("final count=%d" % len(self.viewers))

    def setFilename(self,filename):
        if not filename:
            filename="untitled"
        self.filename=filename
        basename=os.path.basename(self.filename)
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

    def open(self,stcparent):
        filter=GetIOFilter(self.filename)
        if self.stc==None:
            self.initSTC(filter.getSTC(stcparent))
        filter.read(self.stc)
        # if no exceptions, it must have worked.
        self.stc.openPostHook(filter)
        self.guessBinary=self.stc.GuessBinary(self.guessLength,self.guessPercentage)
        self.modified=False
        self.stc.EmptyUndoBuffer()

        if self.defaultmode is None:
            self.defaultmode=GetMajorMode(self)

        BufferHooks(ComponentManager()).openPostHook(self)
        
    def save(self,filename=None):
        self.dprint("Buffer: saving buffer %s" % (self.filename))
        try:
            if filename is None:
                saveas=self.filename
            else:
                saveas=filename
            filter=GetIOFilter(saveas)
            filter.write(self.stc)
            self.stc.SetSavePoint()
            self.modified=False
            if filename is not None and filename!=self.filename:
                self.setFilename(filename)
            self.showModifiedAll()
        except:
            print "Buffer: failed writing!"
            raise

    def showModifiedAll(self):
        for view in self.viewers:
            self.dprint("notifing: %s" % view)
            view.showModified(self.modified)

    def OnChanged(self, evt):
        if self.stc.GetModify():
            self.dprint("modified!")
            changed=True
        else:
            self.dprint("clean!")
            changed=False
        if changed!=self.modified:
            self.modified=changed
            wx.CallAfter(self.showModifiedAll)
        



import wx.lib.customtreectrl as ct

class DemoCustomTree(ct.CustomTreeCtrl):
    def __init__(self, parent, size=wx.DefaultSize):
        ct.CustomTreeCtrl.__init__(self, parent, -1, wx.Point(0, 0), size=size, style=wx.TR_DEFAULT_STYLE | wx.NO_BORDER, ctstyle=ct.TR_HAS_BUTTONS|ct.TR_HAS_VARIABLE_ROW_HEIGHT|ct.TR_HIDE_ROOT)
        #ctstyle=ct.TR_NO_BUTTONS|ct.TR_TWIST_BUTTONS|ct.TR_HAS_VARIABLE_ROW_HEIGHT|ct.TR_HIDE_ROOT|ct.TR_NO_LINES
        root = self.AddRoot("AUI Project")
        items = []
        self.SetFont(wx.Font(7, wx.SWISS, wx.NORMAL, wx.NORMAL))

        imglist = wx.ImageList(12,12, True, 2)
        imglist.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, wx.Size(16,16)))
        imglist.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, wx.Size(16,16)))
        self.AssignImageList(imglist)

        items.append(self.AppendItem(root, "Item 1", image=0))
        items.append(self.AppendItem(root, "Item 2", image=0))
        items.append(self.AppendItem(root, "Item 3", image=0))
        items.append(self.AppendItem(root, "Item 4", image=0))
        items.append(self.AppendItem(root, "Item 5", image=0))

        for ii in xrange(len(items)):
        
            id = items[ii]
            self.AppendItem(id, "Subitem 1", image=1)
            self.AppendItem(id, "Subitem 2", image=1)
            self.AppendItem(id, "Subitem 3", image=1)
            self.AppendItem(id, "Subitem 4", image=1)
            self.AppendItem(id, "Subitem 5", image=1)
        
        #self.Expand(root)

class DemoTree(wx.TreeCtrl):
    def __init__(self, parent, size=wx.DefaultSize):
        wx.TreeCtrl.__init__(self, parent, -1, wx.Point(0, 0), size=size, style=wx.TR_DEFAULT_STYLE | wx.NO_BORDER | wx.TR_HIDE_ROOT)
        
        root = self.AddRoot("AUI Project")
        items = []
        self.SetFont(wx.Font(8, wx.SWISS, wx.NORMAL, wx.NORMAL))

        imglist = wx.ImageList(16,16, True, 2)
        imglist.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, wx.Size(16,16)))
        imglist.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, wx.Size(16,16)))
        self.AssignImageList(imglist)

        items.append(self.AppendItem(root, "Item 1", image=0))
        items.append(self.AppendItem(root, "Item 2", image=0))
        items.append(self.AppendItem(root, "Item 3", image=0))
        items.append(self.AppendItem(root, "Item 4", image=0))
        items.append(self.AppendItem(root, "Item 5", image=0))

        for ii in xrange(len(items)):
        
            id = items[ii]
            self.AppendItem(id, "Subitem 1", image=1)
            self.AppendItem(id, "Subitem 2", image=1)
            self.AppendItem(id, "Subitem 3", image=1)
            self.AppendItem(id, "Subitem 4", image=1)
            self.AppendItem(id, "Subitem 5", image=1)
        
        #self.Expand(root)

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










class MyNotebook(wx.aui.AuiNotebook,debugmixin):
    def __init__(self, parent, size=wx.DefaultSize):
        wx.aui.AuiNotebook.__init__(self, parent, size=size, style=wx.aui.AUI_NB_WINDOWLIST_BUTTON|wx.aui.AUI_NB_TAB_MOVE|wx.aui.AUI_NB_TAB_SPLIT|wx.aui.AUI_NB_CLOSE_BUTTON|wx.aui.AUI_NB_SCROLL_BUTTONS)
        
        self.frame=parent
        self.lastActivePage=None
        
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.OnTabChanged)

    def OnTabChanged(self, evt):
        newpage=evt.GetSelection()
        self.lastActivePage=self.GetPage(evt.GetOldSelection())
        page=self.GetPage(newpage)
        dprint("changing from tab %s to %s; mode %s to %s" % (evt.GetOldSelection(), newpage, self.lastActivePage, page))
        dprint("page: %s" % page)
        wx.CallAfter(self.frame.switchMode)
        evt.Skip()

    def addTab(self,mode):
        self.AddPage(mode, mode.getTabName(), bitmap=getIconBitmap(mode.icon))
        index=self.GetPageIndex(mode)
        self.SetSelection(index)
        
    def replaceTab(self,mode):
        self.Freeze()
        index=self.GetSelection()
        dprint("Replacing tab %s at %d with %s" % (self.GetPage(index), index, mode))
        self.InsertPage(index, mode, mode.getTabName(), bitmap=getIconBitmap(mode.icon))
        self.RemovePage(index+1)
        self.SetSelection(index)
        self.Thaw()
        
    def getCurrent(self):
        return self.GetPage(self.GetSelection())

    def getPrevious(self):
        return self.lastActivePage

    def updateTitle(self,mode):
        index=self.GetPageIndex(mode)
        if index>=0:
            self.SetPageText(index,mode.getTabName())


class FramePluginLoader(Component):
    extensions=ExtensionPoint(IFramePluginProvider)

    def __init__(self):
        # Only call this once.
        if hasattr(FramePluginLoader,'pluginmap'):
            return self
        
        FramePluginLoader.pluginmap={}
        
        for ext in self.extensions:
            for plugin in ext.getFramePlugins():
                dprint("Registering frame plugin %s" % plugin.keyword)
                FramePluginLoader.pluginmap[plugin.keyword]=plugin

    def load(self,frame,pluginlist=[]):
        dprint("Loading plugins %s for %s" % (str(pluginlist),frame))
        for keyword in pluginlist:
            if keyword in FramePluginLoader.pluginmap:
                dprint("found %s" % keyword)
                plugin=FramePluginLoader.pluginmap[keyword]
                frame.createFramePlugin(plugin)

class BufferFrame(wx.Frame,ClassSettingsMixin,debugmixin):
    debuglevel=0
    frameid=0
    perspectives={}
    
    def __init__(self, app, id=-1):
        BufferFrame.frameid+=1
        self.name="peppy: Frame #%d" % BufferFrame.frameid

        # FIXME: temporary hack to get window size from application
        # config
        ClassSettingsMixin.__init__(self)
        size=(int(self.settings.width),int(self.settings.height))
        self.dprint(size)
        
        wx.Frame.__init__(self, None, id=-1, title=self.name, pos=wx.DefaultPosition, size=size, style=wx.DEFAULT_FRAME_STYLE|wx.CLIP_CHILDREN)
        self.app=app

        FrameList.append(self)
        
        self.CreateStatusBar()
        self.SetStatusText("This is the statusbar")

        # tell FrameManager to manage this frame        
        self._mgr = wx.aui.AuiManager()
        self._mgr.SetManagedWindow(self)

        self.tabs = MyNotebook(self)
        self._mgr.AddPane(self.tabs, wx.aui.AuiPaneInfo().Name("notebook").
                          CenterPane())
##        self.minortabs = MinorNotebook(self,size=(100,400))
##        self._mgr.AddPane(self.minortabs, wx.aui.AuiPaneInfo().Name("minor").
##                          Caption("Stuff").Right())
##        self.tree = DemoCustomTree(self,size=(100,400))
##        self._mgr.AddPane(self.tree, wx.aui.AuiPaneInfo().Name("funclist").
##                          Caption("Function List").Right())
        

        # Prepare the menu bar
        self.tempsettings={'asteroids':False,
                           'inner planets':True,
                           'outer planets':True,
                           'major mode':'C++',
                           }
        
        self.SetMenuBar(wx.MenuBar())
        self.menumap=None
        self.toolmap=None
        
        self.keys=KeyProcessor(self)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)

        self.loadFramePlugins()
        
    def addPane(self, win, paneinfo):
        self._mgr.AddPane(win, paneinfo)

    def loadFramePlugins(self):
        plugins=self.settings.plugins
        dprint(plugins)
        if plugins is not None:
            pluginlist=plugins.split(',')
            dprint("loading %s" % pluginlist)
            FramePluginLoader(ComponentManager()).load(self,pluginlist)

    def createFramePlugin(self,plugincls):
        plugin=plugincls(self)


    # Overrides of wx methods
    def OnClose(self, evt=None):
        dprint(evt)
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

        
    def setToolmap(self,majormodes=[],minormodes=[]):
        if self.toolmap is not None:
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
            #self.dprint("major=%s isOpen=%s" % (str(major),str(major!=None)))
        return major is not None

    def isTopWindow(self):
        return self.app.GetTopWindow()==self

    def close(self):
        major=self.getActiveMajorMode()
        if major:
            buffer=major.buffer
            if self.app.close(buffer):
                self.tabs.closeTab(major)

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
        self.dprint("setting buffer to new view %s" % mode)
        self.tabs.replaceTab(mode)
        self.switchMode()

    def changeMajorMode(self,requested):
        mode=self.getActiveMajorMode()
        if mode:
            newmode=mode.buffer.createMajorMode(self,requested)
            self.dprint("new mode=%s" % newmode)
            self.tabs.replaceTab(newmode)
            self.switchMode()

    def newBuffer(self,buffer):
        mode=buffer.createMajorMode(self)
        self.dprint("major mode=%s" % mode)
        self.tabs.addTab(mode)
        self.dprint("after addViewer")
        self.switchMode()

    def titleBuffer(self):
        self.open('about:title.txt')
        
    def open(self,filename,newTab=True,mode=None):
        buffer=Buffer(filename,stcparent=self.app.dummyframe,defaultmode=mode)
        # If we get an exception, it won't get added to the buffer list
        
        self.app.addBuffer(buffer)
        if newTab:
            self.newBuffer(buffer)
        else:
            self.setBuffer(buffer)
        mode=self.getActiveMajorMode()
        msg=mode.getWelcomeMessage()
        self.SetStatusText(msg)

    def save(self):        
        mode=self.getActiveMajorMode()
        if mode and mode.buffer:
            mode.buffer.save()
            
    def switchMode(self):
        last=self.tabs.getPrevious()
        mode=self.getActiveMajorMode()
        self.dprint("Switching from mode %s to mode %s" % (last,mode))

        hierarchy=getSubclassHierarchy(mode,MajorMode)
        self.dprint("Mode hierarchy: %s" % hierarchy)
        # Get the major mode names for the hierarchy (but don't
        # include the last one which is the abstract MajorMode)
        majors=[m.keyword for m in hierarchy[:-1]]
        self.dprint("Major mode names: %s" % majors)
        
        if last:
            self.dprint("saving settings for mode %s" % last)
            BufferFrame.perspectives[last.buffer.filename] = self._mgr.SavePerspective()
        
        mode.focus()
        self.setTitle()
        self.tempsettings['major mode']=mode
        self.setKeys(majors)
        self.setMenumap(majors)
        self.setToolmap(majors)

        if mode.buffer.filename in BufferFrame.perspectives:
            self._mgr.LoadPerspective(BufferFrame.perspectives[mode.buffer.filename])
            self.dprint(BufferFrame.perspectives[mode.buffer.filename])
        else:
            if 'default perspective' in self.tempsettings:
                # This doesn't exactly work because anything not named in
                # the default perspective listing won't be shown.  Need to
                # find a way to determine which panes are new and show
                # them.
                self._mgr.LoadPerspective(self.tempsettings['default perspective'])
                all_panes = self._mgr.GetAllPanes()
                for pane in xrange(len(all_panes)):
                    all_panes[pane].Show()
            else:
                self.tempsettings['default perspective'] = self._mgr.SavePerspective()
        
        # "commit" all changes made to FrameManager   
        self._mgr.Update()

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
        self.SetTopWindow(frame)
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
        self.dprint("prompt for unsaved changes...")
        unsaved=[]
        for buf in BufferList.storage:
            self.dprint("buf=%s modified=%s" % (buf,buf.modified))
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

    def loadPlugin(self, mod):
        self.dprint("loading plugins from module=%s" % str(mod))
        # FIXME: is this needed anymore, now that I'm using Trac plugins?

    def loadPlugins(self,plugins):
        if not isinstance(plugins,list):
            plugins=[p.strip() for p in plugins.split(',')]
        for plugin in plugins:
            try:
                mod=__import__(plugin)
                self.loadPlugin(mod)
            except Exception,ex:
                print "couldn't load plugin %s" % plugin
                print ex
                self.errors.append("couldn't load plugin %s" % plugin)

    def setConfigDir(self,dirname):
        self.confdir=dirname

    def getConfigFilePath(self,filename):
        c=HomeConfigDir(self.confdir)
        self.dprint("found home dir=%s" % c.dir)
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

