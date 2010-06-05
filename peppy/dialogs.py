# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import wx


class CustomDialog(wx.Dialog):
    """Base class for dialog box that can change the default button names.
    
    Standard message dialogs don't seem to allow changing the button names, and
    I wanted the buttons to be less ambiguous than a yes/no or ok/cancel.
    """
    def __init__(self, parent, text=''):
        wx.Dialog.__init__(self, parent, -1, "Unsaved Changes",
                           pos = wx.DefaultPosition,
                           size = wx.DefaultSize,
                           style = wx.DEFAULT_DIALOG_STYLE)
        
        txtsizer = wx.BoxSizer(wx.HORIZONTAL)
        if wx.Platform == "__WXGTK__":
            bitmapsize=(48,48)
        else:
            bitmapsize=(32,32)
        bitmap=wx.StaticBitmap(self, -1, wx.ArtProvider.GetBitmap(wx.ART_WARNING, wx.ART_OTHER, bitmapsize))
        txtsizer.Add(bitmap, 0, wx.ALL, 4)
        stat = wx.StaticText(self, -1, text)
        txtsizer.Add(stat, 0, wx.ALL, 4)
        
        dlgsizer = wx.BoxSizer(wx.VERTICAL)
        dlgsizer.Add(txtsizer, 0, wx.ALL, 10)
        
        btnsizer = wx.StdDialogButtonSizer()
        self.setButtons(btnsizer)
        btnsizer.Realize()
        
        dlgsizer.Add(btnsizer, 0, wx.ALL | wx.ALIGN_RIGHT, 10)
        
        self.SetSizer(dlgsizer)
        
        self.Layout()
        self.Fit()


class CustomOkDialog(CustomDialog):
    """Custom dialog used to confirm application exit.
    """
    def __init__(self, parent, text, ok_message, cancel_message):
        self.ok_message = ok_message
        self.cancel_message = cancel_message
        CustomDialog.__init__(self, parent, text)
    
    def setButtons(self, btnsizer):
        ok = wx.Button(self, wx.ID_NO, self.ok_message)
        btnsizer.SetNegativeButton(ok)
        self.Bind(wx.EVT_BUTTON, self.OnOK, ok)
        
        cancel = wx.Button(self, wx.ID_YES, self.cancel_message)
        btnsizer.SetAffirmativeButton(cancel)
        self.Bind(wx.EVT_BUTTON, self.OnCancel, cancel)
    
    def OnOK(self, evt):
        self.EndModal(wx.ID_OK)

    def OnCancel(self, evt):
        self.EndModal(wx.ID_CANCEL)


class QuitDialog(CustomOkDialog):
    """Custom dialog used to confirm application exit.
    """
    def __init__(self, parent, unsaved_buffers):
        text = "The following files have unsaved changes:\n\n%s\n\nIf you quit now, these changes will be lost." % "\n".join([buf.displayname for buf in unsaved_buffers])
        ok = "Quit and Discard Changes"
        cancel = "Don't Quit"
        CustomOkDialog.__init__(self, parent, text, ok, cancel)
