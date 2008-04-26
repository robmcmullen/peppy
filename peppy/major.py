# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
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

from peppy.actions import *
from peppy.menu import *
from peppy.stcbase import *
from peppy.debug import *
from peppy.minor import *
from peppy.yapsy.plugins import *
from peppy.editra import *

from peppy.lib.userparams import *
from peppy.lib.processmanager import *
from peppy.lib.iconstorage import *
from peppy.lib.controls import *
from peppy.lib.textutil import *

class MajorModeWrapper(wx.Panel, debugmixin):
    """Container around major mode that controls the AUI manager
    
    """    
    icon = "icons/blank.png"
    
    def __init__(self, parent):
        self.editwin=None # user interface window
        self.minibuffer=None
        self.sidebar=None
        
        wx.Panel.__init__(self, parent, -1, style=wx.NO_BORDER, pos=(9000,9000))
        box=wx.BoxSizer(wx.VERTICAL)
        self.SetAutoLayout(True)
        self.SetSizer(box)
        self.splitter=wx.Panel(self)
        box.Add(self.splitter,1,wx.EXPAND)
        self._mgr = wx.aui.AuiManager()
        self._mgr.SetManagedWindow(self.splitter)
        self._mgr.Update()
        
        self.minors = None

    def __del__(self):
        self.dprint("deleting %s: editwin=%s %s" % (self.__class__.__name__, self.editwin, self.getTabName()))
        # FIXME: remove stuff here?

    def createMajorMode(self, frame, buffer, requested=None):
        # Remove the old mode if it exists
        self.deleteMajorMode()
        
        if not requested:
            requested = buffer.defaultmode
        else:
            # Change the default major mode if the old default is the most
            # general major mode.
            if buffer.defaultmode.verifyMimetype('text/plain'):
                dprint("Changing default mode of %s to %s" % (buffer, requested))
                buffer.defaultmode = requested
        self.dprint("creating major mode %s" % requested)
        self.editwin = requested(self.splitter, self, buffer, frame)
        buffer.addViewer(self.editwin)
        self._mgr.AddPane(self.editwin, wx.aui.AuiPaneInfo().Name("main").
                          CenterPane())

        start = time.time()
        self.dprint("starting __init__ at 0.00000s")
        self.editwin.createWindowPostHook()
        self.dprint("createWindowPostHook done in %0.5fs" % (time.time() - start))
        self.editwin.createStatusBarInfo()
        self.dprint("createStatusBarInfo done in %0.5fs" % (time.time() - start))
        self.loadMinorModes()
        self.dprint("loadMinorModes done in %0.5fs" % (time.time() - start))
        self.editwin.loadMinorModesPostHook()
        self.dprint("loadMinorModesPostHook done in %0.5fs" % (time.time() - start))
        self.editwin.createEventBindings()
        self.dprint("createEventBindings done in %0.5fs" % (time.time() - start))
        self.editwin.createEventBindingsPostHook()
        self.dprint("createEventBindingsPostHook done in %0.5fs" % (time.time() - start))
        self.editwin.createListeners()
        self.dprint("createListeners done in %0.5fs" % (time.time() - start))
        self.editwin.createListenersPostHook()
        self.dprint("createListenersPostHook done in %0.5fs" % (time.time() - start))
        self.editwin.createPostHook()
        self.dprint("Created major mode in %0.5fs" % (time.time() - start))
        
        self._mgr.Update()
        return self.editwin
    
    def deleteMajorMode(self):
        if self.editwin:
            self.dprint("deleting major mode %s" % self.editwin)
            self.deleteMinorModes()
            self.removeMinibuffer()
            self._mgr.DetachPane(self.editwin)
            self.editwin.frame.clearMenumap()
            # FIXME: there must be references to the editwin held by other
            # objects, because the window's __del__ method is not getting
            # called.  Have to explicitly hide the window to prevent the
            # editwin from showing up over top of the next editwin.
            self.editwin.Hide()
            self.editwin.deleteWindow()
            self.editwin = None
    
    def getTabName(self):
        if self.editwin:
            return self.editwin.getTabName()
        return "Empty"
    
    def getTabBitmap(self):
        if self.editwin:
            icon = self.editwin.icon
        else:
            icon = self.icon
        return getIconBitmap(icon)
    

    def loadMinorModes(self):
        """Find the listof minor modes to load and create them."""
        
        # get list of minor modes that should be displayed at startup
        minor_list = self.editwin.classprefs.minor_modes
        if minor_list is not None:
            minor_names = [m.strip() for m in minor_list.split(',')]
            assert self.dprint("showing minor modes %s" % minor_names)
        else:
            minor_names = []

        # if the class name or the keyword of the minor mode shows up
        # in the list, turn it on.
        self.minors = MinorModeList(self.splitter, self._mgr, self.editwin,
                                    minor_names)

    def deleteMinorModes(self):
        """Remove the minor modes from the AUI Manager and delete them."""
        try:
            self.minors.deleteAll()
        except AttributeError:
            dprint("Minor modes must not have been initiated for %s" % self.editwin)
            raise
        self.minors = None
    
    def findMinorMode(self, name):
        """Get the minor mode given the name
        
        This will create the mode if it doesn't exist.
        """
        minor = self.minors.getWindow(name)
        if minor:
            return minor
        
        entry = self.minors.create(name)
        self._mgr.Update()
        return entry.win

    def getActiveMinorModes(self):
        """Proxy the minor mode requests up to the wrapper"""
        if self.minors:
            return self.minors.getActive()
        return []

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
            self.editwin.focus()


