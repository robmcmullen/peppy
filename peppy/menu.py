# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Dynamic menubar and toolbar system.

This module implements the menubar and toolbar system that is based on
actions linked to particular major modes.  When the major mode is
changed, the menu and toolbar system changes with it to only show
those actions that are applicable to the current state of the frame.
"""

import os,sys,time
import wx

import weakref

from peppy.debug import *

from peppy.lib.iconstorage import *
from peppy.lib.wxemacskeybindings import *

from peppy.yapsy.plugins import *


class UserActionClassList(debugmixin):
    """Creates a list of actions for a major mode
    
    This class creates a list of action classes and a sorted list of actions
    ready to be populated into a menu.
    """
    default_menu_weights = {}
    
    @classmethod
    def setDefaultMenuBarWeights(cls, weights, override=False):
        """Set the default menubar weights.
        
        Weights is a mapping of the menu name to the sort order of the
        menu name.  By default the sort order of the menu ranges from
        0 to 1000, and floating-point numbers are OK.
        """
        if override:
            cls.default_menu_weights.clear()
        if not cls.default_menu_weights:
            cls.default_menu_weights.update(weights)
    
    def __init__(self, mode):
        """Initialize the mapping with the new set of actions.
        
        The ordering of the menu items is set here, but nothing is actually
        mapped to a menubar or a toolbar until either updateMenuActions or
        updateToolbarActions is called.
        
        frame: parent Frame object
        action_classes: list of possible action classes (i.e.  not instantiated
        classes, but the classes themselves.  They will be instantiated when
        they are mapped to a menubar or toolbar.
        """
        self.action_classes = []
        self.menus = {'root':[]}
        self.getActiveActions(mode)
        self.sortActions()
    
    def getActiveActions(self, mode):
        plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
        #assert self.dprint(plugins)

        actions = []
        for plugin in plugins:
            assert self.dprint("collecting from plugin %s" % plugin)
            
            # old-style way of checking each action for compatibility
            for action in plugin.getActions():
                if action.worksWithMajorMode(mode):
                    # Only if the action works with the major mode do we want
                    # it to be an action that fires events
                    actions.append(action)

            # new-style way of having the plugin check for compatibility
            actions.extend(plugin.getCompatibleActions(mode))
        self.action_classes = actions

    def getInfo(self, action):
        """Get menu ordering info from the action
        
        The class attribute default_menu is decoded here into the mode
        (either a text string or None indicating the action is applicable
        to all major modes), the menu title, menu weight (sorting order of
        the menu itself) and the item weight (sorting order of the action
        within the menu).
        """
        if len(action.default_menu) == 0:
            raise AttributeError('Menu position not specified for %s' % action.name)
        info = action.default_menu
        self.dprint("action: name=%s info=%s" % (action.name, info))
        if isinstance(info, str):
            menu_title = info
            menu_weight = None
            weight = 500
        else:
            if isinstance(info[0], list) or isinstance(info[0], tuple):
                menu_title = info[0][0]
                menu_weight = info[0][1]
            else:
                menu_title = info[0]
                menu_weight = None
            weight = info[1]
        return menu_title, menu_weight, weight
    
    def getParent(self, menu_title):
        """Get the parent menu title.
        
        Submenus are indicated by a / in the menu title
        """
        hier = menu_title.split('/')
        if len(hier) == 1:
            return 'root'
        else:
            return '/'.join(hier[0:-1])
    
    def sortActions(self):
        """Sort the actions into a hierarchy of menus
        
        Menus and menu items are sorted here by the weights given
        in the default_menu attribute of the action.
        """
        # list to hold the sort order of top-level menubar entries and
        # pull-right menus
        menu_weights = {}
        
        # First, loop through to get all actions matched to their
        # menu title
        for actioncls in self.action_classes:
            self.dprint("%s in current mode list" % actioncls)

            if actioncls.default_menu is None or len(actioncls.default_menu) == 0:
                # It's a command event only, not a menu or toolbar
                continue
            
            menu_title, menu_weight, weight = self.getInfo(actioncls)
            if menu_title not in self.menus:
                self.menus[menu_title] = []
                menu_weights[menu_title] = 500

            # If the item weight is less than zero, a separator will
            # be added to the menu before the item
            self.menus[menu_title].append((abs(weight), actioncls, weight<0))
            if menu_weight is not None:
                menu_weights[menu_title] = menu_weight
            elif menu_title in self.default_menu_weights:
                menu_weights[menu_title] = self.default_menu_weights[menu_title]
        
        # Give weights to the top level menus and all pull-right submenus
        for menu_title, menu_weight in menu_weights.iteritems():
            parent = self.getParent(menu_title)

            # Corner case when you've created a submenu, but nothing
            # in the parent menu
            if parent not in self.menus:
                self.dprint("PARENT NOT IN MENUS: %s" % parent)
                self.menus[parent] = []
                search = parent
                while search != 'root':
                    submenu = search.split('/')[-1]
                    search = self.getParent(search)
                    self.dprint("submenu = %s, search = %s" % (submenu, search))
                    self.dprint(self.menus[search])
                    found = False
                    for weight, actioncls, sep in self.menus[search]:
                        if isinstance(actioncls, str) and actioncls == submenu:
                            found = True
                            break
                    if not found:
                        # Need to make sure all intermediate menus are
                        # created, and if it's a default menu, make sure
                        # we're using the correct weight
                        if submenu in self.default_menu_weights:
                            weight = self.default_menu_weights[submenu]
                        else:
                            weight = 500
                        self.menus[search].append((weight, submenu, False))
            if menu_weight < 0:
                menu_weight = abs(menu_weight)
                sep = True
            else:
                sep = False
            self.menus[parent].append((menu_weight, menu_title, sep))
        
        # For each menu, sort all the items within that group
        sorted = {}
        for title, items in self.menus.iteritems():
            items.sort()
            sorted[title] = items
        self.menus = sorted
        self.dprint(self.menus.keys())
    

class UserActionMap(debugmixin):
    """Creates a mapping of actions for a frame.
    
    This class creates the ordering of the menubar, and maps actions to menu
    items.  Note that the order of the menu titles is required here and can't
    be added to later.
    """
    #: mapping of major mode class to list of actions
    mode_actions = {}
    
    def __init__(self, frame, mode):
        """Initialize the mapping with the new set of actions.
        
        The ordering of the menu items is set here, but nothing is actually
        mapped to a menubar or a toolbar until either updateMenuActions or
        updateToolbarActions is called.
        
        frame: parent Frame object
        action_classes: list of possible action classes (i.e.  not instantiated
        classes, but the classes themselves.  They will be instantiated when
        they are mapped to a menubar or toolbar.
        """
        self.frame = frame
        self.actions = {}
        self.popup_actions = {}
        self.index_actions = {}
        self.popup_index_actions = {}
        
        self.title_to_menu = {}
        self.title_to_toolbar = {}
        self.class_list = self.createActions(mode)
        self.class_to_action = {}
    
#    def __del__(self):
#        dprint("DELETING MENUMAP!")

    def createActions(self, mode):
        """Create the list of actions corresponding to this major mode.
        
        The action list includes all commands regardless of how they are
        initiated: menubar, toolbar, or keyboard commands.  If a new minor
        mode or sidebar is activated, this list will have to be regenerated.
        """
        if not mode.__class__ in self.mode_actions:
            action_classes = UserActionClassList(mode)
            self.mode_actions[mode.__class__] = action_classes
        return self.mode_actions[mode.__class__]

    def updateMinMax(self, min, max):
        """Update the min and max menu ids
        
        The range of menu Ids are used in the menu event handlers so that
        you don't have to bind events individually.
        """
        if self.min_id is None:
            self.min_id = min
        elif min < self.min_id:
            self.min_id = min
            
        if self.max_id is None:
            self.max_id = max
        elif max > self.max_id:
            self.max_id = max
    
    def getAction(self, actioncls):
        """Return an existing action if already instantiated, or create it"""
        if actioncls in self.class_to_action:
            return self.actions[self.class_to_action[actioncls].global_id]
        action = actioncls(self.frame)
        self.class_to_action[actioncls] = action
        self.actions[action.global_id] = action
        return action
    
    def updateMenuActions(self, menubar):
        """Populates the frame's menubar with the current actions.
        
        This replaces the current menubar in the frame with the menus
        defined by the current list of actions.
        """
        self.title_to_menu = {}
        self.actions = {}
        self.class_to_action = {}
        self.min_id = None
        self.max_id = None
        for title, items in self.class_list.menus.iteritems():
            if title == 'root':
                # Save the root menu for later, since wx.MenuBar uses a
                # different interface than wx.Menu for adding stuff
                continue
            if title not in self.title_to_menu:
                menu = wx.Menu()
                #storeWeakref('menu', menu)
                self.title_to_menu[title] = menu
            else:
                menu = self.title_to_menu[title]
            
            for weight, actioncls, separator in items:
                if isinstance(actioncls, str):
                    if separator and menu.GetMenuItemCount() > 0:
                        menu.AppendSeparator()
                    submenu_parts = actioncls.split('/')
                    self.dprint("MENU: %s, TITLE: %s" % (submenu_parts, title))
                    if actioncls not in self.title_to_menu:
                        submenu = wx.Menu()
                        #storeWeakref('menu', submenu)
                        self.title_to_menu[actioncls] = submenu
                    else:
                        submenu = self.title_to_menu[actioncls]
                        
                    menu.AppendMenu(-1, _(submenu_parts[-1]), submenu)
                else:
                    action = self.getAction(actioncls)
                    if separator and menu.GetMenuItemCount() > 0:
                        menu.AppendSeparator()
                    action.insertIntoMenu(menu)
                    self.updateMinMax(action.global_id, action.global_id)
                    subids = action.getSubIds()
                    if subids:
                        self.updateMinMax(subids[0], subids[-1])
                        for id in subids:
                            self.index_actions[id] = action
        
        pos = 0
        for weight, title, separator in self.class_list.menus['root']:
            self.dprint("root menu title: %s" % title)
            if pos < menubar.GetMenuCount():
                old = menubar.Replace(pos, self.title_to_menu[title], _(title))
                old.Destroy()
            else:
                menubar.Append(self.title_to_menu[title], _(title))
            pos += 1
        while (pos < menubar.GetMenuCount()):
            old = menubar.Remove(pos)
            old.Destroy()
        
    def updateToolbarActions(self, auimgr):
        needed = {}
        order = []
        for title, items in self.class_list.menus.iteritems():
            if title == 'root':
                # Ignore the root menu -- it only contains other menus
                continue

            # Change the toolbar title to only the first title --
            # e.g. rather than splitting up File and File/Submenu into
            # two toolbars, all of the File toolbars are kept together
            title = title.split('/')[0]
            for weight, actioncls, separator in items:
                if isinstance(actioncls, str):
                    # Ignore submenu definitions -- toolbars don't have subtoolbars
                    pass
                elif actioncls.icon is not None and actioncls.default_toolbar:
                    action = self.getAction(actioncls)
                    # Delay construction of toolbars until now, when
                    # we know that the toolbar is needed
                    if title not in needed:
                        needed[title] = True
                        order.append(title)
                    if title not in self.title_to_toolbar:
                        tb = wx.ToolBar(self.frame, -1, wx.DefaultPosition, wx.DefaultSize,
                            wx.TB_FLAT | wx.TB_NODIVIDER)
                        tb.SetToolBitmapSize(wx.Size(16,16))
                        self.title_to_toolbar[title] = tb
                        self.dprint(tb)
                    toolbar = self.title_to_toolbar[title]
                    if separator and toolbar.GetToolsCount() > 0:
                        toolbar.AddSeparator()
                    action.insertIntoToolbar(toolbar)
        
        if wx.Platform != '__WXMSW__':
            # FIXME: On GTK and OSX, add toolbars in reverse order, because
            # apparently aui inserts toolbars from the left and pushes
            # everything else to the right.  There must be a better way to
            # do this in a standardized manner
            order.reverse()
        for title in order:
            tb = self.title_to_toolbar[title]
            tb.Realize()
            self.dprint("Realized %s: %s" % (title, tb))
            auimgr.AddPane(tb, wx.aui.AuiPaneInfo().
                                  Name(title).Caption(title).
                                  ToolbarPane().Top().
                                  LeftDockable(False).RightDockable(False))

    def getKeyboardActions(self):
        keymap = KeyMap()
        #keymap.debug = True
        for actioncls in self.class_list.action_classes:
            action = self.getAction(actioncls)
            if action.keyboard is None:
                continue
            keymap.define(action.keyboard, action)
        return keymap
            
    def updateActions(self, toolbar=True):
        if wx.Platform == "__WXMAC__":
            # Must use a new menu bar on the mac -- you can't dynamically add
            # to the Help menu apparently due to a limitation in the toolkit.
            # Additionally, using a fresh menu bar fixes the double Help
            # menu problem
            menubar = wx.MenuBar()
        else:
            menubar = self.frame.GetMenuBar()
        self.updateMenuActions(menubar)
        wx.GetApp().SetMacHelpMenuTitleName(_("&Help"))
        self.frame.SetMenuBar(menubar)
        
        if toolbar:
            self.updateToolbarActions(self.frame._mgr)
        keymap = self.getKeyboardActions()
        self.connectEvents()
        return keymap
    
    def popupActions(self, parent, action_classes=[]):
        """Create a popup menu from the list of action classes.
        
        """
        menu = wx.Menu()
        
        self.disconnectEvents()
        for actioncls in action_classes:
            action = actioncls(self.frame)
            self.popup_actions[action.global_id] = action
            action.insertIntoMenu(menu)
            action.showEnable()
            self.updateMinMax(action.global_id, action.global_id)
            subids = action.getSubIds()
            if subids:
                self.updateMinMax(subids[0], subids[-1])
                for id in subids:
                    self.popup_index_actions[id] = action
        
        # register the new ids and allow the event processing to handle the
        # popup
        self.connectEvents()
        parent.PopupMenu(menu)
        
        # clean up after the popup events
        self.popup_actions = {}
        self.popup_index_actions = {}
        self.reconnectEvents()
    
    def cleanupPrevious(self, auimgr):
        self.disconnectEvents()
        for tb in self.title_to_toolbar.values():
            auimgr.DetachPane(tb)
            tb.Destroy()
        self.title_to_toolbar = {}
    
    def cleanupAndDelete(self):
        self.cleanupPrevious(self.frame._mgr)
        #printWeakrefs('menuitem', detail=False)
        #printWeakrefs('menu', detail=False)

    def reconnectEvents(self):
        """Update event handlers if the menu has been dynamically updated
        
        Sub-ids may have changed after a dynamic menu change, so update the
        min-max list, and update the event handlers.
        """
        self.disconnectEvents()
        self.index_actions = {}
        if self.actions:
            for action in self.actions.values():
                # Global ids can't have changed dynamically, so ignore them.
                # We're only interested in the sub-ids
                subids = action.getSubIds()
                if subids:
                    self.updateMinMax(subids[0], subids[-1])
                    for id in subids:
                        self.index_actions[id] = action
            self.connectEvents()

    def disconnectEvents(self):
        """Remove the event handlers for the range of menu ids"""
        self.frame.Disconnect(self.min_id, self.max_id, wx.wxEVT_COMMAND_MENU_SELECTED)
        self.frame.Disconnect(self.min_id, self.max_id, wx.wxEVT_UPDATE_UI)
        self.frame.Unbind(wx.EVT_MENU_OPEN)
    
    def connectEvents(self):
        """Add event handlers for the range of menu ids"""
        self.frame.Connect(self.min_id, self.max_id, wx.wxEVT_COMMAND_MENU_SELECTED,
                           self.OnMenuSelected)
        self.frame.Connect(self.min_id, self.max_id, wx.wxEVT_UPDATE_UI,
                           self.OnUpdateUI)
        self.frame.Bind(wx.EVT_MENU_OPEN, self.OnMenuOpen)
    
    def OnMenuSelected(self, evt):
        """Process a menu selection event"""
        self.dprint(evt)
        id = evt.GetId()
        
        # FIXME: Check for index actions first, because the global id for
        # a list is used as the first item in a list and also shows up in
        # self.actions.  Should the global id be used in lists???
        if id in self.popup_index_actions:
            # Some actions are associated with more than one id, like list
            # actions.  These are dispatched here.
            action = self.popup_index_actions[id]
            index = action.getIndexOfId(id)
            self.dprint("popup index %d of %s" % (index, action))
            action.action(index=index)
        elif id in self.index_actions:
            # Some actions are associated with more than one id, like list
            # actions.  These are dispatched here.
            action = self.index_actions[id]
            index = action.getIndexOfId(id)
            self.dprint("index %d of %s" % (index, action))
            action.action(index=index)
        elif id in self.popup_actions:
            # The id is in the list of single-event actions
            action = self.popup_actions[id]
            self.dprint("popup: %s" % action)
            action.action()
        elif id in self.actions:
            # The id is in the list of single-event actions
            action = self.actions[id]
            self.dprint(action)
            action.action()
     
    def OnUpdateUI(self, evt):
        """Update the state of the toolbar items.
        
        This event only gets fired for toolbars? I had thought it was fired
        just before wx shows the menu, giving us a chance to update the status
        before the user sees it.
        """
        if self.debuglevel > 1: self.dprint(evt)
        id = evt.GetId()
        if id in self.actions:
            # We're only interested in one id per Action, because list
            # actions will set the state for all their sub-ids given a
            # single id
            action = self.actions[id]
            if self.debuglevel > 1 or action.debuglevel: self.dprint(action)
            action.showEnable()
    
    def OnMenuOpen(self, evt):
        """Callback when a menubar menu is about to be opened.
        
        Note that on Windows, this also happens when submenus are opened, but
        gtk only happens when the top level menu gets opened.
        
        By trial and error, it seems to be safe to update dynamic menus here.
        """
        #dprint(evt)
        for action in self.actions.values():
            #dprint(action)
            action.showEnable()
            if hasattr(action, 'updateOnDemand'):
                action.updateOnDemand()
    
    def forceUpdate(self):
        """Convenience function to force the on-demand portions of the menu to
        be updated outside of an EVT_MENU_OPEN event.
        
        This is useful when you need to change a toolbar icon as the result
        of another action and you'd like the change in the menu system to be
        reflected immediately rather than waiting for the next EVT_MENU_OPEN
        when the user pulls down a menu.
        
        
        """
        self.OnMenuOpen(None)
