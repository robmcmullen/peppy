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

from debug import *

from lib.iconstorage import *
from lib.orderer import *
from lib.wxemacskeybindings import *

from peppy.yapsy.plugins import *

class Separator(DelayedOrderer):
    def __init__(self,name="-separator-",mode=None):
        DelayedOrderer.__init__(self,name)
        self.mode=mode
        self.actions=(None,)

class Menu(DelayedOrderer):
    def __init__(self,name,mode=None):
        DelayedOrderer.__init__(self,name)
        self.mode=mode
        self.actions=None

class MenuItem(DelayedOrderer):
    def __init__(self,action):
        if action is None:
            name="-separator-"
        else:
            name=action.name
        DelayedOrderer.__init__(self,name)
            
        self.actions=(action,)
        assert self.dprint(self.actions)

class MenuItemGroup(DelayedOrderer):
    def __init__(self,name,*actions):
        DelayedOrderer.__init__(self,name)
        self.actions=actions
        assert self.dprint(self.actions)



class SelectAction(debugmixin):
    debuglevel=0
    use_accelerators = True
    name=None
    help=""
    icon=None
    tooltip=""
    keyboard=None
    key_bindings = None # map of platform to default keybinding
    _accelerator_text = None # This is not set by the user
    stock_id=None
    submenu=None
    
    def __init__(self, frame, menu=None, toolbar=None):
        self.widget=None
        self.tool=None
        self.frame=frame

        self.initPreHook()
        
        if menu is not None:
            self.insertIntoMenu(menu)
        if toolbar is not None:
            self.insertIntoToolBar(toolbar)

        self.initPostHook()

    def __del__(self):
        assert self.dprint("DELETING action %s" % self.name)

    def initPreHook(self):
        pass

    def initPostHook(self):
        pass

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
            id = self.id
        if name is None:
            name = self.name
        return "%s ('%s', id=%d)" % (self.tooltip, name, id)

    def insertIntoMenu(self,menu):
        if self.stock_id:
            self.id=self.stock_id
        else:
            self.id=wx.NewId()
        self.widget=menu.Append(self.id, self.getMenuItemName(), self.getTooltip())
        self.frame.Connect(self.id,-1,wx.wxEVT_COMMAND_MENU_SELECTED,
                           self.OnMenuSelected)
        self.frame.Connect(self.id,-1,wx.wxEVT_UPDATE_UI,
                           self.OnUpdateUI)
        
    def insertIntoToolBar(self,toolbar):
        self.id=wx.NewId()
        self.tool=toolbar
        toolbar.AddLabelTool(self.id, self.name, getIconBitmap(self.icon), shortHelp=self.name, longHelp=self.getTooltip())
        self.frame.Connect(self.id,-1,wx.wxEVT_COMMAND_MENU_SELECTED,
                           self.OnMenuSelected)

    def remove(self):
        assert self.dprint("removing %s (widget id=%d) result=%s" % (self.name, self.id, self.frame.Disconnect(self.id, -1, wx.wxEVT_COMMAND_MENU_SELECTED)))
        self.widget = None
        self.tool = None
        self.frame = None
        
    def OnMenuSelected(self,evt):
        assert self.dprint("menu item %s (widget id=%d) selected on frame=%s" % (self.name,self.id,self.frame))
        self.action()

    def OnUpdateUI(self,evt):
        assert self.dprint("menu item %s (widget id=%d) on frame=%s" % (self.name,self.id,self.frame))
        self.Enable()

    def action(self, state=None, index=-1):
        pass

    def __call__(self, evt, number=None):
        assert self.dprint("%s called by keybindings" % self)
        self.action()

    def Enable(self):
        assert self.dprint("menu item %s (widget id=%d) enabled=%s" % (self.name,self.id,self.isEnabled()))
        if self.widget is not None:
            self.widget.Enable(self.isEnabled())
        if self.tool is not None:
            assert self.dprint("menu item %s (widget id=%d) enabled=%s tool=%s" % (self.name,self.id,self.isEnabled(), self.tool))
            self.tool.EnableTool(self.id,self.isEnabled())

    def isEnabled(self):
        return True

