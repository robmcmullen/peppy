# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Managing user config files and directories.
"""

import os,types
from ConfigParser import ConfigParser
import cPickle as pickle
from trac.core import *
from debug import *

__all__ = [ 'HomeConfigDir', 'GlobalSettings',
            'ClassSettings', 'ClassSettingsProxy', 'ClassSettingsMixin',
            'getSubclassHierarchy', 'IConfigurationExtender',
            'ConfigurationExtender']

def getHomeDir(debug=False):
    """Find the user's home directory.
    
    Try to find the user home directory, otherwise return current
    directory.  Adapted from
    http://mail.python.org/pipermail/python-list/2005-February/263921.html
    """
    try:
        path1=os.path.expanduser("~")
        if debug: print "path1=%s" % path1
    except:
        path1=""
    try:
        path2=os.environ["HOME"]
        if debug: print "path2=%s" % path2
    except:
        path2=""
    try:
        path3=os.environ["USERPROFILE"]
        if debug: print "path3=%s" % path3
    except:
        path3=""
    try:
        path4 = os.environ.get('HOMEPATH', None)
        if path4 is not None:
            path4 = os.environ['HOMEDRIVE']+homeDir
        if debug: print "path4=%s" % path4
    except:
        path4=""

    # Note that if you are running under Cygwin but using the Windows
    # python, you'll get the unix-style homedir if running under a
    # Cygwin shell, but the Windows 'Documents and Settings' dir if
    # running under standalone Python.
    if os.sys.platform=='win32':
        if os.path.exists(path3):
            return path3
        elif os.path.exists(path4):
            return path4
        # else, fallthrough to regular code
    
    # Cygwin's python shows up with os.sys.platform=='cygwin', so it
    # will default to the unix style homedir.
    if os.path.exists(path1):
        return path1
    elif os.path.exists(path2):
        return path2
    elif os.path.exists(path3):
        return path3
    elif os.path.exists(path4):
        return path4
    else:
        return os.getcwd()

class HomeConfigDir:
    """Simple loader for config files in the home directory.

    Wrapper around home directory files.  Load and save files or
    pickled objects in the home directory.
    """
    
    def __init__(self,dirname,create=True,debug=False):
        self.home=getHomeDir(debug)
        if dirname.startswith('.'):
            dirname=dirname[1:]
        if os.sys.platform=='win32':
            self.dot='_'
        else:
            self.dot='.'
        self.dir=os.path.join(self.home,self.dot+dirname)

        self.check(create)

    def check(self,create):
        if not os.path.exists(self.dir):
            if create:
                os.mkdir(self.dir)

    def exists(self,name):
        return os.path.exists(os.path.join(self.dir,name))

    def open(self,name,mode='r'):
        path=os.path.join(self.dir,name)
        fd=open(path,mode)
        return fd

    def loadObject(self,name):
        item=None
        if self.exists(name):
            fd=self.open(name,'rb')
            item=pickle.load(fd)
            fd.close()
        return item

    def saveObject(self,name,item):
        fd=self.open(name,'wb')
        pickle.dump(item,fd)
        fd.close()


def parents(c, seen=None):
    """Python class base-finder.

    Find the list of parent classes of the given class.  Works with
    either old style or new style classes.  From
    http://mail.python.org/pipermail/python-list/2002-November/132750.html
    """
    if type( c ) == types.ClassType:
        # It's an old-style class that doesn't descend from
        # object.  Make a list of parents ourselves.
        if seen is None:
            seen = {}
        seen[c] = None
        items = [c]
        for base in c.__bases__:
            if not seen.has_key(base):
                items.extend( parents(base, seen))
        return items
    else:
        # It's a new-style class.  Easy.
        return list(c.__mro__)


parentclasses={}
skipclasses=['debugmixin','ClassSettings','ClassSettingsMixin','object']

def getClassHierarchy(klass,debug=0):
    """Get class hierarchy of a class using global class cache.

    If the class has already been seen, it will be pulled from the
    cache and the results will be immediately returned.  If not, the
    hierarchy is generated, stored for future reference, and returned.

    @param klass: class of interest
    @returns: list of parent classes
    """
    global parentclasses
    
    if klass in parentclasses:
        hierarchy=parentclasses[klass]
        if debug: print "Found class hierarchy: %s" % hierarchy
    else:
        hierarchy=[k for k in parents(klass) if k.__name__ not in skipclasses and not k.__module__.startswith('wx.')]
        if debug: print "Created class hierarchy: %s" % hierarchy
        parentclasses[klass]=hierarchy
    return hierarchy

def getHierarchy(obj,debug=0):
    """Get class hierarchy of an object using global class cache.

    If the class has already been seen, it will be pulled from the
    cache and the results will be immediately returned.  If not, the
    hierarchy is generated, stored for future reference, and returned.

    @param obj: object of interest
    @returns: list of parent classes
    """
    klass=obj.__class__
    return getClassHierarchy(klass,debug)

def getNameHierarchy(obj,debug=0):
    """Get the class name hierarchy.

    Given an object, return a list of names of parent classes.
    
    Similar to L{getHierarchy}, except returns the text names of the
    classes instead of the class objects themselves.

    @param obj: object of interest
    @returns: list of strings naming each parent class
    """
    
    hierarchy=getHierarchy(obj,debug)
    names=[k.__name__ for k in hierarchy]
    if debug: print "name hierarchy: %s" % names
    return names

def getSubclassHierarchy(obj,subclass,debug=0):
    """Return class hierarchy of a particular subclass.

    Given an object, return the hierarchy of classes that are
    subclasses of a given type.  In other words, this filters the
    output of C{getHierarchy} such that only the classes that are
    descended from the desired subclass are returned.

    @param obj: object of interest
    @param subclass: subclass type on which to filter
    @returns: list of strings naming each parent class
    """
    
    klasses=getHierarchy(obj)
    subclasses=[]
    for klass in klasses:
        if issubclass(klass,subclass):
            subclasses.append(klass)
    return subclasses
    

class GlobalSettings(object):
    debug=False
    
    default={}
    user={}
    name_hierarchy={}
    class_hierarchy={}
    magic_conversion=True
    
    @staticmethod
    def setDefaults(defs):
        GlobalSettings.default.update(defs)

    @staticmethod
    def addHierarchy(leaf, classhier, namehier):
        if leaf not in GlobalSettings.class_hierarchy:
            GlobalSettings.class_hierarchy[leaf]=classhier
        if leaf not in GlobalSettings.name_hierarchy:
            GlobalSettings.name_hierarchy[leaf]=namehier

    @staticmethod
    def setupHierarchyDefaults(klasshier):
        for klass in klasshier:
            if klass.__name__ not in GlobalSettings.default:
                if hasattr(klass,'defaultsettings'):
                    defs=klass.defaultsettings.copy()
                else:
                    defs={}
                GlobalSettings.default[klass.__name__]=defs
            else:
                # we've loaded application-specified defaults for this
                # class before, but haven't actually checked the
                # class.  Merge them in without overwriting the
                # existing settings.
                #print "!!!!! missed %s" % klass
                if hasattr(klass,'defaultsettings'):
                    defs=klass.defaultsettings
                    g=GlobalSettings.default[klass.__name__]
                    for k,v in defs.iteritems():
                        if k not in g:
                            g[k]=v
                    
            if klass.__name__ not in GlobalSettings.user:
                GlobalSettings.user[klass.__name__]={}
        if GlobalSettings.debug: print "default: %s" % GlobalSettings.default
        if GlobalSettings.debug: print "user: %s" % GlobalSettings.user

    @staticmethod
    def convertValue(section,option,value):
        """Convert a string value to boolean or int if it seems like
        it is a text representation of one of those types."""
        lcval=value.lower()
        if lcval in ['true','on','yes']:
            result=True
        elif lcval in ['false','off','no']:
            result=False
        elif value.isdigit():
            result=int(value)
        else:
            result=value
        return result

    @staticmethod
    def loadConfig(filename):
        cfg=ConfigParser()
        cfg.optionxform=str
        cfg.read(filename)
        for section in cfg.sections():
            d={}
            for option,value in cfg.items(section):
                if GlobalSettings.magic_conversion:
                    d[option]=GlobalSettings.convertValue(section,option,value)
                else:
                    d[option]=value
            GlobalSettings.user[section]=d

    @staticmethod
    def saveConfig(filename):
        print "Saving user configuration: %s" % GlobalSettings.user

class SettingsProxy(debugmixin):
    """Dictionary-like object to provide global settings to a class.

    Implements a dictionary that returns a value for a keyword based
    on the class hierarchy.  Each class will define a group of
    settings and default values for each of those settings.  The class
    hierarchy then defines the search order if a setting is not found
    in a child class -- the search proceeds up the class hierarchy
    looking for the desired keyword.
    """
    
    debuglevel=0
    
    def __init__(self,hier):
        names=[k.__name__ for k in hier]
        self.__dict__['_startSearch']=names[0]
        GlobalSettings.addHierarchy(names[0], hier, names)
        GlobalSettings.setupHierarchyDefaults(hier)

    def __getattr__(self,name):
        klasses=GlobalSettings.name_hierarchy[self.__dict__['_startSearch']]
        d=GlobalSettings.user
        for klass in klasses:
            self.dprint("checking %s for %s in user" % (klass,name))
            if klass in d and name in d[klass]:
                return d[klass][name]
        d=GlobalSettings.default
        for klass in klasses:
            self.dprint("checking %s for %s in default" % (klass,name))
            if klass in d and name in d[klass]:
                return d[klass][name]

        klasses=GlobalSettings.class_hierarchy[self.__dict__['_startSearch']]
        for klass in klasses:
            self.dprint("checking %s for %s in default_settings" % (klass,name))
            if hasattr(klass,'default_settings') and name in klass.default_settings:
                return klass.default_settings[name]
        return None

    def __setattr__(self,name,value):
        GlobalSettings.user[self.__dict__['_startSearch']][name]=value

    def _getValue(self,klass,name):
        d=GlobalSettings.user
        if klass in d and name in d[klass]:
            return d[klass][name]
        d=GlobalSettings.default
        if klass in d and name in d[klass]:
            return d[klass][name]
        return None
    
    def _getDefaults(self):
        return GlobalSettings.default[self.__dict__['_startSearch']]

    def _getUser(self):
        return GlobalSettings.user[self.__dict__['_startSearch']]

    def _getAll(self):
        d=GlobalSettings.default[self.__dict__['_startSearch']].copy()
        d.update(GlobalSettings.user[self.__dict__['_startSearch']])
        return d

    def _getList(self,name):
        vals=[]
        klasses=GlobalSettings.name_hierarchy[self.__dict__['_startSearch']]
        for klass in klasses:
            val=self._getValue(klass,name)
            if val is not None:
                if isinstance(val,list) or isinstance(val,tuple):
                    vals.extend(val)
                else:
                    vals.append(val)
        return vals

    def _getMRO(self):
        return [cls for cls in GlobalSettings.name_hierarchy[self.__dict__['_startSearch']]]
        
        
def ClassSettingsProxy(cls):
    """Return settings object for a given class.

    Returns a SettingProxy object that acts as a dictionary.
    """
    hier=[c for c in getClassHierarchy(cls) if c!=ClassSettingsMixin]
    return SettingsProxy(hier)

class ClassSettingsMetaClass(type):
    def __init__(cls, name, bases, attributes):
        """Add settings attribute to class attributes.

        All classes of the created type will point to the same
        settings object.  Perhaps that's a 'duh', since settings is a
        class attribute, but it is worth the reminder.  Everything
        accessed through self.settings changes the class settings.
        Instance settings are maintained by the class itself.
        """
        #dprint('Bases: %s' % str(bases))
        expanded = [cls]
        for base in bases:
            expanded.extend(getClassHierarchy(base))
        #dprint('New bases: %s' % str(expanded))
        # Add the settings class attribute
        cls.settings = SettingsProxy(expanded)

class ClassSettings(object):
    """Base class to extend in order to support class settings.

    Uses the L{ClassSettingsMetaClass} to provide automatic support
    for the settings class attribute.
    """
    __metaclass__ = ClassSettingsMetaClass

class ClassSettingsMixin(object):
    """Mixin that provides the settings attribute for the class.

    Adds the C{settings} class attribute to a class, providing
    configuration file support and hierarchical parameter setting.
    C{self.settings} acts as a dictionary, and values can be read from
    and written to this dictionary.

    Accessing a key from this dictionary-like object attempts to find
    the keyword by that name in the current class's configuration
    options.  If it is not found, it searches up through the parent
    classes' configuration options until it finds a match.  If no
    match is found through this hierarchical lookup, it returns None.

    FIXME: add the searching of default options through the class
    hierarchy as well.
    """
    def __init__(self,defaults=None):
        self.settings=ClassSettingsProxy(self.__class__)


## Configuration extender interface for hooking into the load/save
## configuration file process

class IConfigurationExtender(Interface):
    """Interface to add new configuration options to the application.

    Implement L{loadConf} to add to the configuration settings before
    the first frame appears.  Could also be used to load additional
    settings not in the main configuration file.

    Implement L{saveConf} to adjust configuration settings before any
    are saved.  Could also be used to save additional settings not in
    the main configuration file.
    """

    def loadConf(app):
        """Load some configuration settings, possibly from an external
        source like a file.

        This is called after the application has loaded all the
        plugins and the main configuration file.
        """

    def saveConf(app):
        """Save configuration settings, possibly to an external file.

        This is called before the main configuration file is written,
        so additions to it are possible.
        """

class ConfigurationExtender(Component):
    """ExtensionPoint that loads L{IConfigurationExtenders}.

    Driver class that is used to call all the registered
    IConfigurationExtenders during application init and shutdown.
    """
    extensions=ExtensionPoint(IConfigurationExtender)

    def load(self,app):
        for ext in self.extensions:
            ext.loadConf(app)

    def save(self,app):
        for ext in self.extensions:
            ext.saveConf(app)




if __name__=='__main__':
    # Testing stuff that creates a directory in the user's homedir.
    # Don't perform this in the standard unit tests.

    def testHomeDir():
        print "for platform %s:" % os.sys.platform
        print getHomeDir()
        c=HomeConfigDir(".configprefs",debug=True)
        print "found home dir=%s" % c.dir
        fd=c.open("test.cfg",'w')
        fd.write('blah!!!')
        fd.close()
        nums=[0,1,2,4,6,99]
        c.saveObject("stuff.bin",nums)
        print c.loadObject("stuff.bin")
    
    testHomeDir()
