"""
Base class for peppy plugins
"""
import os, sys

import wx

from peppy.lib.userparams import *
from peppy.yapsy.IPlugin import IPlugin

from peppy.debug import *

class IPeppyPlugin(IPlugin, ClassPrefs):
    """
    Some peppy-specific methods in addition to the yapsy plugin methods.
    """
    preferences_tab = "Plugins"
    default_classprefs = (
        BoolParam('disable_at_startup', False, 'Plugins are enabled by default at startup.\nSet this to True to disable the plugin.'),
    )
    
    _startup_complete = False
    
    @classmethod
    def setStartupComplete(cls):
        cls._startup_complete = True
    
    def __init__(self):
        """
        Set the basic variables.
        """
        self.is_activated = False
        self._performed_initial_activation = False
        self._import_dir = None

    def activate(self):
        """
        Called at plugin activation.
        """
        if not self.classprefs.disable_at_startup or self._startup_complete:
            self.is_activated = True
            if not self._performed_initial_activation:
                self.initialActivation()
                self._performed_initial_activation = True

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
        for mode in self.getMajorModes():
            if mode in modes:
                return True
        return False

    def importModule(self, relative_module):
        """Import a module relative to the plugin module."""
        
        save = sys.path
        # Save the old sys.path and modify it temporarily to include the
        # directory in which the plugin was loaded
        if hasattr(sys, 'frozen'): # py2exe
            # in a py2exe module, yapsy plugins don't work, so the plugin will
            # have been imported with a regular import statement.  But, check
            # anyway.
            if self.__class__.__module__ == "__builtin__":
                # Don't know how to handle this yet.
                raise ImportError("Can't locate relative import %s in a dynamicly loaded plugin" % relative_module)
            if "." in relative_module:
                # actually have a fully specified module
                base = relative_module.rsplit(".", 1)
                #dprint("base = %s" % base)
                subdir = base[0].replace(".", "\\")
                #dprint("subdir = %s" % subdir)
                relative_module = base[1]
            else:
                # have a relative module.  Find the current "module path" and
                # make that the first place import looks
                base = self.__class__.__module__.rsplit(".", 1)
                #dprint("base = %s" % base)
                subdir = base[0].replace(".", "\\")
                #dprint("subdir = %s" % subdir)
            dir = os.path.join(sys.path[0], subdir)
            sys.path = [dir]
            sys.path.extend(save)
        else:
            # normal import; just prefix the path list with the local dir
            sys.path = [self._import_dir]
            sys.path.extend(save)
            
        try:
            mod = __import__(relative_module)
        except Exception, e:
            import traceback
            error = traceback.format_exc()
            dprint(error)
            mod = None
        sys.path = save
        #dprint("module = %s" % mod)
        return mod

    ##### Lifecycle control methods
    
    def initialActivation(self):
        """Give the plugin a chance to configure itself the first time
        it is activated.
        
        Called during the plugin's first call to the activate method,
        which is typically during application initialization, after
        the application has loaded all its configuration information,
        but before the command line has been processed.    

        It can also occur later in the application lifecycle if the
        plugin is loaded by some other means.
        
        This is for one-time initialization.
        """
        pass
    
    def addCommandLineOptions(self, parser):
        """Add any options to the OptionParser instance.

        If the plugin defines any command line options, add each
        option to the OptionParser instance passed into this method.
        """
        return

    def processCommandLineOptions(self, options):
        """Process the results of any command line options of interest.

        The options dict that results from OptionPorser.parse_args()
        is passed in to this method, so if the plugin defined any
        options in addCommandLineOptions, it should process the
        results here.
        """
        return

    def requestedShutdown(self):
        """Give the plugin a chance to revoke a shutdown.
        
        Throw an exception to revoke a shutdown.  The error message will
        be displayed to the user.
        """
        pass
    
    def finalShutdown(self):
        """Non-revokable shutdown.
        
        Called after a shutdown has been accepted.  All exceptions are caught
        and ignored in the calling code, so this should only be used for
        shutdown items that don't require user interaction.
        """
        pass

    ##### Feature providing methods
    
    def aboutFiles(self):
        """Add entries to the about filesystem.
        
        The plugin may define additions to the about filesystem by
        returning a dict here.  The about filesystem is a pseudo-
        filesystem that returns data from about: urls, and is used
        mostly for storing read-only help files or sample files.  It
        is useful for adding help text for your plugin.
    
        The dict is keyed on the filename, and the value is the contents
        of the file.
        """
        return {}

    def getMajorModes(self):
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

    def getActions(self):
        """Return list of actions provided by the plugin.

        Return an iterator containing the list of actions that are
        provided by this plugin.  Actions are defined as subclasses
        of the SelectAction class in menu.py.  They define the
        menubar, toolbar, and keyboard control commands.
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
    
