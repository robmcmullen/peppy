import os,re

import wx
import wx.stc as stc

from menudev import *
from wxemacskeybindings import *

from cStringIO import StringIO

from configprefs import *
from stcinterface import *
from iofilter import *
from views import *
from tabbedviewer import *
from debug import *



class BufferList(CategoryList):
    debuglevel=0
    
    name = "BufferListMenu"
    empty = "< list of buffers >"
    tooltip = "Show the buffer in the current frame"
    categories = False

    # hash of buffer categories and buffers
    itemdict = {}
    # File list is shared among all windows
    itemlist = []

    # list of viewers
    viewers=[]
    
    def __init__(self, frame):
        FrameActionList.__init__(self, frame)
        self.itemdict = BufferList.itemdict
        self.itemlist = BufferList.itemlist
        self.categories = False

    # FIXME: temporary hack to keep the list in the correct order so
    # that the callback based on index will work.
    def regenList(self):
        del self.itemlist[:]
        cats=self.itemdict.keys()
        cats.sort()
        self.dprint("categories=%s" % cats)
        for category in cats:
            items=self.itemdict[category]
            self.itemlist.extend(items)

    # have to subclass append because we maintain order by groups
    def append(self,buffer):
        newitem={'item':buffer,'name':buffer.name,'icon':None}
        category=buffer.defaultviewer.keyword
        if category in self.itemdict:
            self.itemdict[category].append(newitem)
        else:
            self.itemdict[category]=[newitem]
        self.regenList()
        
    def remove(self,buffer):
        #index=self.findIndex(item)
        #del self.itemlist[index]
        self.dprint("trying to remove buffer %s" % buffer)
        for cat in self.itemdict.keys():
            self.dprint("checking %s; list=%s" % (cat,str(self.itemdict[cat])))
            for entry in self.itemdict[cat]:
                if entry['item']==buffer:
                    self.itemdict[cat].remove(entry)
                    self.dprint("removed buffer %s" % buffer)
                    if len(self.itemdict[cat])==0:
                        del self.itemdict[cat]
        self.regenList()
        
    def action(self, state=None, pos=-1):
        self.dprint("BufferList.run: id(self)=%x name=%s pos=%d id(itemlist)=%x" % (id(self),self.name,pos,id(self.itemlist)))
        self.dprint("BufferList.run: changing frame name=%s to buffer=%s" % (self.name,self.itemlist[pos]))
        self.frame.setBuffer(self.itemlist[pos]['item'])


    def getDefaultViewer(self, filename):
        choices=[]
        for viewer in self.viewers:
            self.dprint("checking viewer %s regex=%s" % (str(viewer),viewer.regex))
            match=re.search(viewer.regex,filename)
            if match:
                choices.append(viewer)
        if len(choices)==0:
            viewer=View
        elif len(choices)>1:
            viewer=choices[0]
            self.dprint("chosing %s out of %d viewers" % (str(viewer),len(choices)))
        else:
            viewer=choices[0]

        self.dprint("loading buffer %s with %s" % (filename,str(viewer)))
        return viewer

    def registerViewer(self,viewer):
        self.viewers.append(viewer)
        self.dprint(self.viewers)





#### Buffers



class Buffer(debugmixin):
    count=0
    debuglevel=0

    filenames={}
    
    def __init__(self,filename=None,fh=None,mystc=None,stcparent=None,defaultviewer=None):
        Buffer.count+=1
        self.fh=fh
        self.defaultviewer=defaultviewer
        self.setFilename(filename)

        self.name="Buffer #%d: %s" % (self.count,str(self.filename))

        self.viewer=None
        self.viewers=[]

        self.modified=False

        # always one STC per buffer
        if mystc==None:
            self.stc=MySTC(stcparent)
        else:
            self.stc=mystc
        self.stc.Bind(stc.EVT_STC_CHANGE, self.OnChanged)
        self.docptr=None

    def getView(self,frame,viewerclass=None):
        if viewerclass:
            viewer=viewerclass(self,frame)
        else:
            viewer=self.defaultviewer(self,frame) # create new view
        self.viewers.append(viewer) # keep track of views
        self.dprint("views of %s: %s" % (self,self.viewers))
        return viewer

    def remove(self,view):
        self.dprint("removing view %s of %s" % (view,self))
        if view in self.viewers:
            self.viewers.remove(view)
        else:
            raise ValueError("Bug somewhere.  View %s not found in Buffer %s" % (view,self))
        self.dprint("views of %s: %s" % (self,self.viewers))

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

    def open(self,app):
        self.docptr=self.stc.CreateDocument()
        self.stc.SetDocPointer(self.docptr)
        self.dprint("open: creating new document %s" % self.docptr)
        filter=GetIOFilter(self.stc,self.filename)
        filter.read()
        # if no exceptions, it must have worked.
        self.modified=False
        self.stc.EmptyUndoBuffer()

        # FIXME: fix this so the app isn't necessary
        if self.defaultviewer is None:
            self.defaultviewer=app.getDefaultViewer(self.filename)

    def save(self,filename=None):
        self.dprint("Buffer: saving buffer %s" % (self.filename))
        try:
            if filename is None:
                filename=self.filename
            filter=GetIOFilter(self.stc,filename)
            filter.write()
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
        

