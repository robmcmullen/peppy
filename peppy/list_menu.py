# peppy Copyright (c) 2006-2009 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""List Menu Actions

Actions that work on ListMode major modes.
"""

import os

import wx

from peppy.list_mode import *
from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.debug import *


class ListMoveMixin(ListModeActionMixin):
    """Mixin to set a flag and move to the next item in the list"""
    direction = 1
    
    def getDirection(self):
        return self.direction
    
    def action(self, index=-1, multiplier=1):
        self.mode.moveSelected(multiplier * self.getDirection())

class ListItemNext(ListMoveMixin, SelectAction):
    """Move the selection to the next item in the list.
    
    """
    alias = "list-item-next"
    name = "Move to Next Item"
    default_menu = ("Actions", 100)
    key_bindings = {'default': ["n", "DOWN"], }

class ListItemPrevious(ListMoveMixin, SelectAction):
    """Move the selection to the previous item in the list.
    
    """
    alias = "list-item-previous"
    name = "Move to Previous Item"
    default_menu = ("Actions", 101)
    key_bindings = {'default': ["p", "UP"], }
    direction = -1

class ListPageMoveMixin(ListMoveMixin):
    """Mixin to set a flag and move to the next item in the list"""
    
    def getDirection(self):
        page = self.mode.list.GetCountPerPage()
        if page > 1:
            # Adjust to make sure that we don't scroll the page on the first
            # scroll; rather we jump from the first visible to the last
            # visible on the same page for that first page down.
            page -= 1
        return self.direction * page

class ListItemPageDown(ListPageMoveMixin, SelectAction):
    """Move the selection to the next item in the list.
    
    """
    alias = "list-item-page-down"
    key_bindings = {'default': "PAGEDOWN", }

class ListItemPageUp(ListPageMoveMixin, SelectAction):
    """Move the selection to the previous item in the list.
    
    """
    alias = "list-item-page-up"
    key_bindings = {'default': "PAGEUP", }
    direction = -1

class ListItemHome(ListMoveMixin, SelectAction):
    """Move the selection to the first item in the list.
    
    """
    alias = "list-item-home"
    key_bindings = {'default': "HOME", }
    direction = -99999

class ListItemEnd(ListMoveMixin, SelectAction):
    """Move the selection to the last item in the list.
    
    """
    alias = "list-item-end"
    key_bindings = {'default': "END", }
    direction = 99999


class ListModePlugin(IPeppyPlugin):
    """Yapsy plugin to register ListMode
    """
    def getActions(self):
        return [ListItemNext, ListItemPrevious,
                
                ListItemPageDown, ListItemPageUp,
                
                ListItemHome, ListItemEnd]
