import os,re

import wx
import wx.stc as stc

from menudev import *
from singletonmixin import *
from wxemacskeybindings import *

from cStringIO import StringIO



class BufferList(CategoryList):
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
        CommandList.__init__(self, frame)
        self.itemdict = BufferList.itemdict
        self.itemlist = BufferList.itemlist
        self.categories = False

    # FIXME: temporary hack to keep the list in the correct order so
    # that the callback based on index will work.
    def regenList(self):
        del self.itemlist[:]
        cats=self.itemdict.keys()
        cats.sort()
        print cats
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
        print "trying to remove buffer %s" % buffer
        for cat in self.itemdict.keys():
            print "checking %s; list=%s" % (cat,str(self.itemdict[cat]))
            for entry in self.itemdict[cat]:
                if entry['item']==buffer:
                    self.itemdict[cat].remove(entry)
                    print "removed buffer %s" % buffer
                    if len(self.itemdict[cat])==0:
                        del self.itemdict[cat]
        self.regenList()
        
    def runthis(self, state=None, pos=-1):
        print "BufferList.run: id(self)=%x name=%s pos=%d id(itemlist)=%x" % (id(self),self.name,pos,id(self.itemlist))
        print "BufferList.run: changing frame name=%s to buffer=%s" % (self.name,self.itemlist[pos])
        self.frame.setBuffer(self.itemlist[pos]['item'])


    def getDefaultViewer(self, filename):
        choices=[]
        for viewer in self.viewers:
            print "checking viewer %s regex=%s" % (str(viewer),viewer.regex)
            match=re.search(viewer.regex,filename)
            if match:
                choices.append(viewer)
        if len(choices)==0:
            viewer=View
        elif len(choices)>1:
            viewer=choices[0]
            print "chosing %s out of %d viewers" % (str(viewer),len(choices))
        else:
            viewer=choices[0]

        print "loading buffer %s with %s" % (filename,str(viewer))
        return viewer

    def registerViewer(self,viewer):
        self.viewers.append(viewer)
        print self.viewers







#### Icons

class IconStorage(object):
    def __init__(self):
        self.il=wx.ImageList(16,16)
        self.map={}

    def get(self,filename):
        if filename not in self.map:
            img=wx.ImageFromBitmap(wx.Bitmap(filename))
            img.Rescale(16,16)
            bitmap=wx.BitmapFromImage(img)
            icon=self.il.Add(bitmap)
            print "ICON=%s" % str(icon)
            print img
            self.map[filename]=icon
        else:
            print "ICON: found icon for %s = %d" % (filename,self.map[filename])
        return self.map[filename]

    def assign(self,notebook):
        notebook.AssignImageList(self.il)

_iconStorage=None
def getIconStorage(icon=None):
    global _iconStorage
    if _iconStorage==None:
        _iconStorage=IconStorage()
    if icon:
        return _iconStorage.get(icon)
    else:
        return _iconStorage



#### STC Interface

class STCInterface(object):
    def CanPaste(self):
        return 0

    def Clear(self):
        pass

    def Copy(self):
        pass

    def Cut(self):
        pass

    def Paste(self):
        pass

    def EmptyUndoBuffer(self):
        pass

    def CanUndo(self):
        return 0

    def Undo(self):
        pass

    def CanRedo(self):
        return 0

    def Redo(self):
        pass

    def CreateDocument(self):
        return "notarealdoc"

    def SetDocPointer(self,ptr):
        pass

    def ReleaseDocument(self,ptr):
        pass

    def AddRefDocument(self,ptr):
        pass

# Global default STC interface for user interface purposes
BlankSTC=STCInterface()



#### Loaders for reading files and populating the STC interface

class Loader(object):
    def __init__(self,buffer):
        buffer.docptr=buffer.stc.CreateDocument()
        buffer.stc.SetDocPointer(buffer.docptr)
        print "Loader: creating new document %s" % buffer.docptr
        self.read(buffer)

    def read(self,buffer):
        pass

class TextLoader(Loader):
    def read(self,buffer):
        fh=buffer.getFileObject()
        txt=fh.read()
        print "TextLoader: reading %d bytes" % len(txt)
        buffer.stc.SetText(txt)

