# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
FoldExplorerMinorMode and FoldExplorerMenu use Stani's fold explorer idea to
display a subset of the fold hierarchy of the file.

Scintilla has language lexers built in to the C code that are capable of
doing a lot of preprocessing of the source file.  It's typically used for
syntax highlighting, but it can also extended to generate a nested list
of items that have some hierarchical relationship.

We can exploit that here to display a function list.
"""

import os

import wx

from peppy.debug import *
from peppy.yapsy.plugins import *
from peppy.minor import *
from peppy.menu import *


class FoldExplorerMenu(ListAction, OnDemandActionMixin):
    debuglevel = 0
    name="Functions"
    inline=True
    tooltip="Go to a function"
    default_menu = ("Functions", 100)
    
    def getItems(self):
        fold = self.mode.editwin.getFoldHierarchy()
        nodes = fold.flatten()
        flat = [node.text.rstrip() for node in nodes]
        #dprint(flat)
        return flat
    
    def getHash(self):
        return (self.mode.editwin.getFoldHierarchy(), self.mode.editwin.GetLineCount())

    def updateOnDemand(self):
        # Update the dynamic menu here
        self.mode.editwin.getFoldHierarchy()
        self.dynamic()

    def action(self, index=-1, multiplier=1):
        fold = self.mode.editwin.getFoldHierarchy()
        node = fold.findFlattenedNode(index)
        #dprint("index=%d node=%s" % (index, node))
        self.mode.editwin.showLine(node.start)
        self.mode.focus()


class FoldExplorerMinorMode(MinorMode, wx.TreeCtrl):
    """Tree control to display Stani's fold explorer.
    """
    keyword="Stani's Fold Explorer"
    
    default_classprefs = (
        IntParam('best_width', 200),
        IntParam('min_width', 200),
    )

    @classmethod
    def worksWithMajorMode(self, mode):
        return hasattr(mode, 'stc_viewer_class') and hasattr(mode.stc_viewer_class, 'getFoldHierarchy')

    def __init__(self, major, parent):
        wx.TreeCtrl.__init__(self, parent, -1, style=wx.TR_HIDE_ROOT|wx.TR_HAS_BUTTONS)
        self.major = major
        self.root = self.AddRoot('foldExplorer root')
        self.hierarchy = None
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate)
        self.Bind(wx.EVT_TREE_KEY_DOWN, self.update)
        self.update()
        
    def update(self, event=None):
        """Update tree with the source code of the editor"""
        hierarchy = self.major.editwin.getFoldHierarchy()
        #dprint(hierarchy)
        if hierarchy != self.hierarchy:
            self.hierarchy = hierarchy
            self.DeleteChildren(self.root)
            self.appendChildren(self.root,self.hierarchy)
    
    def appendChildren(self, wxParent, nodeParent):
        for nodeItem in nodeParent.children:
            if nodeItem.show:
                wxItem = self.AppendItem(wxParent, nodeItem.text.strip())
                self.SetPyData(wxItem, nodeItem)
                self.appendChildren(wxItem, nodeItem)
            else:
                # Append children of a hidden node to the parent
                self.appendChildren(wxParent, nodeItem)
            
    def OnActivate(self, evt):
        node = self.GetPyData(evt.GetItem())
        self.major.editwin.showLine(node.start)
        self.major.focus()


class FunctionMenuPlugin(IPeppyPlugin):
    def getMinorModes(self):
        yield FoldExplorerMinorMode
    
    def getCompatibleActions(self, majorcls):
        if hasattr(majorcls, 'stc_viewer_class') and hasattr(majorcls.stc_viewer_class, 'getFoldHierarchy'):
            return [FoldExplorerMenu]
        return []
