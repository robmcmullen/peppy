import os,sys,time
import wx

from orderer import *
from trac.core import *
from debug import *


class IMenuItemProvider(Interface):
    """Interface used to add user actions to the menu bar."""
    def getMenuItems():
        """Return a 3-tuple (mode,menu,item), where each element is
        defined as follows:

        mode is a string or None.  A string specifies the major mode
        by referring to its keyword, and None means it is a global
        menu item and will appear in all major modes.

        menu is a string that specifies the menu under which this item
        will appear.

        item is an instance of Menu, MenuItem, MenuItemGroup, or
        Separator that is a wrapper around the action to be performed
        when this menu item is selected."""

class IToolBarItemProvider(Interface):
    """Interface for a group of actions that are always available
    through the user interface regardless of the L{MajorMode}."""
    def getToolBarItems():
        """Return the list of actions that are grouped together in the
        user interface."""


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
        self.dprint(self.actions)

class MenuItemGroup(DelayedOrderer):
    def __init__(self,name,*actions):
        DelayedOrderer.__init__(self,name)
        self.actions=actions
        self.dprint(self.actions)



def getIcon(icon):
    if icon is None:
        return wx.ArtProvider_GetBitmap(wx.ART_INFORMATION, wx.ART_OTHER, wx.Size(16, 16))
    else:
        return wx.ArtProvider_GetBitmap(icon, wx.ART_OTHER, wx.Size(16, 16))


class SelectAction(debugmixin):
    debuglevel=0
    name=None
    help=""
    icon=None
    tooltip=""
    keyboard=None
    submenu=None
    
    def __init__(self, menumap, menu=None, toolbar=None):
        self.widget=None
        self.tool=None
        self.menumap=menumap
        self.frame=menumap.frame
        if menu is not None:
            self.insertIntoMenu(menu)
        if toolbar is not None:
            self.insertIntoToolBar(toolbar)
        self.userinit()

    def userinit(self):
        pass

    def insertIntoMenu(self,menu):
        self.id=wx.NewId()
        self.widget=menu.Append(self.id, self.name, self.tooltip)
        self.frame.Connect(self.id,-1,wx.wxEVT_COMMAND_MENU_SELECTED,
                           self.OnMenuSelected)
        self.frame.Connect(self.id,-1,wx.wxEVT_UPDATE_UI,
                           self.OnUpdateUI)
        
    def insertIntoToolBar(self,toolbar):
        self.id=wx.NewId()
        self.tool=toolbar
        toolbar.AddLabelTool(self.id, self.name, getIcon(self.icon), shortHelp=self.name, longHelp=self.tooltip)
        self.frame.Connect(self.id,-1,wx.wxEVT_COMMAND_MENU_SELECTED,
                           self.OnMenuSelected)
        self.frame.Connect(self.id,-1,wx.wxEVT_UPDATE_UI,
                           self.OnUpdateUI)
        
    def OnMenuSelected(self,evt):
        self.dprint("menu item %s (widget id=%d) selected on frame=%s" % (self.name,self.id,self.frame))
        self.action()

    def OnUpdateUI(self,evt):
        self.dprint("menu item %s (widget id=%d) on frame=%s" % (self.name,self.id,self.frame))
        self.Enable()

    def action(self, state=None, index=-1):
        pass

    def __call__(self, evt, number=None):
        self.dprint("%s called by keybindings" % self)
        self.action()

    def Enable(self):
        self.dprint("menu item %s (widget id=%d) enabled=%s" % (self.name,self.id,self.isEnabled()))
        if self.widget is not None:
            self.widget.Enable(self.isEnabled())
        if self.tool is not None:
            self.tool.EnableTool(self.id,self.isEnabled())

    def isEnabled(self):
        return True