class Empty(Buffer):
    def __init__(self,filename=None,fh=None):
        Buffer.__init__(self,filename,fh,BlankSTC,defaultviewer=View)
        self.name="(Empty)"


##class BufferList(object):
##    def __init__(self):
##        self.files={}
##        self.modes={}

##    def registerMajorMode(self,mode):
##        self.modes[mode.keyword]=mode



class BufferFrame(MenuFrame,ClassSettingsMixin):
    def __init__(self, app):
        self.framelist=app.frames

        # FIXME: temporary hack to get window size from application
        # config
        ClassSettingsMixin.__init__(self)
        size=(int(self.settings.width),int(self.settings.height))
        self.dprint(size)
        
        MenuFrame.__init__(self, app, self.framelist, size=size)
        self.app=app
        
        self.tabs=HideOneTabViewer(self)
##        self.tabs=TabbedViewer(self)
        self.setMainWindow(self.tabs)
        self.tabs.addUserChangedCallback(self.OnViewerChanged)

        self.resetMenu()

        self.Bind(wx.EVT_ACTIVATE, self.OnActivate)

        self.titleBuffer()

    def closeWindowHook(self):
        # prevent a PyDeadObjectError when the window is closed by
        # removing this callback.
        self.tabs.clearUserChangedCallbacks()

    def OnActivate(self, evt):
        # When the frame is made the current active frame, update the
        # UI to make sure all the menu items/toolbar items reflect the
        # correct state.
        self.dprint("%s to front" % self.name)
        self.enableMenu()
        viewer=self.getCurrentViewer()
        if viewer:
            wx.CallAfter(viewer.focus)
        self.app.SetTopWindow(self)

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
        
    def getCurrentSTC(self):
        viewer=self.tabs.getCurrentViewer()
        if viewer:
            return viewer.stc
        return BlankSTC
    
    def getCurrentViewer(self):
        viewer=self.tabs.getCurrentViewer()
        return viewer
    
    def resetMenu(self):
        self.setMenuActions(self.app.menu_actions,self.app.globalKeys)
        self.setToolbarActions(self.app.toolbar_actions,self.app.globalKeys)
        self.setKeyboardActions(self.app.keyboard_actions,self.app.globalKeys)

    def addMenu(self,viewer=None):
        if not viewer:
            viewer=self.getCurrentViewer()
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
        viewer=self.getCurrentViewer()
            #self.dprint("viewer=%s isOpen=%s" % (str(viewer),str(viewer!=None)))
        return viewer!=None

    def isTopWindow(self):
        return self.app.GetTopWindow()==self

    def close(self):
        viewer=self.getCurrentViewer()
        if viewer:
            buffer=viewer.buffer
            if self.app.close(buffer):
                self.tabs.closeViewer(viewer)
                self.resetMenu()

    def closeViewer(self,viewer):
        self.tabs.closeViewer(viewer)
        self.resetMenu()

    def setTitle(self):
        viewer=self.getCurrentViewer()
        if viewer:
            self.SetTitle("peppy: %s" % viewer.getTabName())
        else:
            self.SetTitle("peppy")

    def showModified(self,viewer):
        current=self.getCurrentViewer()
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
        self.getCurrentViewer().focus()
        self.setTitle()

    def setBuffer(self,buffer):
        # this gets a default view for the selected buffer
        viewer=buffer.getView(self)
        self.dprint("setting buffer to new view %s" % viewer)
        self.setViewer(viewer)

    def changeMajorMode(self,newmode):
        viewer=self.getCurrentViewer()
        if viewer:
            newview=viewer.buffer.getView(self,newmode)
            self.dprint("new view=%s" % newview)
            self.setViewer(newview)

    def titleBuffer(self):
        self.open('about:title.txt')
        
    def newBuffer(self,buffer):
        viewer=buffer.getView(self)
        self.dprint("viewer=%s" % viewer)
        self.menuactions.widget.Freeze()
        self.resetMenu()
        self.dprint("after resetMenu")
        self.tabs.addViewer(viewer)
        self.dprint("after addViewer")
        self.addMenu()
        self.menuactions.widget.Thaw()
        self.getCurrentViewer().focus()
        self.setTitle()

    def open(self,filename,newTab=True):
        buffer=Buffer(filename,stcparent=self.app.dummyframe)
        # probably should load the file here, and if it fails for some
        # reason, don't add to the buffer list.
        buffer.open(self.app)
        
        self.app.addBuffer(buffer)
        if newTab:
            self.newBuffer(buffer)
        else:
            self.setBuffer(buffer)

    def openFileDialog(self):        
        viewer=self.getCurrentViewer()
        wildcard="*.*"
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
                self.open(path)

        # Destroy the dialog. Don't do this until you are done with it!
        # BAD things can happen otherwise!
        dlg.Destroy()
       
    def save(self):        
        viewer=self.getCurrentViewer()
        if viewer and viewer.buffer:
            viewer.buffer.save()
            
    def saveFileDialog(self):        
        viewer=self.getCurrentViewer()
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
       
    def newTab(self):
        self.dprint("frame=%s" % self)
        buffer=Empty()
        self.dprint("buffer=%s" % buffer)
        self.newBuffer(buffer)


    #### PyPE Compatability

    def getglobal(self,param):
        return None

