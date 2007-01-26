#!/usr/bin/env python

import os,sys,time
up_one=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(up_one)

from cStringIO import StringIO
import wx
import wx.aui

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
        self.frame.OnClose()

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

class MajorModeSelect(RadioAction):
    name="Major Mode"
    inline=False
    tooltip="Switch major mode"

    items=['none','Fundamental','C++','Python']

    def saveIndex(self,index):
        self.frame.settings['major mode']=MajorModeSelect.items[index]

    def getIndex(self):
        return MajorModeSelect.items.index(self.frame.settings['major mode'])
                                           
    def getItems(self):
        return MajorModeSelect.items

    def getIcons(self):
        return MajorModeSelect.items

    def action(self, index=0, old=-1):
        self.frame.switchMode(MajorModeSelect.items[index],
                              MajorModeSelect.items[old])

class MajorModeSelect2(MajorModeSelect):
    inline=True

class PythonShiftRight(SelectAction):
    name="Shift Region Right"
    icon=wx.ART_WARNING

class PythonShiftLeft(SelectAction):
    name="Shift Region Left"
    icon=wx.ART_QUESTION

class PythonMenuItems(Component):
    implements(IMenuItemProvider)
    implements(IToolBarItemProvider)
    
    def getMenuItems(self):
        yield ("Python",None,Menu("Python"))
        for action in PythonShiftRight,PythonShiftLeft,None:
            yield ("Python","Python",MenuItem(action))

    def getToolBarItems(self):
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
    tooltip="Enable display of asteroids"

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
    tooltip="Enable display of outer planets"

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
        dprint("BEFORE: frames: %s" % FrameList.frames)
        dprint("BEFORE: others: %s" % FrameList.others)
        FrameList.frames.remove(frame)

        # can't delete from a list that you're iterating on, so make a
        # new list.
        newlist=[]
        for other in FrameList.others:
            # Search through all related actions and remove references
            # to them. There may be more than one reference, so search
            # them all.
            if other.frame != frame:
                newlist.append(other)
        FrameList.others=newlist

        dprint("AFTER: frames: %s" % FrameList.frames)
        dprint("AFTER: others: %s" % FrameList.others)
        
        for actions in FrameList.others:
            actions.dynamic()
        
    def getHash(self):
        temp=tuple(self.frames)
        self.dprint("hash=%s" % hash(temp))
        return hash(temp)

    def getItems(self):
        return [frame.getTitle() for frame in self.frames]

    def action(self,state=None,index=0):
        self.dprint("top window to %d: %s" % (index,FrameList.frames[index]))
        self.frame.app.SetTopWindow(FrameList.frames[index])
        wx.CallAfter(FrameList.frames[index].Raise)

class FrameList2(FrameList):
    name="Frames"
    inline=True

class GlobalMenu(Component):
    implements(IMenuItemProvider)
    implements(IToolBarItemProvider)

    default_menu=((None,Menu("File").first()),
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
                  ("Edit",MenuItem(MajorModeSelect).first()),
                  ("Edit",MenuItem(MajorModeSelect2).first()),
                  (None,Menu("Elements").before("Major Mode")),
                  ("Elements",Menu("Metals")),
                  (None,Menu("Major Mode").hide()),
                  (None,Menu("Lists").after("Major Mode")),
                  (None,Menu("Minor Mode").hide().after("Major Mode")),
                  (None,Menu("Fun").after("Minor Mode")),
                  (None,Menu("Help").last()),
                  )
    def getMenuItems(self):
        for menu,item in self.default_menu:
            yield (None,menu,item)

    default_tools=((None,Menu("File").first()),
                  ("File",Separator("open")),
                  ("File",MenuItem(NewFrame).after("open")),
                  ("File",Separator("save").after("open")),
                  ("File",Separator("quit").after("save")),
                  ("File",MenuItem(CloseFrame).after("quit")),
                  ("File",MenuItem(Exit).last()),
                  (None,Menu("Edit").after("File").first()),
                  ("Edit",MenuItem(MajorModeSelect).first()),
                  ("Edit",MenuItem(MajorModeSelect2).first()),
                  (None,Menu("Planets").after("Edit").first()),
                  ("Planets",MenuItem(ShowAsteroids).first()),
                  ("Planets",MenuItem(ShowOuterPlanets).first()),
                  )
    def getToolBarItems(self):
        for menu,item in self.default_tools:
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


