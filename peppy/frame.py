# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os, re, threading
from cStringIO import StringIO

import wx
import wx.aui
import wx.stc
from wx.lib.pubsub import Publisher

import peppy.vfs as vfs

from peppy.actions import *
from peppy.menu import *
from peppy.lib.wxemacskeybindings import *
from peppy.lib.iconstorage import *
from peppy.lib.controls import *
from peppy.lib.userparams import *

from peppy.configprefs import *
from peppy.stcbase import *
from peppy.major import *
from peppy.sidebar import *
from peppy.debug import *
from peppy.buffers import *

    
class WindowList(OnDemandGlobalListAction):
    name="Frames"
    default_menu = ("Window", -100)
    inline = True
    
    # provide storage to be shared among instances
    storage = []
    
    @classmethod
    def calcHash(cls):
        cls.globalhash = None
    
    @classmethod
    def getFrames(self):
        return [frame for frame in WindowList.storage]
    
    def getItems(self):
        return [frame.getTitle() for frame in WindowList.storage]

    def action(self, index=0, multiplier=1):
        assert self.dprint("top window to %d: %s" % (index,WindowList.storage[index]))
        wx.GetApp().SetTopWindow(WindowList.storage[index])
        wx.CallAfter(WindowList.storage[index].Raise)

class DeleteWindow(SelectAction):
    alias = "delete-window"
    name = "&Delete Window"
    default_menu = ("Window", 1)
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
    default_menu = ("Window", 0)
    key_bindings = {'emacs': "C-X 5 2",}
    
    def action(self, index=-1, multiplier=1):
        frame=BufferFrame()
        frame.Show(True)


