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

import peppy.vfs as vfs
from peppy.stcbase import *
from peppy.debug import *
from peppy.minor import *
from peppy.sidebar import *
from peppy.yapsy.plugins import *
from peppy.context_menu import ContextMenuMixin

from peppy.lib.userparams import *
from peppy.lib.processmanager import *
from peppy.lib.iconstorage import *
from peppy.lib.controls import *
from peppy.lib.springtabs import SpringTabs


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
        
        self.splitter = wx.Panel(self)
        self.spring = SpringTabs(self, popup_direction="left")
        
        # There seems to be a bug in the AUI layout using DockFixed, so there's
        # an alternate way to set up the springtabs using a box sizer.  The
        # AUI layout problem seems to make the width too narrow, and has
        # additional problems on windows where it prevents the SpringTab from
        # getting mouse clicks to open the popup.
        self.spring_aui = False
        if self.spring_aui:
            box.Add(self.splitter, 1, wx.EXPAND)
        else:
            hsplit = wx.BoxSizer(wx.HORIZONTAL)
            hsplit.Add(self.splitter, 1, wx.EXPAND)
            hsplit.Add(self.spring, 0, wx.EXPAND)
            box.Add(hsplit, 1, wx.EXPAND)
        self._mgr = wx.aui.AuiManager()
        self._mgr.SetManagedWindow(self.splitter)
        
        if self.spring_aui:
            self._mgr.AddPane(self.spring, wx.aui.AuiPaneInfo().
                              Name("MinorSpringTabs").Caption("MinorSpringTabs").
                              Right().Layer(10).Hide().DockFixed().
                              CloseButton(False).CaptionVisible(False).
                              LeftDockable(False).RightDockable(False))
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
        self.dprint("creating major mode %s" % requested)
        self.editwin = requested(self.splitter, self, buffer, frame)
        buffer.addViewer(self.editwin)
        self._mgr.AddPane(self.editwin, wx.aui.AuiPaneInfo().Name("main").
                          CenterPane())

        start = time.time()
        self.dprint("starting __init__ at 0.00000s")
        Publisher().sendMessage('mode.preinit', self.editwin)
        self.dprint("mode.preinit message done in %0.5fs" % (time.time() - start))
        self.editwin.createWindowPostHook()
        self.dprint("createWindowPostHook done in %0.5fs" % (time.time() - start))
        self.editwin.createStatusBarInfo()
        self.dprint("createStatusBarInfo done in %0.5fs" % (time.time() - start))
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
        self.loadMinorModes()
        self.dprint("loadMinorModes done in %0.5fs" % (time.time() - start))
        self.editwin.loadMinorModesPostHook()
        self.dprint("loadMinorModesPostHook done in %0.5fs" % (time.time() - start))
        Publisher().sendMessage('mode.postinit', self.editwin)
        self.dprint("mode.postinit message done in %0.5fs" % (time.time() - start))
        
        self._mgr.Update()
        
        buffer.startChangeDetection()

        if not requested:
            # If the major mode creation was successful, change the default
            # major mode if the old default is the most general major mode.
            if buffer.defaultmode.verifyMimetype('text/plain'):
                self.dprint("Changing default mode of %s to %s" % (buffer, requested))
                buffer.defaultmode = requested
        return self.editwin
    
    def deleteMajorMode(self):
        if self.editwin:
            self.dprint("deleting major mode %s" % self.editwin)
            self.deleteMinorModes()
            self.spring.deleteTabs()
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

    def getActiveMinorModes(self, ignore_hidden=False):
        """Proxy the minor mode requests up to the wrapper"""
        if self.minors:
            return self.minors.getActive(ignore_hidden)
        return []

    def setMinibuffer(self, minibuffer=None):
        self.removeMinibuffer()
        if minibuffer is not None:
            self.minibuffer = minibuffer
            self.minibuffer.addToSizer(self.GetSizer())
            self.Layout()
            self.minibuffer.show()

    def removeMinibuffer(self, specific=None, detach_only=False):
        self.dprint(self.minibuffer)
        if self.minibuffer is not None:
            if specific is not None and specific != self.minibuffer:
                # A minibuffer calling another minibuffer has already
                # cleaned up the last minibuffer.  Don't clean it up
                # again.
                return
            
            self.minibuffer.detachFromSizer(self.GetSizer())
            if not detach_only:
                # for those cases where you still want to keep a
                # pointer around to the minibuffer and close it later,
                # use detach_only
                self.minibuffer.close()
            self.minibuffer = None
            self.Layout()
            #dprint("active major mode = %s, trying to remove minibuffer from %s" % (self.editwin.frame.getActiveMajorMode(), self.editwin))
            if self.editwin.frame.getActiveMajorMode() == self.editwin:
                self.editwin.focus()
            #else:
                #dprint("active major mode = %s, tried to remove minibuffer from %s" % (self.editwin.frame.getActiveMajorMode(), self.editwin))
    
    def clearPopups(self):
        """Clear any popups that the mode may be using"""
        self.spring.clearRadio()


