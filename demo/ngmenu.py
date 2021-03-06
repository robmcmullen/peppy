# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://peppy.flipturn.org for more info
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


class SelectAction(debugmixin):
    debuglevel=0
    use_accelerators = True
    name=None
    alias = ""
    help=""
    icon=None
    tooltip=""
    keyboard=None
    default_menu = ()
    default_toolbar = ()
    key_bindings = None # map of platform to default keybinding
    _accelerator_text = None # This is not set by the user
    stock_id = None
    global_id = None
    submenu=None
    
    def __init__(self, frame, menu=None, toolbar=None):
        self.widget=None
        self.tool=None
        if self.global_id is None:
            if self.stock_id is not None:
                self.__class__.global_id = self.stock_id
            else:
                self.__class__.global_id = wx.NewId()

        # Each action is always associated with a particular frame and
        # major mode
        self.frame = frame
        self.mode = frame.getActiveMajorMode()
##        if self.mode:
##            dprint("%s %s %s" % (self.mode.keyword, menu, toolbar))
##        else:
##            dprint("%s is None! %s %s" % (self.mode, menu, toolbar))

        self.initPreHook()
        
        if menu is not None:
            self.insertIntoMenu(menu)
        if toolbar is not None:
            self.insertIntoToolBar(toolbar)

        self.initPostHook()

    def __del__(self):
        dprint("DELETING action %s" % self.name)

    def initPreHook(self):
        pass

    def initPostHook(self):
        pass
    
    def getSubIds(self):
        return []

    @classmethod
    def setAcceleratorText(cls, force_emacs=False):
        if cls.keyboard:
            keystrokes = KeyMap.split(cls.keyboard)
            if len(keystrokes) == 1 and (cls.stock_id is not None or not force_emacs):
                # if it has a stock id, always force it to use the
                # standard accelerator because wxWidgets will put one
                # there anyway and we need to overwrite it with our
                # definition
                cls._accelerator_text = "\t%s" % KeyMap.nonEmacsName(keystrokes[0])
            else:
                cls._accelerator_text = "    %s" % cls.keyboard
            #dprint("%s %s %s" % (cls.__name__, str(keystrokes), cls._accelerator_text))
            return len(keystrokes)
        else:
            cls._accelerator_text = ""
        return 0
    
    def getMenuItemName(self):
        if self.use_accelerators and self.keyboard:
            return "%s%s" % (self.name, self._accelerator_text)
        else:
            return self.name

    def getTooltip(self, id=None, name=None):
        if id is None:
            id = self.global_id
        if name is None:
            name = self.name
        return "%s ('%s', id=%d)" % (self.tooltip, name, id)

    def insertIntoMenu(self, menu):
        self.widget=menu.Append(self.global_id, self.getMenuItemName(), self.getTooltip())
        
    def insertIntoToolbar(self, toolbar):
        self.tool=toolbar
        toolbar.AddLabelTool(self.global_id, self.name, getIconBitmap(self.icon), shortHelp=self.name, longHelp=self.getTooltip())

    def action(self, index=-1, multiplier=1):
        pass

    def __call__(self, evt, number=None):
        #assert self.
        dprint("%s called by keybindings -- multiplier=%s" % (self, number))
        self.action(0, number)

    def showEnable(self):
        state = self.isEnabled()
        if self.widget is not None:
            assert self.dprint("menu item %s (widget id=%d) enabled=%s" % (self.name, self.global_id, state))
            self.widget.Enable(state)
        if self.tool is not None:
            assert self.dprint("menu item %s (widget id=%d) enabled=%s tool=%s" % (self.name, self.global_id, state, self.tool))
            self.tool.EnableTool(self.global_id, state)

    def isEnabled(self):
        return True

class ToggleAction(SelectAction):
    def insertIntoMenu(self,menu):
        self.widget=menu.AppendCheckItem(self.global_id, self.name, self.getTooltip())

    def insertIntoToolBar(self,toolbar):
        self.tool=toolbar
        toolbar.AddCheckTool(self.global_id, getIconBitmap(self.icon), wx.NullBitmap, shortHelp=self.name, longHelp=self.getTooltip())
        
    def showEnable(self):
        SelectAction.showEnable(self)
        self.showCheck()
        
    def isChecked(self):
        raise NotImplementedError

    def showCheck(self):
        state = self.isChecked()
        if self.widget is not None:
            self.widget.Check(state)
        if self.tool is not None:
            self.tool.ToggleTool(self.id, state)


