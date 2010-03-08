# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Base module for major mode implementations.

Implementing a new major mode means to extend from a wx Control and the
L{MajorMode} base mixin class.  Several attributes must be set: C{icon} that
points to the filename of the icon to be used, and C{keyword} which is a
text string that uniquely identifies the major mode from other major modes.
[FIXME: more documentation here.]

Once the major mode subclass has been created, it must be announced to
peppy.  This is done by returning the class from the peppy plugin method
L{IPeppyPlugin.getMajorModes} from an L{IPeppyPlugin} instance.  Plugins are
automatically loaded if they include a C{.peppy-plugin} companion file in
either the peppy/plugins directory of the source code or the plugins directory
in the user's peppy configuration directory.  Alternatively, plugins can be
installed directly in the python's site-packages directory using setuptools.
See more information in the L{IPeppyPlugin} documentation.

To provide menu items or toolbar items related to a major mode, you can
add actions using the L{SelectAction} class as a baseclass.

To provide context menu (i.e.  popup menus on a right mouse click) actions, use
the L{ContextMenu} interface to return L{SelectAction} classes in response to
the L{SelectAction.getPopupActions} method.
"""

import os, stat, sys, re, time

import wx
import peppy.third_party.aui as aui
import wx.stc
from wx.lib.pubsub import Publisher
from peppy.third_party.pubsub import pub

import peppy.vfs as vfs
from peppy.stcbase import *
from peppy.debug import *
from peppy.minor import *
from peppy.sidebar import *
from peppy.yapsy.plugins import *
from peppy.context_menu import ContextMenuMixin

from peppy.lib.userparams import *
from peppy.lib.iconstorage import *
from peppy.lib.controls import *
from peppy.lib.springtabs import SpringTabs
from peppy.lib.serializer import PickleSerializerMixin


class MajorModeLayout(ClassPrefs, debugmixin):
    """Class to manage the AuiManager perspectives for major modes
    
    Implements a set of classmethods to restore and save the AuiManager layout
    (perspectives in Aui terms) so that given the major mode and a URL, the
    layout of all the minor modes is restored to the same as when the user
    last edited the mode.
    
    Note that it is dependent on the major mode AND the URL; so the
    layout for file://some/path.txt in HexEdit mode is independent of
    file://some/path.txt in TextMode.
    """
    default_classprefs = (
        StrParam('layout_file', 'layout.dat', 'filename within config directory to use to store major/minor mode layout information'),
        )
    
    # a multi-level dict keyed first on major mode keyword, then the stringified
    # version of the URL.  I.e.  layout['Python']['file://some/path.txt']
    # returns the layout object.  (Note: the layout object is opaque as far as
    # this class is concerned.)
    layout = None

    class Serializer(PickleSerializerMixin):
        """Serializer to restore the layout dict to a pickle file.
        
        """
        def getSerializedFilename(self):
            filename = wx.GetApp().getConfigFilePath(MajorModeLayout.classprefs.layout_file)
            return filename
        
        def unpackVersion1(self, data):
            MajorModeLayout.layout = data
        
        def createVersion1(self):
            MajorModeLayout.layout = {}
        
        def packVersion1(self):
            return MajorModeLayout.layout
    
    @classmethod
    def loadLayout(cls):
        loader = cls.Serializer()
        loader.loadStateFromFile()
    
    @classmethod
    def getLayoutFirstTime(cls, major_mode_keyword, url):
        #dprint("getLayoutFirstTime")
        cls.loadLayout()
        cls.getLayout = cls.getLayoutSubsequent
        return cls.getLayoutSubsequent(major_mode_keyword, url)
    
    @classmethod
    def getLayoutSubsequent(cls, major_mode_keyword, url):
        #dprint("getLayoutSubsequent")
        ukey = unicode(url).encode("utf-8")
        if major_mode_keyword in cls.layout:
            try:
                key = str(url)
                # Convert old style string keyword to unicode keyword
                if ukey != key and key in cls.layout[major_mode_keyword]:
                    cls.layout[major_mode_keyword][ukey] = cls.layout[major_mode_keyword][key]
                    del cls.layout[major_mode_keyword][key]
            except UnicodeEncodeError:
                pass
        
        try:
            layout = cls.layout[major_mode_keyword][ukey]
        except KeyError:
            layout = {}
        cls.dprint("%s: layout=%s" % (unicode(url), unicode(layout)))
        return layout
    
    # First time through, call the loader
    getLayout = getLayoutFirstTime
    
    @classmethod
    def saveLayout(cls):
        saver = cls.Serializer()
        saver.saveStateToFile()
    
    @classmethod
    def updateLayoutFirstTime(cls, major_mode_keyword, url, perspective):
        #dprint("updateLayoutFirstTime")
        if cls.layout is None:
            cls.loadLayout()
        cls.updateLayout = cls.updateLayoutSubsequent
        cls.updateLayoutSubsequent(major_mode_keyword, url, perspective)
    
    @classmethod
    def updateLayoutSubsequent(cls, major_mode_keyword, url, perspective):
        #dprint("updateLayoutSubsequent")
        if major_mode_keyword not in cls.layout:
            cls.layout[major_mode_keyword] = {}
        
        cls.layout[major_mode_keyword][unicode(url)] = perspective
    
    # First time through, make sure the layout has been loaded
    updateLayout = updateLayoutFirstTime
    
    @classmethod
    def psQuit(cls):
        #dprint("quitting....")
        cls.saveLayout()
    
pub.subscribe(MajorModeLayout.psQuit, 'application.quit')


class MajorModeWrapper(wx.Panel, debugmixin):
    """Container around major mode that controls the AUI manager
    
    """    
    icon = "icons/blank.png"
    
    def __init__(self, parent):
        self.editwin=None # user interface window
        self.minibuffer=None
        self.sidebar=None
        self.minors = None
        
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
        self._mgr = aui.AuiManager()
        self._mgr.SetManagedWindow(self.splitter)
        self.Bind(aui.EVT_AUI_PERSPECTIVE_CHANGED, self.perspectiveChanged)
        
        if self.spring_aui:
            self._mgr.AddPane(self.spring, aui.AuiPaneInfo().
                              Name("MinorSpringTabs").Caption("MinorSpringTabs").
                              Right().Layer(10).Hide().DockFixed().
                              CloseButton(False).CaptionVisible(False).
                              LeftDockable(False).RightDockable(False))
        self._mgr.Update()

    def __del__(self):
        self.dprint("deleting %s: editwin=%s %s" % (self.__class__.__name__, self.editwin, self.getTabName()))
        # FIXME: remove stuff here?

    def createMajorMode(self, frame, buffer, requested=None):
        """Creates the editing window in the major mode wrapper
        
        This convenience method is the main driver for creating the
        L{MajorMode} instance and its associated event bindings, controls and
        minor modes.  It also adds the editing window to the AUI manager for
        the wrapper and calls the major mode's post-create hooks.
        
        @param frame: L{BufferFrame} instance that this major mode will be added
        
        @param buffer: L{Buffer} instance representing the STC that the major
        mode will be viewing
        
        @kwarg requested: optional L{MajorMode} class to be used to view
        the buffer.  If this argument is not specified, the default mode as
        determined by the file opening process (see L{MajorModeMatcherDriver}
        will be used.
        """
        # Remove the old mode if it exists
        self.deleteMajorMode()
        
        if not requested:
            requested = buffer.defaultmode
        self.dprint("creating major mode %s" % requested)
        self.editwin = requested(self.splitter, self, buffer, frame)
        buffer.addViewer(self.editwin)
        paneinfo = aui.AuiPaneInfo().Name("main").CenterPane()
        layout = MajorModeLayout.getLayout(self.editwin.keyword,
                                           self.editwin.buffer.url)
        if "main" in layout:
            self._mgr.LoadPaneInfo(layout["main"], paneinfo)
        self._mgr.AddPane(self.editwin, paneinfo)
        
        try:
            self.createMajorModeDetails(layout)
        except:
            # Failure creating something during the major mode initialization
            # process; remove the partially created mode from the tabbed pane
            buffer.removeViewer(self.editwin)
            self._mgr.DetachPane(self.editwin)
            self.editwin.Hide()
            self.editwin = None
            raise
        
        self._mgr.Update()
        
        buffer.startChangeDetection()

        if not requested:
            # If the major mode creation was successful, change the default
            # major mode if the old default is the most general major mode.
            if buffer.defaultmode.verifyMimetype('text/plain'):
                self.dprint("Changing default mode of %s to %s" % (buffer, requested))
                buffer.defaultmode = requested
        return self.editwin

    def createMajorModeDetails(self, layout):
        """Driver to create all the hooks, event listeners, and minor modes
        of the new major mode.
        
        If any of the methods called within this driver raise an exception, the
        major mode will be removed and an error mode will replace it.
        """
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
        self.loadMinorModes(layout)
        self.dprint("loadMinorModes done in %0.5fs" % (time.time() - start))
        self.editwin.loadMinorModesPostHook()
        self.dprint("loadMinorModesPostHook done in %0.5fs" % (time.time() - start))
        Publisher().sendMessage('mode.postinit', self.editwin)
        self.dprint("mode.postinit message done in %0.5fs" % (time.time() - start))
    
    def deleteMajorMode(self):
        """Remove the major mode from the wrapper
        
        Performs cleanup actions to remove the major mode references from this
        wrapper instance.
        """
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
        """Returns the name to be used in the notebook tab
        
        @return: string containing a short string identifying the tab contents
        """
        if self.editwin:
            return self.editwin.getTabName()
        return "Empty"
    
    def getTabBitmap(self):
        """Returns icon to be used in the notebook tab
        
        @return: wxBitmap instance
        """
        if self.editwin:
            icon = self.editwin.icon
        else:
            icon = self.icon
        return getIconBitmap(icon)
    
    def loadMinorModes(self, layout):
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
                                    initial=minor_names, perspectives=layout)

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
        self.updateLayout()
        return entry.win

    def getActiveMinorModes(self, ignore_hidden=False):
        """Proxy the minor mode requests up to the wrapper"""
        if self.minors:
            return self.minors.getActive(ignore_hidden)
        return []
    
    def getPerspective(self):
        layout = {}
        paneinfo = self._mgr.GetPane(self.editwin)
        perspective = self._mgr.SavePaneInfo(paneinfo)
        layout[paneinfo.name] = perspective
        for minor in self.getActiveMinorModes():
            paneinfo = self._mgr.GetPane(minor)
            if paneinfo.IsShown():
                # Force the current size of the minor mode to be the best size,
                # otherwise on restart the AuiManager will restore the default
                # saved best size instead of the last size set by the user
                size = minor.GetSize()
                paneinfo.BestSize(size)
                perspective = self._mgr.SavePaneInfo(paneinfo)
                layout[paneinfo.name] = perspective
        #dprint(layout)
        return layout
    
    def getPerspectiveByName(self, name):
        layout = self.getPerspective()
        return layout[name]
    
    def perspectiveChanged(self, evt):
        #dprint("Changed!!!!")
        self.updateLayout()
    
    def updateLayout(self):
        if self.editwin is not None:
            layout = self.getPerspective()
            MajorModeLayout.updateLayout(self.editwin.keyword, self.editwin.buffer.url, layout)

    def setMinibuffer(self, minibuffer=None):
        """Convenience method to display the minibuffer.
        
        Only one minibuffer can be active at any one time, and this method will
        remove any existing minibuffer before replacing it with the specified
        minibuffer.
        """
        self.removeMinibuffer()
        if minibuffer is not None:
            self.minibuffer = minibuffer
            self.minibuffer.addToSizer(self.GetSizer())
            self.Layout()
            self.minibuffer.show()

    def removeMinibuffer(self, specific=None, detach_only=False):
        """Convenience method to remove the mode's minibuffer
        
        Removes the currently active minibuffer (if it exists).  Due to some
        wx issues and the required use of CallAfter on some platforms, some
        care is taken to only remove the requested minibuffer.  If a specific
        minibuffer is passed in as an argument, only that minibuffer will be
        removed; otherwise the active minibuffer will be removed.
        
        @kwarg specific: instance of minibuffer to remove.  In some cases,
        for example where a minibuffer calls another minibuffer, the
        previous minibuffer will have been removed by the newer minibuffer's
        initialization process.
        
        @kwarg detach_only: optional, defaults to False.  If True, the
        minibuffer is only removed from the AUI manager and not destroyed.
        This is only used in rare cases.
        """
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
    
    #: The preferences tab that this mode will appear in, or None if it should not appear in the preferences tab
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
        StrParam('filename_regex', '', 'Regular expression used to match against the filename part of the URL.  Successful match indicates the major mode is compatible with the filename', fullwidth=True),
        StrParam('extensions', '', 'List of filename extensions to match to this major mode.  This is matched after the regular expression, and a successful match indicates the mode is compatible with the filename', fullwidth=True),
        StrParam('minor_modes', '', 'List of minor mode keywords that should be displayed when starting this major mode', fullwidth=True),
        IntParam('line_number_offset', 1, 'Number to add to the line number reported by the mode\'s stc in order to display'),
        IntParam('column_number_offset', 1, 'Number to add to the column number reported by the mode\'s stc in order to display'),
        )

    # Need one keymap per subclass, so we can't use the settings.
    # Settings would propogate up the class hierachy and find a keymap
    # of a superclass.  This is a dict based on the class name.
    localkeymaps = {}

    # Cache kept for saving items that apply to each major mode class.  The
    # cache is indexed by the major mode class attribute 'keyword', because
    # other ways to attempt to create a unique value per class don't work well.
    # Major modes have complex method resolution orders (i.e.  complicated
    # inheritance paths), and testing for the presence of a class attribute
    # doesn't do what is needed.  For instance, if a FundamentalMode has been
    # instantiated, all future subclass modes will detect the presence of a
    # class attribute.  Indexing by major mode keyword prevents this problem.
    major_mode_class_cache = {}


    def __init__(self, parent, wrapper, buffer, frame):
        # set up the view-local versions of classprefs
        self.classprefsCopyToLocals()
        
        self.wrapper = wrapper
        self.buffer = buffer
        self.frame = frame
        self.popup = None
        self.status_info = None
        
        self.pending_idle_messages = {}
        self.ready_for_idle_events = False
        
        # Cache for anything that should be attached to this instance of the
        # major mode
        self.major_mode_instance_cache = {}
        
        self.createClassCache()
        
        # Create a window here!
        pass
    
    def getFrame(self):
        """Convenience method needed by L{ContextMenuMixin} to return the
        L{BufferFrame} instance of this major mode.
        """
        return self.frame
    
    def __del__(self):
        #dprint("deleting %s: buffer=%s %s" % (self.__class__.__name__, self.buffer, self.getTabName()))
        self.major_mode_instance_cache = None
        self.removeListeners()
        self.removeListenersPostHook()
        self.deleteWindowPostHook()
    
    def isReadyForIdleEvents(self):
        """Return whether or not the mode is ready for idle event processing.
        
        """
        return self.ready_for_idle_events
    
    def setReadyForIdleEvents(self):
        """Set the idle event processing flag
        
        Currently there's no automatic way to determine when the mode is
        fully initialized, so this must be called by hand in BufferFrame or
        FrameNotebook when it's known that the mode is ready to process events.
        """
        self.ready_for_idle_events = True
    
    @classmethod
    def getClassCache(cls):
        """Return the dict that is used for this class's class cache
        
        This always checks for the existence of the class cache, so it's safe
        to use this before an instance of the major mode has been created.
        """
        if not cls.keyword in cls.major_mode_class_cache:
            cls.dprint("Creating class cache for %s" % cls)
            cls.major_mode_class_cache[cls.keyword] = {}
        return cls.major_mode_class_cache[cls.keyword]
    
    @classmethod
    def createClassCache(cls):
        """Create a cache for this particular major mode class.
        
        Note that the class cache can't be a simple class attribute of
        MajorMode because that means that all subclasses of this will see the
        same cache, and that's not at all what we intend.  Each class type
        should have its own cache.
        """
        cls.getClassCache()
    
    @classmethod
    def removeFromClassCache(cls, *names):
        """Remove the named values from the class cache"""
        cache = cls.major_mode_class_cache[cls.keyword]
        for name in names:
            if name in cache:
                del cache[name]
    
    @classmethod
    def getSubclassHierarchy(cls):
        """Return the hierarchy of MajorMode subclasses
        
        Returns a list containing only subclasses of MajorMode without any
        mixins or other classes in the inheritance tree.
        
        For example, L{PythonMode} is subclassed from L{FundamentalMode} which
        is in turn subclassed from L{MajorMode}, meaning the following list
        would be returned: C{[PythonMode, FundamentalMode, MajorMode]}
        """
        hierarchy = []
        for subclass in cls.__mro__:
            if issubclass(subclass, MajorMode):
                hierarchy.append(subclass)
        return hierarchy

    def getInstanceCache(self):
        """Returns the dict used as the instance's cache of information.
        
        Rather than promoting the idea of polluting the namespace of the
        major mode with arbitrary keywords, this dict is used to store
        information without regard to conflicting with any of the major mode's
        class attributes.  Because the major mode may have a large subclass
        hierarchy, it's fairly common to accidentally use an attribute in a
        subclass that alters meaning of the attribute in a superclass.  This
        can lead to difficult to debug problems, and sometimes in spectacular
        failures not limited to application crashes and core dumps.
        """
        return self.major_mode_instance_cache
    
    def removeFromInstanceCache(self, *names):
        """Remove the named keywords from the instance cache"""
        for name in names:
            if name in self.major_mode_instance_cache:
                del self.major_mode_instance_cache[name]

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
    def verifyOpenWithRewrittenURL(cls, url):
        """Check to see if the URL could be opened if it were rewritten in some
        manner.
        
        This is provided in case a file in the filesystem can also be
        opened as a folder, for example a zip file that could be opened in
        binary mode or as a folder containing other files.  If the url were
        specified as file://path/to/file.zip and the protocol were rewritten
        as zip://path/to/file.zip then DiredMode could display the files
        contained within the zip.

        @param url: the original URL
        
        @return: False if the mode doesn't support a rewritten url, or a new
        url that the mode does support.
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
        if hasattr(cls, 'regex') and cls.regex:
            match=re.search(cls.regex, filename)
            if match:
                return True
        if cls.classprefs.filename_regex:
            match=re.search(cls.classprefs.filename_regex, filename)
            if match:
                return True
        if cls.classprefs.extensions:
            exts = cls.classprefs.extensions.split()
            filename, ext = os.path.splitext(filename)
            return ext[1:] in exts
        return False

    @classmethod
    def verifyMimetype(cls, mimetype):
        """Hook to allow the major mode to determine compatibility by mimetype.

        mimetype: a string indicating the MIME type of the file
        
        return: True if the mode supports the MIME type
        """
        if cls.verifyMimetypeHook(mimetype):
            return True
        if cls.mimetype:
            if isinstance(cls.mimetype, str) and mimetype == cls.mimetype:
                return True
            for mime in cls.mimetype:
                if mimetype == mime:
                    return True
        return False

    @classmethod
    def verifyMimetypeHook(cls, mimetype):
        """Additional hook method for mimetype verification.
        
        Override this method to provide additional capability while still
        keeping the basic functionality of L{verifyMimetype}; override
        L{verifyMimetype} to replace all mimetype verification functionality.
        """
        pass

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
    def verifyKeyword(cls, keyword):
        """Hook to verify the mode's keyword or emacs alias matches the given
        string.

        @param keyword: text string that identifies a major mode

        @returns: boolean if the keyword matches either the keyword class
        attribute or one of the emacs aliases
        """
        if keyword == cls.keyword:
            return True
        if cls.emacs_synonyms:
            if isinstance(cls.emacs_synonyms, str):
                if keyword == cls.emacs_synonyms:
                    return True
            else:
                if keyword in cls.emacs_synonyms:
                    return True
        return False

    @classmethod
    def verifyCompatibleSTC(cls, stc_class):
        """Hook to verify the mode can work with the specified STC class

        @param stc_class: STC class of interest

        @returns: boolean if the major mode works with the STC
        """
        #dprint("%s: subclass=%s other=%s self=%s" % (cls.keyword, issubclass(stc_class, cls.stc_class), stc_class, cls.stc_class))
        return issubclass(stc_class, cls.stc_class)
    
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
        """Save the file.
        
        Saves the file to the URL specified, or if not specified to the
        original URL from which the file was loaded.
        
        Returns True if the file save was successful; False otherwise.
        """
        veto = self.savePreHook(url)
        if veto == False:
            return False
        try:
            self.buffer.save(url)
            self.savePostHook()
            self.status_info.setText(u"Saved %s" % self.buffer.url)
            return True
        except IOError, e:
            self.status_info.setText(unicode(e))
        except UnicodeEncodeError, e:
            self.status_info.setText(unicode(e))
        except LookupError, e:
            # Bad encoding name!
            self.status_info.setText(unicode(e))
        return False

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
            self.dprint(u"%s has been modified: %s" % (self.buffer.url, changed))
            if changed:
                retval = self.frame.showQuestionDialog(u"%s\n\nhas changed on disk.  Reload?" % self.buffer.url.path, "File Changed on Disk")
                if retval == wx.ID_YES:
                    self.buffer.revert()
                self.buffer.saveTimestamp()
        except OSError:
            self.dprint(u"%s has been deleted" % self.buffer.url)
            self.frame.showWarningDialog(u"%s\n\nhas been deleted on disk.  Your changes\nwill be lost unless you save the file." % self.buffer.url.path, "File Deleted on Disk")
            self.buffer.saveTimestamp()

    # If there is no title, return the keyword
    def getTitle(self):
        """Return title of the major mode.
        
        This is used as a long title of the major mode itself, not the name of
        the contents of the major mode.
        """
        return self.keyword

    def getTabName(self):
        """Returns the name to be used as the notebook tab.
        
        @return: a concise string to be used as the text of the notebook tab.
        This namem should reflect the contents of the major mode, not the
        name of the type of major mode.  For instance if editing the python
        file "main.py", this method must return "main.py" rather than "Python"
        """
        return self.buffer.getTabName()

    def getIcon(self):
        """Returns the icon to be used as the notebook icon.
        
        @return: a wxBitmap typically representing the type of major mode, but
        may be modified to also show some specificity to the particular file
        being edited.
        """
        return getIconStorage(self.icon)

    def getWelcomeMessage(self):
        """Returns a descriptive text string to be used in the status bar
        
        Once the major mode has been initialized and is ready for user
        interaction, a status bar message is displayed indicating that it is
        ready to be edited.  This method returns that message.  It should be an
        informative string that conveys some meaning regarding the particular
        major mode and any statistics that would be valuable to the user.
        """
        return "%s major mode" % self.keyword
    
    def getProperties(self):
        """Return a list of properties about the currently open file and any
        mode-specific info desired.
        
        @return: list of (name, value) pairs
        """
        lines = []
        lines.append(("URL", unicode(self.buffer.url)))
        lines.append(("File Size", vfs.get_size(self.buffer.url)))
        lines.append(("Read-only", self.buffer.readonly))
        lines.extend(self.buffer.stc.getProperties())
        lines.append(("Major Mode", self.keyword))
        if self.buffer.defaultmode != self.__class__:
            lines.append(("Default Major Mode", self.buffer.defaultmode.keyword))
        self.setStatusText(unicode(self.buffer.url))
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
        """Main driver method to create event bindings
        
        Sets event bindings needed by various subsystems.  Typically, this
        method should not be overriden by subclasses; rather, the method
        L{createEventBindingsPostHook} is provided for subclass use.
        """
        if hasattr(self, 'addUpdateUIEvent'):
            self.addUpdateUIEvent(self.OnUpdateUI)
        self.Bind(wx.EVT_SET_FOCUS, self.OnFocus)
        self.createContextMenuEventBindings()

    def createEventBindingsPostHook(self):
        """Hook provided for subclasses to add event bindings
        
        Rather than overridding L{createEventBindings}, subclasses should
        override this to add their own event bindings.
        """
        pass
    
    def getKeyboardCapableControls(self):
        """Return a list of all controls in the major mode that take keyboard
        focus.
        
        This is used by L{UserAccelerators} in its call to L{manageFrame}.
        
        Typically the return value is a one element list containing the
        major mode itself, but in some cases the major mode may be a panel
        containing other controls.  In that case, the controls that actually
        take keyboard focus should be returned instead of the major mode.
        """
        return [self]

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
        self.OnUpdateUIHook(evt)
        if evt is not None:
            evt.Skip()

    def OnUpdateUIHook(self, evt):
        pass

    def OnFocus(self, evt):
        """Callback used to pop down any springtabs.
        
        When the major mode loses keyboard focus, the springtabs should be
        cleared to allow the new focus receiver to display itself.  This fails
        when the major mode never takes keyboard focus at all, in which case a
        focus-lost event is never generated and this method never gets called.
        """
        self.wrapper.spring.clearRadio()
        self.frame.spring.clearRadio()
        evt.Skip()

    def idleHandler(self):
        """Driver for major mode specific idle handling code.
        
        Typically this method should not be overridden; rather, the sublass
        should override L{idlePostHook} to provide specific idle handling code
        for the major mode instance.
        """
        #dprint(u"Idle starting for %s at %f" % (self.buffer.url, time.time()))
        if self.pending_idle_messages:
            self.processPendingIdleMessages()
        self.idlePostHook()
        #dprint(u"Idle finished for %s at %f" % (self.buffer.url, time.time()))
    
    def sendMessageWhenIdle(self, topic, **kwargs):
        """Defers a pubsub3 message until idle processing
        
        @param topic: message topic
        @kwargs kwargs: keyword arguments for pubsub3 message
        """
        if topic not in self.pending_idle_messages:
            #dprint("deferring till idle: %s, %s" % (topic, kwargs))
            self.pending_idle_messages[topic] = kwargs
    
    def processPendingIdleMessages(self):
        """Idle message handler for messages deferred by L{sendMessageWhenIdle}
        
        Called internally by L{idleHandler} and shouldn't be called directly.
        """
        messages = self.pending_idle_messages
        self.pending_idle_messages = {}
        for topic, kwargs in messages.iteritems():
            #dprint("Sending: %s, %s" % (topic, kwargs))
            pub.sendMessage(topic, **kwargs)

    def idlePostHook(self):
        """Hook for subclasses to process during idle time.
        
        Subclasses should typically override this rather than L{idleHandler}.
        """
        pass

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
        self.status_info.resetProgress()
        self.status_info.resetIcons()
        self.createStatusIcons()
    
    def setStatusText(self, text, field=0):
        """Convenience function to set the status bar text.
        
        The status bar has at least two text fields, a primary (field=0) and
        a secondardy, smaller field (field=1).  Field 0 is also used for
        menu/toolbar updates and therefore will change when the user moves the
        mouse to the menubar or toolbar.  Field 1 is used for line updates in
        classes like L{FundamentalMode} and keystroke updates by the keyboard
        procassing system.
        """
        self.status_info.setText(_(text), field)
    
    ##### Proxy services for the wrapper
    def updateAui(self):
        self.wrapper._mgr.Update()
    
    def getMinibuffer(self):
        """Returns the minibuffer instance in use, or None"""
        return self.wrapper.minibuffer

    def setMinibuffer(self, minibuffer=None):
        """Proxy the minibuffer requests up to the wrapper"""
        self.wrapper.spring.clearRadio()
        self.frame.spring.clearRadio()
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
        """Driver to update the major mode when settings are changed by the user.
        
        When the user makes settings changes (typically through the Preferences
        dialog), this method must be called to allow the mode to update itself
        to the new preference settigs.
        
        Rather than being called directly, however, this is done using the
        peppy.preferences.changed message of the pubsub system.
        """
        self.dprint("changing settings for mode %s" % self.__class__.__name__)
        self.applyLocals(message.data)
        self.applySettings()
        self.resetStatusBar()
    
    def regenerateKeyBindings(self):
        """Reconstruct the keybindings for the major mode and all dependencies.
        
        """
        self.frame.setMenumap(self)

    def focus(self):
        """Convenience method to set focus to the appropciate control used by
        the major mode.
        
        In most major modes, this is equivalent to calling SetFocus on the
        primary window, although some additional housekeeping duties are also
        performed.
        """
        # The active tab may have changed, so make sure that this mode is
        # still in the active tab before setting focus.  Otherwise we might
        # change tabs unexpectedly.
        if self and self.frame.getActiveMajorMode() == self:
            # Set focus to the first keyboard capable control
            capable = self.getKeyboardCapableControls()
            capable[0].SetFocus()
            self.focusPostHook()
            self.dprint("Set focus to %s (sanity check: FindFocus = %s, should be same)" % (self, self.FindFocus()))

    def focusPostHook(self):
        """Hook called after L{focus}
        
        Hook provided for L{focus} to allow major mode subclass to add
        functionality to pass the focus hook without overriding L{focus} and
        providing the necessary housekeeping
        """
        pass

    def tabActivatedHook(self):
        """Hook to update some user interface parameters after the tab has been
        made the current tab.
        """
        pass

    def showModified(self,modified):
        """Convenience function to update the frame's {showModified} method."""
        self.frame.showModified(self)

    def showBusy(self, busy, change_cursors=False):
        """Convenience method to enable or disable user action to the major mode.
        
        This method is normally used to show that the mode is involved in a
        long-running process.  When busy, it cuts off user interaction to the
        major mode and displays a busy cursor.
        
        @param busy: True if the major mode is busy and should not accept user
        input, or false when the long-running action is complete to restore
        the ability for the user to interact.
        
        @kwarg change_cursors: (experimental) If True will attempt to
        recursively change the cursors of all children to the busy cursor.
        Only works on Linux, and then only changing to the busy cursor.
        Restoring the cursors to the saved cursor seems to put everything
        back to the default arrow regardless of the saved state.
        """
        if busy:
            cursor = wx.StockCursor(wx.CURSOR_ARROWWAIT)
            self.SetCursor(cursor)
            self._save_cursors = {}
            if change_cursors:
                def saveCursors(parent):
                    try:
                        old = parent.GetCursor()
                        self._save_cursors[id(parent)] = old
                    except:
                        dprint("Couldn't get cursor for %s" % parent)
                    for child in parent.GetChildren():
                        saveCursors(child)
                saveCursors(self)
            def disableChildren(parent):
                #dprint("disabling %s, %d" % (parent, id(parent)))
                parent.Enable(False)
                if change_cursors:
                    try:
                        parent.SetCursor(cursor)
                    except:
                        dprint("Couldn't set cursor for %s" % parent)
                        if id(parent) in self._save_cursors:
                            del self._save_cursors[id(parent)]
                for child in parent.GetChildren():
                    disableChildren(child)
            disableChildren(self)
        else:
            def enableChildren(parent):
                #dprint("enabling %s, %d" % (parent, id(parent)))
                parent.Enable(True)
                if id(parent) in self._save_cursors:
                    parent.SetCursor(self._save_cursors[id(parent)])
                for child in parent.GetChildren():
                    enableChildren(child)
            enableChildren(self)
            cursor = wx.StockCursor(wx.CURSOR_DEFAULT)
            self.SetCursor(cursor)
            del self._save_cursors

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
        self.buffer.stopChangeDetection()
    
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
        self.buffer.startChangeDetection()
    
    
    ### Macro processing flag
    def isMacroProcessingAvailable(self):
        """Flag to indicate whether or not macro processing is available given
        the current state of the major mode
        """
        return False
    
    def beginProcessingMacro(self):
        """Set a flag indicating that macro processing is taking place
        
        This is needed by the action processing to force the action to take
        place even if the focus is not on the major mode.
        
        This call should be used before playing back any macros.
        """
        self.processing_macro = True
    
    def endProcessingMacro(self):
        """Unset the macro processing flag.
        
        """
        del self.processing_macro
    
    def isProcessingMacro(self):
        """Convenience method used by the action processing to check if a macro
        is being played back.
        
        Macro processing turns off the checks for keyboard focus being on the
        major mode.
        """
        return hasattr(self, 'processing_macro')
    
    ## Printing
    def isPrintingSupported(self):
        """Returns True if possible to print the current view of the major
        mode.
        
        The L{getHtmlForPrintout} method is checked first, and if that method
        returns None, the L{getPrintout} method is checked.
        """
        return False
    
    def getHtmlForPrinting(self):
        """If the major mode is capable of producing an HTML representation of
        its data, return that HTML here.
        
        The easiest way to implement printing of a major mode is to convert it
        to HTML and let the HTLMEasyPrinting class handle the details.  If it
        is possible to produce are representation of the major mode in HTML,
        that HTML should be returned here.
        
        If this method returns None, the L{getPrintout} method will be used.
        """
        return None
    
    def getPrintout(self, page_setup_data=None):
        """Returns a wx.Printout object that the printer management driver
        can use to generate a print preview or a paper copy.
        
        @xwarg page_setup_data: an optional instance of a
        wx.PageSetupDialogData that provides the margins
        """
        return None
    
    ## File drop target
    def handleFileDrop(self, x, y, filenames):
        """Handle filenames dropped onto major mode from the file manager or
        windows explorer.
        
        Major mode subclasses can override this method to provide a different
        means to handle files being dropped on the application.  The default
        method is to simply open up the files dropped in new tabs, but this
        can be changed by overriding this method.
        """
        dprint("%d file(s) dropped at %d,%d:" % (len(filenames), x, y))
        for filename in filenames:
            dprint("filename='%s'" % filename)
            self.frame.open(filename)


class EmptyMode(MajorMode, wx.Window):
    """
    The most minimal major mode: a blank screen
    """
    keyword = "Empty"
    icon='icons/application.png'
    
    stc_class = NonResidentSTC
    
    preferences_tab = None

    def __init__(self, parent, wrapper, buffer, frame):
        MajorMode.__init__(self, parent, wrapper, buffer, frame)
        wx.Window.__init__(self, parent, -1, pos=(9000,9000))
        text = self.buffer.stc.GetText()
        lines = wx.StaticText(self, -1, text, (10,10))
        font_family = self.getFontFamily()
        if font_family is not None:
            lines.SetFont(wx.Font(10, font_family, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
        lines.Wrap(500)
        self.stc = self.buffer.stc
        self.buffer.stc.is_permanent = True
    
    def getFontFamily(self):
        return None


class BlankMode(EmptyMode):
    """Special case of EmptyMode to short circuit the about:blank url
    """
    temporary = True
    allow_threaded_loading = False

    @classmethod
    def verifyProtocol(cls, url):
        # Use the verifyProtocol to hijack the loading process and
        # immediately return the match if we're trying to load
        # about:blank
        if url.scheme == 'about' and url.path == 'blank':
            return True
        return False