class MajorModeLoadError(RuntimeError):
    pass


class MajorMode(ContextMenuMixin, ClassPrefs, debugmixin):
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

    # Generic storage for all instances of this class
    class_storage = {}

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
    
    def getFrame(self):
        return self.frame
    
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
    
    @classmethod
    def preferThreadedLoading(cls, url):
        """Returns preference for using threaded loading of the given URL
        
        Loading a file in a background thread is possible in peppy, but it
        does cause a noticeable delay when loading a file from the local
        filesystem.  This class method is provided to allow each major mode to
        state its preference for threaded loading.
        
        Note that this preference will not be honored if the global setting for
        threaded loading is disabled.
        """
        return True

    @classmethod
    def isErrorMode(cls):
        """Return true if this mode is an error reporting mode rather than a
        normal view/edit mode.
        """
        return False
    
    def isTemporaryMode(self):
        """Return true if this mode can be replaced when the user loads a new
        file.
        
        Normally just returns the class's C{temporary} attribute, but this
        method can be overridden on an instance basis.
        """
        return self.temporary

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
    
    def checkFileModified(self):
        """Check if the buffer has been modified by an external program"""
        try:
            changed = self.buffer.isTimestampChanged()
            self.dprint("%s has been modified: %s" % (str(self.buffer.url), changed))
            if changed:
                retval = self.frame.showQuestionDialog("%s\n\nhas changed on disk.  Reload?" % self.buffer.url.path, "File Changed on Disk")
                if retval == wx.ID_YES:
                    self.buffer.revert()
                self.buffer.saveTimestamp()
        except OSError:
            self.dprint("%s has been deleted" % str(self.buffer.url))
            self.frame.showWarningDialog("%s\n\nhas been deleted on disk.  Your changes\nwill be lost unless you save the file." % self.buffer.url.path, "File Deleted on Disk")
            self.buffer.saveTimestamp()

    # If there is no title, return the keyword
    def getTitle(self):
        return self.keyword

    def getTabName(self):
        return self.buffer.getTabName()

    def getIcon(self):
        return getIconStorage(self.icon)

    def getWelcomeMessage(self):
        return "%s major mode" % self.keyword
    
    def getProperties(self):
        """Return a list of properties about the currently open file and any
        mode-specific info desired.
        
        @return: list of (name, value) pairs
        """
        lines = []
        lines.append(("URL", str(self.buffer.url)))
        lines.append(("File Size", vfs.get_size(self.buffer.url)))
        lines.append(("Read-only", self.buffer.readonly))
        lines.extend(self.buffer.stc.getProperties())
        lines.append(("Major Mode", self.keyword))
        if self.buffer.defaultmode != self.__class__:
            lines.append(("Default Major Mode", self.buffer.defaultmode.keyword))
        self.setStatusText(str(self.buffer.url))
        return lines
    
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
        self.Bind(wx.EVT_SET_FOCUS, self.OnFocus)
        self.Bind(wx.EVT_KEY_DOWN, self.frame.OnKeyDown)
        self.createContextMenuEventBindings()
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

    def OnFocus(self, evt):
        self.wrapper.spring.clearRadio()
        self.frame.spring.clearRadio()
        evt.Skip()

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
        if not self:
            # this can get called using a wx.CallAfter, so it's possible
            # that the mode has been deleted in the time between the call to
            # wx.CallAfter and when the event handler gets around to calling
            # this.
            return
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
    
    def applyLocals(self, locals):
        if locals:
            pairs = None
            if self.__class__ in locals:
                pairs = locals[self.__class__]
            elif 'subclass' in locals:
                cls = locals['subclass']
                if issubclass(self.__class__, cls):
                    pairs = locals[cls]
            if pairs:
                self.dprint("applying local variables from %s" % str(pairs))
                self.classprefsUpdateLocals(pairs)
        else:
            self.dprint("%s not found in %s" % (self.__class__, str(locals)))

    def settingsChanged(self, message=None):
        self.dprint("changing settings for mode %s" % self.__class__.__name__)
        self.applyLocals(message.data)
        self.applySettings()
        self.resetStatusBar()

    def focus(self):
        # The active tab may have changed, so make sure that this mode is
        # still in the active tab before setting focus.  Otherwise we might
        # change tabs unexpectedly.
        if self and self.frame.getActiveMajorMode() == self:
            self.SetFocus()
            self.focusPostHook()
            self.dprint("Set focus to %s (sanity check: FindFocus = %s, should be same)" % (self, self.FindFocus()))

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

    def showInitialPosition(self, url, options=None):
        """Hook to scroll to a non-default initial position if desired.
        
        @param url: url, including query string and fragment
        
        @param options: optional dict of name/value options
        """
        self.setViewPositionData(options)
    
    def getViewPositionData(self):
        """Get a dictionary containing enough information to restore the cursor
        position.
        
        This is used when reverting a file or changing major modes so that
        the cursor stays in the same place.  The return value should be a
        dictionary with whatever parameters necessary for the same type of
        major mode to restore the view.
        """
        return {}
    
    def revertPreHook(self):
        """Hook to save any view parameters that should be restored after a revert"""
        self._revert_data = self.getViewPositionData()
    
    def setViewPositionData(self, options=None):
        """Attempt to restore the state of the view from the given data.
        
        Note that the revert data passed in may be from a different major mode,
        so the data should be tested for compatibility.
        
        @param options: optional dict of name/value options
        """
        pass
    
    def revertPostHook(self):
        """Hook to restore the view parameters after a revert"""
        if getattr(self, '_revert_data'):
            self.setViewPositionData(self._revert_data)
        else:
            self.setViewPositionData()


