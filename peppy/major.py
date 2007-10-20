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

import os, stat, sys, re, time

import wx
import wx.stc
from wx.lib.pubsub import Publisher

from peppy.menu import *
from peppy.stcinterface import *
from peppy.debug import *
from peppy.minor import *
from peppy.iofilter import *
from peppy.yapsy.plugins import *
from peppy.editra import *

from peppy.lib.userparams import *
from peppy.lib.processmanager import *
from peppy.lib.iconstorage import *
from peppy.lib.controls import *


class MajorMode(wx.Panel, debugmixin, ClassPrefs):
    """
    Base class for all major modes.  Subclasses need to implement at
    least createEditWindow that will return the main user interaction
    window.
    """
    debuglevel = 0
    
    # Pointer to the icon representing this major mode
    icon = 'icons/page_white.png'
    
    # The single-word keyword representing this major mode
    keyword = 'Abstract_Major_Mode'
    
    # If there are additional emacs synonyms for this mode, list them here
    # as a string for a single synonym, or in a list of strings for multiple.
    # For instance, see hexedit_mode.py: in emacs the hex edit mode is called
    # 'hexl', but in peppy, it's called 'HexEdit'.  'hexl' is listed as in
    # emacs_synomyms in that file.
    emacs_synonyms = None
    
    # Filenames are matched against this regex in the class method
    # verifyFilename when peppy tries to determine which mode to use
    # to edit the file.  If no specific filenames, set to None
    regex = None
    
    # If this mode represents a temporary view and should be replaced by
    # a new tab, make this True
    temporary = False
    
    # If this mode allows threading loading, set this True
    allow_threaded_loading = True

    # stc_class is used to associate this major mode with a storage
    # mechanism (implementing the STCInterface).  The default is
    # PeppySTC, which is a subclass of the scintilla editor.
    stc_class = PeppySTC

    default_classprefs = (
        StrParam('minor_modes', '', 'List of minor mode keywords that should be\ndisplayed when starting this major mode'),
        IntParam('line_number_offset', 1, 'Number to add to the line number reported\nby the mode\'s stc in order to display'),
        IntParam('column_number_offset', 1, 'Number to add to the column number reported\nby the mode\'s stc in order to display'),
        )

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
        
        wx.Panel.__init__(self, frame.tabs, -1, style=wx.NO_BORDER, pos=(9000,9000))
        start = time.time()
        self.dprint("starting __init__ at 0.00000s")
        self.createWindow()
        self.dprint("createWindow done in %0.5fs" % (time.time() - start))
        self.createWindowPostHook()
        self.dprint("createWindowPostHook done in %0.5fs" % (time.time() - start))
        self.loadMinorModes()
        self.dprint("loadMinorModes done in %0.5fs" % (time.time() - start))
        self.loadMinorModesPostHook()
        self.dprint("loadMinorModesPostHook done in %0.5fs" % (time.time() - start))
        self.createEventBindings()
        self.dprint("createEventBindings done in %0.5fs" % (time.time() - start))
        self.createEventBindingsPostHook()
        self.dprint("createEventBindingsPostHook done in %0.5fs" % (time.time() - start))
        self.createListeners()
        self.dprint("createListeners done in %0.5fs" % (time.time() - start))
        self.createListenersPostHook()
        self.dprint("createListenersPostHook done in %0.5fs" % (time.time() - start))
        self.createPostHook()
        self.dprint("Created major mode in %0.5fs" % (time.time() - start))
        
        self._mgr.Update()

    def __del__(self):
        dprint("deleting %s: buffer=%s %s" % (self.__class__.__name__, self.buffer, self.getTabName()))
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
    def verifyEditraType(cls, ext, file_type):
        """Hook to verify the mode can handle the specified Editra type.

        @param ext: filename extension without the '.', or an empty string
        @param file_type: Editra file type string as given in the file
        peppy/editra/synglob.py, or None if not recognized by Editra

        @returns: either the boolean False, indicating Editra doesn't support
        this mode, or a string.  The string can either be the same as the
        input value ext if it matches a specific type supported by this mode
        or 'generic' if Editra supports the mode but if the mode doesn't
        provide any additional functionality (this usually only happens in
        Fundamental mode).
        """
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
        self.deleteStatusBar()

        # remove the mode as one of the buffer's listeners
        self.buffer.removeViewer(self)

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

    def createEventBindingsPostHook(self):
        pass

    def createListeners(self):
        """Required wx.lib.pubsub listeners are created here.

        Subclasses should override createListenersPostHook to add
        their own listeners.
        """
        Publisher().subscribe(self.resetStatusBar, 'resetStatusBar')
        Publisher().subscribe(self.settingsChanged, 'peppy.preferences.changed')

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
        
        minors = MinorMode.getValidMinorModes(self)
        dprint("major = %s, minors = %s" % (self, minors))

        # get list of minor modes that should be displayed at startup
        minor_list = self.classprefs.minor_modes
        if minor_list is not None:
            minor_names = [m.strip() for m in minor_list.split(',')]
            assert self.dprint("showing minor modes %s" % minor_names)
        else:
            minor_names = []

        # if the class name or the keyword of the minor mode shows up
        # in the list, turn it on.
        for minorcls in minors:
            minor = self.createMinorMode(minorcls)
            if minorcls.__name__ in minor_names or minorcls.keyword in minor_names:
                minor.paneinfo.Show(True)
            else:
                minor.paneinfo.Show(False)
        self.createMinorPaneList()

    def loadMinorModesPostHook(self):
        """User hook after all minor modes have been loaded.

        Use this hook if you need to initialize the set of minor modes
        after all of them have been loaded.
        """
        pass

    def createMinorMode(self, minorcls):
        """Create minor modes and register them with the AUI Manager."""
        minor=minorcls(self, self.splitter)
        # register minor mode here
        if isinstance(minor, wx.Window):
            paneinfo = minor.getPaneInfo()
            try:
                self._mgr.AddPane(minor, paneinfo)
            except Exception, e:
                dprint("Failed adding minor mode %s: error: %s" % (minor, str(e)))
        self.minors.append(minor)

        # A different paneinfo object is stored in the AUIManager,
        # so we have to get its version rather than using the
        # paneinfo we generate
        minor.paneinfo = self._mgr.GetPane(minor)
        return minor

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
        while len(self.minors)>0:
            minor = self.minors.pop()
            self.dprint("deleting minor mode %s" % (minor.keyword))
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
        self.frame.SetStatusText("L%d C%d F%d" % (linenum+self.classprefs.line_number_offset, col+self.classprefs.column_number_offset, self.editwin.GetFoldLevel(linenum)&wx.stc.STC_FOLDLEVELNUMBERMASK - wx.stc.STC_FOLDLEVELBASE),1)
        self.idle_update_menu = True
        self.OnUpdateUIHook(evt)
        if evt is not None:
            evt.Skip()

    def OnUpdateUIHook(self, evt):
        pass

    def idleHandler(self):
        #dprint("Idle starting for %s at %f" % (self.buffer.url, time.time()))
        if self.idle_update_menu:
            # FIXME: calling the toolbar enable here is better than in
            # the update UI loop, but it still seems to cause flicker
            # in the paste icon.  What's up with that?
            self.frame.enableTools()
            self.idle_update_menu = False
        self.idlePostHook()
        #dprint("Idle finished for %s at %f" % (self.buffer.url, time.time()))

    def idlePostHook(self):
        """Hook for subclasses to process during idle time.
        """
        pass

    def OnContextMenu(self, evt):
        """Hook to display a context menu relevant to this major mode.

        Currently, this event gets triggered when it happens over the
        major mode AND the minor modes.  So, that means the minor
        modes won't get their own EVT_CONTEXT_MENU events unless
        evt.Skip() is called here.

        This may or may not be the best behavior to implement.  I'll
        have to see as I get further into it.
        """
        dprint("context menu for %s" % self)
        pass

    def createEditWindow(self,parent):
        win=wx.Window(parent, -1, pos=(9000,9000))
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
    
    def deleteStatusBar(self):
        if self.statusbar:
            self.statusbar.Destroy()
            self.statusbar = None

    def setMinibuffer(self, minibuffer=None):
        self.removeMinibuffer()
        if minibuffer is not None:
            self.minibuffer = minibuffer
            box = self.GetSizer()
            box.Add(self.minibuffer.win, 0, wx.EXPAND)
            self.Layout()
            self.minibuffer.win.Show()
            self.minibuffer.focus()

    def removeMinibuffer(self, specific=None, detach_only=False):
        self.dprint(self.minibuffer)
        if self.minibuffer is not None:
            if specific is not None and specific != self.minibuffer:
                # A minibuffer calling another minibuffer has already
                # cleaned up the last minibuffer.  Don't clean it up
                # again.
                return
            
            box = self.GetSizer()
            box.Detach(self.minibuffer.win)
            if not detach_only:
                # for those cases where you still want to keep a
                # pointer around to the minibuffer and close it later,
                # use detach_only
                self.minibuffer.close()
            self.minibuffer = None
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



