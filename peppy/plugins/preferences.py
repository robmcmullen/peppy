# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Preferences dialog.

This plugin implements the preferences dialog that is used to modify
the default settings of objects that inherit from the ClassSettings
class.
"""
import os

from wx.lib.pubsub import Publisher
import wx.grid

from peppy.menu import *
from peppy.trac.core import *
from peppy.configprefs import *
from peppy.lib.iconstorage import *

class Preferences(SelectAction):
    name = _("&Preferences...")
    tooltip = _("Preferences, settings, and configurations...")
    icon = "icons/wrench.png"
    stock_id = wx.ID_PREFERENCES

    def action(self, pos=-1):
        assert self.dprint("exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        dlg = PreferencesDialog(self.frame)
        retval = dlg.ShowModal()
        if retval == wx.ID_OK:
            dlg.applyPreferences()
            Publisher().sendMessage('settingsChanged')
        dlg.Destroy()


class PreferenceTableModel(wx.grid.PyGridTableBase):
    def __init__(self):
        wx.grid.PyGridTableBase.__init__(self)
        self.cls = None
        self.settings = []
        self.local_settings = set()

        self.default_color = wx.Color(240, 240, 240)
        self.local_color = wx.Color(255, 255, 255)
        self.user_color = wx.Color(240, 255, 240)

    def setClass(self, grid, cls):
        oldrows = self.GetNumberRows()
        if 'default_settings' in dir(cls):
            self.cls = cls
            if 'preference_dialog_settings' not in dir(self.cls):
                self.cls.preference_dialog_settings = {}
                
            all = set()
            for parent in cls.settings._getMRO():
                if 'default_settings' in dir(parent):
                    all.update(parent.default_settings.keys())
            self.settings = list(all)
            self.settings.sort()
            self.local_settings = set(cls.default_settings.keys())
##            for setting in self.settings:
##                dprint("  %s = %s" % (setting, cls.settings._get(setting)))
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
        setting = self.settings[row]
        attr = wx.grid.GridCellAttr()
        if col==0:
            attr.SetReadOnly(True)
            if setting in self.local_settings:
                attr.SetBackgroundColour(self.local_color)
            else:
                attr.SetBackgroundColour(self.default_color)
        else:
            d = self.cls.settings._getUser()
            if setting in d or setting in self.cls.preference_dialog_settings:
                attr.SetBackgroundColour(self.user_color)
            else:
                attr.SetBackgroundColour(self.default_color)
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
            return str(self.cls.settings._get(setting, user=False))
        else:
            d = self.cls.preference_dialog_settings
            if setting in d:
                return d[setting]
            d = self.cls.settings._getUser()
            if setting in d:
                return d[setting]
            return ""

    def SetValue(self, row, col, value):
        if col==1:
            setting = self.settings[row]
            d = self.cls.preference_dialog_settings
            if value=="":
                # first, try to delete it in the preference dialog
                # settings list
                if setting in d:
                    del d[setting]
                else:
                    # it hasn't been set during this call to
                    # preference dialog, so try to delete it from the
                    # user settings.
                    d = self.cls.settings._getUser()
                    if setting in d:
                        self.cls.settings._del(setting)
            else:
                old = self.cls.settings._get(setting, user=False)
                dprint("old = %s" % str(old))
                if isinstance(old, bool):
                    # bool has to go first, because according to
                    # isinstance, a bool is also an int.
                    if value.lower() in [_('true'), _('on'), _('yes'), '1']:
                        d[setting] = True
                    else:
                        d[setting] = False
                elif isinstance(old, int):
                    d[setting] = int(value)
                elif isinstance(old, float):
                    d[setting] = float(value)
                else:
                    d[setting] = value


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
    def __init__(self, parent, style=wx.TR_HAS_BUTTONS):
        if wx.Platform != '__WXMSW__':
            style |= wx.TR_HIDE_ROOT
        wx.TreeCtrl.__init__(self, parent, -1, size=(200,400), style=style)

        getIconStorage().assign(self)
        self.AddRoot("Preferences")
        self.SetPyData(self.GetRootItem(), None)
        self.SetItemImage(self.GetRootItem(), getIconStorage("icons/wrench.png"))

    def ExpandAll(self):
        self.ExpandAllChildren(self.GetFirstVisibleItem())

    def FindParent(self, mro, parent=None):
        if parent is None:
            parent = self.GetRootItem()
        if len(mro)==0:
            return parent
        cls = mro.pop()
        if 'default_settings' not in dir(cls):
            # ignore intermediate subclasses that don't have any
            # default settings
            return self.FindParent(mro, parent)
        name = cls.__name__
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
            dprint("  found parent = %s" % self.GetItemText(parent))
            item = self.AppendItem(parent, mro[0].__name__)
            if hasattr(cls, 'icon') and cls.icon is not None:
                self.SetItemImage(item, getIconStorage(cls.icon))
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

    def applyRecurse(self, parent=None):
        if parent is None:
            parent = self.GetRootItem()
        cls = self.GetItemPyData(parent)
        if 'preference_dialog_settings' in dir(cls):
            for key, val in cls.preference_dialog_settings.iteritems():
                dprint("setting %s[%s]=%s" % (cls.__name__, key, val))
                cls.settings._set(key, val)
            cls.preference_dialog_settings.clear()
        item, cookie = self.GetFirstChild(parent)
        while item:
            self.applyRecurse(item)
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

        label = wx.StaticText(self, -1, _("This is a placeholder for the Preferences dialog"))
        sizer.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        main = wx.BoxSizer(wx.HORIZONTAL)
        self.tree = PreferenceTree(self)
        classes = getAllSubclassesOf(ClassSettings)
        dprint(classes)
        for cls in classes:
            self.tree.AppendClass(cls)
            if 'default_settings' in dir(cls):
                attrs = cls.default_settings.keys()
                attrs.sort()
##                for attr in attrs:
##                    dprint("  %s = %s" % (attr, cls.default_settings[attr]))
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

    def applyPreferences(self):
        self.tree.applyRecurse()


class PreferencesPlugin(Component):
    implements(IMenuItemProvider)

    def getMenuItems(self):
        yield (None,_("Edit"),MenuItem(Preferences).after(_("lastsep")))
