# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""

"""

import os

import wx
import wx.aui
from wx.lib.pubsub import Publisher

from peppy.debug import *
from peppy.major import *
from peppy.buffers import BufferList


class FrameNotebook(wx.aui.AuiNotebook, debugmixin):
    def __init__(self, parent, size=wx.DefaultSize):
        wx.aui.AuiNotebook.__init__(self, parent, size=size, style=wx.aui.AUI_NB_WINDOWLIST_BUTTON|wx.aui.AUI_NB_TAB_MOVE|wx.aui.AUI_NB_TAB_SPLIT|wx.aui.AUI_NB_CLOSE_BUTTON|wx.aui.AUI_NB_SCROLL_BUTTONS, pos=(9000,9000))
        
        self.frame = parent
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
        #wx.CallAfter(self.frame.switchMode)
        self.frame.switchMode()
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
        tab = evt.GetSelection()
        wrapper = self.GetPage(tab)
        options = {
            'context_tab': tab,
            'wrapper': wrapper,
            'mode': wrapper.editwin,
            }
        if action_classes:
            self.frame.menumap.popupActions(self, action_classes, options)
        #evt.Skip()

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