class ToggleAction(SelectAction):
    def insertIntoMenu(self,menu):
        self.id=wx.NewId()
        self.widget=menu.AppendCheckItem(self.id, self.name, self.tooltip)
        self.frame.Connect(self.id,-1,wx.wxEVT_COMMAND_MENU_SELECTED,
                           self.OnMenuSelected)
        self.frame.Connect(self.id,-1,wx.wxEVT_UPDATE_UI,
                           self.OnUpdateUI)
        self.Check()

    def insertIntoToolBar(self,toolbar):
        self.id=wx.NewId()
        self.tool=toolbar
        toolbar.AddCheckTool(self.id, getIcon(self.icon), wx.NullBitmap, shortHelp=self.name, longHelp=self.tooltip)
        self.frame.Connect(self.id,-1,wx.wxEVT_COMMAND_MENU_SELECTED,
                           self.OnMenuSelected)
        self.frame.Connect(self.id,-1,wx.wxEVT_UPDATE_UI,
                           self.OnUpdateUI)
        self.Check()
        
    def OnMenuSelected(self,evt):
        self.dprint("menu item %s (widget id=%d) selected on frame=%s" % (self.name,self.id,self.frame))
        self.action()
        self.Check()

    def OnUpdateUI(self,evt):
        self.dprint("menu item %s (widget id=%d) on frame=%s" % (self.name,self.id,self.frame))
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
    
    def __init__(self, menumap, menu=None, toolbar=None):
        # a record of all menu entries at the main level of the menu
        self.toplevel=[]

        # mapping of menu id to position in menu
        self.id2index={}

        # save the top menu
        self.menu=None

        SelectAction.__init__(self,menumap,menu,toolbar)

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
        widget=menu.Insert(pos,id,name,self.tooltip)
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
        self.dprint("list item %s (widget id=%s) selected on frame=%s" % (self.id2index[self.id],self.id,self.frame))
        self.action(index=self.id2index[self.id])

    def OnUpdateUI(self,evt):
        self.dprint("menu item %s (widget id=%d) on frame=%s" % (self.name,self.id,self.frame))
        self.Enable()

    def getHash(self):
        return self.count
                   
    def dynamic(self):
        if self.savehash == self.getHash():
            self.dprint("dynamic menu not changed.  Skipping")
            return
        self.dprint("toplevel=%s" % self.toplevel)
        self.dprint("id2index=%s" % self.id2index)
        self.dprint("items in list: %s" % self.menu.GetMenuItems())
        pos=0
        for item in self.menu.GetMenuItems():
            if item.GetId()==self.toplevel[0]:
                break
            pos+=1
        self.dprint("inserting items at pos=%d" % pos)
        for id in self.toplevel:
            self.dprint("disconnecting widget %d" % id)
            self.frame.Disconnect(id,-1,wx.wxEVT_UPDATE_UI)
            self.dprint("deleting widget %d" % id)
            self.menu.Delete(id)
        self.id2index={}
        self.dprint("inserting new widgets at %d" % pos)
        self.insertIntoMenu(self.menu,pos)

    def getItems(self):
        raise NotImplementedError

    def getIcons(self):
        raise NotImplementedError

    def Enable(self):
        if self.toplevel:
            self.dprint("Enabling all items: %s" % str(self.toplevel))
            for id in self.toplevel:
                self.menu.Enable(id,self.isEnabled())

