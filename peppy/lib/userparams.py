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
"""Helpers to create user preferences for class attribute defaults and
editing widgets for user modification of preferences.

This module is used to create preferences that can be easily saved to
configuration files.  It is designed to be class-based, not instance
based.

Classes need to inherit from ClassPrefs and then define a class
attribute called default_classprefs that is a tuple of Param objects.
Subclasses will inherit the preferences of their parent classes, and
can either redefine the defaults or add new parameters.  For example:

  class Vehicle(ClassPrefs):
      default_classprefs = (
          IntParam('wheels', 0, 'Number of wheels on the vehicle'),
          IntParam('doors', 0, 'Number of doors on the vehicle'),
          BoolParam('operational', True, 'Is it running?'),
          BoolParam('engine', False, 'Does it have a motor?'),
          )

  class Car(Vehicle):
      default_classprefs = (
          IntParam('wheels', 4),
          IntParam('doors', 4),
          BoolParam('engine', True),
          StrParam('license_state', '', 'State in which registered'),
          StrParam('license_plate', '', 'License plate number'),
          )

  class WxCar(wx.Window, Car):
      default_classprefs = (
          IntParam('pixel_height', 400),
          IntParam('pixel_width', 600),
          )

The metaclass for ClassPrefs processes the default_classprefs and adds
another class attribute called classprefs that is a proxy object into
a global preferences object.

The global preferences object GlobalPrefs uses the ConfigParser module
to serialize and unserialize user preferences.  Since the user
preferences are stored in text files, the Param objects turn the user
text into the expected type of the Param so that your python code only
has to deal with the expected type and doesn't have to do any conversion
itself.

The user configuration for the above example could look like this:

  [Vehicle]
  operational = False
  
  [Car]
  license_state = CA
  doors = 2
  
  [WxCar]
  pixel_width = 300
  pixel_height = 200

and the GlobalPrefs.readConfig method will parse the file,
interpreting the section name as the class.  It will set
Vehicle.classprefs.operational to be the boolean value False,
Car.classprefs.license_state to the string 'CA', Car.classprefs.doors to
the integer value 2, etc.

Your code doesn't need to know anything about the conversion from the
string to the expected type -- it's all handled by the ClassPrefs and
GlobalPrefs.

The PrefDialog class provides the user interface dialog to modify
class parameters.  It creates editing widgets that correspond to the
Param class -- for BoolParam it creates a checkbox, IntParam a text
entry widget, ChoiceParam a pulldown list, etc.  The help text is
displayed as a tooltip over the editing widget.  User subclasses of
Param are possible as well.

"""

import os, sys, struct, time, re, types, copy
from cStringIO import StringIO
from ConfigParser import ConfigParser
import locale

import wx
import wx.stc
from wx.lib.pubsub import Publisher
from wx.lib.evtmgr import eventManager
from wx.lib.scrolledpanel import ScrolledPanel
from wx.lib.filebrowsebutton import *
from wx.lib.stattext import GenStaticText

from peppy.lib.column_autosize import ColumnAutoSizeMixin
from peppy.lib.controls import FontBrowseButton

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

