#!/usr/bin/env python
"""
This is an overly-complicated attempt at dynamic menus and toolbars.
Check out ulipad's makemenu.py and maketoolbar.py for more ideas on
how to make this easier to understand.
"""

import os,os.path,sys,re,time,commands,glob,bisect
from optparse import OptionParser


import wx
from wxemacskeybindings import *

from debug import dprint,debugmixin



# is each command a new instance?
class FrameAction(debugmixin):
    name = "FrameAction"
    help = "Help string"
    tooltip = "some tooltip help"
    icon = None
    keyboard = None
    dynamic = False # menu items can change
    dynamictools = False # toolbar items can change
    categories = False
    menutype = wx.ITEM_NORMAL
    
    def __init__(self, frame):
        self.frame=frame

    def __str__(self):
        return self.name

    # If you override run(), you have to do all the housekeeping.
    def run(self, state=None, pos=-1):
        self.dprint("id=%s name=%s" % (id(self),self.name))
        self.action(state,pos)
        self.frame.enableMenu()

    # If you override action(), all the housekeeping is done for you
    # and you just supply the command to run after the housekeeping is
    # complete.
    def action(self, state=None, pos=-1):
        pass

    def __call__(self, evt, number=None):
        self.dprint("%s called by keybindings" % self)
        self.action()

    # pass the state onto the frame without activating the user
    # interface action.
    def setProxyValue(self, state=None):
        pass

    def isEnabled(self, state=None):
        return True

    def isChecked(self, index=None):
        return False

    def getEntries(self):
        return [self.name]

    def getNumEntries(self):
        return 1

    # Regular menu item stuff

    def connectMenu(self,widget,id,callback):
        widget.Connect(id,-1,wx.wxEVT_COMMAND_MENU_SELECTED,callback)

    # Toolbar stuff

    def getToolbarIcon(self, pos=-1):
        return self.icon

    def getToolbarBitmap(self, pos=-1, size=(16,16)):
        icon=self.getToolbarIcon(pos)
        if icon is None:
            bitmap=wx.NullBitmap()
        elif icon.startswith("wxART"):
            bitmap=wx.ArtProvider.GetBitmap(icon, wx.ART_TOOLBAR,size)
        else:
            self.dprint("loading icon %s" % icon)
            bitmap=wx.Bitmap(icon)
        return bitmap

    def insertIntoToolbar(self,parentWidget,index,id,size,pos=-1):
        bitmap=self.getToolbarBitmap(pos,size)
        parentWidget.InsertLabelTool(index,id,self.name,bitmap,shortHelp=self.name,longHelp=self.tooltip,kind=self.menutype)

    def connectToolbar(self,widget,id,callback):
        widget.Connect(id,-1,wx.wxEVT_COMMAND_MENU_SELECTED,callback)

        
class FrameToggle(FrameAction):
    name = "FrameToggle"
    tooltip = "FrameToggle button"
    menutype = wx.ITEM_CHECK
    
    def __init__(self, frame):
        FrameAction.__init__(self, frame)
        self.checked=False

    def isChecked(self, index=None):
        return self.checked

    def run(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,pos))
        self.checked = not self.checked
        self.action(state,pos)


class FrameActionList(FrameAction):
    name = "FrameActionList"
    empty = "< empty list >"
    tooltip = "some help for this list"
    dynamic = True

    def __init__(self, frame):
        FrameAction.__init__(self, frame)

        # list of {'item':item,'name':name, and optional stuff like
        # 'icon':icon,...}
        self.itemlist = []

    def append(self,item,text=None):
        if not text:
            text=str(item)
        self.itemlist.append({'item':item,'name':text,'icon':None})

    def findIndex(self,item):
        for i in range(len(self.itemlist)):
            if self.itemlist[i]['item']==item: return i
        raise ValueError("item %s not found in list" % item)

    def setItemName(self,item,name):
        i=self.findIndex(item)
        self.itemlist[i]['name']=name

    def remove(self,item):
        index=self.findIndex(item)
        del self.itemlist[index]
        
    def isEnabled(self, state=None):
        if len(self.itemlist)==0:
            return False
        return True

    def getEntries(self,category=None):
        if len(self.itemlist)==0:
            return [self.empty]
        return [item['name'] for item in self.itemlist]

    def getItems(self,category=None):
        return [item['item'] for item in self.itemlist]

    def getNumEntries(self):
        if len(self.itemlist)==0:
            return 1
        return len(self.itemlist)

    def run(self, state=None, pos=-1):
        self.dprint("id(self)=%x name=%s pos=%s item=%s" % (id(self),self.name,str(pos),self.itemlist[pos]))
        self.action(state,pos)

    def insertIntoToolbar(self,parentWidget,index,id,size,pos=-1):
        control=wx.ComboBox(parentWidget,id,"",choices=self.getEntries(),size=(150,-1),style=wx.CB_DROPDOWN)
        parentWidget.InsertControl(index,control)

    def connectToolbar(self,widget,id,callback):
        widget.Connect(id,-1,wx.wxEVT_COMMAND_COMBOBOX_SELECTED,callback)
        widget.Connect(id,-1,wx.wxEVT_COMMAND_TEXT_ENTER,callback)