class JobControlMixin(JobOutputMixin, ClassPrefs):
    default_classprefs = (
        PathParam('interpreter_exe', '',
                  'Full path to a program that can interpret this text\nand return results on standard output'),
        BoolParam('autosave_before_run', True,
                  'Automatically save without prompting before running script'),
        )

    def getCommandLineArgs(self):
        dprint(hasattr(self, "commandLineArgs"))
        if hasattr(self, "commandLineArgs"):
            return self.commandLineArgs
        return ""

    def getCommandLine(self, bangpath=False, direct=False):
        script = self.buffer.url.path
        if bangpath or direct:
            mode = os.stat(script)[stat.ST_MODE] | stat.S_IXUSR
            os.chmod(script, mode)
            
            # FIXME: Don't think you can directly execute on MSW.  Mac???
            if wx.Platform != '__WXMSW__':
                script = script.replace(' ', '\ ')
            cmd = "%s %s" % (script, self.getCommandLineArgs())
        else:
            interpreter = self.classprefs.interpreter_exe
            if wx.Platform == '__WXMSW__':
                interpreter = '"%s"' % interpreter
                script = '"%s"' % script
            else:
                # Assuming that Mac is like GTK...
                interpreter = interpreter.replace(' ', '\ ')
                script = script.replace(' ', '\ ')
                pass
            cmd = "%s %s %s" % (interpreter, script, self.getCommandLineArgs())
        dprint(cmd)
        return cmd
        
    def startInterpreter(self, argstring=None):
        if argstring is not None:
            self.commandLineArgs = argstring
            
        if self.buffer.readonly or not self.classprefs.autosave_before_run:
            msg = "You must save this file to the local filesystem\nbefore you can run it through the interpreter."
            dlg = wx.MessageDialog(wx.GetApp().GetTopWindow(), msg, "Save the file!", wx.OK | wx.ICON_ERROR )
            retval=dlg.ShowModal()
            return
        else:
            self.save()

        bangpath = False
        direct = False
        if wx.Platform == '__WXMSW__':
            # FIXME: direct execution of a python script in Windows
            # doesn't seem to work.
            #direct = True
            pass
        elif self.stc.GetLine(0).startswith("#!"):
            bangpath = True
            
        msg = None
        path = self.classprefs.interpreter_exe
        if not bangpath and not direct:
            if not path:
                msg = "No interpreter executable set.\nMust set the full path to the\nexecutable in preferences."
            elif os.path.exists(path):
                if os.path.isdir(path):
                    msg = "Interpreter executable:\n\n%s\n\nis not a valid file.  Locate the\ncorrect executable in the preferences." % path
            else:
                msg = "Interpreter executable not found:\n\n%s\n\nLocate the correct path to the executable\nin the preferences." % path

        if msg:
            dlg = wx.MessageDialog(wx.GetApp().GetTopWindow(), msg, "Problem with interpreter executable", wx.OK | wx.ICON_ERROR )
            retval=dlg.ShowModal()
            Publisher().sendMessage('peppy.preferences.show')
        else:
            cmd = self.getCommandLine(bangpath, direct)
            ProcessManager().run(cmd, self.buffer.cwd(), self)

    def stopInterpreter(self):
        if hasattr(self, 'process'):
            self.process.kill()
    
    def startupCallback(self, job):
        self.process = job
        self.log = self.findMinorMode("OutputLog")
        if self.log:
            self.log.showMessage("\n" + _("Started %s on %s") %
                                 (job.cmd,
                                  time.asctime(time.localtime(time.time()))) +
                                 "\n")

    def stdoutCallback(self, job, text):
        if self.log:
            self.log.showMessage(text)

    def stderrCallback(self, job, text):
        if self.log:
            self.log.showMessage(text)

    def finishedCallback(self, job):
        assert self.dprint()
        del self.process
        if self.log:
            self.log.showMessage(_("Finished %s on %s") %
                                 (job.cmd,
                                  time.asctime(time.localtime(time.time()))) +
                                 "\n")