class FileBrowseButton2(FileBrowseButton):
    """Small enhancements to FileBrowseButton"""
    def createDialog(self, *args, **kwargs):
        """Automatically hide the label because it's not used here"""
        FileBrowseButton.createDialog(self, *args, **kwargs)
        self.label.Hide()
        
    def SetToolTipString(self, text):
        #dprint(text)
        self.textControl.SetToolTipString(text)
        
    def IsEnabled(self):
        """Make IsEnabled work by returning the enabled state of the
        text control
        """
        # FileBrowseButton never sets the enabled state of the panel
        # itself, so it always returns True.  Make it return the state
        # of the text control, which should indicate the real enabled state.
        return self.textControl.IsEnabled()
    
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
    """Generic param interface.

    Param objects follow the lifetime of the class, and so are not
    typically destroyed until the end of the program.  That also means
    that they operate as flyweight objects with their state stored
    extrinsically.  They are also factories for creating editing
    widgets (the getCtrl method) and as visitors to process the
    conversion between the user interface representation of the value
    and the user code's representation of the value (the get/setValue
    methods).

    It's important to understand the two representations of the param.
    What I call "text" is the textual representation that is stored in
    the user configuration file, and what I call "value" is the result
    of the conversion into the correct python type.  The value is what
    the python code operates on, and doesn't need to know anything about
    the textual representation.  These conversions are handled by the
    textToValue and valueToText methods.

    Note that depending on the wx control used to display the value,
    additional conversion may be necessary to show the value.  This is
    handled by the getValue and setValue methods.

    The default Param is a string param, and no restriction on the
    value of the string is imposed.
    """

    # class default to be used as the instance default if no other
    # default is provided.
    default = None
    
    # Event to be used as the callback trigger when the user changes the
    # control.  Subclasses should override this class attribute to correspond
    # to whatever event is appropriate for the control
    callback_event = wx.EVT_TEXT
    
    def __init__(self, keyword, default=None, help='',
                 save_to_file=True, **kwargs):
        self.keyword = keyword
        if default is not None:
            self.default = default
        self.help = help
        self.save_to_file = save_to_file
        
        # join means to place the next param's control on the same line as
        # this one
        if 'next_on_same_line' in kwargs or 'join' in kwargs:
            self.next_on_same_line = True
        else:
            self.next_on_same_line = False
        
        # wide params expand to fill extra columns; fullwidth params expand to
        # fill the width of the window
        if 'fullwidth' in kwargs:
            self.fullwidth = kwargs['fullwidth']
        else:
            self.fullwidth = False
        if 'wide' in kwargs:
            self.wide = kwargs['wide']
        else:
            self.wide = self.fullwidth
        
        # An alternate label can be supplied using the keyword 'label'
        if 'label' in kwargs:
            self.alt_label = kwargs['label']
        else:
            self.alt_label = None
        
        # The editing control of the param can also be disabled
        if 'disable' in kwargs:
            self.enable = not kwargs['disable']
        else:
            self.enable = True
        
        # Params marked as 'local' will be placed in the instance's local
        # namespace as well as in the classprefs.  This means that the
        # instance can have different values for the local version of the
        # param as compared to the class-wide version.
        if 'local' in kwargs:
            self.local = kwargs['local']
        else:
            self.local = False
        
        # Flag to indicate if any callbacks should be processed.  When the
        # value has been changed programmatically (i.e.  not by the user typing
        # something), it may be desirable to turn off callbacks.  This happens
        # if some params dynamically depend on the values in other params, and
        # could lead to a race condition if callbacks are allowed to propagate
        self.user_initiated_callback = True
        
        # Added a user settable callback hook.  Use setObserverCallback
        self.processCallbackHook = None
    
    def __str__(self):
        return "keyword=%s, default=%s, next=%s, show=%s, help=%s" % (self.keyword,
        self.default, self.next_on_same_line, self.alt_label, self.help)

    def isSettable(self):
        """True if the user can set this parameter"""
        return True

    def isVisible(self):
        """True if this item is to be displayed."""
        return True

    def getLabel(self, parent):
        if self.alt_label == False:
            return None
        
        if self.alt_label is None:
            title = GenStaticText(parent, -1, self.keyword)
        else:
            title = GenStaticText(parent, -1, self.alt_label)
        if self.help:
            title.SetToolTipString(self.help)
        return title

    def getCtrl(self, parent, initial=None):
        """Create and editing control.

        Given the parent window, create a user interface element to
        edit the param.
        """
        ctrl = wx.TextCtrl(parent, -1, size=(125, -1),
                           style=wx.TE_PROCESS_ENTER)
        ctrl.Enable(self.enable)
        return ctrl
    
    def setObserverCallback(self, callback):
        """Sets a callback hook that calls this function when the
        processCallback method is called.
        
        This method provides a way to hook a callback to the param without
        subclassing the param.  This hook will be called at the end of the
        processCallback.  The callback should have the following method
        signature:
        
           def callback(param, evt, ctrl, ctrl_list)
        
        See the definition of L{processCallback} for a description of the
        paramaters that will be passed to the callback.
        """
        self.processCallbackHook = callback
    
    def processCallback(self, evt, ctrl, ctrl_list):
        """Subclasses should override this to provide functionality.
        
        This callback is the class-specific callback in response to the
        event named in the class attribute 'callback_event'.
        
        evt: event object
        ctrl: control from evt.GetEventObject
        ctrl_list: dict mapping param objects to their corresponding controls
        """
        evt.Skip()
    
    def OnCallback(self, evt):
        """Callback driver for the control"""
        ctrl = evt.GetEventObject()
        if self.user_initiated_callback:
            self.processCallback(evt, ctrl, ctrl.ctrl_list)
            if self.processCallbackHook:
                self.processCallbackHook(self, evt, ctrl, ctrl.ctrl_list)
    
    def setCallback(self, ctrl, ctrl_list):
        """Set the callback that responds to changes in the state of the control
        
        This is called during control creation to set the callback in response
        to the class attribute 'callback_event' that is particular to the type
        of control being created.  Subclasses should change the callback_event
        to an event that is fired in response to the user changing the state
        of the control.
        
        Some controls have multiple events that can be fired; for now, only
        a single event is handled.
        """
        if self.callback_event is not None:
            ctrl.ctrl_list = ctrl_list
            ctrl.Bind(self.callback_event, self.OnCallback)
    
    def overrideCallback(self, ctrl, callback):
        """Override the callback on the control.
        
        Force the callback for the control to call the specified function.
        Normally the callback is tied to the param's L{OnCallback} method,
        allowing the param to do checking on the input.  However, the callback
        may be overridden with this method to force an individual control to
        call a specific function.  This means that the callback is no longer
        tied to the param's callback, and the callback will have to determine
        which control was acted upon by using the evt.GetEventObject() method.
        
        Some controls have multiple events that can be fired; for now, only
        a single event is handled.
        """
        if self.callback_event is not None:
            ctrl.Bind(self.callback_event, callback)
    
    def setInitialState(self, ctrl, ctrl_list):
        """Set the initial state of the control.
        
        Callback to set the initial state of the widget based on the state of
        all the other controls in the collection of params.  This must only
        be called after all of the controls in the param collection have
        been created, because the the ctrl_list dict must contain the entire
        mapping of params to controls.
        """
        pass

    def textToValue(self, text):
        """Convert the user's config text to the type expected by the
        python code.

        Subclasses should return the type expected by the user code.
        """
        # The default implementation just returns a string with any
        # delimiting quotation marks removed.
        if text.startswith("'") or text.startswith('"'):
            text = text[1:]
        if text.endswith("'") or text.endswith('"'):
            text = text[:-1]
        return text

    def valueToText(self, value):
        """Convert the user value to a string suitable to be written
        to the config file.

        Subclasses should convert the value to a string that is
        acceptable to textToValue.
        """
        # The default string implementation adds quotation characters
        # to the string.
        if isinstance(value, str):
            value = '"%s"' % value
        return value

    def setValue(self, ctrl, value):
        """Populate the control given the user value.

        If any conversion is needed to show the user value in the
        control, do it here.
        """
        # The default string edit control doesn't need any conversion.
        ctrl.SetValue(value)

    def setValueWithoutCallback(self, ctrl, value):
        """Populate the control given the user value, but don't execute any
        callbacks.

        Callbacks are designed to be executed in response to the user changing
        the value, not to a programmatic change.  If you don't care that
        the callback might be triggered when using the setValue method, then
        there's no problem with the program calling setValue.  However, if
        you've extended a Param to depend on the value of another param; e.g.
        you've created a processCallback or setInitialState that changes
        in response to the values in another param, it is most safe to call
        setValueWithoutCallback for programmatic changes, unless you take care
        to guarantee the order of the setValue calls.
        """
        self.user_initiated_callback = False
        self.setValue(ctrl, value)
        self.user_initiated_callback = True

    def getValue(self, ctrl):
        """Get the user value from the control.

        If the control doesn't automatically return a value of the
        correct type, convert it here.
        """
        # The default string edit control simply returns the string.
        return str(ctrl.GetValue())