class BinaryLoader(Loader):
    def read(self,buffer):
        fh=buffer.getFileObject()
        txt=fh.read()
        print "BinaryLoader: reading %d bytes" % len(txt)

        # Now, need to convert it to two bytes per character
        styledtxt='\0'.join(txt)+'\0'
        print "styledtxt: length=%d" % len(styledtxt)

        buffer.stc.ClearAll()
        buffer.stc.AddStyledText(styledtxt)

        length=buffer.stc.GetTextLength()
        #wx.StaticText(self.win, -1, str(length), (0, 25))

        newtxt=buffer.stc.GetStyledText(0,length)
        out=" ".join(["%02x" % ord(i) for i in txt])
        print out
        #wx.StaticText(self.win, -1, out, (20, 45))

        errors=0
        for i in range(len(newtxt)):
            if newtxt[i]!=txt[i*2]:
                print "error at: %d (%02x != %02x)" % (i,ord(newtxt[i]),ord(txt[i]))
                errors+=1
            if errors>50: break
        print "errors=%d" % errors
    



#### View base class

class View(object):
    pluginkey = '-none-'
    icon='icons/page_white.png'
    keyword='Unknown'
    loader=TextLoader
    
    def __init__(self,buffer,frame):
        self.win=None
        self.stc=BlankSTC
        self.buffer=buffer
        self.frame=frame
        self.popup=None

        # View settings.
        self.settings={}

    # If there is no title, return the keyword
    def getTitle(self):
        return self.keyword

    def getIcon(self):
        return getIconStorage(self.icon)
    
    def createWindow(self,parent):
        self.win=wx.Window(parent, -1)
        self.win.SetBackgroundColour(wx.ColorRGB(0xabcdef))
        self.stc=stc.StyledTextCtrl(parent,-1)
        self.stc.Show(False)
        #wx.StaticText(self.win, -1, self.buffer.name, (10,10))

    def reparent(self,parent):
        self.win.Reparent(parent)

    def addPopup(self,popup):
        self.popup=popup
        self.win.Bind(wx.EVT_RIGHT_DOWN, self.popupMenu)

    def popupMenu(self,ev):
        # popups generate menu events as normal menus, so the
        # callbacks to the command objects should still work if the
        # popup is generated in the same way that the regular menu and
        # toolbars are.
        print "popping up menu for %s" % ev.GetEventObject()
        self.win.PopupMenu(self.popup)
        ev.Skip()

    def readySTC(self):
        pass

    def open(self):
        print "View: open docptr=%s" % self.buffer.docptr
        if self.buffer.docptr:
            # the docptr is a real STC, so use it as the base document
            # for the new view
            self.stc.AddRefDocument(self.buffer.docptr)
            self.stc.SetDocPointer(self.buffer.docptr)
        self.readySTC()

    def close(self):
        #self.stc.ReleaseDocument(self.buffer.docptr)
        pass





#### Buffers



fakefiles={}
fakefiles['demo.txt'] = """\
This editor is provided by a class named wx.StyledTextCtrl.  As
the name suggests, you can define styles that can be applied to
sections of text.  This will typically be used for things like
syntax highlighting code editors, but I'm sure that there are other
applications as well.  A style is a combination of font, point size,
foreground and background colours.  The editor can handle
proportional fonts just as easily as monospaced fonts, and various
styles can use different sized fonts.

There are a few canned language lexers and colourizers included,
(see the next demo) or you can handle the colourization yourself.
If you do you can simply register an event handler and the editor
will let you know when the visible portion of the text needs
styling.

wx.StyledTextEditor also supports setting markers in the margin...




...and indicators within the text.  You can use these for whatever
you want in your application.  Cut, Copy, Paste, Drag and Drop of
text works, as well as virtually unlimited Undo and Redo
capabilities, (right click to try it out.)
"""


