# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Dired Menu

Menu items associated with DiredMode
"""

import os

from peppy.dired import DiredMode

from peppy.actions import *
from peppy.actions.minibuffer import *


class DiredRefresh(SelectAction):
    """Refresh the current list"""
    alias = "dired-refresh"
    name = "Refresh"
    tooltip = "Refresh the current view to show any changes."
    default_menu = ("Actions", -1000)
    key_bindings = {'default': "F5", }

    def action(self, index=-1, multiplier=1):
        self.mode.reset(sort=True)


class FlagMixin(object):
    """Mixin to set a flag and move to the next item in the list"""
    flag = None
    
    def action(self, index=-1, multiplier=1):
        if self.flag:
            self.mode.setFlag(self.flag)
        dprint(self.popup_options)
        if self.popup_options is None:
            self.mode.moveSelected(multiplier)

class FlagBackwardsMixin(object):
    """Mixin to set a flag and move to the previous item in the list."""
    flag = None
    
    def action(self, index=-1, multiplier=1):
        if self.flag:
            self.mode.setFlag(self.flag)
        if self.popup_options is None:
            self.mode.moveSelected(-1)


class DiredNext(FlagMixin, SelectAction):
    alias = "dired-next"
    name = "Move to Next Item"
    tooltip = "Move the selection to the next item in the list."
    default_menu = ("Actions", 100)
    key_bindings = {'default': "n", }

class DiredPrevious(FlagBackwardsMixin, SelectAction):
    alias = "dired-previous"
    name = "Move to Previous Item"
    tooltip = "Move the selection to the previous item in the list."
    default_menu = ("Actions", 101)
    key_bindings = {'default': "p", }


class DiredDelete(FlagMixin, SelectAction):
    alias = "dired-delete"
    name = "Mark for Deletion"
    tooltip = "Mark the selected buffer for deletion."
    default_menu = ("Actions", 120)
    key_bindings = {'default': "d", }
    flag = 'D'

class DiredDeleteBackwards(FlagBackwardsMixin, SelectAction):
    alias = "dired-delete-backwards"
    name = "Mark for Deletion and Move Backwards"
    tooltip = "Mark the selected buffer for deletion and move to the previous item."
    default_menu = ("Actions", 121)
    key_bindings = {'default': "C-d", }
    flag = 'D'


class DiredMark(FlagMixin, SelectAction):
    alias = "dired-mark"
    name = "Mark for Display"
    tooltip = "Mark the selected buffer to be displayed."
    default_menu = ("Actions", 130)
    key_bindings = {'default': "m", }
    flag = 'M'

class DiredMarkBackwards(FlagBackwardsMixin, SelectAction):
    alias = "dired-mark-backwards"
    name = "Mark for Display and Move Backwards"
    tooltip = "Mark the selected buffer to be displayed and move to the previous item."
    default_menu = ("Actions", 130)
    key_bindings = {'default': "C-m", }
    flag = 'M'


class DiredClearFlags(SelectAction):
    alias = "dired-clear-flags"
    name = "Clear Flags"
    tooltip = "Clear all flags from the selected item(s)."
    default_menu = ("Actions", 199)
    key_bindings = {'default': "u", }

    def action(self, index=-1, multiplier=1):
        self.mode.clearFlags()
        if self.popup_options is None:
            if multiplier > 1: multiplier = -1
            self.mode.moveSelected(multiplier)


class DiredExecute(SelectAction):
    alias = "dired-execute"
    name = "Save or Delete Marked Buffers"
    tooltip = "Act on the marked buffers according to their flags."
    default_menu = ("Actions", -300)
    key_bindings = {'default': "x", }

    def action(self, index=-1, multiplier=1):
        self.mode.execute()


class DiredShow(SelectAction):
    alias = "dired-show"
    name = "Show Buffer"
    tooltip = "Show the buffer in a new tab."
    default_menu = ("Actions", -400)
    key_bindings = {'default': "o", }

    def action(self, index=-1, multiplier=1):
        url = self.mode.getFirstSelectedKey()
        if url:
            self.frame.open(url)

class DiredReplace(SelectAction):
    alias = "dired-replace"
    name = "Replace Buffer"
    tooltip = "Show the buffer in place of this tab."
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
        action_classes.extend(((500, DiredMark), (510, DiredDelete), (520, DiredClearFlags), (-999, DiredExecute), (-1000, DiredRefresh)))
        #dprint(action_classes)

    def getMajorModes(self):
        yield DiredMode

    def getCompatibleActions(self, mode):
        if issubclass(mode.__class__, DiredMode):
            return [
                DiredRefresh,
                DiredNext, DiredPrevious,
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
        refcopy = vfs.get_reference(unicode(url))
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