class CategoryList(FrameActionList):
    name = "CategoryList"
    empty = "< empty list >"
    tooltip = "some help for this list"
    dynamic = True
    categories = True

    itemdict = {}

    def __init__(self, frame):
        FrameActionList.__init__(self, frame)

        # list of {'item':item,'name':name, and optional stuff like
        # 'icon':icon,...}
        self.itemdict = {}

    def append(self,item,text=None):
        if not text:
            text=str(item)
        self.itemlist.append({'item':item,'name':text,'icon':None})

    def findIndex(self,item):
        for i in range(len(self.itemlist)):
            if self.itemlist[i]['item']==item: return i
        raise ValueError("item %s not found in list" % item)

    def setItemName(self,item,name):
        i=self.findIndex(item)
        self.itemlist[i]['name']=name

    def remove(self,item):
        index=self.findIndex(item)
        del self.itemlist[index]
        
    def isEnabled(self, state=None):
        if len(self.itemlist)==0:
            return False
        return True

    def getCategories(self):
        if len(self.itemdict)==0:
            return [self.empty]
        cats=self.itemdict.keys()
        cats.sort()
        return cats
    
    def getEntries(self,category=None):
        if category==None:
            entries=[]
            cats=self.itemdict.keys()
            cats.sort()
            if len(cats)>0:
                for category in cats:
                    for item in self.itemdict[category]:
                        entries.append(item['name'])
            else:
                entries=[self.empty]
            return entries
        elif category not in self.itemdict or len(self.itemdict[category])<1:
            return [self.empty]
        return [item['name'] for item in self.itemdict[category]]

    def getItems(self,category=None):
        if category==None:
            entries=[]
            cats=self.itemdict.keys()
            cats.sort()
            for category in cats:
                for item in self.itemdict[category]:
                    entries.append(item['item'])
            return entries
        elif category not in self.itemdict or len(self.itemdict[category])<1:
            return []
        return [item['item'] for item in self.itemdict[category]]

    def getNumEntries(self):
        if len(self.itemlist)==0:
            return 1
        return len(self.itemlist)

    def getToolbarIcon(self, index):
        item=self.itemlist[index]
        if 'icon' in item:
            return item['icon']
        return None
    
    def run(self, state=None, pos=-1):
        self.dprint("id(self)=%x name=%s pos=%d item=%s" % (id(self),self.name,pos,self.itemlist[pos]))
        self.action(state,pos)