class BufferApp(wx.App,debugmixin):
    def OnInit(self):
        self.menu_actions=[]
        self.toolbar_actions=[]
        self.keyboard_actions=[]
        self.bufferhandlers=[]
        
        self.frames=FrameList(self) # master frame list
        self.buffers=BufferList(None) # master buffer list

        self.confdir=None
        self.cfgfile=None

        self.globalKeys=KeyMap()

        # the Buffer objects have an stc as the base, and they need a
        # frame in which to work.  So, we create a dummy frame here
        # that is never shown.
        self.dummyframe=wx.Frame(None)
        self.dummyframe.Show(False)

        self.errors=[]

    def getDefaultViewer(self,filename):
        return self.buffers.getDefaultViewer(filename)

    def registerViewer(self,cls):
        self.buffers.registerViewer(cls)

    def addBuffer(self,buffer):
        self.buffers.append(buffer)
        self.rebuildMenus()

    def removeBuffer(self,buffer):
        self.buffers.remove(buffer)
        self.rebuildMenus()

    def addGlobalMenu(self,actions):
        self.menu_actions.extend(actions)
        
    def addGlobalToolbar(self,actions):
        self.toolbar_actions.extend(actions)
        
    def addGlobalKeys(self,actions):
        self.keyboard_actions.extend(actions)
        
    def deleteFrame(self,frame):
        #self.pendingframes.append((self.frames.getid(frame),frame))
        #self.frames.remove(frame)
        pass
    
    def rebuildMenus(self):
        for frame in self.frames.getItems():
            frame.rebuildMenus()
        
    def newFrame(self,callingFrame=None):
        frame=BufferFrame(self)
        self.rebuildMenus()
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
        buffers=self.buffers.getItems()
        for buf in buffers:
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
        if 'viewers' in mod.__dict__:
            self.dprint("found viewers: %s" % mod.viewers)
            for viewer in mod.viewers:
                self.registerViewer(viewer)
        if 'global_menu_actions' in mod.__dict__:
            self.dprint("found menu actions: %s" % mod.global_menu_actions)
            self.addGlobalMenu(mod.global_menu_actions)
        if 'global_toolbar_actions' in mod.__dict__:
            self.dprint("found toolbar actions: %s" % mod.global_toolbar_actions)
            self.addGlobalToolbar(mod.global_toolbar_actions)
        if 'global_keyboard_actions' in mod.__dict__:
            self.dprint("found keyboard actions: %s" % mod.global_keyboard_actions)
            self.addGlobalKeys(mod.global_keyboard_actions)

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

