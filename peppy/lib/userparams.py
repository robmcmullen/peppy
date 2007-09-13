# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Helpers to create editing widgets for user parameters.
"""

import os, struct, time, re, types
from cStringIO import StringIO
from ConfigParser import ConfigParser
import locale

import wx
import wx.stc
from wx.lib.pubsub import Publisher
from wx.lib.evtmgr import eventManager
from wx.lib.scrolledpanel import ScrolledPanel
from wx.lib.filebrowsebutton import FileBrowseButtonWithHistory, DirBrowseButton

try:
    from peppy.debug import *
except:
    def dprint(txt=""):
        print txt

    class debugmixin(object):
        debuglevel = 0
        def dprint(self, txt):
            if self.debuglevel > 0:
                dprint(txt)

if '_' not in dir():
    global _
    _ = str


class DirBrowseButton2(DirBrowseButton):
    """Update to dir browse button to browse to the currently set
    directory instead of always using the initial directory.
    """
    def OnBrowse(self, ev = None):
        current = self.GetValue()
        directory = os.path.split(current)
        if os.path.isdir( current):
            directory = current
            current = ''
        elif directory and os.path.isdir( directory[0] ):
            current = directory[1]
            directory = directory [0]
        else:
            directory = self.startDirectory

        style=0

        if not self.newDirectory:
          style |= wx.DD_DIR_MUST_EXIST

        dialog = self.dialogClass(self,
                                  message = self.dialogTitle,
                                  defaultPath = directory,
                                  style = style)

        if dialog.ShowModal() == wx.ID_OK:
            self.SetValue(dialog.GetPath())
        dialog.Destroy()
    


class Param(debugmixin):
    def __init__(self, keyword, default=None):
        self.keyword = keyword
        self.category = None
        if default is not None:
            self.default = default

    def isSettable(self):
        return True

    def getCtrl(self, parent, initial=None):
        ctrl = wx.TextCtrl(parent, -1, size=(125, -1),
                           style=wx.TE_PROCESS_ENTER)
        return ctrl

    def textToValue(self, text):
        if text.startswith("'") or text.startswith('"'):
            text = text[1:]
        if text.endswith("'") or text.endswith('"'):
            text = text[:-1]
        return text

    def valueToText(self, value):
        if isinstance(value, str):
            value = '"%s"' % value
        return value

    def setValue(self, ctrl, value):
        ctrl.SetValue(value)

    def getValue(self, ctrl):
        return str(ctrl.GetValue())

class ReadOnlyParam(debugmixin):
    def __init__(self, keyword, default=None):
        self.keyword = keyword
        self.category = None
        if default is not None:
            self.default = default

    def isSettable(self):
        return False

class ParamCategory(Param):
    def __init__(self, keyword, default=None):
        self.keyword = keyword
        self.category = keyword

    def isSettable(self):
        return False

    def getCtrl(self, parent, initial=None):
        box = wx.StaticBox(parent, -1, self.keyword)
        ctrl = wx.StaticBoxSizer(box, wx.VERTICAL)
        return ctrl

class BoolParam(Param):
    default = False
    
    def getCtrl(self, parent, initial=None):
        ctrl = wx.CheckBox(parent, -1, "")
        return ctrl

    def textToValue(self, text):
        text = Param.textToValue(self, text).lower()
        if text[0:1] in ['1', 't', 'y']:
            return True
        return False

    def valueToText(self, value):
        if value:
            return "1"
        return "0"

    def setValue(self, ctrl, value):
        ctrl.SetValue(value)

class IntParam(Param):
    default = 0
    
    def textToValue(self, text):
        text = Param.textToValue(self, text)
        tmp = locale.atof(text)
        dprint(tmp)
        val = int(tmp)
        return str(val)

    def setValue(self, ctrl, value):
        ctrl.SetValue(str(value))

    def getValue(self, ctrl):
        return int(ctrl.GetValue())

class FloatParam(Param):
    default = 0.0
    
    def textToValue(self, text):
        text = Param.textToValue(self, text)
        val = locale.atof(text)
        return str(val)

    def setValue(self, ctrl, value):
        ctrl.SetValue(str(value))

    def getValue(self, ctrl):
        return float(ctrl.GetValue())

class StrParam(Param):
    default = ""
    pass

class DateParam(Param):
    default = ""
    
    def getCtrl(self, parent, initial=None):
        dpc = wx.DatePickerCtrl(parent, size=(120,-1),
                                style=wx.DP_DROPDOWN | wx.DP_SHOWCENTURY)
        return dpc

    def textToValue(self, text):
        date_pattern = "(\d+)\D+(\d+)\D+(\d+)"
        match = re.search(date_pattern, text)
        if match:
            dprint("ymd = %d/%d/%d" % (int(match.group(1)),
                                       int(match.group(2)),
                                       int(match.group(3))))
            t = time.mktime([int(match.group(1)), int(match.group(2)),
                             int(match.group(3)), 12, 0, 0, 0, 0, 0])
            dt = wx.DateTimeFromTimeT(t)
        else:
            dt = wx.DateTime()
            dt.Today()
        dprint(dt)
        return dt

    def valueToText(self, dt):
        dprint(dt)
        text = "{ %d , %d , %d }" % (dt.GetYear(), dt.GetMonth() + 1,
                                     dt.GetDay())
        return text

    def getValue(self, ctrl):
        return ctrl.GetValue()

class DirParam(Param):
    default = ""
    
    def getCtrl(self, parent, initial=None):
        if initial is None:
            initial = os.getcwd()
        c = DirBrowseButton2(parent, -1, size=(300, -1),
                            labelText = '', startDirectory=initial)
        return c

    def setValue(self, ctrl, value):
        ctrl.SetValue(os.path.normpath(value))

class PathParam(DirParam):
    default = ""
    
    def getCtrl(self, parent, initial=None):
        if initial is None:
            initial = os.getcwd()
        c = FileBrowseButtonWithHistory(parent, -1, size=(300, -1),
                                        labelText = '',
                                        startDirectory=initial,
                                        changeCallback = self.callback)
        return c

    def callback(self, evt):
        dprint(evt)
        # On MSW, a fake object can be sent to the callback, so check
        # to see if it is a real event before using it.
        if not hasattr(evt, 'GetEventObject'):
            return
        
        ctrl = evt.GetEventObject()
        value = evt.GetString()
        if not value:
            return
        dprint('FileBrowseButtonWithHistory: %s\n' % value)
        history = ctrl.GetHistory()
        if value not in history:
            history.append(value)
            ctrl.SetHistory(history)
            ctrl.GetHistoryControl().SetStringSelection(value)

class ChoiceParam(Param):
    def __init__(self, keyword, choices):
        Param.__init__(self, keyword)
        self.choices = choices
        self.default = choices[0]

    def getCtrl(self, parent, initial=None):
        ctrl = wx.Choice(parent , -1, (100, 50), choices = self.choices)
        return ctrl

    def textToValue(self, text):
        if text.startswith("'") or text.startswith('"'):
            text = text[1:]
        if text.endswith("'") or text.endswith('"'):
            text = text[:-1]
        return text

    def setValue(self, ctrl, value):
        dprint("%s in %s" % (value, self.choices))
        try:
            index = self.choices.index(value)
        except ValueError:
            index = 0
        ctrl.SetSelection(index)

    def getValue(self, ctrl):
        index = ctrl.GetSelection()
        return self.choices[index]






parentclasses={}
skipclasses=['debugmixin','ClassPrefs','object']

def getAllSubclassesOf(parent=debugmixin, subclassof=None):
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
        subs=getAllSubclassesOf(parent=kls)
        if len(subs)>0:
            subclasses.extend(subs)
    return subclasses

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
        if debug: dprint("Found class hierarchy: %s" % hierarchy)
    else:
        hierarchy=[k for k in parents(klass) if k.__name__ not in skipclasses and not k.__name__.endswith('Mixin') and not k.__module__.startswith('wx.')]
        if debug: dprint("Created class hierarchy: %s" % hierarchy)
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
    if debug:  dprint("name hierarchy: %s" % names)
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
    

class GlobalPrefs(object):
    debug=False
    
    default={}
    user={}
    name_hierarchy={}
    class_hierarchy={}
    magic_conversion=True
    
    @staticmethod
    def setDefaults(defs):
        """Set system defaults to the dict of dicts.

        The GlobalPrefs.default values are used as failsafe defaults
        -- they are only used if the user defaults aren't found.

        The outer layer dict is class name, the inner dict has
        name/value pairs.  Note that the value's type should match
        with the default_classprefs, or there'll be trouble.
        """
        d = GlobalPrefs.default
        for section, defaults in defs.iteritems():
            if section not in d:
                d[section] = {}
            d[section].update(defaults)

    @staticmethod
    def addHierarchy(leaf, classhier, namehier):
        if leaf not in GlobalPrefs.class_hierarchy:
            GlobalPrefs.class_hierarchy[leaf]=classhier
        if leaf not in GlobalPrefs.name_hierarchy:
            GlobalPrefs.name_hierarchy[leaf]=namehier

    @staticmethod
    def setupHierarchyDefaults(klasshier):
        for klass in klasshier:
            if klass.__name__ not in GlobalPrefs.default:
                defs={}
                if hasattr(klass,'default_classprefs'):
                    for p in klass.default_classprefs:
                        defs[p.keyword] = p.default
                GlobalPrefs.default[klass.__name__]=defs
            else:
                # we've loaded application-specified defaults for this
                # class before, but haven't actually checked the
                # class.  Merge them in without overwriting the
                # existing prefs.
                #print "!!!!! missed %s" % klass
                if hasattr(klass,'default_classprefs'):
                    g=GlobalPrefs.default[klass.__name__]
                    for p in klass.default_classprefs:
                        if p.keyword not in g:
                            g[p.keyword] = p.default
                    
            if klass.__name__ not in GlobalPrefs.user:
                GlobalPrefs.user[klass.__name__]={}
        if GlobalPrefs.debug: dprint("default: %s" % GlobalPrefs.default)
        if GlobalPrefs.debug: dprint("user: %s" % GlobalPrefs.user)

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
    def readConfig(fh):
        cfg=ConfigParser()
        cfg.optionxform=str
        cfg.readfp(fh)
        for section in cfg.sections():
            d={}
            for option,value in cfg.items(section):
                if GlobalPrefs.magic_conversion:
                    d[option]=GlobalPrefs.convertValue(section,option,value)
                else:
                    d[option]=value
            GlobalPrefs.user[section]=d

    @staticmethod
    def saveConfig(filename):
        print "Saving user configuration: %s" % GlobalPrefs.user

class PrefsProxy(debugmixin):
    """Dictionary-like object to provide global prefs to a class.

    Implements a dictionary that returns a value for a keyword based
    on the class hierarchy.  Each class will define a group of
    prefs and default values for each of those prefs.  The class
    hierarchy then defines the search order if a setting is not found
    in a child class -- the search proceeds up the class hierarchy
    looking for the desired keyword.
    """
    debuglevel=0
    
    def __init__(self,hier):
        names=[k.__name__ for k in hier]
        self.__dict__['_startSearch']=names[0]
        GlobalPrefs.addHierarchy(names[0], hier, names)
        GlobalPrefs.setupHierarchyDefaults(hier)

    def __getattr__(self,name):
        return self._get(name)

    def __call__(self, name):
        return self._get(name)

    def _get(self, name, user=True, default=True):
        klasses=GlobalPrefs.name_hierarchy[self.__dict__['_startSearch']]
        if user:
            d=GlobalPrefs.user
            for klass in klasses:
                assert self.dprint("checking %s for %s in user dict %s" % (klass, name, d))
                if klass in d and name in d[klass]:
                    return d[klass][name]
        if default:
            d=GlobalPrefs.default
            for klass in klasses:
                assert self.dprint("checking %s for %s in default dict %s" % (klass, name, d))
                if klass in d and name in d[klass]:
                    return d[klass][name]

        klasses=GlobalPrefs.class_hierarchy[self.__dict__['_startSearch']]
        for klass in klasses:
            assert self.dprint("checking %s for %s in default_classprefs" % (klass,name))
            if hasattr(klass,'default_classprefs') and name in klass.default_classprefs:
                return klass.default_classprefs[name]
        return None

    def __setattr__(self,name,value):
        GlobalPrefs.user[self.__dict__['_startSearch']][name]=value

    _set = __setattr__

    def _del(self, name):
        del GlobalPrefs.user[self.__dict__['_startSearch']][name]
        
    def _getValue(self,klass,name):
        d=GlobalPrefs.user
        if klass in d and name in d[klass]:
            return d[klass][name]
        d=GlobalPrefs.default
        if klass in d and name in d[klass]:
            return d[klass][name]
        return None
    
    def _getDefaults(self):
        return GlobalPrefs.default[self.__dict__['_startSearch']]

    def _getUser(self):
        return GlobalPrefs.user[self.__dict__['_startSearch']]

    def _getAll(self):
        d=GlobalPrefs.default[self.__dict__['_startSearch']].copy()
        d.update(GlobalPrefs.user[self.__dict__['_startSearch']])
        return d

    def _getList(self,name):
        vals=[]
        klasses=GlobalPrefs.name_hierarchy[self.__dict__['_startSearch']]
        for klass in klasses:
            val=self._getValue(klass,name)
            if val is not None:
                if isinstance(val,list) or isinstance(val,tuple):
                    vals.extend(val)
                else:
                    vals.append(val)
        return vals

    def _getMRO(self):
        return [cls for cls in GlobalPrefs.class_hierarchy[self.__dict__['_startSearch']]]
        

class ClassPrefsMetaClass(type):
    def __init__(cls, name, bases, attributes):
        """Add prefs attribute to class attributes.

        All classes of the created type will point to the same
        prefs object.  Perhaps that's a 'duh', since prefs is a
        class attribute, but it is worth the reminder.  Everything
        accessed through self.prefs changes the class prefs.
        Instance prefs are maintained by the class itself.
        """
        dprint('Bases: %s' % str(bases))
        expanded = [cls]
        for base in bases:
            expanded.extend(getClassHierarchy(base))
        dprint('New bases: %s' % str(expanded))
        # Add the prefs class attribute
        cls.classprefs = PrefsProxy(expanded)

class ClassPrefs(object):
    """Base class to extend in order to support class prefs.

    Uses the L{ClassPrefsMetaClass} to provide automatic support
    for the prefs class attribute.
    """
    __metaclass__ = ClassPrefsMetaClass


class PrefPanel(ScrolledPanel, debugmixin):
    """Panel that shows ui controls corresponding to all preferences
    """
    debuglevel = 0


    def __init__(self, parent, obj):
        ScrolledPanel.__init__(self, parent, -1, size=(500,-1))
        self.parent = parent
        self.obj = obj
        
        self.sizer = wx.GridBagSizer(2,5)

        self.ctrls = {}
        self.create()

        self.SetSizer(self.sizer)
        self.Layout()

    def Layout(self):
        dprint()
        ScrolledPanel.Layout(self)
        self.SetAutoLayout(1)
        self.SetupScrolling()
        self.Scroll(0,0)
        
    def create(self):
        row = 0
        focused = False
        hier = self.obj.classprefs._getMRO()
        dprint(hier)
        for cls in hier:
            if 'default_classprefs' not in dir(cls):
                continue
            
            for param in cls.default_classprefs:
                if param.keyword in self.ctrls:
                    # Don't put another control if it exists in a superclass
                    continue
                
                title = wx.StaticText(self, -1, param.keyword)
                self.sizer.Add(title, (row,0))

                if param.isSettable():
                    ctrl = param.getCtrl(self)
                    self.sizer.Add(ctrl, (row,1), flag=wx.EXPAND)
                    
                    val = self.obj.classprefs(param.keyword)
                    param.setValue(ctrl, val)
                    
                    self.ctrls[param.keyword] = ctrl
                    if not focused:
                        self.SetFocus()
                        ctrl.SetFocus()
                        focused = True

                row += 1
        
    def update(self):
        hier = self.obj.classprefs._getMRO()
        dprint(hier)
        updated = {}
        for cls in hier:
            if 'default_classprefs' not in dir(cls):
                continue
            
            for param in cls.default_classprefs:
                if param.keyword in updated:
                    # Don't update with value in superclass
                    continue
                
                val = self.obj.classprefs(param.keyword)
                dprint("updating %s = %s" % (param.keyword, val))
                ctrl = self.ctrls[param.keyword]
                param.setValue(ctrl, val)
                updated[param.keyword] = True

class PrefClassTree(wx.TreeCtrl):
    def __init__(self, parent, style=wx.TR_HAS_BUTTONS):
        if wx.Platform != '__WXMSW__':
            style |= wx.TR_HIDE_ROOT
        wx.TreeCtrl.__init__(self, parent, -1, size=(200,400), style=style)

        self.AddRoot("Preferences")
        self.SetPyData(self.GetRootItem(), None)
        
        self.setIconStorage()
        self.setIconForItem(self.GetRootItem())

    def setIconStorage(self):
        # FIXME: this isn't portable
        import peppy.lib.iconstorage as icons

        icons.getIconStorage().assign(self)

    def setIconForItem(self, item, cls=None):
        # FIXME: this isn't portable
        import peppy.lib.iconstorage as icons

        icon = None
        if item == self.GetRootItem():
            icon = icons.getIconStorage("icons/wrench.png")
        elif hasattr(cls, 'icon') and cls.icon is not None:
            icon = icons.getIconStorage(cls.icon)

        if icon is not None:
            self.SetItemImage(item, icon)

    def ExpandAll(self):
        self.ExpandAllChildren(self.GetFirstVisibleItem())

    def FindParent(self, mro, parent=None):
        if parent is None:
            parent = self.GetRootItem()
        if len(mro)==0:
            return parent
        cls = mro.pop()
        if 'default_classprefs' not in dir(cls):
            # ignore intermediate subclasses that don't have any
            # default settings
            return self.FindParent(mro, parent)
        name = cls.__name__
        item, cookie = self.GetFirstChild(parent)
        while item:
            if self.GetItemText(item) == name:
                return self.FindParent(mro, item)
            item, cookie = self.GetNextChild(parent, cookie)
        return None
        
    def AppendClass(self, cls):
        dprint("class=%s mro=%s" % (cls, cls.classprefs._getMRO()))
        mro = cls.classprefs._getMRO()
        parent = self.FindParent(mro[1:])
        if parent is not None:
            dprint("  found parent = %s" % self.GetItemText(parent))
            item = self.AppendItem(parent, mro[0].__name__)
            self.setIconForItem(item)
            self.SetPyData(item, cls)

##        self.Bind(wx.EVT_TREE_ITEM_EXPANDED, self.OnItemExpanded, self.tree)
##        self.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.OnItemCollapsed, self.trees)
##        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged, self.tree)
##        self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.OnBeginEdit, self.tree)
##        self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.OnEndEdit, self.tree)
##        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate, self.tree)

##        self.tree.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
##        self.tree.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
##        self.tree.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)

    def SortRecurse(self, parent=None):
        if parent is None:
            parent = self.GetRootItem()
        self.SortChildren(parent)
        item, cookie = self.GetFirstChild(parent)
        while item:
            self.SortRecurse(item)
            item, cookie = self.GetNextChild(parent, cookie)

    def applyRecurse(self, parent=None):
        if parent is None:
            parent = self.GetRootItem()
        cls = self.GetItemPyData(parent)
        if 'preference_dialog_settings' in dir(cls):
            for key, val in cls.preference_dialog_settings.iteritems():
                dprint("setting %s[%s]=%s" % (cls.__name__, key, val))
                cls.classprefs._set(key, val)
            cls.preference_dialog_settings.clear()
        item, cookie = self.GetFirstChild(parent)
        while item:
            self.applyRecurse(item)
            item, cookie = self.GetNextChild(parent, cookie)
    
    def OnCompareItems(self, item1, item2):
        t1 = self.GetItemText(item1)
        t2 = self.GetItemText(item2)
        if t1 < t2: return -1
        if t1 == t2: return 0
        return 1

class PrefDialog(wx.Dialog):
    def __init__(self, parent, obj, title="Preferences"):
        wx.Dialog.__init__(self, parent, -1, title,
                           size=wx.DefaultSize, pos=wx.DefaultPosition, 
                           style=wx.DEFAULT_DIALOG_STYLE)

        self.obj = obj

        sizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self, -1, _("This is a placeholder for the Preferences dialog"))
        sizer.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        self.splitter = wx.SplitterWindow(self)
        self.splitter.SetMinimumPaneSize(50)
        self.tree = self.createTree(self.obj.__class__)
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged, self.tree)

        self.pref_panels = {}
        pref = self.createPanel(self.obj.__class__)

        self.splitter.SplitVertically(self.tree, pref, -500)
        sizer.Add(self.splitter, 0, wx.EXPAND)

        btnsizer = wx.StdDialogButtonSizer()
        
        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Layout()

    def createTree(self, cls):
        tree = PrefClassTree(self.splitter)
        
        classes = getAllSubclassesOf(ClassPrefs)
        dprint(classes)
        for cls in classes:
            tree.AppendClass(cls)
        tree.SortRecurse()
        tree.ExpandAll()
        return tree
        
    def createPanel(self, cls):
        pref = PrefPanel(self.splitter, cls)
        self.pref_panels[cls] = pref
        return pref

    def OnSelChanged(self, evt):
        self.item = evt.GetItem()
        if self.item:
            cls = self.tree.GetItemPyData(self.item)
            if cls in self.pref_panels:
                pref = self.pref_panels[cls]
            else:
                pref = self.createPanel(cls)
            old = self.splitter.GetWindow2()
            self.splitter.ReplaceWindow(old, pref)
            old.Hide()
            pref.Show()
            pref.Layout()
        evt.Skip()

    def applyPreferences(self):
        self.tree.applyRecurse()


if __name__ == "__main__":
    class Test1(ClassPrefs):
        default_classprefs = (
            IntParam("test1", 5),
            FloatParam("testfloat", 6.0),
            IntParam("testbase1", 1),
            IntParam("testbase2", 2),
            IntParam("testbase3", 3),
            )
    
    class Test2(Test1):
        default_classprefs = (
            IntParam("test1", 7),
            FloatParam("testfloat", 6.0),
            StrParam("teststr", "BLAH!"),
            )

   
    t1 = Test1()
    t2 = Test2()

    print t1.classprefs.test1, t1.classprefs.testbase1
    print t2.classprefs.test1, t2.classprefs.testbase1

    t1.classprefs.testbase1 = 113
    
    print t1.classprefs.test1, t1.classprefs.testbase1
    print t2.classprefs.test1, t2.classprefs.testbase1
    
    t2.classprefs.testbase1 = 9874
    
    print t1.classprefs.test1, t1.classprefs.testbase1
    print t2.classprefs.test1, t2.classprefs.testbase1

    app = wx.PySimpleApp()

    dlg = PrefDialog(None, t1)
    dlg.Show(True)

    app.MainLoop()
    
