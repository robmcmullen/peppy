# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""
CodeExplorerMinorMode uses Stani's fold explorer idea to display a subset of
the fold hierarchy of the file.

Scintilla has language lexers built in to the C code that are capable of
doing a lot of preprocessing of the source file.  It's typically used for
syntax highlighting, but it can also extended to generate a nested list
of items that have some hierarchical relationship.

We can exploit that here to display a function list.
"""

import os

import wx

from peppy.third_party.pubsub import pub

from peppy.debug import *
from peppy.yapsy.plugins import *
from peppy.minor import *
from peppy.actions import *


class CodeExplorerMinorMode(MinorMode, wx.TreeCtrl):
    """Tree control to display Stani's fold explorer.
    """
    keyword="Code Explorer"
    
    default_classprefs = (
        IntParam('best_width', 300),
        IntParam('best_height', 500),
        BoolParam('springtab', True),
    )

    @classmethod
    def worksWithMajorMode(self, modecls):
        return hasattr(modecls, 'getFoldHierarchy')

    def __init__(self, parent, **kwargs):
        if wx.Platform == '__WXMSW__':
            style = wx.TR_HAS_BUTTONS
            self.has_root = True
        else:
            style = wx.TR_HIDE_ROOT|wx.TR_HAS_BUTTONS
            self.has_root = False
        wx.TreeCtrl.__init__(self, parent, -1, size=(self.classprefs.best_width, self.classprefs.best_height), style=style)
        MinorMode.__init__(self, parent, **kwargs)
        self.root = self.AddRoot(self.mode.getTabName())
        self.hierarchy = None
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnActivate)
        self.Bind(wx.EVT_TREE_ITEM_EXPANDED, self.OnExpand)
        self.Bind(wx.EVT_TREE_ITEM_COLLAPSED, self.OnCollapse)
        self.Bind(wx.EVT_TREE_ITEM_COLLAPSING, self.OnCollapsing)
        pub.subscribe(self.foldChanged, 'fold_changed')
    
    def foldChanged(self, mode):
        if mode == self.mode:
            #dprint("fold changed in correct mode!")
            self.update()
        else:
            #dprint("Fold changed for some other major mode.  Ignoring")
            pass
    
    def activateSpringTab(self):
        """Callback function from the SpringTab handler requesting that we
        initialize ourselves.
        
        """
        self.update()
        
    def activateMinorMode(self):
        """Callback function from the minor mode construction requesting that
        we initialize ourselves.
        
        """
        self.update()
        
    def update(self, evt=None):
        """Update tree with the source code of the editor"""
        hierarchy = self.mode.getFoldHierarchy()
        #dprint(hierarchy)
        if hierarchy != self.hierarchy:
            self.hierarchy = hierarchy
            
            self.Freeze()
            self.current_line = self.mode.GetCurrentLine()
            self.item_before = None
            top_item = self.GetFirstVisibleItem()
            #print("Top: %s" % self.GetItemText(top_item))
            self.replaceChildren(self.root,self.hierarchy)
            self.highlightCurrentItem(self.root)
            if self.has_root and not self.IsExpanded(self.root):
                self.Expand(self.root)
            #top_item = self.GetFirstVisibleItem()
            #print("Top: %s" % self.GetItemText(top_item))
            self.Thaw()
        else:
            self.UnselectAll()
            self.current_line = self.mode.GetCurrentLine()
            self.item_before = None
            self.highlightCurrentItem(self.root)
        if evt:
            evt.Skip()
    
    def appendChildren(self, wxParent, nodeParent):
        """Recursive capable function to add items from the fold explorer
        hierarchy to the tree
        """
        for nodeItem in nodeParent.children:
            if nodeItem.show:
                wxItem = self.AppendItem(wxParent, nodeItem.text.strip())
                self.SetPyData(wxItem, nodeItem)
                self.appendChildren(wxItem, nodeItem)
                if nodeItem.expanded:
                    self.Expand(wxItem)
                else:
                    self.Collapse(wxItem)
            else:
                # Append children of a hidden node to the parent
                self.appendChildren(wxParent, nodeItem)
    
    def replaceChildren(self, wxParent, nodeParent):
        """Recursive capable function to add items from the fold explorer
        hierarchy to the tree.
        
        This method replaces
        """
        wxItem, cookie = self.GetFirstChild(wxParent)
        new_items = nodeParent.children
        index = 0
        while wxItem and index < len(new_items):
            nodeItem = new_items[index]
            if nodeItem.show:
                old_text = self.GetItemText(wxItem)
                new_text = nodeItem.text.strip()
                if old_text != new_text:
                    #print("Replacing text: %s -> %s" % (old_text, new_text))
                    self.SetItemText(wxItem, nodeItem.text.strip())
                # always replace the pydata because the line numbers may have
                # shifted above this node
                self.SetPyData(wxItem, nodeItem)
                self.replaceChildren(wxItem, nodeItem)
                if nodeItem.expanded:
                    self.Expand(wxItem)
                else:
                    self.Collapse(wxItem)
            else:
                # Append children of a hidden node to the parent
                self.replaceChildren(wxParent, nodeItem)
            wxItem, cookie = self.GetNextChild(wxParent, cookie)
            index += 1
        if wxItem:
            # Have more items in current tree, but no items left to add.  Need
            # to remove the remaining items in this level of the tree (as well
            # as any children of the items).
            to_delete = []
            while wxItem:
                to_delete.append(wxItem)
                wxItem, cookie = self.GetNextChild(wxParent, cookie)
            #print("deleting %d items" % len(to_delete))
            for item in to_delete:
                if self.ItemHasChildren(item):
                    self.DeleteChildren(item)
                self.Delete(item)
        else:
            # have more items in the new list, so have to add them after the
            # last existing item
#            if len(new_items) - index > 0:
#                print("adding %d items" % (len(new_items) - index))
            while index < len(new_items):
                nodeItem = new_items[index]
                if nodeItem.show:
                    wxItem = self.AppendItem(wxParent, nodeItem.text.strip())
                    self.SetPyData(wxItem, nodeItem)
                    self.appendChildren(wxItem, nodeItem)
                    if nodeItem.expanded:
                        self.Expand(wxItem)
                    else:
                        self.Collapse(wxItem)
                else:
                    # Append children of a hidden node to the parent
                    self.appendChildren(wxParent, nodeItem)
                index += 1
    
    def highlightCurrentItem(self, parent):
        """Recursive capable function used to find the item that should be
        highlighted.
        
        Uses the current_line instance attribute to determine the line number,
        or if it is set to None, is used as the exit condition.
        """
        if self.current_line is not None:
            child, cookie = self.GetFirstChild(parent)
            while child:
                node = self.GetPyData(child)
                if node.start <= self.current_line:
                    self.item_before = child
                elif self.item_before is not None:
                    self.SelectItem(self.item_before)
                    self.current_line = None
                    self.item_before = None
                    break
                if self.ItemHasChildren(child):
                    self.highlightCurrentItem(child)
                if self.current_line is None:
                    break
                child, cookie = self.GetNextChild(parent, cookie)
            
    def OnActivate(self, evt):
        node = self.GetPyData(evt.GetItem())
        if node:
            self.mode.showLine(node.start)
        else:
            # root node shows line zero
            self.mode.showLine(0)
    
    def OnExpand(self, evt):
        node = self.GetPyData(evt.GetItem())
        if node:
            node.expanded = True
    
    def OnCollapse(self, evt):
        node = self.GetPyData(evt.GetItem())
        if node:
            node.expanded = False
    
    def OnCollapsing(self, evt):
        item = evt.GetItem()
        dprint(item)
        if item == self.root:
            # Don't allow the root item to be collapsed
            evt.Veto()
        evt.Skip()


class CodeExplorerPlugin(IPeppyPlugin):
    def getMinorModes(self):
        yield CodeExplorerMinorMode