class MajorMode(ClassPrefs, debugmixin):
    """Mixin class for all major modes.
    
    Major modes are associated with some type (or types) of file, and
    provide a way to edit them.  Most major modes that edit text will
    actually want to be a subclass of L{FundamentalMode}, as that class
    uses the wx.stc.StyledTextControl as its base class and provides a
    lot of additional text editing support by default.  See L{PythonMode},
    L{ChangeLogMode}, and L{MakefileMode} for examples of modes that use
    L{FundamentalMode} as a basis.
    
    If a major mode isn't for a text file, however, it should use this
    mixin class along with some other subclass of wx.Window to provide the
    editing interface.  This mixin is required because it provides a lot of
    the boilerplate stuff that peppy needs to manage the major mode.  See
    L{HexEditMode} and L{DiredMode} for modes that don't use an stc for their
    user window.
    
    Associating the Major Mode with a File Type
    ===========================================
    
    When a file is opened, peppy uses the L{MajorModeMatcherDriver}
    class to determine which major mode to use to edit the file.  The
    L{MajorModeMatcherDriver.match} method loops over all major modes and
    uses the heuristics to determine the best match by calling the C{verify*}
    class methods of the major modes.  There are default implementations of
    the verify methods that use class attributes of the major mode to identify
    the mode.
    
    There are several ways to tell peppy to associate the major mode with
    a particular type of file.  
    
    MIME Type
    ---------
    
    The simplest is to specify the MIME type in the class attribute
    L{mimetype}.  The MIME type returned from the L{vfs.get_metadata}
    call will be used to match against the MIME type specified here; or
    alternatively you can override the L{verifyMimetype} class method and
    perform matching on the MIME type of each file as it's opened by peppy.
    
    However, not all MIME types are known by default to the VFS, so you may
    need to provide other ways to match the file.
    
    Filename
    --------
    
    If your file always has a certain extension, you can specify a
    regular expression is the L{regex} class attribute.  This uses the
    L{verifyFilename} method to return a match.  You can also override the
    L{verifyFilename} method directly.
    
    Note that only the filename is passed to the L{verifyFilename} method as
    it should be independent of the scheme used to retrieve the URL.  If you
    actually want to match on the scheme, use the L{verifyProtocol} method.
    
    Magic Bytes
    -----------
    
    If there's no easy way to tell the file type, you may need to check some
    bytes in the file to see if it matches some "magic number" that will
    identify the file that peppy is trying to load as one that your major
    mode supports.
    
    The class method L{verifyMagic} is called if there's no exact match by
    earlier methods.  In order to reduce the expense of this operation, a
    certain number of bytes (a minimum of 1024) are read from the file before
    the call to verifyMagic so that every major mode isn't trying to read the
    same file over and over.  If your file can't be uniquely determined in the
    first 1024 bytes, there is still a way to determine the file type: see the
    L{IPeppyPlugin.attemptOpen} method.
    
    Backend Storage
    ===============
    
    Once the major mode has been selected for that file, it is loaded into a
    L{Buffer} for storage.  There is only one Buffer instance per copy of a
    file that's loaded.  Multiple views of the same file always point back to
    the same Buffer.
    
    The major mode uses the Buffer as the backend storage for the data.  The
    Buffer uses a class that implements the L{STCInterface} as the actual
    storage space for the loaded file.  Major modes declare what type of
    L{STCInterface} is used for the backend storage by setting the class
    attribute L{stc_class}.
    
    Peppy is not limited to editing files that can fit in physical memory.
    However, the wx.stc.StyledTextCtrl (the Scintilla control, abbreviated
    'STC' here) does require that the file be held in physical memory.  So,
    if you're going to use an stc to display your file, you're limited to
    files that can fit in memory.  Files larger than physical memory should
    extend from L{NonResidentSTC}, but currently the extra steps required
    to make a major mode for extremely large files are not documented.  See
    L{hsi_major_mode} if you're interested, until better documentation is
    written.
    
    For a major mode that focuses on files that can be held in memory, the
    backend storage should be implemented by a L{PeppySTC} instance.
    
    STC Backend Storage and STC Used for Display
    --------------------------------------------
    
    If your major mode also uses an STC for displaying the text to the user,
    you should consider extending your major mode from L{FundamentalMode}, as
    the details will be taken care of for you.  But be aware that the STC used
    for backend storage is not the same as the STC presented to the user.
    
    The backend storage is the root document, and this root document does not
    get displayed.  The STC that is used for display will be linked to the
    Buffer's STC using the document pointer capability of Scintilla.  This
    means that multiple views of the same file are possible, and all share the
    same backend storage because they all point to the same buffer.
    
    STC Backend Storage without using an STC for Display
    ----------------------------------------------------
    
    It is also possible to use a real STC for backend storage, but use some
    different wx.Window subclass for display.  See the L{HexEditMode} for an
    example that uses a wx.Grid control to present the file as a string of
    binary bytes.
    
    There are complications to using this approach, however.  Because multiple
    views are possible, there could be a text view of a file at the same time
    as a hex edit view.  If both views were STCs, the changes in one would be
    automatically propagated to the other.  But, because one of the views is a
    wx.Grid, we must catch modification events and update the wx.Grid as bytes
    change in the other view.  See the L{HexEditMode} for more information.
    
    Fundamental Text Editing
    ========================
    
    Most major modes for text editing will use a real STC for user interaction.
    The best way to make a major mode that uses a real STC is to extend
    from L{FundamentalMode}.  Fundamental mode uses a bunch of mixins that
    extend the functionality of the STC, and provide the places for customized
    enhancements like brace highlighting, region commenting, paragraph
    finding, and a lot of other features.  Examining one of the subclasses of
    Fundamental mode is probably the best place to start if you're interested
    in extending peppy to handle a file that is currently unsupported.
        
    """
    #: set to non-zero to activate debug printing for this class
    debuglevel = 0
    
    #: Pointer to the icon representing this major mode
    icon = 'icons/page_white.png'
    
    #: The single-word keyword representing this major mode
    keyword = 'Abstract_Major_Mode'
    
    #: The preferences tab that this mode will appear in
    preferences_tab = "Modes"
    
    #: If there are additional emacs synonyms for this mode, list them here as a string for a single synonym, or in a list of strings for multiple. For instance, see hexedit_mode.py: in emacs the hex edit mode is called 'hexl', but in peppy, it's called 'HexEdit'.  'hexl' is listed as in emacs_synomyms in that file.
    emacs_synonyms = None
    
    #: Filenames are matched against this regex in the class method verifyFilename when peppy tries to determine which mode to use to edit the file.  If no specific filenames, set to None
    regex = None
    
    #: The VFS also provides metadata, including MIME type, and the MIME types supported by the major mode can be listed here.  The MIME types can be a single string or a list of strings for multiple types.
    mimetype = None
    
    #: If this mode represents a temporary view and should be replaced by a new tab, make this True
    temporary = False
    
    #: If this mode allows threading loading, set this True
    allow_threaded_loading = True    

    #: stc_class is used to associate this major mode with a storage mechanism (implementing the STCInterface).  The default is PeppySTC, which is a subclass of the scintilla editor.
    stc_class = PeppySTC

    default_classprefs = (
        StrParam('minor_modes', '', 'List of minor mode keywords that should be displayed when starting this major mode', fullwidth=True),
        IntParam('line_number_offset', 1, 'Number to add to the line number reported by the mode\'s stc in order to display'),
        IntParam('column_number_offset', 1, 'Number to add to the column number reported by the mode\'s stc in order to display'),
        )

    # Need one keymap per subclass, so we can't use the settings.
    # Settings would propogate up the class hierachy and find a keymap
    # of a superclass.  This is a dict based on the class name.
    localkeymaps = {}
    
    def __init__(self, parent, wrapper, buffer, frame):
        # set up the view-local versions of classprefs
        self.classprefsCopyToLocals()
        
        self.wrapper = wrapper
        self.buffer = buffer
        self.frame = frame
        self.popup = None
        self.status_info = None
        
        # Create a window here!
        pass

    def __del__(self):
        #dprint("deleting %s: buffer=%s %s" % (self.__class__.__name__, self.buffer, self.getTabName()))
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

        @param url: vfs.Reference object

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
    def verifyMimetype(cls, mimetype):
        """Hook to allow the major mode to determine compatibility by mimetype.

        mimetype: a string indicating the MIME type of the file

        return: True if the mode supports the MIME type
        """
        if cls.mimetype:
            if isinstance(cls.mimetype, str) and mimetype == cls.mimetype:
                return True
            for mime in cls.mimetype:
                if mimetype == mime:
                    return True
        return False

    @classmethod
    def verifyMetadata(cls, metadata):
        """Hook to allow the major mode to determine compatibility by file
        metadata.
        
        This method is more general than verifyMimetype, as it can operate on
        all the metadata passed to it rather than just the MIME type.

        metadata: a dict containing the results of a call to vfs.get_metadata.
        The MIME type will be in a key called 'mimetype'.

        return: True if the mode supports the MIME type specified by the
        metadata
        """
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

    def save(self, url=None):
        veto = self.savePreHook(url)
        if veto == False:
            return
        try:
            self.buffer.save(url)
            self.savePostHook()
            self.status_info.setText(u"Saved %s" % self.buffer.url)
        except IOError, e:
            self.status_info.setText(unicode(e))
        except UnicodeEncodeError, e:
            self.status_info.setText(unicode(e))
        except LookupError, e:
            # Bad encoding name!
            self.status_info.setText(unicode(e))

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
        if hasattr(self, 'addUpdateUIEvent'):
            self.addUpdateUIEvent(self.OnUpdateUI)
        self.Bind(wx.EVT_KEY_DOWN, self.frame.OnKeyDown)
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
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

    def loadMinorModesPostHook(self):
        """User hook after all minor modes have been loaded.

        Use this hook if you need to initialize the set of minor modes
        after all of them have been loaded.
        """
        pass

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
        linenum = self.GetCurrentLine()
        pos = self.GetCurrentPos()
        col = self.GetColumn(pos)
        self.status_info.setText("L%d C%d" % (linenum+self.classprefs.line_number_offset,
            col+self.classprefs.column_number_offset),1)
        self.idle_update_menu = True
        self.OnUpdateUIHook(evt)
        if evt is not None:
            evt.Skip()

    def OnUpdateUIHook(self, evt):
        pass

    def idleHandler(self):
        #dprint("Idle starting for %s at %f" % (self.buffer.url, time.time()))
        if self.idle_update_menu:
            # FIXME: this was the old way to update the UI; now toolbar buttons
            # are automatically updated in the event handler OnUpdateUI in
            # UserActionMap.
            self.idle_update_menu = False
        self.idlePostHook()
        #dprint("Idle finished for %s at %f" % (self.buffer.url, time.time()))

    def idlePostHook(self):
        """Hook for subclasses to process during idle time.
        """
        pass

    def getPopupActions(self, evt, x, y):
        """Return the list of action classes to use as a context menu.
        
        If the subclass is capable of displaying a popup menu, it needs to
        return a list of action classes.  The x, y pixel coordinates (relative
        to the origin of major mode window) are included in case the subclass
        can display different popup items depending on the position in the
        editing window.
        """
        return []

    def OnContextMenu(self, evt):
        """Hook to display a context menu relevant to this major mode.

        For standard usage, subclasses should override L{getPopupActions} to
        provide a list of actions to display in the popup menu.  Nonstandard
        behaviour on a right click can be implemented by overriding this
        method instead.
        
        Currently, this event gets triggered when it happens over the
        major mode AND the minor modes.  So, that means the minor
        modes won't get their own EVT_CONTEXT_MENU events unless
        evt.Skip() is called here.

        This may or may not be the best behavior to implement.  I'll
        have to see as I get further into it.
        """
        pos = evt.GetPosition()
        screen = self.GetScreenPosition()
        #dprint("context menu for %s at %d, %d" % (self, pos.x - screen.x, pos.y - screen.y))
        action_classes = self.getPopupActions(evt, pos.x - screen.x, pos.y - screen.y)
        if action_classes:
            self.frame.menumap.popupActions(self, action_classes)
        else:
            evt.Skip()

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
    
    def createStatusBarInfo(self):
        """Create the status bar exstrinsic information storage.
        
        The appearance of the statusbar can depend on the major mode, so the
        individual major mode is responsible for creating whatever it needs.
        """
        widths = self.getStatusBarWidths()
        self.status_info = ModularStatusBarInfo(self.frame.GetStatusBar(), widths)
        self.createStatusIcons()

    def createStatusIcons(self):
        """Create any icons in the status bar.

        This is called after making the major mode the active mode in
        the frame.  The status bar will be cleared to its initial
        empty state, so all this method has to do is add any icons
        that it needs.
        """
        pass

    def getStatusBarWidths(self):
        """Returns a list of status bar field widths.

        Override this in subclasses to change the number of text fields in the
        status bar.
        """
        return [-1, 150]

    def resetStatusBar(self, message=None):
        """Updates the status bar.

        This method clears and rebuilds the status bar, usually
        because something requests an icon change.
        """
        self.status_info.reset()
        self.createStatusIcons()
    
    def setStatusText(self, text, field=0):
        self.status_info.setText(text, field)
    
    ##### Proxy services for the wrapper
    def updateAui(self):
        self.wrapper._mgr.Update()
    
    def getMinibuffer(self):
        """Returns the minibuffer instance in use, or None"""
        return self.wrapper.minibuffer

    def setMinibuffer(self, minibuffer=None):
        """Proxy the minibuffer requests up to the wrapper"""
        self.wrapper.setMinibuffer(minibuffer)

    def removeMinibuffer(self, specific=None, detach_only=False):
        """Proxy the minibuffer requests up to the wrapper"""
        self.wrapper.removeMinibuffer(specific, detach_only)

    def findMinorMode(self, name):
        """Proxy the minor mode requests up to the wrapper"""
        return self.wrapper.findMinorMode(name)

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
        self.resetStatusBar()

    def focus(self):
        # The active tab may have changed, so make sure that this mode is
        # still in the active tab before setting focus.  Otherwise we might
        # change tabs unexpectedly.
        if self.frame.getActiveMajorMode() == self:
            self.SetFocus()
            self.focusPostHook()

    def focusPostHook(self):
        pass

    def tabActivatedHook(self):
        """Hook to update some user interface parameters after the tab has been
        made the current tab.
        """
        pass

    def showModified(self,modified):
        self.frame.showModified(self)

    def showBusy(self, busy):
        self.Enable(not busy)
        if busy:
            cursor = wx.StockCursor(wx.CURSOR_WATCH)
        else:
            cursor = wx.StockCursor(wx.CURSOR_DEFAULT)
        self.SetCursor(cursor)

    def showInitialPosition(self, url):
        """Hook to scroll to a non-default initial position if desired."""
        pass
    
    def revertPreHook(self):
        """Hook to save any view parameters that should be restored after a revert"""
        pass
    
    def revertPostHook(self):
        """Hook to restore the view parameters after a revert"""
        pass


