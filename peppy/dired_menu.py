# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Dired Menu

Menu items associated with DiredMode
"""

import os

from peppy.dired import DiredMode
from peppy.list_mode import ListModeActionMixin
from peppy.actions import *
from peppy.actions.minibuffer import *
from peppy.yapsy.plugins import *


class DiredRefresh(ListModeActionMixin, SelectAction):
    """Refresh the current view to show any changes.
    
    """
    name = "Refresh"
    default_menu = ("Actions", -1000)
    key_bindings = {'default': "F5", }

    def action(self, index=-1, multiplier=1):
        self.mode.resetList(sort=True)


class FlagMixin(ListModeActionMixin):
    """Mixin to set a flag and move to the next item in the list
    
    """
    flag = None
    direction = 1
    
    def action(self, index=-1, multiplier=1):
        if self.flag:
            self.mode.setFlag(self.flag)
        if self.popup_options is None:
            self.mode.moveSelected(multiplier * self.direction)

class FlagBackwardsMixin(FlagMixin):
    """Mixin to set a flag and move to the previous item in the list.
    
    """
    direction = -1


class DeleteMixin(object):
    def isEnabled(self):
        # can only delete if the user has write permissions on the directory
        return not self.mode.buffer.readonly


class DiredDelete(FlagMixin, DeleteMixin, SelectAction):
    """Mark the selected buffer for deletion.
    
    """
    name = "Mark for Deletion"
    default_menu = ("Actions", 120)
    key_bindings = {'default': "d", }
    flag = 'D'


class DiredDeleteBackwards(FlagBackwardsMixin, DeleteMixin, SelectAction):
    """Mark the selected buffer for deletion and move to the previous item.
    
    """
    name = "Mark for Deletion and Move Backwards"
    default_menu = ("Actions", 121)
    key_bindings = {'default': "C-d", }
    flag = 'D'


class DiredMark(FlagMixin, SelectAction):
    """Mark the selected buffer to be displayed.
    
    """
    name = "Mark for Display"
    default_menu = ("Actions", 130)
    key_bindings = {'default': "m", }
    flag = 'M'

class DiredMarkBackwards(FlagBackwardsMixin, SelectAction):
    """Mark the selected buffer to be displayed and move to the previous item.
    
    """
    name = "Mark for Display and Move Backwards"
    default_menu = ("Actions", 130)
    key_bindings = {'default': "C-m", }
    flag = 'M'


class DiredClearFlags(ListModeActionMixin, SelectAction):
    """Clear all flags from the selected item(s).
    
    """
    name = "Clear Flags"
    default_menu = ("Actions", 199)
    key_bindings = {'default': "u", }

    def action(self, index=-1, multiplier=1):
        self.mode.clearFlags()
        if self.popup_options is None:
            if multiplier > 1: multiplier = -1
            self.mode.moveSelected(multiplier)


class DiredExecute(ListModeActionMixin, SelectAction):
    """Act on the marked buffers according to their flags.
    
    """
    name = "Perform Marked Actions"
    default_menu = ("Actions", -300)
    key_bindings = {'default': "x", }

    def action(self, index=-1, multiplier=1):
        self.mode.execute()


class DiredShow(ListModeActionMixin, SelectAction):
    """Show the buffer in a new tab.
    
    """
    name = "Show Buffer"
    default_menu = ("Actions", -400)
    key_bindings = {'default': "o", }

    def action(self, index=-1, multiplier=1):
        url = self.mode.getFirstSelectedKey()
        if url:
            self.frame.open(url)

class DiredReplace(ListModeActionMixin, SelectAction):
    """Show the buffer in place of this tab.
    
    """
    name = "Replace Buffer"
    default_menu = ("Actions", 401)
    key_bindings = {'default': "f", }

    def action(self, index=-1, multiplier=1):
        url = self.mode.getFirstSelectedKey()
        if url:
            wx.CallAfter(self.frame.open, url, mode_to_replace=self.mode)


class DiredMenu(IPeppyPlugin):
    """Plugin providing the dired-specific menu items
    """
    def activateHook(self):
        Publisher().subscribe(self.getDiredMenu, 'dired.context_menu')
    
    def deactivateHook(self):
        Publisher().unsubscribe(self.getDiredMenu)
    
    def getDiredMenu(self, msg):
        action_classes = msg.data
        action_classes.extend(((-500, DiredMark), (510, DiredDelete), (520, DiredClearFlags), (-999, DiredExecute), (-1000, DiredRefresh)))
        #dprint(action_classes)

    def getMajorModes(self):
        yield DiredMode

    def getCompatibleActions(self, modecls):
        if issubclass(modecls, DiredMode):
            return [
                DiredRefresh,
                DiredDelete, DiredDeleteBackwards,
                DiredMark, DiredMarkBackwards,
                DiredClearFlags,
                DiredShow, DiredReplace,
                DiredExecute,
                ]
        return []

    def attemptOpen(self, buffer, url):
        # use a copy of the url because don't want to change the buffer's url
        # unless it turns out that we want to change the scheme
        refcopy = vfs.get_reference(unicode(url)).copy()
        #print "url = %s" % str(refcopy)
        if refcopy.scheme == "file" and vfs.exists(refcopy) and vfs.get_size(refcopy) > 0:
            # change scheme and see if tar can open it
            refcopy.scheme = "tar"
            if vfs.exists(refcopy):
                # OK, we do a bit of a trick here: rewrite the url to change
                # the scheme to tar:
                url.scheme = "tar"
                return (DiredMode, [])
        return (None, [])
