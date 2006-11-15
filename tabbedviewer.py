import os,re

import wx
from debug import *

from views import getIconStorage



wxEVT_VIEWER_CHANGED = wx.NewEventType()

class ViewerChangedEvent(wx.PyCommandEvent):
    def __init__(self, viewer, eventType=wxEVT_VIEWER_CHANGED, id=1):
        wx.PyCommandEvent.__init__(self, eventType, id)
        self._eventType = eventType
        self._viewer=viewer

    def SetViewer(self, viewer):
        self._viewer=viewer

    def GetViewer(self):
        return self._viewer

class TabbedViewer(wx.Notebook,debugmixin):
    def __init__(self, parent, frame=None):
        wx.Notebook.__init__(self,parent,-1,style=wx.NO_BORDER)

        # if the frame is specified, chances are we're inside a
        # HideOneTabViewer.
        if frame is not None:
            self.frame=frame
        else:
            self.frame=parent
        
        getIconStorage().assign(self)
        
        self.managed=[] # dict with keys 'viewer','panel','box'

        self.updating=False
        self.Bind(wx.EVT_NOTEBOOK_PAGE_CHANGED, self.OnTabChanged)
        self.userChangedCallbacks=[]

    def addUserChangedCallback(self, func):
        self.userChangedCallbacks.append(func)

    def clearUserChangedCallbacks(self):
        self.userChangedCallbacks=[]

    def OnTabChanged(self,evt):
        self.dprint("changing to %s" % evt.GetSelection())
        if not self.updating:
            viewer=self.getViewer(evt.GetSelection())
            out=ViewerChangedEvent(viewer)
            for func in self.userChangedCallbacks:
                func(out)
        else:
            self.dprint("ignoring tab changed event for %d" % evt.GetSelection())
        evt.Skip()
    
    def showModified(self,viewer):
        index=self.findIndex(viewer)
        if index>=0:
            self.SetPageText(index,viewer.getTabName())            

    # Replace the current tab contents with this viewer, or create if
    # doesn't exist.
    def setViewer(self, viewer):
        index=self.GetSelection()
        if index>=0:
            self.updating=True
            managed=self.managed[index]
            managed['box'].Detach(managed['viewer'].win)
            managed['viewer'].close()
            viewer.createWindow(managed['panel'])
            managed['box'].Add(viewer.win, 1, wx.EXPAND)
            managed['box'].Layout()
            managed['viewer']=viewer
            self.SetPageText(index,viewer.getTabName())
            self.SetPageImage(index,viewer.getIcon())
            self.updating=False
        else:
            self.addViewer(viewer)
        viewer.open()

    # Add a viewer to a new tab
    def addViewer(self, viewer):
        self.updating=True
        index=self.GetPageCount()
        panel=wx.Panel(self, style=wx.NO_BORDER)
        box=wx.BoxSizer(wx.HORIZONTAL)
        panel.SetAutoLayout(True)
        panel.SetSizer(box)

        # if the window doesn't exist, create it; otherwise reparent it
        if not viewer.win:
            viewer.createWindow(panel)
            viewer.open()
        else:
            viewer.reparent(panel)
            viewer.win.Show()
        box.Add(viewer.win, 1, wx.EXPAND)
        panel.Layout()
        if self.AddPage(panel, viewer.getTabName()):
            managed={'panel': panel,
                     'box': box,
                     'viewer': viewer,
                     }
            self.managed.append(managed)
            self.SetPageImage(index,viewer.getIcon())
            self.SetSelection(index)
            self.dprint("added page=%d" % index)
            self.dprint("managed=%s" % str(self.managed))
        else:
            print "FIXME: error adding page #%d" % index
        self.updating=False

    def closeViewer(self, viewer, close=True):
        self.updating=True
        if viewer:
            index=self.findIndex(viewer)
        else:
            index=self.GetSelection()
        self.dprint("closing page %d" % index)
        if index>=0:
            self.RemovePage(index)

            managed=self.managed[index]
            del self.managed[index]
            if close: viewer.close() # don't close if we are reparenting!
                
            index=self.GetSelection()
            self.dprint("new current page=%d" % index)
            self.dprint("managed=%s" % str(self.managed))
        self.updating=False
        return index

    def getCurrentIndex(self):
        return self.GetSelection()

    def getCurrentViewer(self):
        index=self.GetSelection()
        if index>=0:
            return self.managed[index]['viewer']
        return None
        
    def getViewer(self,index):
        if index>=0 and index<len(self.managed):
            return self.managed[index]['viewer']
        return None
        
    def findIndex(self,viewer):
        for index in range(len(self.managed)):
            if viewer==self.managed[index]['viewer']:
                return index
        return -1
        