class Buffer(object):
    count=0

    filenames={}
    
    def __init__(self,parent,filename=None,viewer=View,fh=None):
        Buffer.count+=1
        self.fh=fh
        self.defaultviewer=viewer
        self.setFilename(filename)

        self.name="Buffer #%d: %s.  Default viewer=%s" % (self.count,str(self.filename),self.defaultviewer.keyword)

        self.viewer=None

        # always one STC per buffer
        self.stc=stc.StyledTextCtrl(parent,-1)
        self.docptr=None

    def getView(self,frame):
        return self.defaultviewer(self,frame) # create new view

    def setFilename(self,filename):
        if not filename:
            filename="untitled"
        self.filename=filename
        if filename in self.filenames:
            count=self.filenames[filename]+1
            self.filenames[filename]=count
            self.displayname=filename+"<%d>"%count
        else:
            self.filenames[filename]=1
            self.displayname=filename
        
    def getFilename(self):
        return self.filename

    def getDisplayname(self):
        return self.displayname

    def getFileObject(self):
        if not self.fh:
            try:
                fh=open(self.filename,"rb")
            except:
                print "Couldn't open %s" % self.filename
                if self.filename in fakefiles:
                    fh=StringIO()
                    fh.write(fakefiles[self.filename])
                    fh.seek(0)
                else:
                    fh=StringIO()
                    fh.write("sample text for %s" % self.filename)
                    fh.seek(0)
            return fh
        return self.fh
    
    def open(self):
        self.defaultviewer.loader(self)
        

class Empty(Buffer):
    def __init__(self,parent,filename=None,viewer=View,fh=None):
        self.filename=filename
        self.fh=fh
        self.defaultviewer=viewer
        self.name="(Empty)"

        # always one STC per buffer
        self.stc=BlankSTC
        self.docptr=None


##class BufferList(object):
##    def __init__(self):
##        self.files={}
##        self.modes={}

##    def registerMajorMode(self,mode):
##        self.modes[mode.keyword]=mode



wxEVT_VIEWER_CHANGED = wx.NewEventType()

class ViewerChangedEvent(wx.PyCommandEvent):
    def __init__(self, viewer, eventType=wxEVT_VIEWER_CHANGED, id=1):
        wx.PyCommandEvent.__init__(self, eventType, id)
        self._eventType = eventType
        self._viewer=viewer

    def SetViewer(self, viewer):
        self._viewer=viewer

    def GetViewer(self):
        return self._viewer

class TabbedViewer(wx.Notebook):
    def __init__(self, parent, frame=None):
        wx.Notebook.__init__(self,parent,-1,style=wx.NO_BORDER)

        # if the frame is specified, chances are we're inside a
        # HideOneTabViewer.
        if frame is not None:
            self.frame=frame
        else:
            self.frame=parent
        
        getIconStorage().assign(self)
        
        self.managed=[] # dict with keys 'viewer','panel','box'

        self.updating=False
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.onTabChanged)
        self.userChangedCallbacks=[]

    def addUserChangedCallback(self, func):
        self.userChangedCallbacks.append(func)

    def onTabChanged(self,ev):
        if not self.updating:
            viewer=self.getViewer(ev.GetSelection())
            out=ViewerChangedEvent(viewer)
            for func in self.userChangedCallbacks:
                func(out)
        else:
            print "Skipping tab changed event for %d" % ev.GetSelection()
        ev.Skip()

    # Replace the current tab contents with this viewer, or create if
    # doesn't exist.
    def setViewer(self, viewer):
        index=self.GetSelection()
        if index>=0:
            self.updating=True
            managed=self.managed[index]
            managed['box'].Detach(managed['viewer'].win)
            managed['viewer'].win.Destroy()
            viewer.createWindow(managed['panel'])
            managed['box'].Add(viewer.win, 1, wx.EXPAND)
            managed['box'].Layout()
            managed['viewer']=viewer
            self.SetPageText(index,viewer.keyword)
            self.SetPageImage(index,viewer.getIcon())
            self.updating=False
        else:
            self.addViewer(viewer)
        viewer.open()

    # Add a viewer to a new tab
    def addViewer(self, viewer):
        self.updating=True
        index=self.GetPageCount()
        panel=wx.Panel(self, style=wx.NO_BORDER)
        box=wx.BoxSizer(wx.HORIZONTAL)
        panel.SetAutoLayout(True)
        panel.SetSizer(box)

        # if the window doesn't exist, create it; otherwise reparent it
        if not viewer.win:
            viewer.createWindow(panel)
            viewer.open()
        else:
            viewer.reparent(panel)
            viewer.win.Show()
        box.Add(viewer.win, 1, wx.EXPAND)
        panel.Layout()
        if self.AddPage(panel, viewer.keyword):
            managed={'panel': panel,
                     'box': box,
                     'viewer': viewer,
                     }
            self.managed.append(managed)
            self.SetPageImage(index,viewer.getIcon())
            self.SetSelection(index)
            print "added page=%d" % index
            print "managed=%s" % str(self.managed)
        else:
            print "FIXME: error adding page #%d" % index
        self.updating=False

    def closeViewer(self, viewer, close=True):
        self.updating=True
        if viewer:
            index=self.findIndex(viewer)
        else:
            index=self.GetSelection()
        print "closing page %d" % index
        if index>=0:
            self.DeletePage(index)

            managed=self.managed[index]
            del self.managed[index]
            if close: viewer.close() # don't close if we are reparenting!
                
            index=self.GetSelection()
            print "new current page=%d" % index
            print "managed=%s" % str(self.managed)
        self.updating=False
        return index

    def getCurrentIndex(self):
        return self.GetSelection()

    def getCurrentViewer(self):
        index=self.GetSelection()
        if index>=0:
            return self.managed[index]['viewer']
        return None
        
    def getViewer(self,index):
        if index>=0 and index<len(self.managed):
            return self.managed[index]['viewer']
        return None
        
    def findIndex(self,viewer):
        for index in range(len(self.managed)):
            if viewer==self.managed[index]['viewer']:
                return index
        return -1
        

