import os,sys,re

import wx
import wx.stc as stc

from menudev import FrameAction
from stcinterface import *
from configprefs import *
from plugin import *
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


class ShiftLeft(ViewAction):
    name = "Shift &Left"
    tooltip = "Unindent a line region"
    icon = 'icons/text_indent_remove_rob.png'
    keyboard = 'S-TAB'

    def action(self, viewer, state=None, pos=-1):
        viewer.indent(-1)

class ShiftRight(ViewAction):
    name = "Shift &Right"
    tooltip = "Indent a line or region"
    icon = 'icons/text_indent_rob.png'
    keyboard = 'TAB'

    def action(self, viewer, state=None, pos=-1):
        dprint("HERE!!!")
        viewer.indent(1)

class ElectricReturn(ViewAction):
    name = "Electric Return"
    tooltip = "Indent the next line following a return"
    icon = 'icons/text_indent_rob.png'
    keyboard = 'RET'

    def action(self, viewer, state=None, pos=-1):
        viewer.electricReturn()



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




#### MajorMode base class

class MajorMode(debugmixin,ClassSettingsMixin):
    """
    Base class for all major modes.  Subclasses need to implement at
    least createEditWindow that will return the main user interaction
    window.
    """
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
        dprint("deleting %s: buffer=%s" % (self.__class__.__name__,self.buffer))
        dprint("deleting %s: %s" % (self.__class__.__name__,self.getTabName()))

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
        if isinstance(self.editwin,MySTC):
            self.editwin.Bind(stc.EVT_STC_UPDATEUI, self.OnUpdateUI)

        from pype.codetree import hierCodeTreePanel
        self.funclist=hierCodeTreePanel(self,self.splitter,False)
        fl=self.getFunctionList()
        self.funclist.new_hierarchy(fl[0])
        ## self.splitter.Initialize(self.editwin)
        self.splitter.SplitVertically(self.editwin,self.funclist,-200)
        self.splitter.SetMinimumPaneSize(0)
        self.splitter.SetSashGravity(0.75)
        if not fl[0]:
            self.splitter.Unsplit(self.funclist)

    def OnUpdateUI(self,evt):
        dprint("OnUpdateUI for view %s, frame %s" % (self.keyword,self.frame))
        linenum = self.editwin.GetCurrentLine()
        pos = self.editwin.GetCurrentPos()
        col = self.editwin.GetColumn(pos)
        self.frame.SetStatusText("L%d C%d" % (linenum+1,col+1),1)

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
            self.focus()

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

    def getFunctionList(self):
        '''
        Return a list of tuples, where each tuple contains information
        about a notable line in the source code corresponding to a
        class, a function, a todo item, etc.
        '''
        return ([], [], {}, [])

    def indent(self, direction):
        """
        Indent (or unindent) a region.  The absolute value of the
        direction parameter is the number of tab stops to indent (or
        unindent).

        @param direction: positive to indent, negative to unindent;
        @type direction: int
        """
        pass

    def electricReturn(self):
        """
        Indent the next line to the appropriate level.  This is called
        instead of letting the STC handle a return press on its own.
        """
        pass

    def getNumWin(self, evt=None):
        """PyPE compat"""
        return 1,self.editwin




class MajorModeMatcherDriver(Component,debugmixin):
    debuglevel=0
    plugins=ExtensionPoint(IMajorModeMatcher)

    def parseEmacs(self,line):
        """
        Parse a potential emacs major mode specifier line into the
        mode and the optional variables.  The mode may appears as any
        of::

          -*-C++-*-
          -*- mode: Python; -*-
          -*- mode: Ksh; var1:value1; var3:value9; -*-

        @param line: first or second line in text file
        @type line: string
        @return: two-tuple of the mode and a dict of the name/value pairs.
        @rtype: tuple
        """
        match=re.search(r'-\*\-\s*(mode:\s*(.+?)|(.+?))(\s*;\s*(.+?))?\s*-\*-',line)
        if match:
            vars={}
            varstring=match.group(5)
            if varstring:
                try:
                    for nameval in varstring.split(';'):
                        s=nameval.strip()
                        if s:
                            name,val=s.split(':')
                            vars[name.strip()]=val.strip()
                except:
                    pass
            if match.group(2):
                return (match.group(2),vars)
            elif match.group(3):
                return (match.group(3),vars)
        return None

    def find(self,buffer):
        """
        Determine the best possible L{View} subclass for the given
        buffer.  See L{IMajorModeMatcher} for more information on designing
        plugins that this method uses.

        Emacs-style major mode strings are searched for first, and if
        a match is found, immediately returns that View.  Bangpath
        lines are then searched, also returning immediately if
        identified.

        If neither of those cases match, a more complicated search
        procedure is used.  If a filename match is determined to be an
        exact match, that View is used.  But, if the filename match is
        only a generic match, searching continues.  Magic values
        within the file are checked, and again if an exact match is
        found the View is returned.

        If only generic matches are left ... figure out some way to
        choose the best one.

        @param buffer: the buffer of interest
        @type buffer: L{Buffer<buffers.Buffer>}

        @returns: the best view for the buffer
        @rtype: L{View} subclass
        """
        
        bangpath=buffer.stc.GetLine(0)
        if bangpath.startswith('#!'):
            emacs=self.parseEmacs(bangpath + buffer.stc.GetLine(1))
        else:
            emacs=self.parseEmacs(bangpath)
            bangpath=None
        self.dprint("bangpath=%s" % bangpath)
        self.dprint("emacs=%s" % emacs)
        best=None
        generics=[]
        if emacs is not None:
            for plugin in self.plugins:
                best=plugin.scanEmacs(*emacs)
                if best is not None:
                    if best.exact:
                        return best.view
                    else:
                        self.dprint("scanEmacs: appending generic %s" % best.view)
                        generics.append(best)
        if bangpath is not None:
            for plugin in self.plugins:
                best=plugin.scanShell(bangpath)
                if best is not None:
                    if best.exact:
                        return best.view
                    else:
                        self.dprint("scanShell: appending generic %s" % best.view)
                        generics.append(best)
        for plugin in self.plugins:
            best=plugin.scanFilename(buffer.filename)
            if best is not None:
                if best.exact:
                    return best.view
                else:
                    self.dprint("scanFilename: appending generic %s" % best.view)
                    generics.append(best)
        for plugin in self.plugins:
            best=plugin.scanMagic(buffer)
            if best is not None:
                if best.exact:
                    return best.view
                else:
                    self.dprint("scanMagic: appending generic %s" % best.view)
                    generics.append(best)
        if generics:
            self.dprint("Choosing from generics: %s" % [g.view for g in generics])
            # FIXME: don't just use the first one, do something smarter!
            return generics[0].view
        else:
            # FIXME: need to specify the global default mode, but not
            # like this.  The plugins should manage it.  Maybe add a
            # method to the IMajorModeMatcher to see if this mode is
            # the default mode.
            return FundamentalMode

def GetMajorMode(buffer):
    """
    Application-wide entry point used to find the best view for the
    given buffer.

    @param buffer: the newly loaded buffer
    @type buffer: L{Buffer<buffers.Buffer>}
    """
    
    comp_mgr=ComponentManager()
    driver=MajorModeMatcherDriver(comp_mgr)
    view=driver.find(buffer)
    return view
