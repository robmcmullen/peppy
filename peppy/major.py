# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Base module for major mode implementations.

Implementing a new major mode means to extend from the L{MajorMode}
base class and at least implement the createEditWindow method.
Several attributes must be set: C{icon} that points to the filename of
the icon to be used, and C{keyword} which is a text string that
uniquely identifies the major mode from other major modes.  [FIXME:
more documentation here.]

Once the major mode subclass has been created, it must be announced to
peppy.  This is done by creating another class that extends from
L{MajorModeMatcherBase} and implements the L{IMajorModeMatcher}
interface.  This interface is used by the file loader to determine
which major mode gets the default view of a file when it is opened.

Because MajorModeMatcherBase is a trac component, all you have to do
is list your new module in the plugin path specified in your
configuration directory, and it will get picked up the next time peppy
starts.  You can also place them in your python's [FIXME: some
directory to be added like site-packages/peppy/autoload] directory
which is always scanned by peppy as it starts.

To provide user interface objects, you can add the
L{IMenuItemProvider} and L{IToolBarItemProvider} interfaces to your
subclass of L{IMajorModeMatcher} and implement the methods that those
require to add menu items or toolbar items.  Note that the first
element of the tuple returned by getMenuItems or getToolBarItems will
be the C{keyword} attribute of your major mode.
"""

import os,sys,re

import wx
import wx.stc
from wx.lib.pubsub import Publisher

from menu import *
from stcinterface import *
from configprefs import *
from debug import *
from minor import *
from iofilter import *

from lib.iconstorage import *
from lib.controls import *

class BufferBusyActionMixin(object):
    """Mixin to disable an action when the buffer is being modified.

    If a subclass needs to supply more information about its enable
    state, override isActionAvailable instead of isEnabled, or else
    you lose the buffer busy test.
    """
    def isEnabled(self):
        mode = self.frame.getActiveMajorMode()
        if mode is not None:
            return not mode.buffer.busy and self.isActionAvailable(mode)
        return False

    def isActionAvailable(self, mode):
        return True

class BufferModificationAction(BufferBusyActionMixin, SelectAction):
    """Base class for any action that changes the bytes in the buffer.

    This uses the BufferBusyActionMixin to disable any action that
    would change the buffer when the buffer is in the process of being
    modified by a long-running process.
    """
    # Set up a new run() method to pass the viewer
    def action(self, pos=-1):
        assert self.dprint("id=%s name=%s" % (id(self),self.name))
        self.modify(self.frame.getActiveMajorMode(),pos)

    def modify(self, mode, pos=-1):
        raise NotImplementedError

    # Set up a new keyboard callback to also pass the viewer
    def __call__(self, evt, number=None):
        assert self.dprint("%s called by keybindings" % self)
        self.modify(self.frame.getActiveMajorMode())


class MajorModeSelect(BufferBusyActionMixin, RadioAction):
    name=_("Major Mode")
    inline=False
    tooltip=_("Switch major mode")

    modes=None
    items=None

    def initPreHook(self):
        currentmode = self.frame.getActiveMajorMode()
        modes = getSubclasses(MajorMode)

        # Only display those modes that use the same type of STC as
        # the current mode.
        modes = [m for m in modes if m.stc_class == currentmode.stc_class]
        
        modes.sort(key=lambda s:s.keyword)
        assert self.dprint(modes)
        MajorModeSelect.modes = modes
        names = [m.keyword for m in modes]
        MajorModeSelect.items = names

    def saveIndex(self,index):
        assert self.dprint("index=%d" % index)

    def getIndex(self):
        modecls = self.frame.getActiveMajorMode().__class__
        assert self.dprint("searching for %s in %s" % (modecls, MajorModeSelect.modes))
        if modecls is not None.__class__:
            return MajorModeSelect.modes.index(modecls)
        return 0
                                           
    def getItems(self):
        return MajorModeSelect.items

    def action(self, index=0, old=-1):
        self.frame.changeMajorMode(MajorModeSelect.modes[index])


#### MajorMode base class

class MajorMode(wx.Panel,debugmixin,ClassSettings):
    """
    Base class for all major modes.  Subclasses need to implement at
    least createEditWindow that will return the main user interaction
    window.
    """
    debuglevel = 0
    
    icon = 'icons/page_white.png'
    keyword = 'Abstract Major Mode'
    emacs_synonyms = None
    
    regex = None
    temporary = False # True if it is a temporary view

    # stc_class is used to associate this major mode with a storage
    # mechanism (implementing the STCInterface).  The default is
    # PeppySTC, which is a subclass of the scintilla editor.
    stc_class = PeppySTC

    default_settings = {
        'line_number_offset': 1,
        'column_number_offset': 1,
        }

    # Need one keymap per subclass, so we can't use the settings.
    # Settings would propogate up the class hierachy and find a keymap
    # of a superclass.  This is a dict based on the class name.
    localkeymaps = {}
    
    def __init__(self,buffer,frame):
        self.splitter=None
        self.editwin=None # user interface window
        self.minibuffer=None
        self.sidebar=None
        self.stc=None # data store
        self.buffer=buffer
        self.frame=frame
        self.popup=None
        self.minors=[]
        self.minor_panes = []
        self.statusbar = None
        
        wx.Panel.__init__(self, frame.tabs, -1, style=wx.NO_BORDER)
        self.createWindow()
        self.createWindowPostHook()
        self.loadMinorModes()
        self.loadMinorModesPostHook()
        self.createEventBindings()
        self.createEventBindingsPostHook()
        self.createListeners()
        self.createListenersPostHook()
        self.createPostHook()
        
        self._mgr.Update()

    def __del__(self):
        dprint("deleting %s: buffer=%s" % (self.__class__.__name__,self.buffer))
        dprint("deleting %s: %s" % (self.__class__.__name__,self.getTabName()))
        self.removeListeners()
        self.removeListenersPostHook()
        self.deleteWindowPostHook()

    @classmethod
    def verifyProtocol(cls, url):
        """Hook to short-circuit the mode matching heuristics.

        For non-editing applications and client applications that
        connect to a server, this hook provides the ability to
        short-circuit the matching process and open a mode
        immediately.

        This method must not attempt to open the url and read any
        data.  All modes' verifyProtocol methods are called before the
        file is attempted to be opened, and attempting to read data
        here could mess up streaming files.

        @param url: URLInfo object

        @returns: True to short circuit and use this mode.
        """
        return False

    @classmethod
    def verifyFilename(cls, filename):
        """Hook to verify filename matches the default regular
        expression for this mode.

        @param filename: the pathname part of the url (i.e. not the
        protocol, port number, query string, or anything else)

        @returns: True if the filename matches
        """
        if cls.regex:
            match=re.search(cls.regex, filename)
            if match:
                return True
        return False

    @classmethod
    def verifyMagic(cls, header):
        """Hook to verify the file is acceptable to this mode.

        If the file can be identified by magic characters within the
        first n bytes (typically n < 1024), return a flag that
        indicates whether or not this file can be opened by this mode.

        @param header: string with the first n characters of the file
        
        @returns: True if the magic was identified exactly, False if
        the file is not capable of being opened by this mode, or None
        if indeterminate.
        """
        return None

    @classmethod
    def attemptOpen(cls, url):
        """Last resort to major mode matching: attempting to open the url.

        This method is the last resort if all other pattern matching
        and mode searching fails.  Typically, this is only an issue
        with non-Scintilla editors that use third-party file loading
        libraries.

        @returns: True if the open was successful or False if not.
        """
        return False

    def save(self, url=None):
        veto = self.savePreHook(url)
        if veto == False:
            return
        self.buffer.save(url)
        self.savePostHook()

    def savePreHook(self, url=None):
        """Hook before the buffer is saved.

        The save is vetoable by returning False.  Returning True or
        None (None is also returned when you don't explicitly return
        anything) allows the save to continue.
        """
        pass

    def savePostHook(self):
        """Hook to perform any housekeeping after a save"""
        pass

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
        """Non-user-callable routine to create the main window.

        Users should override createEditWindow to generate the main
        window, and can also override createWindowPostHook to add any
        non-window resources to the major mode.
        """
        box=wx.BoxSizer(wx.VERTICAL)
        self.SetAutoLayout(True)
        self.SetSizer(box)
        self.splitter=wx.Panel(self)
        box.Add(self.splitter,1,wx.EXPAND)
        self._mgr = wx.aui.AuiManager()
        self._mgr.SetManagedWindow(self.splitter)
        self.editwin=self.createEditWindow(self.splitter)
        self._mgr.AddPane(self.editwin, wx.aui.AuiPaneInfo().Name("main").
                          CenterPane())

    def createWindowPostHook(self):
        """User hook to add resources after the edit window is created.
        """
        pass

    def deleteWindowPre(self):
        """Manager routine to delete resources before the main window
        is deleted.

        Not called from user code; override deleteWindowPreHook to add
        user code to the delete process.
        """
        self.deleteWindowPreHook()
        self.deleteMinorModes()

    def deleteWindowPreHook(self):
        """Hook to remove resources before windows are deleted.

        This is called before anything is deleted.  Don't try to
        delete any of the resources that are automatically managed
        (i.e. minor modes, windows, toolbars, etc.) or BadThings(tm)
        will happen.
        """
        pass

    def deleteWindow(self):
        # remove reference to this view in the buffer's listeners
        assert self.dprint("closing view %s of buffer %s" % (self,self.buffer))
        self.buffer.remove(self)

        self.deleteWindowPre()

        assert self.dprint("destroying window %s" % (self))
        self.Destroy()

    def deleteWindowPostHook(self):
        """Hook after all widgets are deleted.

        This is called after all windows have been deleted, in case
        there are any non-window references to clean up.
        """
        pass

    def createEventBindings(self):
        if hasattr(self.editwin,'addUpdateUIEvent'):
            self.editwin.addUpdateUIEvent(self.OnUpdateUI)
        
        self.editwin.Bind(wx.EVT_KEY_DOWN, self.frame.OnKeyPressed)

        self.idle_update_menu = False
        self.Bind(wx.EVT_IDLE, self.OnIdle)

    def createEventBindingsPostHook(self):
        pass

    def createListeners(self):
        """Required wx.lib.pubsub listeners are created here.

        Subclasses should override createListenersPostHook to add
        their own listeners.
        """
        Publisher().subscribe(self.resetStatusBar, 'resetStatusBar')
        Publisher().subscribe(self.settingsChanged, 'settingsChanged')

    def createListenersPostHook(self):
        """Hook to add custom listeners.

        Subclasses should override this method rather than
        createListeners to add their own listeners.
        """
        pass

    def removeListeners(self):
        """Required wx.lib.pubsub listeners are removed here.

        Subclasses should override removeListenersPostHook to remove
        any listeners that were added.  Normally, wx.lib.pubsub
        removes references to dead objects, and so this cleanup
        shouldn't be necessary.  But, because the MajorMode is
        subclassed from the C++ object, the python part is removed but
        the C++ part isn't cleaned up immediately.  So, we have to
        remove the listener references manually.
        """
        Publisher().unsubscribe(self.resetStatusBar)
        Publisher().unsubscribe(self.settingsChanged)

    def removeListenersPostHook(self):
        """Hook to remove custom listeners.

        Any listeners added by subclasses in createListenersPostHook
        should be removed here.
        """
        pass

    def loadMinorModes(self):
        """Find the listof minor modes to load and create them."""
        
        minor_list = self.settings.minor_modes
        assert self.dprint(minor_list)
        if minor_list is not None:
            minor_names=minor_list.split(',')
            assert self.dprint("loading %s" % minor_names)

            # convert the list of strings into the corresponding list
            # of classes
            minors = MinorModeLoader(ComponentManager()).getClasses(self, minor_names)
            assert self.dprint("found class list: %s" % str(minors))
            for minorcls in minors:
                self.createMinorMode(minorcls)
            self.createMinorPaneList()

    def loadMinorModesPostHook(self):
        """User hook after all minor modes have been loaded.

        Use this hook if you need to initialize the set of minor modes
        after all of them have been loaded.
        """
        pass

    def createMinorMode(self, minorcls):
        """Create minor modes and register them with the AUI Manager."""
        try:
            minor=minorcls(self, self.splitter)
            # register minor mode here
            if isinstance(minor, wx.Window):
                paneinfo = minor.getPaneInfo()
                self._mgr.AddPane(minor, paneinfo)
            self.minors.append(minor)

            # A different paneinfo object is stored in the AUIManager,
            # so we have to get it's version rather than using the
            # paneinfo we generate
            minor.paneinfo = self._mgr.GetPane(minor)
        except MinorModeIncompatibilityError:
            pass

    def createMinorPaneList(self):
        """Create alphabetized list of minor modes.

        This is used by the menu system to display the list of minor
        modes to the user.
        """
        self.minor_panes = []
        panes = self._mgr.GetAllPanes()
        for pane in panes:
            assert self.dprint("name=%s caption=%s window=%s state=%s" % (pane.name, pane.caption, pane.window, pane.state))
            if pane.name != "main":
                self.minor_panes.append(pane)
        self.minor_panes.sort(key=lambda s:s.caption)

    def findMinorMode(self, name):
        for minor in self.minors:
            if minor.keyword == name:
                return minor
        return None

    def deleteMinorModes(self):
        """Remove the minor modes from the AUI Manager and delete them."""
        dprint()
        while len(self.minors)>0:
            minor = self.minors.pop()
            dprint("deleting minor mode %s" % (minor.keyword))
            minor.deletePreHook()
            if self._mgr.GetPane(minor):
                self._mgr.DetachPane(minor)
                minor.Destroy()

    def OnUpdateUI(self, evt):
        """Callback to update user interface elements.

        This event is called when the user interacts with the editing
        window, possibly creating a state change that would require
        some user interface elements to change state.

        Don't depend on this coming from the STC, as non-STC based
        modes won't have the STC_EVT_UPDATEUI event and may be calling
        this using other events.

        @param evt: some event of undetermined type
        """
        assert self.dprint("OnUpdateUI for view %s, frame %s" % (self.keyword,self.frame))
        linenum = self.editwin.GetCurrentLine()
        pos = self.editwin.GetCurrentPos()
        col = self.editwin.GetColumn(pos)
        self.frame.SetStatusText("L%d C%d F%d" % (linenum+self.settings.line_number_offset, col+self.settings.column_number_offset, self.editwin.GetFoldLevel(linenum)&wx.stc.STC_FOLDLEVELNUMBERMASK - wx.stc.STC_FOLDLEVELBASE),1)
        self.idle_update_menu = True
        self.OnUpdateUIHook(evt)
        if evt is not None:
            evt.Skip()

    def OnUpdateUIHook(self, evt):
        pass

    def OnIdle(self, evt):
        if self.idle_update_menu:
            # FIXME: calling the toolbar enable here is better than in
            # the update UI loop, but it still seems to cause flicker
            # in the paste icon.  What's up with that?
            self.frame.enableTools()
            self.idle_update_menu = False
        self.idlePostHook()
        evt.Skip()

    def idlePostHook(self):
        """Hook for subclasses to process during idle time.
        """
        pass

    def createEditWindow(self,parent):
        win=wx.Window(parent, -1)
        win.SetBackgroundColour(wx.ColorRGB(0xabcdef))
        text=self.buffer.stc.GetText()
        wx.StaticText(win, -1, text, (10,10))
        return win

    def createPostHook(self):
        """Hook called when everything has been created.

        This hook is called just before control is returned to the
        main application loop, i.e. after the edit window, minor
        modes, and all bindings and other hooks are called.
        """
        pass

    def createStatusIcons(self):
        """Create any icons in the status bar.

        This is called after making the major mode the active mode in
        the frame.  The status bar will be cleared to its initial
        empty state, so all this method has to do is add any icons
        that it needs.
        """
        pass

    def getStatusBar(self):
        """Returns pointer to this mode's status bar.

        Individual status bars are maintained by each instance of a
        major mode.  The frame only shows the status bar of the active
        mode and hides all the rest.  This means that modes may change
        their status bars without checking if they are the active
        mode.  This situation arizes when there is some background
        processing going on (either with threads or using wx.Yield)
        and the user switches to some other mode.
        """
        if self.statusbar is None:
            self.statusbar = PeppyStatusBar(self.frame)
            self.createStatusIcons()
        return self.statusbar

    def resetStatusBar(self, message=None):
        """Updates the status bar.

        This method clears and rebuilds the status bar, usually
        because something requests an icon change.
        """
        self.statusbar.reset()
        self.createStatusIcons()

    def setMinibuffer(self,minibuffer=None):
        self.removeMinibuffer()
        if minibuffer is not None:
            self.minibuffer=minibuffer
            box=self.GetSizer()
            box.Add(self.minibuffer.win,0,wx.EXPAND)
            self.Layout()
            self.minibuffer.win.Show()
            self.minibuffer.focus()

    def removeMinibuffer(self, detach_only=False):
        dprint(self.minibuffer)
        if self.minibuffer is not None:
            box=self.GetSizer()
            box.Detach(self.minibuffer.win)
            if not detach_only:
                # for those cases where you still want to keep a
                # pointer around to the minibuffer and close it later,
                # use detach_only
                self.minibuffer.close()
            self.minibuffer=None
            self.Layout()
            self.focus()

    def reparent(self,parent):
        self.Reparent(parent)

    def addPopup(self,popup):
        self.popup=popup
        self.Bind(wx.EVT_RIGHT_DOWN, self.popupMenu)

    def popupMenu(self,evt):
        # popups generate menu events as normal menus, so the
        # callbacks to the command objects should still work if the
        # popup is generated in the same way that the regular menu and
        # toolbars are.
        assert self.dprint("popping up menu for %s" % evt.GetEventObject())
        self.PopupMenu(self.popup)
        evt.Skip()

    def applySettings(self):
        """Apply settings to the view

        This is the place where settings for the class show their
        effects.  Calling this should update the view to reflect any
        changes in the settings.
        """
        pass

    def settingsChanged(self, message=None):
        dprint("changing settings for mode %s" % self.__class__.__name__)
        self.applySettings()       

    def focus(self):
        #assert self.dprint("View: setting focus to %s" % self)
        self.editwin.SetFocus()
        self.focusPostHook()

    def focusPostHook(self):
        pass

    def showModified(self,modified):
        self.frame.showModified(self)

    def showBusy(self, busy):
        self.Enable(not busy)
        if busy:
            cursor = wx.StockCursor(wx.CURSOR_WATCH)
        else:
            cursor = wx.StockCursor(wx.CURSOR_DEFAULT)
        self.editwin.SetCursor(cursor)

    def getFunctionList(self):
        '''
        Return a list of tuples, where each tuple contains information
        about a notable line in the source code corresponding to a
        class, a function, a todo item, etc.
        '''
        return ([], [], {}, [])



class IMajorModeMatcher(Interface):
    """Interface that plugins should use to announce new MajorModes.
    """

    def possibleModes():
        """Return list of possible major modes.

        A subclass that extends MajorModeMatcherBase should return a
        list or generator of all the major modes that this matcher is
        representing.  Generally, a matcher will only represent a
        single mode, but it is possible to represent more.

        @returns: list of MajorMode classes
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
    def possibleModes(self):
        """Return list of possible major modes.

        A subclass that extends MajorModeMatcherBase should return a
        list or generator of all the major modes that this matcher is
        representing.  Generally, a matcher will only represent a
        single mode, but it is possible to represent more.

        @returns: list of MajorMode classes
        """
        return []