class ReadOnlyParam(debugmixin):
    """Read-only parameter for display only."""
    callback_event = None
    
    def __init__(self, keyword, default=None, help=''):
        self.keyword = keyword
        if default is not None:
            self.default = default
        self.help = ''

    def isSettable(self):
        return False

class ParamSection(ReadOnlyParam):
    def isVisible(self):
        return False
    
class BoolParam(Param):
    """Boolean parameter that displays a checkbox as its user interface.

    Text uses one of 'yes', 'true', or '1' to represent the bool True,
    and anything else to represent False.
    """
    default = False
    callback_event = wx.EVT_CHECKBOX

    # For i18n support, load your i18n conversion stuff and change
    # these class attributes
    yes_values = ["yes", "true", "1"]
    no_values = ["no", "false", "0"]
    
    def getCtrl(self, parent, initial=None):
        """Return a checkbox control"""
        ctrl = wx.CheckBox(parent, -1, "")
        return ctrl

    def textToValue(self, text):
        """Return True if one of the yes values, otherwise False"""
        text = Param.textToValue(self, text).lower()
        if text in self.yes_values:
            return True
        return False

    def valueToText(self, value):
        """Convert the boolean value to a string"""
        if value:
            return self.yes_values[0]
        return self.no_values[0]

    def setValue(self, ctrl, value):
        # the control operates on boolean values directly, so no
        # conversion is needed.
        ctrl.SetValue(value)

    def getValue(self, ctrl):
        # The control returns booleans, which is what we want
        return ctrl.GetValue()

class IntParam(Param):
    """Int parameter that displays a text entry field as its user interface.

    The text is converted through the locale atof conversion, then
    cast to an integer.
    """
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
    """Int parameter that displays a text entry field as its user interface.

    The text is converted through the locale atof conversion.
    """
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
    """String parameter that displays a text entry field as its user interface.

    This is an alias to the Param class.
    """
    default = ""
    pass

class UnquotedStrParam(StrParam):
    """String parameter that doesn't enclose the string in quotes"""
    def valueToText(self, value):
        return value

class DateParam(Param):
    """Date parameter that displays a DatePickerCtrl as its user
    interface.

    The wx.DateTime class is used as the value.
    """
    default = wx.DateTime().Today()
    callback_event = wx.EVT_DATE_CHANGED
    
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
    """Directory parameter that displays a DirBrowseButton2 as its
    user interface.

    A string that represents a directory path is used as the value.
    It will always be a normalized path.
    """
    default = os.path.dirname(os.getcwd())
    callback_event = None

    def getCtrl(self, parent, initial=None):
        if initial is None:
            initial = os.getcwd()
        c = DirBrowseButton2(parent, -1, size=(300, -1),
                             labelText = '', startDirectory=initial,
                             changeCallback = self.changeCallback)
        return c

    def setValue(self, ctrl, value):
        ctrl.SetValue(os.path.normpath(value))

    def changeCallback(self, evt):
        # FIXME: this possibly can be used to maintain a history, but
        # haven't worked it out yet.
        
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

    def overrideCallback(self, ctrl, callback):
        """Override the callback with a new one.
        
        Note that this callback will originate from the text control, not
        the DirBrowseButton.  Any callbacks that rely on determining the
        control using GetEventObject will have to search up through the window
        hierarchy to get back to the browse button.
        """
        ctrl.changeCallback = callback

class PathParam(DirParam):
    """Directory parameter that displays a FileBrowseButton as its
    user interface.

    A string that represents a path to a file is used as the value.
    """
    default = os.getcwd()
    
    def getCtrl(self, parent, initial=None):
        if initial is None:
            initial = os.getcwd()
        c = FileBrowseButton2(parent, -1, size=(300, -1),
                                        labelText = '',
                                        startDirectory=initial,
                                        changeCallback = self.changeCallback)
        return c


