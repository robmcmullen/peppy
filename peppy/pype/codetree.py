import wx
import sys
import os

icons = 1
colors = 1
colored_icons = 1
newroot = sys.platform != 'win32'

blue = wx.Colour(0, 0, 200)
red = wx.Colour(200, 0, 0)
green = wx.Colour(0, 200, 0)

D = {'cl':blue,
     'de':red,
     'cd':green,
     '\\l':red,
     '\\s':blue,
     '#d':green}

class TreeCtrl(wx.TreeCtrl):
    def __init__(self, parent, st):
        wx.TreeCtrl.__init__(self, parent, -1, style=wx.TR_DEFAULT_STYLE|wx.TR_HAS_BUTTONS|wx.TR_HIDE_ROOT)
        
        if icons:
            isz = (16,16)
            il = wx.ImageList(isz[0], isz[1])
            self.images = [wx.ArtProvider_GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, isz),
                        wx.ArtProvider_GetBitmap(wx.ART_FILE_OPEN, wx.ART_OTHER, isz),
                        wx.ArtProvider_GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, isz)]
            
            for icf in ('icons/green.gif', 'icons/yellow.gif', 'icons/red.gif'):
                #icf = os.path.join(_pype.runpath, icf)
                self.images.append(wx.BitmapFromImage(wx.Image(icf)))
            
            for i in self.images:
                il.Add(i)
            self.SetImageList(il)
            self.il = il
        self.SORTTREE = st
        self.root = self.AddRoot("Unseen Root")

    def OnCompareItems(self, item1, item2):
        if self.SORTTREE:
            return cmp(self.GetItemData(item1).GetData(),\
                       self.GetItemData(item2).GetData())
        else:
            return cmp(self.GetItemData(item1).GetData()[1],\
                       self.GetItemData(item2).GetData()[1])

class hierCodeTreePanel(wx.Panel):
    def __init__(self, root, parent, st):
        # Use the WANTS_CHARS style so the panel doesn't eat the Return key.
        wx.Panel.__init__(self, parent, -1, style=wx.WANTS_CHARS)
        self.parent = parent

        self.root = root

        tID = wx.NewId()

        self.tree = TreeCtrl(self, st)
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(self.tree, 1, wx.EXPAND)
        self.SetSizer(sizer)
        
        #self.tree.Expand(self.root)
        self.Bind(wx.EVT_LEFT_DCLICK, self.OnLeftDClick)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate)

    def new_hierarchy(self, hier):
        self.tree.DeleteAllItems()
        if newroot:
            #on GTK/Linux, tree.DeleteAllItems() kills the unseen root,
            #not so on Windows.
            self.tree.root = self.tree.AddRoot("Unseen Root")
        root = [self.tree.root]
        stk = [hier[:]]
        while stk:
            cur = stk.pop()
            while cur:
                name, line_no, leading, children = cur.pop()
                item_no = self.tree.AppendItem(root[-1], name)
                self.tree.SetPyData(item_no, line_no)
                if colors: self.tree.SetItemTextColour(item_no, D.get(name[:2], blue))
                if children:
                    if icons:
                        self.tree.SetItemImage(item_no, 0, wx.TreeItemIcon_Normal)
                        self.tree.SetItemImage(item_no, 1, wx.TreeItemIcon_Expanded)
                    stk.append(cur)
                    root.append(item_no)
                    cur = children[:]
                elif icons:
                    color = 2
                    if colored_icons:
                        n = line_no[2]
                        green = n.startswith('__') and n.endswith('__')
                        green = green or not n.startswith('_')
                        red = (not green) and n.startswith('__')
                        
                        if green:
                            color = 3
                        elif red:
                            color = 5
                        else:
                            color = 4
                    
                    self.tree.SetItemImage(item_no, color, wx.TreeItemIcon_Normal)
                    self.tree.SetItemImage(item_no, color, wx.TreeItemIcon_Selected)
            self.tree.SortChildren(root[-1])
            root.pop()

    def OnLeftDClick(self, event):
        #pity this doesn't do what it should.
        num, win = self.root.getNumWin(event)
        win.SetFocus()

    def OnActivate(self, event):
        num, win = self.root.getNumWin(event)
        dat = self.tree.GetItemData(event.GetItem()).GetData()
        if dat == None:
            return event.Skip()
        ln = dat[1]-1
        #print ln
        #print dir(win)
        linepos = win.GetLineEndPosition(ln)
        win.EnsureVisible(ln)
        win.SetSelection(linepos-len(win.GetLine(ln))+len(win.format), linepos)
        win.ScrollToColumn(0)
        win.SetFocus()
    
