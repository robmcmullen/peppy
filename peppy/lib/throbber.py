import wx
import wx.aui

from wx.lib.embeddedimage import PyEmbeddedImage
import wx.lib.throbber

data = PyEmbeddedImage(
    "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"
    "Sq6AAEsAAAAASUVORK5CYII=")

class Throbber(wx.lib.throbber.Throbber):
    def __init__(self, parent):
        wx.lib.throbber.Throbber.__init__(self, parent, -1, data.GetBitmap(),
                                          frames=12, frameWidth=16)