class HideOneTabViewer(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, style=wx.NO_BORDER)
        self.frame=parent
        
        self.mainsizer=wx.BoxSizer(wx.VERTICAL)
        self.tabs=TabbedViewer(self,self.frame)
        self.mainsizer.Add(self.tabs,1,wx.EXPAND)
        self.SetAutoLayout(True)
        self.SetSizer(self.mainsizer)
        self.mainsizer.Hide(self.tabs)
        self.managed=None

        self.count=0
        self.viewer=None

    def addUserChangedCallback(self, func):
        self.tabs.addUserChangedCallback(func)

    def setWindow(self, win):
        # GetItem throws an exception on Windows if no item exists at
        # that position.  On unix it just returns None as according to
        # the docs.  So, keep track of any managed window ourselves.
        if self.managed:
            self.mainsizer.Detach(1)
            # the old view is destroyed here.  Should I save the state
            # somehow so the next view of this buffer sees the same
            # location in the file?
            self.managed.Destroy()
            self.managed=None
        if win:
            self.mainsizer.Add(win,1,wx.EXPAND)
            self.mainsizer.Hide(self.tabs)
            self.mainsizer.Show(win)
            self.managed=win
        self.Layout()

    def setViewer(self, viewer):
        if self.count<=1:
            self.viewer=viewer
            viewer.createWindow(self)
            print "setViewer: viewer.win=%s" % viewer.win
            self.setWindow(viewer.win)
            print "setViewer: after setWindow"
            viewer.open()
            print "setViewer: after viewer.open"
            self.count=1
        else:
            self.tabs.setViewer(viewer)

    def addViewer(self,viewer):
        if self.count==0:
            self.setViewer(viewer)
            self.count=1
        elif self.count==1:
            # reparent!
            self.Freeze()
            self.mainsizer.Hide(self.managed)
            self.mainsizer.Show(self.tabs)
            self.mainsizer.Detach(self.managed)
            # add old viewer as tab 1 (new window is created)
            self.tabs.addViewer(self.viewer)
            # clean up old stuff, but don't delete old window till
            # after the new one is created so the viewer can clone
            # itself.  ACTUALLY, now don't delete at all but reparent.
            #self.managed.Destroy()
            self.managed=None
            self.viewer=None
            # add new viewer as tab 2
            self.tabs.addViewer(viewer)
            self.Layout() # WXMSW: must call Layout after show/hide
            self.Thaw()
            self.count+=1
        else:
            self.tabs.addViewer(viewer)
            self.count+=1

    def closeViewer(self, viewer):
        if self.count>1:
            self.tabs.closeViewer(viewer)
            self.count-=1
            if self.count==1:
                # reparent from tabs
                viewer=self.tabs.getViewer(0)
                self.tabs.closeViewer(self.viewer,close=False)
                self.setViewer(viewer)
        elif self.count==1:
            win=wx.Window(self,-1)
            self.setWindow(win)
            self.viewer.close()
            self.viewer=None
            self.count=0

    def getCurrentIndex(self):
        if self.count==0:
            return -1
        elif self.count==1:
            return 0
        else:
            return self.tabs.getCurrentIndex()

    def getCurrentViewer(self):
        if self.count==0:
            return None
        elif self.count==1:
            return self.viewer
        else:
            return self.tabs.getCurrentViewer()
        
    def getViewer(self,index):
        if self.count==0:
            return None
        elif self.count==1 and index==0:
            return self.viewer
        else:
            return self.tabs.getViewer(index)
        
    def findIndex(self,viewer):
        if self.count==0:
            return None
        elif self.count==1 and viewer==self.viewer:
            return 1
        else:
            return self.tabs.findIndex(viewer)

