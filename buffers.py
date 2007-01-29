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



class BufferList(ListAction):
    name="Buffers"
    inline=True

    buffers=[]
    others=[]
    
    def __init__(self, menumap, menu):
        ListAction.__init__(self,menumap,menu)
        BufferList.others.append(self)

    @staticmethod
    def append(frame):
        BufferList.buffers.append(frame)
        for actions in BufferList.others:
            actions.dynamic()
        
    @staticmethod
    def remove(frame):
        dprint("BEFORE: buffers: %s" % BufferList.buffers)
        dprint("BEFORE: others: %s" % BufferList.others)
        BufferList.buffers.remove(frame)

        # can't delete from a list that you're iterating on, so make a
        # new list.
        newlist=[]
        for other in BufferList.others:
            # Search through all related actions and remove references
            # to them. There may be more than one reference, so search
            # them all.
            if other.frame != frame:
                newlist.append(other)
        BufferList.others=newlist

        dprint("AFTER: buffers: %s" % BufferList.buffers)
        dprint("AFTER: others: %s" % BufferList.others)
        
        for actions in BufferList.others:
            actions.dynamic()
        
    def getHash(self):
        temp=tuple(self.buffers)
        self.dprint("hash=%s" % hash(temp))
        return hash(temp)

    def getItems(self):
        return [buf.name for buf in self.buffers]

    def action(self,state=None,index=0):
        self.dprint("top window to %d: %s" % (index,BufferList.buffers[index]))
        self.frame.app.SetTopWindow(BufferList.buffers[index])
        wx.CallAfter(BufferList.buffers[index].Raise)

class FrameList(ListAction):
    name="Frames"
    inline=True

    frames=[]
    others=[]
    
    def __init__(self, menumap, menu):
        ListAction.__init__(self,menumap,menu)
        FrameList.others.append(self)

    @staticmethod
    def append(frame):
        FrameList.frames.append(frame)
        for actions in FrameList.others:
            actions.dynamic()
        
    @staticmethod
    def remove(frame):
        dprint("BEFORE: frames: %s" % FrameList.frames)
        dprint("BEFORE: others: %s" % FrameList.others)
        FrameList.frames.remove(frame)

        # can't delete from a list that you're iterating on, so make a
        # new list.
        newlist=[]
        for other in FrameList.others:
            # Search through all related actions and remove references
            # to them. There may be more than one reference, so search
            # them all.
            if other.frame != frame:
                newlist.append(other)
        FrameList.others=newlist

        dprint("AFTER: frames: %s" % FrameList.frames)
        dprint("AFTER: others: %s" % FrameList.others)
        
        for actions in FrameList.others:
            actions.dynamic()
        
    def getHash(self):
        temp=tuple(self.frames)
        self.dprint("hash=%s" % hash(temp))
        return hash(temp)

    def getItems(self):
        return [frame.getTitle() for frame in self.frames]

    def action(self,state=None,index=0):
        self.dprint("top window to %d: %s" % (index,FrameList.frames[index]))
        self.frame.app.SetTopWindow(FrameList.frames[index])
        wx.CallAfter(FrameList.frames[index].Raise)


class DeleteFrame(SelectAction):
    name = "&Delete Frame"
    tooltip = "Delete current window"
    
    def action(self, pos=-1):
        self.frame.closeWindow(None)

    def isEnabled(self):
        if len(FrameList.frames)>1:
            return True
        return False

class NewFrame(SelectAction):
    name = "&New Frame"
    tooltip = "Open a new window"
    keyboard = "C-X 5 2"
    
    def action(self, pos=-1):
        frame=self.frame.app.newFrame(callingFrame=self.frame)
        frame.Show(True)

#### Buffers



class Buffer(debugmixin):
    count=0
    debuglevel=0

    filenames={}
    
    def __init__(self,filename=None,fh=None,mystc=None,stcparent=None,defaultmode=None):
        Buffer.count+=1
        self.fh=fh
        self.defaultmode=defaultmode
        self.setFilename(filename)

        self.name="Buffer #%d: %s" % (self.count,str(self.filename))

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

    def save(self,filename=None):
        self.dprint("Buffer: saving buffer %s" % (self.filename))
        try:
            if filename is None:
                filename=self.filename
            filter=GetIOFilter(filename)
            filter.write(self.stc)
            self.stc.SetSavePoint()
            if filename is not None:
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
        