class ToggleAction(SelectAction):
    def insertIntoMenu(self,menu):
        self.id=wx.NewId()
        self.widget=menu.AppendCheckItem(self.id, self.name, self.getTooltip())
        self.frame.Connect(self.id,-1,wx.wxEVT_COMMAND_MENU_SELECTED,
                           self.OnMenuSelected)
        self.frame.Connect(self.id,-1,wx.wxEVT_UPDATE_UI,
                           self.OnUpdateUI)
        self.Check()

    def insertIntoToolBar(self,toolbar):
        self.id=wx.NewId()
        self.tool=toolbar
        toolbar.AddCheckTool(self.id, getIconBitmap(self.icon), wx.NullBitmap, shortHelp=self.name, longHelp=self.getTooltip())
        self.frame.Connect(self.id,-1,wx.wxEVT_COMMAND_MENU_SELECTED,
                           self.OnMenuSelected)
        self.frame.Connect(self.id,-1,wx.wxEVT_UPDATE_UI,
                           self.OnUpdateUI)
        self.Check()
        
    def OnMenuSelected(self,evt):
        assert self.dprint("menu item %s (widget id=%d) selected on frame=%s" % (self.name,self.id,self.frame))
        self.action()
        self.Check()

    def OnUpdateUI(self,evt):
        assert self.dprint("menu item %s (widget id=%d) on frame=%s" % (self.name,self.id,self.frame))
        self.Enable()
        self.Check()

    def isChecked(self):
        raise NotImplementedError

    def Check(self):
        if self.widget is not None:
            self.widget.Check(self.isChecked())
        if self.tool is not None:
            self.tool.ToggleTool(self.id,self.isChecked())
    
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

    def insertIntoMenu(self,menu,pos=None):
        self.menu=menu
        self.id=-1

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

        # One menu item in this group has to have the EVT_UPDATE_UI
        # event in order to keep the state of the menu synced with the
        # application
        if len(self.toplevel)>0:
            self.frame.Connect(self.toplevel[0],-1,wx.wxEVT_UPDATE_UI,
                               self.OnUpdateUI)

    def _insertItems(self,menu,pos,is_toplevel=False):
        items=self.getItems()
        
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
        id=wx.NewId()
        widget=menu.Insert(pos,id,name, self.getTooltip(id, name))
        self.id2index[id]=self.count
        if is_toplevel:
            self.toplevel.append(id)
        self.frame.Connect(id,-1,wx.wxEVT_COMMAND_MENU_SELECTED,
                           self.OnMenuSelected)
        self.count+=1

    def _insertMenu(self,menu,pos,child,name,is_toplevel=False):
        id=wx.NewId()
        widget=menu.InsertMenu(pos,id,name,child)
        if is_toplevel:
            self.toplevel.append(id)

    def OnMenuSelected(self,evt):
        self.id=evt.GetId()
        assert self.dprint("list item %s (widget id=%s) selected on frame=%s" % (self.id2index[self.id],self.id,self.frame))
        self.action(index=self.id2index[self.id])

    def OnUpdateUI(self,evt):
        assert self.dprint("menu item %s (widget id=%d) on frame=%s" % (self.name,self.id,self.frame))
        self.Enable()

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
            assert self.dprint("disconnecting widget %d" % id)
            self.frame.Disconnect(id,-1,wx.wxEVT_UPDATE_UI)
            assert self.dprint("deleting widget %d" % id)
            self.menu.Delete(id)
        self.toplevel=[]
        self.id2index={}
        assert self.dprint("inserting new widgets at %d" % pos)
        self.insertIntoMenu(self.menu,pos)

    def getItems(self):
        raise NotImplementedError

    def getIcons(self):
        raise NotImplementedError

    def Enable(self):
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
        self.Check()

    def _insert(self,menu,pos,name,is_toplevel=False):
        id=wx.NewId()
        widget=menu.InsertRadioItem(pos,id,name, self.getTooltip(id, name))
        self.id2index[id]=self.count
        if is_toplevel:
            self.toplevel.append(id)
        self.frame.Connect(id,-1,wx.wxEVT_COMMAND_MENU_SELECTED,
                           self.OnMenuSelected)
        self.count+=1

    def OnMenuSelected(self,evt):
        old=self.getIndex()
        self.id=evt.GetId()
        index=self.id2index[self.id]
        assert self.dprint("list item %s (widget id=%s) selected on frame=%s" % (self.id2index[self.id],self.id,self.frame))
        self.saveIndex(index)
        self.action(index=index,old=old)

    def OnUpdateUI(self,evt):
        assert self.dprint("menu item %s (widget id=%d) on frame=%s" % (self.name,self.id,self.frame))
        self.Enable()
        self.Check()

    def Check(self):
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
        id=wx.NewId()
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

    def Check(self):
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
    
    def __init__(self, frame, menu):
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


