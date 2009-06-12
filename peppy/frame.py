# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os, re, threading
from cStringIO import StringIO

import wx
import wx.aui
import wx.stc
from wx.lib.pubsub import Publisher

import peppy.vfs as vfs

from peppy.fileopener import FileOpener, FileOpenerExceptionHandled
from peppy.notebook import FrameNotebook

from peppy.actions import *
from peppy.menu import *
from peppy.lib.multikey import *
from peppy.lib.iconstorage import *
from peppy.lib.controls import *
from peppy.lib.userparams import *
from peppy.lib.null import Null

from peppy.configprefs import *
from peppy.stcbase import *
from peppy.major import *
from peppy.sidebar import *
from peppy.debug import *
from peppy.buffers import *

    
class WindowList(OnDemandGlobalListAction):
    name="Frames"
    default_menu = ("Window", -999)
    inline = True
    osx_minimal_menu = True
    
    # provide storage to be shared among instances
    storage = []
    
    # hidden frame for use on Mac OS X
    hidden = None
    
    @classmethod
    def calcHash(cls):
        cls.globalhash = None
    
    @classmethod
    def getFrames(self):
        return [frame for frame in WindowList.storage]
    
    @classmethod
    def setHiddenFrame(cls, hidden):
        cls.hidden = hidden
    
    @classmethod
    def canCloseWindow(cls, frame):
        if cls.hidden:
            # When on OS X, the user is always allowed to close windows unless
            # the user somehow tries to close the hidden window (which should
            # never be possible)
            if frame == cls.hidden:
                dprint("Attempting to close the hidden window on OS X.  Should never happen!")
                return False
            return True
        elif len(WindowList.storage) == 1:
            # If attempting to close the last window when not on OS X, check to
            # make sure that the user didn't cancel the quit
            return wx.GetApp().quit()
        return True

    def getItems(self):
        return [frame.getTitle() for frame in WindowList.storage]

    def action(self, index=0, multiplier=1):
        assert self.dprint("top window to %d: %s" % (index,WindowList.storage[index]))
        wx.GetApp().SetTopWindow(WindowList.storage[index])
        wx.CallAfter(WindowList.storage[index].Raise)

class DeleteWindow(SelectAction):
    alias = "delete-window"
    name = "&Delete Window"
    default_menu = ("Window", 101)
    tooltip = "Delete current window"
    
    def action(self, index=-1, multiplier=1):
        self.frame.closeWindow()

    def isEnabled(self):
        if len(WindowList.storage)>1:
            return True
        return False

class NewWindow(SelectAction):
    alias = "new-window"
    name = "&New Window"
    tooltip = "Open a new window"
    default_menu = ("Window", -100)
    key_bindings = {'emacs': "C-X 5 2",}
    osx_minimal_menu = True
    
    def action(self, index=-1, multiplier=1):
        frame=BufferFrame()
        frame.Show(True)


class BringAllToFront(SelectAction):
    """Bring all peppy windows to the front of the window stack"""
    name = "Bring All to Front"
    default_menu = ("Window", -300)

    def action(self, index=-1, multiplier=1):
        top = wx.GetApp().GetTopWindow()
        for frame in WindowList.getFrames():
            frame.Raise()
        top.Raise()


class Minimize(SelectAction):
    """Minimize the current window"""
    name = "Minimize"
    default_menu = ("Window", -1)

    def action(self, index=-1, multiplier=1):
        self.frame.Iconize(not self.frame.IsIconized())


## BufferFrames

class FrameDropTarget(wx.FileDropTarget, debugmixin):
    def __init__(self, frame):
        wx.FileDropTarget.__init__(self)
        self.frame = frame

    def OnDropFiles(self, x, y, filenames):
        assert self.dprint("%d file(s) dropped at %d,%d:" % (len(filenames),
                                                             x, y))

        for filename in filenames:
            assert self.dprint("filename='%s'" % filename)
            self.frame.open(filename)


