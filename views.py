import os,re

import wx
import wx.stc as stc

from menudev import FrameAction
from stcinterface import *
from configprefs import *
from trac.core import *
from debug import *



class ViewAction(FrameAction):
    # Set up a new run() method to pass the viewer
    def run(self, state=None, pos=-1):
        self.dprint("id=%s name=%s" % (id(self),self.name))
        self.action(self.frame.getCurrentViewer(),state,pos)
        self.frame.enableMenu()

    # Set up a new keyboard callback to also pass the viewer
    def __call__(self, evt, number=None):
        self.dprint("%s called by keybindings" % self)
        self.action(self.frame.getCurrentViewer())


class Minibuffer(object):
    def __init__(self,viewer):
        self.viewer=viewer
        self.minibuffer(viewer)
        
    def minibuffer(self,viewer):
        # set self.win to the minibuffer window
        pass

    def focus(self):
        print "focus!!!"
        self.win.SetFocus()
    
    def close(self):
        self.win.Destroy()
        self.win=None


class MinibufferAction(ViewAction):
    def action(self, viewer, state=None, pos=-1):
        minibuffer=self.minibuffer(viewer)
        print minibuffer.win
        viewer.setMinibuffer(minibuffer)

#### Icons

class IconStorage(debugmixin):
    def __init__(self):
        self.il=wx.ImageList(16,16)
        self.map={}

    def get(self,filename):
        if filename not in self.map:
            img=wx.ImageFromBitmap(wx.Bitmap(filename))
            img.Rescale(16,16)
            bitmap=wx.BitmapFromImage(img)
            icon=self.il.Add(bitmap)
            self.dprint("ICON=%s" % str(icon))
            self.dprint(img)
            self.map[filename]=icon
        else:
            self.dprint("ICON: found icon for %s = %d" % (filename,self.map[filename]))
        return self.map[filename]

    def assign(self,notebook):
        # Don't use AssignImageList because the notebook takes
        # ownership of the image list and will delete it when the
        # notebook is deleted.  We're sharing the list, so we don't
        # want the notebook to delete it if the notebook itself
        # deletes it.
        notebook.SetImageList(self.il)

_iconStorage=None
def getIconStorage(icon=None):
    global _iconStorage
    if _iconStorage==None:
        _iconStorage=IconStorage()
    if icon:
        return _iconStorage.get(icon)
    else:
        return _iconStorage




#### View base class