class JobControlMixin(JobOutputMixin, ClassPrefs):
    """Process handling mixin to run scripts based on the current major mode.
    
    This mixin provides some common interfacing to run scripts that are
    tied to a major mode.  An interpreter classpref is provided that links
    a major mode to a binary file to run scripts in that mode.  Actions
    like RunScript and StopScript are tied to the presense of this mixin
    and will be automatically enabled when they find a mode has the
    interpreter_exe classpref.
    """
    default_classprefs = (
        PathParam('interpreter_exe', '', 'Full path to a program that can interpret this text and return results on standard output', fullwidth=True),
        BoolParam('autosave_before_run', True, 'Automatically save without prompting before running script'),
        )

    def getInterpreterArgs(self):
        """Hook to pass arguments to the command interpreter"""
        dprint(hasattr(self, "interpreterArgs"))
        if hasattr(self, "interpreterArgs"):
            return self.interpreterArgs
        return ""

    def getScriptArgs(self):
        """Hook to specify any arguments passed to the script itself"""
        dprint(hasattr(self, "scriptArgs"))
        if hasattr(self, "scriptArgs"):
            return self.scriptArgs
        return ""
    
    def getCommandLine(self, bangpath=None):
        """Return the entire command line of the job to be started.
        
        If allowed by the operating system, the script is parsed for a
        bangpath and will be executed directly if it exists.  Otherwise,
        the command interpreter will be used to start the script.
        """
        if self.buffer.url.scheme != "file":
            msg = "You must save this file to the local filesystem\nbefore you can run it through the interpreter."
            dlg = wx.MessageDialog(wx.GetApp().GetTopWindow(), msg, "Save the file!", wx.OK | wx.ICON_ERROR )
            retval=dlg.ShowModal()
            return
        script = str(self.buffer.url.path)
        if bangpath:
            if wx.Platform == '__WXMSW__':
                # MSW doesn't pass to a shell, so simulate a bangpath by pulling
                # out the script name and using that as the interpreter.
                interpreter = bangpath.rstrip()
                tmp = interpreter.lower()
                i = interpreter.find(".exe")
                if i > -1:
                    args = interpreter[i + 4:]
                    interpreter = interpreter[:i + 4]
                else:
                    args = self.getInterpreterArgs()
                cmd = '"%s" %s "%s" %s' % (interpreter, args,
                                       script, self.getScriptArgs())
            else:
                mode = os.stat(script)[stat.ST_MODE] | stat.S_IXUSR
                os.chmod(script, mode)
            
                script = script.replace(' ', '\ ')
                cmd = "%s %s" % (script, self.getScriptArgs())
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
            cmd = "%s %s %s %s" % (interpreter, self.getInterpreterArgs(),
                                   script, self.getScriptArgs())
        dprint(cmd)
        return cmd
        
    def startInterpreter(self, argstring=None):
        """Interface used by actions to start the interpreter.
        
        This method is the outside interface to the job control mixin to
        start the interpreter.  See the RunScript action for an example
        of its usage in practice.
        """
        if argstring is not None:
            self.scriptArgs = argstring
            
        if self.buffer.readonly or not self.classprefs.autosave_before_run:
            msg = "You must save this file to the local filesystem\nbefore you can run it through the interpreter."
            dlg = wx.MessageDialog(wx.GetApp().GetTopWindow(), msg, "Save the file!", wx.OK | wx.ICON_ERROR )
            retval=dlg.ShowModal()
            return
        else:
            self.save()

        bangpath = None
        first = self.GetLine(0)
        if first.startswith("#!"):
            bangpath = first[2:]
            
        msg = None
        path = self.classprefs.interpreter_exe
        if bangpath is None:
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
            cmd = self.getCommandLine(bangpath)
            ProcessManager().run(cmd, self.buffer.cwd(), self)

    def stopInterpreter(self):
        """Interface used by actions to kill the currently running job.
        
        This method is the outside interface to the job control mixin to
        stop the currently running job.  See the StopScript action for an
        example of its usage in practice.
        """
        if hasattr(self, 'process'):
            self.process.kill()
    
    def startupCallback(self, job):
        """Callback from the JobOutputMixin when a job is successfully
        started.
        """
        self.process = job
        self.log = self.findMinorMode("OutputLog")
        if self.log:
            self.log.showMessage("\n" + _("Started %s on %s") %
                                 (job.cmd,
                                  time.asctime(time.localtime(time.time()))) +
                                 "\n")

    def stdoutCallback(self, job, text):
        """Callback from the JobOutputMixin for a block of text on stdout."""
        if self.log:
            self.log.showMessage(text)

    def stderrCallback(self, job, text):
        """Callback from the JobOutputMixin for a block of text on stderr."""
        if self.log:
            self.log.showMessage(text)

    def finishedCallback(self, job):
        """Callback from the JobOutputMixin when the job terminates."""
        assert self.dprint()
        del self.process
        if self.log:
            self.log.showMessage(_("Finished %s on %s") %
                                 (job.cmd,
                                  time.asctime(time.localtime(time.time()))) +
                                 "\n")



