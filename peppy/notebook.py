# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""

"""

import os

import wx
from wx.lib.pubsub import Publisher
import peppy.third_party.aui as aui
from peppy.third_party.pubsub import pub

from peppy.debug import *
from peppy.major import *
from peppy.buffers import Buffer, BufferList
from peppy.menu import PopupMenu


class FrameNotebook(aui.AuiNotebook, debugmixin):
    def __init__(self, parent, size=wx.DefaultSize):
        style = self.getStyle()
        aui.AuiNotebook.__init__(self, parent, size=size, agwStyle=style, pos=(9000,9000))
        
        self.frame = parent
        self.lastActivePage=None
        self.context_tab = -1 # which tab is currently displaying a context menu?
        
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.OnTabChanged)
        self.Bind(aui.EVT_AUINOTEBOOK_PAGE_CLOSE, self.OnTabClosed)
        self.Bind(aui.EVT_AUINOTEBOOK_TAB_RIGHT_DOWN, self.OnTabContextMenu)
        self.Bind(aui.EVT_AUINOTEBOOK_BG_RIGHT_DOWN, self.OnTabBackgroundContextMenu)
        Publisher().subscribe(self.settingsChanged, 'peppy.preferences.changed')
        
        self.allow_changes = True

    def settingsChanged(self, msg):
        """Pubsub callback to handle settings change that might change the
        appearance of the tabs.
        """
        style = self.getStyle()
        self.SetAGWWindowStyleFlag(style)
    
    def getStyle(self):
        style = aui.AUI_NB_WINDOWLIST_BUTTON|aui.AUI_NB_TAB_MOVE|aui.AUI_NB_TAB_SPLIT|aui.AUI_NB_SCROLL_BUTTONS
        if wx.GetApp().tabs.isCloseButtonOnTab():
            style |= aui.AUI_NB_CLOSE_ON_ACTIVE_TAB
        else:
            style |= aui.AUI_NB_CLOSE_BUTTON
        return style

    def holdChanges(self):
        """Defer updates to menu system until processChanges is called.
        
        This short-circuits the automatic call to BufferFrame.switchMode
        in OnTabChanged until a call to processChanges.  This prevents the
        creation of intermediate menubars when multiple tabs are added or
        deleted.
        """
        self.allow_changes = False

    def processChanges(self):
        """Restore the normal operation of OnTabChanged and force the
        recreation of the menubar.
        
        Returns OnTabChanged to its normal state where it recreates the menubar
        every time it is called.
        """
        self.frame.switchMode()
        self.allow_changes = True

    def OnTabChanged(self, evt):
        """Callback for aui.EVT_AUINOTEBOOK_PAGE_CHANGED
        
        Keeps a record of the last active tab (if there was one) and activates
        the new active tab in the frame by calling L{BufferFrame.switchMode}.
        """
        newpage = evt.GetSelection()
        oldpage = evt.GetOldSelection()
        assert self.dprint("changing from tab %s to %s" % (oldpage, newpage))
        if oldpage >= 0:
            self.lastActivePage=self.GetPage(oldpage)
            # There are some cases where springtabs aren't popped down when
            # activating a popup menu that calls for the switch to a new mode.
            # So, make the explicit call to clearPopups here to force any
            # springtabs tied to the old major mode to be cleared.
            self.lastActivePage.clearPopups()
        else:
            self.lastActivePage=None
        if self.allow_changes:
            self.frame.switchMode()
        else:
            self.dprint("Pending tab change; will be updated after all changes completed.")
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

    def OnTabBackgroundContextMenu(self, evt):
        """Handle context menu on the tab area background.
        
        If a right click occurs on a tab, L{OnTabContextMenu} is called instead.
        """
        action_classes = []
        pub.sendMessage('tab_background.context_menu', action_classes=action_classes)
        #dprint(action_classes)
        if action_classes:
            PopupMenu(self.frame, self, None, action_classes)
        
    def OnTabContextMenu(self, evt):
        """Handle context menu on a tab button.
        
        Unlike a traditional notebook control that has a single row of tabs at
        the top of the control, an AUI notebook may have multiple rows of tab
        buttons if the control is split.  The index number of any particular
        tab is dependent on which row of tab buttons the event happens.
        
        However, there is another index that is invariant and based on the
        order in which the page was added to the notebook itself.  This is the
        index used by the AuiNotebook.GetPage method.
        
        Only this context menu driver is concerned about multiple rows of tab
        buttons; the index produced by this method and passed to the popup
        menu as the C{context_tab} key is the invariant index.
        """
        # The event will be reported on one of the potentially multiple
        # AuiTabCtrl controls
        tabctrl = evt.GetEventObject()
        tab = evt.GetSelection()
        aui_notebook_page = tabctrl.GetPage(tab)
        wrapper = aui_notebook_page.window
        
        # This index is the invariant index
        index = self._tabs.GetIdxFromWindow(wrapper)
        #dprint("Context menu over tab %d: %s" % (tab, aui_notebook_page.caption))
        action_classes = []
        pub.sendMessage('tabs.context_menu', action_classes=action_classes)
        #dprint(action_classes)
        options = {
            'context_tab': index,
            'wrapper': wrapper,
            'mode': wrapper.editwin,
            }
        if action_classes:
            PopupMenu(self.frame, self, None, action_classes, options)

    def closeAllTabs(self):
        self.holdChanges()
        for index in range(0, self.GetPageCount()):
            self.removeWrapper(0)
    
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
                if self.allow_changes:
                    self.frame.switchMode()
                else:
                    self.dprint("Pending tab change; will be updated after all changes completed.")
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

    def newBuffer(self, user_url, buffer, modecls=None, mode_to_replace=None, new_tab=False, options=None):
        if mode_to_replace:
            wrapper = self.getWrapper(mode_to_replace)
        else:
            wrapper = self.getNewModeWrapper(new_tab=new_tab)
        mode = wrapper.createMajorMode(self.frame, buffer, modecls)
        assert self.dprint("major mode=%s" % mode)
        self.updateWrapper(wrapper)
        mode.showInitialPosition(user_url, options)
        msg = mode.getWelcomeMessage()
        mode.status_info.setText(msg)
        mode.setReadyForIdleEvents()

    def newMode(self, buffer, modecls=None, mode_to_replace=None, wrapper=None):
        assert self.dprint("mode=%s replace=%s" % (buffer, mode_to_replace))
        if mode_to_replace:
            wrapper = self.getWrapper(mode_to_replace)
        elif not wrapper:
            wrapper = self.getNewModeWrapper()
        try:
            mode = wrapper.createMajorMode(self.frame, buffer, modecls)
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
