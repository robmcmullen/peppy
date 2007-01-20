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
from plugin import *
from trac.core import *
from debug import *

from menu import *


class Exit(SelectAction):
    name="Exit"
    tooltip="Quit the program."

    def action(self, pos=-1):
        self.frame.CloseWindow(None)

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

class PythonMenu(Component):
    implements(IMenuBarProvider)
    mode="Python"

    def getMenuBar(self):
        return Menu("Python")

class PythonMenuItems(Component):
    implements(IModeMenuItems)
    menu="Python"
    
    def getMenuItems(self):
        return ("Python",MenuItemGroup("shift",PythonShiftRight,PythonShiftLeft,None))



class MenuSwitchers(Component):
    implements(IGlobalMenuItems)
    menu="File"

    def getMenuItems(self):
        return MenuItemGroup("switchers",NoMode,Python,CPlusPlus,None)

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
    implements(IGlobalMenuItems)
    implements(IMenuBarProvider)
    menu="Planets"

    def getMenuItems(self):
        return MenuItemGroup("inner",Mercury,Venus,Earth,Mars,None).first()

    def getMenuBar(self):
        return Menu("Planets")

class Asteroids(Component):
    implements(IGlobalMenuItems)
    menu="Planets"

    def getMenuItems(self):
        return MenuItemGroup("asteroids",ShowAsteroids,Ceres,None).after("inner")

class OuterPlanets(Component):
    implements(IGlobalMenuItems)
    menu="Planets"

    def getMenuItems(self):
        return MenuItemGroup("outer",ShowOuterPlanets,Jupiter,Saturn,Uranus,Neptune,Pluto,None,PlanetTen,None).after("asteroids")

class HelpMenu(Component):
    implements(IMenuBarProvider)

    def getMenuBar(self):
        return Menu("Help").last()

class FileMenu(Component):
    implements(IMenuBarProvider)

    def getMenuBar(self):
        return Menu("File").first()

class ProgramControl(Component):
    implements(IGlobalMenuItems)
    menu="File"

    def getMenuItems(self):
        return MenuItemGroup("exit",None,Exit).last()

class EditMenu(Component):
    implements(IMenuBarProvider)

    def getMenuBar(self):
        return Menu("Edit").after("File").first()

class ElementsMenu(Component):
    implements(IMenuBarProvider)

    def getMenuBar(self):
        return Menu("Elements").after("Planets")

class NobleGasses(ListAction):
    submenu='Inert'
    
    def getItems(self):
        return ['Helium','Neon','Argon']

class Alkalis(ListAction):
    submenu=['Metals','Alkalis']
    
    def getItems(self):
        return ['Lithium','Sodium','Potassium']

class AlkaliEarth(ListAction):
    submenu=['Metals','Alkali Earth']
    
    def getItems(self):
        return ['Beryllium','Magnesium','Calcium']

class ElementsMenuItems(Component):
    implements(IGlobalMenuItems)
    menu="Elements"

    def getMenuItems(self):
        return MenuItemGroup("noble",NobleGasses,Alkalis,AlkaliEarth)

class ListMenu(Component):
    implements(IMenuBarProvider)

    def getMenuBar(self):
        return Menu("Lists").after("Planets")

class SmallList(ListAction):
    def getItems(self):
        items=[]
        for i in range(10):
            items.append("Number %d" % i)
        return items

class BigList(ListAction):
    def getItems(self):
        items=[]
        for i in range(100):
            items.append("Number %d" % i)
        return items

class ListMenuItems(Component):
    implements(IGlobalMenuItems)
    menu="Lists"

    def getMenuItems(self):
        return MenuItemGroup("lists",SmallList,None,BigList)

class FunMenu(Component):
    implements(IMenuBarProvider)

    def getMenuBar(self):
        return Menu("Fun").after("Planets")




#-------------------------------------------------------------------

class MyFrame(wx.Frame):

    def __init__(self, app, id=-1):
        wx.Frame.__init__(self, None, id, 'Playing with menus', size=(400, 200))
        self.app=app
        
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
        
        menu5 = self.menumap.find("&Fun")
        # Show how to put an icon in the menu
        item = wx.MenuItem(menu5, 500, "&Smile!\tCtrl+S", "This one has an icon")
        #item.SetBitmap(images.getSmilesBitmap())
        menu5.AppendItem(item)

        # Shortcuts
        menu5.Append(501, "Interesting thing\tCtrl+A", "Note the shortcut!")
        menu5.AppendSeparator()
        menu5.Append(502, "Hello\tShift+H")
        menu5.AppendSeparator()
        menu5.Append(503, "remove the submenu")
        menu6 = wx.Menu()
        menu6.Append(601, "Submenu Item")
        menu5.AppendMenu(504, "submenu", menu6)
        menu5.Append(505, "remove this menu")
        menu5.Append(506, "this is updated")
        menu5.Append(507, "insert after this...")
        menu5.Append(508, "...and before this")


        # Menu events
        self.Bind(wx.EVT_MENU_HIGHLIGHT_ALL, self.OnMenuHighlight)

        self.Bind(wx.EVT_MENU, self.Menu500, id=500)
        self.Bind(wx.EVT_MENU, self.Menu501, id=501)
        self.Bind(wx.EVT_MENU, self.Menu502, id=502)
        self.Bind(wx.EVT_MENU, self.TestRemove, id=503)
        self.Bind(wx.EVT_MENU, self.TestRemove2, id=505)
        self.Bind(wx.EVT_MENU, self.TestInsert, id=507)
        self.Bind(wx.EVT_MENU, self.TestInsert, id=508)

        wx.GetApp().Bind(wx.EVT_UPDATE_UI, self.TestUpdateUI, id=506)

    # Methods
    def OnMenuHighlight(self, event):
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
        menuloader=MenuBarLoader(comp_mgr)
        self.menumap=menuloader.load(self,majormode,minormodes)
        
    def switchMode(self,mode):
        dprint("Switching to mode %s" % mode)
        self.setMenumap(mode)

    def CloseWindow(self, event):
        self.Close()

    def Menu500(self, event):
        dprint('Have a happy day!\n')

    def Menu501(self, event):
        dprint('Look in the code how the shortcut has been realized\n')

    def Menu502(self, event):
        dprint('Hello from Jean-Michel\n')


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


    def TestRemove2(self, evt):
        mb = self.GetMenuBar()
        mb.Remove(4)


    def TestUpdateUI(self, evt):
        text = time.ctime()
        evt.SetText(text)


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
        return True
    
def run(options=None,args=None):
    if options is not None:
        if options.logfile:
            debuglog(options.logfile)
    app=TestApp(redirect=False)
    frame=MyFrame(app)
    frame.Show(True)
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

