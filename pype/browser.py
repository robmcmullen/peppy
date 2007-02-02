
#system imports
import os
import stat
import sys

#site-packages imports
import wx

#local imports
import filehistory

def ChangedPage(evt):
    nb = evt.GetEventObject()
    pn = evt.GetSelection()
    if nb.GetPageText(pn).startswith('Browse'):
        nb.GetPage(pn).showstuff()
    evt.Skip()

class LateBinding:
    def __init__(self, obj, name, attr):
        self.obj = obj
        self.name = name
        self.attr = attr
    def __call__(self, *args, **kwargs):
        return getattr(getattr(self.obj, self.name), self.attr)(*args, **kwargs)

class FilesystemBrowser(wx.Panel):
    def __init__(self, parent, root, pathnames=[], maxlen=0):
        wx.Panel.__init__(self, parent)
        self.root = root
        
        self.pathnames = pathnames
        self.maxlen = maxlen
        
        self.op = filehistory.FileHistory(self, callback=[self.chdir, LateBinding(self, 'browser', 'SetPath')], seq=self.pathnames,maxlen=self.maxlen)
        self.rp = filehistory.FileHistory(self, remove=1, callback=[self.op.ItemRemove], seq=self.pathnames,maxlen=self.maxlen,
                                delmsg=('Are you sure you want to delete the pathmark?\n%s', "Delete Pathmark?"))
        self.op.callback.append(self.rp.ItemAdd)
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)
        
        ## self.showstuff()
    
    def showstuff(self):
        if hasattr(self, 'button'):
            return
        
        ## print "called showstuff!"
        
        sizer = self.sizer
        
        self.button = wx.Button(self, -1, "Pathmark...")
        wx.EVT_BUTTON(self, self.button.GetId(), self.OnButton)
        sizer.Add(self.button, 0, wx.EXPAND)
        
        self.browser = wx.GenericDirCtrl(self, -1, style=wx.DIRCTRL_SHOW_FILTERS, filter=self.root.wildcard, defaultFilter=0)
        try:
            #for all other wxPython versions
            self.browser.ShowHidden(1)
        except TypeError:
            #for wxPython 2.7.0 - 2.7.1.2
            self.browser.ShowHidden = 1
        tree = self.browser.GetTreeCtrl()
        tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate, tree)
        sizer.Add(self.browser, 1, wx.EXPAND)
        
        #create menu
        self.m = wx.Menu()
        np = wx.NewId()
        self.m.Append(np, "Add Selected Path")
        wx.EVT_MENU(self, np, self.OnNewPathmark)
        
        self.m.AppendMenu(wx.NewId(), "Choose Path", self.op)
        self.m.AppendSeparator()
        self.m.AppendMenu(wx.NewId(), "Remove Path", self.rp)
        
        wx.CallAfter(self.sizer.Layout)
    
    def chdir(self, path):
        self.root.config.pop('lastpath', None)
        self.root.current_path = path
    
    def gethier(self):
        p = self.browser.GetFilePath()
        ## print "Path:", p
        return p

    def OnActivate(self, evt):
        fn = self.gethier()
        try:
            st = os.stat(fn)[0]
            if stat.S_ISREG(st):
                self.root.OnDrop([fn])
        except:
            evt.Skip()
    
    def OnNewPathmark(self, evt):
        fn = self.browser.GetPath()
        try:
            st = os.stat(fn)[0]
            if stat.S_ISDIR(st):
                self.op.ItemAdd(fn)
                self.rp.ItemAdd(fn)
        except:
            evt.Skip()
    
    def OnButton(self, evt):
        self.PopupMenu(self.m, self.button.GetPositionTuple())
