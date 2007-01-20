import os,sys,time
import wx

from orderer import *
from plugin import *
from trac.core import *
from debug import *


class SelectAction(debugmixin):
    debuglevel=1
    name=None
    help=""
    icon=None
    tooltip=""
    keyboard=None

    def __init__(self, frame, menu, extrinsic=None):
        self.frame=frame
        self.state=extrinsic
        self.insertIntoMenu(menu)

    def insertIntoMenu(self,menu):
        self.id=wx.NewId()
        self.widget=menu.Append(self.id, self.name, self.tooltip)
        self.frame.Connect(self.id,-1,wx.wxEVT_COMMAND_MENU_SELECTED,
                           self.OnMenuSelected)
        
    def OnMenuSelected(self,evt):
        dprint("menu item %s (widget id=%d) selected on frame=%s" % (self.name,self.id,self.frame))
        self.action()
        self.frame.menumap.enable()

    def action(self, state=None, pos=-1):
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
        self.Check()

    def OnMenuSelected(self,evt):
        dprint("menu item %s (widget id=%d) selected on frame=%s" % (self.name,self.id,self.frame))
        self.action()
        self.Check()
        self.frame.menumap.enable()

    def isChecked(self):
        raise NotImplementedError

    def Check(self):
        self.widget.Check(self.isChecked())
    
class ListAction(SelectAction):
    def insertIntoMenu(self,menu):
        self.widgetmap={}
        for name in self.getItems():
            id=wx.NewId()
            widget=menu.Append(id, name, self.tooltip)
            self.widgetmap[id]=widget
            self.frame.Connect(id,-1,wx.wxEVT_COMMAND_MENU_SELECTED,
                           self.OnMenuSelected)

    def OnMenuSelected(self,evt):
        self.id=evt.GetId()
        self.widget=self.widgetmap[self.id]
        dprint("list item %s (widget id=%s) selected on frame=%s" % (self.name,self.id,self.frame))
        self.action()
        self.frame.menumap.enable()

    def getItems(self):
        raise NotImplementedError

    def Enable(self):
        for menuid,widget in self.widgetmap.iteritems():
            self.dprint("menu item %s (widget id=%s) enabled=%s" % (self.name,menuid,self.isEnabled()))
            widget.Enable(self.isEnabled())


class MenuBarActionMap(object):
    def __init__(self,frame,menus):
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

        # Create order of menu titles
        order=Orderer(menus)
        rootmenus=order.sort()
        print rootmenus
        self.rootmenus=rootmenus

        # each menu title has a list of menu items below it
        self.menumap={}
        for rootmenu in rootmenus:
            self.menumap[rootmenu.name]=[]
        
    def addMenuItems(self,menuname,group):
        """Add a menu item (or group) to a menu.

        @param menuname: name of menu title to add to
        @type menuname: str
        @param group: group of menu items
        @type group: MenuItemGroup
        """
        self.menumap[menuname].append(group)
        self.dirty=True

    def sort(self):
        """Sorts the list of menu items within each menu.  This is not
        called in the constructor because items are added using the
        L{addMenuItem} method of this object.
        """
        if not self.dirty:
            return
        for menu in self.rootmenus:
            label=menu.name
            dprint("processing menu items for %s" % label)
            dprint("before: %s" % self.menumap[label])
            order=Orderer(self.menumap[label])
            itemgroups=order.sort()
            self.menumap[label]=itemgroups
            dprint("after: %s" % self.menumap[label])
        self.dirty=False

    def populate(self):
        """Populates the frame's menubar with the current definition.
        This replaces the current menubar in the frame.
        """
        self.sort()
        menubar=self.frame.GetMenuBar()
        index=0
        count=menubar.GetMenuCount()
        for menu in self.rootmenus:
            label=menu.name
            dprint("  processing menu %s" % label)
            menu = wx.Menu()
            if index<count:
                menubar.Replace(index, menu, label)
            else:
                menubar.Append(menu, label)

            addsep=False
            for itemgroup in self.menumap[label]:
                dprint("  processing itemgroup %s" % itemgroup)
                for action in itemgroup.actions:
                    if action is None:
                        addsep=True
                    else:
                        if addsep:
                            # Don't allow multiple separators or the
                            # menu to end on a separator
                            menu.AppendSeparator()
                        a=action(self.frame,menu)
                        self.actions.append(a)
                        addsep=False
            index+=1

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


class GlobalActionLoader(Component):
    debuglevel=0
    extensions=ExtensionPoint(IGlobalMenuItems)

    def load(self,menumap):
        """Load the global actions into the menu system.  Any
        L{Component} that implements the L{IGlobalMenuItems} interface
        will be loaded here and stuffed into the GUI.

        @param app: the main application object
        @type app: L{BufferApp<buffers.BufferApp>}
        """
        dprint(self.extensions)
        for proxy in self.extensions:
            group=proxy.getMenuItems()
            dprint("processing group %s" % group)
            menumap.addMenuItems(proxy.menu,group)

class ModeActionLoader(Component):
    debuglevel=0
    extensions=ExtensionPoint(IModeMenuItems)

    def load(self,menumap,major,minors):
        """Load the global actions into the menu system.  Any
        L{Component} that implements the L{IGlobalMenuItems} interface
        will be loaded here and stuffed into the GUI.

        @param app: the main application object
        @type app: L{BufferApp<buffers.BufferApp>}
        """
        dprint(self.extensions)
        for proxy in self.extensions:
            mode,group=proxy.getMenuItems()
            if mode==major or mode in minors:
                dprint("mode %s: processing group %s" % (mode,group))
                menumap.addMenuItems(proxy.menu,group)



class MenuBarLoader(Component):
    debuglevel=0
    extensions=ExtensionPoint(IMenuBarProvider)
    rootmenus=[]
    menumap={}
    dirty=False

    def load(self,frame,major=None,minors=[]):
        """Load the global actions into the menu system.  Any
        L{Component} that implements the L{IGlobalMenuItems} interface
        will be loaded here and stuffed into the GUI.

        @param app: the main application object
        @type app: L{BufferApp<buffers.BufferApp>}
        """
        dprint(self.extensions)
        menus=[]
        majorentries=[]
        minorentries=[]
        for entry in self.extensions:
            if not hasattr(entry,'mode'):
                menu=entry.getMenuBar()
                menus.append(menu)
            else:
                if entry.mode==major:
                    majorentries.append(entry)
                elif entry.mode in minors:
                    minorentries.append(entry)
        print menus

        # Load the major mode menus
        dprint("majorentries: %s" % majorentries)
        for entry in majorentries:
             menu=entry.getMenuBar()
             menus.append(menu)

        # Load the minor mode menus
        dprint("minorentries: %s" % minorentries)
        for entry in minorentries:
             menu=entry.getMenuBar()
             menus.append(menu)

        # Generate the menu bar mapper
        menumap=MenuBarActionMap(frame,menus)

        # Load the global actions
        comp_mgr=ComponentManager()
        loader=GlobalActionLoader(comp_mgr)
        loader.load(menumap)

        # Load the major mode actions
        loader=ModeActionLoader(comp_mgr)
        loader.load(menumap,major,minors)

        # create the menubar
        menumap.populate()
        menumap.enable()

        return menumap