class JobControlMixin(JobOutputMixin, ClassPrefs):
    """Process handling mixin to run scripts based on the current major mode.
    
    This mixin provides some common interfacing to run scripts that are
    tied to a major mode.  An interpreter classpref is provided that links
    a major mode to a binary file to run scripts in that mode.  Actions
    like RunScript and StopScript are tied to the presense of this mixin
    and will be automatically enabled when they find a mode has the
    interpreter_exe classpref.
    """
    #: Is the full path required to be specified in interpreter_exe?
    full_path_required = False
    
    default_classprefs = (
        PathParam('interpreter_exe', '', 'Program that can interpret this text and return results on standard output', fullwidth=True),
        StrParam('interpreter_args', '', 'Standard arguments to be used with the interpreter', fullwidth=True),
        BoolParam('autosave_before_run', True, 'Automatically save without prompting before running script'),
        IndexChoiceParam('output_log',
                         ['use minor mode', 'use sidebar'],
                         1, 'Does the output stay in the tab (minor mode) or visible to all tabs in the frame (major mode)'),
        )

    def getInterpreterArgs(self):
        """Hook to pass arguments to the command interpreter"""
        # FIXME: Why did I put interpreterArgs as an instance attribute?
        #dprint(hasattr(self, "interpreterArgs"))
        if hasattr(self, "interpreterArgs"):
            return self.interpreterArgs
        return self.classprefs.interpreter_args

    def getScriptArgs(self):
        """Hook to specify any arguments passed to the script itself.
        
        scriptArgs are saved as an instance attribute so they can be used as
        defaults the next time you run the script.
        """
        #dprint(hasattr(self, "scriptArgs"))
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
        script = self.buffer.getFilename()
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
                # Rather than calling the script directly, simulate how the
                # operating system uses the bangpath by calling the bangpath
                # program with the path to the script supplied as the argument
                script = script.replace(' ', '\ ')
                cmd = "%s %s %s" % (bangpath, script, self.getScriptArgs())
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
        #dprint(cmd)
        return cmd
    
    def bangpathModificationHook(self, path):
        """Hook method to modify the bang path as read from the first line in
        the script.
        
        Note that the passed-in string will have already had the "#!" characters
        stripped off, so only the pathname and arguments will exist.
        """
        return path
        
    def startInterpreter(self, argstring=None):
        """Interface used by actions to start the interpreter.
        
        This method is the outside interface to the job control mixin to
        start the interpreter.  See the RunScript action for an example
        of its usage in practice.
        """
        if argstring is not None:
            self.scriptArgs = argstring
            
        bangpath = None
        first = self.GetLine(0)
        if first.startswith("#!"):
            bangpath = self.bangpathModificationHook(first[2:].rstrip())
            
        msg = None
        path = self.classprefs.interpreter_exe
        if bangpath is None:
            if not path:
                msg = "No interpreter executable set.\n\nMust set the executable name in preferences or\ninclude a #! specifier as the first line in the file."
            elif self.full_path_required:
                if os.path.exists(path):
                    if os.path.isdir(path):
                        msg = "Interpreter executable:\n\n%s\n\nis not a valid file.  Locate the\ncorrect executable in the preferences." % path
                else:
                    msg = "Interpreter executable not found:\n\n%s\n\nLocate the correct path to the executable\nin the preferences." % path

        if msg:
            self.frame.showErrorDialog(msg, "Problem with interpreter executable")
        else:
            cmd = self.getCommandLine(bangpath)
            self.startCommandLine(cmd)
    
    def expandCommandLine(self, cmd):
        """Expand the command line to include the filename of the buffer"""
        filename = self.buffer.url.path.get_name()
        if '%' in cmd:
            cmd = cmd % filename
        else:
            cmd = "%s %s" % (cmd, filename)
        return cmd
    
    def startCommandLine(self, cmd, expand=False):
        """Attempt to create a process using the command line"""
        if hasattr(self, 'process'):
            self.frame.setStatusText("Already running a process.")
        else:
            if self.buffer.readonly or not self.classprefs.autosave_before_run:
                msg = "You must save this file to the local filesystem\nbefore you can run it through the interpreter."
                dlg = wx.MessageDialog(wx.GetApp().GetTopWindow(), msg, "Save the file!", wx.OK | wx.ICON_ERROR )
                retval=dlg.ShowModal()
                return
            else:
                self.save()

            if expand:
                cmd = self.expandCommandLine(cmd)
            if self.classprefs.output_log == 0:
                output = self
            else:
                output = JobOutputSidebarController(self.frame, self.registerProcess, self.deregisterProcess)
            ProcessManager().run(cmd, self.buffer.cwd(), output)

    def registerProcess(self, job):
        self.process = job
    
    def deregisterProcess(self, job):
        del self.process
    
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
            text = "\n" + job.getStartMessage()
            self.log.showMessage(text)

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
            text = "\n" + job.getFinishMessage()
            self.log.showMessage(text)


class BlankMode(MajorMode, wx.Window):
    """
    The most minimal major mode: a blank screen
    """
    keyword = "Blank"
    icon='icons/application.png'
    temporary = True
    allow_threaded_loading = False
    
    stc_class = NonResidentSTC

    def __init__(self, parent, wrapper, buffer, frame):
        MajorMode.__init__(self, parent, wrapper, buffer, frame)
        wx.Window.__init__(self, parent, -1, pos=(9000,9000))
        text = self.buffer.stc.GetText()
        lines = wx.StaticText(self, -1, text, (10,10))
        lines.Wrap(500)
        self.stc = self.buffer.stc
        self.buffer.stc.is_permanent = True

    @classmethod
    def verifyProtocol(cls, url):
        # Use the verifyProtocol to hijack the loading process and
        # immediately return the match if we're trying to load
        # about:blank
        if url.scheme == 'about' and url.path == 'blank':
            return True
        return False
