# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Main application class.
"""

import os, sys
import __builtin__

import wx
from wx.lib.pubsub import Publisher

from configprefs import *
from debug import *

from peppy.lib.loadfileserver import LoadFileProxy
from peppy.lib.userparams import *

from trac.core import *

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


class Peppy(wx.App, ClassPrefs, debugmixin):
    """Main application object.

    This handles the initialization of the debug parameters for
    objects and loads the configuration file, plugins, configures the
    initial keyboard mapping, and other lower level initialization
    from the BufferApp superclass.
    """
    debuglevel = 1
    verbose = 0
    options = {}

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
                                  'height':600,
                                  'sidebars':'filebrowser,debug_list,error_log',
                                  },
                   'Peppy':{'plugins': '',
                            'recentfiles':'recentfiles.txt',
                            },
                   }
    default_classprefs = (
        StrParam('plugins', ''),
        StrParam('recentfiles', 'recentfiles.txt'),
        StrParam('key_bindings', 'win'),
        IntParam('listen_port', 55555),
        BoolParam('one_instance', True),
        IntParam('binary_percentage', 10),
        IntParam('magic_size', 1024),
        StrParam('default_text_mode', 'Fundamental'),
        StrParam('default_binary_mode', 'HexEdit'),
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

        self.initialConfig(self.minimal_config)
        self.i18nConfig()
        self.loadConfig("peppy.cfg")

        self.errors=[]

        # set verbosity on any new plugins that may have been loaded
        # and set up the debug menu
        #self.setVerbosity(menu=DebugClass,reset=self.verbose)

        Publisher().subscribe(self.quit, 'peppy.app.quit')
        
        Publisher().sendMessage('peppy.startup.complete')

        return True

    def processCommandLineOptions(self):
        if self.options.logfile:
            debuglog(self.options.logfile)

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

    def initialConfig(self,defaults={'Frame':{'width':400,
                                                 'height':400,
                                                 }
                                        }):
        GlobalPrefs.setDefaults(defaults)
        dprint("port = %s, type=%s" % (self.classprefs.listen_port, type(self.classprefs.listen_port)))

    def i18nConfig(self):
        dprint("found home dir=%s" % self.config.dir)

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

    def loadConfig(self, filename):
        try:
            fh = self.config.open(filename)
            GlobalPrefs.readConfig(fh)
        except:
            print "Failed opening config file %s" % filename

        self.loadConfigPostHook()
        
        ConfigurationExtender(ComponentManager()).load(self)

    def loadConfigPostHook(self):
        """
        Main driver for any functions that need to look in the config file.
        """
        self.startServer()
        self.autoloadImports()
        self.autoloadStandardPlugins()
        self.autoloadSetuptoolsPlugins()
        self.parseConfigPlugins()
##        if cfg.has_section('debug'):
##            self.parseConfigDebug('debug',cfg)

    def saveConfigPreHook(self):
        pass

    def saveConfig(self,filename):
        self.saveConfigPreHook()
        
        ConfigurationExtender(ComponentManager()).save(self)

        GlobalSettings.saveConfig(filename)

    def loadPlugin(self, plugin, abort=True):
        """Import a plugin from a module name

        Given a module name (e.g. 'peppy.plugins.example_plugin',
        import the module and trap any import errors.

        @param: name of plugin to load
        """
        assert self.dprint("loading plugins from module=%s" % str(plugin))
        # FIXME: make abort's default state be dependent on some
        # configuration parameter
        if abort:
            mod=__import__(plugin)
        else:
            try:
                mod=__import__(plugin)
            except Exception,ex:
                print "couldn't load plugin %s" % plugin
                print ex
                self.errors.append("couldn't load plugin %s" % plugin)

    def loadPlugins(self,plugins):
        """Import a list of plugins.

        From either a list or a comma separated string, import a group
        of plugins.

        @param plugins: list or comma separated string of plugins to
        load
        """
        if not isinstance(plugins,list):
            plugins=[p.strip() for p in plugins.split(',')]
        for plugin in plugins:
            self.loadPlugin(plugin)

    def autoloadImports(self):
        pass
    
    def autoloadStandardPlugins(self, plugindir='plugins'):
        """Autoload plugins from peppy plugins directory.

        All .py files that exist in the peppy.plugins directory are
        loaded here.  Currently uses a naive approach by loading them
        in the order returned by os.listdir.  No dependency ordering
        is done.
        """
        autoloaddir = os.path.join(os.path.dirname(__file__), plugindir)
        basemodule = self.__module__.rsplit('.', 1)[0]
        for plugin in os.listdir(autoloaddir):
            if plugin.endswith(".py"):
                self.loadPlugin("%s.%s.%s" % (basemodule, plugindir,
                                              plugin[:-3]))

    def autoloadSetuptoolsPlugins(self, entry_point='peppy.plugins'):
        """Autoload setuptools plugins.

        All setuptools plugins with the peppy entry point are loaded
        here, if setuptools is installed.
        """
        import peppy.lib.setuptools_utils
        peppy.lib.setuptools_utils.load_plugins(entry_point)

    def parseConfigPlugins(self):
        """Load plugins specified in the config file.

        Additional plugins specified in the 'plugins' setting in the
        Peppy setting of the config file, e.g.:

          [Peppy]
          plugins = pluginlib.plugin1, alternate.plugin.lib.pluginX

        which means that the plugins must reside somewhere in the
        PYTHONPATH.
        """
        mods=self.classprefs.plugins
        assert self.dprint(mods)
        if mods:
            self.loadPlugins(mods)

    def deleteFrame(self,frame):
        #self.pendingframes.append((self.frames.getid(frame),frame))
        #self.frames.remove(frame)
        pass

    def showFrame(self, frame):
        frame.Show(True)

    def getTopFrame(self):
        frame = self.GetTopWindow()
        if not isinstance(frame, BufferFrame):
            # FIXME: can this ever happen?
            dprint("Top window not a BufferFrame!")
            for frame in wx.GetTopLevelWindows():
                if isinstance(frame, BufferFrame):
                    return frame
            dprint("No top level BufferFrames found!")
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
            buffer.removeAllViews()
            BufferList.removeBuffer(buffer)

    def quit(self, msg):
        doit=self.quitHook()
        if doit:
            wx.GetApp().ExitMainLoop()

    def quitHook(self):
        self.saveConfig("peppy.cfg")
        Publisher().sendMessage('peppy.shutdown')
        return True
    

def run(options={},args=None):
    """Start an instance of the application.

    @param options: OptionParser option class
    @param args: command line argument list
    """
    
    Peppy.options = options
    peppy = Peppy(redirect=False)
    dprint(peppy)
    
    if options.sample_config:
        from keyboard import KeyboardConf
        KeyboardConf.configDefault()
        sys.exit()

    if peppy.otherInstanceRunning():
        if args:
            for filename in args:
                peppy.sendToOtherInstance(filename)
        sys.exit()

    from buffers import BufferFrame
    frame=BufferFrame(peppy)
    frame.Show(True)
    bad=[]
    if args:
        for filename in args:
            try:
                frame.open(filename)
            except IOError:
                bad.append(filename)

    frame.showTitleIfNecessary()
        
    if len(bad)>0:
        frame.SetStatusText("Failed loading %s" % ", ".join([f for f in bad]))
    
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
    parser.add_option("-l", action="store", dest="logfile", default=None)
    parser.add_option("--config-dir", action="store", dest="confdir", default="")
    parser.add_option("--i18n-catalog", action="store", dest="i18n_catalog", default="peppy")
    parser.add_option("--sample-config", action="store_true", dest="sample_config", default=False)
    parser.add_option("--key-bindings", action="store", dest="key_bindings", default='win')
    (options, args) = parser.parse_args()
    print options

    if options.profile:
        import profile
        profile.run('run()','profile.out')
    else:
        run(options,args)



if __name__ == "__main__":
    main()