class ChoiceParam(Param):
    """Parameter that is restricted to a string from a list of choices.

    A Choice control is its user interface, and the currently selected
    string is used as the value.
    """
    callback_event = wx.EVT_CHOICE
    
    def __init__(self, keyword, choices, default=None, help='', **kwargs):
        Param.__init__(self, keyword, help=help, **kwargs)
        self.choices = choices
        if default is not None:
            self.default = default
        else:
            self.default = choices[0]

    def getCtrl(self, parent, initial=None):
        ctrl = wx.Choice(parent , -1, (100, 50), choices = self.choices)
        return ctrl

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
    """Parameter that is restricted to a string from a list of
    choices, but using an integer as the value.

    The user interface presents a list of strings, but the value is either
    the index of the string within the list in the simple case, or using a map
    of index to another integer.  If the choices are a simple text string,
    index mode is used; however, if the choices are each tuples of an int
    and a string, the int in the tuple is used as the value.
    
    For example, IndexChoiceParam('Citrus', ['Lemon','Lime','Grapefruit']) is
    a simple index lookup, from the set {0, 1, 2}, where the following uses a
    keyed lookup and represents the value as the integer in the first element
    of each tuple:
        
      IndexChoiceParam('coins', [(1, 'penny'), (5, 'nickel'), (10, 'dime')])
    """
    callback_event = wx.EVT_CHOICE
    
    def __init__(self, keyword, choices, default=None, help='', **kwargs):
        Param.__init__(self, keyword, help=help, **kwargs)
        if isinstance(choices[0], list) or isinstance(choices[0], tuple):
            self.choices = []
            self.index_to_value = {}
            self.value_to_index = {}
            index = 0
            for c in choices:
                self.index_to_value[index] = c[0]
                self.value_to_index[c[0]] = index
                self.choices.append(c[1])
                index += 1
        else:
            self.choices = choices
            self.index_to_value = self.value_to_index = range(0, len(choices))
        if default is not None and default in self.value_to_index:
            self.default = default
        else:
            self.default = self.index_to_value[0]

    def getCtrl(self, parent, initial=None):
        ctrl = wx.Choice(parent , -1, (100, 50), choices = self.choices)
        ctrl.SetSelection(self.default)
        return ctrl

    def textToValue(self, text):
        try:
            text = Param.textToValue(self, text)
            tmp = locale.atof(text)
            val = int(tmp)
            if val not in self.value_to_index:
                val = self.default
        except:
            val = self.default
        return val

    def setValue(self, ctrl, value):
        index = self.value_to_index[value]
        if index >= len(self.choices):
            index = 0
        ctrl.SetSelection(index)

    def getValue(self, ctrl):
        index = ctrl.GetSelection()
        return self.index_to_value[index]

class KeyedIndexChoiceParam(IndexChoiceParam):
    """Parameter that is restricted to a string from a list of
    choices, but using a key corresponding to the string as the value.

    A Choice control is its user interface, and the key of the
    currently selected string is used as the value.

    An example:
    
        KeyedIndexChoiceParam('edge_indicator',
                              [(wx.stc.STC_EDGE_NONE, 'none'),
                               (wx.stc.STC_EDGE_LINE, 'line'),
                               (wx.stc.STC_EDGE_BACKGROUND, 'background'),
                               ], 'line', help='Long line indication mode'),

    means that the user code deals with wx.stc.STC_EDGE_NONE,
    wx.stc.STC_EDGE_LINE, and wx.stc.STC_EDGE_BACKGROUND, but stored
    in the configuration will be 'none', 'line', or 'background'.  The
    strings 'none', 'line', or 'background' are the items that will be
    displayed in the choice control.
    """
    def __init__(self, keyword, choices, default=None, help='', **kwargs):
        Param.__init__(self, keyword, help=help, **kwargs)
        self.choices = [entry[1] for entry in choices]
        self.keys = [entry[0] for entry in choices]
        if default is not None and default in self.choices:
            self.default = self.keys[self.choices.index(default)]
        else:
            self.default = self.keys(0)

    def getCtrl(self, parent, initial=None):
        ctrl = wx.Choice(parent , -1, (100, 50), choices = self.choices)
        index = self.keys.index(self.default)
        ctrl.SetSelection(index)
        return ctrl

    def textToValue(self, text):
        text = Param.textToValue(self, text)
        try:
            index = self.choices.index(text)
        except ValueError:
            index = 0
        return self.keys[index]

    def valueToText(self, value):
        index = self.keys.index(value)
        return str(self.choices[index])

    def setValue(self, ctrl, value):
        index = self.keys.index(value)
        ctrl.SetSelection(index)

    def getValue(self, ctrl):
        index = ctrl.GetSelection()
        return self.keys[index]

