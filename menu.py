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


class SelectAction(debugmixin):
    debuglevel=1
    name=None
    help=""
    icon=None
    tooltip=""
    keyboard=None
    submenu=None
    
    def __init__(self, menumap, menu, extrinsic=None):
        self.menumap=menumap
        self.frame=menumap.frame
        self.state=extrinsic
        self.insertIntoMenu(menu)

    def insertIntoMenu(self,menu):
        self.id=wx.NewId()
        self.widget=menu.Append(self.id, self.name, self.tooltip)
        self.frame.Connect(self.id,-1,wx.wxEVT_COMMAND_MENU_SELECTED,
                           self.OnMenuSelected)
        self.frame.Connect(self.id,-1,wx.wxEVT_UPDATE_UI,
                           self.OnUpdateUI)
        
    def OnMenuSelected(self,evt):
        dprint("menu item %s (widget id=%d) selected on frame=%s" % (self.name,self.id,self.frame))
        self.action()
        #self.frame.menumap.enable()

    def OnUpdateUI(self,evt):
        dprint("menu item %s (widget id=%d) on frame=%s" % (self.name,self.id,self.frame))
        self.Enable()

    def action(self, state=None, index=-1):
        pass

    def __call__(self, evt, number=None):
        self.dprint("%s called by keybindings" % self)
        self.action()

    def Enable(self):
        self.dprint("menu item %s (widget id=%d) enabled=%s" % (self.name,self.id,self.isEnabled()))
        self.widget.Enable(self.isEnabled())

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

    def OnMenuSelected(self,evt):
        dprint("menu item %s (widget id=%d) selected on frame=%s" % (self.name,self.id,self.frame))
        self.action()
        self.Check()
        #self.frame.menumap.enable()

    def OnUpdateUI(self,evt):
        dprint("menu item %s (widget id=%d) on frame=%s" % (self.name,self.id,self.frame))
        self.Enable()
        self.Check()

    def isChecked(self):
        raise NotImplementedError

    def Check(self):
        self.widget.Check(self.isChecked())
    
class ListAction(SelectAction):
    menumax=20
    inline=False
    
    def insertIntoMenu(self,menu,pos=None):
        self.menu=menu
        dprint("menu=%s" % str(self.menu))
        
        toplevel=True
        self.id=-1
        self.toplevel=[]
        if pos is None:
            pos=menu.GetMenuItemCount()
        dprint("pos=%d" % pos)
        self.widgetmap={}
        
        if not self.inline:
            # This is a named list, which means that all the items in
            # the list will be placed in a pop-right menu
            child=wx.Menu()
            self._insertMenu(menu,pos,child,self.name,True)
            self.topindex=pos
            pos=0
            menu=child
            toplevel=False
        else:
            self.topindex=pos
        
        self._insertItems(menu,pos,toplevel)
        dprint("self.toplevel=%s" % self.toplevel)

    def _insertItems(self,menu,pos,toplevel=False):
        items=self.getItems()
        
        self.count=0
        if len(items)>self.menumax:
            for group in range(0,len(items),self.menumax):
                last=min(group+self.menumax,len(items))
                groupname="%s ... %s" % (items[group],items[last-1])
                child=wx.Menu()
                i=0
                for name in items[group:last]:
                    self._insert(child,i,name)
                    i+=1
                self._insertMenu(menu,pos,child,groupname,toplevel)
                pos+=1
        else:
            for name in items:
                self._insert(menu,pos,name,toplevel=toplevel)
                pos+=1
                
        self.savehash=self.getHash()

    def _insert(self,menu,pos,name,toplevel=False):
        id=wx.NewId()
        widget=menu.Insert(pos,id,name,self.tooltip)
        self.widgetmap[id]={'widget':widget,'index':pos,'toplevel':toplevel}
        if toplevel:
            self.toplevel.append(id)
            self.frame.Connect(id,-1,wx.wxEVT_UPDATE_UI,self.OnUpdateUI)
        self.frame.Connect(id,-1,wx.wxEVT_COMMAND_MENU_SELECTED,
                           self.OnMenuSelected)
        self.count+=1

    def _insertMenu(self,menu,pos,child,name,toplevel=False):
        id=wx.NewId()
        widget=menu.InsertMenu(pos,id,name,child)
        self.widgetmap[id]={'widget':widget,'index':pos,'toplevel':toplevel}
        if toplevel:
            self.toplevel.append(id)
            self.frame.Connect(id,-1,wx.wxEVT_UPDATE_UI,self.OnUpdateUI)

    def OnMenuSelected(self,evt):
        self.id=evt.GetId()
        dprint("list item %s (widget id=%s) selected on frame=%s" % (self.widgetmap[self.id]['index'],self.id,self.frame))
        self.action(index=self.widgetmap[self.id]['index'])
        #self.frame.menumap.enable()

    def OnUpdateUI(self,evt):
        dprint("menu item %s (widget id=%d) on frame=%s" % (self.name,self.id,self.frame))
        self.Enable()

    def getHash(self):
        return self.count
                   
    def dynamic(self):
        if self.savehash == self.getHash():
            dprint("dynamic menu not changed.  Skipping")
            return
        dprint("toplevel=%s" % self.toplevel)
        dprint("widgetmap=%s" % self.widgetmap)
        dprint("items in list: %s" % self.menu.GetMenuItems())
        pos=0
        for item in self.menu.GetMenuItems():
            if item.GetId()==self.toplevel[0]:
                break
            pos+=1
        dprint("inserting items at pos=%d" % pos)
        for id in self.toplevel:
            dprint("disconnecting widget %d" % id)
            self.frame.Disconnect(id,-1,wx.wxEVT_UPDATE_UI)
            dprint("deleting widget %d" % id)
            self.menu.Delete(id)
        self.widgetmap={}
        dprint("inserting new widgets at %d" % pos)
        self.insertIntoMenu(self.menu,pos)

    def getItems(self):
        raise NotImplementedError

    def Enable(self):
        self.dprint("Enabling all items: %s" % str(self.toplevel))
        for id in self.toplevel:
            #widget.Enable(self.isEnabled())
            self.menu.Enable(id,self.isEnabled())


