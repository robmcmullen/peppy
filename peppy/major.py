# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
import os,sys,re

import wx
import wx.stc as stc

from menu import SelectAction
from stcinterface import *
from configprefs import *
from debug import *
from iconstorage import *
from minor import *


class MajorAction(SelectAction):
    # Set up a new run() method to pass the viewer
    def action(self, pos=-1):
        self.dprint("id=%s name=%s" % (id(self),self.name))
        self.majoraction(self.frame.getActiveMajorMode(),pos)

    def majoraction(self, viewer, pos=-1):
        raise NotImplementedError

    # Set up a new keyboard callback to also pass the viewer
    def __call__(self, evt, number=None):
        self.dprint("%s called by keybindings" % self)
        self.majoraction(self.frame.getActiveMajorMode())


class ShiftLeft(MajorAction):
    name = "Shift &Left"
    tooltip = "Unindent a line region"
    icon = 'icons/text_indent_remove_rob.png'
    keyboard = 'S-TAB'

    def majoraction(self, viewer, pos=-1):
        viewer.indent(-1)

class ShiftRight(MajorAction):
    name = "Shift &Right"
    tooltip = "Indent a line or region"
    icon = 'icons/text_indent_rob.png'
    keyboard = 'TAB'

    def majoraction(self, viewer, pos=-1):
        viewer.indent(1)

class ElectricReturn(MajorAction):
    name = "Electric Return"
    tooltip = "Indent the next line following a return"
    icon = 'icons/text_indent_rob.png'
    keyboard = 'RET'

    def majoraction(self, viewer, pos=-1):
        viewer.electricReturn()


#### MajorMode base class

class MajorMode(wx.Panel,debugmixin,ClassSettingsMixin):
    """
    Base class for all major modes.  Subclasses need to implement at
    least createEditWindow that will return the main user interaction
    window.
    """
    debuglevel=0
    
    icon='icons/page_white.png'
    keyword='Abstract Major Mode'
    temporary=False # True if it is a temporary view

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
        self.stc=NullSTC()
        self.buffer=buffer
        self.frame=frame
        self.popup=None
        
        wx.Panel.__init__(self, frame.tabs, -1, style=wx.NO_BORDER)
        self.win=self
        self.createWindow()
        self.createWindowPostHook()

    def __del__(self):
        dprint("deleting %s: buffer=%s" % (self.__class__.__name__,self.buffer))
        dprint("deleting %s: %s" % (self.__class__.__name__,self.getTabName()))
        self.deleteWindowPostHook()

    # If there is no title, return the keyword
    def getTitle(self):
        return self.keyword

    def getTabName(self):
        return self.buffer.getTabName()

    def getIcon(self):
        return getIconStorage(self.icon)

    def getWelcomeMessage(self):
        return "%s major mode" % self.keyword
    
    def createWindow(self):
        box=wx.BoxSizer(wx.VERTICAL)
        self.win.SetAutoLayout(True)
        self.win.SetSizer(box)
        self.splitter=wx.Panel(self.win)
        box.Add(self.splitter,1,wx.EXPAND)
        self._mgr = wx.aui.AuiManager()
        self._mgr.SetManagedWindow(self.splitter)
        self.editwin=self.createEditWindow(self.splitter)
        self._mgr.AddPane(self.editwin, wx.aui.AuiPaneInfo().Name("main").
                          CenterPane())
        if isinstance(self.editwin,MySTC):
            self.editwin.Bind(stc.EVT_STC_UPDATEUI, self.OnUpdateUI)

        self.loadMinorModes()
        
        self._mgr.Update()

    def createWindowPostHook(self):
        pass

    def deleteWindow(self):
        self.dprint("closing view %s of buffer %s" % (self,self.buffer))
        # remove reference to this view in the buffer's listeners
        self.buffer.remove(self)
        self.Destroy()

    def deleteWindowPostHook(self):
        pass

    def addPane(self, win, paneinfo):
        self._mgr.AddPane(win, paneinfo)

    def loadMinorModes(self):
        minors=self.settings.minor_modes
        self.dprint(minors)
        if minors is not None:
            minorlist=minors.split(',')
            self.dprint("loading %s" % minorlist)
            MinorModeLoader(ComponentManager()).load(self,minorlist)

    def createMinorMode(self,minorcls):
        try:
            minor=minorcls(self,self.splitter)
            # register minor mode here
        except MinorModeIncompatibilityError:
            pass

    def OnUpdateUI(self,evt):
        self.dprint("OnUpdateUI for view %s, frame %s" % (self.keyword,self.frame))
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

    def focus(self):
        #self.dprint("View: setting focus to %s" % self)
        self.editwin.SetFocus()

    def showModified(self,modified):
        self.frame.showModified(self)

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



class MajorModeMatch(object):
    """
    Return type of a L{IMajorModeMatcher} when a successful match is
    made.  In addition of the View class, any name/value pairs
    specific to this file can be passed back to the caller, as well as
    an indicator if the match is exact or generic.

    """
    
    def __init__(self,view,generic=False,exact=True,editable=True):
        self.view=view
        self.vars={}
        if generic:
            self.exact=False
        else:
            self.exact=True
        self.editable=True


