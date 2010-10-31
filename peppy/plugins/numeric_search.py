# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Extension to SearchMode to allow searching through numeric values in a
file using comparison operators
"""

import os, re

import wx
from wx.lib.pubsub import Publisher

from peppy.debug import debugmixin
from peppy.yapsy.plugins import *
from peppy.lib.searchutils import *


class AbstractNumericMatcher(AbstractStringMatcher):
    cre = None
    
    def __init__(self, limit, func):
        self.limit, self.error = self.stringToNumber(limit)
        self.func = func
    
    def stringToNumber(self, text):
        try:
            number = self.convertFunc(text)
            error = ""
        except ValueError, e:
            number = None
            error = str(e)
        return number, error
    
    def convertFunc(self, text):
        raise NotImplementedError
        
    def iterLine(self, line):
        values = self.cre.findall(line)
        for value in values:
            v = self.convertFunc(value)
            if self.compareValue(v, self.limit):
                yield -1, -1, value
    
    def isValid(self):
        return self.limit is not None
    
    def getErrorString(self):
        if len(self.error) > 0:
            return "Search error: %s" % self.error
        return "Search error: invalid search string"

class FloatSingleParamMatcher(AbstractNumericMatcher):
    """Matches numbers less than the limit value"""
    cre = re.compile("([-+]?[0-9]*\.?[0-9]+(?:[eE][-+]?[0-9]+)?)")
    
    def convertFunc(self, text):
        return float(text)
    
    def compareValue(self, value, limit):
        return self.func(value, limit)

class HexSingleParamMatcher(AbstractNumericMatcher):
    """Matches numbers less than the limit value"""
    cre = re.compile("(0[xX][0-9a-fA-F]+)")
    
    def convertFunc(self, text):
        return int(text, 16)
    
    def compareValue(self, value, limit):
        return self.func(value, limit)


class NumericSearchType(object):
    """Implements the AbstractSearchType interface from
    peppy.plugins.search_in_files to provide the user interface for searching
    through text files using numeric comparisons and matches
    
    """
    def __init__(self, mode):
        self.mode = mode
        self.ui = None
    
    def getName(self):
        return "Numeric Search"
    
    def getUI(self, parent):
        self.ui = wx.Panel(parent, -1)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.hex = wx.CheckBox(self.ui, -1, _("Hexadecimal"))
        hbox.Add(self.hex, 0, wx.EXPAND)
        self.ui.SetSizer(hbox)
        return self.ui
    
    def setUIDefaults(self):
        pass

    def getStringMatcher(self, search_text):
        search_text = search_text.strip()
        if self.hex.IsChecked():
            matcher_cls = HexSingleParamMatcher
        else:
            matcher_cls = FloatSingleParamMatcher
        if search_text.startswith("<="):
            return matcher_cls(search_text[2:], lambda val, limit: val <= limit)
        elif search_text.startswith("<"):
            return matcher_cls(search_text[1:], lambda val, limit: val < limit)
        elif search_text.startswith(">="):
            return matcher_cls(search_text[2:], lambda val, limit: val >= limit)
        elif search_text.startswith(">"):
            return matcher_cls(search_text[1:], lambda val, limit: val > limit)
        elif search_text.startswith("="):
            return matcher_cls(search_text[1:], lambda val, limit: val == limit)
        else:
            return matcher_cls(search_text, lambda val, limit: val == limit)


class NumericSearchPlugin(IPeppyPlugin):
    """Add numeric search type to SearchMode
    """
    def activateHook(self):
        Publisher().subscribe(self.getTextSearchTypeProvider, 'search_in_files.text_search_type.provider')
    
    def deactivateHook(self):
        Publisher().unsubscribe(self.getTextSearchTextProvider)

    def getTextSearchTypeProvider(self, message):
        message.data.append(NumericSearchType)
