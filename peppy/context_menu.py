# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Mixin class providing context menus for wx.Window subclasses.

The subclass must call L{createContextMenuEventBindings} to register the event
handlers that allow the context menu to be popped up.
"""

import os
import wx

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
        pos = evt.GetPosition()
        screen = self.GetScreenPosition()
        #dprint("context menu for %s at %d, %d" % (self, pos.x - screen.x, pos.y - screen.y))
        action_classes = self.getPopupActions(evt, pos.x - screen.x, pos.y - screen.y)
        options = self.getOptionsForPopupActions()
        if action_classes:
            frame = self.getFrame()
            frame.menumap.popupActions(self, action_classes, options)
    
    def getOptionsForPopupActions(self):
        return None

    def getPopupActions(self, evt, x, y):
        """Return the list of action classes to use as a context menu.
        
        If the subclass is capable of displaying a popup menu, it needs to
        return a list of action classes.  The x, y pixel coordinates (relative
        to the origin of major mode window) are included in case the subclass
        can display different popup items depending on the position in the
        editing window.
        """
        return []