class IdCache(object):
    def __init__(self, first):
        self.first = first
        self.cache = [self.first]
        self.resetIndex()
        
    def resetIndex(self):
        self.index = 0
        
    def getNewId(self):
        if self.index >= len(self.cache):
            id = wx.NewId()
            self.cache.append(id)
        else:
            id = self.cache[self.index]
        self.index += 1
        return id

class ListAction(SelectAction):
    menumax=20
    inline=False
    
    def __init__(self, frame, menu=None, toolbar=None):
        # a record of all menu entries at the main level of the menu
        self.toplevel=[]

        # mapping of menu id to position in menu
        self.id2index={}

        # save the top menu
        self.menu=None

        SelectAction.__init__(self,frame,menu,toolbar)
        self.cache = IdCache(self.global_id)
    
    def getSubIds(self):
        ids = self.id2index.keys()
        ids.extend(self.toplevel)
        ids.sort()
        return ids
    
    def getIndexOfId(self, id):
        return self.id2index[id]
    
    def insertIntoMenu(self,menu,pos=None):
        self.cache.resetIndex()
        self.menu=menu

        # start off adding entries to the top level menu
        is_toplevel=True

        # Unless specified, add menu items to the end of the menu
        if pos is None:
            pos=menu.GetMenuItemCount()

        if not self.inline:
            # This is a named list, which means that all the items in
            # the list will be placed in a pop-right menu
            child=wx.Menu()
            self._insertMenu(menu,pos,child,self.name,True)
            self.topindex=pos
            pos=0
            menu=child
            is_toplevel=False
        else:
            self.topindex=pos
        
        self._insertItems(menu,pos,is_toplevel)

    def _insertItems(self,menu,pos,is_toplevel=False):
        items = self.getItems()
        
        self.count=0
        if self.menumax>0 and len(items)>self.menumax:
            for group in range(0,len(items),self.menumax):
                last=min(group+self.menumax,len(items))
                groupname="%s ... %s" % (items[group],items[last-1])
                child=wx.Menu()
                i=0
                for name in items[group:last]:
                    self._insert(child,i,name)
                    i+=1
                self._insertMenu(menu,pos,child,groupname,is_toplevel)
                pos+=1
        else:
            for name in items:
                self._insert(menu,pos,name,is_toplevel=is_toplevel)
                pos+=1
                
        self.savehash=self.getHash()

    def _insert(self,menu,pos,name,is_toplevel=False):
        id = self.cache.getNewId()
        widget=menu.Insert(pos,id,name, self.getTooltip(id, name))
        self.id2index[id]=self.count
        if is_toplevel:
            self.toplevel.append(id)
        self.count+=1

    def _insertMenu(self,menu,pos,child,name,is_toplevel=False):
        id = self.cache.getNewId()
        widget=menu.InsertMenu(pos,id,name,child)
        if is_toplevel:
            self.toplevel.append(id)

    def getHash(self):
        return self.count
                   
    def dynamic(self):
        if self.savehash == self.getHash():
            assert self.dprint("dynamic menu not changed.  Skipping")
            return
        assert self.dprint("toplevel=%s" % self.toplevel)
        assert self.dprint("id2index=%s" % self.id2index)
        assert self.dprint("items in list: %s" % self.menu.GetMenuItems())
        pos=0
        for item in self.menu.GetMenuItems():
            if item.GetId()==self.toplevel[0]:
                break
            pos+=1
        assert self.dprint("inserting items at pos=%d" % pos)
        for id in self.toplevel:
            assert self.dprint("deleting widget %d" % id)
            self.menu.Delete(id)
        self.toplevel=[]
        self.id2index={}
        assert self.dprint("inserting new widgets at %d" % pos)
        self.insertIntoMenu(self.menu,pos)
        self.frame.menumap.reconnectEvents()

    def getItems(self):
        raise NotImplementedError

    def getIcons(self):
        raise NotImplementedError

    def showEnable(self):
        if self.toplevel:
            assert self.dprint("Enabling all items: %s" % str(self.toplevel))
            for id in self.toplevel:
                self.menu.Enable(id,self.isEnabled())

