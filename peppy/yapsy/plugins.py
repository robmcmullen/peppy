"""
Base class for peppy plugins
"""
import os, sys

import wx

from peppy.lib.userparams import *
from peppy.yapsy.IPlugin import IPlugin

from peppy.debug import *

class IPeppyPlugin(IPlugin, ClassPrefs, debugmixin):
    """Use this interface to extend peppy.
    
    This is the interface that all peppy plugins must implement.  All methods
    in this interface have default implementations, though, so it is only
    necessary to implement those methods that you need for your plugin.
    
    There are two ways to tell peppy about plugins: setuptools and yapsy.

    Setuptools Plugins
    ==================
    
    Setuptools is the more traditional python plugin approach, but currently
    doesn't keep track of version numbers.  To create a setuptools plugin, you
    need to create new module and directory structure somewhere on your hard
    drive, something like this::
    
        mynewplugin-dev/
            setup.py
            mynewplugin/
                __init__.py
                newplugin.py
    
    where your setup.py contains something like this::
    
        from setuptools import setup, find_packages

        setup(
            name="mynewpluginname",
            version="0.1",
            description="my stupendous new plugin",
            author="Your Name",
            packages=['mynewplugin'],
            entry_points='''
            [peppy.plugins]
            MyNewPluginKeyword = mynewplugin.newplugin:NewPlugin
            ''',
        )

    and newplugin.py contains the class NewPlugin that implements the
    IPeppyPlugin interface.  The entry point "peppy.plugins" is the keyword
    that peppy uses to identify the plugins.  MyNewPluginKeyword is a unique
    name that is used within the setuptools system to identify the plugin to
    the user.
    
    To test the plugin, you'll want to use C{python setup.py develop} which
    will make a symbolic link from the python site-packages directory to your
    development directory.  The other option is to create an egg every time
    you want to test a change -- that's not a very efficient option.
    
    Yapsy Plugins
    =============
    
    The other method of informing peppy about the existence of plugins is to
    place the plugins in a special folder in your user configuration directory.
    
    Every user has their own peppy configuration directory.  On unix
    it's called .peppy in your home directory.  On windows, it's in your
    application data directory, usually C{C:/Documents and Settings/Your User
    Name/Application Data/Peppy} where Your User Name is replaced by your
    actual user name.  On Mac OSX, I have no idea and could use your help.
    
    Inside this configuration directory, there's a directory called plugins.
    You place your plugin source code (the .py file) in this directory, along
    with a companion file that should be the same filename except replacing
    the C{.py} extension with C{.peppy-plugin}.  The python source file should
    implement the L{IPeppyPlugin} interface, and the companion file should
    contain the metadata about the plugin, as in the following example::
    
        [Core]
        Name = mynewpluginname
        Module = newplugin

        [Documentation]
        Author = Your User Name
        Version = 0.1
        Website = http://your.web.site
        Description = my stupendous plugin

    where the yapsy plugin code expects the Module to be the name of the python
    source file without the C{.py} extension.
    
    The Yapsy plugin system is currently better supported in the source, but
    it is non-standard.  It may be replaced by a totally-setuptools plugin
    system at some point.  But, the underlying L{IPeppyPlugin} interface won't
    change (or at least methods won't be removed) so plugins are safe to be
    implemented using that interface.
    
    
    @group convenience: isInUse
    @group interface: initial*, addCommandLineOptions, processCommandLineOptions, requestedShutdown, finalShutdown, get*, about*, attempt*, load*, support*
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
        """Setup the required plugin attributes.
        
        NOTE: if overridden in a subclass, make sure to call this constructor
        in the subclass's constructor.
        """
        self.is_activated = False
        self._performed_initial_activation = False
        self._import_dir = None

    def activate(self):
        """Called at plugin activation to initialize some internal parameters.
        
        NOTE: if overridden in a subclass, make sure to call this method
        in the overriding method.  In most cases, it's better to override
        L{activateHook} instead.
        """
        if not self.classprefs.disable_at_startup or self._startup_complete:
            self.is_activated = True
            if not self._performed_initial_activation:
                self.initialActivation()
                self._performed_initial_activation = True
            self.activateHook()
    
    def activateHook(self):
        """Hook called when a plugin is successfully activated.
        
        This is the recommended method to override in subclass when the
        subclass needs to take some action upon activation.  Note that
        plugins can be started and stopped many times during the application's
        lifecycle.  If the plugin needs only one-time activation, override the
        L{initialActivation} method instead.
        """
        pass

    def deactivate(self):
        """Called when the plugin is disabled.
        
        NOTE: if overridden in a subclass, make sure to call this method in the
        overriding method.
        """
        if self.is_activated:
            self.deactivateHook()
        self.is_activated = False

    def deactivateHook(self):
        """Hook called when an active plugin is about to be deactivated.
        
        This is the recommended method to override in subclass when the
        subclass needs to take some action upon deactivation.
        """
        pass

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
    
        The dict is keyed on the filename, and the value is the contents of the
        file, or a tuple with the contents of the file and the mime type.
        
        Some examples::
        
            def aboutFiles(self):
                return {"test.txt": "stuff"}
        
            def aboutFiles(self):
                return {"test.html": ("Hello <strong>world</strong>", "text/html")}
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

    ##### New methods for on-demand plugin loading
    
    def loadVirtualFileSystem(self, url):
        """Load vfs handler for the specified url scheme.

        If an unknown vfs scheme is encountered during the file opening
        process, this method is called with the offending url.  This is the
        opportunity for a plugin to load the vfs handler for that scheme.
        
        There is no need for a return value from this method, as the loader
        will attempt to load the url after calling this method in each plugin.
        If it succeeds, it won't process any further.
        """
        return
    
    def attemptOpen(self, buffer):
        """Last resort to major mode matching: attempting to open the url.

        This method is the last resort if all other pattern matching
        and mode searching fails.  Typically, this is only an issue
        with non-Scintilla editors that use third-party file loading
        libraries.

        buffer: the Buffer object to attempt to load

        @returns: tuple (exact, generic_list) where when exact is not None the
        matching will stop, and the generic_list indicates major modes that
        are acceptable but not necessarily specific
        """
        return (None, [])
    
    def getCompatibleMajorModes(self, stc_class):
        """Return list of major modes that are compatible to the given stc
        class.
        
        Return an iterator containing the major mode classes if the stc backend
        is compatible with the given stc.  This is used to provide the list
        of allowable major modes when the user wants to switch the major mode
        view.
        """
        return []

    def getCompatibleMinorModes(self, majorcls):
        """Return list of minor modes provided by the plugin that are
        compatible with the specified major mode.
        
        Return an iterator containing the minor modes if they are compatible
        with the specified major mode class.
        """
        return []
    
    def getCompatibleActions(self, major):
        """Return list of actions compatible with the major mode.
        
        Return an iterator containing the list of actions provided by this
        plugin that are compatible with the given major mode.  Actions are
        defined as subclasses of the SelectAction class in menu.py.  They
        define the menubar, toolbar, and keyboard control commands.
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
    