class MenuBarActionMap(debugmixin):
    debuglevel=0
    
    def __init__(self,frame,menus=[]):
        """Creates a menu map for a frame.  This class creates the
        ordering of the menubar, and maps actions to menu items.  Note
        that the order of the menu titles is required here and can't
        be added to later.

        @param frame: parent Frame object
        @type frame: Frame
        @param menus: list of Menu objects
        @type menus: Menu
        """
        self.frame=frame
        self.actions=[]
        self.dirty=False
        self.submenus={}
        self.rootmenus=[]

        self.toolbars=[]

        self.keymap=KeyMap()

        # Create order of menu titles
        self.hier={}
        self.gethier(('root',))

        # each menu title has a list of menu items below it
        self.menumap={}

    def __del__(self):
        assert self.dprint("DELETING %s" % self)

    def getkey(self,parent,name=None):
        if parent is None:
            return tuple(('root',name))
        elif isinstance(parent,str):
            if name is None:
                if parent=='root':
                    return ('root',)
                return tuple(('root',parent))
            else:
                if parent=='root':
                    return tuple((parent,name))
                else:
                    return tuple(('root',parent,name))
        elif isinstance(parent,tuple) or isinstance(parent,list):
            temp=list(parent)
            if temp[0]!='root':
                temp[0:0]=['root']
            if name is not None:
                temp.append(name)
            return tuple(temp)
        raise TypeError("Unrecognized menu definition %s" % parent)

    def gethier(self,menukey):
        hier=self.hier
        for name in menukey[:-1]:
            if name not in hier:
                hier[name]={'submenus':{}, 'items':[], 'sorted':[]}
            hier=hier[name]['submenus']
        if menukey[-1] not in hier:
            hier[menukey[-1]]={'submenus':{}, 'items':[], 'sorted':[]}
        return hier[menukey[-1]]

    def setorderer(self,menukey,menu):
        hier=self.gethier(menukey)
        hier['order']=menu
        
    def addMenu(self,parent,menu):
        menukey=self.getkey(parent,menu.name)
        self.setorderer(menukey,menu)
        
        assert self.dprint("Adding %s to menu %s: key=%s" % (menu,parent,str(menukey)))
        if menukey not in self.menumap:
            # if the menuname doesn't exist yet, make a
            # placeholder under the assumption that the menu will
            # be defined later.
            self.menumap[menukey]=[]
        self.dirty=True
        
    def addMenuItems(self,menuname,group):
        """Add a menu item (or group) to a menu.

        @param menuname: name of menu title to add to
        @type menuname: str
        @param group: group of menu items
        @type group: MenuItemGroup
        """
        if group.actions is None:
            self.addMenu(menuname,group)
        else:
            menukey=self.getkey(menuname)
            hier=self.gethier(menukey)
            hier['items'].append(group)
            self.dirty=True

    def sortHierarchy(self,hier):
        # Both submenus and items should be sorted together
        for menu in hier.keys():
            assert self.dprint("sorting: %s" % str(menu))
            submenus=hier[menu]['submenus']
            assert self.dprint("submenus: %s" % str(submenus))
            menus = []
            for i in submenus.keys():
                if 'order' in submenus[i]:
                    menus.append(submenus[i]['order'])
                else:
                    dprint("submenu %s of %s not ordered" % (i, hier))
            menus.extend(hier[menu]['items'])
            order=Orderer(menus)
            menus=order.sort()
            hier[menu]['sorted']=menus
            assert self.dprint("sorted:  %s" % hier[menu]['sorted'])

            self.sortHierarchy(hier[menu]['submenus'])

    def sort(self):
        """Sorts the list of menu items within each menu.  This is not
        called in the constructor because items are added using the
        L{addMenuItem} method of this object.
        """
        if not self.dirty:
            return

        assert self.dprint(self.hier)

        self.sortHierarchy(self.hier)
        self.dirty=False

    def populateMenu(self,parent,hier):
        # Both submenus and items should be sorted together
        for menu in hier.keys():
            currentkey=self.getkey(parent,menu)
            order=hier[menu]['sorted']
            assert self.dprint("populating: %s with %s" % (menu,order))
            assert self.dprint("  parent=%s, hier=%s" % (str(parent),str(hier)))
            if 'widget' in hier[menu]:
                widget=hier[menu]['widget']
                addsep=False
                for itemgroup in hier[menu]['sorted']:
                    assert self.dprint("  processing itemgroup %s" % itemgroup)
                    if itemgroup.actions is None:
                        submenu=wx.Menu()
                        widget.AppendMenu(-1,itemgroup.name,submenu)
                        menukey=self.getkey(currentkey,itemgroup.name)
                        h=self.gethier(menukey)
                        h['widget']=submenu
                        assert self.dprint("  submenu menukey %s: %s" % (str(menukey),h))
                    else:
                        for action in itemgroup.actions:
                            if action is None:
                                addsep=True
                            else:
                                if addsep:
                                    # Don't allow multiple separators or the
                                    # menu to end on a separator
                                    widget.AppendSeparator()
                                a=action(self.frame,menu=widget)
                                self.actions.append(a)
                                addsep=False

                                # define keyboard equivalent
                                if action.keyboard is not None:
                                    self.keymap.define(action.keyboard,
                                                       action(self.frame))
            if len(hier[menu]['submenus'])>0:
                self.populateMenu(self.getkey(parent,menu),hier[menu]['submenus'])


    def populateMenuBar(self, menubar):
        """Populates the frame's menubar with the current definition.
        This replaces the current menubar in the frame.
        """
        self.sort()
        index=0
        count=menubar.GetMenuCount()
        hier=self.hier['root']
        parent=None
        for menu in hier['sorted']:
            label=menu.name
            if menu.hidden:
                assert self.dprint("  skipping hidden menu %s" % label)
                continue
            assert self.dprint("  processing menu %s" % label)
            menu = wx.Menu()
            if index<count:
                menubar.Replace(index, menu, label)
            else:
                menubar.Append(menu, label)

            menukey=self.getkey(parent,label)
            h=self.gethier(menukey)
            h['widget']=menu
            index+=1
           
        assert self.dprint(hier)
        self.populateMenu('root',hier['submenus'])

        while index<count:
            menubar.Remove(index)
            index+=1
        assert self.dprint("count=%d" % menubar.GetMenuCount())


    def populateTools(self,parent,hier):
        for menu in hier.keys():
            currentkey=self.getkey(parent,menu)
            order=hier[menu]['sorted']
            assert self.dprint("populating: %s with %s" % (menu,order))
            assert self.dprint("  parent=%s, hier=%s" % (str(parent),str(hier)))
            if 'widget' in hier[menu]:
                widget=hier[menu]['widget']
                addsep=False
                for itemgroup in hier[menu]['sorted']:
                    assert self.dprint("  processing itemgroup %s" % itemgroup)
                    if itemgroup.actions is None:
                        # Currently, submenus are ignored it toolbars!
                        pass
                    else:
                        for action in itemgroup.actions:
                            if action is None:
                                addsep=True
                            else:
                                if addsep:
                                    # Don't allow multiple separators or the
                                    # menu to end on a separator
                                    widget.AddSeparator()
                                a=action(self.frame,toolbar=widget)
                                self.actions.append(a)
                                addsep=False

                                # define keyboard equivalent
                                if action.keyboard is not None:
                                    self.keymap.define(action.keyboard,
                                                       action(self.frame))

    def populateToolBars(self):
        """Populates the frame's menubar with the current definition.
        This replaces the current menubar in the frame.
        """
        self.sort()
        hier=self.hier['root']
        parent=None
        self.toolbars=[]
        for menu in hier['sorted']:
            label=menu.name
            if menu.hidden:
                assert self.dprint("  skipping hidden toolbar %s" % label)
                continue
            assert self.dprint("  processing toolbar %s" % label)
            tb = wx.ToolBar(self.frame, -1, wx.DefaultPosition, wx.DefaultSize,
                            wx.TB_FLAT | wx.TB_NODIVIDER)
            tb.label=label
            
            tb.SetToolBitmapSize(wx.Size(16,16))
            self.toolbars.append(tb)
            
            menukey=self.getkey(parent,label)
            h=self.gethier(menukey)
            h['widget']=tb
           
        assert self.dprint(hier)
        self.populateTools('root',hier['submenus'])
            


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