class FontParam(Param):
    """Font parameter that pops up a font dialog.

    The wx.Font class is used as the value.
    """
    
    def getCtrl(self, parent, initial=None):
        btn = FontBrowseButton(parent)
        return btn

    def textToValue(self, text):
        face, size = text.split(',')
        face = face.strip()
        size = int(size.strip())
        font = wx.FFont(size, wx.DEFAULT, face=face)
        return font

    def valueToText(self, font):
        assert self.dprint(font)
        text = "%s, %d" % (font.GetFaceName(), font.GetPointSize())
        return text

    def setValue(self, ctrl, value):
        ctrl.setFont(value)

    def getValue(self, ctrl):
        return ctrl.getFont()



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
    subclasses={}

    # this call only returns immediate (child) subclasses, not
    # grandchild subclasses where there is an intermediate class
    # between the two.
    classes=parent.__subclasses__()
    for kls in classes:
        # FIXME: this seems to return multiple copies of the same class,
        # but I probably just don't understand enough about how python
        # creates subclasses
        # dprint("%s id=%s" % (kls, id(kls)))
        if issubclass(kls,subclassof):
            subclasses[kls] = 1
        # for each subclass, recurse through its subclasses to
        # make sure we're not missing any descendants.
        subs=getAllSubclassesOf(parent=kls)
        if len(subs)>0:
            for kls in subs:
                subclasses[kls] = 1
    return subclasses.keys()

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
        hierarchy=[k for k in parents(klass) if k.__name__ not in skipclasses and not k.__module__.startswith('wx.')]
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
    seen = {} # has the default_classprefs been seen for the class?
    convert_already_seen = {}
    
    # configuration has been loaded from text for this class, but not
    # converted yet.
    needs_conversion = {}
    
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
        #dprint(namehier)
        if leaf not in GlobalPrefs.class_hierarchy:
            GlobalPrefs.class_hierarchy[leaf]=classhier
        if leaf not in GlobalPrefs.name_hierarchy:
            GlobalPrefs.name_hierarchy[leaf]=namehier

    @staticmethod
    def setupHierarchyDefaults(klasshier):
        for klass in klasshier:
            if klass.__name__ not in GlobalPrefs.default:
                #dprint("%s not seen before" % klass)
                defs={}
                params = {}
                if hasattr(klass,'default_classprefs'):
                    GlobalPrefs.seen[klass.__name__] = True
                    for p in klass.default_classprefs:
                        defs[p.keyword] = p.default
                        params[p.keyword] = p
                GlobalPrefs.default[klass.__name__]=defs
                GlobalPrefs.params[klass.__name__] = params
            else:
                #dprint("%s app defaults seen" % klass)
                # we've loaded application-specified defaults for this
                # class before, but haven't actually checked the
                # class.  Merge them in without overwriting the
                # existing prefs.
                #print "!!!!! missed %s" % klass
                if hasattr(klass,'default_classprefs'):
                    GlobalPrefs.seen[klass.__name__] = True
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
            GlobalPrefs.needs_conversion[section] = True
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
    def convertSection(section):
        if section not in GlobalPrefs.params or section in GlobalPrefs.convert_already_seen or section not in GlobalPrefs.seen:
            # Don't process values before the param definition for
            # the class is loaded.  Copy the existing text values
            # and defer the conversion till the next time
            # convertConfig is called.
            if GlobalPrefs.debuglevel > 0:
                if section not in GlobalPrefs.params:
                    dprint("haven't loaded class %s" % section)
                elif section in GlobalPrefs.convert_already_seen:
                    dprint("already converted class %s" % section)
                elif section not in GlobalPrefs.seen:
                    dprint("only defaults loaded, haven't loaded Params for class %s" % section)
            return
        
        GlobalPrefs.convert_already_seen[section] = True
        if section in GlobalPrefs.needs_conversion:
            options = GlobalPrefs.user[section]
            d = {}
            for option, text in options.iteritems():
                param = GlobalPrefs.findParam(section, option)
                try:
                    if param is not None:
                        val = param.textToValue(text)
                        if GlobalPrefs.debuglevel > 0: dprint("Converted %s to %s(%s) for %s[%s]" % (text, val, type(val), section, option))
                    else:
                        val = text
                    d[option] = val
                except Exception, e:
                    eprint("Error converting %s in section %s: %s" % (option, section, str(e)))
            GlobalPrefs.user[section] = d
    
    @staticmethod
    def convertConfig():
        # Need to copy dict to temporary one, because BadThings happen
        # while trying to update a dictionary while iterating on it.
        if GlobalPrefs.debuglevel > 0: dprint("before: %s" % GlobalPrefs.user)
        if GlobalPrefs.debuglevel > 0: dprint("name_hierarchy: %s" % GlobalPrefs.name_hierarchy)
        if GlobalPrefs.debuglevel > 0: dprint("params: %s" % GlobalPrefs.params)
        sections = GlobalPrefs.user.keys()
        for section in sections:
            GlobalPrefs.convertSection(section)
        if GlobalPrefs.debuglevel > 0: dprint("after: %s" % GlobalPrefs.user)

        # Save a copy so we can tell if the user changed anything.  Can't
        # use copy.deepcopy(GlobalPrefs.user) anymore because wx.Font objects
        # are now param types and get a type exception trying to deepcopy them.
        saved = {}
        for section, options in GlobalPrefs.user.iteritems():
            saved[section] = {}
            for option, val in options.iteritems():
                try:
                    saved[section][option] = copy.deepcopy(val)
                except Exception, e:
                    # wx swig objects can't be deepcopied, but they are also
                    # unlikely to be modified in place, so setting the saved
                    # value to the same reference is probably OK.
                    #dprint(str(e))
                    saved[section][option] = val
        GlobalPrefs.save_user = saved
            
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
                    if not printed_section:
                        lines.append("[%s]" % section)
                        printed_section = True
                    if param is None:
                        # No param means that the section doesn't correspond
                        # to any loaded class, probably meaning that it was
                        # a dynamically loaded class that just wasn't loaded
                        # this time.  So, save the raw text since we don't
                        # have a param to use to convert.
                        lines.append("%s = %s" % (option, val))
                    else:
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
                #assert self.dprint("checking %s for %s in user dict %s" % (klass, name, d[klass]))
                if klass in d and name in d[klass]:
                    if klass not in GlobalPrefs.convert_already_seen:
                        dprint("warning: GlobalPrefs[%s] not converted yet." % klass)
                        GlobalPrefs.convertSection(klass)
                        d = GlobalPrefs.user
                    return d[klass][name]
        if default:
            d=GlobalPrefs.default
            for klass in klasses:
                #assert self.dprint("checking %s for %s in default dict %s" % (klass, name, d[klass]))
                if klass in d and name in d[klass]:
                    return d[klass][name]

        klasses=GlobalPrefs.class_hierarchy[self.__dict__['_startSearch']]
        for klass in klasses:
            #assert self.dprint("checking %s for %s in default_classprefs" % (klass,name))
            if hasattr(klass,'default_classprefs') and name in klass.default_classprefs:
                return klass.default_classprefs[name]
        raise AttributeError("%s not found in %s.classprefs" % (name, self.__dict__['_startSearch']))

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


class LocalPrefs(object):
    pass