class MajorModeMatcherDriver(debugmixin):
    @classmethod
    def getCompatibleMajorModes(cls, stc_class):
        plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
        modes = []
        for plugin in plugins:
            # Only display those modes that use the same type of STC as the
            # current mode.
            modes.extend([m for m in plugin.getMajorModes() if m.stc_class == stc_class])
        
            modes.extend(plugin.getCompatibleMajorModes(stc_class))
        cls.dprint("%s: compatible modes = %s" % (stc_class, str(modes)))
        return modes

    @classmethod
    def match(cls, buffer, magic_size=None):
        app = wx.GetApp()
        if magic_size is None:
            magic_size = app.classprefs.magic_size

        plugins = app.plugin_manager.getActivePluginObjects()
        
        # Try to match a specific protocol
        modes = cls.scanProtocol(plugins, buffer.url)
        cls.dprint("scanProtocol matches %s" % modes)
        if modes:
            return modes[0]

        # ok, it's not a specific protocol.  Try to match a url pattern and
        # generate a list of possible modes
        try:
            metadata = vfs.get_metadata(buffer.url)
        except:
            metadata = {'mimetype': None,
                        'mtime': None,
                        'size': 0,
                        'description': None,
                        }
        modes, binary_modes = cls.scanURL(plugins, buffer.url, metadata)
        cls.dprint("scanURL matches %s (binary: %s) using metadata %s" % (modes, binary_modes, metadata))

        # get a buffered file handle to examine some bytes in the file
        fh = buffer.getBufferedReader(magic_size)
        if not fh:
            # ok, the file doesn't exist, meaning that we're creating a new
            # file.  Return the best guess we have based on filename only.
            if modes:
                return modes[0]
            else:
                return cls.findModeByMimetype(plugins, "text/plain")
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
        cls.dprint("scanEmacs matches %s" % emacs_match)
        if emacs_match:
            return emacs_match

        # Like the emacs match, a match on a shell bangpath should
        # override anything determined out of the filename
        bang_match = cls.scanShell(plugins, header)
        cls.dprint("scanShell matches %s" % bang_match)
        if bang_match:
            return bang_match

        # Try to match some magic bytes that identify the file
        modes = cls.scanMagic(plugins, header)
        cls.dprint("scanMagic matches %s" % modes)
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
        mode = cls.attemptOpen(plugins, buffer)
        cls.dprint("attemptOpen matches %s" % mode)
        if mode:
            return mode

        # If we fail all the tests, use a generic mode
        if guessBinary(header, app.classprefs.binary_percentage):
            if binary_modes:
                # FIXME: needs to be a better way to select which mode to use
                # if there are multiple application/octet-stream viewers
                return binary_modes[0]
        return cls.findModeByMimetype(plugins, "text/plain")

    @classmethod
    def findModeByMimetype(cls, plugins, mimetype):
        cls.dprint("checking plugins %s" % plugins)
        for plugin in plugins:
            cls.dprint("checking plugin %s" % str(plugin.__class__.__mro__))
            for mode in plugin.getMajorModes():
                cls.dprint("searching %s" % mode.keyword)
                if mode.verifyMimetype(mimetype):
                    return mode
        return None

    @classmethod
    def scanProtocol(cls, plugins, url):
        """Scan for url protocol match.
        
        Determine if the protocol is enough to specify the major mode.
        This generally happens only when the major mode is a client of
        a specific server and not a generic editor.  (E.g. MPDMode)

        @param url: vfs.Reference object to scan
        
        @returns: list of matching L{MajorMode} subclasses
        """
        
        modes = []
        for plugin in plugins:
            for mode in plugin.getMajorModes():
                if mode.verifyProtocol(url):
                    modes.append(mode)
        return modes
    
    @classmethod
    def getEditraType(cls, url):
        filename = url.path.get_name()
        # Also scan Editra extensions
        name, ext = os.path.splitext(filename)
        if ext.startswith('.'):
            ext = ext[1:]
            cls.dprint("ext = %s, filename = %s" % (ext, filename))
            extreg = syntax.ExtensionRegister()
            cls.dprint(extreg.GetAllExtensions())
            if ext in extreg.GetAllExtensions():
                editra_type = extreg.FileTypeFromExt(ext)
                cls.dprint(editra_type)
                return ext, editra_type
        return ext, None

    @classmethod
    def scanURL(cls, plugins, url, metadata):
        """Scan for url filename match.
        
        Determine if the pathname matches some pattern that can
        identify the corresponding major mode.

        @param url: vfs.Reference object to scan
        
        @returns: list of matching L{MajorMode} subclasses
        """
        
        modes = []
        generics = []
        
        # Anything that matches application/octet-stream is a generic mode, so
        # save it for last.
        binary = []
        binary_generics = []
        
        mimetype = metadata['mimetype']
        ext, editra_type = cls.getEditraType(url)
        for plugin in plugins:
            for mode in plugin.getMajorModes():
                if mode.verifyMimetype(mimetype):
                    if mimetype == 'application/octet-stream':
                        binary.append(mode)
                    else:
                        modes.append(mode)
                elif mode.verifyMetadata(metadata):
                    modes.append(mode)
                elif mode.verifyFilename(url.path.get_name()):
                    modes.append(mode)
                elif mode.verifyMimetype("application/octet-stream"):
                    binary_generics.append(mode)
                
                # check if the mode is recognized by Editra.  It could also be
                # a generic mode or not recognized at all (in which case it
                # is ignored).
                editra = mode.verifyEditraType(ext, editra_type)
                if editra == 'generic':
                    generics.append(mode)
                elif isinstance(editra, str):
                    modes.append(mode)
        modes.extend(generics)
        binary.extend(binary_generics)
        return modes, binary

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
                    regex = r'[\W]%s([\W]|$)' % re.escape(keyword)
                    match=re.search(regex, bangpath)
                    if match:
                        return mode
        return None
    
    @classmethod
    def attemptOpen(cls, plugins, buffer):
        """Use the mode's attemptOpen method to see if it recognizes the url.
        
        @param buffer: Buffer object to scan
        
        @returns: matching L{MajorMode} subclass or None
        """
        modes = []
        for plugin in plugins:
            try:
                exact, generics = plugin.attemptOpen(buffer)
                if exact:
                    return exact
                modes.extend(generics)
            except ImportError:
                # plugin tried to load a module that didn't exist
                pass
            except:
                # some other error
                import traceback
                error = traceback.format_exc()
                dprint("Some non-import related error attempting to open from plugin %s\n:%s" % (str(plugin), error))
        if modes:
            return modes[0]
        return None