class oldBufferFrame(wx.Frame,ClassSettingsMixin,debugmixin):
    debuglevel=0
    frameid = 0
    
    def __init__(self, app):
        self.framelist=app.frames

        BufferFrame.frameid+=1
        self.name="peppy: Frame #%d" % BufferFrame.frameid

        # FIXME: temporary hack to get window size from application
        # config
        ClassSettingsMixin.__init__(self)
        size=(int(self.settings.width),int(self.settings.height))
        self.dprint(size)
        
        wx.Frame.__init__(self, None, id=-1, title=self.name, pos=wx.DefaultPosition, size=size, style=wx.DEFAULT_FRAME_STYLE|wx.CLIP_CHILDREN)
        self.app=app
        
        self.Bind(wx.EVT_CLOSE,self.OnClose)
        self.CreateStatusBar()
        self.SetStatusText("This is the statusbar")

        self.SetMenuBar(wx.MenuBar())
        self.setMenumap()

        self.tabs=HideOneTabViewer(self)
##        self.tabs=TabbedViewer(self)
        self.setMainWindow(self.tabs)
        self.tabs.addUserChangedCallback(self.OnViewerChanged)

        self.resetMenu()

        self.Bind(wx.EVT_ACTIVATE, self.OnActivate)

        self.titleBuffer()

    def CreateStatusBar(self):
        MenuFrame.CreateStatusBar(self,number=2)
        self.statusbar.SetStatusWidths([-1,100])

    def closeWindowHook(self):
        # prevent a PyDeadObjectError when the window is closed by
        # removing this callback.
        self.tabs.clearUserChangedCallbacks()

    def OnActivate(self, evt):
        # When the frame is made the current active frame, update the
        # UI to make sure all the menu items/toolbar items reflect the
        # correct state.
        if evt.GetActive():
            self.dprint("%s to front" % self.name)
            self.enableMenu()
            viewer=self.getActiveMajorMode()
            if viewer:
                wx.CallAfter(viewer.focus)
            self.app.SetTopWindow(self)
        else:
            self.dprint("%s not current frame anymore" % self.name)

    def OnViewerChanged(self,evt):
        self.dprint("%s to viewer %s" % (self.name,evt.GetViewer()))
        self.menuactions.widget.Freeze()
        self.resetMenu()
        viewer=evt.GetViewer()
        self.addMenu(viewer)
        self.menuactions.widget.Thaw()
        wx.CallAfter(viewer.focus)
        self.setTitle()
        evt.Skip()
        
    def getActiveMajorMode(self):
        viewer=self.tabs.getCurrentViewer()
        return viewer
    
    def resetMenu(self):
        self.setMenuActions(self.app.menu_actions,self.app.globalKeys)
        self.setToolbarActions(self.app.toolbar_actions,self.app.globalKeys)
        self.setKeyboardActions(self.app.keyboard_actions,self.app.globalKeys)

    def addMenu(self,viewer=None):
        if not viewer:
            viewer=self.getActiveMajorMode()
        self.dprint("menu from viewer %s" % viewer)
        if viewer:
            self.dprint("  from page %d" % self.tabs.getCurrentIndex())

            keymap=viewer.getLocalKeyMap()
            
            self.menuactions.addMenu(viewer.getMenuActions(),keymap)
            self.menuactions.proxyValue(self)
            
            self.toolbaractions.addTools(viewer.getToolbarActions(),keymap)
            self.toolbaractions.proxyValue(self)

            self.keys.setLocalKeyMap(keymap)

            if self.popup:
                viewer.addPopup(self.popup)
            
        self.enableMenu()

    def isOpen(self):
        viewer=self.getActiveMajorMode()
            #self.dprint("viewer=%s isOpen=%s" % (str(viewer),str(viewer!=None)))
        return viewer!=None

    def isTopWindow(self):
        return self.app.GetTopWindow()==self

    def close(self):
        viewer=self.getActiveMajorMode()
        if viewer:
            buffer=viewer.buffer
            if self.app.close(buffer):
                self.tabs.closeViewer(viewer)
                self.resetMenu()

    def closeViewer(self,viewer):
        self.tabs.closeViewer(viewer)
        self.resetMenu()

    def setTitle(self):
        viewer=self.getActiveMajorMode()
        if viewer:
            self.SetTitle("peppy: %s" % viewer.getTabName())
        else:
            self.SetTitle("peppy")

    def showModified(self,viewer):
        current=self.getActiveMajorMode()
        if current:
            self.setTitle()
        self.tabs.showModified(viewer)

    def setViewer(self,viewer):
        self.menuactions.widget.Freeze()
        self.resetMenu()
        self.tabs.setViewer(viewer)
        #viewer.open()
        self.addMenu()
        self.menuactions.widget.Thaw()
        self.getActiveMajorMode().focus()
        self.setTitle()

    def setBuffer(self,buffer):
        # this gets a default view for the selected buffer
        viewer=buffer.createMajorMode(self)
        self.dprint("setting buffer to new view %s" % viewer)
        self.setViewer(viewer)

    def changeMajorMode(self,newmode):
        viewer=self.getActiveMajorMode()
        if viewer:
            newview=viewer.buffer.createMajorMode(self,newmode)
            self.dprint("new view=%s" % newview)
            self.setViewer(newview)

    def titleBuffer(self):
        self.open('about:title.txt')
        
    def newBuffer(self,buffer):
        viewer=buffer.createMajorMode(self)
        self.dprint("viewer=%s" % viewer)
        self.menuactions.widget.Freeze()
        self.resetMenu()
        self.dprint("after resetMenu")
        self.tabs.addViewer(viewer)
        self.dprint("after addViewer")
        self.addMenu()
        self.menuactions.widget.Thaw()
        self.getActiveMajorMode().focus()
        self.setTitle()

    def open(self,filename,newTab=True,mode=None):
        buffer=Buffer(filename,stcparent=self.app.dummyframe,defaultmode=mode)
        # If we get an exception, it won't get added to the buffer list
        
        self.app.addBuffer(buffer)
        if newTab:
            self.newBuffer(buffer)
        else:
            self.setBuffer(buffer)

    def openFileDialog(self):        
        viewer=self.getActiveMajorMode()
        wildcard="*"
        cwd=os.getcwd()
        dlg = wx.FileDialog(
            self, message="Open File", defaultDir=cwd, 
            defaultFile="", wildcard=wildcard, style=wx.OPEN)

        # Show the dialog and retrieve the user response. If it is the
        # OK response, process the data.
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            paths = dlg.GetPaths()

            for path in paths:
                self.dprint("open file %s:" % path)
                # Force the loader to use the file: protocol
                self.open("file:%s" % path)

        # Destroy the dialog. Don't do this until you are done with it!
        # BAD things can happen otherwise!
        dlg.Destroy()
       
    def save(self):        
        viewer=self.getActiveMajorMode()
        if viewer and viewer.buffer:
            viewer.buffer.save()
            
    def saveFileDialog(self):        
        viewer=self.getActiveMajorMode()
        paths=None
        if viewer and viewer.buffer:
            saveas=viewer.buffer.getFilename()

            # Do this in a loop so that the user can get a chance to
            # change the filename if the specified file exists.
            while True:
                # If we come through this loop again, saveas will hold
                # a complete pathname.  Shorten it.
                saveas=os.path.basename(saveas)
                
                wildcard="*.*"
                cwd=os.getcwd()
                dlg = wx.FileDialog(
                    self, message="Save File", defaultDir=cwd, 
                    defaultFile=saveas, wildcard=wildcard, style=wx.SAVE)

                retval=dlg.ShowModal()
                if retval==wx.ID_OK:
                    # This returns a Python list of files that were selected.
                    paths = dlg.GetPaths()
                dlg.Destroy()

                if retval!=wx.ID_OK:
                    break
                elif len(paths)==1:
                    saveas=paths[0]
                    self.dprint("save file %s:" % saveas)

                    # If new filename exists, make user confirm to
                    # overwrite
                    if os.path.exists(saveas):
                        dlg = wx.MessageDialog(self, "%s\n\nexists.  Overwrite?" % saveas, "Overwrite?", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION )
                        retval=dlg.ShowModal()
                        dlg.Destroy()
                    else:
                        retval=wx.ID_YES
                    if retval==wx.ID_YES:
                        viewer.buffer.save(saveas)
                        break
                elif paths!=None:
                    raise IndexError("BUG: probably shouldn't happen: len(paths)!=1 (%s)" % str(paths))


    #### PyPE Compatability

    def getglobal(self,param):
        return None