class RadioAction(ListAction):
    menumax=-1
    inline=False

    def __init__(self, menumap, menu=None, toolbar=None):
        # mapping of index (that is, position in menu starting from
        # zero) to the wx widget id
        self.index2id={}
        
        ListAction.__init__(self,menumap,menu,toolbar)

    def insertIntoMenu(self,menu,pos=None):
        ListAction.insertIntoMenu(self,menu,pos)
        for id,index in self.id2index.iteritems():
            self.index2id[index]=id
        self.Check()

    def _insert(self,menu,pos,name,is_toplevel=False):
        id=wx.NewId()
        widget=menu.InsertRadioItem(pos,id,name,self.tooltip)
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
        self.dprint("list item %s (widget id=%s) selected on frame=%s" % (self.id2index[self.id],self.id,self.frame))
        self.saveIndex(index)
        self.action(index=index,old=old)

    def OnUpdateUI(self,evt):
        self.dprint("menu item %s (widget id=%d) on frame=%s" % (self.name,self.id,self.frame))
        self.Enable()
        self.Check()

    def Check(self):
        if self.index2id:
            index=self.getIndex()
            self.dprint("checking %d" % (index))
            self.menu.Check(self.index2id[index],True)

    def saveIndex(self,index):
        raise NotImplementedError

    def getIndex(self):
        raise NotImplementedError
    


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

        # Create order of menu titles
        self.hier={}
        self.gethier(('root',))

        # each menu title has a list of menu items below it
        self.menumap={}

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
        
        self.dprint("Adding %s to menu %s: key=%s" % (menu,parent,str(menukey)))
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
            self.dprint("sorting: %s" % str(menu))
            submenus=hier[menu]['submenus']
            menus=[submenus[i]['order'] for i in submenus.keys()]
            menus.extend(hier[menu]['items'])
            order=Orderer(menus)
            menus=order.sort()
            hier[menu]['sorted']=menus
            self.dprint("sorted:  %s" % hier[menu]['sorted'])

            self.sortHierarchy(hier[menu]['submenus'])

    def sort(self):
        """Sorts the list of menu items within each menu.  This is not
        called in the constructor because items are added using the
        L{addMenuItem} method of this object.
        """
        if not self.dirty:
            return

        self.dprint(self.hier)

        self.sortHierarchy(self.hier)
        self.dirty=False

    def populateMenu(self,parent,hier):
        # Both submenus and items should be sorted together
        for menu in hier.keys():
            currentkey=self.getkey(parent,menu)
            order=hier[menu]['sorted']
            self.dprint("populating: %s with %s" % (menu,order))
            self.dprint("  parent=%s, hier=%s" % (str(parent),str(hier)))
            if 'widget' in hier[menu]:
                widget=hier[menu]['widget']
                addsep=False
                for itemgroup in hier[menu]['sorted']:
                    self.dprint("  processing itemgroup %s" % itemgroup)
                    if itemgroup.actions is None:
                        submenu=wx.Menu()
                        widget.AppendMenu(-1,itemgroup.name,submenu)
                        menukey=self.getkey(currentkey,itemgroup.name)
                        h=self.gethier(menukey)
                        h['widget']=submenu
                        self.dprint("  submenu menukey %s: %s" % (str(menukey),h))
                    else:
                        for action in itemgroup.actions:
                            if action is None:
                                addsep=True
                            else:
                                if addsep:
                                    # Don't allow multiple separators or the
                                    # menu to end on a separator
                                    widget.AppendSeparator()
                                a=action(self,menu=widget)
                                self.actions.append(a)
                                addsep=False
            if len(hier[menu]['submenus'])>0:
                self.populateMenu(self.getkey(parent,menu),hier[menu]['submenus'])


    def populateMenuBar(self):
        """Populates the frame's menubar with the current definition.
        This replaces the current menubar in the frame.
        """
        self.sort()
        menubar=self.frame.GetMenuBar()
        index=0
        count=menubar.GetMenuCount()
        hier=self.hier['root']
        parent=None
        for menu in hier['sorted']:
            label=menu.name
            if menu.hidden:
                self.dprint("  skipping hidden menu %s" % label)
                continue
            self.dprint("  processing menu %s" % label)
            menu = wx.Menu()
            if index<count:
                menubar.Replace(index, menu, label)
            else:
                menubar.Append(menu, label)

            menukey=self.getkey(parent,label)
            h=self.gethier(menukey)
            h['widget']=menu
            index+=1
           
        self.dprint(hier)
        self.populateMenu('root',hier['submenus'])

        while index<count:
            menubar.Remove(index)
            index+=1
        self.dprint("count=%d" % menubar.GetMenuCount())


    def populateTools(self,parent,hier):
        for menu in hier.keys():
            currentkey=self.getkey(parent,menu)
            order=hier[menu]['sorted']
            dprint("populating: %s with %s" % (menu,order))
            dprint("  parent=%s, hier=%s" % (str(parent),str(hier)))
            if 'widget' in hier[menu]:
                widget=hier[menu]['widget']
                addsep=False
                for itemgroup in hier[menu]['sorted']:
                    dprint("  processing itemgroup %s" % itemgroup)
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
                                a=action(self,toolbar=widget)
                                self.actions.append(a)
                                addsep=False

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
                dprint("  skipping hidden toolbar %s" % label)
                continue
            dprint("  processing toolbar %s" % label)
            tb = wx.ToolBar(self.frame, -1, wx.DefaultPosition, wx.DefaultSize,
                            wx.TB_FLAT | wx.TB_NODIVIDER)
            tb.label=label
            
            tb.SetToolBitmapSize(wx.Size(16,16))
            self.toolbars.append(tb)
            
            menukey=self.getkey(parent,label)
            h=self.gethier(menukey)
            h['widget']=tb
           
        dprint(hier)
        self.populateTools('root',hier['submenus'])
            


