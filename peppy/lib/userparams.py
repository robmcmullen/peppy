#-----------------------------------------------------------------------------
# Name:        userparams.py
# Purpose:     class attribute preferences and serialization
#
# Author:      Rob McMullen
#
# Created:     2007
# RCS-ID:      $Id: $
# Copyright:   (c) 2007 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""Helpers to create editing widgets for user parameters.
"""

import os, struct, time, re, types, copy
from cStringIO import StringIO
from ConfigParser import ConfigParser
import locale

import wx
import wx.stc
from wx.lib.pubsub import Publisher
from wx.lib.evtmgr import eventManager
from wx.lib.scrolledpanel import ScrolledPanel
from wx.lib.filebrowsebutton import *

try:
    from peppy.debug import *
except:
    def dprint(txt=""):
        print txt
        return True

    class debugmixin(object):
        debuglevel = 0
        def dprint(self, txt):
            if self.debuglevel > 0:
                dprint(txt)
            return True


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

    # For i18n support, load your i18n conversion stuff and change
    # these class attributes
    yes_values = ["yes", "true", "1"]
    no_values = ["no", "false", "0"]
    
    def getCtrl(self, parent, initial=None):
        ctrl = wx.CheckBox(parent, -1, "")
        return ctrl

    def textToValue(self, text):
        text = Param.textToValue(self, text).lower()
        if text in self.yes_values:
            return True
        return False

    def valueToText(self, value):
        if value:
            return self.yes_values[0]
        return self.no_values[0]

    def setValue(self, ctrl, value):
        ctrl.SetValue(value)

    def getValue(self, ctrl):
        return ctrl.GetValue()

class IntParam(Param):
    default = 0
    
    def textToValue(self, text):
        text = Param.textToValue(self, text)
        tmp = locale.atof(text)
        val = int(tmp)
        return val

    def setValue(self, ctrl, value):
        ctrl.SetValue(str(value))

    def getValue(self, ctrl):
        return int(ctrl.GetValue())

class FloatParam(Param):
    default = 0.0
    
    def textToValue(self, text):
        text = Param.textToValue(self, text)
        val = locale.atof(text)
        return val

    def setValue(self, ctrl, value):
        ctrl.SetValue(str(value))

    def getValue(self, ctrl):
        return float(ctrl.GetValue())

class StrParam(Param):
    default = ""
    pass

class DateParam(Param):
    default = wx.DateTime().Today()
    
    def getCtrl(self, parent, initial=None):
        dpc = wx.DatePickerCtrl(parent, size=(120,-1),
                                style=wx.DP_DROPDOWN | wx.DP_SHOWCENTURY)
        return dpc

    def textToValue(self, text):
        date_pattern = "(\d+)\D+(\d+)\D+(\d+)"
        match = re.search(date_pattern, text)
        if match:
            assert self.dprint("ymd = %d/%d/%d" % (int(match.group(1)),
                                                   int(match.group(2)),
                                                   int(match.group(3))))
            t = time.mktime([int(match.group(1)), int(match.group(2)),
                             int(match.group(3)), 12, 0, 0, 0, 0, 0])
            dt = wx.DateTimeFromTimeT(t)
        else:
            dt = wx.DateTime()
            dt.Today()
        assert self.dprint(dt)
        return dt

    def valueToText(self, dt):
        assert self.dprint(dt)
        text = "{ %d , %d , %d }" % (dt.GetYear(), dt.GetMonth() + 1,
                                     dt.GetDay())
        return text

    def getValue(self, ctrl):
        return ctrl.GetValue()

class DirParam(Param):
    default = os.path.dirname(os.getcwd())
    
    def getCtrl(self, parent, initial=None):
        if initial is None:
            initial = os.getcwd()
        c = DirBrowseButton2(parent, -1, size=(300, -1),
                            labelText = '', startDirectory=initial)
        return c

    def setValue(self, ctrl, value):
        ctrl.SetValue(os.path.normpath(value))

class PathParam(DirParam):
    default = os.getcwd()
    
    def getCtrl(self, parent, initial=None):
        if initial is None:
            initial = os.getcwd()
        c = FileBrowseButton(parent, -1, size=(300, -1),
                                        labelText = '',
                                        startDirectory=initial,
                                        changeCallback = self.callback)
        return c

    def callback(self, evt):
        # On MSW, a fake object can be sent to the callback, so check
        # to see if it is a real event before using it.
        if not hasattr(evt, 'GetEventObject'):
            evt.Skip()
            return
        
##        ctrl = evt.GetEventObject()
##        value = evt.GetString()
##        if value:
##            dprint('FileBrowseButtonWithHistory: %s\n' % value)
##            history = ctrl.GetHistory()
##            if value not in history:
##                history.append(value)
##                ctrl.SetHistory(history)
##                ctrl.GetHistoryControl().SetStringSelection(value)
        evt.Skip()

class ChoiceParam(Param):
    def __init__(self, keyword, choices, initial=None):
        Param.__init__(self, keyword)
        self.choices = choices
        if initial is not None:
            self.default = initial
        else:
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
        #dprint("%s in %s" % (value, self.choices))
        try:
            index = self.choices.index(value)
        except ValueError:
            index = 0
        ctrl.SetSelection(index)

    def getValue(self, ctrl):
        index = ctrl.GetSelection()
        return self.choices[index]

class IndexChoiceParam(Param):
    def __init__(self, keyword, choices):
        Param.__init__(self, keyword)
        self.choices = choices
        self.default = choices[0]

    def getCtrl(self, parent, initial=None):
        ctrl = wx.Choice(parent , -1, (100, 50), choices = self.choices)
        return ctrl

    def textToValue(self, text):
        text = Param.textToValue(self, text)
        tmp = locale.atof(text)
        val = int(tmp)
        return val

    def setValue(self, ctrl, value):
        if value >= len(self.choices):
            value = 0
        ctrl.SetSelection(value)

    def getValue(self, ctrl):
        index = ctrl.GetSelection()
        return index

class KeyedIndexChoiceParam(IndexChoiceParam):
    def __init__(self, keyword, choices):
        Param.__init__(self, keyword)
        self.choices = [entry[1] for entry in choices]
        self.keys = [entry[0] for entry in choices]
        self.default = choices[0]

    def getCtrl(self, parent, initial=None):
        ctrl = wx.Choice(parent , -1, (100, 50), choices = self.choices)
        return ctrl

    def textToValue(self, text):
        text = Param.textToValue(self, text)
        tmp = locale.atof(text)
        val = int(tmp)
        try:
            index = self.keys.index(val)
        except ValueError:
            index = 0
        return index

    def valueToText(self, value):
        return str(self.keys[value])






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
    

class GlobalPrefs(debugmixin):
    debuglevel = 0
    
    default={}
    params = {}
    convert_already_seen = {}
    
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
        p = GlobalPrefs.params
        for section, defaults in defs.iteritems():
            if section not in d:
                d[section] = {}
            d[section].update(defaults)
            if section not in p:
                p[section] = {}

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
                params = {}
                if hasattr(klass,'default_classprefs'):
                    for p in klass.default_classprefs:
                        defs[p.keyword] = p.default
                        params[p.keyword] = p
                GlobalPrefs.default[klass.__name__]=defs
                GlobalPrefs.params[klass.__name__] = params
            else:
                # we've loaded application-specified defaults for this
                # class before, but haven't actually checked the
                # class.  Merge them in without overwriting the
                # existing prefs.
                #print "!!!!! missed %s" % klass
                if hasattr(klass,'default_classprefs'):
                    gd = GlobalPrefs.default[klass.__name__]
                    gp = GlobalPrefs.params[klass.__name__]
                    for p in klass.default_classprefs:
                        if p.keyword not in gd:
                            gd[p.keyword] = p.default
                        if p.keyword not in gp:
                            gp[p.keyword] = p
                    
            if klass.__name__ not in GlobalPrefs.user:
                GlobalPrefs.user[klass.__name__]={}
        if GlobalPrefs.debuglevel > 1: dprint("default: %s" % GlobalPrefs.default)
        if GlobalPrefs.debuglevel > 1: dprint("user: %s" % GlobalPrefs.user)

    @staticmethod
    def findParam(section, option):
        params = GlobalPrefs.params
        if section in params and option in params[section]:
            param = params[section][option]
        elif section in GlobalPrefs.name_hierarchy:
            # Need to march up the class hierarchy to find the correct
            # Param
            klasses=GlobalPrefs.name_hierarchy[section]
            #dprint(klasses)
            param = None
            for name in klasses[1:]:
                if name in params and option in params[name]:
                    param = params[name][option]
                    break
        else:
            dprint("Unknown configuration %s[%s]" % (section, option))
            return None
        if GlobalPrefs.debuglevel > 0: dprint("Found %s for %s in class %s" % (param.__class__.__name__, option, section))
        return param

    @staticmethod
    def readConfig(fh):
        cfg=ConfigParser()
        cfg.optionxform=str
        cfg.readfp(fh)
        for section in cfg.sections():
            d={}
            for option, text in cfg.items(section):
                # NOTE! text will be converted later, after all
                # plugins are loaded and we know what type each
                # parameter is supposed to be
                d[option]=text
            if section in GlobalPrefs.user:
                GlobalPrefs.user[section].update(d)
            else:
                GlobalPrefs.user[section]=d

    @staticmethod
    def convertConfig():
        # Need to copy dict to temporary one, because BadThings happen
        # while trying to update a dictionary while iterating on it.
        if GlobalPrefs.debuglevel > 0: dprint("before: %s" % GlobalPrefs.user)
        if GlobalPrefs.debuglevel > 0: dprint("name_hierarchy: %s" % GlobalPrefs.name_hierarchy)
        if GlobalPrefs.debuglevel > 0: dprint("params: %s" % GlobalPrefs.params)
        d = {}
        for section, options in GlobalPrefs.user.iteritems():
            d[section] = {}
            
            if section not in GlobalPrefs.params or section in GlobalPrefs.convert_already_seen or not GlobalPrefs.params[section]:
                # Don't process values before the param definition for
                # the class is loaded.  Copy the existing text values
                # and defer the conversion till the next time
                # convertConfig is called.
                if GlobalPrefs.debuglevel > 0:
                    if section not in GlobalPrefs.params:
                        dprint("haven't loaded class %s" % section)
                    elif section in GlobalPrefs.convert_already_seen:
                        dprint("already converted class %s" % section)
                    elif not GlobalPrefs.params[section]:
                        dprint("only defaults loaded, haven't loaded Params for class %s" % section)
                d[section].update(options)
                continue
            
            GlobalPrefs.convert_already_seen[section] = True
                
            for option, text in options.iteritems():
                param = GlobalPrefs.findParam(section, option)
                if param is not None:
                    val = param.textToValue(text)
                    if GlobalPrefs.debuglevel > 0: dprint("Converted %s to %s(%s) for %s[%s]" % (text, val, type(val), section, option))
                else:
                    val = text
                d[section][option] = val
        GlobalPrefs.user = d
        if GlobalPrefs.debuglevel > 0: dprint("after: %s" % GlobalPrefs.user)

        # Save a copy so we can tell if the user changed anything
        GlobalPrefs.save_user = copy.deepcopy(GlobalPrefs.user)

    @staticmethod
    def isUserConfigChanged():
        d = GlobalPrefs.user
        saved = GlobalPrefs.save_user
        for section, options in d.iteritems():
            if GlobalPrefs.debuglevel > 0: dprint("checking section %s" % section)
            if section not in saved:
                # If we have a new section that didn't exist when we
                # loaded the file, something's changed
                if GlobalPrefs.debuglevel > 0: dprint("  new section %s!  Change needs saving." % (section))
                return True
            for option, val in options.iteritems():
                if option not in saved[section]:
                    # We have a new option in an existing section.
                    # It's changed.
                    if GlobalPrefs.debuglevel > 0: dprint("  new option %s in section %s!  Change needs saving." % (option, section))
                    return True
                if val != saved[section][option]:
                    # The value itself has changed.
                    if GlobalPrefs.debuglevel > 0: dprint("  new value %s for %s[%s]." % (val, section, option))
                    return True
                if GlobalPrefs.debuglevel > 0: dprint("  nope, %s[%s] is still %s" % (section, option, val))
        # For completeness, we should check to see if an option has
        # been removed, but currently the interface doesn't provide
        # that ability.
        if GlobalPrefs.debuglevel > 0: dprint("nope, user configuration hasn't changed.")
        return False

    @staticmethod
    def configToText():
        if GlobalPrefs.debuglevel > 0: dprint("Saving user configuration: %s" % GlobalPrefs.user)
        lines = ["# Automatically generated file!  Do not edit -- use one of the following",
                 "# files instead:",
                 "#",
                 "# peppy.cfg        For general configuration on all platforms",
                 "# [platform].cfg   For configuration on a specific platform, where [platform]",
                 "#                  is one of the platforms returned by the command",
                 "#                  python -c 'import platform; print platform.system()'",
                 "# [machine].cfg    For configuration on a specific machine, where [machine]",
                 "#                  is the hostname as returned by the command",
                 "#                  python -c 'import platform; print platform.node()'",
                 "",
                 ]
        
        saved = GlobalPrefs.save_user
        sections = GlobalPrefs.user.keys()
        sections.sort()
        for section in sections:
            options = GlobalPrefs.user[section]
            printed_section = False # flag to indicate if need to print header
            if options:
                keys = options.keys()
                keys.sort()
                for option in keys:
                    val = options[option]
                    param = GlobalPrefs.findParam(section, option)
                    if param is None:
                        dprint("Found a None param: %s[%s] = %s" % (section, option, val))
                        continue
                    if not printed_section:
                        lines.append("[%s]" % section)
                        printed_section = True
                    lines.append("%s = %s" % (option, param.valueToText(val)))
                lines.append("")
        text = os.linesep.join(lines)
        if GlobalPrefs.debuglevel > 0: dprint(text)
        return text
        

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
                assert self.dprint("checking %s for %s in user dict %s" % (klass, name, d[klass]))
                if klass in d and name in d[klass]:
                    return d[klass][name]
        if default:
            d=GlobalPrefs.default
            for klass in klasses:
                assert self.dprint("checking %s for %s in default dict %s" % (klass, name, d[klass]))
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
        #dprint('Bases: %s' % str(bases))
        expanded = [cls]
        for base in bases:
            expanded.extend(getClassHierarchy(base))
        #dprint('New bases: %s' % str(expanded))
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
        ScrolledPanel.__init__(self, parent, -1, size=(500,-1),
                               pos=(9000,9000))
        self.parent = parent
        self.obj = obj
        
        self.sizer = wx.GridBagSizer(2,5)

        self.ctrls = {}
        self.orig = {}
        self.create()

        self.SetSizer(self.sizer)
        self.Layout()

    def Layout(self):
        ScrolledPanel.Layout(self)
        self.SetupScrolling()
        self.Scroll(0,0)
        
    def create(self):
        row = 0
        focused = False
        hier = self.obj.classprefs._getMRO()
        self.dprint(hier)
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
                    self.dprint("keyword %s: val = %s(%s)" % (param.keyword, val, type(val)))
                    param.setValue(ctrl, val)
                    
                    self.ctrls[param.keyword] = ctrl
                    self.orig[param.keyword] = val
                    if not focused:
                        self.SetFocus()
                        ctrl.SetFocus()
                        focused = True

                row += 1
        
    def update(self):
        hier = self.obj.classprefs._getMRO()
        self.dprint(hier)
        updated = {}
        for cls in hier:
            if 'default_classprefs' not in dir(cls):
                continue
            
            for param in cls.default_classprefs:
                if param.keyword in updated:
                    # Don't update with value in superclass
                    continue

                if param.isSettable():
                    # It's possible that a keyword won't have an
                    # associated control, so only deal with those
                    # controls that are settable
                    ctrl = self.ctrls[param.keyword]
                    val = param.getValue(ctrl)
                    if val != self.orig[param.keyword]:
                        self.dprint("%s has changed from %s(%s) to %s(%s)" % (param.keyword, self.orig[param.keyword], type(self.orig[param.keyword]), val, type(val)))
                        self.obj.classprefs._set(param.keyword, val)
                    updated[param.keyword] = True

class PrefClassTree(wx.TreeCtrl, debugmixin):
    def __init__(self, parent, style=wx.TR_HAS_BUTTONS):
        if wx.Platform != '__WXMSW__':
            style |= wx.TR_HIDE_ROOT
        wx.TreeCtrl.__init__(self, parent, -1, size=(200,400), style=style)

        self.AddRoot("Preferences")
        self.SetPyData(self.GetRootItem(), None)
        
        self.setIconStorage()
        self.setIconForItem(self.GetRootItem())

        self.class_to_item = {}

    def setIconStorage(self):
        pass

    def setIconForItem(self, item, cls=None):
        pass

    def ExpandAll(self):
        self.ExpandAllChildren(self.GetFirstVisibleItem())

    def ensureClassVisible(self, cls):
        item = self.class_to_item[cls]
        self.EnsureVisible(item)
        self.SelectItem(item)

    def findParent(self, mro, parent=None):
        if parent is None:
            parent = self.GetRootItem()
        if len(mro)==0:
            return parent
        cls = mro.pop()
        if 'default_classprefs' not in dir(cls):
            # ignore intermediate subclasses that don't have any
            # default settings
            return self.findParent(mro, parent)
        name = cls.__name__
        item, cookie = self.GetFirstChild(parent)
        while item:
            if self.GetItemText(item) == name:
                return self.findParent(mro, item)
            item, cookie = self.GetNextChild(parent, cookie)
        return None
        
    def appendClass(self, cls):
        assert self.dprint("class=%s mro=%s" % (cls, cls.classprefs._getMRO()))
        mro = cls.classprefs._getMRO()
        parent = self.findParent(mro[1:])
        if parent is not None:
            assert self.dprint("  found parent = %s" % self.GetItemText(parent))
            item = self.AppendItem(parent, mro[0].__name__)
            self.setIconForItem(item, cls)
            self.SetPyData(item, cls)
            self.class_to_item[cls] = item

##        self.Bind(wx.EVT_TREE_ITEM_EXPANDED, self.OnItemExpanded, self.tree)
##        self.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.OnItemCollapsed, self.trees)
##        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged, self.tree)
##        self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.OnBeginEdit, self.tree)
##        self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.OnEndEdit, self.tree)
##        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate, self.tree)

##        self.tree.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
##        self.tree.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
##        self.tree.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)

    def sortRecurse(self, parent=None):
        if parent is None:
            parent = self.GetRootItem()
        self.SortChildren(parent)
        item, cookie = self.GetFirstChild(parent)
        while item:
            self.sortRecurse(item)
            item, cookie = self.GetNextChild(parent, cookie)

    def OnCompareItems(self, item1, item2):
        t1 = self.GetItemText(item1)
        t2 = self.GetItemText(item2)
        if t1 < t2: return -1
        if t1 == t2: return 0
        return 1

class PrefDialog(wx.Dialog):
    dialog_title = "Preferences"
    static_title = "This is a placeholder for the Preferences dialog"
    
    def __init__(self, parent, obj, title=None):
        if title is None:
            title = self.dialog_title
        wx.Dialog.__init__(self, parent, -1, title,
                           size=(700, 500), pos=wx.DefaultPosition, 
                           style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        self.obj = obj

        sizer = wx.BoxSizer(wx.VERTICAL)

        if self.static_title:
            label = wx.StaticText(self, -1, self.static_title)
            sizer.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        self.splitter = wx.SplitterWindow(self)
        self.splitter.SetMinimumPaneSize(50)
        self.tree = self.createTree(self.splitter)
        self.populateTree()
        
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged, self.tree)

        self.pref_panels = {}
        pref = self.createPanel(self.obj.__class__)

        self.splitter.SplitVertically(self.tree, pref, -500)
        sizer.Add(self.splitter, 1, wx.EXPAND)

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

    def createTree(self, parent):
        tree = PrefClassTree(parent)
        return tree

    def populateTree(self, cls=ClassPrefs):
        classes = getAllSubclassesOf(cls)
        for cls in classes:
            self.tree.appendClass(cls)
        self.tree.sortRecurse()
        self.tree.ensureClassVisible(self.obj.__class__)
        
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
        # Look at all the panels that have been created: this gives us
        # an upper bound on what may have changed.
        for cls, pref in self.pref_panels.iteritems():
            pref.update()


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

    class TestA(ClassPrefs):
        default_classprefs = (
            BoolParam("testa"),
            )

    class TestB(TestA):
        default_classprefs = (
            PathParam("testpath"),
            )
        pass

    class TestC(TestA):
        pass
   
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

    # Close down the dialog on a button press
    import sys
    dlg.Bind(wx.EVT_BUTTON, lambda e: sys.exit())

    app.MainLoop()
    