class BufferFrame(MenuFrame):
    def __init__(self, proxy):
        self.framelist=FrameList(self)
        MenuFrame.__init__(self, proxy, self.framelist)

        self.proxy=proxy

        self.tabs=HideOneTabViewer(self)
##        self.tabs=TabbedViewer(self)
        self.setMainWindow(self.tabs)
        self.tabs.addUserChangedCallback(self.onViewerChanged)

        self.resetMenu()

        self.Bind(wx.EVT_ACTIVATE, self.OnActivate)


    def OnActivate(self, evt):
        # When the frame is made the current active frame, update the
        # UI to make sure all the menu items/toolbar items reflect the
        # correct state.
        print "OnActivate: %s" % self.name
        self.enableMenu()
        self.getCurrentViewer().win.SetFocus()

    def getCurrentSTC(self):
        viewer=self.tabs.getCurrentViewer()
        if viewer:
            return viewer.stc
        return BlankSTC
    
    def getCurrentViewer(self):
        viewer=self.tabs.getCurrentViewer()
        return viewer
    
    def resetMenu(self):
        self.setMenuPlugins('main',self.proxy.menu_plugins)
        self.setToolbarPlugins('main',self.proxy.toolbar_plugins)
        self.setKeyboardPlugins('main',self.proxy.keyboard_plugins)

    def addMenu(self,viewer=None):
        if not viewer:
            viewer=self.getCurrentViewer()
        print "menu from viewer %s" % viewer
        if viewer:
            print "  from page %d" % self.tabs.getCurrentIndex()
            keyword=viewer.pluginkey
            self.menuplugins.addMenu(keyword,self.proxy.menu_plugins)
            self.menuplugins.proxyValue(self)
            
            self.toolbarplugins.addTools(keyword,self.proxy.toolbar_plugins)
            self.toolbarplugins.proxyValue(self)

            if self.popup:
                viewer.addPopup(self.popup)
            
        self.enableMenu()

    def isOpen(self):
        viewer=self.getCurrentViewer()
            #print "viewer=%s isOpen=%s" % (str(viewer),str(viewer!=None))
        return viewer!=None

    def close(self):
        viewer=self.getCurrentViewer()
        if viewer:
            buffer=viewer.buffer
            if self.proxy.close(buffer):
                self.tabs.closeViewer(viewer)
                self.resetMenu()

    def setViewer(self,viewer):
        self.menuplugins.widget.Freeze()
        self.resetMenu()
        self.tabs.setViewer(viewer)
        #viewer.open()
        self.addMenu()
        self.menuplugins.widget.Thaw()
        self.getCurrentViewer().win.SetFocus()

    def setBuffer(self,buffer):
        # this gets a default view for the selected buffer
        viewer=buffer.getView(self)
        print "setting buffer to new view %s" % viewer
        self.setViewer(viewer)

    def changeMajorMode(self,newmode):
        viewer=self.getCurrentViewer()
        if viewer:
            buffer=viewer.buffer
            newview=newmode(buffer,self)
            print "changeMajorMode: new view=%s" % newview
            self.setViewer(newview)
        
    def newBuffer(self,buffer):
        viewer=buffer.getView(self)
        print "newBuffer: viewer=%s" % viewer
        self.menuplugins.widget.Freeze()
        self.resetMenu()
        print "newBuffer: after resetMenu"
        self.tabs.addViewer(viewer)
        print "newBuffer: after addViewer"
        self.addMenu()
        self.menuplugins.widget.Thaw()
        self.getCurrentViewer().win.SetFocus()

    def onViewerChanged(self,ev):
        self.menuplugins.widget.Freeze()
        self.resetMenu()
        self.addMenu(ev.GetViewer())
        self.menuplugins.widget.Thaw()
        self.getCurrentViewer().win.SetFocus()
        ev.Skip()
        
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
                print "open file %s:" % path
                self.proxy.open(self,path)

        # Destroy the dialog. Don't do this until you are done with it!
        # BAD things can happen otherwise!
        dlg.Destroy()
       



