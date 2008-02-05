# -*- coding: utf8 -*-        
# Copyright (c) www.stani.be, GPL licensed
# Copyright (c) 2007 Rob McMullen
"""Scintilla Fold Explorer mixin for text editors

This is a mixin class based on Stani Michiels' fold explorer he posted to the
pyxides mailing list.
"""

import os, sys, random, time
import wx
import wx.stc

class FoldExplorerNode(object):
    def __init__(self, level, start, end, text, parent=None, styles=[]):
        """Folding node as data for tree item."""
        self.parent = parent
        self.level = level
        self.start = start
        self.end = end
        self.text = text
        self.styles = styles #can be useful for icon detection
        
        self.show = True
        self.children   = []
        
        # Storage for a flattened version of the hierarchy for use in menus.
        # This is typically only used in the root of the hierarchy.
        self.flattened = None
    
    def _flatten(self, parent):
        for node in parent.children:
            if node.show:
                self.flattened.append(node)
                self._flatten(node)
            else:
                # Append children of a hidden node to the parent
                self._flatten(node)

    def flatten(self):
        if not self.flattened:
            self.flattened = []
            self._flatten(self)
        return self.flattened
    
    def findFlattenedNode(self, index):
        flat = self.flatten()
        node = flat[index]
        return node

    def __str__(self):
        return "L%d s%d e%d %s" % (self.level, self.start, self.end, self.text.rstrip())

class FoldExplorerMixin(object):
    def _findRecomputeStart(self, parent, recompute_from_line, good):
        print parent
        
        # If the start of the parent is past the recompute point, we know that
        # none if its children will be before the recompute point, so go back
        # to the last known good node
        if parent.start > recompute_from_line:
            return good
        
        # If the end of this parent is still before the recompute position,
        # ignore all its children, because all of its children will be before
        # this position, too.
        if parent.end < recompute_from_line:
            return parent
        
        # OK, this parent is good: it's before the recompute point.  Search
        # its children now.
        good = parent
        for node in parent.children:
            check = self._findRecomputeStart(node, recompute_from_line, good)
            
            # If the end of the returned node is past the recompute point,
            # return it because that means that somewhere down in its
            # hierarchy it has found the correct node
            if check.end > recompute_from_line:
                return check
            
            # Otherwise, this node is good and continue with the search
            good = node
        
        # We've exhausted this parent's children without finding a node that's
        # past the recompute point, so it's still good.
        return good

    def findRecomputeStart(self, root, recompute_from=1000000):
        start = self._findRecomputeStart(root, recompute_from, None)
        print "found starting position for line %d: %s" % (recompute_from, start)
    
    def getFoldEntry(self, level, line, end):
        text = self.getFoldEntryFunctionName(line)
        node = FoldExplorerNode(level=level, start=line, end=end, text=text)
        node.show = text
        return node
    
    def recomputeFoldHierarchy(self, start_line, root, prevNode):
        t = time.time()
        n = self.GetLineCount()+1
        for line in range(start_line, n-1):
            foldBits    = self.GetFoldLevel(line)
            if foldBits&wx.stc.STC_FOLDLEVELHEADERFLAG:
                level = foldBits & wx.stc.STC_FOLDLEVELNUMBERMASK
                node = self.getFoldEntry(level, line, n)
                
                #folding point
                prevLevel = prevNode.level
                #print node
                if level == prevLevel:
                    #say hello to new brother or sister
                    node.parent = prevNode.parent
                    node.parent.children.append(node)
                    prevNode.end= line
                elif level>prevLevel:
                    #give birth to child (only one level deep)
                    node.parent = prevNode
                    prevNode.children.append(node)
                else:
                    #find your uncles and aunts (can be several levels up)
                    while level < prevNode.level:
                        prevNode.end = line
                        prevNode = prevNode.parent
                    if prevNode.parent == None:
                        node.parent = root
                    else:
                        node.parent = prevNode.parent
                    node.parent.children.append(node)
                    prevNode.end= line
                prevNode = node

        prevNode.end = line
        #print("Finished fold node creation: %0.5fs" % (time.time() - t))

    def computeFoldHierarchy(self):
        t = time.time()
        n = self.GetLineCount()+1
        prevNode = root = FoldExplorerNode(level=0,start=0,end=n,text='root',parent=None)
        self.recomputeFoldHierarchy(0, root, prevNode)
        return root
    
class SimpleFoldFunctionMatchMixin(object):
    """Simple getFoldEntryFunctionName provider that matches at the beginning
    of the line.
    
    This mixin looks at the class attribute 'fold_function_match' to determine
    if a potential fold entry should be included in the function list.
    'fold_function_match' should be a list of strings without leading
    whitespace that will be used to match against folded lines.
    """
    def getFoldEntryFunctionName(self, line):
        text = self.GetLine(line)
        name = text.lstrip()
        for start in self.fold_function_match:
            if name.startswith(start):
                return text
        return ""

class SimpleCLikeFoldFunctionMatchMixin(object):
    """Simple getFoldEntryFunctionName provider for C-like languages that
    matches at the beginning of the line.
    
    This mixin looks at the class attribute 'fold_function_ignore' to determine
    if a potential fold entry should be included in the function list.
    'fold_function_ignore' should be a list of strings without leading
    whitespace that will be used to match against folded lines.
    
    It also is aware of braces, and if a line contains only a single brace, it
    will backtrack until it finds a non-blank line.
    """
    
    #: default ignore list for C like languages.  Override in subclasses if you want to add more entries
    fold_function_ignore = ["}", "if", "else", "for", "do", "while", "switch",
                            "case", "enum", "struct"]
    
    def getFoldEntryFunctionName(self, line):
        text = self.GetLine(line)
        name = text.strip()
        #print "checking %s at %d" % (name, line)
        for start in self.fold_function_ignore:
            if name.startswith(start):
                print "  found bad %s at %d" % (name, line)
                return ""
        if name.startswith('{') or not name:
            while line > 0:
                text = self.GetLine(line - 1)
                name = text.strip()
                for start in self.fold_function_ignore:
                    if name.startswith(start):
                        print "  found bad %s at %d" % (name, line)
                        return ""
                if not name.startswith('#'):
                    break
                line = line - 1
        print "  found good %s at %d" % (name, line)
        return text

