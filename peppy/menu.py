# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Dynamic menubar and toolbar system.

This module implements the menubar and toolbar system that is based on
actions linked to particular major modes.  When the major mode is
changed, the menu and toolbar system changes with it to only show
those actions that are applicable to the current state of the frame.
"""

import os,sys,time
import wx
import peppy.third_party.aui as aui

import weakref

from peppy.debug import *

from peppy.lib.iconstorage import *
from peppy.lib.multikey import *

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
    
    def __init__(self, modecls, frame):
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
        self.getActiveActionsOfFrame(modecls, frame)
        self.sortActions()
    
    def getActiveActionsOfFrame(self, modecls, frame):
        osx_menu = frame.isOSXMinimalMenuFrame()
        
        self.action_classes = self.getActiveActions(modecls, osx_menu)
    
    @classmethod
    def getActiveActions(self, modecls, osx_menu=False):
        """Get the active actions given the major mode class
        
        Note that actions may be added or removed if plugins change.
        """
        plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
        #assert self.dprint(plugins)

        actions = []
        for plugin in plugins:
            assert self.dprint("collecting from plugin %s" % plugin)
            
            # old-style way of checking each action for compatibility
            for action in plugin.getActions():
                if action.worksWithMajorMode(modecls):
                    if not osx_menu or (osx_menu and action.worksWithOSXMinimalMenu(modecls)):
                        # Only if the action works with the major mode do we
                        # want it to be an action that fires events
                        actions.append(action)

            # new-style way of having the plugin check for compatibility
            compatible = plugin.getCompatibleActions(modecls)
            if compatible is not None:
                actions.extend(compatible)
        return actions

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


class UserAccelerators(AcceleratorManager, debugmixin):
    """Creates a mapping of actions for a frame.
    
    This class creates the ordering of the menubar, and maps actions to menu
    items.  Note that the order of the menu titles is required here and can't
    be added to later.
    """
    debuglevel = 0
    
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
        AcceleratorManager.__init__(self)
        self.frame = frame
        self.mode = mode
        
        self.title_to_menu = {}
        self.title_to_toolbar = {}
        self.createActions()
        
        self.toolbar_actions = []
        self.toolbar_ondemand_actions = []
    
        Publisher().subscribe(self.clearCache, 'peppy.plugins.changed')
        Publisher().subscribe(self.clearCache, 'keybindings.changed')
    
    def __del__(self):
        Publisher().unsubscribe(self.clearCache)
    
    def clearCache(self, msg):
        self.mode.removeFromClassCache('UserAccelerators.class_list')
        
    def createActions(self):
        """Create the list of actions corresponding to this major mode.
        
        The action list includes all commands regardless of how they are
        initiated: menubar, toolbar, or keyboard commands.  If a new minor
        mode or sidebar is activated, this list will have to be regenerated.
        """
        cache = self.mode.getClassCache()
        if 'UserAccelerators.class_list' not in cache:
            self.dprint("Creating new UserActionClassList for %s" % self.mode.__class__.__name__)
            action_classes = UserActionClassList(self.mode.__class__, self.frame)
            cache['UserAccelerators.class_list'] = action_classes
        self.class_list = cache['UserAccelerators.class_list']
        
        # There used to be a call to self.mode.getInstanceCache here, used to
        # remember the actions to avoid the creation process.  But, it caused
        # PyDeadObject errors with the toolbar if the toolbar was removed.
        # Profiling said that this was not any large factor (the bulk of the
        # time being in the widget creation routines in the C++ code.)
        self.actions = {}
        self.class_to_action = {}

    def getAction(self, actioncls):
        """Return an existing action if already instantiated, or create it"""
        if actioncls in self.class_to_action:
            return self.actions[self.class_to_action[actioncls].global_id]
        action = actioncls(self.frame)
        self.class_to_action[actioncls] = action
        self.actions[action.global_id] = action
        return action
    
    def cleanupPrevious(self, auimgr):
        for tb in self.title_to_toolbar.values():
            auimgr.DetachPane(tb)
            tb.Destroy()
        self.title_to_toolbar = {}
        self.toolbar_actions = []
        self.toolbar_ondemand_actions = []
    
    def cleanupAndDelete(self):
        self.cleanupPrevious(self.frame._mgr)
        self.cleanup()
        self.frame.Unbind(wx.EVT_MENU_OPEN)
        
    def updateActions(self, toolbar=True):
        self.updateKeyboardAccelerators()
        
        if wx.Platform == "__WXMAC__":
            # Must use a new menu bar on the mac -- you can't dynamically add
            # to the Help menu apparently due to a limitation in the toolkit.
            # Additionally, using a fresh menu bar fixes the double Help
            # menu problem
            menubar = wx.MenuBar()
        else:
            menubar = self.frame.GetMenuBar()
        self.updateMenuAccelerators(menubar)
        wx.GetApp().SetMacHelpMenuTitleName(_("&Help"))
        self.frame.SetMenuBar(menubar)
        
        if toolbar:
            self.updateToolbarActions(self.frame._mgr)
        
        ctrls = self.mode.getKeyboardCapableControls()
        self.manageFrame(self.frame, *ctrls)
        
        minibuffer = self.mode.getMinibuffer()
        if minibuffer:
            minibuffer.addRootKeyboardBindings()
            
        self.frame.Bind(wx.EVT_MENU_OPEN, self.OnMenuOpen)
        
        # Cache the list of actions
        cache = self.mode.getInstanceCache()
        cache['UserAccelerators.actions'] = self.actions
        cache['UserAccelerators.class_to_action'] = self.class_to_action

    def OnMenuOpen(self, evt):
        """Callback when a menubar menu is about to be opened.
        
        Note that on Windows, this also happens when submenus are opened, but
        gtk only happens when the top level menu gets opened.
        
        By trial and error, it seems to be safe to update dynamic menus here.
        """
        # FIXME: On MAC and GTK, the event occurs on the menu object that
        # is actually opened, so it would be possible to optimize this call
        # to only set the enable state of the items in this menu.  On MSW,
        # however, the event object appears to be the frame regardless of
        # which menu bar title is actually pulled down.
        self.dprint("menu=%s" % evt.GetEventObject())
        for action in self.actions.values():
            #dprint("menumap=%s toolbar=%s action=%s" % (id(self), id(action.tool), action.__class__.__name__))
            action.showEnable()
            if hasattr(action, 'updateOnDemand'):
                action.updateOnDemand(self)

    def updateKeyboardAccelerators(self):
        action_to_last_id = {}
        for actioncls in self.class_list.action_classes:
            action = self.getAction(actioncls)
            action.addKeyBindingToAcceleratorList(self)
    
    def updateMenuAccelerators(self, menubar):
        """Populates the frame's menubar with the current actions.
        
        This replaces the current menubar in the frame with the menus
        defined by the current list of actions.
        """
        self.title_to_menu = {}
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
                    action.insertIntoMenu(menu, self)
        
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
                    if title not in self.title_to_toolbar:
                        tb = wx.ToolBar(self.frame, -1, wx.DefaultPosition, wx.DefaultSize,
                            wx.TB_FLAT | wx.TB_NODIVIDER)
                        tb.SetToolBitmapSize(wx.Size(16,16))
                        self.title_to_toolbar[title] = tb
                        self.dprint(tb)
                    toolbar = self.title_to_toolbar[title]
                    if separator and toolbar.GetToolsCount() > 0:
                        toolbar.AddSeparator()
                    action.insertIntoToolbar(toolbar, self)
                    action.showEnable()
                    
                    if hasattr(action, 'updateToolOnDemand'):
                        self.toolbar_ondemand_actions.append(action)
                        action.updateToolOnDemand()
                    else:
                        self.toolbar_actions.append(action)
        
        order = []
        # Use order of the menubar to determine order of the toolbar
        for weight, title, separator in self.class_list.menus['root']:
            if title in needed:
                order.append(title)

        for title in order:
            tb = self.title_to_toolbar[title]
            tb.Realize()
            self.dprint("Realized %s: %s" % (title, tb))
            auimgr.AddPane(tb, aui.AuiPaneInfo().
                                  Name(title).Caption(title).
                                  ToolbarPane().Top().
                                  LeftDockable(False).RightDockable(False))
    
    def forceToolbarUpdate(self):
        """Convenience function to force the on-demand items in the toolbar to
        be updated outside of an EVT_MENU_OPEN event.
        
        This is used in place of an EVT_UPDATE_UI event callback which is
        called waaaay too often.  Instead, this method is called from the idle
        timer in the frame.
        
        This method is also useful when you need to change a toolbar icon as
        the result of another action and you'd like the change in the menu
        system to be reflected immediately rather than waiting for the next
        EVT_MENU_OPEN when the user pulls down a menu.
        """
        for action in self.toolbar_actions:
            action.showEnable()
        for action in self.toolbar_ondemand_actions:
            action.showEnable()
            action.updateToolOnDemand()


class PopupMenu(AcceleratorManager, debugmixin):
    """Creates a mapping of actions for a frame.
    
    This class creates the ordering of the menubar, and maps actions to menu
    items.  Note that the order of the menu titles is required here and can't
    be added to later.
    """
    debuglevel = 0
    
    #: mapping of major mode class to list of actions
    mode_actions = {}
    
    def __init__(self, frame, parent, mode, action_classes=[], options=None):
        """Create a popup menu from the list of action classes.
        
        @param parent: window on which to create the popup menu
        
        @param action_classes: list of actions to be made into the popup menu.
        The list entries can either be SelectAction subclasses, or a tuple
        consisting of an integer and the SelectAction subclass.  The integer
        if used specifies the relative position between 0 and 1000.  If the
        integer is not specified, it is assumed to be a value of 500 which
        will place it at the center of the popup menu items.
        
        @param options: optional dict of name/value pairs to pass to the action
        """
        AcceleratorManager.__init__(self)
        self.frame = frame
    
        menu = wx.Menu()
        
        sorted = []
        position = 500
        needs_separator = False
        for item in action_classes:
            if isinstance(item, tuple):
                position = abs(item[0])
                sorted.append((position, item[1], item[0] < 0))
                needs_separator = False
            elif item is None:
                needs_separator = True
            else:
                sorted.append((position, item, needs_separator))
                needs_separator = False
            position += .0001
        sorted.sort(key=lambda a:a[0])
        
        if mode is None:
            mode = self.frame.getActiveMajorMode()
        
        if options is None:
            options = {}
        if hasattr(action_classes, 'getOptions'):
            options.update(action_classes.getOptions())
        
        first = True
        for pos, actioncls, sep in sorted:
            action = actioncls(self.frame, popup_options=options, mode=mode)
            if sep and not first:
                menu.AppendSeparator()
            action.insertIntoMenu(menu, self)
            action.showEnable()
            
            first = False
        
        # Override the frame's current EVT_MENU binding
        self.frame.root_accel.addPopupCallback(self.OnMenu)
        
        parent.PopupMenu(menu)
        
        # Reset the EVT_MENU binding back to the frame's root_accel default
        # EVT_MENU binding
        self.frame.root_accel.removePopupCallback()

    def OnMenu(self, evt):
        """Process a menu selection event"""
        self.dprint(evt)
        eid = evt.GetId()
        
        action = self.getMenuAction(eid)
        if action is not None:
            try:
                index = self.menu_id_to_index[eid]
            except KeyError:
                index = None
        self.dprint("popup index %s of %s" % (index, action))
        
        # Handle the special case when the action is called from the OS X menu
        if index is not None:
            if action.frame.isOSXMinimalMenuFrame():
                wx.CallAfter(action.actionOSXMinimalMenu, index=index)
            else:
                wx.CallAfter(action.action, index=index)
        elif action is not None:
            if action.frame.isOSXMinimalMenuFrame():
                wx.CallAfter(action.actionOSXMinimalMenu)
            else:
                wx.CallAfter(action.action)
