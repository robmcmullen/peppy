# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import wx

class QuitDialog(wx.Dialog):
    """
    Custom dialog used to confirm application exit.  Standard message
    dialogs don't seem to allow changing the button names, and I
    wanted the buttons to be less ambiguous than a yes/no or
    ok/cancel.
    """
    def __init__(self, parent, unsaved):
        wx.Dialog.__init__(self, parent, -1, "Unsaved Changes",
                           pos = wx.DefaultPosition,
                           size = wx.DefaultSize,
                           style = wx.DEFAULT_DIALOG_STYLE)
        
        discard = wx.Button(self, wx.ID_NO, "Quit and Discard Changes")
        self.Bind(wx.EVT_BUTTON, self.OnQuit, discard)
        cancel = wx.Button(self, wx.ID_YES, "Don't Quit")
        self.Bind(wx.EVT_BUTTON, self.OnCancel, cancel)
        
        txtsizer = wx.BoxSizer(wx.HORIZONTAL)
        if wx.Platform == "__WXGTK__":
            bitmapsize=(48,48)
        else:
            bitmapsize=(32,32)
        bitmap=wx.StaticBitmap(self, -1, wx.ArtProvider.GetBitmap(wx.ART_WARNING, wx.ART_OTHER, bitmapsize))
        txtsizer.Add(bitmap, 0, wx.ALL, 4)
        stat = wx.StaticText(self, -1, "The following files have unsaved changes:\n\n%s\n\nIf you quit now, these changes will be lost." % "\n".join([buf.displayname for buf in unsaved]))
        txtsizer.Add(stat, 0, wx.ALL, 4)
        
        dlgsizer = wx.BoxSizer(wx.VERTICAL)
        dlgsizer.Add(txtsizer, 0, wx.ALL, 10)
        
        btnsizer = wx.StdDialogButtonSizer()
        btnsizer.SetNegativeButton(discard)
        btnsizer.SetAffirmativeButton(cancel)
        btnsizer.Realize()
        
        dlgsizer.Add(btnsizer, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        
        self.SetSizer(dlgsizer)
        
        self.Layout()
        self.Fit()

    def OnQuit(self, evt):
        self.EndModal(wx.ID_OK)

    def OnCancel(self, evt):
        self.EndModal(wx.ID_CANCEL)