class MenuBarActionMap(object):
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

        # Create order of menu titles
        self.hier={}

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
                hier[name]={'submenus':{}, 'items':[]}
            hier=hier[name]['submenus']
        if menukey[-1] not in hier:
            hier[menukey[-1]]={'submenus':{}, 'items':[]}
        return hier[menukey[-1]]

    def setorderer(self,menukey,menu):
        hier=self.gethier(menukey)
        hier['order']=menu
        
    def addMenu(self,parent,menu):
        menukey=self.getkey(parent,menu.name)
        self.setorderer(menukey,menu)
        
        dprint("Adding %s to menu %s: key=%s" % (menu,parent,str(menukey)))
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

    def sorthier(self,hier):
        # Both submenus and items should be sorted together
        for menu in hier.keys():
            dprint("sorting: %s" % str(menu))
            submenus=hier[menu]['submenus']
            menus=[submenus[i]['order'] for i in submenus.keys()]
            menus.extend(hier[menu]['items'])
            order=Orderer(menus)
            menus=order.sort()
            hier[menu]['sorted']=menus
            dprint("sorted:  %s" % hier[menu]['sorted'])

            self.sorthier(hier[menu]['submenus'])

    def sort(self):
        """Sorts the list of menu items within each menu.  This is not
        called in the constructor because items are added using the
        L{addMenuItem} method of this object.
        """
        if not self.dirty:
            return

        dprint(self.hier)

        self.sorthier(self.hier)
        self.dirty=False

    def populateMenu(self,parent,hier):
        # Both submenus and items should be sorted together
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
                        submenu=wx.Menu()
                        widget.AppendMenu(-1,itemgroup.name,submenu)
                        menukey=self.getkey(currentkey,itemgroup.name)
                        h=self.gethier(menukey)
                        h['widget']=submenu
                        dprint("  submenu menukey %s: %s" % (str(menukey),h))
                    else:
                        for action in itemgroup.actions:
                            if action is None:
                                addsep=True
                            else:
                                if addsep:
                                    # Don't allow multiple separators or the
                                    # menu to end on a separator
                                    widget.AppendSeparator()
                                a=action(self,widget)
                                self.actions.append(a)
                                addsep=False
            if len(hier[menu]['submenus'])>0:
                self.populateMenu(self.getkey(parent,menu),hier[menu]['submenus'])


    def populate(self):
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
                dprint("  skipping hidden menu %s" % label)
                continue
            dprint("  processing menu %s" % label)
            menu = wx.Menu()
            if index<count:
                menubar.Replace(index, menu, label)
            else:
                menubar.Append(menu, label)

            menukey=self.getkey(parent,label)
            h=self.gethier(menukey)
            h['widget']=menu
            index+=1
           
        dprint(hier)
        self.populateMenu('root',hier['submenus'])

        while index<count:
            menubar.Remove(index)
            index+=1
        dprint("count=%d" % menubar.GetMenuCount())

    def enable(self):
        for action in self.actions:
            state=action.Enable()
            

    def find(self,menuname):
        menubar=self.frame.GetMenuBar()
        index = menubar.FindMenu(menuname)
        if index==wx.NOT_FOUND:
            raise IndexError("Menu %s not found" % menuname)
        menu=menubar.GetMenu(index)
        return menu

    def findSubmenu(self,menu,title):
        if isinstance(title,list) or isinstance(title,tuple):
            searchkey=str(title)
        else:
            searchkey=title
            title=[title]
            
        if menu in self.submenus:
            if searchkey in self.submenus[menu]:
                return self.submenus[menu][searchkey]
        else:
            self.submenus[menu]={}

        parent=menu
        sofar=[]
        for name in title:
            sofar.append(name)
            if str(sofar) in self.submenus[menu]:
                submenu=self.submenus[menu][str(sofar)]
            else:
                submenu=wx.Menu()
                dprint("submenu=%s name=%s" % (submenu,name))
                parent.AppendMenu(-1,name,submenu)
                self.submenus[menu][str(sofar)]=submenu
            parent=submenu
        return submenu



class MenuItemLoader(Component):
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

        dprint(self.extensions)
        later=[]
        for extension in self.extensions:
            dprint("collecting from extension %s" % extension)
            for mode,menu,group in extension.getMenuItems():
                if mode is None:
                    dprint("global menu %s: processing group %s" % (menu,group))
                    menumap.addMenuItems(menu,group)
                elif mode==major or mode in minors:
                    # save the major mode & minor mode until the
                    # global menu is populated
                    later.append((menu,group))
        for menu,group in later:
            dprint("mode %s, menu %s: processing group %s" % (mode,menu,group))
            menumap.addMenuItems(menu,group)

        # create the menubar
        menumap.populate()
        #menumap.enable()

        return menumap