class ClassPrefs(object):
    """Base class to extend in order to support class prefs.

    Uses the L{ClassPrefsMetaClass} to provide automatic support
    for the prefs class attribute.
    """
    __metaclass__ = ClassPrefsMetaClass
    
    #: Sorting weight (from 0 to 1000) if you want to group items out of the
    # ordinary the dictionary sort order
    preferences_sort_weight = 500
    
    def classprefsCopyToLocals(self):
        if not hasattr(self, 'locals'):
            self.locals = LocalPrefs()
        hier = self.classprefs._getMRO()
        #dprint(hier)
        updated = {}
        for cls in hier:
            if 'default_classprefs' not in dir(cls):
                continue
            for param in cls.default_classprefs:
                if param.local:
                    #dprint("setting instance var %s to %s" % (param.keyword, self.classprefs._get(param.keyword)))
                    setattr(self.locals, param.keyword, self.classprefs._get(param.keyword))

    def classprefsCopyFromLocals(self):
        if not hasattr(self, 'locals'):
            raise AttributeError("local copy of classprefs doesn't exist in %s!" % self)
        hier = self.classprefs._getMRO()
        #dprint(hier)
        updated = {}
        for cls in hier:
            if 'default_classprefs' not in dir(cls):
                continue
            for param in cls.default_classprefs:
                if param.local:
                    #dprint("setting classpref %s to %s" % (param.keyword, self.classprefs._get(param.keyword)))
                    self.classprefs._set(param.keyword, getattr(self.locals, param.keyword))
    
    def classprefsFindParam(self, keyword):
        """Find the Param instance corresponding to the keyword.
        
        Search each default_classprefs going up the class hierarchy for a param
        with the specified keyword.
        
        This currently uses an inefficient linear search, so if this is called
        a lot, it will probably be slow.
        
        @param keyword: string to search for
        @return: param instance
        @raises: IndexError if not found
        """
        if not hasattr(self, 'locals'):
            raise AttributeError("local copy of classprefs doesn't exist in %s!" % self)
        hier = self.classprefs._getMRO()
        #dprint(hier)
        updated = {}
        for cls in hier:
            if 'default_classprefs' not in dir(cls):
                continue
            for param in cls.default_classprefs:
                if param.keyword == keyword:
                    #dprint("found %s in %s" % (param.keyword, cls))
                    return param
        raise IndexError("keyword %s not found in default_classprefs in any class in the MRO of %s" % (param.keyword, self))


class PrefPanel(ScrolledPanel, debugmixin):
    """Panel that shows ui controls corresponding to all preferences
    """

    def __init__(self, parent, obj):
        ScrolledPanel.__init__(self, parent, -1, size=(500,-1),
                               pos=(9000,9000))
        self.parent = parent
        self.obj = obj
        
        self.ctrls = {}
        self.orig = {}
        
        # self.sizer = wx.GridBagSizer(2,5)
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.create()
        self.SetSizer(self.sizer)
        self.Layout()

    def Layout(self):
        ScrolledPanel.Layout(self)
        self.SetupScrolling()
        self.Scroll(0,0)
    
    @staticmethod
    def populateGrid(parent, sizer, name, params, ctrls, orig, default_getter=None):
        """Static method to populate some sizer with classprefs.
        
        This is a static method because it can be used by outside functions
        that use params but aren't classprefs.  For example, generic dialog
        boxes can be created by setting up a list of params, and then
        populating the dialog with the controls.
        
        parent: parent of all the controls to be generated
        sizer: sizer in which to add all the grid sizer
        name: name of the StaticBox that wraps the grid sizer
        ctrls: dict keyed on param to add the created controls
        orig: dict keyed on param to store the original values
        default_getter: optional functor to return a default value for the keyword
        """
        row = 0
        col = 0
        existing_keywords = {}
        for param in ctrls:
            existing_keywords[param.keyword] = True
        for param in params:
            if param.keyword in existing_keywords:
                # Don't put another control if it exists in a superclass
                continue

            if isinstance(param, ParamSection):
                name = param.keyword
                
            if name:
                box = wx.StaticBox(parent, -1, name)
                bsizer = wx.StaticBoxSizer(box, wx.VERTICAL)
                sizer.Add(bsizer, 0, wx.EXPAND)
                grid = wx.GridBagSizer(2,5)
                bsizer.Add(grid, 0, wx.EXPAND)
                
                # reset so it acts as a flag
                name = None
                row = 0
                col = 0
            
            if not param.isVisible():
                continue
            
            width = 1
            title = param.getLabel(parent)
            if title is not None:
                if grid.CheckForIntersectionPos((row,col), (1,width)):
                    dprint("found overlap for %s at (%d,%d)" % (param.keyword, row, col))
                else:
                    grid.Add(title, (row,col))
                col += 1
            else:
                width = 2
            if param.wide:
                if isinstance(param.wide, int):
                    width += param.wide
                else:
                    width += 2
                if param.fullwidth:
                    grid.AddGrowableCol(col + width - 1)

            if param.isSettable():
                ctrl = param.getCtrl(parent)
                ctrls[param] = ctrl
                param.setCallback(ctrl, ctrls)
                if param.help:
                    ctrl.SetToolTipString(param.help)
                if grid.CheckForIntersectionPos((row,col), (1,width)):
                    dprint("found overlap for control of %s at (%d,%d)" % (param.keyword, row, col))
                else:
                    grid.Add(ctrl, (row,col), (1,width), flag=wx.EXPAND)
                col += width
                
                if default_getter is not None:
                    val = default_getter(param.keyword)
                    #dprint("keyword %s: val = %s(%s)" % (param.keyword, val, type(val)))
                    param.setValue(ctrl, val)
                    orig[param] = val
                
            if not param.next_on_same_line:
                row += 1
                col = 0

    def create(self):
        """Create the list of classprefs, organized by MRO.
        
        Creates a group of StaticBoxes, each one representing the classprefs
        of a class in the MRO (method resolution order).
        """
        row = 0
        focused = False
        hier = [c for c in self.obj.classprefs._getMRO() if 'default_classprefs' in dir(c)]
        self.dprint(hier)
        first = True
        for cls in hier:
            if first:
                name = cls.__name__
                first = False
            else:
                name = "Inherited from %s" % cls.__name__
            self.populateGrid(self, self.sizer, name, cls.default_classprefs,
                              self.ctrls, self.orig, self.obj.classprefs)
        
    def update(self):
        """Update the class with the changed preferences."""
        hier = self.obj.classprefs._getMRO()
        self.dprint(hier)
        updated = {}
        for cls in hier:
            if 'default_classprefs' not in dir(cls):
                continue
            
            for param in cls.default_classprefs:
                if param in updated:
                    # Don't update with value in superclass
                    continue

                # It's possible that a param won't have an associated control
                # because the param is handled by a subclass.  Params are
                # class attributes, and if a param of the same name is
                # overridden by a subclass, the control will only appear in
                # the subclass, not any superclasses.  In addition, only deal
                # with those controls that are settable
                if param in self.ctrls and param.isSettable():
                    ctrl = self.ctrls[param]
                    val = param.getValue(ctrl)
                    if val != self.orig[param]:
                        self.dprint("%s has changed from %s(%s) to %s(%s)" % (param.keyword, self.orig[param], type(self.orig[param]), val, type(val)))
                        self.obj.classprefs._set(param.keyword, val)
                    updated[param] = True


