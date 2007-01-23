#-------------------------------------------------------------------
# essaimenu.py
#
# menus in wxPython 2.3.3
#
#-------------------------------------------------------------------
#
# o Debug message when adding a menu item (see last menu):
#
#   Debug: ..\..\src\msw\menuitem.cpp(370): 'GetMenuState' failed with 
#   error 0x00000002 (the system cannot find the file specified.). 
#

import os,sys,time
import wx
#import  images
from orderer import *
from trac.core import *
from debug import *

from menu import *


class NewFrame(SelectAction):
    name="New Frame"
    tooltip="Open a new window."

    def action(self, pos=-1):
        self.frame.app.NewFrame()

class CloseFrame(SelectAction):
    name="Close Frame"
    tooltip="Quit the program."

    def action(self, pos=-1):
        self.frame.app.CloseFrame(self.frame)

class Exit(SelectAction):
    name="Exit"
    tooltip="Quit the program."

    def action(self, pos=-1):
        self.frame.app.Exit()

class NoMode(SelectAction):
    name="No Mode"
    tooltip="Switch to default mode."

    def action(self, pos=-1):
        self.frame.switchMode('none')

class Python(SelectAction):
    name="Python Mode"
    tooltip="Switch to Python Mode."

    def action(self, pos=-1):
        self.frame.switchMode('Python')

class CPlusPlus(SelectAction):
    name="C++ Mode"
    tooltip="Switch to C++ Mode."

    def action(self,  pos=-1):
        self.frame.switchMode('C++')

class PythonShiftRight(SelectAction):
    name="Shift Region Right"

class PythonShiftLeft(SelectAction):
    name="Shift Region Left"

class PythonMenuItems(Component):
    implements(IMenuItemProvider)
    
    def getMenuItems(self):
        yield ("Python",None,Menu("Python"))
        for action in PythonShiftRight,PythonShiftLeft,None:
            yield ("Python","Python",MenuItem(action))



class MenuSwitchers(Component):
    implements(IMenuItemProvider)

    default_items=(("File",MenuItem(NoMode).after("save")),
                   ("File",MenuItem(Python).after("save")),
                   ("File",MenuItem(CPlusPlus).after("save")),
                   ("File",Separator("mode switching")),
                   )
    def getMenuItems(self):
        for menu,item in self.default_items:
            yield (None,menu,item)

class Mercury(SelectAction):
    name="Mercury"
    tooltip="This text in statusbar if in menu or tooltip if in toolbar"

class Venus(SelectAction):
    name="Venus"

class Earth(SelectAction):
    name="Earth"

class Mars(SelectAction):
    name="Mars"

class ShowAsteroids(ToggleAction):
    name="Asteroids"

    def isChecked(self):
        return self.frame.settings['asteroids']

    def action(self):
        self.frame.settings['asteroids']=not self.frame.settings['asteroids']

class Ceres(SelectAction):
    name="Ceres"

    def isEnabled(self):
        return self.frame.settings['asteroids']

class ShowOuterPlanets(ToggleAction):
    name="Outer Planets"

    def isChecked(self):
        return self.frame.settings['outer planets']

    def action(self):
        self.frame.settings['outer planets']=not self.frame.settings['outer planets']

class OuterPlanet(SelectAction):
    def isEnabled(self):
        return self.frame.settings['outer planets']

class Jupiter(OuterPlanet):
    name="Jupiter"

class Saturn(OuterPlanet):
    name="Saturn"

class Uranus(OuterPlanet):
    name="Uranus"

class Neptune(OuterPlanet):
    name="Neptune"

class Pluto(OuterPlanet):
    name="Pluto"

class PlanetTen(OuterPlanet):
    name="Planet 10"

    def isEnabled(self):
        return False

class InnerPlanets(Component):
    implements(IMenuItemProvider)

    def getMenuItems(self):
        yield (None,None,Menu("Planets").before("Elements"))
        yield (None,"Planets",MenuItemGroup("inner",Mercury,Venus,Earth,Mars,None).first())

class Asteroids(Component):
    implements(IMenuItemProvider)

    def getMenuItems(self):
        yield (None,"Planets",MenuItemGroup("asteroids",ShowAsteroids,Ceres,None).after("inner"))