class MenuItemLoader(Component,debugmixin):
    debuglevel=0
    extensions=ExtensionPoint(IMenuItemProvider)

    def load(self,frame,major=None,minors=[]):
        """Load the global actions into the menu system.  Any
        L{Component} that implements the L{IGlobalMenuItems} interface
        will be loaded here and stuffed into the GUI.

        @param app: the main application object
        @type app: L{BufferApp<buffers.BufferApp>}
        """
        # Generate the menu bar mapper
        menumap=MenuBarActionMap(frame)

        self.dprint(self.extensions)
        later=[]
        for extension in self.extensions:
            self.dprint("collecting from extension %s" % extension)
            for mode,menu,group in extension.getMenuItems():
                if mode is None:
                    self.dprint("global menu %s: processing group %s" % (menu,group))
                    menumap.addMenuItems(menu,group)
                elif mode==major or mode in minors:
                    # save the major mode & minor mode until the
                    # global menu is populated
                    later.append((menu,group))
        for menu,group in later:
            self.dprint("mode %s, menu %s: processing group %s" % (mode,menu,group))
            menumap.addMenuItems(menu,group)

        # create the menubar
        menumap.populateMenuBar()
        #menumap.enable()

        return menumap




class ToolBarItemLoader(Component,debugmixin):
    debuglevel=0
    extensions=ExtensionPoint(IToolBarItemProvider)

    def load(self,frame,major=None,minors=[]):
        """Load the global actions into the menu system.  Any
        L{Component} that implements the L{IGlobalMenuItems} interface
        will be loaded here and stuffed into the GUI.

        @param app: the main application object
        @type app: L{BufferApp<buffers.BufferApp>}
        """
        # Generate the menu bar mapper
        toolmap=MenuBarActionMap(frame)

        self.dprint(self.extensions)
        later=[]
        for extension in self.extensions:
            self.dprint("collecting from extension %s" % extension)
            for mode,menu,group in extension.getToolBarItems():
                if mode is None:
                    self.dprint("global menu %s: processing group %s" % (menu,group))
                    toolmap.addMenuItems(menu,group)
                elif mode==major or mode in minors:
                    # save the major mode & minor mode until the
                    # global menu is populated
                    later.append((menu,group))
        for menu,group in later:
            self.dprint("mode %s, menu %s: processing group %s" % (mode,menu,group))
            toolmap.addMenuItems(menu,group)

        # create the menubar
        toolmap.populateToolBars()
        #toolmap.enable()

        return toolmap