class IMajorModeMatcher(Interface):
    """
    Interface that
    L{MajorModeMatcherDriver<views.MajorModeMatcherDriver>} uses to
    determine if a View represented by this plugin is capable of
    viewing the data in the buffer.  (Note that one IMajorModeMatcher
    may represent more than one View.)  Several methods are used in an
    attempt to pick the best match for the data in the buffer.

    First, if the first non-blank line in the buffer (or second line
    if the first contains the shell string C{#!}) contains the emacs
    mode, the L{scanEmacs} method will be called to see if your plugin
    recognizes the emacs major mode string within the C{-*-} delimiters.

    Secondly, if the first line starts with C{#!}, the rest of the line
    is passed to L{scanShell} method to see if it looks like an shell
    command.

    If neither of these methods return a View, then the user hasn't
    explicitly named the view, so we need to determine which View to
    use based on either the filename or by scanning the contents.

    The first of the subsequent search methods is also the simplest:
    L{scanFilename}.  If a pattern (typically the filename extension)
    is recognized, that view is used.

    Next in order, L{scanMagic} is called to see if some pattern in
    the text can be used to identify the file type.
    """

    def scanEmacs(emacsmode,vars):
        """
        This method is called if the first non-blank line in the
        buffer (or second line if the first contains the shell string
        C{#!}) contains an emacs major mode specifier.  Emacs
        recognizes a string in the form of::

          -*-C++-*-
          -*- mode: Python; -*-
          -*- mode: Ksh; var1:value1; var3:value9; -*-
      
        The text within the delimiters is parsed by the
        L{MajorModeMatcherDriver<views.MajorModeMatcherDriver>}, and
        two parameters are passed to this method.  The emacs mode
        string is passed in as C{emacsmode}, and any name/value pairs
        are passed in the C{vars} dict (which could be empty).  It is
        not required that your plugin understand and process the
        variables.

        If your plugin recognizes the emacs major mode string, return
        a L{MajorModeMatch} object that contains the View class.
        Otherwise, return None and the
        L{MajorModeMatcherDriver<views.MajorModeMatcherDriver>} will
        continue processing.

        @param emacsmode: text string of the Emacs major mode
        @type emacsmode: string
        @param vars: name:value pairs, can be the empty list
        @type vars: list
        """

    def scanShell(bangpath):
        """
        Called if the first line starts with the system shell string
        C{#!}.  The remaining characters from the first line are
        passed in as C{bangpath}.

        If your plugin recognizes something in the shell string,
        return a L{MajorModeMatch} object that contains the View class and
        the L{MajorModeMatcherDriver<views.MajorModeMatcherDriver>}
        will stop looking and use than View.  If not, return None and
        the L{MajorModeMatcherDriver<views.MajorModeMatcherDriver>}
        will continue processing.

        @param bangpath: characters after the C{#!}
        @type bangpath: string
        """

    def scanFilename(filename):
        """
        Called to see if a pattern in the filename can be identified
        that determines the file type and therefore the
        L{View<views.View>} that should be used.

        If your plugin recognizes something, return a L{MajorModeMatch}
        object with the optional indicators filled in.  If not, return
        None and the
        L{MajorModeMatcherDriver<views.MajorModeMatcherDriver>} will
        continue processing.

        @param filename: filename, can be in URL form
        @type filename: string
        """
    
    def scanMagic(buffer):
        """
        Called to see if a pattern in the text can be identified that
        determines the file type and therefore the L{View<views.View>}
        that should be used.

        If your plugin recognizes something, return a L{MajorModeMatch}
        object with the optional indicators filled in.  If not, return
        None and the
        L{MajorModeMatcherDriver<views.MajorModeMatcherDriver>} will
        continue processing.

        @param buffer: buffer of already loaded file
        @type buffer: L{Buffer<buffers.Buffer>}
        """

class MajorModeMatcherBase(Component):
    """
    Simple do-nothing base class for L{IMajorModeMatcher}
    implementations so that you don't have to provide null methods for
    scans you don't want to implement.

    @see: L{IMajorModeMatcher} for the interface description

    @see: L{FundamentalPlugin<fundamental.FundamentalPlugin>} or
    L{PythonPlugin} for examples.
    """
    def scanEmacs(self,emacsmode,vars):
        return None

    def scanShell(self,bangpath):
        return None

    def scanFilename(self,filename):
        return None
    
    def scanMagic(self,buffer):
        return None
    


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
        Determine the best possible L{MajorMode} subclass for the
        given buffer.  See L{IMajorModeMatcher} for more information
        on designing plugins that this method uses.

        Emacs-style major mode strings are searched for first, and if
        a match is found, immediately returns that MajorMode.
        Bangpath lines are then searched, also returning immediately
        if identified.

        If neither of those cases match, a more complicated search
        procedure is used.  If a filename match is determined to be an
        exact match, that MajorMode is used.  But, if the filename
        match is only a generic match, searching continues.  Magic
        values within the file are checked, and again if an exact
        match is found the MajorMode is returned.

        If only generic matches are left ... figure out some way to
        choose the best one.

        @param buffer: the buffer of interest
        @type buffer: L{Buffer<buffers.Buffer>}

        @returns: the best view for the buffer
        @rtype: L{MajorMode} subclass
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