class HideOneTabViewer(wx.Panel,debugmixin):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, style=wx.NO_BORDER)
        self.frame=parent
        
        self.mainsizer=wx.BoxSizer(wx.VERTICAL)
        self.tabs=TabbedViewer(self,self.frame)
        self.mainsizer.Add(self.tabs,1,wx.EXPAND)
        self.SetAutoLayout(True)
        self.SetSizer(self.mainsizer)
        self.mainsizer.Hide(self.tabs)

        # This is the wxWindow that is being managed, not the View
        self.managed=None

        self.count=0
        self.viewer=None

    def addUserChangedCallback(self, func):
        self.tabs.addUserChangedCallback(func)

    def clearUserChangedCallbacks(self):
        self.tabs.clearUserChangedCallbacks()

    def setWindow(self, win):
        """Set the wxWindow that is managed by this notebook, not the
        Viewer.  The viewer is managed by setViewer; this is a
        lower-level function.
        """
        
        # GetItem throws an exception on Windows if no item exists at
        # that position.  On unix it just returns None as according to
        # the docs.  So, keep track of any managed window ourselves.
        if self.managed:
            self.mainsizer.Detach(1)
            # the old view is destroyed here.  Should I save the state
            # somehow so the next view of this buffer sees the same
            # location in the file?
            self.dprint("closing old self.managed=%s" % str(self.managed))
            #self.managed.Destroy()
            self.managed=None
        if win:
            self.mainsizer.Add(win,1,wx.EXPAND)
            self.mainsizer.Hide(self.tabs)
            self.mainsizer.Show(win)
            self.managed=win
        self.Layout()

    def setViewer(self, viewer):
        if self.count<=1:
            self.viewer=viewer
            viewer.createWindow(self)
            self.dprint("viewer.win=%s" % viewer.win)
            self.setWindow(viewer.win)
            self.dprint("after setWindow")
            viewer.open()
            self.dprint("after viewer.open")
            self.count=1
        else:
            self.tabs.setViewer(viewer)

    def addViewer(self,viewer):
        if self.count==0:
            self.setViewer(viewer)
            self.count=1
        elif self.count==1:
            if self.viewer.temporary:
                self.viewer.close()
                self.setViewer(viewer)
            else:
                # reparent!
                self.Freeze()
                self.mainsizer.Hide(self.managed)
                self.mainsizer.Show(self.tabs)
                self.mainsizer.Detach(self.managed)
                # add old viewer as tab 1 (new window is created)
                self.tabs.addViewer(self.viewer)
                # clean up old stuff, but don't delete old window till
                # after the new one is created so the viewer can clone
                # itself.  ACTUALLY, now don't delete at all but reparent.
                #self.managed.close()
                self.managed=None
                self.viewer=None
                # add new viewer as tab 2
                self.tabs.addViewer(viewer)
                self.Layout() # WXMSW: must call Layout after show/hide
                self.Thaw()
                self.count+=1
        else:
            self.tabs.addViewer(viewer)
            self.count+=1

    def closeViewer(self, viewer):
        if self.count>1:
            self.tabs.closeViewer(viewer)
            self.count-=1
            if self.count==1:
                # reparent from tabs
                viewer=self.tabs.getViewer(0)
                self.tabs.closeViewer(self.viewer,close=False)
                self.setViewer(viewer)
        elif self.count==1:
            if viewer==self.viewer:
##                win=wx.Window(self,-1)
##                self.setWindow(win)
                self.viewer.close()
                self.viewer=None
                self.count=0
                self.frame.titleBuffer()

    def getCurrentIndex(self):
        if self.count==0:
            return -1
        elif self.count==1:
            return 0
        else:
            return self.tabs.getCurrentIndex()

    def getCurrentViewer(self):
        if self.count==0:
            return None
        elif self.count==1:
            return self.viewer
        else:
            return self.tabs.getCurrentViewer()
        
    def getViewer(self,index):
        if self.count==0:
            return None
        elif self.count==1 and index==0:
            return self.viewer
        else:
            return self.tabs.getViewer(index)
        
    def findIndex(self,viewer):
        if self.count==0:
            return None
        elif self.count==1 and viewer==self.viewer:
            return 1
        else:
            return self.tabs.findIndex(viewer)

    def showModified(self,viewer):
        self.tabs.showModified(viewer)
            
