import sys
#sys.path.append('/opt/wx/src/wxPython/wx/tools/Editra/src')

import wx


app = wx.PySimpleApp()

from projecttree import *

frame = wx.Frame(None, -1, "Hello from wxPython")
proj = ProjectTree(frame, None)
proj.addProject("/opt/python/editra-projects-plugin-svn")
frame.Show(True)

app.MainLoop()
