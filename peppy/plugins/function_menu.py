# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
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
from peppy.actions import *


class FoldExplorerMenu(ListAction, OnDemandActionMixin):
    debuglevel = 0
    name="Functions"
    inline=True
    tooltip="Go to a function"
    default_menu = ("Functions", 100)
    
    def getItems(self):
        fold = self.mode.getFoldHierarchy()
        nodes = fold.flatten()
        flat = [node.text.rstrip() for node in nodes]
        #dprint(flat)
        return flat
    
    def getHash(self):
        return (self.mode.getFoldHierarchy(), self.mode.GetLineCount())

    def updateOnDemand(self):
        # Update the dynamic menu here
        self.mode.getFoldHierarchy()
        self.dynamic()

    def action(self, index=-1, multiplier=1):
        fold = self.mode.getFoldHierarchy()
        node = fold.findFlattenedNode(index)
        #dprint("index=%d node=%s" % (index, node))
        self.mode.showLine(node.start)
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
        hierarchy = self.major.getFoldHierarchy()
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
        self.major.showLine(node.start)
        self.major.focus()


class FunctionMenuPlugin(IPeppyPlugin):
    def getMinorModes(self):
        yield FoldExplorerMinorMode
    
    def getCompatibleActions(self, major):
        if hasattr(major, 'getFoldHierarchy'):
            # Only if the major mode has the 'fold' property will the fold
            # explorer actually return anything meaningful, so to prevent an
            # empty 'Functions' menu, make sure the mode supports folding.
            props = major.getEditraSyntaxProperties(major.editra_lang)
            #dprint(props)
            for prop in props:
                if prop[0] == 'fold' and prop[1] == '1':
                    return [FoldExplorerMenu]
        return []
