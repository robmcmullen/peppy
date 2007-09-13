# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Helpers to create editing widgets for user parameters.
"""

import os, struct, time, re
from cStringIO import StringIO
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

class Param(debugmixin):
    def __init__(self, keyword, default=None):
        self.keyword = keyword
        self.category = None
        if default is not None:
            self.default = default

    def isSettable(self):
        return True

    def getCtrl(self, parent):
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

class ParamCategory(Param):
    def __init__(self, keyword, default=None):
        self.keyword = keyword
        self.category = keyword

    def isSettable(self):
        return False

    def getCtrl(self, parent):
        box = wx.StaticBox(parent, -1, self.keyword)
        ctrl = wx.StaticBoxSizer(box, wx.VERTICAL)
        return ctrl

class BoolParam(Param):
    default = False
    
    def getCtrl(self, parent):
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
    
    def getCtrl(self, parent):
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
    
    def getCtrl(self, parent):
        c = DirBrowseButton(parent, -1, size=(300, -1),
                            labelText = '', startDirectory=parent.cwd())
        return c

    def setValue(self, ctrl, value):
        ctrl.SetValue(os.path.normpath(value))

class PathParam(DirParam):
    default = ""
    
    def getCtrl(self, parent):
        c = FileBrowseButtonWithHistory(parent, -1, size=(300, -1),
                                        labelText = '',
                                        startDirectory=parent.cwd(),
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

    def getCtrl(self, parent):
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