def parseEmacs(header):
    """
    Parse a potential emacs major mode specifier line into the
    mode and the optional variables.  The mode may appears as any
    of::

      -*-C++-*-
      -*- mode: Python; -*-
      -*- mode: Ksh; var1:value1; var3:value9; -*-

    @param header: first x bytes of the file to be loaded
    @return: two-tuple of the mode and a dict of the name/value pairs.
    @rtype: tuple
    """
    lines = header.splitlines()
    if len(lines) == 0:
        return None, None
    elif len(lines) > 1:
        line = lines[0] + lines[1]
    else:
        line = lines[0]
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

class MajorModeMatcherDriver(debugmixin):
    debuglevel = 0
    
    @classmethod
    def getActiveModes(cls):
        plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
        cls.dprint(plugins)
        modes = []
        for plugin in plugins:
            modes.extend(plugin.getMajorModes())
        return modes

    @classmethod
    def match(cls, url, magic_size=None):
        app = wx.GetApp()
        if magic_size is None:
            magic_size = app.classprefs.magic_size

        plugins = app.plugin_manager.getActivePluginObjects()
        cls.dprint(plugins)
        
        # Try to match a specific protocol
        modes = cls.scanProtocol(plugins, url)
        if modes:
            return modes[0]

        # ok, it's not a specific protocol.  Try to match a url pattern and
        # generate a list of possible modes
        modes = cls.scanURL(plugins, url)
        
        #
        fh = url.getReader(magic_size)
        header = fh.read(magic_size)

        url_match = None
        if modes:
            # OK, there is a match with the filenames.  Determine the
            # capability of the mode to edit the file by verifying any
            # magic bytes in the file
            capable = [m.verifyMagic(header) for m in modes]
            cm = zip(capable, modes)

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
        emacs_match = cls.scanEmacs(plugins, header)
        if emacs_match:
            return emacs_match

        # Like the emacs match, a match on a shell bangpath should
        # override anything determined out of the filename
        bang_match = cls.scanShell(plugins, header)
        if bang_match:
            return bang_match

        # Try to match some magic bytes that identify the file
        modes = cls.scanMagic(plugins, header)
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
        mode = cls.attemptOpen(plugins, url)
        if mode:
            return mode

        # If we fail all the tests, use a generic mode
        if guessBinary(header, app.classprefs.binary_percentage):
            return cls.findModeByName(plugins,
                                         app.classprefs.default_binary_mode)
        return cls.findModeByName(plugins,
                                     app.classprefs.default_text_mode)

    @classmethod
    def findModeByName(cls, plugins, name):
        cls.dprint("checking plugins %s" % plugins)
        for plugin in plugins:
            cls.dprint("checking plugin %s" % str(plugin.__class__.__mro__))
            for mode in plugin.getMajorModes():
                cls.dprint("searching %s" % mode.keyword)
                if mode.keyword == name:
                    return mode
        return None

    @classmethod
    def scanProtocol(cls, plugins, url):
        """Scan for url protocol match.
        
        Determine if the protocol is enough to specify the major mode.
        This generally happens only when the major mode is a client of
        a specific server and not a generic editor.  (E.g. MPDMode)

        @param url: URLInfo object to scan
        
        @returns: list of matching L{MajorMode} subclasses
        """
        
        modes = []
        for plugin in plugins:
            for mode in plugin.getMajorModes():
                cls.dprint("scanning %s" % mode)
                if mode.verifyProtocol(url):
                    modes.append(mode)
        return modes
    
    @classmethod
    def getEditraType(cls, pathname):
        # Also scan Editra extensions
        name, ext = os.path.splitext(pathname)
        if ext.startswith('.'):
            ext = ext[1:]
            cls.dprint("ext = %s, filename = %s" % (ext, pathname))
            extreg = syntax.ExtensionRegister()
            cls.dprint(extreg.GetAllExtensions())
            if ext in extreg.GetAllExtensions():
                editra_type = extreg.FileTypeFromExt(ext)
                cls.dprint(editra_type)
                return ext, editra_type
        return ext, None

    @classmethod
    def scanURL(cls, plugins, url):
        """Scan for url filename match.
        
        Determine if the pathname matches some pattern that can
        identify the corresponding major mode.

        @param url: URLInfo object to scan
        
        @returns: list of matching L{MajorMode} subclasses
        """
        
        modes = []
        generics = []
        ext, editra_type = cls.getEditraType(url.path)
        for plugin in plugins:
            for mode in plugin.getMajorModes():
                if mode.verifyFilename(url.path):
                    modes.append(mode)
                editra = mode.verifyEditraType(ext, editra_type)
                if editra == 'generic':
                    generics.append(mode)
                elif isinstance(editra, str):
                    modes.append(mode)
        modes.extend(generics)
        return modes

    @classmethod
    def scanMagic(cls, plugins, header):
        """Scan for a pattern match in the first bytes of the file.
        
        Determine if there is a 'magic' pattern in the first n bytes
        of the file that can associate it with a major mode.

        @param header: first n bytes of the file
        
        @returns: list of matching L{MajorMode} subclasses
        """
        
        modes = []
        for plugin in plugins:
            for mode in plugin.getMajorModes():
                if mode.verifyMagic(header):
                    modes.append(mode)
        return modes

    @classmethod
    def scanEmacs(cls, plugins, header):
        """Scan the first two lines of a file for an emacs mode
        specifier.
        
        Determine if an emacs mode specifier in the file can be
        associated with a major mode.

        @param header: first n bytes of the file
        
        @returns: matching L{MajorMode} subclass or None
        """
        
        modename, settings = parseEmacs(header)
        cls.dprint("modename = %s, settings = %s" % (modename, settings))
        for plugin in plugins:
            for mode in plugin.getMajorModes():
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
        
    @classmethod
    def scanShell(cls, plugins, header):
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
            for plugin in plugins:
                for mode in plugin.getMajorModes():
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
    
    @classmethod
    def attemptOpen(cls, plugins, url):
        """Use the mode's attemptOpen method to see if it recognizes
        the url.
        
        @param url: URLInfo object to scan
        
        @returns: matching L{MajorMode} subclass or None
        """
        
        for plugin in plugins:
            for mode in plugin.getMajorModes():
                cls.dprint("scanning %s" % mode)
                if mode.attemptOpen(url):
                    return mode
        return None
