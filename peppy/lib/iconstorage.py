# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
import os,sys,re

import wx

from peppy.debug import *

__all__ = ['getIconStorage', 'getIconBitmap', 'addIconBitmap']

#### Icons

class IconStorage(debugmixin):
    def __init__(self):
        self.il=wx.ImageList(16,16)
        self.map={}
        self.bitmap={}

        # FIXME: shouldn't depend on icons directory being one level
        # up from this dir.
        self.basedir=os.path.dirname(os.path.dirname(__file__))

    def set(self, filename, bitmap):
        self.bitmap[filename]=bitmap
        icon=self.il.Add(bitmap)
        self.dprint("ICON=%s" % str(icon))
        self.map[filename]=icon

    def get(self,filename):
        if filename not in self.map:
            img=wx.ImageFromBitmap(wx.Bitmap(os.path.join(self.basedir,filename)))
            img.Rescale(16,16)
            self.dprint(img)
            bitmap=wx.BitmapFromImage(img)
            self.set(filename, bitmap)
        else:
            self.dprint("ICON: found icon for %s = %d" % (filename,self.map[filename]))
        return self.map[filename]

    def getBitmap(self,filename):
        self.get(filename)
        return self.bitmap[filename]

    def assign(self,notebook):
        # Don't use AssignImageList because the notebook takes
        # ownership of the image list and will delete it when the
        # notebook is deleted.  We're sharing the list, so we don't
        # want the notebook to delete it if the notebook itself
        # deletes it.
        notebook.SetImageList(self.il)

_iconStorage=None
def getIconStorage(icon=None):
    global _iconStorage
    if _iconStorage==None:
        _iconStorage=IconStorage()
    if icon:
        return _iconStorage.get(icon)
    else:
        return _iconStorage

def getIconBitmap(icon=None):
    store = getIconStorage()
    if icon:
        return store.getBitmap(icon)
    else:
        return wx.ArtProvider_GetBitmap(wx.ART_QUESTION, wx.ART_OTHER, wx.Size(16,16))

def addIconBitmap(name, data):
    store = getIconStorage()
    store.set(name, data)
    