class PrefClassList(ColumnAutoSizeMixin, wx.ListCtrl, debugmixin):
    def __init__(self, parent, classes):
        wx.ListCtrl.__init__(self, parent, size=(200,400), style=wx.LC_REPORT)
        ColumnAutoSizeMixin.__init__(self)

        self.setIconStorage()
        
        self.skip_verify = False

        self.createColumns()
        self.reset(classes)

    def setIconStorage(self):
        pass

    def appendItem(self, name):
        self.InsertStringItem(sys.maxint, name)

    def setItem(self, index, name):
        self.SetStringItem(index, 0, name)

    def createColumns(self):
        self.InsertSizedColumn(0, "Class")

    def reset(self, classes):
        index = 0
        list_count = self.GetItemCount()
        self.class_names = []
        self.class_map = {}
        for cls in classes:
            name = cls.__name__
            self.class_names.append(name)
            self.class_map[name] = cls
            if index >= list_count:
                self.appendItem(name)
            else:
                self.setItem(index, name)
            index += 1

        if index < list_count:
            for i in range(index, list_count):
                # always delete the first item because the list gets
                # shorter by one each time.
                self.DeleteItem(index)
        self.SetColumnWidth(0, wx.LIST_AUTOSIZE)

    def getClass(self, index=-1):
        if index == -1:
            index = self.GetNextItem(-1, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
        if index == -1:
            index = 0
        return self.class_map[self.class_names[index]]

    def ensureClassVisible(self, cls):
        try:
            index = self.class_names.index(cls.__name__)
            self.SetItemState(index, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
            self.EnsureVisible(index)
        except:
            # item not in list. skip it.
            pass

class PrefPage(wx.SplitterWindow):
    """Notebook page to hold preferences for one notebook tab"""
    
    def __init__(self, parent, classes, *args, **kwargs):
        wx.SplitterWindow.__init__(self, parent, -1, *args, **kwargs)
        self.SetMinimumPaneSize(50)
        
        self.pref_panels = {}
        list = self.createList(classes)
        dum = wx.Window(self, -1)
        self.SplitVertically(list, dum, -500)
        list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected, list)

    def OnItemSelected(self, evt):
        index = evt.GetIndex()
        list = evt.GetEventObject()
        if index >= 0:
            cls = list.getClass(index)
            self.changePanel(cls)
        evt.Skip()

    def createList(self, classes):
        """Create the ListCtrl that holds the list of classes"""
        list = PrefClassList(self, classes)
        return list
        
    def showClass(self, cls):
        """Make sure the requested class is highlighted and its pref panel
        is shown."""
        self.GetWindow1().ensureClassVisible(cls)
    
    def getPanel(self, cls=None):
        """Get or create the requested class's pref panel"""
        if cls is None:
            cls = self.GetWindow1().getClass()
        if cls.__name__ in self.pref_panels:
            pref = self.pref_panels[cls.__name__]
        else:
            pref = PrefPanel(self, cls)
            self.pref_panels[cls.__name__] = pref
        return pref
    
    def changePanel(self, cls=None):
        """Change the currently shown pref panel to the requested"""
        old = self.GetWindow2()
        pref = self.getPanel(cls)
        self.ReplaceWindow(old, pref)
        old.Hide()
        pref.Show()
        pref.Layout()

    def applyPreferences(self):
        """On an OK from the dialog, process any updates to the plugins"""
        # Look at all the panels that have been created: this gives us
        # an upper bound on what may have changed.
        for cls, pref in self.pref_panels.iteritems():
            pref.update()


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
            label = GenStaticText(self, -1, self.static_title)
            sizer.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        self.createClassMap()
        
        self.notebook = wx.Notebook(self)
        sizer.Add(self.notebook, 1, wx.EXPAND)
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnTabChanged)
        
        # Sort the names so that Misc and Plugins are always last
        last = []
        names = self.tab_map.keys()
        for name in ['Misc', 'Plugins']:
            if name in names:
                names.remove(name)
                last.append(name)
        names.sort()
        names.extend(last)
        
        self.tab_to_page = {}
        count = 0
        for tab in names:
            splitter = self.createPage(tab, self.tab_map[tab])
            self.notebook.AddPage(splitter, tab)
            self.tab_to_page[tab] = count
            count += 1
        
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

        index = self.getPageIndex(self.obj.__class__)
        self.notebook.SetSelection(index)
        page = self.notebook.GetPage(index)
        page.showClass(self.obj.__class__)

        self.Layout()
    
    def OnTabChanged(self, evt):
        #dprint()
        val = evt.GetSelection()
        page = self.notebook.GetPage(val)
        page.changePanel()
        evt.Skip()

    def createClassMap(self):
        classes = getAllSubclassesOf(ClassPrefs)
        # Because getAllSubclassesOf can return multiple classes that
        # really refer to the same class (still don't understand how this
        # is possible) we need to sort on class name and make that the
        # key instead of the class object itself.
        unique = {}
        for cls in classes:
            unique[cls.__name__] = cls
        self.class_map = unique
        classes = unique.values()
        classes.sort(key=lambda x: (x.preferences_sort_weight, x.__name__))
        
        self.tab_map= {}
        self.class_to_tab = {}
        for cls in classes:
            if hasattr(cls, 'preferences_tab'):
                tab = cls.preferences_tab
            else:
                tab = "Misc"
            if tab not in self.tab_map:
                self.tab_map[tab] = []
            self.tab_map[tab].append(cls)
            self.class_to_tab[cls.__name__] = tab
        #dprint(self.tab_map)
        #dprint(self.class_to_tab)
        self.class_names = [x.__name__ for x in classes]
    
    def createPage(self, tab, classes):
        splitter = PrefPage(self.notebook, classes)
        return splitter

    def getPageIndex(self, cls):
        tab = self.class_to_tab[cls.__name__]
        index = self.tab_to_page[tab]
        return index

    def applyPreferences(self):
        # For every notebook page, update the preferences for that notebook
        for index in range(self.notebook.GetPageCount()):
            page = self.notebook.GetPage(index)
            page.applyPreferences()