class BufferFrame(wx.Frame, ClassPrefs, debugmixin):
    frameid=0
    load_error_count = 0
    size_timer = None
    
    preferences_tab = "General"
    preferences_label = "Windows"
    if wx.Platform == "__WXMAC__":
        icon = "icons/application_osx.png"
    else:
        icon = "icons/application.png"
    
    perspectives={}

    default_classprefs = (
        IntParam('width', 800, 'Width of the main frame in pixels'),
        IntParam('height', 600, 'Height of the main frame in pixels'),
        BoolParam('show_toolbar', True, 'Show the toolbar on all frames?\nNote: this is a global setting for all frames.'),
        BoolParam('resize_becomes_default', True, 'Should the new size following a resize become the default size of all subsequently created frames?'),
        # FIXME: this attempt at fast resizing caused Freeze() mismatch
        # problems.  It's not worth that much, so I'm disabling it for
        # now.
        # BoolParam('fast_resize', False, 'Speed up resize events by deferring window\nrepaints until the mouse stops moving'),
        )

    default_menubar = {
        _("File"): 0,
        _("File/Export"): 850, # position within the parent menu for submenus
        _("Edit"): 0.001,
        _("View"): 0.003,
        _("View/Apply Settings"): -980,
        _("Tools"): 0.004,
        _("Transform"): 0.005,
        _("Project"): 1000.05,
        _("Documents"): 1000.1,
        _("Window"): 1000.2,
        _("&Help"): 1000.3,
        }


    def __init__(self, urls=[], id=-1, buffer=None):
        BufferFrame.frameid+=1
        self.name="peppy: Window #%d" % BufferFrame.frameid
        
        # flags to prevent multiple timestamp checks
        self.pending_timestamp_check = False
        self.currently_processing_timestamp = False

        # initialize superclass
        pos, size = self.initPositionAndSize()
        wx.Frame.__init__(self, None, id=-1, title=self.name, pos=pos, size=size, style=wx.DEFAULT_FRAME_STYLE|wx.CLIP_CHILDREN)

        self.initIcon()
        self.initLayout()
        self.initMenu()
        self.loadSidebars()
        self.initEventBindings()
        self.initLoad(buffer, urls)
        self.initRegisterWindow()
        self.Show()
    
    def initPositionAndSize(self):
        pos = wx.DefaultPosition
        size = (int(self.classprefs.width), int(self.classprefs.height))
        return pos, size
    
    def initIcon(self):
        icon = wx.EmptyIcon()
        icon.CopyFromBitmap(getIconBitmap('icons/peppy.png'))
        self.SetIcon(icon)

    def initLayout(self):
        ModularStatusBar(self)

        hsplit = wx.BoxSizer(wx.HORIZONTAL)
        self.SetAutoLayout(True)
        self.SetSizer(hsplit)
        
        self.spring = SpringTabs(self)

        # tell FrameManager to manage this frame        
        self._mgr = wx.aui.AuiManager()
        self._mgr.SetManagedWindow(self)

        self.tabs = FrameNotebook(self)
        self._mgr.AddPane(self.tabs, wx.aui.AuiPaneInfo().Name("notebook").
                          CenterPane())
        self.sidebar_panes = []
        
        # paneinfo can use the C++ style notation for setting flags because
        # each method of AuiPaneInfo returns itself
        paneinfo = wx.aui.AuiPaneInfo().Name("SpringTabs").Caption("SpringTabs").Left().Layer(10).CloseButton(False).CaptionVisible(False).LeftDockable(False).RightDockable(False)
        
        # Stock wxPython distributed with OS X 10.5 is version 2.8.4.0, which
        # apparently doesn't have the DockFixed method.  So, I check for that
        # here before using it.
        if hasattr(paneinfo, 'DockFixed'):
            paneinfo.DockFixed()
        self._mgr.AddPane(self.spring, paneinfo)

    def initMenu(self):
        UserActionClassList.setDefaultMenuBarWeights(self.default_menubar)
        menubar = wx.MenuBar()
        if wx.Platform == '__WXMAC__':
            # turn off the automatic generation of the Window menu.
            # We generate one ourselves
            wx.MenuBar.SetAutoWindowMenu(False)
            # Replace the system Help menu with ours by creating this small
            # fake menu in order to register the help menu.  Note that you
            # have to add something to the menubar on the mac (i.e.  the
            # separator) in order for it to actually register with the Mac
            # menu system as being present.  An empty Help menu is ignored as
            # far as SetMacHelpMenuTitleName is concerned.
            help = wx.Menu()
            help.AppendSeparator()
            menubar.Append(help, _("&Help"))
            wx.GetApp().SetMacHelpMenuTitleName(_("&Help"))
        self.SetMenuBar(menubar)
        
        self.show_toolbar = self.classprefs.show_toolbar
        self.root_accel = Null()

    def initEventBindings(self):
        self.dropTarget=FrameDropTarget(self)
        self.SetDropTarget(self.dropTarget)        
        
        Publisher().subscribe(self.pluginsChanged, 'peppy.plugins.changed')
        wx.GetApp().SetTopWindow(self)
        self.bindEvents()
        
    def initLoad(self, buffer, urls):
        if buffer:
            self.newBuffer(buffer)
        else:
            self.loadList(urls)
    
    def initRegisterWindow(self):
        WindowList.append(self)

    def __str__(self):
        return "%s %s id=%s" % (self.__class__.__name__, self.name, hex(id(self)))
    
    def isOSXMinimalMenuFrame(self):
        return False
        
    def bindEvents(self):
        self.Bind(wx.EVT_CLOSE,self.OnClose)
        self.Bind(wx.EVT_ACTIVATE, self.OnRaise)
        self.Bind(wx.EVT_SIZE, self.OnSize)

    def unbindEvents(self):
        self.Unbind(wx.EVT_CLOSE)
        self.Unbind(wx.EVT_ACTIVATE)
        self.Unbind(wx.EVT_SIZE)

    def loadList(self, urls):
        if urls:
            for url in urls:
                #dprint("Opening %s" % url)
                wx.CallAfter(self.open, url, force_new_tab=True)
        else:
            wx.CallAfter(self.titleBuffer)
        
    def addPane(self, win, paneinfo):
        self._mgr.AddPane(win, paneinfo)

    def loadSidebars(self):
        sidebars = Sidebar.getClasses(self)
        for sidebarcls in sidebars:
            if sidebarcls.classprefs.springtab:
                self.spring.addTab(sidebarcls.caption, sidebarcls)
            else:
                self.createSidebar(sidebarcls)
        self.createSidebarList()

    def createSidebar(self, sidebarcls):
        """Create the sidebar and register it with the frame's AUI
        Manager."""

        sidebar = sidebarcls(self)
        paneinfo = sidebar.getPaneInfo()
        self._mgr.AddPane(sidebar, paneinfo)
        sidebar.paneinfo = self._mgr.GetPane(sidebar)

    def createSidebarList(self):
        self.sidebar_panes = []
        sidebars = self._mgr.GetAllPanes()
        for sidebar in sidebars:
            assert self.dprint("name=%s caption=%s window=%s state=%s" % (sidebar.name, sidebar.caption, sidebar.window, sidebar.state))
            if sidebar.name != "notebook":
                self.sidebar_panes.append(sidebar)
        self.sidebar_panes.sort(key=lambda s:s.caption)

    def processIdleEvent(self):
        mode = self.getActiveMajorMode()
        if mode and mode.isReadyForIdleEvents():
            #dprint("Idle for mode %s" % mode)
            mode.idleHandler()
            
            # Refs #665: this call to forceToolbarUpdate causes the yield to
            # freeze until tabs get switched.  Now this only happens when the
            # mode is ready for idle event processing
            self.root_accel.forceToolbarUpdate()
            
            # Timestamp checks are performed here for two reasons: 1) windows
            # reports activate events whenever a dialog is popped up, so
            # you get an unending stream of dialogs.  2) when trying to use
            # dialogs after changing tabs on linux, the mouse events seemed to
            # get eaten.  The only workaround I could find was to put the call
            # to isModeChangedOnDisk here wrapped by a CallAfter.
            if self.pending_timestamp_check and not self.currently_processing_timestamp:
                self.currently_processing_timestamp = True
                wx.CallAfter(self.isModeChangedOnDisk)
                self.pending_timestamp_check = False
        #else:
        #    dprint("mode %s not ready for idle events" % mode)

    # Overrides of wx methods
    def OnRaise(self, evt):
        self.dprint("Focus! %s" % self.name)
        if evt.GetActive():
            wx.GetApp().SetTopWindow(self)
            if not self.pending_timestamp_check and not self.currently_processing_timestamp:
                self.pending_timestamp_check = True
        evt.Skip()
    
    def OnSize(self, evt):
        # FIXME: this fast resizing was causing problems, so I've disabled it
        # with the embedded False
        if False and self.classprefs.fast_resize:
            if not self.tabs.IsFrozen():
                dprint("not frozen.  Freezing")
                self.tabs.Freeze()
            if not self.__class__.size_timer:
                self.__class__.size_timer = wx.PyTimer(self.OnSizeTimer)
            self.__class__.size_timer.Start(50, oneShot=True)
        else:
            self.rememberFrameSize()
            evt.Skip()
    
    def rememberFrameSize(self):
        if self.classprefs.resize_becomes_default:
            size = self.GetSize()
            self.classprefs.width = size.GetWidth()
            self.classprefs.height = size.GetHeight()

    def OnSizeTimer(self, evt=None):
        if self.tabs.IsFrozen():
            dprint("frozen.  Thawing")
            # FIXME: for some reason, IsFrozen returns True even when it's
            # not frozen.
            self.tabs.Thaw()

    def OnClose(self, evt=None):
        assert self.dprint(evt)
        if WindowList.canCloseWindow(self):
            self.closeWindow()

    def Raise(self):
        wx.Frame.Raise(self)
        major=self.getActiveMajorMode()
        if major is not None:
            major.SetFocus()
        
    def SetStatusText(self, text, index=0):
        mode = self.getActiveMajorMode()
        if mode is not None:
            mode.status_info.setText(text, index)
    
    # non-wx methods
    
    def showErrorDialog(self, msg, title="Error"):
        dlg = wx.MessageDialog(self, msg, title, wx.OK | wx.ICON_ERROR )
        retval = dlg.ShowModal()
        return retval
    
    def showWarningDialog(self, msg, title="Warning"):
        dlg = wx.MessageDialog(self, msg, title, wx.OK | wx.ICON_WARNING )
        retval = dlg.ShowModal()
        return retval
    
    def showQuestionDialog(self, msg, title="Question"):
        dlg = wx.MessageDialog(self, msg, title, wx.YES_NO | wx.ICON_QUESTION )
        retval = dlg.ShowModal()
        return retval
    
    def clearMenumap(self):
        self.root_accel.cleanupAndDelete()

    def setMenumap(self, mode):
        self.clearMenumap()
        self.root_accel = UserAccelerators(self, mode)
        #storeWeakref('menumap', self.menumap)
        
        self.root_accel.updateActions(self.show_toolbar)
        self._mgr.Update()
    
    def updateMenumap(self):
        self.root_accel.forceToolbarUpdate()

    def getActiveMajorMode(self):
        wrapper = self.tabs.getCurrent()
        if wrapper:
            major=self.tabs.getCurrent().editwin
            return major
        return None

    def getAllMajorModes(self):
        modes = self.tabs.getAll()
        return modes
    
    def isOpen(self):
        major=self.getActiveMajorMode()
            #assert self.dprint("major=%s isOpen=%s" % (str(major),str(major!=None)))
        return major is not None

    def isTopWindow(self):
        return wx.GetApp().GetTopWindow()==self
    
    def closeWindow(self):
        self.unbindEvents()
        self.clearMenumap()
        WindowList.remove(self)
        self.Hide()
        self.tabs.closeAllTabs()
        self.Destroy()

    @classmethod
    def closeAllWindows(cls):
        frames = WindowList.getFrames()
        for frame in frames:
            frame.closeWindow()
    
    def closeBuffer(self):
        major=self.getActiveMajorMode()
        if major:
            buffer=major.buffer
            if buffer.permanent:
                self.tabs.closeWrapper(major)
            else:
                if buffer.modified:
                    dlg = wx.MessageDialog(self, "%s\n\nhas unsaved changes.\n\nClose anyway?" % buffer.displayname, "Unsaved Changes", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION )
                    retval=dlg.ShowModal()
                    dlg.Destroy()
                else:
                    retval=wx.ID_YES

                if retval==wx.ID_YES:
                    if buffer.numViewers() > 1:
                        dlg = wx.MessageDialog(self, u"Multiple views of:\n\n%s\n\nexist.  Really remove buffer?" % buffer.url, "Remove All Views?", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION )
                        retval=dlg.ShowModal()
                        dlg.Destroy()
                    else:
                        retval=wx.ID_YES
                        
                    if retval==wx.ID_YES:
                        buffer.removeAllViewsAndDelete()
    
    def setTitle(self):
        self.SetTitle(self.getTitle())

    def getTitle(self):
        major = self.getActiveMajorMode()
        if major:
            return u"peppy: %s" % major.getTabName()
        return self.name
    
    def showModified(self, major):
        current=self.getActiveMajorMode()
        if current:
            self.setTitle()
            self.tabs.updateWrapperTitle(major)

    def titleBuffer(self):
        self.open(wx.GetApp().classprefs.title_page)

    def isTitleBufferOnly(self):
        if len(self.getAllMajorModes()) > 1:
            return False
        mode = self.getActiveMajorMode()
        url = vfs.normalize(wx.GetApp().classprefs.title_page)
        dprint(u"%s == %s => %s" % (url, mode.buffer.url, mode.buffer.url == url))
        if mode.buffer.url == url:
            return True
        return False

    def setBuffer(self, buffer, wrapper=None, use_current=None, options=None):
        if wrapper is None:
            if use_current:
                wrapper = self.tabs.getCurrent()
            else:
                # this gets a default view for the selected buffer
                wrapper = self.tabs.getDocumentWrapper()
        mode = self.tabs.newMode(buffer, wrapper=wrapper)
        assert self.dprint("set buffer to new view %s" % mode)
        if not mode.isErrorMode():
            mode.showInitialPosition(buffer.raw_url, options)
        mode.setReadyForIdleEvents()

    def newBuffer(self, buffer):
        # proxy it up to tabs
        self.tabs.newBuffer(buffer.url, buffer)
    
    def changeMajorMode(self, requested):
        """Change the currently active major mode to the requested mode
        
        This changes the view of the current buffer to the new mode, but
        doesn't change any of the data in the buffer.
        """
        mode = self.getActiveMajorMode()
        cursor_data = mode.getViewPositionData()
        newmode = self.tabs.newMode(mode.buffer, requested, mode)
        if not newmode.isErrorMode():
            newmode.setViewPositionData(cursor_data)
        newmode.setReadyForIdleEvents()

    def makeTabActive(self, url):
        """Make the tab current that corresponds to the url.
        
        If the url isn't found, nothing happens.
        
        @return: True if URL was found, False if not.
        """
        normalized = vfs.normalize(url)
        self.dprint("url=%s normalized=%s" % (url, normalized))
        mode = self.tabs.moveSelectionToURL(normalized)
        if mode:
            mode.showInitialPosition(normalized)
        return mode is not None
    
    def findTabOrOpen(self, url):
        """Find a tab that contains this URL, otherwise open a new tab"""
        if not self.makeTabActive(url):
            self.open(url)

    def open(self, *args, **kwargs):
        """Open a new tab to edit the given URL.
        
        Driver function that uses L{FileOpener} to open URLs
        """
        try:
            opener = FileOpener(self, *args, **kwargs)
            opener.open()
        except FileOpenerExceptionHandled:
            pass

    def save(self):        
        mode=self.getActiveMajorMode()
        if mode and mode.buffer:
            mode.buffer.save()

    def cwd(self, use_vfs=False):
        """Get working filesystem directory for current mode.

        Convenience function to get working directory of the current
        mode.
        """
        mode = self.getActiveMajorMode()
        if mode and mode.buffer:
            cwd = mode.buffer.cwd(use_vfs)
        else:
            cwd = unicode(os.getcwd())
        return cwd
    
    def isModeChangedOnDisk(self):
        """Convenience function to ask user what to if the file has been changed
        out from under us by an external program.
        """
        self.currently_processing_timestamp = True
        try:
            major = self.getActiveMajorMode()
            if major:
                major.checkFileModified()
        finally:
            self.currently_processing_timestamp = False

    def switchMode(self, set_focus=True):
        """Update the user interface to reflect the current mode.
        
        This changes the menu bar, tool bar, status bar, and keystroke commands
        to reflect the currently active major mode.  Can also be used to
        update the existing major mode if actions were added to the major mode
        in response to some user action.
        
        @param set_focus: should the major mode take the focus.  There is a
        problem if this method is used to loop through and update all frames:
        the focus seems to be stolen by the first mode in the loop regardless
        of which mode is in the top frame (see bug #492).  When using this
        method in a loop, set_focus should be false.
        """
        start = time.time()
        self.dprint("starting switchMode at 0.00000s")
        last=self.tabs.getPrevious()
        if last:
            last.clearPopups()
            last = last.editwin
        mode=self.getActiveMajorMode()
        if mode is None:
            assert self.dprint("No currently active mode for %s" % (self))
            # If there were multiple tabs open and they were all the
            # same, they will go away when the buffer is closed.  In
            # this case, don't try to do anything more because there
            # isn't a mode that's left associated with this frame
            return

        assert self.dprint("Switching from mode %s to mode %s" % (last,mode))
        self.dprint("found active mode at %0.5fs" % (time.time() - start))

        self.spring.clearRadio()
        self.dprint("springtabs cleared at %0.5fs" % (time.time() - start))

        if set_focus:
            mode.focus()
        self.setTitle()
        self.dprint("title set at %0.5fs" % (time.time() - start))
        #self.setKeys(majors)
        self.setMenumap(mode)
        self.dprint("menu created at %0.5fs" % (time.time() - start))
        self.GetStatusBar().changeInfo(mode.status_info)
        self.dprint("status bar updated at %0.5fs" % (time.time() - start))

