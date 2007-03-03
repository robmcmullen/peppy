#!/usr/bin/env python
"""
Main application program.
"""

import os

import wx

from menu import *
from buffers import *
from debug import *
from trac.core import *
from about import *
import mainmenu


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

    def loadConfigPostHook(self):
        """
        Main driver for any functions that need to look in the config file.
        """
        self.autoloadPlugins()
        self.parseConfigPlugins()
##        if cfg.has_section('debug'):
##            self.parseConfigDebug('debug',cfg)

    def autoloadPlugins(self, plugindir='plugins'):
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
        return True


def run(options={},args=None):
    """Start an instance of the application.

    @param options: OptionParser option class
    @param args: command line argument list
    """
    
    if options.logfile:
        debuglog(options.logfile)
    Peppy.verbose=options.verbose
    app=Peppy(redirect=False)
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
    (options, args) = parser.parse_args()
    #print options

    if options.profile:
        import profile
        profile.run('run()','profile.out')
    else:
        run(options,args)



if __name__ == "__main__":
    main()
