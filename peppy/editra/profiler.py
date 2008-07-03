# Wrapper around Editra configuration get/set utilities to return the peppy
# equivalent
import os, sys
import wx

def Profile_Get(index, fmt=None, default=None):
    app = wx.GetApp()
    try:
        if index == 'FONT1':
            font = app.fonts.classprefs.primary_editing_font
            return font
        elif index == 'FONT2':
            font = app.fonts.classprefs.secondary_editing_font
            return font
        elif index == 'SYNTHEME':
            theme = 'Default'
            return theme
    except:
        # catch the exception if we're running a mock object
        pass
    return None

def Profile_Set(index, val, fmt):
    return None