if __name__ == "__main__":
    class Test1(ClassPrefs):
        default_classprefs = (
            IntParam("test1", 5, local=True),
            FloatParam("testfloat", 6.0),
            IntParam("testbase1", 1, local=True),
            IntParam("testbase2", 2),
            IntParam("testbase3", 3),
            )
        
        def __init__(self):
            self.classprefsCopyToLocals()
    
    class Test2(Test1):
        default_classprefs = (
            IntParam("test1", 7, join=True),
            FloatParam("testfloat", 6.0),
            StrParam("teststr", "BLAH!"),
            IntParam("col1", 1, next_on_same_line=True),
            IntParam("col2", 2),
            IntParam("col1again", 3, label=False),
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

    print "at initialization"
    print "t1.classprefs.test1=%s t1.locals.test1=%s" % (t1.classprefs.test1, t1.locals.test1)
    print "t1.classprefs.testbase1=%s t1.locals.testbase1=%s" % (t1.classprefs.testbase1, t1.locals.testbase1)
    print "t2.classprefs.test1=%s t2.locals.test1=%s" % (t2.classprefs.test1, t2.locals.test1)
    print "t2.classprefs.testbase1=%s t2.locals.testbase1=%s" % (t2.classprefs.testbase1, t2.locals.testbase1)
    print

    t1.classprefs.testbase1 = 113
    t1.locals.test1 = 593
    print "after setting t1.classprefs.test1=%s t1.locals.test1=%s" % (t1.classprefs.test1, t1.locals.test1)
    print "t1.classprefs.test1=%s t1.locals.test1=%s" % (t1.classprefs.test1, t1.locals.test1)
    print "t1.classprefs.testbase1=%s t1.locals.testbase1=%s" % (t1.classprefs.testbase1, t1.locals.testbase1)
    print "t2.classprefs.test1=%s t2.locals.test1=%s" % (t2.classprefs.test1, t2.locals.test1)
    print "t2.classprefs.testbase1=%s t2.locals.testbase1=%s" % (t2.classprefs.testbase1, t2.locals.testbase1)
    print

    t1.classprefsCopyToLocals()
    print "after t1.classprefsCopyToLocals"
    print "t1.classprefs.test1=%s t1.locals.test1=%s" % (t1.classprefs.test1, t1.locals.test1)
    print "t1.classprefs.testbase1=%s t1.locals.testbase1=%s" % (t1.classprefs.testbase1, t1.locals.testbase1)
    print "t2.classprefs.test1=%s t2.locals.test1=%s" % (t2.classprefs.test1, t2.locals.test1)
    print "t2.classprefs.testbase1=%s t2.locals.testbase1=%s" % (t2.classprefs.testbase1, t2.locals.testbase1)
    print

    t1.locals.test1 = -888
    t1.classprefsCopyFromLocals()
    print "after setting t1.locals.test1=%d and then t1.classprefsCopyFromLocals" % t1.locals.test1
    print "t1.classprefs.test1=%s t1.locals.test1=%s" % (t1.classprefs.test1, t1.locals.test1)
    print "t1.classprefs.testbase1=%s t1.locals.testbase1=%s" % (t1.classprefs.testbase1, t1.locals.testbase1)
    print "t2.classprefs.test1=%s t2.locals.test1=%s" % (t2.classprefs.test1, t2.locals.test1)
    print "t2.classprefs.testbase1=%s t2.locals.testbase1=%s" % (t2.classprefs.testbase1, t2.locals.testbase1)
    print

    t2.classprefs.testbase1 = 9874
    print "after setting t2.classprefs.testbase1=%s" % t2.classprefs.testbase1
    print "t1.classprefs.test1=%s t1.locals.test1=%s" % (t1.classprefs.test1, t1.locals.test1)
    print "t1.classprefs.testbase1=%s t1.locals.testbase1=%s" % (t1.classprefs.testbase1, t1.locals.testbase1)
    print "t2.classprefs.test1=%s t2.locals.test1=%s" % (t2.classprefs.test1, t2.locals.test1)
    print "t2.classprefs.testbase1=%s t2.locals.testbase1=%s" % (t2.classprefs.testbase1, t2.locals.testbase1)
    print
    
    t1.classprefsFindParam('testbase1')

    app = wx.PySimpleApp()

    dlg = PrefDialog(None, t1)
    dlg.Show(True)

    # Close down the dialog on a button press
    import sys
    dlg.Bind(wx.EVT_BUTTON, lambda e: sys.exit())

    app.MainLoop()
    
