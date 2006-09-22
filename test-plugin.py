import os

import wx

from menudev import *
from buffers import *

class OpenCharlie(Command):
    name = "&Open Charlie..."
    tooltip = "Open a Charlie object"
    icon = wx.ART_FILE_OPEN

##    def isEnabled(self, state=None):
##        return not self.frame.isOpen()

    def runthis(self, state=None, pos=-1):
        print "exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos))
        self.frame.proxy.open(self.frame,"charlie")

class Stuff(Command):
    name = "Stuff"
    tooltip = "Do Stuff"
    icon = wx.ART_HELP_SETTINGS
    
    def __init__(self, frame):
        Command.__init__(self, frame)

class Things(Command):
    name = "Things"
    tooltip = "Do Things"
    icon = wx.ART_HELP_BOOK
    
    def __init__(self, frame):
        Command.__init__(self, frame)


menu_plugins=[
    ['main',[('&File',0.0)],OpenCharlie,0.2],
    ['charlie',[('&File',0.0)],Stuff,0.7],
    [Things],
    [None],
]

toolbar_plugins=[
    # toolbar plugins here...
#    ['main',OpenCharlie,0.1],
    ['charlie',Stuff,0.3],
    [Things],
    ]




class CharlieView(View):
    pluginkey = 'charlie'
    keyword='Charlie'
    icon='icons/map_magnify.png'
    regex="charlie"

    def createWindow(self,parent):
        self.win=wx.Window(parent, -1)
        wx.StaticText(self.win, -1, self.buffer.name, (145, 145))
   

viewers=[
    CharlieView,
    ]


if __name__ == "__main__":
    app=testapp(0)
    frame=RootFrame(app.main)
    frame.Show(True)
    app.MainLoop()

