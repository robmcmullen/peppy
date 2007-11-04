# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Main application class.
"""

import os, sys, imp, platform, random
import __builtin__

import wx
from wx.lib.pubsub import Publisher

from peppy.buffers import *
from peppy.frame import BufferFrame
from peppy.configprefs import *
from peppy.debug import *

from peppy.yapsy.plugins import *
from peppy.yapsy.PeppyPluginManager import *

from peppy.iofilter import *
from peppy.lib.gaugesplash import *
from peppy.lib.loadfileserver import LoadFileProxy
from peppy.lib.userparams import *
from peppy.lib.processmanager import *

#### py2exe support

def main_is_frozen():
    return (hasattr(sys, "frozen") or # new py2exe
           hasattr(sys, "importers") # old py2exe
           or imp.is_frozen("__main__")) # tools/freeze

##### i18n

def i18n_gettext(path):
    import gettext

    trans = gettext.GNUTranslations(open(path, 'rb'))
    __builtin__._ = trans.ugettext

def lower(text):
    """Dummy conversion to test i18n without loading i18n stuff"""
    return text.lower()

def init_i18n(path, lang, catalog):
    gettext_path = os.path.join(path, lang, catalog)
    if os.path.exists(gettext_path):
        i18n_gettext(gettext_path)
    else:
        __builtin__._ = str

class errorRedirector(object):
    def __init__(self, which='error'):
        self.msg = "peppy.log.%s" % which
        self.save = StringIO()
        self.isready = False
        Publisher().subscribe(self.ready, "peppy.ready.%s" % which)

    def ready(self, msg):
        Publisher().sendMessage(msg, self.save.getvalue())
        self.isready = True
        
    def write(self, text):
        if self.isready:
            wx.CallAfter(Publisher().sendMessage, self.msg, text)
        else:
            self.save.write(text)


class Fonts(ClassPrefs):
    preferences_tab = "General"
    default_classprefs = (
        FontParam('primary_editing_font', None, 'Font name of the primary editing font'),
        FontParam('secondary_editing_font', None, 'Font name of the secondary scintilla font'),
    )
    
    def __init__(self):
        # Can't set fonts in the default_classprefs, because at module load
        # time, the wx.App object hasn't been created yet.
        if self.classprefs.primary_editing_font is None:
            self.classprefs.primary_editing_font = wx.Font(10, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        if self.classprefs.secondary_editing_font is None:
            self.classprefs.secondary_editing_font = wx.Font(10, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)


class Mouse(ClassPrefs):
    preferences_tab = "General"
    default_classprefs = (
        ChoiceParam('mouse_wheel_scroll_style', ['lines', 'half', 'page'], 'page', help='Mouse wheel scroll style: lines,\nhalf a page, or entire page'),
        IntParam('mouse_wheel_scroll_lines', 5, 'Number of lines to scroll when mouse wheel\nis in line scrolling mode'),
    )
    

class Peppy(wx.App, ClassPrefs, debugmixin):
    """Main application object.

    This handles the initialization of the debug parameters for
    objects and loads the configuration file, plugins, configures the
    initial keyboard mapping, and other lower level initialization
    from the BufferApp superclass.
    """
    debuglevel = 0
    verbose = 0
    options = {}
    args = []
    
    icon = "icons/peppy.png"

    base_preferences = "preferences.cfg"
    override_preferences = "peppy.cfg"
    standard_plugin_dirs = ['plugins', 'hsi']
    preferences_plugin_dir = "plugins"
    server_port_filename = ".server.port"

    ##
    # This mapping controls the verbosity level required for debug
    # printing to be shown from the class names that match these
    # regular expressions.  Everything not listed here will get turned
    # on with a verbosity level of 1.
    verboselevel={'.*Frame':2,
                  'ActionMenu.*':4,
                  'ActionTool.*':4,
                  '.*Filter':3,
                  }
    
    minimal_config={'BufferFrame':{'width':900,
                                   'height':700,
                                   'sidebars':'filebrowser, debug_log, error_log, info_log, processes',
                                   },
                   }
    preferences_tab = "General"
    default_classprefs = (
        StrParam('full_name', '', 'Your full name, used for annotation in\ndocuments (e.g. in ChangeLog entries)'),
        StrParam('email', '', 'Your email address, used for annotation in\ndocuments (e.g. in ChangeLog entries)'),
        StrParam('plugin_search_path', 'plugins', 'os.pathsep separated list of paths to search\nfor additional plugins'),
        StrParam('title_page', 'about:peppy', 'URL of page to load when no other file\n is loaded'),
        BoolParam('request_server', True, 'Force peppy to send file open requests to\nan already running copy of peppy'),
        BoolParam('requests_in_new_frame', True, 'File open requests will appear in\na new frame if True, or as a new tab in\nan existing frame if False'),
        IntParam('binary_percentage', 10, 'Percentage of non-displayable characters that results\nin peppy guessing that the file is binary'),
        IntParam('magic_size', 1024, 'Size of initial buffer used to guess the type\nof the file.'),
        BoolParam('load_threaded', True, 'Load files in a separate thread?'),
        BoolParam('show_splash', True, 'Show the splash screen on start?'),
        StrParam('default_text_mode', 'Fundamental', 'Name of the default text mode if peppy\ncan\'t guess the correct type'),
        StrParam('default_binary_mode', 'HexEdit', 'Name of the default binary viewing mode if peppy\ncan\'t guess the correct type'),
        StrParam('default_text_encoding', 'latin1', 'Default file encoding if otherwise not specified\nin the file'),
        )
    mouse = Mouse()
    
    config = None
    
    def OnInit(self):
        """Main application initialization.

        Called by the wx framework and used instead of the __init__
        method in a wx application.
        """
        name = self.__class__.__name__
        if wx.Platform not in ["__WXMAC__", "__WXMSW__"]:
            name = name.lower()
        self.SetAppName(name)

        self.bootstrapCommandLineOptions()

        self.menu_actions=[]
        self.toolbar_actions=[]
        self.keyboard_actions=[]
        self.bufferhandlers=[]
        
        GlobalPrefs.setDefaults(self.minimal_config)
        self.loadConfig()

        # Splash screen and the peppy server need to know if its
        # option is set, so convert as many configuration params as
        # are currently known.
        GlobalPrefs.convertConfig()
        
        self.findRunningServer()
        if self.otherInstanceRunning():
            return True
        else:
            self.startServer()

        self.startSplash()

        count = self.countYapsyPlugins() + 7
        self.splash.setTicks(count)
        
        self.splash.tick("Loading standard plugins...")
        self.autoloadImports()
        self.splash.tick("Loading setuptools plugins...")
        self.autoloadSetuptoolsPlugins()
        self.autoloadYapsyPlugins()
            
        # Now that the remaining plugins and classes are loaded, we
        # can convert the rest of the configuration params
        self.splash.tick("Loading extra configuration...")
        GlobalPrefs.convertConfig()

        # Send message to any plugins that are interested that all the
        # configuration information has been loaded.
        self.splash.tick("Initializing plugins...")
        self.activatePlugins()

        # Command line args can now be processed
        self.splash.tick("Processing command line arguments...")
        self.processCommandLineOptions()

        self.splash.tick("Setting up graphics...")
        self.initGraphics()

        # set verbosity on any new plugins that may have been loaded
        # and set up the debug menu
        #self.setVerbosity(menu=DebugClass,reset=self.verbose)

        Publisher().sendMessage('peppy.startup.complete')
        self.splash.tick("Starting peppy...")

        wx.SetDefaultPyEncoding(self.classprefs.default_text_encoding)
        
        self.Bind(wx.EVT_IDLE, self.OnIdle)

        return True
    
    def OnIdle(self, evt):
        """Application-wide idle update events are processed here.
        """
        # The process manager is a global, so it should be updated here
        ProcessManager().idle()
        evt.Skip()

    def bootstrapCommandLineOptions(self):
        """Process a small number of configuration options before
        plugins are loaded.

        Plugins can also define command line options, which obviously
        delays full command line processing until plugins are loaded.
        However, a few options must be parsed before further
        processing takes place.  These are processed here.
        """
        self.dprint("argv before: %s" % (sys.argv,))

        # Check for -v flag for the verbosity level
        self.verbose = 0
        while "-v" in sys.argv:
            index = sys.argv.index("-v")
            self.verbose += 1
            del sys.argv[index]
            index = sys.argv.index("-v")
            
        if self.verbose:
            self.setVerbosity()

        confdir = ""
        if "-c" in sys.argv:
            index = sys.argv.index("-c")
            if len(sys.argv) > index:
                confdir = sys.argv[index + 1]
                del sys.argv[index:index + 2]
        self.config = HomeConfigDir(confdir)

        catalog = "peppy"
        if "--i18n-catalog" in sys.argv:
            index = sys.argv.index("--i18n-catalog")
            if len(sys.argv) > index:
                catalog = sys.argv[index + 1]
                del sys.argv[index:index + 2]
        self.i18nConfig(catalog)

        if "--no-server" in sys.argv:
            index = sys.argv.index("--no-server")
            del sys.argv[index:index + 1]
            self.no_server_option = False

        if "--no-setuptools" in sys.argv:
            index = sys.argv.index("--no-setuptools")
            del sys.argv[index:index + 1]
            self.no_setuptools = True

        self.dprint("argv after: %s" % (sys.argv,))
    
    def getOptionParser(self):
        from optparse import OptionParser

        usage="usage: %prog file [files...]"
        #print sys.argv[1:]
        parser=OptionParser(usage=usage)
        parser.add_option("-p", action="store_true", dest="profile", default=False)
        parser.add_option("-v", action="count", dest="verbose", default=0)
        parser.add_option("--log-stderr", action="store_true", dest="log_stderr", default=False)
        parser.add_option("-c", action="store", dest="confdir", default="")
        parser.add_option("--i18n-catalog", action="store", dest="i18n_catalog", default="peppy")
        parser.add_option("--sample-config", action="store_true", dest="sample_config", default=False)
        parser.add_option("--no-server", action="store_true", dest="no_server", default=False)
        parser.add_option("--no-setuptools", action="store_true", dest="no_setuptools", default=False)

        plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
        for plugin in plugins:
            plugin.addCommandLineOptions(parser)
        return parser

    def processCommandLineOptions(self):
        """Process the bulk of the command line options.

        Because eventually it will be possible to load command line
        options from plugins, most of the command line parsing happens
        after plugins are loaded.  The bootstrap options are repeated
        here so that a usage statement will show the options.
        """
        parser = self.getOptionParser()
        Peppy.options, Peppy.args = parser.parse_args()
        #dprint(Peppy.options)
        
        import logging
        #logging.debug = dprint
        
#        if self.options.sample_config:
#            from peppy.keyboard import KeyboardConf
#            KeyboardConf.configDefault()
#            sys.exit()

        if not self.options.log_stderr:
            debuglog(errorRedirector('debug'))
            errorlog(errorRedirector('error'))

        plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
        for plugin in plugins:
            plugin.processCommandLineOptions(Peppy.options)
        
    def setVerboseLevel(self,kls):
        """
        Set the class's debuglevel if the verbosity level is high
        enough.  Matches the class name against list of regular
        expressions in verboselevel to see if extra verbosity is
        needed to turn on debugging output for that class.

        @param kls: class
        @param type: subclass of debugmixin
        """
        level=self.verbose
        for regex,lev in self.verboselevel.iteritems():
            match=re.match(regex,kls.__name__)
            if match:
                if self.verbose<self.verboselevel[regex]:
                    level=0
                break
        kls.debuglevel=level

    def setVerbosity(self,menu=None,reset=False):
        """
        Find all classes that use the debugmixin and set the logging
        level to the value of verbose.

        @param menu: if set, the value of the menu to populate
        @type menu: DebugClass instance, or None
        """
        debuggable=getAllSubclassesOf(debugmixin)
        debuggable.sort(key=lambda s:s.__name__)
        for kls in debuggable:
            if reset:
                self.setVerboseLevel(kls)
            assert self.dprint("%s: %d (%s)" % (kls.__name__,kls.debuglevel,kls))
            if menu:
                menu.append(kls)
        #sys.exit()

    def findRunningServer(self):
        """Determine if a single instance server is running.
        
        If the server port specification file exists, try to open that file to
        determine the port that is being used by the other running instance.
        """
        self.server = None
        if self.classprefs.request_server and not hasattr(self, 'no_server_option'):
            listen_port = None
            name = self.server_port_filename
            if self.config.exists(name):
                dprint("found existing server port config file %s" % name)
                try:
                    fh = self.config.open(name)
                    listen_port = int(fh.read())
                except:
                    # It's a bad file, so remove it.
                    self.config.remove(name)
                    dprint("removed server port file %s" % name)
                    listen_port = None
            if listen_port is not None:
                server = LoadFileProxy(port=listen_port)
                server.find()
                if server.isActive():
                    self.server = server
                    dprint("socket = %s" % server.socket)
                else:
                    self.config.remove(name)
                    dprint("removed server port file %s" % name)
                    listen_port = None
            dprint("found port = %s" % listen_port)
        
    def getServerPort(self, lo=50000, hi=60000, tries=10):
        """Determine the port to use for the load file server.
        
        Find a port that is open (i.e. that doesn't respond when trying to
        open it) in the specified range and return a LoadFileProxy for it.
        """
        listen_port = None
        server = LoadFileProxy(port=listen_port)
        tried_config = False
        trying = 0
        while trying < tries:
            listen_port = random.randint(lo, hi)
            dprint("trying port %d" % listen_port)
            if not server.find(listen_port):
                # OK, it didn't respond, so it's open.  Let's use it.
                break
            trying += 1
        if not server.isActive():
            fh = self.config.open(self.server_port_filename, "w")
            fh.write(str(listen_port))
            return server
        return None
        
    def startServer(self):
        if self.classprefs.request_server and not hasattr(self, 'no_server_option'):
            dprint(self.server)
            if not self.server:
                self.server = self.getServerPort()
            if self.server:
                self.remote_args = []
                self.server.start(self.loadRemoteArgs)
        else:
            self.server = None

    def otherInstanceRunning(self):
        dprint(self.server)
        return self.server is not None and self.server.socket is not None

    def sendToOtherInstance(self, filename):
        self.server.send(filename)
    
    def loadRemoteArgs(self, arg):
        dprint(arg)
        if arg != LoadFileProxy.EOF:
            self.remote_args.append(arg)
            dprint(self.remote_args)
        else:
            dprint("Processing %s" % self.remote_args)
            parser = self.getOptionParser()
            opnions, args = parser.parse_args(self.remote_args)
            # throw away options, only look at args
            dprint(args)
            
            if self.classprefs.requests_in_new_frame:
                frame = BufferFrame(args)
                frame.Show(True)
            else:
                frame = self.getTopFrame()
                for filename in args:
                    frame.open(filename)
            self.remote_args = []
        
    def getConfigFilePath(self,filename):
        assert self.dprint("found home dir=%s" % self.config.dir)
        return os.path.join(self.config.dir,filename)

    def i18nConfig(self, catalog):
        #dprint("found home dir=%s" % self.config.dir)

        basedir = os.path.dirname(os.path.dirname(__file__))

        try:
            fh = self.config.open("i18n.cfg")
            cfg = ConfigParser()
            cfg.optionxform = str
            cfg.readfp(fh)
            defaults = cfg.defaults()
        except:
            defaults = {}

        locale = defaults.get('locale', 'en')
        path = defaults.get('dir', os.path.join(basedir, 'locale'))

        init_i18n(path, locale, catalog)

    def loadConfig(self):
        files = [self.base_preferences,
                 "%s.cfg" % platform.system(),
                 "%s.cfg" % platform.node(),
                 self.override_preferences]

        for filename in files:
            self.loadConfigFile(filename)

    def loadConfigFile(self, filename):
        if self.config.exists(filename):
            try:
                fh = self.config.open(filename)
                GlobalPrefs.readConfig(fh)
                if self.verbose > 0: dprint("Loaded config file %s" % filename)
            except:
                eprint("Failed opening config file %s" % filename)
        else:
            if self.verbose > 0: dprint("Configuration file %s not found" % self.config.fullpath(filename))

    def startSplash(self):
        if self.classprefs.show_splash:
            import peppy.splash_image
            self.splash = GaugeSplash(peppy.splash_image.getBitmap())
            self.splash.Show()
            self.splash.Update()
            wx.Yield()
            self.splash.Update()
            wx.Yield()
        else:
            self.splash = None
        
    def stopSplash(self):
        if self.splash:
            self.splash.Destroy()

    def saveConfig(self, filename):
        if GlobalPrefs.isUserConfigChanged():
            dprint("User configuration has changed!  Saving")
            text = GlobalPrefs.configToText()
            try:
                fh = self.config.open(filename, "w")
                fh.write(text)
                retval=wx.ID_YES
            except:
                dlg = wx.MessageDialog(wx.GetApp().GetTopWindow(), "Unable to save configuration file\n%s\n\nQuit anyway?" % self.config.fullpath(filename), "Unsaved Changes", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION )
                retval=dlg.ShowModal()
                dlg.Destroy()

            if retval==wx.ID_YES:
                return True
            return False
        return True

    def autoloadImports(self):
        # FIXME: Could make mainmenu a plugin, but at least have to
        # defer main menu loading till after the i18n '_' method is
        # defined.
        import peppy.mainmenu
        import peppy.fundamental
        
        # py2exe imports go here.
        try:
            import peppy.py2exe_plugins
        except:
            pass

    def gaugeCallback(self, plugin_info):
        self.splash.tick("Loading %s..." % plugin_info.name)

    def countYapsyPlugins(self):
        """Autoload plugins from peppy plugins directory.

        All .py files that exist in the peppy.plugins directory are
        loaded here.  Currently uses a naive approach by loading them
        in the order returned by os.listdir.  No dependency ordering
        is done.
        """
        paths = [os.path.join(os.path.dirname(__file__), p) for p in self.standard_plugin_dirs]
        paths.append(os.path.join(self.config.dir, self.preferences_plugin_dir))
        if self.classprefs.plugin_search_path:
            userdirs = self.classprefs.plugin_search_path.split(os.pathsep)
            for path in userdirs:
                paths.append(path)
        
        self.plugin_manager = PeppyPluginManager(
            categories_filter={"Default": IPeppyPlugin},
            directories_list=paths,
            plugin_info_ext="peppy-plugin",
            )

        # To remove the dependency on wx in URLHandler, instead of it
        # using wx.GetApp().plugin_manager in URLHandler, we
        # explicitly set URLHandler's plugin manager
        URLHandler.setPluginManager(self.plugin_manager)
        
        # count the potential plugins that were be found
        count = self.plugin_manager.locatePlugins()
        return count
        
    def autoloadYapsyPlugins(self):
        """Autoload plugins from peppy plugins directory.

        All .py files that exist in the peppy.plugins directory are
        loaded here.  Currently uses a naive approach by loading them
        in the order returned by os.listdir.  No dependency ordering
        is done.
        """
        # Have to activate builtins before loading plugins, because
        # builtins scan the python namespace for subclasses of
        # IPeppyPlugin, and if you wait till after plugins are loaded
        # from the filesystem, two copies will exist.
        self.plugin_manager.activateBuiltins()
        
        self.plugin_manager.loadPlugins(self.gaugeCallback)
        
    def activatePlugins(self):
        cats = self.plugin_manager.getCategories()
        for cat in cats:
            plugins = self.plugin_manager.getLatestPluginsOfCategory(cat)
            self.dprint("Yapsy plugins in %s category: %s" % (cat, plugins))
            for plugininfo in plugins:
                self.dprint("  activating plugin %s: %s" % (plugininfo.name,
                    plugininfo.plugin_object.__class__.__mro__))
                try:
                    plugininfo.plugin_object.activate()
                    self.dprint("  plugin activation = %s" % plugininfo.plugin_object.is_activated)
                except:
                    eprint("Plugin %s failed with exception %s" % (plugininfo.name, str(e)))
        self.plugin_manager.startupCompleted()
        
    def autoloadSetuptoolsPlugins(self, entry_point='peppy.plugins'):
        """Autoload setuptools plugins.

        All setuptools plugins with the peppy entry point are loaded
        here, if setuptools is installed.
        """
        if not hasattr(self, 'no_setuptools'):
            import peppy.lib.setuptools_utils
            peppy.lib.setuptools_utils.load_plugins(entry_point)

    def initGraphics(self):
        try:
            import peppy.iconmap
            self.dprint("Imported icons!")
        except:
            pass
        self.fonts = Fonts()
        
    def deleteFrame(self,frame):
        #self.pendingframes.append((self.frames.getid(frame),frame))
        #self.frames.remove(frame)
        pass

    def showFrame(self, frame):
        frame.Show(True)

    def getTopFrame(self):
        frame = self.GetTopWindow()
        if hasattr(frame, 'open'):
            # FIXME: can this ever happen?
            dprint("Top window not a Peppy frame!")
            for frame in wx.GetTopLevelWindows():
                if hasattr(frame, 'open'):
                    return frame
            dprint("No top level Peppy frames found!")
        return frame

    def enableFrames(self):
        """Force all frames to update their enable status.

        Loop through each frame and force an update of the
        enable/disable state of ui items.  The menu does this in
        response to a user event, so this is really for the toolbar
        and other always-visible widgets that aren't automatically
        updated.
        """
        for frame in wx.GetTopLevelWindows():
            assert self.dprint(frame)
            try:
                frame.enableTools()
            except:
                # not all top level windows will be BufferFrame
                # subclasses, so just use the easy way out and catch
                # all exceptions.
                pass

    def close(self, buffer):
        if buffer.modified:
            dlg = wx.MessageDialog(wx.GetApp().GetTopWindow(), "%s\n\nhas unsaved changes.\n\nClose anyway?" % buffer.displayname, "Unsaved Changes", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION )
            retval=dlg.ShowModal()
            dlg.Destroy()
        else:
            retval=wx.ID_YES

        if retval==wx.ID_YES:
            buffer.removeAllViewsAndDelete()

    def quit(self):
        doit=self.quitHook()
        if doit:
            frame = self.getTopFrame()
            frame.closeAllWindows()
            wx.GetApp().ExitMainLoop()
            
            # FIXME: something is holding the application open; there must be
            # a reference to something that isn't being cleaned up.  This
            # explicit call to sys.exit shouldn't be necessary.
            sys.exit()

    def quitHook(self):
        if not self.saveConfig(self.base_preferences):
            return False
        if not BufferList.promptUnsaved():
            return False
        plugins = self.plugin_manager.getActivePluginObjects()
        exceptions = []
        for plugin in plugins:
            try:
                plugin.requestedShutdown()
            except Exception, e:
                exceptions.append(e)
        if exceptions:
            text = os.linesep().join([str(e) for e in exceptions])
            dlg = wx.MessageDialog(wx.GetApp().GetTopWindow(),
                "Errors shutting down plugins:\n%s\n\nQuit anyway?" % text,
                "Shutdown Errors", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
            retval=dlg.ShowModal()
            dlg.Destroy()
            if retval != wx.ID_YES:
                return False
        for plugin in plugins:
            try:
                plugin.finalShutdown()
            except Exception, e:
                pass
        return True
        
    def GetLog(self):
        """Return logger for Editra compatibility.
        """
        if self.debuglevel > 0:
            return dprint
        else:
            return lambda x: None
    

def run():
    """Start an instance of the application.

    @param options: OptionParser option class
    @param args: command line argument list
    """
    peppy = Peppy(redirect=False)
    
    if peppy.otherInstanceRunning():
        dprint("Found other instance")
        if len(sys.argv) > 1:
            dprint(sys.argv)
            for filename in sys.argv[1:]:
                if filename.find('://') == -1 and not filename.startswith('/') and not filename.startswith('-'):
                    # handle filenames that are relative to the current
                    # directory of the new instance, but since the current
                    # directory of the old instance may be different, we
                    # need to use an absolute path
                    filename = os.path.abspath(filename)
                peppy.sendToOtherInstance(filename)
            peppy.sendToOtherInstance(None)
        sys.exit()

    Buffer.loadPermanent('about:blank')
    Buffer.loadPermanent('about:peppy')
    Buffer.loadPermanent('about:scratch')
    frame=BufferFrame(peppy.args)
    frame.Show(True)

    peppy.stopSplash()
    Publisher().sendMessage('peppy.starting.mainloop')
    wx.CallAfter(Publisher().sendMessage, 'peppy.in.mainloop')
    peppy.MainLoop()

def main():
    """Main entry point for editor.

    This is called from a script outside the package, parses the
    command line, and starts up a new wx.App.
    """

    try:
        index = sys.argv.index("-p")
        import profile
        profile.run('peppy.main.run()','profile.out')
    except ValueError:
        run()



if __name__ == "__main__":
    main()