class RadioList(FrameActionList):
    name = "RadioList"
    tooltip = "Some help for this group of radio items"
    menutype = wx.ITEM_RADIO

    def __init__(self, frame):
        FrameActionList.__init__(self, frame)
        self.itemlist = []
        self.selected = 0 # zero-based list, so we're selecting 'item 3'

    def isChecked(self, index):
        if index==self.selected:
            return True
        return False

    def run(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.selected = pos
        self.action(state,pos)





class NewWindow(FrameAction):
    name = "&New Window"
    tooltip = "Open a new window"
    keyboard = "C-X 5 2"
    
    def __init__(self, frame):
        FrameAction.__init__(self, frame)

    def action(self, state=None, pos=-1):
        frame=self.frame.app.newFrame(callingFrame=self.frame)
        frame.Show(True)


class FrameList(FrameActionList):
    name = "FrameList"
    empty = "< list of frames >"
    tooltip = "Bring the frame to the front"

    # File list is shared among all windows
    itemlist = []
    
    def __init__(self, frame):
        FrameActionList.__init__(self, frame)
        self.itemlist = FrameList.itemlist

    def action(self, state=None, pos=-1):
        self.dprint("id(self)=%x name=%s pos=%d id(itemlist)=%x" % (id(self),self.name,pos,id(self.itemlist)))
        self.dprint("  raising frame name=%s pos=%d" % (self.name,pos))
        self.itemlist[pos]['item'].Raise()
    
class DeleteWindow(FrameAction):
    name = "&Delete Window"
    tooltip = "Delete current window"
    
    def __init__(self, frame):
        FrameAction.__init__(self, frame)
        self.itemlist = FrameList.itemlist

    def action(self, state=None, pos=-1):
        self.frame.closeWindow(None)

    def isEnabled(self, state=None):
        if len(self.itemlist)>1:
            return True
        return False



class Open(FrameAction):
    name = "&Open Image..."
    tooltip = "Open an image or hypercube"
    icon = wx.ART_FILE_OPEN
    keyboard = "C-X C-F"


class OpenRecent(FrameActionList):
    name = "< no recent files >"
    tooltip = "Open a previously loaded file"
    debug = False

    # File list is shared among all windows, so it's a class attribute
    itemlist = []
    truncate = 10

    def __init__(self, frame):
        FrameAction.__init__(self, frame)
        self.itemlist=OpenRecent.itemlist

    def setFiles(self,filelist):
        # initial population of the list
        if filelist is not None:
            names=self.getItems()
            for name in filelist:
                if name not in names:
                    self.itemlist.append({'item':name,'name':name})
        if len(self.itemlist)>OpenRecent.truncate:
            self.itemlist[OpenRecent.truncate:]=[]
        self.dprint("itemlist=%s" % self.itemlist)

    # have to subclass append because in this case we add new stuff to
    # the beginning of the array.
    def append(self, item, text=None):
        # if name already exists, move it to the top of the list
        names=self.getItems()
        if item in names:
            index=names.index(item)
            if self.debug: print "found %s at %d.  Removing" % (item,index)
            del self.itemlist[index]
        newitem={'item':item,'name':item}
        self.itemlist[0:0]=[newitem]
        if len(self.itemlist)>OpenRecent.truncate:
            self.itemlist[OpenRecent.truncate:]=[]
        self.dprint("itemlist=%s" % self.itemlist)
        
    def action(self, state=None, pos=None):
        self.dprint("id=%x pos=%d name=%s" % (id(self),pos,self.itemlist[pos]['item']))
        self.frame.open(self.itemlist[pos]['item'])


class Save(FrameAction):
    name = "&Save Image..."
    tooltip = "Save the current image"
    icon = wx.ART_FILE_SAVE
    keyboard = "C-X C-S"

    def isEnabled(self, state=None):
        return False

class SaveAs(FrameAction):
    name = "Save &As..."
    tooltip = "Save the image as a new file"
    icon = wx.ART_FILE_SAVE_AS
    keyboard = "C-X C-W"
    
    def isEnabled(self, state=None):
        return False

class Quit(FrameAction):
    name = "E&xit"
    tooltip = "Quit the program."
    keyboard = "C-X C-C"
    
    def __init__(self, frame):
        FrameAction.__init__(self, frame)

    def action(self, state=None, pos=-1):
        self.frame.app.quit()



class TestRadioList(RadioList):
    name = "TestRadioList"
    tooltip = "Some help for this group of radio items"

    # radio list shared
    itemlist = [
        {'item':1,'name':'item 1','icon':wx.ART_COPY},
        {'item':2,'name':'item 2','icon':wx.ART_CUT},
        {'item':3,'name':'item 3','icon':wx.ART_PASTE},
        ]
    
    def __init__(self, frame):
        RadioList.__init__(self, frame)
        self.itemlist = TestRadioList.itemlist
        self.selected = 2 # zero-based list, so we're selecting 'item 3'


class FrameToggleList(FrameActionList):
    name = "FrameToggleList"
    tooltip = "Some help for this group of toggle buttons"
    menutype = wx.ITEM_CHECK
    dynamictools = True

    # radio list shared
    itemlist = [
        {'item':1,'name':'toggle 1','icon':wx.ART_HARDDISK,'checked':False},
        {'item':2,'name':'toggle 2','icon':wx.ART_FLOPPY,'checked':True},
        {'item':3,'name':'toggle 3','icon':wx.ART_CDROM,'checked':True},
        ]
    
    def __init__(self, frame):
        FrameActionList.__init__(self, frame)
        self.itemlist = FrameToggleList.itemlist

    def append(self,item,text=None):
        if not text:
            text=str(item)
        self.itemlist.append({'item':item,'name':text,'icon':None,'checked':False})

    def isChecked(self, index):
        if index>=0 and index<len(self.itemlist):
            return self.itemlist[index]['checked']
        return False
    
    def getToolbarIcon(self, index):
        item=self.itemlist[index]
        if 'icon' in item:
            return item['icon']
        return None
    
    def insertIntoToolbar(self,parentWidget,index,id,size,pos=-1):
        self.dprint("calling FrameAction parent method to create toolbar icons")
        FrameAction.insertIntoToolbar(self,parentWidget,index,id,size,pos)

    def run(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%d" % (id(self),self.name,pos))
        self.itemlist[pos]['checked'] = not self.itemlist[pos]['checked']
        state=self.itemlist[pos]['checked']
        self.action(state,pos)
    
class ShowToolbar(FrameToggle):
    name = "&Show Toolbar"
    tooltip = "Toggle the toolbar on and off"
    icon = wx.ART_TOOLBAR

    def isEnabled(self, state=None):
        return True
    
    def isChecked(self, index):
        return self.frame.toolbarvisible
    
    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s" % (id(self),self.name))
        self.frame.showToolbar(not self.frame.toolbarvisible)
    


all_plugins=[
    {'menubar':[('&File',0.0)],
     'command':Open,
     'weight':0.0,
     },
    [[('&File',0.0),('Open Recent',0.1)],OpenRecent,0.1],
    [[('&File',0.0)],None,None], # separator
    Save,
    SaveAs,
    None, # separator
    {'menubar':[('&File',0.0)],
     'command':Quit,
     'weight':1.0,
     },
    [[('&Windows',0.9)],NewWindow,0.0],
    [DeleteWindow,0.1],
    None,
    [FrameList,0.2],
    None,
    TestRadioList,
    None,
    FrameToggleList,
    ]

toolbar_plugins=[
    [Open,0.0],
    Save,
    SaveAs,
    None,
    TestRadioList,
    None,
    FrameToggleList,
    ]


def parseActionEntry(entry):
    if isinstance(entry,list):
        if len(entry)==1:
            menubar=None
            command=entry[0]
            weight=None
        elif len(entry)==2:
            menubar=None
            command=entry[0]
            weight=entry[1]
        elif len(entry)==3:
            menubar=entry[0]
            command=entry[1]
            weight=entry[2]
        else:
            dprint(entry)
    elif isinstance(entry,dict):
        menubar=entry['menubar']
        command=entry['command']
        weight=entry['weight']
    else:
        menubar=None
        command=entry
        weight=None
    return (menubar,command,weight)

class ActionMenuItemBase(debugmixin):
    debuglevel=0
    
    def __init__(self):
        self.command=None
        self.name='--none--'
        self.id = -1
        self.listpos = None # position in dynamic list

    def insertInto(self, parent, index):
        pass

    def connectEvent(self, frame):
        pass

    def enableInMenu(self, parent, state):
        pass

    def proxyValue(self, state):
        pass
        
    def getList(self):
        return [self]


class _ActionMenuSeparator(ActionMenuItemBase):
    def __init__(self):
        ActionMenuItemBase.__init__(self)
        self.name='--separator--'

    def insertInto(self, parent, index):
        parent.InsertSeparator(index)

ActionMenuSeparator=_ActionMenuSeparator()
        
class ActionMenuItem(ActionMenuItemBase):
    def __init__(self, frame, command, commandInstance=None, name=None, listpos=None):
        ActionMenuItemBase.__init__(self)
        self.frame=frame
        if commandInstance:
            self.command=commandInstance
        else:
            self.command=command(self.frame)
        if name:
            self.name=name
        else:
            self.name=self.command.name
        self.listpos=listpos

        self.id = wx.NewId()
        self.widget = None
        self.parentList = None # for list of items managed

    def insertInto(self, parentWidget, index):
        parentWidget.Insert(index,self.id,self.name,self.command.tooltip,self.command.menutype)
        self.widget=parentWidget.FindItemByPosition(index)
        self.dprint("self=%s widget=%s" % (self,self.widget))

    def removeFrom(self, parentWidget):
        parentWidget.Remove(self.id)

    def connectEvent(self, frameWidget):
        self.command.connectMenu(frameWidget,self.id,self.callback)
        #frameWidget.Connect(self.id,-1,wx.wxEVT_COMMAND_MENU_SELECTED,self.callback)
        
    def callback(self, ev):
        self.dprint("got event '%s' for frame '%s'" % (self.name,self.frame.name))
        self.command.run(self.frame.getState(),self.listpos)
        
    def enableInMenu(self, parentWidget, state):
        enable=self.command.isEnabled(state)
##        parentWidget.Enable(self.id,enable)
        self.widget.Enable(enable)
        if type!=wx.ITEM_NORMAL:
##        if type==wx.ITEM_CHECK:
            if self.widget.IsCheckable(): # this is necessary under windows
                checked=self.command.isChecked(self.listpos)
##            parentWidget.Check(self.id,checked)
                self.widget.Check(checked)

    # propogate toggle and radio values up into the frame so that the
    # application knows its state.
    def proxyValue(self, state):
        self.command.setProxyValue(state)

class ActionMenuList(ActionMenuItem):
    """Container class for a group of menu items that are maintained
    together.  This can be a dynamic list or maybe later will include
    a radio list."""
    
    def __init__(self, frame, command, commandInstance=None, parent=None, category=None):
        ActionMenuItemBase.__init__(self)
        self.frame=frame
        if commandInstance:
            self.command=commandInstance
        else:
            self.command=command(self.frame)
        self.name=self.command.name
        self.category=category

        self.id = -1 # ids are stored in a list now
        self.items = [] # ActionMenuItems associated with this list

        self.parentMenu=parent
    
    def getList(self):
        """Generate list of ActionMenuItems based on the text strings
        contained in the command instance."""
        
        entries=self.command.getEntries(self.category)
        self.dprint("inserting entries %s" % entries)
        self.dprint("  command=%s" % self.command)
        i=0
        for entry in entries:
            item=ActionMenuItem(self.frame,None,self.command,entry,i)
            # item.parentList=self
            self.items.append(item)
            i+=1
        return self.items

    def rebuildList(self):
        """Rebuild the list of ActionMenuItems in the parent Menu
        object.  When the list changes, menu items are created or
        destroyed only when necessary; the text of the widgets are
        renamed when possible."""
        
        entries=self.command.getEntries(self.category)
        old=len(self.items)
        current=len(entries)
        self.dprint("name %s: old entries=%d, new entries=%d" % (self.name,old,current))

        fewer=min(old,current)
        for i in range(fewer):
            item=self.items[i]
            self.dprint("  item=%s, entries[%d]=%s" % (item,i,entries[i]))

            # replace the item info with the new details
            item.name=entries[i]

            # replace the wx widget with the new details
            widget=self.parentMenu.widget.FindItemById(item.id)
            widget.SetText(item.name)

        if fewer<current:
            # need to add menu entries
            lastitem=self.items[i]
            for i in range (fewer,current):
                self.dprint("name %s: adding %s" % (self.name,entries[i]))
                item=ActionMenuItem(self.frame,None,self.command,entries[i],i)
                # item.parentList=self
                self.items.append(item)
                self.parentMenu.insertAfter(item,lastitem)
                lastitem=item
        elif fewer<old:
            # need to remove menu entries
            for i in range (fewer,old):
                item=self.items[i]
                self.dprint("name %s: removing %s" % (self.name,item.name))
                self.parentMenu.remove(item)
            self.items[fewer:old]=[]


class ActionMenuCategoryList(ActionMenuItem):
    """Container class for a group of menu items that are maintained
    together.  This can be a dynamic list or maybe later will include
    a radio list."""
    
    def __init__(self, frame, command, commandInstance=None, parent=None):
        ActionMenuItemBase.__init__(self)
        self.frame=frame
        if commandInstance:
            self.command=commandInstance
        else:
            self.command=command(self.frame)
        self.name=command.name

        self.id = -1 # ids are stored in a list now
        self.items = [] # ActionMenuItems associated with this list

        self.menus = [] # ActionMenus associated with this list
        self.menutolist = {}

        self.parentMenu=parent

    def newMenu(self,category):
        menu=ActionMenu(self.frame,category)
        self.menus.append(menu)
        menulist=ActionMenuList(self.frame,None,self.command,menu,category)
        self.menutolist[menu]=menulist
        menu.insertItem(menulist,0.5)
        return menu
    
    def getList(self):
        """Generate list of ActionMenuItems based on the text strings
        contained in the command instance."""
        
        cats=self.command.getCategories()
        for category in cats:
            self.dprint("inserting entries in category=%s" % category)
            menu=self.newMenu(category)
        return self.menus

    def rebuildList(self):
        """Rebuild the list of ActionMenuItems in the parent Menu
        object.  When the list changes, menu items are created or
        destroyed only when necessary; the text of the widgets are
        renamed when possible."""
        
        cats=self.command.getCategories()
        self.dprint("categories=%s" % cats)
        old=len(self.menus)
        current=len(cats)
        self.dprint("name %s: old entries=%d, new entries=%d" % (self.name,old,current))

        fewer=min(old,current)
        for i in range(fewer):
            item=self.menus[i]
            self.dprint("  menu=%s, category[%d]=%s" % (item,i,cats[i]))

            # replace the wx widget with the new details
            widget=self.parentMenu.widget.FindItemById(item.id)
            self.dprint("  parent=%s parent.widget=%s widget=%s id=%d" % (str(self.parentMenu),str(self.parentMenu.widget),str(widget),item.id))
            widget.SetText(cats[i])
            item.rebuildList() # rebuild sub menu

        if fewer<current:
            # need to add menu entries
            lastitem=self.menus[i]
            for i in range (fewer,current):
                self.dprint("name %s: adding %s" % (self.name,cats[i]))
                item=self.newMenu(cats[i])
                self.parentMenu.insertAfter(item,lastitem)
                lastitem=item
        elif fewer<old:
            # need to remove menu cats
            for i in range (fewer,old):
                item=self.menus[i]
                self.dprint("name %s: removing %s" % (self.name,item.name))
                self.parentMenu.remove(item)
            self.menus[fewer:old]=[]


class ActionMenu(ActionMenuItemBase):
    def __init__(self, frame, name):
        self.frame=frame
        self.command=None
        self.name=name

        self.menus = []
        self.menunames = []
        self.menuweights = []

        self.items = []
        self.itemweights = []

        self.dynamics = []

        self.id = wx.NewId()
        self.widget = wx.Menu()

    def getMenu(self, name, weight):
        """Get the ActionMenu that is a child of this menu.  If the
        menu already exists, simply return the pointer to it.  If it
        doesn't, create the ActionMenu and the wx component and return
        the ActionMenu."""
        
        if name in self.menunames:
            return self.menus[self.menunames.index(name)]

        menu=ActionMenu(self.frame, name)

        if weight<0.0:
            menuindex=0
        else:
            menuindex=bisect.bisect_right(self.menuweights,weight)
        self.menus.insert(menuindex,menu)
        self.menunames.insert(menuindex,name)
        self.menuweights.insert(menuindex,weight)

        self.insertMenu(menu, menuindex, weight)

        self.dprint(self.menunames)

        return menu

    def populateMenu(self, plugins, keymap=None):
        lastclass=None
        lastbar=None
        lastweight=0.5
        
        for plugin in plugins:
            menubar,command,weight=parseActionEntry(plugin)

            if menubar==None:
                menubar=lastbar
            if weight==None:
                weight=lastweight

            self.dprint("found menubar=%s command=%s weight=%f" % (str(menubar),command,weight))
            parent=self
            for name,menuweight in menubar:
                menu=parent.getMenu(name,menuweight)
                parent=menu
            self.dprint("inserting command=%s into menu %s" % (command,menu.name))

            if command:
                if command.dynamic:
                    if command.categories:
                        item=ActionMenuCategoryList(self.frame,command,None,menu)
                        self.dynamics.append(item)
                    else:
                        item=ActionMenuList(self.frame,command,None,menu)
                        self.dynamics.append(item)
                else:
                    item=ActionMenuItem(self.frame,command)

                # Add keyboard command to the specified keymap
                if keymap and command.keyboard:
                    try:
                        self.dprint("found key=%s for %s" % (command.keyboard,command))
                        keymap.define(command.keyboard,item.command)
                    except DuplicateKeyError:
                        dprint("apparently already defined the keyboard shortcut key for %s in keymap %s." % (command,keymap))

                        
            else:
                item=ActionMenuSeparator
            menu.insertItem(item,weight)

            lastbar=menubar
            lastweight=weight
            
    def remove(self, item):
        self.dprint("self=%s" % self)
        self.dprint("self.items=%s" % self.items)
        self.dprint("item=%s" % item)
        index=self.items.index(item)
        self.dprint("index=%d" % index)
        del self.items[index]
        del self.itemweights[index]
        item.removeFrom(self.widget)
        

    def insertIndex(self, item, weight):
        if weight<0.0:
            index=0
        else:
            index=bisect.bisect_right(self.itemweights,weight)
        self.items.insert(index,item)
        self.itemweights.insert(index,weight)
        return index

    def insertAfter(self, item, after):
        self.dprint("self=%s" % self)
        self.dprint("self.items=%s" % self.items)
        self.dprint("after=%s" % after)
        index=self.items.index(after)
        self.dprint("index=%d" % index)
        weight=self.itemweights[index]
        index+=1 # insert after this item
        self.items.insert(index,item)
        self.itemweights.insert(index,weight)
        item.insertInto(self.widget,index)
        item.connectEvent(self.frame)
        self.dprint("inserted %s (weight=%f) at position %d" % (item.name,weight,index))

    def insertMenu(self, menu, menuindex, weight):
        index=self.insertIndex(menu,weight)
        self.dprint("inserting menu %s in submenu %s at index=%d" % (menu.name,self.name,index))
        self.widget.InsertMenu(index,menu.id,menu.name,menu.widget)

    def insertItem(self, item, weight):
        for entry in item.getList():
            index=self.insertIndex(entry,weight)
            entry.insertInto(self.widget,index)
            entry.connectEvent(self.frame)
            self.dprint("inserted id=%d %s (weight=%f) at position %d" % (entry.id,entry.name,weight,index))

    # insert this menu into another menu
    def insertInto(self, parentWidget, index):
        parentWidget.InsertMenu(index,self.id,self.name,self.widget)
        self.dprint("self=%s widget=%s" % (self,self.widget))

    def rebuildList(self):
        return

    def updateDynamic(self):
        # look at each ActionMenuList object
        for dynamic in self.dynamics:
            dynamic.rebuildList()

    def enableInMenu(self, parent, state):
        self.dprint("currently, whole menus aren't greyed out.")
        pass

    def enable(self, state):
        for item in self.items:
            item.enableInMenu(self.widget,state)
        for menu in self.menus:
            menu.enable(state)

    # propogate toggle and radio values up into the frame so that the
    # application knows its state.
    def proxyValue(self, state):
        for item in self.items:
            item.proxyValue(state)
        for menu in self.menus:
            menu.proxyValue(state)

    def findItemByFrameAction(self, instance):
        item=None
        for item in self.items:
            self.dprint("searching %s" % item.name)
            if isinstance(item.command,instance):
                self.dprint("found %s in %s" % (item.command.name,item.name))
                return item
        item=None
        for menu in self.menus:
            item=menu.findItemByFrameAction(instance)
            if item: return item
            item=None
        return item


class ActionMenuBar(ActionMenu):
    def __init__(self, frame, plugins, keymap):
        ActionMenu.__init__(self,frame,None)

        # Apparently some platforms can only use SetMenuBar once, so
        # this new menu creation routine replaces menus if there is an
        # already existing menu on the frame.  I thought this would
        # help with the flicker on GTK, but apparently not.
        menubar=frame.GetMenuBar()
        if menubar:
            self.widget=menubar
            self.oldcount=menubar.GetMenuCount()
        else:
            self.widget=wx.MenuBar()
            self.oldcount=0
            frame.SetMenuBar(self.widget)
        self.count=0
        
        self.populateMenu(plugins,keymap)

    def finishInit(self):
        while self.oldcount>self.count:
            self.widget.Remove(self.count)
            self.oldcount-=1
            
        # Force new menus to be inserted instead of replaced after we
        # finish the initial population of the menu.
        self.oldcount=0

    def addMenu(self,plugins,keymap=None):
        self.populateMenu(plugins,keymap)


    # wx commands to insert a menu in a menu bar is different than
    # inserting into a menu, so this method has to be overridden.
    def insertMenu(self, menu, menuindex, weight):
        self.dprint("inserting menu %s at %d" % (menu.name,menuindex))
        if menuindex<self.oldcount:
            self.widget.Replace(menuindex,menu.widget,menu.name)
        else:
            self.widget.Insert(menuindex,menu.widget,menu.name)
        self.count+=1

    def buildDynamic(self):
        self.updateDynamic()


class ActionToolBarItem(ActionMenuItem):
    def __init__(self, frame, command, commandInstance=None, name=None, listpos=None, size=(-1,-1)):
        ActionMenuItem.__init__(self, frame, command, commandInstance, name, listpos)
        self.size=size

    def connectEvent(self, frameWidget):
        self.command.connectToolbar(frameWidget,self.id,self.callback)
        
    def insertInto(self, parentWidget, index):
        self.command.insertIntoToolbar(parentWidget,index,self.id,self.size,self.listpos)

    def enableInMenu(self, parentWidget, state):
        self.dprint("enabling %s in menu %s (listpos=%s)" % (self.name,self,self.listpos))
        enable=self.command.isEnabled(state)
        parentWidget.EnableTool(self.id,enable)

        # this works for both radio and toggle items in a toolbar.
        if self.command.menutype in [wx.ITEM_NORMAL,wx.ITEM_CHECK]:
            checked=self.command.isChecked(self.listpos)
            parentWidget.ToggleTool(self.id,checked)


ActionToolBarSeparator = ActionMenuSeparator

class ActionToolBarList(ActionToolBarItem):
    """Container class for a group of toolbar items that are
    maintained together.  Currently this is not a dynamic list."""
    
    def __init__(self, frame, command, parent, size=(-1,-1)):
        ActionMenuItemBase.__init__(self)
        self.frame=frame
        self.command=command(self.frame)
        self.name=command.name
        self.size=size

        self.id = -1 # ids are stored in a list now
        self.items = [] # ActionToolBarItems associated with this list

        self.parentToolBar=parent
    
    def getList(self):
        """Generate list of ActionToolBarItems based on the text strings
        contained in the command instance."""
        
        entries=self.command.getEntries()
        i=0
        for entry in entries:
            item=ActionToolBarItem(self.frame,None,commandInstance=self.command,name=entry,listpos=i,size=self.size)
            # item.parentList=self
            self.items.append(item)
            i+=1
        return self.items
            
class ActionToolBar(ActionMenu):
    def __init__(self, frame, plugins, keymap=None, size=None, reuse=True):
        ActionMenu.__init__(self,frame,None)

        # Reusing the same toolbar cures the flicker on GTK
        toolbar=frame.GetToolBar()

        # If we're using the same toolbar, delete all the existing tools
        if reuse:
            self.dprint("Clearing toolbar!")
            toolbar.ClearTools()
##            # FIXME!  Platforms seem to work differently
##            if wx.Platform == '__WXMSW__':
##                # Works on windows, crashes on linux.
##                toolbar.ClearTools()
##            else:
##                # Works on linux, crashes on windows.  But, I don't
##                # like not being able to find out how many tools there
##                # are...
##                while toolbar.DeleteToolByPos(0):
##                    pass
            
        self.widget=toolbar
        self.oldcount=0
        self.count=0
        
        if not size:
            if wx.Platform == '__WXGTK__':
                size=(16,16)
            else:
                size=(-1,-1)
        self.size = size

        self.addTools(plugins,keymap)

    def finishInit(self,visible=True):
        while self.oldcount>self.count:
            self.widget.Remove(self.count)
            self.oldcount-=1
            
        # Force new menus to be inserted instead of replaced after we
        # finish the initial population of the menu.
        self.oldcount=0
        self.widget.Freeze()
        self.show(visible)
        self.widget.Thaw()

    def show(self, visible):
        self.dprint("Showing toolbar=%s" % visible)
        self.widget.Realize()
        self.widget.SetMinSize(self.widget.GetSize())
        self.widget.Show(visible)

    def addTools(self, plugins, keymap=None):
        self.dprint("Adding plugins %s" % plugins)
        self.widget.Freeze()
        self.populateTools(plugins,keymap)
        self.widget.Realize() # WXMSW: without this, updates won't appear

        # WXMSW toolbar height hack; necessary after adding tools.
        # Must be after a Realize, or it won't determine the proper height.
        self.widget.SetMinSize(self.widget.GetSize())
        
        self.widget.Thaw()

    def populateTools(self, plugins, keymap=None):
        lastweight=0.5
        
        for plugin in plugins:
            if isinstance(plugin,list):
                if len(plugin)==1:
                    command=plugin[0]
                    weight=None
                elif len(plugin)==2:
                    command=plugin[0]
                    weight=plugin[1]
                else:
                    command=plugin[1]
                    weight=plugin[2]
            elif isinstance(plugin,dict):
                command=plugin['command']
                weight=plugin['weight']
            else:
                command=plugin
                weight=None
                
            if weight==None:
                weight=lastweight

            self.dprint("found command=%s weight=%f" % (command,weight))

            if command:
                if command.dynamictools:
                    item=ActionToolBarList(self.frame,command,self,size=self.size)
                    self.dynamics.append(item)
                else:
                    item=ActionToolBarItem(self.frame,command,size=self.size)
                    
                # Add keyboard command to the specified keymap
                if keymap and command.keyboard:
                    try:
                        self.dprint("found key=%s for %s" % (command.keyboard,command))
                        keymap.define(command.keyboard,item.command)
                    except DuplicateKeyError:
                        dprint("apparently already defined the keyboard shortcut key for %s in keymap %s." % (command,keymap))
                        
            else:
                item=ActionToolBarSeparator
            self.insertItem(item,weight)
            lastweight=weight
            


class MenuFrame(wx.Frame,debugmixin):
    debuglevel=0
    frameid = 0
    
    def __init__(self, app, framelist, size=(500,500), actions=None, toolbar=None):
        MenuFrame.frameid+=1
        self.name="peppy: Frame #%d" % MenuFrame.frameid
        wx.Frame.__init__(self, None, id=-1, title=self.name, pos=wx.DefaultPosition, size=size, style=wx.DEFAULT_FRAME_STYLE|wx.CLIP_CHILDREN)

        self.app=app
        self.menuactions=None
        self.toolbaractions=None
        self.keyboardactions=None

        # This is how to create a statusbar with more than one
        # division, but the automatic menubar help text always appears
        # in the first field.  Dunno how to change that.
##        self.statusbar=self.CreateStatusBar(3,wx.ST_SIZEGRIP)
##        self.statusbar.SetStatusWidths([50,50,-1])
##        self.statusbar.SetStatusText("x=0",0)
##        self.statusbar.SetStatusText("y=0",1)
##        self.statusbar.SetStatusText("255x640x256 BIL",2)
        self.statusbar=self.CreateStatusBar(1,wx.ST_SIZEGRIP)
        
        wx.EVT_CLOSE(self, self.closeWindow)

        self.framelist=framelist
        self.framelist.append(self)
        self.dprint("framelist = %x" % id(self.framelist))
        
        if actions:
            self.setMenuActions(actions)

        self.mainsizer=wx.BoxSizer(wx.VERTICAL)
        self.SetAutoLayout(True)
        self.SetSizer(self.mainsizer)

        self.toolbar=None
        self._recreateToolbar=False
        self.CreateToolBar(wx.TB_HORIZONTAL|wx.NO_BORDER|wx.CLIP_CHILDREN)
        #self.mainsizer.Add(self.toolbar,0,wx.EXPAND)
        
        win=wx.Window(self,-1)
        self.mainsizer.Add(win,1,wx.EXPAND)

        self.toolbarvisible=True
        if toolbar:
            self.setToolbarActions(toolbar)
            self.mainsizer.Show(self.toolbar)
        elif self.toolbar:
            self.mainsizer.Hide(self.toolbar)

        self.keys=KeyProcessor(self)
        self.keys.setGlobalKeyMap(self.app.globalKeys)
        self.Bind(wx.EVT_KEY_DOWN, self.KeyPressed)

        self.popup=self.getDummyMenu(popup=True)
        self.Bind(wx.EVT_RIGHT_DOWN, self.popupMenu)

    def __str__(self):
        return self.name

    def KeyPressed(self, evt):
        self.keys.process(evt)
##        if function:
##            print "num=%d function=%s" % (num,function)
##        else:
##            print "unprocessed by KeyProcessor"

    def createKeyMap(self,actions):
        keymap=KeyMap()
        for action in actions:
            if action and action.keyboard:
                self.dprint("found key=%s for %s" % (action.keyboard,action))
                keymap.define(action.keyboard,action(self))
        return keymap

    def setKeyboardActions(self,actions,keymap):
        try:
            for action in actions:
                action=parseKeyboardActionEntry(action)
                if action and action.keyboard:
                    self.dprint("found key=%s for %s" % (action.keyboard,action))
                    keymap.define(action.keyboard,action(self))
        except:
            dprint("apparently already defined the keyboard shortcut keys.")
            raise
            
    def popupMenu(self,evt):
        self.dprint("popping up menu for %s" % evt.GetEventObject())
        item=self.mainsizer.GetItem(1)
        if item:
            win=item.GetWindow()
            if not self.popup:
                self.popup=self.getDummyMenu(popup=True)
            win.PopupMenu(self.popup,evt.GetPosition())
        evt.Skip()

    def getDummyMenu(self,popup=False):
        file_menu = wx.Menu()
        file_menu.Append(wx.NewId(), "Stuff")
        file_menu.Append(wx.NewId(), "And")
        file_menu.Append(wx.NewId(), "Things")
        file_menu.Append(wx.NewId(), "&Exit")
        help_menu = wx.Menu()
        help_menu.Append(wx.NewId(), "About...")
        if popup:
            menu_bar = wx.Menu()
            menu_bar.AppendMenu(wx.NewId(), "&File", file_menu)
            menu_bar.AppendMenu(wx.NewId(), "&Help", help_menu)
        else:
            menu_bar = wx.MenuBar()
            menu_bar.Append(file_menu, "&File")
            menu_bar.Append(help_menu, "&Help")
        return menu_bar

    # manage the toolbar ourselves by overriding the Frame's method
    def CreateToolBar(self,style=wx.TB_HORIZONTAL|wx.NO_BORDER|wx.CLIP_CHILDREN):
        if self.toolbar==None or self._recreateToolbar:
            toolbar=wx.ToolBar(self,-1,style=style)
            toolbar.SetToolBitmapSize((16,16))
            self.SetToolBar(toolbar)
        return self.toolbar

    # override Frame's method to return our toolbar
    def GetToolBar(self):
        if self._recreateToolbar:
            return self.CreateToolBar()
        return self.toolbar

    # override Frame's method to set our toolbar
    def SetToolBar(self,toolbar):
        if toolbar != self.toolbar:
            if self.toolbar:
                self.mainsizer.Detach(self.toolbar)
                self.toolbar.Destroy()
            self.mainsizer.Insert(0,toolbar,0,wx.EXPAND)
            # If previous toolbar exists, relayout
            if self.toolbar:
                self.Layout()
            self.toolbar=toolbar

    def setMenuActions(self, actions, keymap=None):
        self.dprint(actions)
        self.menuactions=ActionMenuBar(self,actions,keymap)

        self.rebuildMenus()
        self.menuactions.finishInit()
            

    def setToolbarActions(self, actions, keymap=None, size=None):
        if len(actions)>0:
            self.toolbaractions=ActionToolBar(self,actions,keymap,size,reuse=not self._recreateToolbar)
##            self.toolbaractions.widget.Realize()
##            self.SetToolBar(self.toolbaractions.widget)
            self.toolbaractions.finishInit(self.toolbarvisible)
            self.toolbaractions.enable(self)

    def setMainWindow(self, win, destroy=True):
        # GetItem fails on Windows if no item exists at that position.
        # On unix it just returns None as according to the docs.
        item=self.mainsizer.GetItem(1)
        if item:
            oldwin=item.GetWindow()
            self.mainsizer.Detach(1)
            if destroy:
                if oldwin: oldwin.Destroy()
        else:
            oldwin=None
        self.mainsizer.Add(win,1,wx.EXPAND)
        win.Bind(wx.EVT_RIGHT_DOWN, self.popupMenu)
        self.Layout()
        return oldwin

    def showToolbar(self, state):
        if self.toolbaractions:
            self.toolbarvisible=state
            self.toolbaractions.show(state)
            self.Layout()
        
    def getState(self):
        return self
        
    def enableMenu(self):
        self.menuactions.enable(self)
        self.toolbaractions.enable(self)

    def rebuildMenus(self):
        if self.menuactions:
            self.menuactions.buildDynamic()
            self.menuactions.enable(self)
            self.menuactions.proxyValue(self)
        if self.toolbaractions:
            self.toolbaractions.enable(self)
            self.toolbaractions.proxyValue(self)

    def SetStatusText(self,text,log=None): # log for pype compat
        self.statusbar.SetStatusText(text)

    def closeWindow(self, ev):
        if self.framelist.getNumEntries()==1:
            self.app.quit()
        else:
            self.closeWindowHook()
            self.app.deleteFrame(self)
            self.framelist.remove(self)
            self.Destroy()
            self.app.rebuildMenus()

    def closeWindowHook(self):
        return True

    def showModalDialog(self,message,title,style=wx.OK | wx.ICON_INFORMATION):
        dlg = wx.MessageDialog(self, message, title, style)
        dlg.ShowModal()
        dlg.Destroy()

    def open(self,filename):
        pass

    def save(self,filename):
        pass


class MyApp(wx.App):
    def OnInit(self):
        self.frames=FrameList(self) # master frame list
        #self.frame = ImageFrame(None, -1, "Hello from wxPython")
        #self.frame.Show(True)
        # self.SetTopWindow(self.frame)
        
        self.globalKeys=KeyMap()

        return True

    def quit(self):
        print "prompt for unsaved changes..."
        sys.exit()

    def deleteFrame(self,frame):
        #self.pendingframes.append((self.frames.getid(frame),frame))
        #self.frames.remove(frame)
        pass
    
    def rebuildMenus(self):
        for frame in self.frames.getItems():
            frame.rebuildMenus()
        
    def newFrame(self,callingFrame=None):
        frame=MenuFrame(self,self.frames,actions=all_actions,toolbar=toolbar_actions)
        self.rebuildMenus()
        return frame
        
    def showFrame(self,frame):
        frame.Show(True)
        # frame.showBands((10,20,30),stretch)
        # frame.showTestPattern()


if __name__ == "__main__":
    usage="usage: %prog [-u] [-s filter_value] [-o file] file [files...]"
    parser=OptionParser(usage=usage)
    parser.add_option("-u", action="store_true", dest="unstretch")
    parser.add_option("-s", action="store", type="float", dest="filter",
                      default=.65)
    parser.add_option("-r", action="store", type="float", dest="red",
                      default=676.0)
    parser.add_option("-n", action="store", type="float", dest="nir",
                      default=788.0)
    parser.add_option("-b", action="store", type="float", dest="bluerange",
                      nargs=2, default=[400.0,500.0])
    parser.add_option("-o", action="store", dest="outputfile")
    (options, args) = parser.parse_args()
    print options

    app=MyApp(0)
    frame=app.newFrame()
    app.showFrame(frame)
    app.MainLoop()