class RadioAction(ListAction):
    menumax=-1
    inline=False

    def __init__(self, frame, menu=None, toolbar=None):
        # mapping of index (that is, position in menu starting from
        # zero) to the wx widget id
        self.index2id={}
        
        ListAction.__init__(self,frame,menu,toolbar)

    def insertIntoMenu(self,menu,pos=None):
        ListAction.insertIntoMenu(self,menu,pos)
        for id,index in self.id2index.iteritems():
            self.index2id[index]=id
        self.showCheck()

    def _insert(self,menu,pos,name,is_toplevel=False):
        id = self.cache.getNewId()
        widget=menu.InsertRadioItem(pos,id,name, self.getTooltip(id, name))
        self.id2index[id]=self.count
        if is_toplevel:
            self.toplevel.append(id)
        self.count+=1
    
    def showEnable(self):
        ListAction.showEnable(self)
        self.showCheck()
        
    def showCheck(self):
        if self.index2id:
            index=self.getIndex()
            assert self.dprint("checking %d" % (index))
            self.menu.Check(self.index2id[index],True)

    def saveIndex(self,index):
        raise NotImplementedError

    def getIndex(self):
        raise NotImplementedError
    
class ToggleListAction(ListAction):
    def __init__(self, frame, menu=None, toolbar=None):
        # list of all toggles so we can switch 'em on and off
        self.toggles=[]
        
        ListAction.__init__(self,frame,menu,toolbar)

    def _insert(self,menu,pos,name,is_toplevel=False):
        id = self.cache.getNewId()
        widget=menu.InsertCheckItem(pos,id,name, self.getTooltip())
        self.id2index[id]=self.count
        if is_toplevel:
            self.toplevel.append(id)
        self.toggles.append(id)
        self.frame.Connect(id,-1,wx.wxEVT_COMMAND_MENU_SELECTED,
                           self.OnMenuSelected)
        self.count+=1

    def OnMenuSelected(self,evt):
        self.id=evt.GetId()
        assert self.dprint("list item %s (widget id=%s) selected on frame=%s" % (self.id2index[self.id],self.id,self.frame))
        self.action(index=self.id2index[self.id])

    def OnUpdateUI(self,evt):
        assert self.dprint("menu item %s (widget id=%d) on frame=%s" % (self.name,self.id,self.frame))
        self.Enable()
        self.Check()

    def showCheck(self):
        if self.toplevel:
            assert self.dprint("Checking all items: %s" % str(self.toplevel))
            for id in self.toggles:
                self.menu.Check(id,self.isChecked(self.id2index[id]))

    def isChecked(self,index):
        raise NotImplementedError


class GlobalList(ListAction):
    debuglevel=0
    inline=True

    # storage and others must be defined in the subclass

    # storage holds the list of objects to be managed
    #storage=[]

    # others holds the list of currently active global lists that will
    # be used to update other menubars or toolbars when this object
    # changes.
    #others=[]
    
    def __init__(self, frame, menu=None):
        ListAction.__init__(self, frame, menu)
        self.__class__.others.append(weakref.ref(self))
        assert self.dprint("others: %s" % self.__class__.others)
        import gc
        reference=self.__class__.others[0]
        action=reference()
        assert self.dprint(gc.get_referrers(action))

    def createClassReferences(self):
        raise NotImplementedError

    @classmethod
    def append(cls,item):
##        dprint("BEFORE: storage: %s" % cls.storage)
##        dprint("BEFORE: others: %s" % cls.others)
        cls.storage.append(item)
        cls.update()
##        dprint("AFTER: storage: %s" % cls.storage)
##        dprint("AFTER: others: %s" % cls.others)
        
    @classmethod
    def extend(cls,items):
##        dprint("BEFORE: storage: %s" % cls.storage)
##        dprint("BEFORE: others: %s" % cls.others)
        cls.storage.extend(items)
        cls.update()
##        dprint("AFTER: storage: %s" % cls.storage)
##        dprint("AFTER: others: %s" % cls.others)
        
    @classmethod
    def remove(cls,item):
##        dprint("BEFORE: storage: %s" % cls.storage)
##        dprint("BEFORE: others: %s" % cls.others)
        cls.storage.remove(item)

##        # can't delete from a list that you're iterating on, so make a
##        # new list.
##        newlist=[]
##        for reference in cls.others:
##            action=reference()
##            if action is not None:
##                # Search through all related actions and remove references
##                # to them. There may be more than one reference, so search
##                # them all.
##                if action != item:
##                    newlist.append(weakref.ref(action))
##        cls.others=newlist