class OuterPlanets(Component):
    implements(IMenuItemProvider)

    def getMenuItems(self):
        yield (None,"Planets",MenuItemGroup("outer",ShowOuterPlanets,Jupiter,Saturn,Uranus,Neptune,Pluto,None,PlanetTen,None).after("asteroids"))




class OpenRecent(ListAction):
    name="Open Recent"
    
    def getItems(self):
        return ['file1.txt','file2.txt','file3.txt']

class FrameList(ListAction):
    name="Frames"

    frames=[]
    others=[]
    
    def __init__(self, menumap, menu):
        ListAction.__init__(self,menumap,menu)
        FrameList.others.append(self)

    @staticmethod
    def append(frame):
        FrameList.frames.append(frame)
        for actions in FrameList.others:
            actions.dynamic()
        
    @staticmethod
    def remove(frame):
        FrameList.frames.remove(frame)
        for actions in FrameList.others:
            actions.dynamic()
        
    def getHash(self):
        temp=tuple(self.frames)
        dprint("hash=%s" % hash(temp))
        return hash(temp)

    def getItems(self):
        return [frame.getTitle() for frame in self.frames]

class FrameList2(FrameList):
    name="Frames"
    inline=True

class GlobalMenu(Component):
    implements(IMenuItemProvider)

    default_items=((None,Menu("File").first()),
                   ("File",Separator("open")),
                   ("File",MenuItem(NewFrame).after("open")),
                   ("File",MenuItem(FrameList).after("New Frame")),
                   ("File",MenuItem(FrameList2).after("New Frame")),
                   ("File",MenuItem(OpenRecent).after("New Frame")),
                   ("File",Separator("save").after("Open Recent")),
                   ("File",Separator("quit").after("save")),
                   ("File",MenuItem(CloseFrame).after("quit")),
                   ("File",MenuItem(Exit).last()),
                   (None,Menu("Edit").after("File").first()),
                   ("Edit",Menu("More Edits").first()),
                   (("Edit","More Edits"),MenuItem(OpenRecent).first()),
                   (None,Menu("Elements").before("Major Mode")),
                   ("Elements",Menu("Metals")),
                   (None,Menu("Major Mode").hide()),
                   (None,Menu("Lists").after("Major Mode")),
                   (None,Menu("Minor Mode").hide().after("Major Mode")),
                   (None,Menu("Fun").after("Minor Mode")),
                   (None,Menu("Help").last()),
                   )
    def getMenuItems(self):
        for menu,item in self.default_items:
            yield (None,menu,item)

class ShowElements(ToggleAction):
    name="Show Elements"

    def isChecked(self):
        return self.frame.app.settings['elements']

    def action(self):
        self.frame.app.settings['elements']=not self.frame.app.settings['elements']

class Hydrogen(SelectAction):
    name="Hydrogen"
    
    def isEnabled(self):
        return self.frame.app.settings['elements']

class NobleGasses(ListAction):
    name='Inert'

    def isEnabled(self):
        return self.frame.app.settings['elements']
    
    def getItems(self):
        return ['Helium','Neon','Argon']

class Alkalis(ListAction):
    name='Alkalis'
    
    def isEnabled(self):
        return self.frame.app.settings['elements']
    
    def getItems(self):
        return ['Lithium','Sodium','Potassium']

class AlkaliEarth(ListAction):
    name='Alkali Earth'
    
    def isEnabled(self):
        return self.frame.app.settings['elements']
    
    def getItems(self):
        return ['Beryllium','Magnesium','Calcium']

class ElementsMenuItems(Component):
    implements(IMenuItemProvider)

    default_items=((None,"Elements",MenuItem(ShowElements).first()),
                   (None,"Elements",Separator("element list")),
                   (None,"Elements",MenuItem(Hydrogen)),
                   (None,"Elements",MenuItem(NobleGasses)),
                   (None,("Elements","Metals"),MenuItemGroup("alkalis",Alkalis,AlkaliEarth)),
                   )
    def getMenuItems(self):
        for i in self.default_items:
            yield i

class SmallList(ListAction):
    inline=True
    
    def getItems(self):
        items=[]
        for i in range(10):
            items.append("Number %d" % i)
        return items

class BigList(ListAction):
    inline=True
    
    def getItems(self):
        items=[]
        for i in range(100):
            items.append("Number %d" % i)
        return items