class BufferProxy(Singleton):
    def __init__(self, app):
        self.app=app
        self.menu_plugins=[]
        self.toolbar_plugins=[]
        self.keyboard_plugins=[]
        self.bufferhandlers=[]
        
        self.frames=FrameList(self) # master frame list
        self.buffers=BufferList(None) # master buffer list

        self.globalKeys=KeyMap()

        # the Buffer objects have an stc as the base, and they need a
        # frame in which to work.  So, we create a dummy frame here
        # that is never shown.
        self.dummyframe=wx.Frame(None)
        self.dummyframe.Show(False)

    def registerViewer(self,cls):
        self.buffers.registerViewer(cls)

    def addBuffer(self,buffer):
        self.buffers.append(buffer)
        self.rebuildMenus()

    def removeBuffer(self,buffer):
        self.buffers.remove(buffer)
        self.rebuildMenus()

    def addMenuPlugins(self,plugins):
        self.menu_plugins.extend(plugins)
        
    def addToolbarPlugins(self,plugins):
        self.toolbar_plugins.extend(plugins)
        
    def addKeyboardPlugins(self,plugins):
        self.keyboard_plugins.extend(plugins)
        
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
        return frame
        
    def showFrame(self,frame):
        frame.Show(True)

    def open(self,frame,filename):
        viewer=self.buffers.getDefaultViewer(filename)
        buffer=Buffer(self.dummyframe,filename,viewer)
        # probably should load the file here, and if it fails for some
        # reason, don't add to the buffer list.
        buffer.open()
        
        self.addBuffer(buffer)
        frame.setBuffer(buffer)

    def newTab(self,frame):
        print "newTab: frame=%s" % frame
        buffer=Empty(self.dummyframe)
        print "newTab: buffer=%s" % buffer
        frame.newBuffer(buffer)

    def close(self,buffer):
        self.removeBuffer(buffer)
        return True

    def quit(self):
        print "prompt for unsaved changes..."
        sys.exit()


class BufferApp(wx.App):
    def OnInit(self):
        self.main=BufferProxy.getInstance(self)
        return True

    def getProxy(self):
        return self.main

    def loadPlugin(self, mod):
        print "loading plugins from module=%s" % str(mod)
        if 'viewers' in mod.__dict__:
            print "found viewers: %s" % mod.viewers
            for viewer in mod.viewers:
                self.main.registerViewer(viewer)
        if 'menu_plugins' in mod.__dict__:
            print "found menu plugins: %s" % mod.menu_plugins
            self.main.addMenuPlugins(mod.menu_plugins)
        if 'toolbar_plugins' in mod.__dict__:
            print "found toolbar plugins: %s" % mod.toolbar_plugins
            self.main.addToolbarPlugins(mod.toolbar_plugins)
        if 'keyboard_plugins' in mod.__dict__:
            print "found keyboard plugins: %s" % mod.keyboard_plugins
            self.main.addKeyboardPlugins(mod.keyboard_plugins)

if __name__ == "__main__":
    pass

