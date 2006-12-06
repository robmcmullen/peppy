import os

import wx

from menudev import *
from buffers import *

class OpenCharlie(FrameAction):
    name = "&Open Charlie..."
    tooltip = "Open a Charlie object"
    icon = wx.ART_FILE_OPEN

##    def isEnabled(self, state=None):
##        return not self.frame.isOpen()

    def action(self, state=None, pos=-1):
        print "exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos))
        self.frame.open("charlie")

class Stuff(FrameAction):
    name = "Stuff"
    tooltip = "Do Stuff"
    icon = wx.ART_HELP_SETTINGS
    
    def __init__(self, frame):
        FrameAction.__init__(self, frame)

class Things(FrameAction):
    name = "Things"
    tooltip = "Do Things"
    icon = wx.ART_HELP_BOOK
    
    def __init__(self, frame):
        FrameAction.__init__(self, frame)




class CharlieView(View):
    pluginkey = 'charlie'
    keyword='Charlie'
    icon='icons/map_magnify.png'
    regex="charlie"

    defaultsettings={
        'menu_actions':[
            [[('&File',0.0)],Stuff,0.7],
            Things,
            None,
            ],
        'toolbar_actions':[
            [Stuff,0.3],
            Things,
            ]
        }

    def createEditWindow(self,parent):
        win=wx.Window(parent, -1)
        wx.StaticText(win, -1, self.buffer.name, (145, 145))
        return win

global_menu_actions=[
    [[('&File',0.0)],OpenCharlie,0.2],
]


class ViewFactory(Component,debugmixin):
    implements(IViewFactory)

    def viewScore(self,buffer):
        match=re.search(CharlieView.regex,buffer.filename)
        if match:
            return 100
        return 1

    def getView(self,buffer):
        return CharlieView