class DemoTree(wx.TreeCtrl):
    def __init__(self, parent, size=wx.DefaultSize):
        wx.TreeCtrl.__init__(self, parent, -1, wx.Point(0, 0), size=size, style=wx.TR_DEFAULT_STYLE | wx.NO_BORDER)
        
        root = self.AddRoot("AUI Project")
        items = []
        self.SetFont(wx.Font(8, wx.SWISS, wx.NORMAL, wx.NORMAL))

        imglist = wx.ImageList(16,16, True, 2)
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










class MyNotebook(wx.aui.AuiNotebook,debugmixin):
    def __init__(self, parent, size=wx.DefaultSize):
        wx.aui.AuiNotebook.__init__(self, parent, size=size, style=wx.aui.AUI_NB_WINDOWLIST_BUTTON|wx.aui.AUI_NB_TAB_MOVE|wx.aui.AUI_NB_TAB_SPLIT|wx.aui.AUI_NB_CLOSE_BUTTON|wx.aui.AUI_NB_SCROLL_BUTTONS)
        
        self.frame=parent
        self.lastActivePage=None
        
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.OnTabChanged)

    def OnTabChanged(self, evt):
        newpage=evt.GetSelection()
        self.lastActivePage=self.GetPage(evt.GetOldSelection())
        dprint("changing from %s to %s" % (self.lastActivePage,newpage))
        page=self.GetPage(newpage)
        dprint("page: %s" % page)
        wx.CallAfter(self.frame.switchMode)
        evt.Skip()

    def addTab(self,mode):
        self.AddPage(mode, mode.getTabName(), bitmap=getIconBitmap(mode.icon))
        index=self.GetPageIndex(mode)
        self.SetSelection(index)
        
    def getCurrent(self):
        return self.GetPage(self.GetSelection())

    def getPrevious(self):
        return self.lastActivePage

    def updateTitle(self,mode):
        index=self.GetPageIndex(mode)
        if index>=0:
            self.SetPageText(index,mode.getTabName())








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
                       'major mode':'C++',
                       }
        
        self.SetMenuBar(wx.MenuBar())
        self.menumap=None
        self.toolmap=None
        
        self.keys=KeyProcessor(self)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyPressed)

        self.titleBuffer()
        


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
            newmode=viewer.buffer.createMajorMode(self,requested)
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

    def switchMode(self):
        last=self.tabs.getPrevious()
        mode=self.getActiveMajorMode()
        dprint("Switching from mode %s to mode %s" % (last,mode))

        hierarchy=getSubclassHierarchy(mode,MajorMode)
        dprint("Mode hierarchy: %s" % hierarchy)
        # Get the major mode names for the hierarchy (but don't
        # include the last one which is the abstract MajorMode)
        majors=[m.keyword for m in hierarchy[:-1]]
        dprint("Major mode names: %s" % majors)
        
        if last:
            dprint("saving settings for mode %s" % last)
            BufferFrame.perspectives[last.buffer.filename] = self._mgr.SavePerspective()
        
        mode.focus()
        self.setTitle()
        self.settings['major mode']=mode
        self.setKeys(majors)
        self.setMenumap(majors)
        self.setToolmap(majors)

        if mode.buffer.filename in BufferFrame.perspectives:
            self._mgr.LoadPerspective(BufferFrame.perspectives[mode.buffer.filename])
            dprint(BufferFrame.perspectives[mode.buffer.filename])
        else:
            if 'default perspective' in self.settings:
                # This doesn't exactly work because anything not named in
                # the default perspective listing won't be shown.  Need to
                # find a way to determine which panes are new and show
                # them.
                self._mgr.LoadPerspective(self.settings['default perspective'])
                all_panes = self._mgr.GetAllPanes()
                for pane in xrange(len(all_panes)):
                    all_panes[pane].Show()
            else:
                self.settings['default perspective'] = self._mgr.SavePerspective()
        
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
        BufferList.buffers.append(buffer)

    def removeBuffer(self,buffer):
        BufferList.buffers.remove(buffer)

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
        for buf in BufferList.buffers:
            self.dprint("buf=%s modified=%s" % (buf,buf.modified))
            if buf.modified:
                unsaved.append(buf)
        if len(unsaved)>0:
            dlg = wx.MessageDialog(self.GetTopWindow(), "The following files have unsaved changes:\n\n%s\n\nExit anyway?" % "\n".join([buf.displayname for buf in unsaved]), "Unsaved Changes", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION )
            retval=dlg.ShowModal()
            dlg.Destroy()
        else:
            retval=wx.ID_YES

        if retval==wx.ID_YES:
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

    def saveConfig(self,filename):
        GlobalSettings.saveConfig(filename)


if __name__ == "__main__":
    pass