##        dprint("AFTER: storage: %s" % cls.storage)
##        dprint("AFTER: others: %s" % cls.others)

        cls.update()

    @classmethod
    def update(cls):
        newlist=[]
        for reference in cls.others:
            action=reference()
            if action is not None:
                newlist.append(reference)
                action.dynamic()
        cls.others=newlist
        
    def getHash(self):
        temp=tuple(self.getItems())
        assert self.dprint("hash=%s" % hash(temp))
        return hash(temp)

    def getItems(self):
        return self.__class__.storage


class UserActionMap(debugmixin):
    """Creates a mapping of actions for a frame.
    
    This class creates the ordering of the menubar, and maps actions to menu
    items.  Note that the order of the menu titles is required here and can't
    be added to later.
    """
    debuglevel=0
    
    default_menu_weights = {}
    
    @classmethod
    def setDefaultMenuBarWeights(cls, weights):
        """Set the default menubar weights.
        
        Weights is a mapping of the menu name to the sort order of the
        menu name.  By default the sort order of the menu ranges from
        0 to 1000, and floating-point numbers are OK.
        """
        cls.default_menu_weights.clear()
        cls.default_menu_weights.update(weights)
    
    def __init__(self, frame, action_classes, modes):
        """Initialize the mapping with the new set of actions.
        
        The ordering of the menu items is set here, but nothing is actually
        mapped to a menubar or a toolbar until either updateMenuActions or
        updateToolbarActions is called.
        
        @param frame: parent Frame object
        @param menus: list of action classes (i.e. not instantiated classes,
        but the classes themselves.  They will be instantiated when they are
        mapped to a menubar and another copy will be instantiated when mapped
        to a toolbar
        """
        self.frame = frame
        self.actions = {}
        self.index_actions = {}
        self.menus = {'root':[]}
        self.title_to_menu = {}
        self.title_to_toolbar = {}
        self.sortActions(action_classes, modes)

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
        mode = info[0]
        if isinstance(info[1], list) or isinstance(info[1], tuple):
            menu_title = info[1][0]
            menu_weight = info[1][1]
        else:
            menu_title = info[1]
            menu_weight = None
        weight = info[2]
        return mode, menu_title, menu_weight, weight
    
    def getParent(self, menu_title):
        """Get the parent menu title.
        
        Submenus are indicated by a / in the menu title
        """
        hier = menu_title.split('/')
        if len(hier) == 1:
            return 'root'
        else:
            return '/'.join(hier[0:-1])
    
    def sortActions(self, action_classes, modes):
        """Sort the actions into a hierarchy of menus
        
        Menus and menu items are sorted here by the weights given
        in the default_menu attribute of the action.
        """
        # list to hold the sort order of top-level menubar entries and
        # pull-right menus
        menu_weights = {}
        
        # First, loop through to get all actions matched to their
        # menu title
        for actioncls in action_classes:
            mode, menu_title, menu_weight, weight = self.getInfo(actioncls)
            
            # If the mode from the menu specification is in the
            # mode list passed in to the method, then we want this action
            # in the menu
            dprint("%s %s" % (mode, modes))
            if mode is None or mode in modes:
                action = actioncls(self.frame)
                self.actions[action.global_id] = action
                dprint("%s in current mode list" % action)
            
                if menu_title not in self.menus:
                    self.menus[menu_title] = []
                    menu_weights[menu_title] = 500
                
                # If the item weight is less than zero, a separator will
                # be added to the menu before the item
                self.menus[menu_title].append((abs(weight), action, weight<0))
                if menu_weight is not None:
                    menu_weights[menu_title] = menu_weight
                elif menu_title in self.default_menu_weights:
                    menu_weights[menu_title] = self.default_menu_weights[menu_title]
            else:
                dprint("%s not in current mode list" % actioncls.name)
                pass
        
        # Give weights to the top level menus and all pull-right submenus
        for menu_title, menu_weight in menu_weights.iteritems():
            parent = self.getParent(menu_title)
            self.menus[parent].append((menu_weight, menu_title, False))
        
        # For each menu, sort all the items within that group
        sorted = {}
        for title, items in self.menus.iteritems():
            items.sort()
            sorted[title] = items
        self.menus = sorted
        print self.menus
    
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
    
    def updateMenuActions(self, menubar):
        """Populates the frame's menubar with the current actions.
        
        This replaces the current menubar in the frame with the menus
        defined by the current list of actions.
        """
        self.min_id = None
        self.max_id = None
        for title, items in self.menus.iteritems():
            if title == 'root':
                # Save the root menu for later, since wx.MenuBar uses a
                # different interface than wx.Menu for adding stuff
                continue
            if title not in self.title_to_menu:
                menu = wx.Menu()
                self.title_to_menu[title] = menu
            menu = self.title_to_menu[title]
            for weight, action, separator in items:
                if isinstance(action, str):
                    submenu_title = action.split('/')
                    dprint("MENU: %s, TITLE: %s" % (submenu_title, title))
                    submenu = self.title_to_menu[action]
                    menu.AppendMenu(-1, submenu_title[-1], submenu)
                else:
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
        for weight, title, separator in self.menus['root']:
            if pos < menubar.GetMenuCount():
                menubar.Replace(pos, self.title_to_menu[title], title)
            else:
                menubar.Append(self.title_to_menu[title], title)
            pos += 1
        while (pos < menubar.GetMenuCount()):
            menubar.Remove(pos)
        self.connectEvents()
        
    def updateToolbarActions(self, auimgr):
        needed = {}
        order = []
        for title, items in self.menus.iteritems():
            if title == 'root':
                # Ignore the root menu -- it only contains other menus
                continue
            # Delay construction of toolbars until we know that the toolbar
            # is needed
            for weight, action, separator in items:
                if isinstance(action, str):
                    # Ignore submenu definitions -- toolbars don't have subtoolbars
                    pass
                elif action.icon is not None:
                    if title not in needed:
                        needed[title] = True
                        order.append(title)
                    if title not in self.title_to_toolbar:
                        tb = wx.ToolBar(self.frame, -1, wx.DefaultPosition, wx.DefaultSize,
                            wx.TB_FLAT | wx.TB_NODIVIDER)
                        tb.SetToolBitmapSize(wx.Size(16,16))
                        self.title_to_toolbar[title] = tb
                        dprint(tb)
                    toolbar = self.title_to_toolbar[title]
                    if separator and toolbar.GetToolsCount() > 0:
                        toolbar.AddSeparator()
                    action.insertIntoToolbar(toolbar)
                    
        for title in order:
            tb = self.title_to_toolbar[title]
            tb.Realize()
            dprint("Realized %s: %s" % (title, tb))
            auimgr.AddPane(tb, wx.aui.AuiPaneInfo().
                                  Name(title).Caption(title).
                                  ToolbarPane().Top().
                                  LeftDockable(False).RightDockable(False))
    
    def cleanupPrevious(self, auimgr):
        self.disconnectEvents()
        for tb in self.title_to_toolbar.values():
            auimgr.DetachPane(tb)
            tb.Destroy()
        self.title_to_toolbar = {}

    def reconnectEvents(self):
        """Update event handlers if the menu has been dynamically updated
        
        Sub-ids may have changed after a dynamic menu change, so update the
        min-max list, and update the event handlers.
        """
        self.disconnectEvents()
        self.index_actions = {}
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
    
    def connectEvents(self):
        """Add event handlers for the range of menu ids"""
        self.frame.Connect(self.min_id, self.max_id, wx.wxEVT_COMMAND_MENU_SELECTED,
                           self.OnMenuSelected)
        self.frame.Connect(self.min_id, self.max_id, wx.wxEVT_UPDATE_UI,
                           self.OnUpdateUI)
    
    def OnMenuSelected(self, evt):
        """Process a menu selection event"""
        dprint(evt)
        id = evt.GetId()
        
        if id in self.actions:
            # The id is in the list of single-event actions
            action = self.actions[id]
            dprint(action)
            action.action()
        elif id in self.index_actions:
            # Some actions are associated with more than one id, like list
            # actions.  These are dispatched here.
            action = self.index_actions[id]
            index = action.getIndexOfId(id)
            dprint("index %d of %s" % (index, action))
            action.action(index=index)
        
    def OnUpdateUI(self, evt):
        """Update the state of the menu items.
        
        This event gets fired just before wx shows the menu, giving us a
        chance to update the status before the user sees it.
        """
        dprint(evt)
        id = evt.GetId()
        if id in self.actions:
            # We're only interested in one id per Action, because list
            # actions will set the state for all their sub-ids given a
            # single id
            action = self.actions[id]
            dprint(action)
            action.showEnable()

    