##        if mode.buffer.filename in BufferFrame.perspectives:
##            self._mgr.LoadPerspective(BufferFrame.perspectives[mode.buffer.filename])
##            assert self.dprint(BufferFrame.perspectives[mode.buffer.filename])
##        else:
##            if 'default perspective' in self.tempsettings:
##                # This doesn't exactly work because anything not named in
##                # the default perspective listing won't be shown.  Need to
##                # find a way to determine which panes are new and show
##                # them.
##                self._mgr.LoadPerspective(self.tempsettings['default perspective'])
##                all_panes = self._mgr.GetAllPanes()
##                for pane in xrange(len(all_panes)):
##                    all_panes[pane].Show()
##            else:
##                self.tempsettings['default perspective'] = self._mgr.SavePerspective()
        
        # "commit" all changes made to FrameManager   
        self._mgr.Update()
        self.dprint("switchMode completed at %0.5fs" % (time.time() - start))
        
        # NOTE: using wx.CallAfter(self.isModeChangedOnDisk) here seems to do
        # something bad to the mouse pointer, because after calling this no
        # more mouse events are received by the application.  Instead, I have
        # to set a flag and process in the idle event handler.
        self.pending_timestamp_check = True

    def getAllModes(self):
        modes = []
        for index in range(self.tabs.GetPageCount()):
            page = self.tabs.GetPage(index).editwin
            modes.append(page.__class__)
        return modes

    def pluginsChanged(self, msg):
        """Update the display after plugins changed, because it might
        affect the menu or toolbar if new plugins were activated or
        existing ones were deactivated.
        """
        # FIXME: check to make sure that any major modes currently in
        # use haven't been deactivated.  If so, force them to be
        # enabled again.  Or, perhaps check before disabling.

        # FIXME: what to do in the case of a classpref changing that
        # affects an attribute?  E.g. if classpref.show_toolbar
        # changes, should self.show_toolbar also change?  Or, prompt
        # the user to say "global setting <blah> has changed.  Update
        # all instances?"
        self.switchMode()

    def showSaveAs(self, title, default_name=None, extra=None, wildcard="*.*"):
        """Show a save as dialog relative to the currently active major mode.
        
        Displays a save as dialog and returns the chosen filename.  The
        dialog's initial directory will be current working directory of the
        active major mode.
        
        @param title: string to display in the window title bar
        
        @param extra: extra suffix to append to the default filename
        
        @return: filename of desired file, or None if cancelled.
        """
        mode = self.getActiveMajorMode()
        cwd = self.cwd()
        if default_name:
            saveas = default_name
        else:
            saveas = mode.buffer.getFilename()
            saveas = os.path.basename(saveas)
        if extra and not saveas.endswith(extra):
            saveas += extra
        assert self.dprint("cwd = %s, file = %s" % (cwd, saveas))

        dlg = wx.FileDialog(
            self, message=title, defaultDir=cwd, 
            defaultFile=saveas, wildcard=wildcard,
            style=wx.SAVE| wx.CHANGE_DIR | wx.OVERWRITE_PROMPT)

        # FIXME: bug in linux: setting defaultFile to some
        # non-blank string causes directory to be set to
        # current working directory.  If defaultFile == "",
        # working directory is set to the specified
        # defaultDir.           
        dlg.SetDirectory(cwd)
        
        retval = dlg.ShowModal()
        if retval == wx.ID_OK:
            # This returns a Python list of files that were selected.
            paths = dlg.GetPaths()
            if len(paths) > 0:
                saveas = paths[0]
                assert self.dprint("save file %s:" % saveas)
            elif paths!=None:
                raise IndexError("BUG: probably shouldn't happen: len(paths)!=1 (%s)" % str(paths))
        else:
            saveas = None

        dlg.Destroy()
        return saveas