class ListMenuItems(Component):
    implements(IMenuItemProvider)

    def getMenuItems(self):
        yield (None,"Lists",MenuItemGroup("lists",SmallList,None,BigList))




#-------------------------------------------------------------------

class MyFrame(wx.Frame,debugmixin):
    count=0
    
    def __init__(self, app, id=-1):
        wx.Frame.__init__(self, None, id, 'Playing with menus', size=(400, 200))
        self.app=app
        MyFrame.count+=1
        self.count=MyFrame.count
        FrameList.append(self)
        
        self.CenterOnScreen()

        self.CreateStatusBar()
        self.SetStatusText("This is the statusbar")

        tc = wx.TextCtrl(self, -1, """
A bunch of bogus menus have been created for this frame.  You
can play around with them to see how they behave and then
check the source for this sample to see how to implement them.
""", style=wx.TE_READONLY|wx.TE_MULTILINE)

        # Prepare the menu bar
        self.settings={'asteroids':False,
                       'inner planets':True,
                       'outer planets':True,
                       }
        
        self.SetMenuBar(wx.MenuBar())
        self.setMenumap()
        
        # Menu events
        self.Bind(wx.EVT_MENU_HIGHLIGHT_ALL, self.OnMenuHighlight)

    # Methods
    def Close(self):
        FrameList.remove(self)
        wx.Frame.Close(self)
        
    def OnMenuHighlight(self, event):
        dprint("stuff")
        # Show how to get menu item info from this event handler
        id = event.GetMenuId()
        item = self.GetMenuBar().FindItemById(id)
        if item:
            text = item.GetText()
            help = item.GetHelp()

        # but in this case just call Skip so the default is done
        event.Skip() 

    def setMenumap(self,majormode=None,minormodes=[]):
        comp_mgr=ComponentManager()
        menuloader=MenuItemLoader(comp_mgr)
        self.menumap=menuloader.load(self,majormode,minormodes)
        
    def switchMode(self,mode):
        dprint("Switching to mode %s" % mode)
        self.setMenumap(mode)

    def getTitle(self):
        return "Frame #%d" % self.count

    def TestRemove(self, evt):
        mb = self.GetMenuBar()
        submenuItem = mb.FindItemById(601)

        if not submenuItem:
            return

        submenu = submenuItem.GetMenu()
        menu = submenu.GetParent()

        # This works
        #menu.Remove(504)

        # this also works
        menu.RemoveItem(mb.FindItemById(504))  

        # This doesn't work, as expected since submenuItem is not on menu        
        #menu.RemoveItem(submenuItem)   

    def TestInsert(self, evt):
        theID = 508
        # get the menu
        mb = self.GetMenuBar()
        menuItem = mb.FindItemById(theID)
        menu = menuItem.GetMenu()

        # figure out the position to insert at
        pos = 0

        for i in menu.GetMenuItems():
            if i.GetId() == theID:
                break

            pos += 1

        # now insert the new item
        ID = wx.NewId()
        menu.Insert(pos, ID, "NewItem " + str(ID))
        # following doesn't work with 2.7?
##        item = wx.MenuItem(menu,ID)
##        item.SetId(ID)
##        item.SetText("NewItem " + str(ID))
##        menu.InsertItem(pos, item)


class TestApp(wx.App,debugmixin):
    def OnInit(self):
        self.settings={'elements':True,
                       }
        return True

    def NewFrame(self):
        frame=MyFrame(self)
        frame.Show(True)
    
    def CloseFrame(self, frame):
        frame.Close()

    def Exit(self):
        frames=[f for f in FrameList.frames]
        for frame in frames:
            frame.Close()

def run(options=None,args=None):
    if options is not None:
        if options.logfile:
            debuglog(options.logfile)
    app=TestApp(redirect=False)
    app.NewFrame()
    app.MainLoop()


if __name__ == '__main__':
    from optparse import OptionParser

    usage="usage: %prog file [files...]"
    parser=OptionParser(usage=usage)
    parser.add_option("-p", action="store_true", dest="profile", default=False)
    parser.add_option("-v", action="count", dest="verbose", default=0)
    parser.add_option("-l", action="store", dest="logfile", default=None)
    (options, args) = parser.parse_args()
    
    run(options)

