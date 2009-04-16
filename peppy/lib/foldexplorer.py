# -*- coding: utf8 -*-        
# Copyright (c) www.stani.be, GPL licensed
# Copyright (c) 2007 Rob McMullen
"""Scintilla Fold Explorer mixin for text editors

This is a mixin class based on Stani Michiels' fold explorer he posted to the
pyxides mailing list.
"""

import os, sys, random, time, re
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
        self.expanded = True
        
        self.show = True
        self.children   = []

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
    
    def iterFoldEntries(self, line, last_line=-1):
        """Iterator returning items to be included in code explorer.
        
        Given the range of lines in the current mode, return a FoldExplorerNode
        for each item that should be included in the code explorer.
        """
        if last_line < 0:
            last_line = self.GetLineCount()
        while line < last_line:
            foldBits = self.GetFoldLevel(line)
            if foldBits&wx.stc.STC_FOLDLEVELHEADERFLAG:
                level = foldBits & wx.stc.STC_FOLDLEVELNUMBERMASK
                text = self.getFoldEntryFunctionName(line)
                if text:
                    node = FoldExplorerNode(level=level, start=line, end=last_line, text=text)
                    node.show = True
                    yield node
            line += 1
    
    def recomputeFoldHierarchy(self, start_line, root, prevNode, expanded=True):
        t = time.time()
        last = self.GetLineCount()
        for node in self.iterFoldEntries(start_line, last):
            node.expanded = expanded
            
            #folding point
            prevLevel = prevNode.level
            #print node
            if node.level == prevLevel:
                #say hello to new brother or sister
                node.parent = prevNode.parent
                node.parent.children.append(node)
                prevNode.end = node.start
            elif node.level>prevLevel:
                #give birth to child (only one level deep)
                node.parent = prevNode
                prevNode.children.append(node)
            else:
                #find your uncles and aunts (can be several levels up)
                while node.level < prevNode.level:
                    prevNode.end = node.start
                    prevNode = prevNode.parent
                if prevNode.parent == None:
                    node.parent = root
                else:
                    node.parent = prevNode.parent
                node.parent.children.append(node)
                prevNode.end = node.start
            prevNode = node

        prevNode.end = last
        #print("Finished fold node creation: %0.5fs" % (time.time() - t))

    def computeFoldHierarchy(self, expanded=True):
        t = time.time()
        n = self.GetLineCount()+1
        prevNode = root = FoldExplorerNode(level=0,start=0,end=n,text='root',parent=None)
        root.expanded = expanded
        self.recomputeFoldHierarchy(0, root, prevNode, expanded)
        return root
    
    def copyFoldHierarchyTreeExpansion(self, old_folds, new_folds):
        """Attempt to keep the same tree expansion state from the old fold list
        to the new one.
        
        For this to work well, the nodes should be in the same order
        """
        new_items = new_folds.children
        new_index = 0
        for old in old_folds.children:
            #print("old: %s" % old.text.strip())
            found = False
            for index in range(new_index, len(new_items)):
                if new_items[index].text == old.text:
                    new_items[index].expanded = old.expanded
                    #print(" found new %s. expanded=%s from %s" % (new_items[index].text.strip(), old.expanded, old.text.strip()))
                    self.copyFoldHierarchyTreeExpansion(new_items[index], old)
                    found = True
                    break
                #else:
                    #print(" skipping new %s" % new_items[index].text.strip())
            if found:
                new_index = index + 1


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
                return self.getFoldEntryPrettyName(start, text)
        return ""
    
    def getFoldEntryPrettyName(self, start, text):
        return text

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
    
    # regular expressions modified from pygments:
    # http://dev.pocoo.org/projects/pygments/browser/pygments/lexers/compiled.py
    _ws = r'(?:\s|//.*?\n|/[*].*?[*]/)+'
    
    funcre = re.compile(
        r'(?:\s*const)?' # function might return const reference
        r'\s*((?:[a-zA-Z0-9_*&\s])+?(?:\s|[*]+))' # return arguments
        r'([a-zA-Z_][a-zA-Z0-9_:<>]*(?:operator\s*(?:[+\-/*=<>&|%!^\[\]]+|new(?:\s*\[\])?|delete(?:\s*\[\])?))?)' # method name including possible template type parameter
        r'(\s*\((?:([^;]*?|\s*))\))' # signature
        r'(?:\s*const)?' # const
        r'(' + _ws + r')({)'
        )
    
    def getFoldEntryFunctionName(self, line):
        fold = (self.GetFoldLevel(line)&wx.stc.STC_FOLDLEVELNUMBERMASK) - wx.stc.STC_FOLDLEVELBASE
        # previous lines with the same fold level will determine the range to
        # search for a function name.
        start = line
        while start > 0:
            if (self.GetFoldLevel(start - 1)&wx.stc.STC_FOLDLEVELNUMBERMASK) - wx.stc.STC_FOLDLEVELBASE != fold:
                break
            start -= 1
        
        # Need both text and styling information, because we use the styling
        # info to figure out the language keywords (we don't need to
        # explicitly specify a list here because the editra syntax stuff
        # already has a list of keywords tied to the styling code)
        bytes = self.GetStyledText(self.PositionFromLine(start),
                                   self.GetLineEndPosition(line))
        #print repr(bytes)
        
        # Remove comments and text strings so we're only left with code
        text = []
        style = []
        for index in xrange(0, len(bytes), 2):
            s = ord(bytes[index + 1])
            if not self.isStyleComment(s) and not self.isStyleString(s):
                text.append(bytes[index])
                style.append(s)
        code = "".join(text)
        self.dprint(" function name has to be within this block\nvvvvv\n%s\n^^^^^" % code)
        match = self.funcre.search(code)
        if match and match.group(1).strip():
            args = match.group(1).strip()
            name = match.group(2).strip()
            if args:
                index = match.start(2)
                
                # It's only a match if the return arguments and method name
                # aren't a reserved keyword.  We don't want stuff like "if
                # blah()" or "if (blah)" to match a function call.
                if not self.isStyleKeyword(style[match.start(1)]) and not self.isStyleKeyword(style[match.start(2)]):
                    #print repr(code)
                    #print style
                    name = match.group(2).strip()
                    sig = match.group(3).strip()
                    # FIXME: can't seem to tweak the regex to get it to match
                    # for operator() as it leaves out the ().  So here's a
                    # special case.
                    if name.endswith('operator') and sig.startswith("()"):
                        name += '()'
                        
                    self.dprint("matches!!!: return args=%s (index=%d, %d) name=%s (index=%d %d) sig=%s" % (match.group(1).strip(), match.start(1), style[match.start(1)], name, match.start(2), style[match.start(2)], sig))
                    return "%s" % name
                else:
                    self.dprint("%s or %s is a keyword" % (match.group(1).strip(), match.group(2).strip()))
            else:
                self.dprint("regular expression didn't match")
        return ""
