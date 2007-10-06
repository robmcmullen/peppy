# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Main application class.
"""

import os, sys, imp, platform
import __builtin__

import wx
from wx.lib.pubsub import Publisher

from peppy.configprefs import *
from peppy.debug import *

from peppy.yapsy.plugins import *
from peppy.yapsy.PeppyPluginManager import *

from peppy.iofilter import *
from peppy.lib.gaugesplash import *
from peppy.lib.loadfileserver import LoadFileProxy
from peppy.lib.userparams import *

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

    base_preferences = "preferences.cfg"
    override_preferences = "peppy.cfg"
    standard_plugin_dirs = ['plugins', 'hsi']

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
    
    minimal_config={'BufferFrame':{'width':800,
                                   'height':700,
                                   'sidebars':'filebrowser, debug_log, error_log, processes',
                                   },
                   }
    default_classprefs = (
        StrParam('plugins', ''),
        StrParam('plugin_dirs', ''),
        StrParam('recentfiles', 'recentfiles.txt'),
        StrParam('title_page', 'about:peppy'),
        StrParam('key_bindings', 'win'),
        IntParam('listen_port', 55555),
        BoolParam('one_instance', True),
        IntParam('binary_percentage', 10),
        IntParam('magic_size', 1024),
        BoolParam('load_threaded', True),
        BoolParam('show_splash', True),
        StrParam('default_text_mode', 'Fundamental'),
        StrParam('default_binary_mode', 'HexEdit'),
        StrParam('default_text_encoding', 'latin1'),
        )

    config = None
    
    def OnInit(self):
        """Main application initialization.

        Called by the wx framework and used instead of the __init__
        method in a wx application.
        """
        self.processCommandLineOptions()

        if self.verbose:
            self.setVerbosity()
        self.menu_actions=[]
        self.toolbar_actions=[]
        self.keyboard_actions=[]
        self.bufferhandlers=[]
        
        name = self.__class__.__name__
        if wx.Platform not in ["__WXMAC__", "__WXMSW__"]:
            name = name.lower()
        self.SetAppName(name)
        self.config = HomeConfigDir(self.options.confdir)

        GlobalPrefs.setDefaults(self.minimal_config)
        self.i18nConfig()
        self.loadConfig()

        # Splash screen and the peppy server need to know if its
        # option is set, so convert as many configuration params as
        # are currently known.
        GlobalPrefs.convertConfig()
        
        self.startServer()
        if self.otherInstanceRunning():
            return True

        self.startSplash()

        count = self.countYapsyPlugins() + 6
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
        Publisher().sendMessage('peppy.config.load')

        self.splash.tick("Setting up graphics...")
        self.initGraphics()

        # set verbosity on any new plugins that may have been loaded
        # and set up the debug menu
        #self.setVerbosity(menu=DebugClass,reset=self.verbose)

        Publisher().subscribe(self.quit, 'peppy.app.quit')
        
        Publisher().sendMessage('peppy.startup.complete')
        self.splash.tick("Starting peppy...")

        wx.SetDefaultPyEncoding(self.classprefs.default_text_encoding)

        return True

    def processCommandLineOptions(self):
        import logging
        #logging.debug = dprint
        
        if not self.options.log_stderr:
            debuglog(errorRedirector('debug'))
            errorlog(errorRedirector('error'))

        if self.options.key_bindings:
            self.classprefs.key_bindings = self.options.key_bindings
            
        self.verbose = self.options.verbose

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

    def startServer(self):
        if self.classprefs.one_instance:
            self.server = LoadFileProxy(port=self.classprefs.listen_port)
            if not self.server.find():
                self.server.start(self)
        else:
            self.server = None

    def otherInstanceRunning(self):
        return self.server is not None and self.server.socket is not None

    def sendToOtherInstance(self, filename):
        self.server.send(filename)

    def loadFile(self, filename):
        frame = self.getTopFrame()
        frame.open(filename)
        
    def getConfigFilePath(self,filename):
        assert self.dprint("found home dir=%s" % self.config.dir)
        return os.path.join(self.config.dir,filename)

    def i18nConfig(self):
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

        init_i18n(path, locale, self.options.i18n_catalog)

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

    def saveConfigPreHook(self):
        pass

    def saveConfig(self, filename):
        self.saveConfigPreHook()
        
        # Send message to any interested plugins that configuration
        # information is about to be saved and provide them with an
        # opportunity to save any auxillary config files.
        Publisher().sendMessage('peppy.config.save')

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
        if main_is_frozen():
            import peppy.py2exe_plugins
        pass
    
    def gaugeCallback(self, plugin_info):
        self.splash.tick("Loading %s..." % plugin_info.name)

    def countYapsyPlugins(self, userdirs=[]):
        """Autoload plugins from peppy plugins directory.

        All .py files that exist in the peppy.plugins directory are
        loaded here.  Currently uses a naive approach by loading them
        in the order returned by os.listdir.  No dependency ordering
        is done.
        """
        paths = [os.path.join(os.path.dirname(__file__), p) for p in self.standard_plugin_dirs]
        paths.extend(userdirs)
        
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
        self.plugin_manager.activateBuiltins()
        
        self.plugin_manager.loadPlugins(self.gaugeCallback)
        
        cats = self.plugin_manager.getCategories()
        for cat in cats:
            plugins = self.plugin_manager.getPluginsOfCategory(cat)
            self.dprint("Yapsy plugins in %s category: %s" % (cat, plugins))
            for plugin in plugins:
                self.dprint("  activating plugin %s: %s" % (plugin.name, plugin.plugin_object.__class__.__mro__))
                plugin.plugin_object.activate()
                self.dprint("  plugin activation = %s" % plugin.plugin_object.is_activated)

    def autoloadSetuptoolsPlugins(self, entry_point='peppy.plugins'):
        """Autoload setuptools plugins.

        All setuptools plugins with the peppy entry point are loaded
        here, if setuptools is installed.
        """
        import peppy.lib.setuptools_utils
        peppy.lib.setuptools_utils.load_plugins(entry_point)

    def initGraphics(self):
        try:
            import peppy.icons.iconmap
            self.dprint("Imported icons!")
        except:
            pass
        
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

    def quit(self, msg):
        doit=self.quitHook()
        if doit:
            wx.GetApp().ExitMainLoop()

    def quitHook(self):
        if not self.saveConfig(self.base_preferences):
            return False
        Publisher().sendMessage('peppy.shutdown')
        return True
    

def run(options={},args=None):
    """Start an instance of the application.

    @param options: OptionParser option class
    @param args: command line argument list
    """
    
    Peppy.options = options
    peppy = Peppy(redirect=False)
    
    if options.sample_config:
        from peppy.keyboard import KeyboardConf
        KeyboardConf.configDefault()
        sys.exit()

    if peppy.otherInstanceRunning():
        if args:
            for filename in args:
                peppy.sendToOtherInstance(filename)
        sys.exit()

    from peppy.buffers import Buffer
    from peppy.frame import BufferFrame
    Buffer.loadPermanent('about:blank')
    Buffer.loadPermanent('about:peppy')
    Buffer.loadPermanent('about:scratch')
    frame=BufferFrame(args)
    frame.Show(True)

    peppy.stopSplash()
    peppy.MainLoop()

def main():
    """Main entry point for editor.

    This is called from a script outside the package, parses the
    command line, and starts up a new wx.App.
    """
    from optparse import OptionParser

    usage="usage: %prog file [files...]"
    parser=OptionParser(usage=usage)
    parser.add_option("-p", action="store_true", dest="profile", default=False)
    parser.add_option("-v", action="count", dest="verbose", default=0)
    parser.add_option("--log-stderr", action="store_true", dest="log_stderr", default=False)
    parser.add_option("--config-dir", action="store", dest="confdir", default="")
    parser.add_option("--i18n-catalog", action="store", dest="i18n_catalog", default="peppy")
    parser.add_option("--sample-config", action="store_true", dest="sample_config", default=False)
    parser.add_option("--key-bindings", action="store", dest="key_bindings", default='win')
    (options, args) = parser.parse_args()
    #print options

    if options.profile:
        import profile
        profile.run('run()','profile.out')
    else:
        run(options,args)



if __name__ == "__main__":
    main()
