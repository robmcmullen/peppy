# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""
Main application class.
"""

import os, sys, imp, platform, random, string, time
import __builtin__

import wx
from wx.lib.pubsub import Publisher

import peppy.vfs as vfs

from peppy.py2exe_utils import *
from peppy.buffers import *
from peppy.frame import BufferFrame
from peppy.configprefs import *
from peppy.debug import *
from peppy.i18n import *

from peppy.yapsy.plugins import *
from peppy.yapsy.PeppyPluginManager import *

from peppy.lib.gaugesplash import *
from peppy.lib.loadfileserver import LoadFileProxy
from peppy.lib.userparams import *
from peppy.lib.processmanager import *
from peppy.lib.textutil import piglatin

from peppy.autosave import Autosave, BackupFiles

# Debug method to display when CallAfters are being made.
#OrigCallAfter = wx.CallAfter
#def NewCallAfter(*args, **kwargs):
#    import traceback
#    dprint("CallAfter: args=%s kwargs=%s" % (str(args), str(kwargs)))
#    #traceback.print_stack()
#    OrigCallAfter(*args, **kwargs)
#    #wx.GetApp().cooperativeYield()
#wx.CallAfter = NewCallAfter


def get_plugin_dirs(search_path):
    # 'plugins' directory at root of current installation (either when bundled
    # as an app or when running from the file system) is automatically included
    if main_is_frozen():
        top = os.path.dirname(sys.argv[0])
        dirs = []
    else:
        top = os.path.dirname(__file__)
        dirs = [os.path.join(top, "plugins/eggs")]
        if 'site-packages' not in top:
            # running from the local installation, so check for the googlecode
            # plugins at one higher level, checked out in the plugins directory
            top = os.path.dirname(top)
    dirs.append(os.path.join(top, "plugins"))
    
    # Because setuptools can only load plugins from the local filesystem (not
    # from the vfs) we can check for the existence of the directory here
    # before including it in the plugin search path
    if isinstance(search_path, str):
        for path in search_path.split(os.pathsep):
            if os.path.exists(path):
                dirs.append(path)
    #dprint(dirs)
    return dirs

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
    icon = "icons/font.png"
    default_classprefs = (
        FontParam('primary_editing_font', None, 'Font name of the primary editing font', fullwidth=True),
        FontParam('secondary_editing_font', None, 'Font name of the secondary scintilla font', fullwidth=True),
        StrParam('editra_style_theme', 'Default', 'Current Editra style theme'),
    )
    if wx.Platform == "__WXMAC__":
        default_fontsize = 12
    else:
        default_fontsize = 10
    
    first_time = True

    def __init__(self):
        # Can't set fonts in the default_classprefs, because at module load
        # time, the wx.App object hasn't been created yet.
        if self.classprefs.primary_editing_font is None:
            self.classprefs.primary_editing_font = wx.Font(self.default_fontsize, wx.FONTFAMILY_MODERN, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)
        if self.classprefs.secondary_editing_font is None:
            self.classprefs.secondary_editing_font = wx.Font(self.default_fontsize, wx.FONTFAMILY_SWISS, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL)

    def getStylePath(self, name=None):
        c = wx.GetApp().config
        path = c.fullpath('styles')
        if not os.path.exists(path):
            c.create('styles')
            #dprint("created %s" % path)
            
            # Handle conversion from old-style 'styles.ess' to new style
            # directory of style files
            if self.__class__.first_time:
                source = c.fullpath('styles.ess')
                #dprint("Looking for %s to rename" % source)
                if os.path.exists(source):
                    dest = os.path.join(path, '%s.ess' % time.strftime("%Y%m%d", time.localtime(time.time())))
                    os.rename(source, dest)
                self.__class__.first_time = False
        if name:
            if not name.endswith(".ess"):
                name += ".ess"
            path = os.path.join(path, name)
        return path

    def getStyleFile(self, mode=None):
        pathname = self.getStylePath(self.classprefs.editra_style_theme)
        #dprint(pathname)
        return pathname
    

class Mouse(ClassPrefs):
    preferences_tab = "General"
    icon = "icons/mouse.png"
    default_classprefs = (
        ChoiceParam('mouse_wheel_scroll_style', ['lines', 'half', 'page'], 'lines', help='Mouse wheel scroll style: lines, half a page, or entire page'),
        IntParam('mouse_wheel_scroll_lines', 5, 'Number of lines to scroll when mouse wheel is in line scrolling mode'),
        BoolParam('middle_mouse_x11_primary_selection', False, 'Only usable on X11 systems: when a region is selected, should the selection be copied to the primary selection?  Note: due to a bug in wxPython, using this option will erase the value in the standard cut/copy/paste clipboard when a selection is made.'),
    )

    def __init__(self):
        Publisher().subscribe(self.settingsChanged, 'peppy.preferences.changed')
        Publisher().subscribe(self.settingsChanged, 'initialize.preferences')
    
    def settingsChanged(self, msg=None):
        self.setPrimarySelection()
    
    def setPrimarySelection(self):
        import peppy.stcbase as stcbase
        stcbase.setAllowX11PrimarySelection(self.classprefs.middle_mouse_x11_primary_selection)


class Tabs(ClassPrefs):
    preferences_tab = "General"
    icon = "icons/tab.png"
    default_classprefs = (
        IndexChoiceParam('open_file_in_new_tab',
                         ['always use new tab', 'use new tab unless blank', 'always reuse current tab'],
                         1, 'Should a new file be opened in a new tab or should the current tab be reused?'),
        IndexChoiceParam('documents_in_new_tab',
                         ['always use new tab', 'use new tab unless blank', 'always reuse current tab'],
                         1, 'When selecting a document from the documents menu, should it be displayed in a new tab or should the current tab be reused?'),
    )
    
    def useNewTab(self, mode, new_tab):
        if new_tab == 0 or (new_tab == 1 and not mode.isTemporaryMode()):
            return True
        return False
    
    def useNewTabForNewFile(self, mode):
        return self.useNewTab(mode, self.classprefs.open_file_in_new_tab)

    def useNewTabForDocument(self, mode):
        return self.useNewTab(mode, self.classprefs.documents_in_new_tab)


class User(ClassPrefs):
    preferences_tab = "General"
    icon = "icons/user.png"
    default_classprefs = (
        StrParam('full_name', '', 'Your full name, used for annotation in documents (e.g. in ChangeLog entries)', fullwidth=True),
        StrParam('email', '', 'Your email address, used for annotation in documents (e.g. in ChangeLog entries)', fullwidth=True),
    )


class LocaleParam(Param):
    """I18N parameter that pops up a dialog containing available locales.

    The locale's canonical name is used as the value.
    """
    
    def getCtrl(self, parent, initial=None):
        btn = LangListCombo(parent)
        return btn

    def setValue(self, ctrl, value):
        ctrl.setCatalog(value)

    def getValue(self, ctrl):
        return ctrl.getCatalog()

class Language(ClassPrefs):
    preferences_tab = "General"
    icon = "icons/world.png"
    default_classprefs = (
        LocaleParam('language', 'en_US', 'Locale for user interface', wide=True),
        ChoiceParam('fun_translator', ['normal', 'leet', 'pig latin'], 'Have some fun with the localization'),
    )
    
    # Leet speak transformation used to test the translate method
    leet = string.maketrans(u'abegilorstz', u'4639!102572')
        
    def __init__(self):
        self.locale = None
        self.lang = None
        self.fun = None
        Publisher().subscribe(self.settingsChanged, 'peppy.preferences.changed')
        Publisher().subscribe(self.settingsChanged, 'initialize.preferences')

    def translateLeet(self, msgid):
        if u"%" in msgid:
            return msgid
        return msgid.encode('utf-8').translate(self.leet).decode('utf-8')
    
    def translatePigLatin(self, msgid):
        if u"%" in msgid:
            return msgid
        return piglatin(msgid)
    
    def translateSimple(self, msgid):
        msgid = unicode(msgid)
        if self.fun:
            return self.fun(msgid)
        return msgid
    
    def translateLocale(self, msgid):
        msgid = unicode(msgid)
        try:
            msgid = self.messages[msgid].decode(self.encoding)
        except (AttributeError, KeyError):
            #print("didn't find %s" % repr(msgid))
            pass
        if self.fun:
            return self.fun(msgid)
        return msgid
    
    def settingsChanged(self, msg=None):
        self.setLanguage()
        wx.CallAfter(wx.GetApp().updateAllFrames)

    def setLanguage(self):
        #dprint("Updating language to %s" % self.classprefs.language)
        
        # Make *sure* any existing locale is deleted before the new
        # one is created.  The old C++ object needs to be deleted
        # before the new one is created, and if we just assign a new
        # instance to the old Python variable, the old C++ locale will
        # not be destroyed soon enough, likely causing a crash.
        if self.locale:
            assert sys.getrefcount(self.locale) <= 2
            del self.locale
            
        # create a locale object for this language
        translations = getTranslationMap()
        try:
            lang_id = translations[self.classprefs.language].lang_id
        except KeyError:
            lang_id = -1
            
        Publisher().sendMessage('spelling.default_language', self.classprefs.language)
        self.locale = wx.Locale(lang_id)
        if self.locale.IsOk():
            self.messages, self.encoding = importCatalog(self.classprefs.language)
        else:
            self.messages = {}
            self.encoding = 'utf-8'
            # don't keep the bad locale reference around
            self.locale = None
            self.classprefs.language = ''
        
        if self.classprefs.fun_translator == 'leet':
            self.fun = self.translateLeet
        elif self.classprefs.fun_translator == 'pig latin':
            self.fun = self.translatePigLatin
        else:
            self.fun = None
        
        if self.messages:
            __builtin__._ = self.translateLocale
        elif self.fun:
            __builtin__._ = self.translateSimple
        else:
            __builtin__._ = unicode


class Peppy(wx.App, ClassPrefs, debugmixin):
    """Main application object.

    This handles the initialization of the debug parameters for
    objects and loads the configuration file, plugins, configures the
    initial keyboard mapping, and other lower level initialization
    from the BufferApp superclass.
    """
    verbose = 0
    options = {}
    args = []
    
    icon = "icons/peppy.png"

    base_preferences = "preferences.cfg"
    override_preferences = "peppy.cfg"
    standard_plugin_dirs = ['plugins', 'hsi', 'project', 'major_modes']
    preferences_plugin_dir = "plugins"
    server_port_filename = ".server.port"

    ##
    # This mapping controls the verbosity level required for debug
    # printing to be shown from the class names that match these
    # regular expressions.  Everything not listed here will get turned
    # on with a verbosity level of 1.
    verboselevel={'.*Frame':2,
                  'IconStorage':2,
                  'UserActionMap':2,
                  'UserActionClassList':2,
                  '.*Filter':3,
                  }
    
    minimal_config={'BufferFrame':{'width':700,
                                   'height':700,
                                   },
                   }
    preferences_tab = "General"
    preferences_sort_weight = 0
    default_classprefs = (
        StrParam('yapsy_search_path', 'plugins', 'os.pathsep separated list of paths to search for additional yapsy plugins'),
        StrParam('plugin_search_path', '', 'os.pathsep separated list of paths to search for additional setuptools plugins', fullwidth=True),
        StrParam('title_page', 'about:peppy', 'URL of page to load when no other file  is loaded'),
        BoolParam('request_server', True, 'Force peppy to send file open requests to an already running copy of peppy'),
        BoolParam('requests_in_new_frame', True, 'File open requests will appear in a new frame if True, or as a new tab in an existing frame if False'),
        IntParam('binary_percentage', 10, 'Percentage of non-displayable characters that results in peppy guessing that the file is binary'),
        IntParam('magic_size', 1024, 'Size of initial buffer used to guess the type of the file.'),
        FloatParam('minimum_idle_delay', 0.5, 'Minimum delay (in seconds) between idle event updates to prevent a slowdown by propagating too many idle events in a short time period.'),
        BoolParam('load_threaded', True, 'Load files in a separate thread?'),
        BoolParam('show_splash', False, 'Show the splash screen on start?'),
        StrParam('default_text_encoding', 'latin1', 'Default file encoding if otherwise not specified in the file'),
        )
    mouse = Mouse()
    user = User()
    tabs = Tabs()
    language = Language()
    autosave = Autosave()
    backup = BackupFiles()
    
    config = None
    yielding = False
    
    def checkVersion(self):
        """Check to see that the installed wxPython is new enough
        
        """
        version_string = wx.version().split()[0]
        version = version_string.split(".")
        number = int(version[0]) * 100 + int(version[1]) * 10 + int(version[2])
        if number < 287:
            dlg = wx.MessageDialog(self.GetTopWindow(), "You have wxPython %s installed.\nThis is very old and some features may be unavailable or disabled.\n\nwxPython 2.8.8.0 is the recommended minimum version." % version_string, "Old wxPython Version", wx.OK | wx.ICON_EXCLAMATION )
            retval=dlg.ShowModal()
            dlg.Destroy()
            
            self.attemptOldWxPythonVersionFixup()
    
    def attemptOldWxPythonVersionFixup(self):
        """If an old version of wxPython is detected, attempt to fix what we
        can to allow peppy to run as smoothly as possible.
        
        """
        # 2.8.4.2 doesn't have SetItemLabel; only SetText
        if 'SetItemLabel' not in dir(wx.MenuItem):
            wx.MenuItem.SetItemLabel = wx.MenuItem.SetText
    
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
        self.last_idle_update = 0
        
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

        self.initPluginManager()
        count = self.countImports()
        if count == 0:
            # only load yapsy plugins if no py2exe plugins
            count = self.countYapsyPlugins()
            load_yapsy = True
        else:
            load_yapsy = False
        count += self.countSetuptoolsPlugins()
        count += 7
        self.splash.setTicks(count)
        
        self.splash.tick("Loading standard plugins...")
        self.autoloadImports()
        self.splash.tick("Loading setuptools plugins...")
        self.autoloadSetuptoolsPlugins()
        self.autoloadYapsyPlugins(load_yapsy)
            
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
        
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(wx.EVT_IDLE, self.OnIdle)

        return True
    
    def OnKeyDown(self, evt):
        """Last chance to handle keystroke processing.
        
        This is the failsafe keystroke processing handler, which catches all
        key down events that have not been processed by other controls.  If
        a key event makes it all the way out to here, we're probably dealing
        with a major mode that doesn't have a key handler.  Therefore, it's
        likely that the major mode hasn't called L{BufferFrame.OnKeyDown},
        meaning that keystroke commands will not have been handled.
        
        This method makes sure that keystroke events are processed by calling
        the active frame's OnKeyDown function.
        """
        frame = self.GetTopWindow()
        if hasattr(frame, 'root_accel'):
            #dprint(evt)
            frame.root_accel.OnKeyDown(evt)
        evt.Skip()

    def OnIdle(self, evt):
        """Process EVT_IDLE events on the currently active window.
        
        Note that only the top BufferFrame will get idle events, and further
        only the currently active major mode of that frame will get idle
        events.  This prevents a huge slowdown due to toolbar management --
        because toolbars need to update their enable state continually, if
        idle events were processed on all frames, there would be a noticeable
        delay after only a few frames were open.
        """
        top = self.getTopFrame()
        if top:
            #dprint("Processing priority idle event on %s" % top)
            top.processPriorityIdleEvent()
            
        if time.time() < self.last_idle_update + self.classprefs.minimum_idle_delay:
            # don't do idle events too often
            #dprint("Skipping normal idle event because it happened too quickly")
            return
        
        # Move the process manager idle call here to the application level
        # rather than in each list's idle time.
        ProcessManager().idle()
        
        if top:
            #dprint("Processing normal idle event on %s" % top)
            top.processNormalIdleEvent()
        self.last_idle_update = time.time()

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
            
        if self.verbose:
            self.setVerbosity()

        confdir = ""
        if "-c" in sys.argv:
            index = sys.argv.index("-c")
            if len(sys.argv) > index:
                confdir = sys.argv[index + 1]
                del sys.argv[index:index + 2]
        self.config = HomeConfigDir(confdir)

        if "--dbg" in sys.argv:
            index = sys.argv.index("--dbg")
            if len(sys.argv) > index:
                if sys.argv[index + 1 ] == "all":
                    debugmixin.debuglevel = 1

        if "--no-server" in sys.argv:
            index = sys.argv.index("--no-server")
            del sys.argv[index:index + 1]
            self.no_server_option = False

        if "--test" in sys.argv or "-t" in sys.argv:
            # currently just a synonym of --no-server, but that may change
            self.no_server_option = False

        if "--no-setuptools" in sys.argv:
            index = sys.argv.index("--no-setuptools")
            del sys.argv[index:index + 1]
            self.no_setuptools = True

        if "--no-splash" in sys.argv:
            index = sys.argv.index("--no-splash")
            del sys.argv[index:index + 1]
            self.no_splash = True

        self.dprint("argv after: %s" % (sys.argv,))
    
    def getOptionParser(self):
        from optparse import OptionParser

        usage="usage: %prog file [files...]"
        #print sys.argv[1:]
        parser=OptionParser(usage=usage)
        parser.add_option("-p", action="store_true", dest="profile", default=False, help="Run with the python profiler")
        parser.add_option("-v", action="count", dest="verbose", default=0, help="Increase verbosity level.  -vv lots, -vvv insane")
        parser.add_option("-t", "--test", action="store_true", dest="test_mode", default=False, help="Test mode: disable server and redirect errors to stderr")
        parser.add_option("-d", "--debug-print", action="store_true", dest="log_stderr", default=False, help="redirect errors to stderr")
        parser.add_option("-c", action="store", dest="confdir", default="", help="Specify alternate configuration directory")
        parser.add_option("--sample-config", action="store_true", dest="sample_config", default=False, help="Generate sample config file and exit")
        parser.add_option("--no-server", action="store_true", dest="no_server", default=False, help="Disable 'server' that listens for file open requents")
        parser.add_option("--no-setuptools", action="store_true", dest="no_setuptools", default=False, help="Disable setuptools plugin loading")
        parser.add_option("--no-splash", action="store_false", dest="splash", default=True, help="Disable splash screen")
        parser.add_option("--thanks", action="store_true", dest="thanks", default=False, help="Print thank-you notice")

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

        if not self.options.log_stderr and not self.options.test_mode:
            debuglog(errorRedirector('debug'))
            errorlog(errorRedirector('error'))
        
        if self.options.thanks:
            fh = vfs.open("about:thanks")
            print fh.read()
            self.Exit()

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
                self.dprint("found existing server port config file %s" % name)
                try:
                    fh = self.config.open(name)
                    listen_port = int(fh.read())
                    # Windows needs the file to be closed so that it could be
                    # removed below if necessary.
                    fh.close()
                    fh = None
                except:
                    # It's a bad file, so remove it.  (close it first if it's
                    # still open for windows)
                    if fh:
                        fh.close()
                    self.config.remove(name)
                    self.dprint("removed server port file %s" % name)
                    listen_port = None
            if listen_port is not None:
                server = LoadFileProxy(port=listen_port)
                server.find()
                if server.isActive():
                    self.server = server
                    self.dprint("socket = %s" % server.socket)
                else:
                    self.config.remove(name)
                    self.dprint("removed server port file %s" % name)
                    listen_port = None
            self.dprint("found port = %s" % listen_port)
        
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
            self.dprint("trying port %d" % listen_port)
            if not server.find(listen_port):
                # OK, it didn't respond, so it's open.  Let's use it.
                break
            trying += 1
        if not server.isActive():
            fh = self.config.open(self.server_port_filename, "w")
            fh.write(str(listen_port))
            fh.close()
            return server
        return None
        
    def startServer(self):
        if self.classprefs.request_server and not hasattr(self, 'no_server_option'):
            self.dprint(self.server)
            if not self.server:
                self.server = self.getServerPort()
            if self.server:
                self.remote_args = []
                self.server.start(self.loadRemoteArgs)
        else:
            self.server = None

    def otherInstanceRunning(self):
        self.dprint(self.server)
        return self.classprefs.request_server and not hasattr(self, 'no_server_option') and self.server is not None and self.server.socket is not None

    def sendToOtherInstance(self, filename):
        self.server.send(filename)
    
    def loadRemoteArgs(self, arg):
        dprint(arg)
        if arg != LoadFileProxy.EOF:
            self.remote_args.append(arg)
            dprint(self.remote_args)
        else:
            dprint("Processing %s" % self.remote_args)
            # Can't use optparse here because if the remote_args list contains
            # an argument that starts with a '-' and doesn't happen to match
            # an existing argument, it will exit the program
            #parser = self.getOptionParser()
            #opnions, args = parser.parse_args(self.remote_args)
            ## throw away options, only look at args
            args = [arg for arg in self.remote_args if not arg.startswith('-')]
            dprint(args)
            
            if self.classprefs.requests_in_new_frame:
                frame = BufferFrame(args)
                frame.Show(True)
            else:
                frame = self.getTopFrame()
                for filename in args:
                    frame.open(filename, new_tab=True)
            self.remote_args = []
        
    def getConfigFilePath(self,filename):
        assert self.dprint("found home dir=%s" % self.config.dir)
        return os.path.join(self.config.dir,filename)

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
        if self.classprefs.show_splash and not hasattr(self, 'no_splash'):
            import peppy.splash_image
            self.splash = GaugeSplash(peppy.splash_image.getBitmap())
            self.splash.Show()
            self.splash.Update()
            wx.Yield()
            self.splash.Update()
            wx.Yield()
        else:
            from peppy.lib.null import Null
            self.splash = Null()
        
    def stopSplash(self):
        if self.splash:
            self.splash.Destroy()

    def saveConfig(self, filename):
        if GlobalPrefs.isUserConfigChanged():
            self.dprint("User configuration has changed!  Saving")
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

    def countImports(self):
        try:
            import peppy.py2exe_plugins_count
            count = peppy.py2exe_plugins_count.count
        except:
            count = 0
        return count

    def autoloadImports(self):
        # FIXME: Could make mainmenu a plugin, but at least have to
        # defer main menu loading till after the i18n '_' method is
        # defined.
        import peppy.fundamental
        import peppy.fundamental_menu
        
        import peppy.dired
        import peppy.dired_menu
        
        import peppy.list_menu
        
        import peppy.jobcontrol_menu
        
        import peppy.mainmenu
        
        # py2exe imports go here.
        try:
            import peppy.py2exe_plugins
        except:
            pass

    def gaugeCallback(self, plugin_info):
        if isinstance(plugin_info, str):
            name = plugin_info
        else:
            name = plugin_info.name
        self.dprint("Loading %s..." % name)
        self.splash.tick("Loading %s..." % name)

    def initPluginManager(self):
        """Initialize plugin manager and yapsy plugin search path.

        All .py files that exist in the peppy.plugins directory are
        loaded here.  Currently uses a naive approach by loading them
        in the order returned by os.listdir.  No dependency ordering
        is done.
        """
        paths = [os.path.join(os.path.dirname(__file__), p) for p in self.standard_plugin_dirs]
        paths.append(os.path.join(self.config.dir, self.preferences_plugin_dir))
        if self.classprefs.yapsy_search_path:
            userdirs = self.classprefs.yapsy_search_path.split(os.pathsep)
            for path in userdirs:
                paths.append(path)
        
        self.plugin_manager = PeppyPluginManager(
            categories_filter={"Default": IPeppyPlugin},
            directories_list=paths,
            plugin_info_ext="peppy-plugin",
            )

    def countYapsyPlugins(self):
        """Count all yapsy plugins from all plugin directories.
        """
        # count the potential plugins that were be found
        count = self.plugin_manager.locatePlugins()
        return count
        
    def autoloadYapsyPlugins(self, load=True):
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
        if load:
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
                except Exception, e:
                    eprint("Plugin %s failed with exception %s" % (plugininfo.name, str(e)))
        self.plugin_manager.startupCompleted()
        
    def countSetuptoolsPlugins(self, entry_point='peppy.plugins'):
        """Count all yapsy plugins from all plugin directories.
        """
        # count the potential plugins that were be found
        if not hasattr(self, 'no_setuptools'):
            import peppy.lib.setuptools_utils
            dirs = get_plugin_dirs(self.classprefs.plugin_search_path)
            self.dprint("Setuptools search path: %s" % dirs)
            return peppy.lib.setuptools_utils.count_plugins(entry_point, dirs)
        return 0

    def autoloadSetuptoolsPlugins(self, entry_point='peppy.plugins'):
        """Autoload setuptools plugins.

        All setuptools plugins with the peppy entry point are loaded
        here, if setuptools is installed.
        """
        if not hasattr(self, 'no_setuptools'):
            import peppy.lib.setuptools_utils
            dirs = get_plugin_dirs(self.classprefs.plugin_search_path)
            peppy.lib.setuptools_utils.load_plugins(entry_point, dirs, self.gaugeCallback)

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
        if not hasattr(frame, 'open'):
            # FIXME: can this ever happen?
            #dprint("Top window not a Peppy frame!")
            for frame in wx.GetTopLevelWindows():
                if hasattr(frame, 'open'):
                    return frame
            #dprint("No top level Peppy frames found!")
            return None
        return frame
    
    def MacOpenFile(self, filename):
        """OSX specific routine to handle files that are dropped on the icon
        
        """
        frame = self.getTopFrame()
        frame.open(filename)

    def MacReopenApp(self):
        """Called when the doc icon is clicked, and ???

        This will assure that a Frame is brought up, even if they all were
        minimized.
        """
        frame = self.getTopFrame()
        frame.Raise()

    def updateAllFrames(self):
        """Recreate the UI for all frames.

        Loop through each frame and force an update of the entire UI.  This is
        useful after changing languages to force the menubar to be redrawn in
        the new language.
        """
        for frame in wx.GetTopLevelWindows():
            assert self.dprint(frame)
            try:
                frame.switchMode(set_focus=False)
            except:
                # not all top level windows will be BufferFrame
                # subclasses, so just use the easy way out and catch
                # all exceptions.
                pass

    def quit(self):
        doit=self.quitHook()
        if doit:
            frame = self.getTopFrame()
            frame.closeAllWindows()
            wx.GetApp().Exit()
            
            # FIXME: something is holding the application open; there must be
            # a reference to something that isn't being cleaned up.  This
            # explicit call to sys.exit shouldn't be necessary.
            #sys.exit()
        return False

    def quitHook(self):
        if not self.saveConfig(self.base_preferences):
            return False
        if not BufferList.promptUnsaved():
            return False
        BufferList.removeAllAutosaveFiles()
        plugins = self.plugin_manager.getActivePluginObjects()
        exceptions = []
        for plugin in plugins:
            try:
                plugin.requestedShutdown()
            except Exception, e:
                exceptions.append(e)
        if exceptions:
            text = os.linesep.join([str(e) for e in exceptions])
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
    
    def cooperativeYield(self):
        """Make sure you don't try to wx.Yield inside another wx.Yield
        
        wx.Yield doesn't like being called by another function when it's in the
        middle of another yield, so guard against that by using this barrier.
        """
        if self.yielding:
            if self.debuglevel > 0:
                dprint("Caught a yield inside a yield")
                import traceback
                dprint("".join(traceback.format_stack()))
            return
        self.yielding = True
        if self.debuglevel > 0:
            dprint("Pending events: %s.  Yielding at:" % self.Pending())
            import traceback
            dprint("".join(traceback.format_stack()))
        self.Yield()
        if self.debuglevel > 0:
            dprint("Yield returned.")
        self.yielding = False
    
    
    def showHelp(self, section=None):
        from wx.html import HtmlHelpController
        if not hasattr(self, 'helpframe') or self.helpframe is None:
            filename = self.getConfigFilePath("htmlhelp.cfg")
            cfg = wx.FileConfig(localFilename=filename, style=wx.CONFIG_USE_LOCAL_FILE)
            # NOTE: using a FileConfig directly in the HtmlHelpController by
            # self.helpframe.UseConfig(cfg) crashes when closing the help
            # window
            wx.ConfigBase.Set(cfg)
            self.helpframe = HtmlHelpController()
        filename = get_package_data_dir("peppy/help/peppydoc.hhp")
        if os.path.exists(filename):
            self.helpframe.AddBook(filename)
            plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
            for plugin in plugins:
                for book in plugin.getHelpBooks():
                    self.helpframe.AddBook(book)
            if section:
                self.helpframe.Display(section)
            else:
                self.helpframe.DisplayContents()
        else:
            dlg = wx.MessageDialog(self.GetTopWindow(), "Unable to locate help files; installation error?\nThe files should be located here:\n\n%s\n\nbut were not found." % os.path.dirname(filename), "Help Files Not Found", wx.OK | wx.ICON_EXCLAMATION )
            retval=dlg.ShowModal()
            dlg.Destroy()


def run():
    """Start an instance of the application.

    @param options: OptionParser option class
    @param args: command line argument list
    """
    if wx.Platform == "__WXGTK__":
        # Gnome filemanager puts '//' at the beginning of absolute pathnames
        sys.argv = [arg[1:] if arg.startswith("//") else arg for arg in sys.argv]
        #dprint(sys.argv)
    
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
        return

    Buffer.loadPermanent('about:blank')
    Buffer.loadPermanent('about:peppy')
    Buffer.loadPermanent('about:scratch')
    
    # Special case initialization routines for some global settings
    Publisher().sendMessage('initialize.preferences')
    
    Publisher().sendMessage('peppy.before_initial_frame_creation')
    frame=BufferFrame(peppy.args)

    peppy.stopSplash()
    Publisher().sendMessage('peppy.starting.mainloop')
    wx.CallAfter(peppy.checkVersion)
    wx.CallAfter(Publisher().sendMessage, 'peppy.in.mainloop')
    peppy.MainLoop()

def main():
    """Main entry point for editor.

    This is called from a script outside the package, parses the
    command line, and starts up a new wx.App.
    """

    try:
        index = sys.argv.index("-p")
        import cProfile
        cProfile.run('peppy.main.run()','profile.out')
    except ValueError:
        run()



if __name__ == "__main__":
    main()
