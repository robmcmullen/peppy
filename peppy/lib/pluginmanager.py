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
from peppy.lib.column_autosize import *

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


class PluginList(wx.ListCtrl, CheckListCtrlMixin, ColumnAutoSizeMixin, debugmixin):
    def __init__(self, parent, pm):
        wx.ListCtrl.__init__(self, parent, size=(200,400), style=wx.LC_REPORT)
        CheckListCtrlMixin.__init__(self)
        ColumnAutoSizeMixin.__init__(self)

        self.plugin_manager = pm
        cats = self.plugin_manager.getCategories()
        self.plugins = []
        for cat in cats:
            plugins = self.plugin_manager.getPluginsOfCategory(cat)
            #print plugins
            self.plugins.extend(plugins)
        self.dprint(self.plugins)
        # Sort first by name, then by version number
        self.plugins.sort(key=lambda s:(s.name, s.version))
        
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)

        self.skip_verify = False

        self.createColumns()
        self.reset()

    def createColumns(self):
        self.InsertSizedColumn(0, "Name")
        self.InsertSizedColumn(1, "Version")

    def getPlugin(self, index=-1):
        if index == -1:
            index = self.GetNextItem(-1, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
        if index == -1:
            index = 0
        return self.plugins[index]

    def OnItemActivated(self, evt):
        index = evt.GetIndex()
        dprint("selected plugin %d: %s" % (index, self.plugins[index]))
        evt.Skip()

    def reset(self):
        index = 0
        list_count = self.GetItemCount()
        for plugin in self.plugins:
            self.dprint(plugin.name)
            if index >= list_count:
                self.InsertStringItem(sys.maxint, plugin.name)
            else:
                self.SetStringItem(index, 0, plugin.name)
            self.dprint(plugin.version)
            self.SetStringItem(index, 1, str(plugin.version))

            index += 1

        if index < list_count:
            for i in range(index, list_count):
                # always delete the first item because the list gets
                # shorter by one each time.
                self.DeleteItem(index)
        
        # Once all the plugin items are in the list, set the checkbox
        # state to indicate which are active
        index = 0
        for plugin in self.plugins:
            self.CheckItem(index, plugin.plugin_object.is_activated)
            index += 1
        self.ResizeColumns()

    def OnCheckItem(self, index, flag):
        if flag:
            what = "checked"
        else:
            what = "unchecked"
        self.dprint("toggling plugin %d: %s = %s" % (index, self.plugins[index],
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
    """Addition to the PrefPanel that shows additional plugin info.
    
    Plugins include some additional informational text that is displayed
    using this small addition to the PrefPanel.  Otherwise, the preference
    dialog page is the same an a normal preference page.
    """
    def __init__(self, parent, plugin_info):
        self.plugin_info = plugin_info
        PrefPanel.__init__(self, parent, plugin_info.plugin_object)
        
    def create(self):
        row = 0
        order = ['path', 'author', 'version', 'website', 'copyright',
                 'description']
        box = wx.StaticBox(self, -1, self.plugin_info.name)
        bsizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        self.sizer.Add(bsizer)
        grid = wx.GridBagSizer(2,5)
        bsizer.Add(grid, 0, wx.EXPAND)
                
        for info in order:
            title = wx.StaticText(self, -1, info)
            grid.Add(title, (row,0))

            value = wx.StaticText(self, -1, str(getattr(self.plugin_info, info)))
            grid.Add(value, (row,1), flag=wx.EXPAND)

            row += 1
            
        PrefPanel.create(self)
            
class PluginPage(wx.SplitterWindow):
    """Page representing the preference list and panel for a plugin.
    
    This page differs from the standard preference page in that it uses
    the plugin list from the application's plugin manager and ignores
    the class list that could be generated by finding all subclasses of
    IPeppyPlugin.
    """
    def __init__(self, parent, pm, *args, **kwargs):
        wx.SplitterWindow.__init__(self, parent, -1, *args, **kwargs)
        self.SetMinimumPaneSize(50)
        
        self.plugin_manager = pm
        
        self.panels = {}
        list = self.createList()
        pref = self.getPanel(list.getPlugin(0))

        self.SplitVertically(list, pref, -500)
        self.SetSashGravity(0.4)

        list.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnItemSelected)
        list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)

    def createList(self):
        """Create the wxListCtrl from the list of plugins"""
        list = PluginList(self, self.plugin_manager)
        list.SetItemState(0, wx.LIST_STATE_SELECTED, wx.LIST_STATE_SELECTED)
        return list
        
    def OnItemSelected(self, evt):
        index = evt.GetIndex()
        list = evt.GetEventObject()
        plugin_info = list.getPlugin(index)
        if plugin_info:
            self.changePanel(plugin_info)
        evt.Skip()
    
    def getPanel(self, plugin_info=None):
        """Get or create the pref panel for the requested plugin"""
        if plugin_info is None:
            plugin_info = self.GetWindow1().getPlugin()
        if plugin_info in self.panels:
            pref = self.panels[plugin_info]
        else:
            pref = PluginPanel(self, plugin_info)
            self.panels[plugin_info] = pref
        return pref

    def changePanel(self, plugin_info=None):
        """Change the currently shown panel"""
        old = self.GetWindow2()
        pref = self.getPanel(plugin_info)
        self.ReplaceWindow(old, pref)
        old.Hide()
        pref.Show()
        pref.Layout()

    def OnItemActivated(self, evt):
        evt.Skip()

    def applyPreferences(self):
        """On an OK from the dialog, process any updates to the plugins"""
        # Look at all the panels that have been created: this gives us
        # an upper bound on what preferences may have changed.
        for plugin, pref in self.panels.iteritems():
            pref.update()

        # After the preferences have been changed, activate or
        # deactivate plugins as required
        self.GetWindow1().update()


class PluginDialog(wx.Dialog):
    dialog_title = "Plugin Control Panel and Preferences"
    static_title = "Activate and deactivate plugins and change plugin preferences using this panel."
    
    def __init__(self, parent, pm, title=None):
        if title is None:
            title = self.dialog_title
        wx.Dialog.__init__(self, parent, -1, title,
                           size=(700, 500), pos=wx.DefaultPosition, 
                           style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)

        sizer = wx.BoxSizer(wx.VERTICAL)

        if self.static_title:
            label = wx.StaticText(self, -1, self.static_title)
            sizer.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 5)

        self.page = PluginPage(self, pm)
        sizer.Add(self.page, 1, wx.EXPAND)

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

        self.Layout()

    def applyPreferences(self):
        self.page.applyPreferences()



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
        dprint(plugins)

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
