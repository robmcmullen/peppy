#-----------------------------------------------------------------------------
# Name:        pluginmanager.py
# Purpose:     global plugin management and dialog to control them
#
# Author:      Rob McMullen
#
# Created:     2007
# RCS-ID:      $Id: $
# Copyright:   (c) 2007 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""Plugin management support

This module provides plugin management for yapsy plugins.
"""

import os, sys
from cStringIO import StringIO

import wx
import wx.stc
from wx.lib.pubsub import Publisher
from wx.lib.evtmgr import eventManager
from wx.lib.mixins.listctrl import CheckListCtrlMixin

from peppy.lib.userparams import *
from peppy.lib.columnsizer import *

try:
    from peppy.debug import *
except:
    def dprint(txt=""):
        print txt

    class debugmixin(object):
        debuglevel = 0
        def dprint(self, txt=""):
            if self.debuglevel > 0 and txt:
                dprint(txt)
            return True


class PluginList(wx.ListCtrl, CheckListCtrlMixin, ColumnSizerMixin, debugmixin):
    def __init__(self, parent, pm):
        wx.ListCtrl.__init__(self, parent, size=(200,400), style=wx.LC_REPORT)
        CheckListCtrlMixin.__init__(self)
        ColumnSizerMixin.__init__(self)

        self.plugin_manager = pm
        cats = self.plugin_manager.getCategories()
        self.plugins = []
        for cat in cats:
            plugins = self.plugin_manager.getPluginsOfCategory(cat)
            print plugins
            self.plugins.extend(plugins)
        print self.plugins
        # Sort first by name, then by version number
        self.plugins.sort(key=lambda s:(s.name, s.version))
        
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)

        self.skip_verify = False

        self.createColumns()
        self.reset()
        self.resizeColumns()

    def createColumns(self):
        self.InsertColumn(0, "Name")
        self.SetColumnWidth(0, wx.LIST_AUTOSIZE)
        self.InsertColumn(1, "Version")
        self.SetColumnWidth(1, wx.LIST_AUTOSIZE)

    def getPlugin(self, index):
        return self.plugins[index]

    def OnItemActivated(self, evt):
        index = evt.GetIndex()
        dprint("selected plugin %d: %s" % (index, self.plugins[index]))
        evt.Skip()

    def reset(self):
        index = 0
        list_count = self.GetItemCount()
        for plugin in self.plugins:
            print plugin.name
            if index >= list_count:
                self.InsertStringItem(sys.maxint, plugin.name)
            else:
                self.SetStringItem(index, 0, plugin.name)
            print plugin.version
            self.SetStringItem(index, 1, str(plugin.version))

            self.CheckItem(index, plugin.plugin_object.is_activated)

            index += 1

        if index < list_count:
            for i in range(index, list_count):
                # always delete the first item because the list gets
                # shorter by one each time.
                self.DeleteItem(index)

    def OnCheckItem(self, index, flag):
        if flag:
            what = "checked"
        else:
            what = "unchecked"
        dprint("toggling plugin %d: %s = %s" % (index, self.plugins[index],
                                                what))
        if not self.skip_verify:
            # If we aren't currently verifying another item, verify
            # that only one plugin of the same name is active
            self.verify(index)

    def verify(self, selected_index):
        """Check two things:

        * make sure a plugin that is currently in use isn't deactivated

        * When multiple versions of the same plugin exist, verify
        that only the selected version is active and all other
        versions are deactivated.
        """
        # CheckItem always calls OnCheckItem, so setting the checked
        # state within this method would cause in infinite loop
        # without this skip_verify flag
        self.skip_verify = True
        selected = self.plugins[selected_index]

        # If the user tried to disable an in-use plugin, don't allow it
        if hasattr(selected.plugin_object, 'isInUse'):
            if not self.IsChecked(selected_index) and selected.plugin_object.isInUse():
                self.CheckItem(selected_index, True)
                self.skip_verify = False
                dlg = wx.MessageDialog(self, "Plugin %s in use.\n\nCan't deactivate a running plugin." % selected.name, "Plugin in use", wx.OK | wx.ICON_EXCLAMATION )
                dlg.ShowModal()
                return

        # otherwise, make sure the selected plugin doesn't have any
        # other versions active
        index = 0
        for plugin in self.plugins:
            if plugin.name == selected.name and plugin != selected:
                self.CheckItem(index, False)
            index += 1
        self.skip_verify = False

    def update(self):
        index = 0
        for plugin in self.plugins:
            activated = self.IsChecked(index)
            if activated != plugin.plugin_object.is_activated:
                if activated:
                    dprint("Activating %s" % plugin.plugin_object)
                    plugin.plugin_object.activate()
                else:
                    dprint("Deactivating %s" % plugin.plugin_object)
                    plugin.plugin_object.deactivate()
            index += 1


class PluginPanel(PrefPanel):
    def __init__(self, parent, plugin_info):
        self.plugin_info = plugin_info
        PrefPanel.__init__(self, parent, plugin_info.plugin_object)
        
    def create(self):
        row = 0
        order = ['name', 'path', 'author', 'version', 'website', 'copyright']
        for info in order:
            title = wx.StaticText(self, -1, info)
            self.sizer.Add(title, (row,0))

            value = wx.StaticText(self, -1, str(getattr(self.plugin_info, info)))
            self.sizer.Add(value, (row,1), flag=wx.EXPAND)

            row += 1

    def update(self):
        # update preferences here
        pass
            

class PluginDialog(wx.Dialog):
    dialog_title = "Plugin Control Panel and Preferences"
    static_title = "Activate and deactivate plugins and change plugin preferences using this panel."
    
    def __init__(self, parent, pm, title=None):
        if title is None:
            title = self.dialog_title
        wx.Dialog.__init__(self, parent, -1, title,
                           size=(700, 500), pos=wx.DefaultPosition, 
                           style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        self.plugin_manager = pm

        sizer = wx.BoxSizer(wx.VERTICAL)

        if self.static_title:
            label = wx.StaticText(self, -1, self.static_title)
            sizer.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        self.splitter = wx.SplitterWindow(self)
        self.splitter.SetMinimumPaneSize(50)
        self.list = self.createList(self.splitter)
        
        self.panels = {}
        pref = self.createPanel(self.list.getPlugin(0))

        self.splitter.SplitVertically(self.list, pref, -500)
        self.splitter.SetSashGravity(0.4)
        sizer.Add(self.splitter, 1, wx.EXPAND)

        btnsizer = wx.StdDialogButtonSizer()
        
        btn = wx.Button(self, wx.ID_OK)
        btn.SetDefault()
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        self.list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Layout()

    def createList(self, parent):
        list = PluginList(parent, self.plugin_manager)
        list.SetItemState(0, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
        return list
        
    def createPanel(self, plugin_info):
        pref = PluginPanel(self.splitter, plugin_info)
        self.panels[plugin_info] = pref
        return pref

    def OnItemSelected(self, evt):
        index = evt.GetIndex()
        plugin_info = self.list.getPlugin(index)
        if plugin_info:
            if plugin_info in self.panels:
                pref = self.panels[plugin_info]
            else:
                pref = self.createPanel(plugin_info)
            old = self.splitter.GetWindow2()
            self.splitter.ReplaceWindow(old, pref)
            old.Hide()
            pref.Show()
            pref.Layout()
        evt.Skip()

    def OnItemActivated(self, evt):
        evt.Skip()

    def applyPreferences(self):
        # Look at all the panels that have been created: this gives us
        # an upper bound on what preferences may have changed.
        for plugin, pref in self.panels.iteritems():
            pref.update()

        # After the preferences have been changed, activate or
        # deactivate plugins as required
        self.list.update()



if __name__ == "__main__":
    from peppy.yapsy.VersionedPluginManager import *
    import logging
    
    logging.basicConfig(level=logging.DEBUG)

    app = wx.PySimpleApp()

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../tests/yapsy')
    app.plugin_manager = VersionedPluginManager(
        directories_list=[path],
        plugin_info_ext="version-plugin",
        )
    # load the plugins that may be found
    app.plugin_manager.collectPlugins()

    cats = app.plugin_manager.getCategories()
    for cat in cats:
        plugins = app.plugin_manager.getPluginsOfCategory(cat)
        print plugins

    dlg = PluginDialog(None, app.plugin_manager)
    dlg.Show(True)

    # Close down the dialog on a button press
    import sys
    def process(evt):
        dprint(evt)
        if evt.GetId() == wx.ID_OK:
            dlg.applyPreferences()
        sys.exit()
    dlg.Bind(wx.EVT_BUTTON, process)

    app.MainLoop()
