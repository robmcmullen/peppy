#!/usr/bin/env python
"""
Managing user config files and directories.
"""

import os,types
from ConfigParser import ConfigParser
import cPickle as pickle
from debug import *

__all__ = [ 'HomeConfigDir', 'GlobalSettings', 'ClassSettingsMixin' ]

def getHomeDir(debug=False):
    """
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
    """Python class base-finder from
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
skipclasses=['debugmixin','ClassSettingsMixin','object']

def getHierarchy(obj,debug=0):
    global parentclasses
    
    klass=obj.__class__
    if klass in parentclasses:
        hierarchy=parentclasses[klass]
        if debug: print "Found class hierarchy: %s" % hierarchy
    else:
        hierarchy=[k for k in parents(klass) if k.__name__ not in skipclasses]
        if debug: print "Created class hierarchy: %s" % hierarchy
        parentclasses[klass]=hierarchy
    return hierarchy

def getNameHierarchy(obj,debug=0):
    hierarchy=getHierarchy(obj,debug)
    names=[k.__name__ for k in hierarchy]
    if debug: print "name hierarchy: %s" % names
    return names

    

class GlobalSettings(object):
    debug=False
    
    default={}
    user={}
    hierarchy={}
    magic_conversion=True
    
    @staticmethod
    def setDefaults(defs):
        GlobalSettings.default.update(defs)

    @staticmethod
    def addHierarchy(leaf,hier):
        GlobalSettings.hierarchy[leaf]=hier

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
                    d[option]=convertValue(section,option,value)
                else:
                    d[option]=value
            GlobalSettings.user[section]=d

    @staticmethod
    def saveConfig(filename):
        print "Saving user configuration: %s" % GlobalSettings.user

class SettingsProxy(debugmixin):
    debuglevel=0
    
    def __init__(self,hier):
        names=[k.__name__ for k in hier]
        self.__dict__['_startSearch']=names[0]
        GlobalSettings.addHierarchy(names[0],names)
        GlobalSettings.setupHierarchyDefaults(hier)

    def __getattr__(self,name):
        klasses=GlobalSettings.hierarchy[self.__dict__['_startSearch']]
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
        klasses=GlobalSettings.hierarchy[self.__dict__['_startSearch']]
        for klass in klasses:
            val=self._getValue(klass,name)
            if val is not None:
                if isinstance(val,list) or isinstance(val,tuple):
                    vals.extend(val)
                else:
                    vals.append(val)
        return vals
        
        
class ClassSettingsMixin(object):
    def __init__(self,defaults=None):
        hier=[klass for klass in getHierarchy(self) if klass!=ClassSettingsMixin]
        self.settings=SettingsProxy(hier)


##### Testing stuff
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

class Vehicle(ClassSettingsMixin):
    defaultsettings={'wheels':0,
                     'doors':0,
                     'wings':'no wings on this puppy',
                     'primes':[2,3,5,7],
                     }

class Truck(Vehicle):
    defaultsettings={'wheels':True,
                     'doors':True,
                     'primes':[11,13,17,19],
                     }

class PickupTruck(Truck):
    defaultsettings={'wheels':4,
                     'doors':2,
                     'primes':[23,29],
                     }

class ShortBedPickupTruck(Truck):
    pass

def testHierarchy():
    GlobalSettings.setDefaults({
        'MenuFrame':{'width':600,
                     'height':500,
                     },
        'Peppy':{'plugins':'hexedit-plugin,python-plugin,fundamental',
                 },
        'MajorMode':{'linenumbers':'True',
                     'wordwrap':'False',
                     },
        'PythonMode':{'wordwrap':'True',
                      },
        })
    vehicle=ShortBedPickupTruck()
    print getHierarchy(vehicle,debug=True)
    print getNameHierarchy(vehicle,debug=True)
    print vehicle.settings.wheels
    vehicle.settings.mudflaps=True
    vehicle.settings.wheels=6
    print vehicle.settings._getDefaults()
    print vehicle.settings._getUser()
    print vehicle.settings._getAll()
    print vehicle.settings.wings
    print vehicle.settings.primes
    print vehicle.settings._getList('primes')
    print vehicle.settings._getList('wheels')
    
class SettingsMixin(object):
    def __init__(self):
        pass

class Plant(SettingsMixin):
    settings=['roots','branches','leaves','fruit']
    roots=True

    def __init__(self):
        self.branches=False
        self.leaves=False
        self.fruit=False
        
class Tree(Plant):
    def __init__(self):
        self.branches=True
        self.leaves=True

class OrangeTree(Tree):
    settings=['company']
    fruit="tangerines"
    
    def __init__(self):
        self.fruit="oranges"
        self.company="Tropicana"

def testSettingMixin():
    tree=OrangeTree()
    print tree.fruit
    print tree.__class__.fruit
    print tree.settings
    print tree.company


if __name__=='__main__':
    testHierarchy()
    #testSettingMixin()
