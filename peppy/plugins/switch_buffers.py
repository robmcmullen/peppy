# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Actions to switch the current tab to show a new buffer

A group of actions used to change the contents of the current tab to something
else, or to adjust the tabs themselves.
"""

import os

import wx

from peppy.yapsy.plugins import *
from peppy.frame import *
from peppy.actions import *
from peppy.actions.minibuffer import *
from peppy.debug import *
from peppy.buffers import BufferList


class BufferPopupList(ListAction):
    name = "Same Major Mode"
    inline = False
    
    def getItems(self):
        wrapper = self.frame.tabs.getContextMenuWrapper()
        tab_mode = wrapper.editwin
        self.savelist = [buf for buf in BufferList.storage if buf.defaultmode == tab_mode.__class__]
        return [buf.displayname for buf in self.savelist]

    def action(self, index=-1, multiplier=1):
        assert self.dprint("top window to %d: %s" % (index, self.savelist[index]))
        wrapper = self.frame.tabs.getContextMenuWrapper()
        # Have to use CallAfter here because the call to setBuffer changes the
        # tab structure, and we're in the tab callback during this method
        wx.CallAfter(self.frame.setBuffer, self.savelist[index], wrapper)


class SwitchToBuffer(SelectAction):
    name = "Switch to Buffer"
    alias = "switch-to-buffer"
    tooltip = "Change to a document by typing part of its name"
    key_bindings = {'emacs': "C-X B", }
    default_menu = ("Tools", 610)
    
    def createList(self):
        """Generate list of possible buffer names to complete.

        Note that we complete on the short name of the buffer, not on the full
        URL.
        """
        self.map = {}
        self.full_names = [buf for buf in BufferList.storage]
        self.display_names = [buf.displayname for buf in self.full_names]

    def action(self, index=-1, multiplier=1):
        # FIXME: ignoring number right now
        self.createList()
        minibuffer = StaticListCompletionMinibuffer(self.mode, self,
                                                    label = self.name,
                                                    list = self.display_names,
                                                    initial = "")
        self.mode.setMinibuffer(minibuffer)

    def processMinibuffer(self, minibuffer, mode, text):
        if text in self.display_names:
            index = self.display_names.index(text)
            url = self.full_names[index]
            dprint("found %s, switching to %s" % (text, url))
            wx.CallAfter(self.frame.setBuffer, url)
        else:
            dprint("buffer %s doesn't exist" % text)


class SwitchBuffersPlugin(IPeppyPlugin):
    """Yapsy plugin to register the tab change actions
    """
    def activateHook(self):
        Publisher().subscribe(self.getTabMenu, 'tabs.context_menu')
    
    def deactivateHook(self):
        Publisher().unsubscribe(self.getTabMenu)
    
    def getTabMenu(self, msg):
        action_classes = msg.data
        action_classes.extend([BufferPopupList])
        #dprint(action_classes)

    def getActions(self):
        return [SwitchToBuffer]