def parseEmacs(line):
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
    return None, None

def guessBinary(text, percentage):
    """
    Guess if the text in this file is binary or text by scanning
    through the first C{amount} characters in the file and
    checking if some C{percentage} is out of the printable ascii
    range.

    Obviously this is a poor check for unicode files, so this is
    just a bit of a hack.

    @param amount: number of characters to check at the beginning
    of the file

    @type amount: int

    @param percentage: percentage of characters that must be in
    the printable ASCII range

    @type percentage: number

    @rtype: boolean
    """
    data = [ord(i) for i in text]
    binary=0
    for ch in data:
        if (ch<8) or (ch>13 and ch<32) or (ch>126):
            binary+=1
    if binary>(len(text)/percentage):
        return True
    return False

class MajorModeMatcherDriver(Component, debugmixin):
    debuglevel=0
    plugins=ExtensionPoint(IMajorModeMatcher)
    implements(IMenuItemProvider)

    default_menu=((_("View"),MenuItem(MajorModeSelect).first()),
                  )

    def getMenuItems(self):
        for menu,item in self.default_menu:
            yield (None,menu,item)

    @staticmethod
    def match(url, magic_size=None):
        comp_mgr=ComponentManager()
        driver=MajorModeMatcherDriver(comp_mgr)

        app = wx.GetApp()
        if magic_size is None:
            magic_size = app.settings.magic_size

        # Try to match a specific protocol
        modes = driver.scanProtocol(url)
        if modes:
            return modes[0]

        # ok, it's not a specific protocol.  Try to match a url pattern
        modes = driver.scanURL(url)
        fh = url.getReader(magic_size)
        header = fh.read(magic_size)

        url_match = None
        if modes:
            # OK, there is a match with the filenames.  Determine the
            # capability of the mode to edit the file by verifying any
            # magic bytes in the file
            capable = [m.verifyMagic(header) for m in modes]
            cm = zip(capable, modes)
            dprint(cm)

            # If there's an exact match, make a note of it
            for c, m in cm:
                if c is not None and c:
                    url_match = m
                    break

            if url_match is None:
                # if there's an acceptable one, make a note of it
                for c, m in cm:
                    if c is None:
                        url_match = m
                        break

        # Regardless if there's a match on the URL, try to match an
        # emacs mode specifier since a match here means that we should
        # override the match based on filename
        emacs_match = driver.scanEmacs(header)
        if emacs_match:
            return emacs_match

        # Like the emacs match, a match on a shell bangpath should
        # override anything determined out of the filename
        bang_match = driver.scanShell(header)
        if bang_match:
            return bang_match

        # Try to match some magic bytes that identify the file
        modes = driver.scanMagic(header)
        if modes:
            # It is unlikely that multiple modes will match the same magic
            # values, so just load the first one that we find
            return modes[0]

        # Now we get to the filename match above: if there had been a
        # match on a filename but nothing more specific, we can return
        # it because we've exhausted the other checks
        if url_match:
            return url_match

        # As a last resort to open a specific mode, attempt to open it
        # with any third-party openers that have been registered
        mode = driver.attemptOpen(url)
        if mode:
            return mode

        # If we fail all the tests, use a generic mode
        if guessBinary(header, app.settings.binary_percentage):
            return MajorModeMatcherDriver.findModeByName(app.settings.default_binary_mode)
        return MajorModeMatcherDriver.findModeByName(app.settings.default_text_mode)

    @staticmethod
    def findModeByName(name):
        comp_mgr=ComponentManager()
        driver=MajorModeMatcherDriver(comp_mgr)

        for plugin in driver.plugins:
            for mode in plugin.possibleModes():
                dprint("searching %s" % mode.keyword)
                if mode.keyword == name:
                    return mode
        return None

    def scanProtocol(self, url):
        """Scan for url protocol match.
        
        Determine if the protocol is enough to specify the major mode.
        This generally happens only when the major mode is a client of
        a specific server and not a generic editor.  (E.g. MPDMode)

        @param url: URLInfo object to scan
        
        @returns: list of matching L{MajorMode} subclasses
        """
        
        modes = []
        for plugin in self.plugins:
            for mode in plugin.possibleModes():
                dprint("scanning %s" % mode)
                if mode.verifyProtocol(url):
                    modes.append(mode)
        return modes

    def scanURL(self, url):
        """Scan for url filename match.
        
        Determine if the pathname matches some pattern that can
        identify the corresponding major mode.

        @param url: URLInfo object to scan
        
        @returns: list of matching L{MajorMode} subclasses
        """
        
        modes = []
        for plugin in self.plugins:
            for mode in plugin.possibleModes():
                if mode.verifyFilename(url.path):
                    modes.append(mode)
        return modes

    def scanMagic(self, header):
        """Scan for a pattern match in the first bytes of the file.
        
        Determine if there is a 'magic' pattern in the first n bytes
        of the file that can associate it with a major mode.

        @param header: first n bytes of the file
        
        @returns: list of matching L{MajorMode} subclasses
        """
        
        modes = []
        for plugin in self.plugins:
            for mode in plugin.possibleModes():
                if mode.verifyMagic(header):
                    modes.append(mode)
        return modes

    def scanEmacs(self, header):
        """Scan the first two lines of a file for an emacs mode
        specifier.
        
        Determine if an emacs mode specifier in the file can be
        associated with a major mode.

        @param header: first n bytes of the file
        
        @returns: matching L{MajorMode} subclass or None
        """
        
        modename, settings = parseEmacs(header)
        dprint("modename = %s, settings = %s" % (modename, settings))
        for plugin in self.plugins:
            for mode in plugin.possibleModes():
                if modename == mode.keyword:
                    return mode
                if mode.emacs_synonyms:
                    if isinstance(mode.emacs_synonyms, str):
                        if modename == mode.emacs_synonyms:
                            return mode
                    else:
                        if modename in mode.emacs_synonyms:
                            return mode
        return None
        
    def scanShell(self, header):
        """Scan the first lines of a file for a shell 'bangpath'
        specifier.
        
        Determine if a shell bangpath in the file can be associated
        with a major mode.

        @param header: first n bytes of the file
        
        @returns: matching L{MajorMode} subclass or None
        """
        
        if header.startswith("#!"):
            lines = header.splitlines()
            bangpath = lines[0].lower()
            for plugin in self.plugins:
                for mode in plugin.possibleModes():
                    keyword = mode.keyword.lower()

                    # only match words that are bounded by some sort
                    # of non-word delimiter.  For instance, if the
                    # mode is "test", it will match "/usr/bin/test" or
                    # "/usr/bin/test.exe" or "/usr/bin/env test", but
                    # not /usr/bin/testing or /usr/bin/attested
                    match=re.search(r'[\W]%s([\W]|$)' % keyword, bangpath)
                    if match:
                        return mode
        return None
    
    def attemptOpen(self, url):
        """Use the mode's attemptOpen method to see if it recognizes
        the url.
        
        @param url: URLInfo object to scan
        
        @returns: matching L{MajorMode} subclass or None
        """
        
        for plugin in self.plugins:
            for mode in plugin.possibleModes():
                dprint("scanning %s" % mode)
                if mode.attemptOpen(url):
                    return mode
        return None
