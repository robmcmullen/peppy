# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Main application class.
"""

import os, sys

import wx
from wx.lib.pubsub import Publisher

from menu import *
from buffers import *
from debug import *
from trac.core import *
import mainmenu

from peppy.lib.loadfileserver import LoadFileProxy


class KeyboardConf(ClassSettings, debugmixin):
    """Loader for keyboard configurations.

    Keyboard accelerator settings are made in the application
    configuration file peppy.cfg in the user's configuration
    directory.  In the file, the section KeyboardConf is used to map
    an action name to its keyboard accelerator.

    For example:

      [KeyboardConf]
      Copy = C-C
      Open = C-X C-F
      SaveAs = None
      Help = default

    will set the keyboard accelerators for the Copy and Open actions,
    remove any keyboard accelerator from SaveAs, and use the
    application's default setting for Help.  Additionally, if an
    action doesn't appear in the KeyboardConf section it will also use
    the application's default value (which is specified in the source
    code.)
    """
    default_settings = {}
    platform = 'win'
    
    ignore_list = ['MajorAction', 'MinibufferAction']

    @classmethod
    def getKey(cls, action):
        keyboard = None
        bindings = action.key_bindings
        if isinstance(bindings, dict):
            if cls.platform in bindings:
                keyboard = bindings[cls.platform]
            elif 'default' in bindings:
                keyboard = bindings['default']
        return keyboard
    
    @classmethod
    def load(cls):
        actions = Peppy.getSubclasses(SelectAction)
        #dprint(actions)
        found_emacs = False
        for action in actions:
            #dprint("%s: default=%s new=%s" % (action.__name__, action.keyboard, cls.settings._get(action.__name__)))
            acc = cls.settings._get(action.__name__)
            if acc is not None and acc.lower() != 'default':
                if acc.lower() == "none":
                    # if the text is None, don't bind it to anything.
                    action.keyboard = None
                else:
                    action.keyboard = acc
            else:
                action.keyboard = cls.getKey(action)

            # Determine up the accelerator text here, up front, rather
            # than computing it every time the menu is displayed.
            numkeystrokes = action.setAcceleratorText()
            if numkeystrokes>1:
                found_emacs = True

        if found_emacs:
            # Found a multi-key accelerator: force all accelerators to
            # be displayed in emacs style.
            for action in actions:
                action.setAcceleratorText(force_emacs=True)

    @classmethod
    def configDefault(cls, fh=sys.stdout):
        lines = []
        lines.append("[%s]" % cls.__name__)
        keymap = {}
        for action in Peppy.getSubclasses(SelectAction):
            if not issubclass(action, ToggleAction) and not issubclass(action, ListAction) and action.__name__ not in cls.ignore_list:
                keymap[action.__name__] = cls.getKey(action)
        names = keymap.keys()
        names.sort()
        for name in names:
            lines.append("%s = %s" % (name, keymap[name]))
        fh.write(os.linesep.join(lines) + os.linesep)

class DebugClass(ToggleListAction):
    """A multi-entry menu list that allows individual toggling of debug
    printing for classes.

    All frames will share the same list, which makes sense since the
    debugging is controlled by class attributes.
    """
    debuglevel=0
    
    name = "DebugClassMenu"
    empty = "< list of classes >"
    tooltip = "Turn on/off debugging for listed classes"
    categories = False
    inline = True

    # File list is shared among all windows
    itemlist = []

    @staticmethod
    def append(kls,text=None):
        """Add a class to the list of entries

        @param kls: class
        @type kls: class
        @param text: (optional) name of class
        @type text: text
        """
        if not text:
            text=kls.__name__
        DebugClass.itemlist.append({'item':kls,'name':text,'icon':None,'checked':kls.debuglevel>0})
        
    def getHash(self):
        return len(DebugClass.itemlist)

    def getItems(self):
        return [item['name'] for item in DebugClass.itemlist]

    def isChecked(self, index):
        return DebugClass.itemlist[index]['checked']

    def action(self, index=-1):
        """
        Turn on or off the debug logging for the selected class
        """
        assert self.dprint("DebugClass.action: id(self)=%x name=%s index=%d id(itemlist)=%x" % (id(self),self.name,index,id(DebugClass.itemlist)))
        kls=DebugClass.itemlist[index]['item']
        DebugClass.itemlist[index]['checked']=not DebugClass.itemlist[index]['checked']
        if DebugClass.itemlist[index]['checked']:
            kls.debuglevel=1
        else:
            kls.debuglevel=0
        assert self.dprint("class=%s debuglevel=%d" % (kls,kls.debuglevel))


class Peppy(BufferApp, ClassSettings):
    """Main application object.

    This handles the initialization of the debug parameters for
    objects and loads the configuration file, plugins, configures the
    initial keyboard mapping, and other lower level initialization
    from the BufferApp superclass.
    """
    debuglevel=0
    verbose=0

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
    
    initialconfig={'BufferFrame':{'width':800,
                                  'height':600,
                                  'sidebars':'filebrowser,debug_list',
                                  },
                   'Peppy':{'plugins': '',
                            'recentfiles':'recentfiles.txt',
                            },
                   }
    default_settings = {
        'listen_port': 55555,
        'one_instance': True,
        'binary_percentage': 10,
        'magic_size': 1024,
        'default_text_mode': 'Fundamental',
        'default_binary_mode': 'HexEdit',
        }
    
    def OnInit(self):
        """Main application initialization.

        Called by the wx framework and used instead of the __init__
        method in a wx application.
        """
        if self.verbose:
            self.setVerbosity()
        BufferApp.OnInit(self)

        self.setConfigDir("peppy")
        self.setInitialConfig(self.initialconfig)
        self.loadConfig("peppy.cfg")

        # set verbosity on any new plugins that may have been loaded
        # and set up the debug menu
        self.setVerbosity(menu=DebugClass,reset=self.verbose)

        return True

    @classmethod
    def getSubclasses(self,parent=debugmixin,subclassof=None):
        """
        Recursive call to get all classes that have a specified class
        in their ancestry.  The call to __subclasses__ only finds the
        direct, child subclasses of an object, so to find
        grandchildren and objects further down the tree, we have to go
        recursively down each subclasses hierarchy to see if the
        subclasses are of the type we want.

        @param parent: class used to find subclasses
        @type parent: class
        @param subclassof: class used to verify type during recursive calls
        @type subclassof: class
        @returns: list of classes
        """
        if subclassof is None:
            subclassof=parent
        subclasses=[]

        # this call only returns immediate (child) subclasses, not
        # grandchild subclasses where there is an intermediate class
        # between the two.
        classes=parent.__subclasses__()
        for kls in classes:
            if issubclass(kls,subclassof):
                subclasses.append(kls)
            # for each subclass, recurse through its subclasses to
            # make sure we're not missing any descendants.
            subs=self.getSubclasses(parent=kls)
            if len(subs)>0:
                subclasses.extend(subs)
        return subclasses

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
        debuggable=self.getSubclasses()
        debuggable.sort(key=lambda s:s.__name__)
        for kls in debuggable:
            if reset:
                self.setVerboseLevel(kls)
            assert self.dprint("%s: %d (%s)" % (kls.__name__,kls.debuglevel,kls))
            if menu:
                menu.append(kls)
        #sys.exit()

    def startServer(self):
        if self.settings.one_instance:
            self.server = LoadFileProxy(port=self.settings.listen_port)
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
        
    def loadConfigPostHook(self):
        """
        Main driver for any functions that need to look in the config file.
        """
        self.startServer()
        self.autoloadStandardPlugins()
        self.autoloadSetuptoolsPlugins()
        self.parseConfigPlugins()
        KeyboardConf.load()
##        if cfg.has_section('debug'):
##            self.parseConfigDebug('debug',cfg)

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
        mods=self.settings.plugins
        assert self.dprint(mods)
        if mods:
            self.loadPlugins(mods)

    def quitHook(self):
        self.saveConfig("peppy.cfg")
        Publisher().sendMessage('peppy.shutdown')
        return True


def run(options={},args=None):
    """Start an instance of the application.

    @param options: OptionParser option class
    @param args: command line argument list
    """
    
    if options.logfile:
        debuglog(options.logfile)

    if options.key_bindings:
        KeyboardConf.platform = options.key_bindings
        
    Peppy.verbose=options.verbose
    app=Peppy(redirect=False)

    if options.sample_config:
        KeyboardConf.configDefault()
        sys.exit()

    if app.otherInstanceRunning():
        if args:
            for filename in args:
                app.sendToOtherInstance(filename)
        sys.exit()
    
    frame=BufferFrame(app)
    frame.Show(True)
    bad=[]
    if args:
        for filename in args:
            try:
                frame.open(filename)
            except IOError:
                bad.append(filename)

    if len(BufferList.storage)==0:
        frame.titleBuffer()
        
    if len(bad)>0:
        frame.SetStatusText("Failed loading %s" % ", ".join([f for f in bad]))
    
    app.MainLoop()
