# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Preferences dialog.

This plugin implements the preferences dialog that is used to modify
the default settings of objects that inherit from the ClassSettings
class.
"""
import os

import wx.grid

from peppy import *
from peppy.menu import *
from peppy.trac.core import *
from peppy.configprefs import *
from peppy.lib.iconstorage import *

class Preferences(SelectAction):
    name = "&Preferences..."
    tooltip = "Preferences, settings, and configurations..."
    icon = "icons/wrench.png"
    stock_id = wx.ID_PREFERENCES

    def action(self, pos=-1):
        assert self.dprint("exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        dlg = PreferencesDialog(self.frame)
        retval = dlg.ShowModal()
        dlg.Destroy()


class PreferenceTableModel(wx.grid.PyGridTableBase):
    def __init__(self):
        wx.grid.PyGridTableBase.__init__(self)
        self.cls = None
        self.settings = []
        self.local_settings = set()

        self.normal=wx.grid.GridCellAttr()
        self.normal.SetBackgroundColour("white")
        self.from_parent=wx.grid.GridCellAttr()
        self.from_parent.SetBackgroundColour("gray70")

    def setClass(self, grid, cls):
        oldrows = self.GetNumberRows()
        if 'default_settings' in dir(cls):
            self.cls = cls
            all = set()
            for parent in cls.settings._getMRO():
                all.update(parent.default_settings.keys())
            self.settings = list(all)
            self.settings.sort()
            self.local_settings = set(cls.settings._getAll().keys()) - all
            for setting in self.settings:
                dprint("  %s = %s" % (setting, cls.settings._get(setting)))
        else:
            self.cls = None
            self.settings = []
        newrows = self.GetNumberRows()

        grid.BeginBatch()
        if newrows < oldrows:
            msg = wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_DELETED, newrows, oldrows - newrows)
            grid.ProcessTableMessage(msg)
        elif newrows > oldrows:
            msg = wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED, newrows - oldrows)
            grid.ProcessTableMessage(msg)

        msg = wx.grid.GridTableMessage(self, wx.grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        grid.ProcessTableMessage(msg)
        grid.EndBatch()
        grid.AdjustScrollbars()
        grid.ForceRefresh()

    def GetAttr(self, row, col, kind):
        #attr = [self.even, self.odd][row % 2]
        setting = self.settings[row]
        if setting in self.local_settings:
            attr = self.normal
        else:
            attr = self.from_parent
        attr.IncRef()
        return attr

    def GetNumberRows(self):
        return len(self.settings)

    def GetRowLabelValue(self, row):
        return self.settings[row]

    def GetNumberCols(self):
        return 2

    def GetColLabelValue(self, col):
        if col == 0:
            return "Default"
        else:
            return "User"

    def IsEmptyCell(self, row, col):
        return False

    def GetValue(self, row, col):
        if self.cls is None:
            return ""
        setting = self.settings[row]
        if col==0:
            return str(self.cls.settings._get(setting))
        else:
            d = self.cls.settings._getUser()
            if setting in d:
                return d[setting]
            return ""

    def SetValue(self, row, col, value):
        pass


class PreferenceTable(wx.grid.Grid):
    def __init__(self, parent):
        wx.grid.Grid.__init__(self, parent, -1, size=(400,400))

        self.tablemodel = PreferenceTableModel()
        self.SetTable(self.tablemodel, True)
        self.SetRowLabelSize(200)
        self.SetRowLabelAlignment(wx.ALIGN_LEFT, wx.ALIGN_CENTER)
        
    def setClass(self, cls):
        self.tablemodel.setClass(self, cls)
        

class PreferenceTree(wx.TreeCtrl):
    def __init__(self, parent, style=wx.TR_HIDE_ROOT|wx.TR_HAS_BUTTONS):
        wx.TreeCtrl.__init__(self, parent, -1, size=(200,400), style=style)

        self.AddRoot("The Root Item")
        self.SetPyData(self.GetRootItem(), None)
        getIconStorage().assign(self)

    def FindParent(self, mro, parent=None):
        if parent is None:
            parent = self.GetRootItem()
        if len(mro)==0:
            return parent
        name = mro.pop().__name__
        item, cookie = self.GetFirstChild(parent)
        while item:
            if self.GetItemText(item) == name:
                return self.FindParent(mro, item)
            item, cookie = self.GetNextChild(parent, cookie)
        return None
        
    def AppendClass(self, cls):
        dprint("class=%s mro=%s" % (cls, cls.settings._getMRO()))
        mro = cls.settings._getMRO()
        parent = self.FindParent(mro[1:])
        if parent is not None:
            item = self.AppendItem(parent, mro[0].__name__)
            self.SetPyData(item, cls)

##        self.Bind(wx.EVT_TREE_ITEM_EXPANDED, self.OnItemExpanded, self.tree)
##        self.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.OnItemCollapsed, self.trees)
##        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged, self.tree)
##        self.Bind(wx.EVT_TREE_BEGIN_LABEL_EDIT, self.OnBeginEdit, self.tree)
##        self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.OnEndEdit, self.tree)
##        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate, self.tree)

##        self.tree.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
##        self.tree.Bind(wx.EVT_RIGHT_DOWN, self.OnRightDown)
##        self.tree.Bind(wx.EVT_RIGHT_UP, self.OnRightUp)

    def SortRecurse(self, parent=None):
        if parent is None:
            parent = self.GetRootItem()
        self.SortChildren(parent)
        item, cookie = self.GetFirstChild(parent)
        while item:
            self.SortRecurse(item)
            item, cookie = self.GetNextChild(parent, cookie)
        
    
    def OnCompareItems(self, item1, item2):
        t1 = self.GetItemText(item1)
        t2 = self.GetItemText(item2)
        if t1 < t2: return -1
        if t1 == t2: return 0
        return 1


class PreferencesDialog(wx.Dialog):
    def __init__(self, parent, title="Preferences"):
        wx.Dialog.__init__(self, parent, -1, title,
                           size=wx.DefaultSize, pos=wx.DefaultPosition, 
                           style=wx.DEFAULT_DIALOG_STYLE)


        sizer = wx.BoxSizer(wx.VERTICAL)

        label = wx.StaticText(self, -1, "This is a placeholder for the Preferences dialog")
        sizer.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        main = wx.BoxSizer(wx.HORIZONTAL)
        self.tree = PreferenceTree(self)
        classes = wx.GetApp().getSubclasses(ClassSettings)
        dprint(classes)
        for cls in classes:
            self.tree.AppendClass(cls)
            if 'default_settings' in dir(cls):
                attrs = cls.default_settings.keys()
                attrs.sort()
                for attr in attrs:
                    dprint("  %s = %s" % (attr, cls.default_settings[attr]))
        self.tree.SortRecurse()
        self.tree.ExpandAll()
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnSelChanged, self.tree)
        main.Add(self.tree, 0, wx.EXPAND, border=0)

        self.table = PreferenceTable(self)
        main.Add(self.table, 0, wx.EXPAND, border=0)
        
        sizer.Add(main, 0, wx.EXPAND, border=0)

        btnsizer = wx.StdDialogButtonSizer()
        
        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

    def OnSelChanged(self, evt):
        self.item = evt.GetItem()
        if self.item:
            cls = self.tree.GetItemPyData(self.item)
            self.table.setClass(cls)
        evt.Skip()




class PreferencesPlugin(Component):
    implements(IMenuItemProvider)

    def getMenuItems(self):
        yield (None,"Edit",MenuItem(Preferences).after("lastsep"))