class MyNotebook(wx.aui.AuiNotebook, debugmixin):
    def __init__(self, parent, size=wx.DefaultSize):
        wx.aui.AuiNotebook.__init__(self, parent, size=size, style=wx.aui.AUI_NB_WINDOWLIST_BUTTON|wx.aui.AUI_NB_TAB_MOVE|wx.aui.AUI_NB_TAB_SPLIT|wx.aui.AUI_NB_CLOSE_BUTTON|wx.aui.AUI_NB_SCROLL_BUTTONS, pos=(9000,9000))
        
        self.frame=parent
        self.lastActivePage=None
        self.context_tab = -1 # which tab is currently displaying a context menu?
        
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.OnTabChanged)
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.OnTabClosed)
        if 'EVT_AUINOTEBOOK_TAB_RIGHT_DOWN' in dir(wx.aui):
            # This event was only added as of wx 2.8.7.1, so ignore it on
            # earlier releases
            self.Bind(wx.aui.EVT_AUINOTEBOOK_TAB_RIGHT_DOWN, self.OnTabContextMenu)

    def OnTabChanged(self, evt):
        newpage = evt.GetSelection()
        oldpage = evt.GetOldSelection()
        assert self.dprint("changing from tab %s to %s" % (oldpage, newpage))
        if oldpage>0:
            self.lastActivePage=self.GetPage(oldpage)
        else:
            self.lastActivePage=None
        page=self.GetPage(newpage)
        wx.CallAfter(self.frame.switchMode)
        evt.Skip()

    def removeWrapper(self, index, in_callback=False):
        wrapper = self.GetPage(index)
        assert self.dprint("closing tab # %d: mode %s" % (index, wrapper.editwin))
        wrapper.deleteMajorMode()
        if not in_callback:
            self.RemovePage(index)
            wrapper.Destroy()

    def OnTabClosed(self, evt):
        index = evt.GetSelection()
        self.removeWrapper(index, in_callback=True)
        if self.GetPageCount() == 1:
            wx.CallAfter(self.frame.open, "about:blank")
        evt.Skip()

    def closeTab(self, index=None):
        if index == None:
            index = self.context_tab
        if index >= 0:
            self.removeWrapper(index)
            if self.GetPageCount() == 0:
                wx.CallAfter(self.frame.open, "about:blank")

    def OnTabContextMenu(self, evt):
        dprint("Context menu over tab %d" % evt.GetSelection())
        action_classes = []
        Publisher().sendMessage('tabs.context_menu', action_classes)
        dprint(action_classes)
        self.context_tab = evt.GetSelection()
        if action_classes:
            self.frame.menumap.popupActions(self, action_classes)
        self.context_tab = -1
        #evt.Skip()

    def getContextMenuWrapper(self):
        if self.context_tab >= 0:
            return self.GetPage(self.context_tab)
        raise IndexError("Not currently processing a popup!")

    def closeAllTabs(self):
        for index in range(0, self.GetPageCount()):
            self.removeWrapper(0)
    
    def moveSelectionLeft(self):
        """Change the selection to the tab to the left of the currently
        selected tab.
        """
        # FIXME: if the tab order is changed by dragging tabs around, the
        # order doesn't seem to be reflected in the index.  It looks like the
        # index of a tab is tied to the order in which it was created, and no
        # matter how the tabs a physically rearranged on screen, the tab order
        # is constant.
        index = self.GetSelection()
        if index > 0:
            index -= 1
            self.SetSelection(index)
    
    def moveSelectionRight(self):
        """Change the selection to the tab to the right of the currently
        selected tab.
        """
        # FIXME: see moveSelectionLeft
        index = self.GetSelection()
        if index < self.GetPageCount() - 1:
            index += 1
            self.SetSelection(index)
    
    def moveSelectionToURL(self, url):
        """Change the selection to the tab containing the given URL
        
        @return: major mode if found, or None
        """
        for index in range(0, self.GetPageCount()):
            mode = self.GetPage(index).editwin
            if mode.buffer.isURL(url):
                self.SetSelection(index)
                mode.focus()
                return mode
        return None
    
    def getCurrent(self):
        index = self.GetSelection()
        if index<0:
            return None
        return self.GetPage(index)

    def getPrevious(self):
        return self.lastActivePage

    def updateTitle(self,mode):
        index=self.GetPageIndex(mode)
        if index>=0:
            self.SetPageText(index,mode.getTabName())

    def getAll(self):
        pages = []
        for index in range(0, self.GetPageCount()):
            pages.append(self.GetPage(index))
        return pages
    
    ##### New methods for MajorModeWrapper support
    def getCurrentMode(self):
        wrapper = self.getCurrent()
        if wrapper:
            return wrapper.editwin

    def getWrapper(self, mode):
        for index in range(0, self.GetPageCount()):
            if self.GetPage(index).editwin == mode:
                return self.GetPage(index)
        raise IndexError("No tab found for mode %s" % mode)
    
    def updateWrapper(self, wrapper):
        index=self.GetPageIndex(wrapper)
        if index>=0:
            self.SetPageText(index, wrapper.getTabName())
            self.SetPageBitmap(index, wrapper.getTabBitmap())
            if wrapper == self.getCurrent():
                self.frame.switchMode()
            else:
                self.SetSelection(index)
            wrapper.editwin.tabActivatedHook()

    def updateWrapperTitle(self, mode):
        for index in range(0, self.GetPageCount()):
            page = self.GetPage(index)
            if page.editwin == mode:
                self.SetPageText(index, page.getTabName())
                break
    
    def newWrapper(self):
        page = MajorModeWrapper(self)
        self.AddPage(page, page.getTabName(), bitmap=page.getTabBitmap())
        index = self.GetPageIndex(page)
        self.SetSelection(index)
        return page
    
    def closeWrapper(self, mode):
        if self.GetPageCount() > 1:
            for index in range(0, self.GetPageCount()):
                wrapper = self.GetPage(index)
                if wrapper.editwin == mode:
                    wrapper.deleteMajorMode()
                    self.RemovePage(index)
                    wrapper.Destroy()
                    break
        else:
            page = self.GetPage(0)
            page.deleteMajorMode()
            buffer = BufferList.findBufferByURL("about:blank")
            page.createMajorMode(self.frame, buffer)
            self.updateWrapper(page)

    def getNewModeWrapper(self, new_tab=False):
        current = self.getCurrentMode()
        if current and not new_tab and (not wx.GetApp().tabs.useNewTabForNewFile(current)):
            wrapper = self.getCurrent()
        else:
            wrapper = self.newWrapper()
        return wrapper

    def getDocumentWrapper(self):
        current = self.getCurrentMode()
        if current and not wx.GetApp().tabs.useNewTabForDocument(current):
            wrapper = self.getCurrent()
        else:
            wrapper = self.newWrapper()
        return wrapper

    def newBuffer(self, user_url, buffer, modecls=None, mode_to_replace=None, new_tab=False):
        if mode_to_replace:
            wrapper = self.getWrapper(mode_to_replace)
        else:
            wrapper = self.getNewModeWrapper(new_tab=new_tab)
        mode = wrapper.createMajorMode(self.frame, buffer, modecls)
        assert self.dprint("major mode=%s" % mode)
        self.updateWrapper(wrapper)
        mode.showInitialPosition(user_url)

    def newMode(self, buffer, mode_to_replace=None):
        assert self.dprint("mode=%s replace=%s" % (buffer, mode_to_replace))
        if mode_to_replace:
            wrapper = self.getWrapper(mode_to_replace)
        else:
            wrapper = self.getNewModeWrapper()
        try:
            mode = wrapper.createMajorMode(self.frame, buffer)
        except MajorModeLoadError, error:
            buffer = Buffer.createErrorBuffer(buffer.url, error)
            mode = wrapper.createMajorMode(self.frame, buffer)
        except:
            import traceback
            error = traceback.format_exc()
            try:
                buffer = Buffer.createErrorBuffer(buffer.url, error)
                mode = wrapper.createMajorMode(self.frame, buffer)
            except:
                dprint(error)
        self.updateWrapper(wrapper)
        return mode


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
    
    perspectives={}

    default_classprefs = (
        IntParam('width', 800, 'Width of the main frame in pixels'),
        IntParam('height', 600, 'Height of the main frame in pixels'),
        StrParam('sidebars', '', 'List of sidebars to activate with the frame', fullwidth=True),
        BoolParam('show_toolbar', True, 'Show the toolbar on all frames?\nNote: this is a global setting for all frames.'),
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

        size=(int(self.classprefs.width),int(self.classprefs.height))
        wx.Frame.__init__(self, None, id=-1, title=self.name, pos=wx.DefaultPosition, size=size, style=wx.DEFAULT_FRAME_STYLE|wx.CLIP_CHILDREN)
        icon = wx.EmptyIcon()
        icon.CopyFromBitmap(getIconBitmap('icons/peppy.png'))
        self.SetIcon(icon)

        WindowList.append(self)
        
        ModularStatusBar(self)

        # tell FrameManager to manage this frame        
        self._mgr = wx.aui.AuiManager()
        self._mgr.SetManagedWindow(self)

        self.tabs = MyNotebook(self)
        self._mgr.AddPane(self.tabs, wx.aui.AuiPaneInfo().Name("notebook").
                          CenterPane())
        self.sidebar_panes = []

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
        
        self.menumap=None
        self.show_toolbar = self.classprefs.show_toolbar
        
        self.keys=KeyProcessor(self)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)

        self.loadSidebars()

        self.dropTarget=FrameDropTarget(self)
        self.SetDropTarget(self.dropTarget)        
        
        Publisher().subscribe(self.pluginsChanged, 'peppy.plugins.changed')
        wx.GetApp().SetTopWindow(self)
        self.bindEvents()
        
        #dprint(urls)
        
        # counter to make sure the title buffer is shown if we attempt
        # to load files and they all fail.
        self.initial_load = 0
        if buffer:
            self.newBuffer(buffer)
        else:
            self.loadList(urls)
        self.Show()
        
    def bindEvents(self):
        self.Bind(wx.EVT_CLOSE,self.OnClose)
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.Bind(wx.EVT_ACTIVATE, self.OnRaise)
        self.Bind(wx.EVT_SIZE, self.OnSize)

    def unbindEvents(self):
        self.Unbind(wx.EVT_CLOSE)
        self.Unbind(wx.EVT_IDLE)
        self.Unbind(wx.EVT_ACTIVATE)
        self.Unbind(wx.EVT_SIZE)

    def loadList(self, urls):
        if urls:
            for url in urls:
                #dprint("Opening %s" % url)
                wx.CallAfter(self.open, url, force_new_tab=True)
                self.initial_load += 1
        else:
            wx.CallAfter(self.titleBuffer)
        
    def addPane(self, win, paneinfo):
        self._mgr.AddPane(win, paneinfo)

    def loadSidebars(self):
        sidebar_list = self.classprefs.sidebars
        assert self.dprint(sidebar_list)
        if sidebar_list is not None:
            sidebar_names = [s.strip() for s in sidebar_list.split(',')]
            assert self.dprint("loading %s" % sidebar_names)
            sidebars = Sidebar.getClasses(self,sidebar_names)
            for sidebarcls in sidebars:
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


    # Overrides of wx methods
    def OnIdle(self, evt):
        if wx.GetApp().GetTopWindow() != self:
            self.dprint("idle events only on top window: top=%s self=%s" % (wx.GetApp().GetTopWindow(), self.name))
            pass
        else:
            mode = self.getActiveMajorMode()
            mode.idleHandler()
            
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
        evt.Skip()
        
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
            evt.Skip()

    def OnSizeTimer(self, evt=None):
        if self.tabs.IsFrozen():
            dprint("frozen.  Thawing")
            # FIXME: for some reason, IsFrozen returns True even when it's
            # not frozen.
            self.tabs.Thaw()

    def OnClose(self, evt=None):
        assert self.dprint(evt)
        close = True
        if len(WindowList.storage)==1:
            # If attempting to close the last window, check to make sure that
            # the user didn't cancel the quit
            close = wx.GetApp().quit()
        if close:
            self.closeWindow()

    def OnKeyDown(self, evt):
        self.keys.process(evt)
