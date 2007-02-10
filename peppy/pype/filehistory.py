
import wx

root = None

class FileHistory(wx.Menu):
    def __init__(self, parent, name='', remove=0, callback=None, seq=[], maxlen=0, delmsg=('', '')):
        self.delmsg = delmsg
        if name:
            wx.Menu.__init__(self, name)
        else:
            wx.Menu.__init__(self)
        
        self.remove = remove
        if not callback:
            self.callback = []
        else:
            self.callback = callback
        self.maxlen = maxlen
        
        self.parent = parent
        
        for i in seq:
            if maxlen > 0 and len(self) >= maxlen:
                break
            iid = wx.NewId()
            self.Append(iid, i)
            wx.EVT_MENU(self.parent, iid, self.OnClicked)
        
        self.last = None
    
    def __len__(self):
        return self.GetMenuItemCount()
    
    def __iter__(self):
        for i in xrange(len(self)):
            yield self.FindItemByPosition(i)
    
    def GetLabels(self):
        return [i.GetLabel() for i in self]
    
    def ResetMenu(self):
        l = list(iter(self))
        l.reverse()
        for i in l:
            self.Delete(i.GetId())
    
    def ItemRemove(self, name):
        for item in self:
            if item.GetLabel() == name:
                if name == self.last:
                    self.last = None
                #ask user whether they really want to remove the pathmark
                self.Delete(item.GetId())
                return
    
    def ItemAdd(self, name):
        self.last = name
        
        for item in self:
            if item.GetLabel() == name:
                self.Remove(item.GetId())
                self.PrependItem(item)
                return
        
        if self.maxlen > 0 and len(self) >= self.maxlen:
            lst = list(iter(self))
            while lst and len(lst) >= self.maxlen:
                it  = lst.pop()
                iid = it.GetId()
                self.Delete(it)
        else:
            iid = wx.NewId()
            wx.EVT_MENU(self.parent, iid, self.OnClicked)
        
        self.Prepend(iid, name)
        
    def OnClicked(self, evt):
        eid = evt.GetId()
        label = self.GetLabel(eid)
        if label:
            if self.remove:
                if root.dialog(self.delmsg[0]%label, self.delmsg[1], wx.OK|wx.CANCEL)&1 != 0:
                    return
                self.ItemRemove(label)
            else:
                self.ItemAdd(label)
            for i in self.callback:
                i(label)
