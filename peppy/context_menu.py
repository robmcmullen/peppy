# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Mixin class providing context menus for wx.Window subclasses.

The subclass must call L{createContextMenuEventBindings} to register the event
handlers that allow the context menu to be popped up.
"""

import os
import wx

from peppy.debug import *
from peppy.menu import PopupMenu

class ContextMenuActions(list):
    """Helper class to provide options to the list of actions.
    
    A normal list can be used as the return value for
    L{ContextMenuMixin.getPopupActions}, but this class can also be used if
    you want to include additional options to the popup actions.
    """
    def __init__(self, options=None, **kwargs):
        """Constructor used to supply options for later use by the menu system.
        
        Options can be passed in as a dict using the 'options' keyword
        parameter, or as name/value pairs as keyword arguments to this
        constructor.  Either way, the name/value pairs will be returned from
        L{getOptions} when L{UserActionMap.popupActions} creates the actions.
        """
        list.__init__(self)
        self.options = {}
        if options is not None:
            self.options.update(options)
        self.options.update(kwargs)
    
    def getOptions(self):
        """Called by L{UserActionMap.popupActions} when constructing the
        popup_options list for the actions.
        """
        return self.options


class ContextMenuMixin(object):
    """Mixin class to provide content menu on right click.
    
    In the class that uses this mixin, override L{getPopupActions} to provide
    the list of L{SelectAction} subclasses that will be shown in the popup.
    
    Override L{getOptionsForPopupActions} to provide data that will get passed
    to each action created in the popup.
    """
    def getFrame(self):
        """Return the L{BufferFrame} instance that this window is associated
        with.
        
        Must be overridden by classes that use this mixin.
        """
        raise NotImplementedError
        
    def createContextMenuEventBindings(self):
        self.Bind(wx.EVT_CONTEXT_MENU, self.OnContextMenu)
    
    def removeContextMenuEventBindings(self):
        self.Unind(wx.EVT_CONTEXT_MENU)
    
    def OnContextMenu(self, evt):
        """Hook to display a context menu relevant to this minor mode.

        For standard usage, subclasses should override L{getPopupActions} to
        provide a list of actions to display in the popup menu.  Nonstandard
        behaviour on a right click can be implemented by overriding this
        method instead.
        
        Currently, this event gets triggered when it happens over the
        major mode AND the minor modes.  So, that means the minor
        modes won't get their own EVT_CONTEXT_MENU events unless
        evt.Skip() is called here.

        This may or may not be the best behavior to implement.  I'll
        have to see as I get further into it.
        """
        parent = evt.GetEventObject()
        
        pos = evt.GetPosition()
        screen = self.GetScreenPosition()
        #dprint("context menu for %s at %d, %d" % (self, pos.x - screen.x, pos.y - screen.y))
        action_classes = self.getPopupActions(evt, pos.x - screen.x, pos.y - screen.y)
        options = self.getOptionsForPopupActions()
        if action_classes:
            frame = self.getFrame()
            PopupMenu(frame, parent, self, action_classes, options)
    
    def getOptionsForPopupActions(self):
        """Override this to provide options to the popup actions.
        
        The default implementation returns an empty dict.  By convention,
        the presence of a dict rather than None in an action's popup_options
        attribute can be used to check whether or not the action has been
        called from a popup.
        """
        return {}

    def getPopupActions(self, evt, x, y):
        """Return the list of action classes to use as a context menu.
        
        If the subclass is capable of displaying a popup menu, it needs to
        return a list of action classes.  The x, y pixel coordinates (relative
        to the origin of major mode window) are included in case the subclass
        can display different popup items depending on the position in the
        editing window.
        
        You can use a regular list or a L{ContextMenuActions} instance.
        """
        return []