class UserInterfaceLoader(debugmixin):
    debuglevel = 0

    @classmethod
    def loadMenu(cls, frame, majors=[], minors=[], create=True):
        """Load the global actions into the menu system.

        Any L{IPeppyPlugin} that returns menu items through the
        getMenuItems() method will be loaded here and stuffed into the
        GUI.

        @param app: the main application object
        @type app: L{BufferApp<buffers.BufferApp>}
        """
        # Generate the menu bar mapper
        menumap=MenuBarActionMap(frame)

        extensions = wx.GetApp().plugin_manager.getActivePluginObjects()
        assert cls.dprint(extensions)

        later = []
        for extension in extensions:
            assert cls.dprint("collecting from extension %s" % extension)
            for mode,menu,group in extension.getMenuItems():
                if mode is None:
                    assert cls.dprint("global menu %s: processing group %s" % (menu,group))
                    menumap.addMenuItems(menu,group)
                elif mode in majors or mode in minors:
                    # save the major mode & minor mode until the
                    # global menu is populated
                    later.append((menu,group))
        for menu,group in later:
            assert cls.dprint("mode %s, menu %s: processing group %s" % (mode,menu,group))
            menumap.addMenuItems(menu,group)

        # create the menubar
        if create:
            bar = wx.MenuBar()
        else:
            bar = frame.GetMenuBar()
            
        if wx.Platform == '__WXMAC__':
            # turn off the automatic generation of the Window menu.
            # We generate one ourselves
            wx.MenuBar.SetAutoWindowMenu(False)
            
        menumap.populateMenuBar(bar)
        if create:
            frame.SetMenuBar(bar)

        return menumap

    @classmethod
    def loadToolbar(cls, frame,majors=[],minors=[]):
        """Load actions into the toolbar system.

        Any L{IPeppyPlugin} that returns toolbar items through the
        getToolBarItems() method will be loaded here and stuffed into
        the GUI.

        @param app: the main application object
        @type app: L{BufferApp<buffers.BufferApp>}
        """
        # Generate the menu bar mapper
        toolmap=MenuBarActionMap(frame)

        extensions = wx.GetApp().plugin_manager.getActivePluginObjects()
        assert cls.dprint(extensions)
        
        later=[]
        for extension in extensions:
            assert cls.dprint("collecting from extension %s" % extension)
            for mode,menu,group in extension.getToolBarItems():
                if mode is None:
                    assert cls.dprint("global menu %s: processing group %s" % (menu,group))
                    toolmap.addMenuItems(menu,group)
                elif mode in majors or mode in minors:
                    # save the major mode & minor mode until the
                    # global menu is populated
                    later.append((menu,group))
        for menu,group in later:
            assert cls.dprint("mode %s, menu %s: processing group %s" % (mode,menu,group))
            toolmap.addMenuItems(menu,group)

        # create the menubar
        toolmap.populateToolBars()

        return toolmap

    @classmethod
    def setupKeys(cls):
        # Only call this once.
        if hasattr(cls, 'globalkeys'):
            return
        
        cls.globalkeys=[]
        cls.modekeys={}
        
        extensions = wx.GetApp().plugin_manager.getActivePluginObjects()
        for extension in extensions:
            assert cls.dprint("collecting from extension %s" % extension)
            for mode,action in extension.getKeyboardItems():
                if action.keyboard is None:
                    continue
                
                if mode is None:
                    assert cls.dprint("found global key %s" % (action.keyboard))
                    cls.globalkeys.append(action)
                else:
                    if mode not in cls.modekeys:
                        cls.modekeys[mode]=[]
                    assert cls.dprint("found mode %s, key %s" % (mode,action.keyboard))
                    cls.modekeys[mode].append(action)

    @classmethod
    def loadKeys(cls, frame, majors=[], minors=[]):
        """Load actions into the keyboard handler.

        Any L{IPeppyPlugin} that returns toolbar items through the
        getKeyboardItems() method will be loaded here and stuffed into
        the GUI.

        @param app: the main application object
        @type app: L{BufferApp<buffers.BufferApp>}
        """
        cls.setupKeys()
        
        # Generate the keyboard mapping
        keymap=KeyMap()

        # Global keymappings first
        for action in cls.globalkeys:
             keymap.define(action.keyboard,action(frame))

        # loop through major modes
        for mode in majors:
            if mode in cls.modekeys:
                for action in cls.modekeys[mode]:
                    keymap.define(action.keyboard,action(frame))

        # loop through minor modes
        for mode in minors:
            if mode in cls.modekeys:
                for action in cls.modekeys[mode]:
                    keymap.define(action.keyboard,action(frame))

        return keymap