class View(debugmixin,ClassSettingsMixin):
    debuglevel=0
    
    pluginkey = '-none-'
    icon='icons/page_white.png'
    keyword='Unknown'
    temporary=False # True if it is a temporary view
    defaultsettings={
        'menu_actions':[],
        'toolbar_actions':[],
        'keyboard_actions':[],
        }

    # Need one keymap per subclass, so we can't use the settings.
    # Settings would propogate up the class hierachy and find a keymap
    # of a superclass.  This is a dict based on the class name.
    localkeymaps={}
    
    def __init__(self,buffer,frame):
        ClassSettingsMixin.__init__(self)
        self.win=None
        self.splitter=None
        self.editwin=None
        self.minibuffer=None
        self.sidebar=None
        self.stc=BlankSTC
        self.buffer=buffer
        self.frame=frame
        self.popup=None

    def __del__(self):
        dprint("deleting %s %s" % (self.__class__.__name__,self.getTabName()))

    # If there is no title, return the keyword
    def getTitle(self):
        return self.keyword

    def getTabName(self):
        return self.buffer.getTabName()

    def getIcon(self):
        return getIconStorage(self.icon)
    
    def createWindow(self,parent):
        self.win=wx.Panel(parent, -1, style=wx.NO_BORDER)
        box=wx.BoxSizer(wx.VERTICAL)
        self.win.SetAutoLayout(True)
        self.win.SetSizer(box)
        self.splitter=wx.SplitterWindow(self.win)
        self.splitter.SetSplitMode(wx.SPLIT_VERTICAL)
        box.Add(self.splitter,1,wx.EXPAND)
        self.editwin=self.createEditWindow(self.splitter)
        self.splitter.Initialize(self.editwin)
        self.splitter.SetMinimumPaneSize(10)

    def createEditWindow(self,parent):
        win=wx.Window(parent, -1)
        win.SetBackgroundColour(wx.ColorRGB(0xabcdef))
        text=self.buffer.stc.GetText()
        wx.StaticText(win, -1, text, (10,10))
        return win

    def setMinibuffer(self,minibuffer=None):
        self.removeMinibuffer()
        if minibuffer is not None:
            self.minibuffer=minibuffer
            box=self.win.GetSizer()
            box.Add(self.minibuffer.win,0,wx.EXPAND)
            self.win.Layout()
            self.minibuffer.win.Show()
            self.minibuffer.focus()

    def removeMinibuffer(self):
        if self.minibuffer is not None:
            box=self.win.GetSizer()
            box.Detach(self.minibuffer.win)
            self.minibuffer.close()
            self.minibuffer=None
            self.win.Layout()

    def reparent(self,parent):
        self.win.Reparent(parent)

    def getMenuActions(self):
        actions=self.settings._getList('menu_actions')
        self.dprint("getMenuActions: %s %s" % (self,actions))
        return actions

    def getToolbarActions(self):
        actions=self.settings._getList('toolbar_actions')
        self.dprint("getToolbarActions: %s %s" % (self,actions))
        return actions

    def getLocalKeyMap(self):
        if self.__class__.__name__ not in self.localkeymaps:
            actions=self.settings._getList('keyboard_actions')
            self.dprint("keyboard actions=%s" % actions)
            self.localkeymaps[self.__class__.__name__]=self.frame.createKeyMap(actions)
            self.dprint("created keymap %s for class %s" % (self.localkeymaps[self.__class__.__name__],self.__class__.__name__))
        else:
            self.dprint("found keymap %s for class %s" % (self.localkeymaps[self.__class__.__name__],self.__class__.__name__))
        return self.localkeymaps[self.__class__.__name__]

    def addPopup(self,popup):
        self.popup=popup
        self.win.Bind(wx.EVT_RIGHT_DOWN, self.popupMenu)

    def popupMenu(self,evt):
        # popups generate menu events as normal menus, so the
        # callbacks to the command objects should still work if the
        # popup is generated in the same way that the regular menu and
        # toolbars are.
        self.dprint("popping up menu for %s" % evt.GetEventObject())
        self.win.PopupMenu(self.popup)
        evt.Skip()

    def openPostHook(self):
        pass

    def open(self):
        self.dprint("View: open docptr=%s" % self.buffer.docptr)
        if self.buffer.docptr:
            # the docptr is a real STC, so use it as the base document
            # for the new view
            self.stc.AddRefDocument(self.buffer.docptr)
            self.stc.SetDocPointer(self.buffer.docptr)
        self.openPostHook()

    def close(self):
        self.dprint("View: closing view %s of buffer %s" % (self,self.buffer))
        #self.stc.ReleaseDocument(self.buffer.docptr)
        self.win.Destroy()
        # remove reference to this view in the buffer's listeners
        self.buffer.remove(self)
        pass

    def focus(self):
        #self.dprint("View: setting focus to %s" % self)
        self.editwin.SetFocus()

    def showModified(self,modified):
        self.frame.showModified(self)
        self.frame.enableMenu()



class IViewFactory(Interface):
    def viewScore(buffer):
        """Return a number between 0 and 100 that represents the
        ability of the view to render the information in the buffer.
        0 = incapable of rendering, 100 = don't look any further
        because this is the one.  The greater the number, the more
        specific the renderer.  So, a renderer that just shows
        information about the file might have a score of 1; a generic
        text renderer might have a score of 10; and a python renderer
        for python text has a score of 100."""

    def getView(buffer):
        """Return the class that represents this view."""

class ViewFactory(Component):
    implements(IViewFactory)

    def viewScore(self,buffer):
        return 1

    def getView(self,buffer):
        return View

class ViewFinder(Component,debugmixin):
    debuglevel=1
    factories=ExtensionPoint(IViewFactory)

    def find(self,buffer):
        best=None
        bestscore=0
        for factory in self.factories:
            score=factory.viewScore(buffer)
            self.dprint("factory %s: score=%d" % (factory,score))
            if score>bestscore:
                best=factory.getView(buffer)
                bestscore=score
        return best

def GetView(buffer):
    comp_mgr=ComponentManager()
    finder=ViewFinder(comp_mgr)
    view=finder.find(buffer)
    return view



if __name__ == "__main__":
    pass

