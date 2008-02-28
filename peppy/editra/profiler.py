# Misc utility files from Editra that don't have any other dependencies
import os, sys
import wx

def Profile_Get(index, fmt=None, default=None):
    app = wx.GetApp()
    if index == 'FONT1':
        try:
            font = app.fonts.classprefs.primary_editing_font
            return font
        except:
            # If we're running a mock object for testing purposes, just
            # let this pass
            pass
    elif index == 'FONT2':
        try:
            font = app.fonts.classprefs.secondary_editing_font
            return font
        except:
            # again, catch the exception if we're running a mock object
            pass
    return None

def Profile_Set(index, val, fmt):
    return None
