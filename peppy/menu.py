# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
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
    
    # This is the name of the menu entry as it appears in the menu bar.
    # i18n processing happens within the menu system, so no need to
    # wrap this string in a call to the _ function
    name = None
    
    # This alias holds an emacs style name that is used during M-X processing
    # If you don't want this action to have an emacs style name, don't
    # include this or set it equal to None
    alias = ""
    
    # Tooltip that is displayed when the mouse is hovering over the menu
    # entry.  If the tooltip is None, the tooltip is taken from the first
    # line of the docstring, if it exists.
    tooltip = None
    
    # The default menu location is specified here as a tuple containing
    # the menu path (separated by / characters) and a number between 1 and
    # 1000 representing the position within the menu.  A negative number
    # means that a separator should appear before the item
    default_menu = ()
    
    # If there is an icon associated with this action, name it here.  Icons
    # are referred to by path name relative to the peppy directory.  A toolbar
    # entry will be automatically created if the icon is specified here, unless
    # you specify default_toolbar = False
    icon = None
    default_toolbar = True
    
    # Map of platform to default keybinding.  This is used to assign the
    # class attribute keyboard, which is the current keybinding.  Currently,
    # the defined platforms are named "win", "mac", and "emacs".  A platform
    # named 'default' may also be included that will be the default key
    # unless overridden by a specific platform
    key_bindings = None
    keyboard = None
    
    # If this menu action has a stock wx id, such as wx.ID_ABOUT or
    # wx.ID_PREFERENCES, add it here and the wx menu system can do some
    # special things to it, like automatically give it the correct
    # location on WXMAC.
    stock_id = None
    
    # If the action doesn't use a stock id, it will automatically get assigned
    # a global id here.  Note that if you are subclassing an action, you
    # should explicitly assign a global id (or None) to your subclass's
    # global_id attribute, otherwise the menu system will get confused
    # and attempt to use the superclass's global_id
    global_id = None

    
    # The rest of these class attributes aren't for individual class
    # customization
    _use_accelerators = True
    _accelerator_text = None # This is not set by the user

    @classmethod
    def worksWithMajorMode(cls, mode):
        return True
    
    @classmethod
    def getHelp(cls):
        #dprint(dir(cls))
        help = "\n\n'%s' is an action from module %s\nBound to keystrokes: %s\nAlias: %s\nDocumentation: %s" % (cls.__name__, cls.__module__, cls.keyboard, cls.alias, cls.__doc__)
        return help
    
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
            self.insertIntoToolbar(toolbar)

        self.initPostHook()

    def __del__(self):
        self.dprint("DELETING action %s" % self.name)

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
        if self._use_accelerators and self.keyboard:
            return "%s%s" % (_(self.name), self._accelerator_text)
        else:
            return self.name

    def getTooltip(self, id=None, name=None):
        if id is None:
            id = self.global_id
        if name is None:
            name = self.name
        if self.tooltip is None:
            if self.__doc__ is not None:
                lines = self.__doc__.splitlines()
                self.__class__.tooltip = lines[0]
        return "%s ('%s', id=%d)" % (_(self.tooltip), _(name), id)

    def insertIntoMenu(self, menu):
        self.widget = wx.MenuItem(menu, self.global_id, self.getMenuItemName(), self.getTooltip())
        if self.icon:
            bitmap = getIconBitmap(self.icon)
            self.widget.SetBitmap(bitmap)
        menu.AppendItem(self.widget)

    def insertIntoToolbar(self, toolbar):
        self.tool=toolbar
        toolbar.AddLabelTool(self.global_id, self.name, getIconBitmap(self.icon), shortHelp=self.name, longHelp=self.getTooltip())

    def action(self, index=-1, multiplier=1):
        pass

    def __call__(self, evt, number=1):
        assert self.dprint("%s called by keybindings -- multiplier=%s" % (self, number))
        # Make sure that the action is enabled before allowing it to be called
        # using the keybinding
        if self.isEnabled():
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

    def insertIntoToolbar(self,toolbar):
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
            #dprint("%s, %s, %s" % (self.tool, self.global_id, state))
            self.tool.ToggleTool(self.global_id, state)


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
    menumax = 30
    abbrev_width = 16
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
                str1 = items[group].strip()[0:self.abbrev_width]
                str2 = items[last-1].strip()[0:self.abbrev_width]
                groupname="%s ... %s" % (str1, str2)
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
        # FIXME: it seems that on app exit, frame.menumap can be None, so check
        # for that here
        if self.frame.menumap:
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
        self.count+=1

    def showEnable(self):
        ListAction.showEnable(self)
        self.showCheck()
        
    def showCheck(self):
        if self.toplevel:
            assert self.dprint("Checking all items: %s" % str(self.toplevel))
            for id in self.toggles:
                self.menu.Check(id,self.isChecked(self.id2index[id]))

    def isChecked(self,index):
        raise NotImplementedError