##        if function:
##            print "num=%d function=%s" % (num,function)
##        else:
##            print "unprocessed by KeyProcessor"

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
    
    def setKeys(self,majormodes=[],minormodes=[]):
##        keymap=UserInterfaceLoader.loadKeys(self,majormodes,minormodes)
##        self.keys.setGlobalKeyMap(keymap)
##        self.keys.clearMinorKeyMaps()
        pass
    
    def clearMenumap(self):
        if self.menumap is not None:
            self.menumap.cleanupAndDelete()
            self.menumap = None
            #printWeakrefs('menumap')

    def setMenumap(self, mode):
        self.clearMenumap()
        self.menumap = UserActionMap(self, mode)
        #storeWeakref('menumap', self.menumap)
        
        keymap = self.menumap.updateActions(self.show_toolbar)
        self.keys.setGlobalKeyMap(keymap)
        self._mgr.Update()
    
    def updateMenumap(self):
        self.menumap.forceToolbarUpdate()

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
                wx.GetApp().close(buffer)
    
    def setTitle(self):
        major=self.getActiveMajorMode()
        if major:
            self.SetTitle(u"peppy: %s" % major.getTabName())
        else:
            self.SetTitle(u"peppy")

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
        dprint(u"%s == %s => %s" % (unicode(url), unicode(mode.buffer.url), mode.buffer.url == url))
        if mode.buffer.url == url:
            return True
        return False

    def setBuffer(self, buffer, wrapper=None):
        if wrapper is None:
            # this gets a default view for the selected buffer
            wrapper = self.tabs.getDocumentWrapper()
        mode = wrapper.createMajorMode(self, buffer)
        assert self.dprint("set buffer to new view %s" % mode)
        self.tabs.updateWrapper(wrapper)
    
    def newBuffer(self, buffer):
        # proxy it up to tabs
        self.tabs.newBuffer(buffer.url, buffer)
    
    def changeMajorMode(self, requested):
        wrapper = self.tabs.getCurrent()
        cursor_data = wrapper.editwin.getViewPositionData()
        newmode = wrapper.createMajorMode(self, wrapper.editwin.buffer, requested)
        assert self.dprint("new mode=%s" % newmode)
        newmode.setViewPositionData(cursor_data)
        self.tabs.updateWrapper(wrapper)

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

    def open(self, url, modecls=None, mode_to_replace=None, force_new_tab=False, created_from_url=None):
        """Open a new tab to edit the given URL.
        
        Driver function that loads a file and creates a new tab in the user
        interface.  Depending on settings, the file may be loaded by a thread.
        
        @param url: URL of the file to open
        
        @param modecls: (optional) L{MajorMode} sublass to be used to edit
        the file
        
        @param mode_to_replace: (optional) if used, this L{MajorMode} instance
        will be replaced in the GUI with the newly created major mode.
        
        @param force_new_tab: (optional) force a new tab to be reused,
        regardless of preference settings that would otherwise cause a tab to
        be replaced.
        
        @param create_from_url: (optional) the URL of the buffer that was
        used to generate this URL.  This is not typically used unless you're
        creating a new file in the mem: filesystem and want a working directory
        on the local filesystem to be available if needed to save a copy.
        """
        # The canonical url stored in the buffer will be without query string
        # or fragment, so we need to keep track of the full url (with the
        # query string and fragment) it separately.
        user_url = vfs.normalize(url)
        try:
            buffer = BufferList.findBufferByURL(user_url)
        except NotImplementedError:
            # This means that the vfs implementation doesn't recognize the
            # filesystem type.  This is the first place in the loading chain
            # that the error can be encountered, so check for it here and load
            # a new plugin if necessary.
            found = False
            plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
            for plugin in plugins:
                assert self.dprint("Checking %s" % plugin)
                plugin.loadVirtualFileSystem(user_url)
                try:
                    buffer = BufferList.findBufferByURL(user_url)
                    found = True
                    break
                except NotImplementedError:
                    pass
            if not found:
                self.openFailure(user_url, "Unknown URI scheme")
                return

        if buffer is not None:
            #dprint("found permanent buffer %s, new_tab=%s" % (unicode(url), force_new_tab))
            self.tabs.newBuffer(user_url, buffer, modecls, mode_to_replace, force_new_tab)
        else:
            try:
                buffer = LoadingBuffer(user_url, modecls, created_from_url)
            except Exception, e:
                import traceback
                error = traceback.format_exc()
                self.openFailure(user_url, error)
                return
            
            if wx.GetApp().classprefs.load_threaded and buffer.allowThreadedLoading():
                self.tabs.newBuffer(user_url, buffer, mode_to_replace=mode_to_replace, new_tab=force_new_tab)
            else:
                self.openNonThreaded(user_url, buffer, mode_to_replace, force_new_tab=force_new_tab)
    
    def openNonThreaded(self, user_url, loading_buffer, mode_to_replace=None, force_new_tab=False):
        #traceon()
        wx.SetCursor(wx.StockCursor(wx.CURSOR_WATCH))
        try:
            buffer = loading_buffer.clone()
            buffer.openGUIThreadStart()
            buffer.openBackgroundThread()
            if force_new_tab:
                mode_to_replace = None
            self.openSuccess(user_url, buffer, mode_to_replace)
        except Exception, e:
            import traceback
            error = traceback.format_exc()
            self.openFailure(user_url, error)
        wx.SetCursor(wx.StockCursor(wx.CURSOR_DEFAULT))

    def openThreaded(self, user_url, loading_buffer, mode_to_replace=None):
        #traceon()
        buffer = loading_buffer.clone()
        buffer.openGUIThreadStart()
        statusbar = mode_to_replace.status_info
        statusbar.startProgress(u"Loading %s" % user_url, message=str(mode_to_replace))
        thread = BufferLoadThread(self, user_url, buffer, mode_to_replace, statusbar)
        wx.GetApp().cooperativeYield()
        thread.start()

    def openSuccess(self, user_url, buffer, mode_to_replace=None, progress=None):
        try:
            buffer.openGUIThreadSuccess()
            assert self.dprint("buffer=%s" % buffer)
        except:
            import traceback
            error = traceback.format_exc()
            self.openFailure(user_url, error, mode_to_replace, progress)
            return
        
        if progress:
            progress.stopProgress("Parsing...")
            wx.GetApp().cooperativeYield()

        assert self.dprint("mode to replace = %s" % mode_to_replace)
        mode = self.tabs.newMode(buffer, mode_to_replace)
        assert self.dprint("major mode=%s" % mode)
        
        #raceoff()
        assert self.dprint("after addViewer")
        msg = mode.getWelcomeMessage()
        mode.status_info.setText(msg)
        mode.showInitialPosition(user_url)

    def openFailure(self, url, error, mode_to_replace=None, progress=None):
        #traceoff()
        msg = "Failed opening %s.\n" % unicode(url)
        buffer = Buffer.createErrorBuffer(url, error)
        mode = self.tabs.newMode(buffer, mode_to_replace)
        assert self.dprint("major mode=%s" % mode)
        if progress:
            progress.stopProgress(msg)
        else:
            mode.status_info.setText(msg)

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

    def switchMode(self):
        last=self.tabs.getPrevious()
        if last:
            last = last.editwin
        mode=self.getActiveMajorMode()
        if mode is None:
            # If there were multiple tabs open and they were all the
            # same, they will go away when the buffer is closed.  In
            # this case, don't try to do anything more because there
            # isn't a mode that's left associated with this frame
            return

        assert self.dprint("Switching from mode %s to mode %s" % (last,mode))

        mode.focus()
        self.setTitle()
        #self.setKeys(majors)
        self.setMenumap(mode)
        self.GetStatusBar().changeInfo(mode.status_info)

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

    def getTitle(self):
        mode = self.getActiveMajorMode()
        if mode:
            return "peppy: %s" % mode.buffer.getTabName()
        return self.name
    
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
