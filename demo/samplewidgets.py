"""
Collection of sample widgets without dependencies on other parts of
peppy.  These can be used to provide widgets for example purposes in
minor modes or plugins.
"""

import os

import wx
import wx.lib.customtreectrl as ct

class DemoCustomTree(ct.CustomTreeCtrl):
    def __init__(self, parent, size=wx.DefaultSize):
        ct.CustomTreeCtrl.__init__(self, parent, -1, wx.Point(0, 0), size=size, style=wx.TR_DEFAULT_STYLE | wx.NO_BORDER, ctstyle=ct.TR_HAS_BUTTONS|ct.TR_HAS_VARIABLE_ROW_HEIGHT|ct.TR_HIDE_ROOT)
        #ctstyle=ct.TR_NO_BUTTONS|ct.TR_TWIST_BUTTONS|ct.TR_HAS_VARIABLE_ROW_HEIGHT|ct.TR_HIDE_ROOT|ct.TR_NO_LINES
        root = self.AddRoot("AUI Project")
        items = []
        self.SetFont(wx.Font(7, wx.SWISS, wx.NORMAL, wx.NORMAL))

        imglist = wx.ImageList(12,12, True, 2)
        imglist.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, wx.Size(16,16)))
        imglist.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, wx.Size(16,16)))
        self.AssignImageList(imglist)

        items.append(self.AppendItem(root, "Item 1", image=0))
        items.append(self.AppendItem(root, "Item 2", image=0))
        items.append(self.AppendItem(root, "Item 3", image=0))
        items.append(self.AppendItem(root, "Item 4", image=0))
        items.append(self.AppendItem(root, "Item 5", image=0))

        for ii in xrange(len(items)):
        
            id = items[ii]
            self.AppendItem(id, "Subitem 1", image=1)
            self.AppendItem(id, "Subitem 2", image=1)
            self.AppendItem(id, "Subitem 3", image=1)
            self.AppendItem(id, "Subitem 4", image=1)
            self.AppendItem(id, "Subitem 5", image=1)
        
        #self.Expand(root)

class DemoTree(wx.TreeCtrl):
    def __init__(self, parent, size=wx.DefaultSize):
        wx.TreeCtrl.__init__(self, parent, -1, wx.Point(0, 0), size=size, style=wx.TR_DEFAULT_STYLE | wx.NO_BORDER | wx.TR_HIDE_ROOT)
        
        root = self.AddRoot("AUI Project")
        items = []
        self.SetFont(wx.Font(8, wx.SWISS, wx.NORMAL, wx.NORMAL))

        imglist = wx.ImageList(16,16, True, 2)
        imglist.Add(wx.ArtProvider_GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, wx.Size(16,16)))
        imglist.Add(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, wx.Size(16,16)))
        self.AssignImageList(imglist)

        items.append(self.AppendItem(root, "Item 1", image=0))
        items.append(self.AppendItem(root, "Item 2", image=0))
        items.append(self.AppendItem(root, "Item 3", image=0))
        items.append(self.AppendItem(root, "Item 4", image=0))
        items.append(self.AppendItem(root, "Item 5", image=0))

        for ii in xrange(len(items)):
        
            id = items[ii]
            self.AppendItem(id, "Subitem 1", image=1)
            self.AppendItem(id, "Subitem 2", image=1)
            self.AppendItem(id, "Subitem 3", image=1)
            self.AppendItem(id, "Subitem 4", image=1)
            self.AppendItem(id, "Subitem 5", image=1)
        
        #self.Expand(root)

class MinorNotebook(wx.aui.AuiNotebook):
    def __init__(self, parent, size=wx.DefaultSize):
        wx.aui.AuiNotebook.__init__(self, parent, size=size, style=wx.aui.AUI_NB_WINDOWLIST_BUTTON|wx.aui.AUI_NB_TAB_MOVE|wx.aui.AUI_NB_TAB_SPLIT|wx.aui.AUI_NB_CLOSE_BUTTON|wx.aui.AUI_NB_SCROLL_BUTTONS)
        
        page = DemoTree(self, size=(100,400))
        self.AddPage(page, "Stuff", bitmap=self.getBitmap())

        for num in range(1, 8):
            page = wx.TextCtrl(self, -1, "This is page %d" % num ,
                               style=wx.TE_MULTILINE)
            self.addTab(page, "Page %d" % num)
            
        self.Bind(wx.aui.EVT_AUINOTEBOOK_PAGE_CHANGED, self.OnTabChanged)

    def getBitmap(self):
        img=wx.ImageFromBitmap(wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, wx.Size(16,16)))
        img.Rescale(16,16)
        bitmap=wx.BitmapFromImage(img)
        return bitmap

    def addTab(self,win,title):
        self.AddPage(win, title, bitmap=self.getBitmap())

    def OnTabChanged(self, evt):
        newpage=evt.GetSelection()
        page=self.GetPage(newpage)
        evt.Skip()


class SizeReportCtrl(wx.PyControl):
    """
    Utility control that always reports its client size.  If embedded
    in an AUI manager, it can also display information about the
    position of the window within the managed framework.

    (From the wxPython AUI_DockingWindowMgr.py demo.)
    """

    def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, mgr=None):

        wx.PyControl.__init__(self, parent, id, pos, size, wx.NO_BORDER)
            
        self._mgr = mgr

        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)


    def OnPaint(self, event):

        dc = wx.PaintDC(self)
        
        size = self.GetClientSize()
        s = ("Size: %d x %d")%(size.x, size.y)

        dc.SetFont(wx.NORMAL_FONT)
        w, height = dc.GetTextExtent(s)
        height = height + 3
        dc.SetBrush(wx.WHITE_BRUSH)
        dc.SetPen(wx.WHITE_PEN)
        dc.DrawRectangle(0, 0, size.x, size.y)
        dc.SetPen(wx.LIGHT_GREY_PEN)
        dc.DrawLine(0, 0, size.x, size.y)
        dc.DrawLine(0, size.y, size.x, 0)
        dc.DrawText(s, (size.x-w)/2, ((size.y-(height*5))/2))
        
        if self._mgr:
        
            pi = self._mgr.GetPane(self)
            
            s = ("Layer: %d")%pi.dock_layer
            w, h = dc.GetTextExtent(s)
            dc.DrawText(s, (size.x-w)/2, ((size.y-(height*5))/2)+(height*1))
           
            s = ("Dock: %d Row: %d")%(pi.dock_direction, pi.dock_row)
            w, h = dc.GetTextExtent(s)
            dc.DrawText(s, (size.x-w)/2, ((size.y-(height*5))/2)+(height*2))
            
            s = ("Position: %d")%pi.dock_pos
            w, h = dc.GetTextExtent(s)
            dc.DrawText(s, (size.x-w)/2, ((size.y-(height*5))/2)+(height*3))
            
            s = ("Proportion: %d")%pi.dock_proportion
            w, h = dc.GetTextExtent(s)
            dc.DrawText(s, (size.x-w)/2, ((size.y-(height*5))/2)+(height*4))
        

    def OnEraseBackground(self, event):
        # intentionally empty
        pass        
    

    def OnSize(self, event):
        self.Refresh()
        event.Skip()
