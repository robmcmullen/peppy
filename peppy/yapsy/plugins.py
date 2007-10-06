"""
Base class for peppy plugins
"""
import wx

from peppy.yapsy.IPlugin import IPlugin

class IPeppyPlugin(IPlugin, object):
    """
    Some peppy-specific methods in addition to the yapsy plugin methods.
    """

    def __init__(self):
        """
        Set the basic variables.
        """
        self.is_activated = False

    def activate(self):
        """
        Called at plugin activation.
        """
        self.is_activated = True

    def deactivate(self):
        """
        Called when the plugin is disabled.
        """
        self.is_activated = False

    def isInUse(self):
        """
        Used in deactivation processing -- if the plugin reports that
        it is currently in use, it won't be deactivated.  Currently,
        only an active major mode will cause this to return True.
        """
        modes = []
        for frame in wx.GetTopLevelWindows():
            if hasattr(frame, 'getAllModes'):
                modes.extend(frame.getAllModes())
        for mode in self.possibleModes():
            if mode in modes:
                return True
        return False

    def possibleModes(self):
        """Return list of major modes provided by the plugin.

        If this plugin provides any major modes, return a list or
        generator of all the major modes that this plugin is
        representing.  Generally, a plugin will only represent a
        single mode, but it is possible to represent more.
        """
        return []

    def getMinorModes(self):
        """Return list of minor modes provided by the plugin.
        
        Return an iterator containing the minor mode classes
        associated with this plugin.
        """
        return []

    def getSidebars(self):
        """Return list of sidebars provided by the plugin.
        
        Return iterator containing list of frame sidebars that are
        provided by this plugin.
        """
        return []

    def getMenuItems(self):
        """Return list of menu items.

        If the plugin implements any menu actions, return a 3-tuple
        (mode,menu,item) for each menu action, where each element is
        defined as follows:

        mode is a string or None.  A string specifies the major mode
        by referring to its keyword, and None means it is a global
        menu item and will appear in all major modes.

        menu is a string that specifies the menu under which this item
        will appear.  Submenus can be indicated by a tuple of strings.

        item is an instance of Menu, MenuItem, MenuItemGroup, or
        Separator that is a wrapper around the action to be performed
        when this menu item is selected.
        """
        return []

    def getToolBarItems(self):
        """Return list of toolbar items.

        If the plugin implements any toolbar actions, return a 3-tuple
        (mode, menu, item) for each action, where the elements are
        defined as in getMenuItems().
        """
        return []

    def getKeyboardItems(self):
        """Return list of keyboard actions that don't have equivalents
        through the menu or toolbar interfaces.

        If the plugin implements any keyboard actions, return a
        2-tuple (mode, action) for each action, where the mode is as
        defined in getMenuItems() and action is the class representing
        the action.
        """
        return []
    
    def getURLHandlers(self):
        """Return list of urllib2 handlers if provided by the plugin.

        If the plugin defines new urllib2 handlers that provide
        support for new protocols, return that list here.  The
        handlers should be a subclass of urllib2.BaseHandler, and
        provide a method called [protocol]_open, where the string
        [protocol] is replaced by text of the protocol.

        For instance, if you were to write a handler for the xyz
        protocol, the handler class would include an xyz_open method.
        """
        return []

#-----
# The next two methods are to provide an interface for shells that
# take a line of input and return a response.

    def supportedShells(self):
        """
        Return a list of shells that this interface supports, e.g. a
        bash shell should return ['bash'] or python should return
        ['python'].
        """
        return []
        
    def getPipe(self, filename):
        """
        Return a file-like object that is the interface to the shell.
        Typically this will act like a pipe to an object: stuff that
        is written to this file handle will get sent through the pipe
        to the shell, and when data is available it can be read from
        this object.
        """
        return None
    
