#!/usr/bin/env python

import os,sys,time
up_one=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(up_one)

from cStringIO import StringIO
import wx
import wx.aui

from peppy.debug import *

from ngmenu import *
_ = str

class NewFrame(SelectAction):
    name="New Frame"
    tooltip="Open a new window."
    icon = "icons/tux.png"
    default_menu = (None, ('File', 0), -1)
    key_bindings = {'win': "C-N", }

    def action(self, pos=-1):
        self.frame.app.NewFrame()

class CloseFrame(SelectAction):
    name="Close Frame"
    tooltip="Close the current Frame."
    icon="icons/cross.png"
    default_menu = (None, 'File', 10)
    
    def isEnabled(self):
        if len(FrameList.frames) > 1:
            return True
        return False
    
    def action(self, pos=-1):
        self.frame.OnClose()
        
class ShowToolbar(ToggleAction):
    name="Show Toolbar"
    tooltip="Enable display of toolbar"
    default_menu = (None, 'File', -300)

    def isChecked(self):
        return self.frame.settings['toolbar']

    def action(self):
        self.frame.settings['toolbar'] = not self.frame.settings['toolbar']
        self.frame.setMenumap()

class Exit(SelectAction):
    name="Exit"
    tooltip="Quit the program."
    icon = "icons/bug.png"
    default_menu = (None, 'File', -1000)

    def action(self, pos=-1):
        self.frame.app.Exit()

class Python(SelectAction):
    name="Python Mode"
    tooltip="Switch to Python Mode."
    default_menu = (None, 'Modes', 300)

    def action(self, pos=-1):
        self.frame.switchMode('Python')

class CPlusPlus(SelectAction):
    name="C++ Mode"
    tooltip="Switch to C++ Mode."
    default_menu = (None, 'Modes', 300)

    def action(self,  pos=-1):
        self.frame.switchMode('C++')

class MajorModeSelect(RadioAction):
    name="Major Mode"
    inline=False
    tooltip="Switch major mode"
    default_menu = (None, 'Modes', 200)

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
        self.frame.switchMode(MajorModeSelect.items[index])

class MajorModeSelect2(MajorModeSelect):
    inline=True

class PythonShiftRight(SelectAction):
    name="Shift Region Right"
    icon=wx.ART_WARNING
    default_menu = ('Python', 'Edit', 100)

class PythonShiftLeft(SelectAction):
    name="Shift Region Left"
    icon=wx.ART_QUESTION
    default_menu = ('Python', 'Edit', 200)

class Mercury(SelectAction):
    name="Mercury"
    tooltip="This text in statusbar if in menu or tooltip if in toolbar"
    default_menu = (None, ('Planets', 10), 0)

class Venus(SelectAction):
    name="Venus"
    default_menu = (None, 'Planets', 100)

class Earth(SelectAction):
    name="Earth"
    default_menu = (None, 'Planets', 101)

class Mars(SelectAction):
    name="Mars"
    default_menu = (None, 'Planets', 102)

class ShowAsteroids(ToggleAction):
    name="Asteroids"
    tooltip="Enable display of asteroids"
    default_menu = (None, 'Planets', -103)

    def isChecked(self):
        return self.frame.settings['asteroids']

    def action(self):
        self.frame.settings['asteroids']=not self.frame.settings['asteroids']

class Ceres(SelectAction):
    name="Ceres"
    default_menu = (None, 'Planets', 104)

    def isEnabled(self):
        return self.frame.settings['asteroids']

class ShowOuterPlanets(ToggleAction):
    name="Outer Planets"
    tooltip="Enable display of outer planets"
    default_menu = (None, 'Planets', -200)

    def isChecked(self):
        return self.frame.settings['outer planets']

    def action(self):
        self.frame.settings['outer planets']=not self.frame.settings['outer planets']

class OuterPlanet(SelectAction):
    def isEnabled(self):
        return self.frame.settings['outer planets']

class Jupiter(OuterPlanet):
    name="Jupiter"
    default_menu = (None, 'Planets', 205)

class Saturn(OuterPlanet):
    name="Saturn"
    default_menu = (None, 'Planets', 206)

class Uranus(OuterPlanet):
    name="Uranus"
    default_menu = (None, 'Planets', 207)

class Neptune(OuterPlanet):
    name="Neptune"
    default_menu = (None, 'Planets', 208)

class Pluto(OuterPlanet):
    name="Pluto"
    default_menu = (None, 'Planets', 209)

class PlanetTen(OuterPlanet):
    name="Planet 10"
    default_menu = (None, 'Planets', 210)

    def isEnabled(self):
        return False

class OpenRecent(ListAction):
    name="Open Recent"
    default_menu = (None, 'File', 100)

    def getItems(self):
        return ['file1.txt','file2.txt','file3.txt']

class FrameList(ListAction):
    name="Frames"
    default_menu = (None, ('Window', 990), 100)

    frames=[]
    others=[]
    
    def __init__(self, *args, **kwargs):
        ListAction.__init__(self, *args, **kwargs)
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
    name="Frames2"
    inline=True
    global_id = wx.NewId()
    default_menu = (None, 'Window', 200)

class ShowElements(ToggleAction):
    name="Show Elements"
    default_menu = (None, ('Stuff', 300), 10)

    def isChecked(self):
        return self.frame.app.settings['elements']

    def action(self):
        self.frame.app.settings['elements']=not self.frame.app.settings['elements']

class Hydrogen(SelectAction):
    name="Hydrogen"
    default_menu = (None, 'Stuff', 100)
    
    def isEnabled(self):
        return self.frame.app.settings['elements']

class NobleGasses(ListAction):
    name='Inert'
    default_menu = (None, 'Stuff', 200)

    def isEnabled(self):
        return self.frame.app.settings['elements']
    
    def getItems(self):
        return ['Helium','Neon','Argon']

class Alkalis(ListAction):
    name='Alkalis'
    default_menu = (None, 'Stuff/Metals', 100)

    def isEnabled(self):
        return self.frame.app.settings['elements']
    
    def getItems(self):
        return ['Lithium','Sodium','Potassium']

class AlkaliEarth(ListAction):
    name='Alkali Earth'
    default_menu = (None, 'Stuff/Metals', 200)

    def isEnabled(self):
        return self.frame.app.settings['elements']
    
    def getItems(self):
        return ['Beryllium','Magnesium','Calcium']

class SmallList(ListAction):
    inline=True
    default_menu = (None, 'Lists', 800)

    def getItems(self):
        items=[]
        for i in range(10):
            items.append("Number %d" % i)
        return items

class BigList(ListAction):
    inline=True
    default_menu = (None, 'Lists', 810)

    def getItems(self):
        items=[]
        for i in range(100):
            items.append("Number %d" % i)
        return items

def getActions():
    return [NewFrame, CloseFrame, Exit, ShowToolbar,
        MajorModeSelect, Python, CPlusPlus,
        PythonShiftLeft, PythonShiftRight,
        Mercury, Venus, Earth, Mars,
        ShowAsteroids, Ceres, ShowOuterPlanets, Jupiter, Saturn, Uranus,
        Neptune, Pluto, PlanetTen, OpenRecent, FrameList, FrameList2,
        SmallList, BigList, ShowElements, Hydrogen, NobleGasses, Alkalis,
        AlkaliEarth]