class OnDemandActionMixin(object):
    """Mixin to provide on-demand updating as the menubar is opened
    
    On-demand actions don't have to be created ahead of time -- the
    updateOnDemand method is called immediately before the menu bar entry
    is opened.
    """
    
    def updateOnDemand(self):
        raise NotImplementedError


class OnDemandGlobalListAction(OnDemandActionMixin, ListAction):
    """On-demand list that shares its items in all menu bars.
    
    Menu items are shared by using class attributes for the storage.  Be aware
    that you either have to, in your subclass of OnDemandGlobalListAction,
    have to explicitly name a class attribute 'storage' and it must be a list,
    or you can call your subclasses class method setStorage and supply it with
    a list.
    """
    # identifier that keeps track whenever ANY instance of
    # OnDemandGlobalListAction changes.  This causes menus to be rebuilt
    # unnecessarily, as most operations aren't expensive, anything more
    # complicated is a waste.  If you want a hash that only tracks your class,
    # create a class attribute 'localhash' in your subclass
    globalhash = 0
    
    # storage for each class.  setStorage should be called before using
    # any methods, or alternatively you can define a class attribute named
    # 'storage' that's a list, which will shadow the None definition here.
    storage = None
    
    @classmethod
    def setStorage(cls, array):
        cls.storage = array
    
    @classmethod
    def trimStorage(cls, num):
        if len(cls.storage) > num:
            cls.storage[num:]=[]

    @classmethod
    def append(cls, item):
        cls.storage.append(item)
        cls.calcHash()

    @classmethod
    def remove(cls, item):
        cls.storage.remove(item)
        cls.calcHash()
    
    @classmethod
    def calcHash(cls):
        if hasattr(cls, 'localhash'):
            cls.localhash += 1
        else:
            cls.globalhash += 1

    def getHash(self):
        """Simplistic implementation that only keeps track of additions or deletions.
        
        Should more rigorous hashing be needed, override this.
        """
        if hasattr(self, 'localhash'):
            return self.localhash
        else:
            return self.globalhash
    
    def getItems(self):
        return [str(item) for item in self.storage]

    def updateOnDemand(self):
        self.dynamic()







class UserActionClassList(debugmixin):
    """Creates a list of actions for a major mode
    
    This class creates a list of action classes and a sorted list of actions
    ready to be populated into a menu.
    """
    debuglevel=0
    
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
            actions.extend(plugin.getCompatibleActions(mode.__class__))
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
    debuglevel=0
    
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
        self.index_actions = {}
        self.title_to_menu = {}
        self.title_to_toolbar = {}
        self.class_list = mode.action_classes
        self.class_to_action = {}
    
    def __del__(self):
        dprint("DELETING MENUMAP!")

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
                        self.title_to_menu[actioncls] = submenu
                    else:
                        submenu = self.title_to_menu[actioncls]
                        
                    menu.AppendMenu(-1, submenu_parts[-1], submenu)
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
                menubar.Replace(pos, self.title_to_menu[title], title)
            else:
                menubar.Append(self.title_to_menu[title], title)
            pos += 1
        while (pos < menubar.GetMenuCount()):
            menubar.Remove(pos)
        
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
        
        if wx.Platform == '__WXGTK__':
            # FIXME: On GTK, add toolbars in reverse order, because apparently
            # aui inserts toolbars from the left and pushes everything else to
            # the right.  There must be a better way to do this.
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
        self.updateMenuActions(self.frame.GetMenuBar())
        if toolbar:
            self.updateToolbarActions(self.frame._mgr)
        keymap = self.getKeyboardActions()
        self.connectEvents()
        return keymap
    
    def cleanupPrevious(self, auimgr):
        self.disconnectEvents()
        for tb in self.title_to_toolbar.values():
            auimgr.DetachPane(tb)
            tb.Destroy()
        self.title_to_toolbar = {}
    
    def cleanupAndDelete(self):
        self.cleanupPrevious(self.frame._mgr)
        # Force garbage collection of actions by resetting all of the dicts
        # that hold references to actions
        self.actions = None
        self.class_list = None
        self.class_to_action = None
        self.index_actions = None
        self.title_to_menu = None
        self.title_to_toolbar = None

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
        self.frame.Bind(wx.EVT_MENU_OPEN, self.OnMenuOpen)
    
    def OnMenuSelected(self, evt):
        """Process a menu selection event"""
        self.dprint(evt)
        id = evt.GetId()
        
        # FIXME: Check for index actions first, because the global id for
        # a list is used as the first item in a list and also shows up in
        # self.actions.  Should the global id be used in lists???
        if id in self.index_actions:
            # Some actions are associated with more than one id, like list
            # actions.  These are dispatched here.
            action = self.index_actions[id]
            index = action.getIndexOfId(id)
            self.dprint("index %d of %s" % (index, action))
            action.action(index=index)
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
