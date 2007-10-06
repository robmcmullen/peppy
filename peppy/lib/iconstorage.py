#-----------------------------------------------------------------------------
# Name:        iconstorage.py
# Purpose:     a centrally managed icon store for an application
#
# Author:      Rob McMullen
#
# Created:     2007
# RCS-ID:      $Id: $
# Copyright:   (c) 2007 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
import os, sys, imp, re, glob
from cStringIO import StringIO

import wx

from peppy.debug import *

__all__ = ['getIconStorage', 'getIconBitmap', 'addIconBitmap',
           'addIconsFromDirectory', 'addIconsFromDict',
           'setInitialIconsDict']

##### py2exe support

def main_is_frozen():
    return (hasattr(sys, "frozen") or # new py2exe
           hasattr(sys, "importers") # old py2exe
           or imp.is_frozen("__main__")) # tools/freeze

#### Icons
icondict = {}    # mapping from filename to string containing

class IconStorage(debugmixin):
    def __init__(self):
        self.il=wx.ImageList(16,16)
        self.map={}
        self.bitmap={}

        # FIXME: shouldn't depend on icons directory being one level
        # up from this dir.
        if not main_is_frozen():
            self.basedir = os.path.dirname(os.path.dirname(__file__))
        else:
            self.basedir = None

    def set(self, filename, bitmap):
        self.bitmap[filename]=bitmap
        icon=self.il.Add(bitmap)
        assert self.dprint("ICON=%s" % str(icon))
        self.map[filename]=icon

    def load(self, path):
        if path in icondict:
            return self.loadLocal(path)
        else:
            return self.loadFile(path)

    def loadLocal(self, path):
        data = icondict[path]
        stream = StringIO(data)
        img = wx.ImageFromStream(stream)
        img.Rescale(16, 16)
        bitmap=wx.BitmapFromImage(img)
        return bitmap

    def loadFile(self, path):
        if os.path.exists(path) and wx.Image.CanRead(path):
            img = wx.ImageFromBitmap(wx.Bitmap(path))
        else:
            # return placeholder icon if a real one isn't found
            img = wx.ImageFromBitmap(wx.ArtProvider_GetBitmap(wx.ART_QUESTION, wx.ART_OTHER, wx.Size(16,16)))
                
        img.Rescale(16,16)
        assert self.dprint(img)
        bitmap=wx.BitmapFromImage(img)
        return bitmap

    def get(self, filename, dir=None):
        if filename not in self.map:
            if self.basedir is not None:
                if dir is not None:
                    # if a directory is specified, use the whole path name
                    # so as to not conflict with the standard icons
                    filename = os.path.join(dir, filename)
                    path = filename
                else:
                    path = os.path.join(self.basedir,filename)
            else:
                path = filename
            bitmap = self.load(path)
            self.set(filename, bitmap)
        else:
            assert self.dprint("ICON: found icon for %s = %d" % (filename,self.map[filename]))
        return self.map[filename]

    def getBitmap(self,filename, dir=None):
        self.get(filename, dir)
        return self.bitmap[filename]

    def assign(self, notebook):
        # Don't use AssignImageList because the notebook takes
        # ownership of the image list and will delete it when the
        # notebook is deleted.  We're sharing the list, so we don't
        # want the notebook to delete it if the notebook itself
        # deletes it.
        notebook.SetImageList(self.il)

    def assignList(self, list):
        list.SetImageList(self.il, wx.IMAGE_LIST_SMALL)

_iconStorage=None
def getIconStorage(icon=None, path=None):
    global _iconStorage
    if _iconStorage==None:
        _iconStorage=IconStorage()
    if icon:
        return _iconStorage.get(icon, path)
    else:
        return _iconStorage

def getIconBitmap(icon=None, path=None):
    store = getIconStorage()
    if icon:
        return store.getBitmap(icon, path)
    else:
        return wx.ArtProvider_GetBitmap(wx.ART_QUESTION, wx.ART_OTHER, wx.Size(16,16))

def addIconBitmap(name, data):
    store = getIconStorage()
    store.set(name, data)
    
def addIconsFromDirectory(path):
    store = getIconStorage()
    files = glob.glob(os.path.join(path,'*'))
    for path in files:
        filename = os.path.basename(path)
        bitmap = store.load(path)
        store.set(filename, bitmap)

def setInitialIconsDict(d):
    global icondict
    
    icondict = d

def addIconsFromDict(d):
    icondict.update(d)
