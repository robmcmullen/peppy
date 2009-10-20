#-----------------------------------------------------------------------------
# Name:        diffview.py
# Purpose:     Graphical diff viewer
#
# Author:      Rob McMullen
#
# Created:     2009
# RCS-ID:      $Id: $
# Copyright:   (c) 2009 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
#
# Graphical diff viewer based on the Trac HTML diff representation
#
# The diffing functions are from Trac, licensed under the modified BSD license.
# These functions carry the copyright:
#
# Copyright (C) 2004-2008 Edgewall Software
# Copyright (C) 2004-2006 Christopher Lenz <cmlenz@gmx.de>
# All rights reserved.

"""Diff viewer

"""

import os, re
from difflib import SequenceMatcher

import wx

from peppy.lib.column_autosize import *


def expandtabs(s, tabstop=8, ignoring=None):
    if '\t' not in s: return s
    if ignoring is None: return s.expandtabs(tabstop)

    outlines = []
    for line in s.split('\n'):
        if '\t' not in line:
            outlines.append(line)
            continue
        p = 0
        s = []
        for c in line:
            if c == '\t':
                n = tabstop-p%tabstop
                s.append(' '*n)
                p+=n
            elif not ignoring or c not in ignoring:
                p += 1
                s.append(c)
            else:
                s.append(c)
        outlines.append(''.join(s))
    return '\n'.join(outlines)

def _get_change_extent(str1, str2):
    """
    Determines the extent of differences between two strings. Returns a tuple
    containing the offset at which the changes start, and the negative offset
    at which the changes end. If the two strings have neither a common prefix
    nor a common suffix, (0, 0) is returned.
    """
    start = 0
    limit = min(len(str1), len(str2))
    while start < limit and str1[start] == str2[start]:
        start += 1
    end = -1
    limit = limit - start
    while -end <= limit and str1[end] == str2[end]:
        end -= 1
    return (start, end + 1)

def _get_opcodes(fromlines, tolines, ignore_blank_lines=False,
                 ignore_case=False, ignore_space_changes=False):
    """
    Generator built on top of SequenceMatcher.get_opcodes().
    
    This function detects line changes that should be ignored and emits them
    as tagged as 'equal', possibly joined with the preceding and/or following
    'equal' block.
    """

    def is_ignorable(tag, fromlines, tolines):
        if tag == 'delete' and ignore_blank_lines:
            if ''.join(fromlines) == '':
                return True
        elif tag == 'insert' and ignore_blank_lines:
            if ''.join(tolines) == '':
                return True
        elif tag == 'replace' and (ignore_case or ignore_space_changes):
            if len(fromlines) != len(tolines):
                return False
            def f(str):
                if ignore_case:
                    str = str.lower()
                if ignore_space_changes:
                    str = ' '.join(str.split())
                return str
            for i in range(len(fromlines)):
                if f(fromlines[i]) != f(tolines[i]):
                    return False
            return True

    matcher = SequenceMatcher(None, fromlines, tolines)
    previous = None
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == 'equal':
            if previous:
                previous = (tag, previous[1], i2, previous[3], j2)
            else:
                previous = (tag, i1, i2, j1, j2)
        else:
            if is_ignorable(tag, fromlines[i1:i2], tolines[j1:j2]):
                if previous:
                    previous = 'equal', previous[1], i2, previous[3], j2
                else:
                    previous = 'equal', i1, i2, j1, j2
                continue
            if previous:
                yield previous
            yield tag, i1, i2, j1, j2
            previous = None

    if previous:
        yield previous

def _group_opcodes(opcodes, n=3):
    """
    Python 2.2 doesn't have SequenceMatcher.get_grouped_opcodes(), so let's
    provide equivalent here. The opcodes parameter can be any iterable or
    sequence.

    This function can also be used to generate full-context diffs by passing 
    None for the parameter n.
    """
    # Full context produces all the opcodes
    if n is None:
        yield list(opcodes)
        return

    # Otherwise we leave at most n lines with the tag 'equal' before and after
    # every change
    nn = n + n
    group = []
    for idx, (tag, i1, i2, j1, j2) in enumerate(opcodes):
        if idx == 0 and tag == 'equal': # Fixup leading unchanged block
            i1, j1 = max(i1, i2 - n), max(j1, j2 - n)
        elif tag == 'equal' and i2 - i1 > nn:
            group.append((tag, i1, min(i2, i1 + n), j1, min(j2, j1 + n)))
            yield group
            group = []
            i1, j1 = max(i1, i2 - n), max(j1, j2 - n)
        group.append((tag, i1, i2, j1 ,j2))

    if group and not (len(group) == 1 and group[0][0] == 'equal'):
        if group[-1][0] == 'equal': # Fixup trailing unchanged block
            tag, i1, i2, j1, j2 = group[-1]
            group[-1] = tag, i1, min(i2, i1 + n), j1, min(j2, j1 + n)
        yield group

def diff_blocks(fromlines, tolines, context=None, tabwidth=8,
                ignore_blank_lines=0, ignore_case=0, ignore_space_changes=0):
    """Return an array that is adequate for adding to the data dictionary

    See the diff_div.html template.
    """

    type_map = {'replace': 'mod', 'delete': 'rem', 'insert': 'add',
                'equal': 'unmod'}

    def markup_intraline_changes(opcodes):
        for tag, i1, i2, j1, j2 in opcodes:
            if tag == 'replace' and i2 - i1 == j2 - j1:
                for i in range(i2 - i1):
                    fromline, toline = fromlines[i1 + i], tolines[j1 + i]
                    (start, end) = _get_change_extent(fromline, toline)
                    if start != 0 or end != 0:
                        last = end+len(fromline)
                        fromlines[i1+i] = fromline[:start] + '\0' + fromline[start:last] + \
                                       '\1' + fromline[last:]
                        last = end+len(toline)
                        tolines[j1+i] = toline[:start] + '\0' + toline[start:last] + \
                                     '\1' + toline[last:]
            yield tag, i1, i2, j1, j2

    changes = []
    opcodes = _get_opcodes(fromlines, tolines, ignore_blank_lines, ignore_case,
                           ignore_space_changes)
    for group in _group_opcodes(opcodes, context):
        blocks = []
        last_tag = None
        for tag, i1, i2, j1, j2 in markup_intraline_changes(group):
            if tag != last_tag:
                blocks.append({'type': type_map[tag],
                               'base': {'offset': i1, 'lines': []},
                               'changed': {'offset': j1, 'lines': []}})
            if tag == 'equal':
                for line in fromlines[i1:i2]:
                    line = line.expandtabs(tabwidth)
                    blocks[-1]['base']['lines'].append(unicode(line))
                for line in tolines[j1:j2]:
                    line = line.expandtabs(tabwidth)
                    blocks[-1]['changed']['lines'].append(unicode(line))
            else:
                if tag in ('replace', 'delete'):
                    for line in fromlines[i1:i2]:
                        line = expandtabs(line, tabwidth, '\0\1')
                        line = '<del>'.join(line.split('\0'))
                        line = line.replace('\1', '</del>')
                        blocks[-1]['base']['lines'].append(
                            unicode(line))
                if tag in ('replace', 'insert'):
                    for line in tolines[j1:j2]:
                        line = expandtabs(line, tabwidth, '\0\1')
                        line = '<ins>'.join(line.split('\0'))
                        line = line.replace('\1', '</ins>')
                        blocks[-1]['changed']['lines'].append(
                            unicode(line))
        changes.append(blocks)
    return changes



class DiffCtrl(wx.ListCtrl, ColumnAutoSizeMixin):
    def __init__(self, *args, **kwargs):
        kwargs['style'] = wx.LC_REPORT
        wx.ListCtrl.__init__(self, *args, **kwargs)
        ColumnAutoSizeMixin.__init__(self)
        self.createColumns()
        
        self.added_color = wx.Colour(0xdd, 0xff, 0xdd)
        self.added_highlight_color = wx.Colour(0x99, 0xee, 0x99)
        self.added_border_color = wx.Colour(0x00, 0xaa, 0x00)
        self.removed_color = wx.Colour(0xff, 0xdd, 0xdd)
        self.removed_highlight_color = wx.Colour(0xee, 0x99, 0x99)
        self.removed_border_color = wx.Colour(0xcc, 0x00, 0x00)
        self.show_unmodified = True
        self.context = 2
        
    def createColumns(self):
        self.InsertSizedColumn(0, "Old", min=30)
        self.InsertSizedColumn(1, "New", min=30)
        self.InsertSizedColumn(2, "Diff", ok_offscreen=True)
    
    def showModified(self, group):
        print "type: %s" % group['type']
        print "base: %s" % group['base']
        print "changed: %s" % group['changed']
        print
        self.append(group['base']['offset'], "", group['base']['lines'], self.removed_color)
        self.append("", group['changed']['offset'], group['changed']['lines'], self.added_color)
    
    def showRemoved(self, group):
        print "type: %s" % group['type']
        print "base: %s" % group['base']
        print "changed: %s" % group['changed']
        print
        self.append(group['base']['offset'], "", group['base']['lines'], self.removed_color)
    
    def showAdded(self, group):
        print "type: %s" % group['type']
        print "base: %s" % group['base']
        print "changed: %s" % group['changed']
        print
        self.append("", group['changed']['offset'], group['changed']['lines'], self.added_color)
    
    def showUnmodified(self, group):
        print "type: %s" % group['type']
        print "base: %s" % group['base']
        print "changed: %s" % group['changed']
        print
        left = group['base']['offset']
        right = group['changed']['offset']
        if left > self.last_left + 1:
            self.append("...", "...", [""], show_if_first=False)
        self.append(left, right, group['base']['lines'])
    
    type_map = {
        'mod': showModified,
        'rem': showRemoved,
        'add': showAdded,
        'unmod': showUnmodified,
        }
    
    def load(self, old_lines, new_lines):
        blocks = diff_blocks(old_lines, new_lines, self.context)
        self.last_left = -1
        for block in blocks:
            print block
            for group in block:
                func = self.type_map[group['type']]
                print(func)
                func(self, group)

    def append(self, left, right, lines, color=None, show_if_first=True):
        index = self.GetItemCount()
        if index == 0 and not show_if_first:
            return
        for line in lines:
            self.InsertStringItem(sys.maxint, str(left))
            self.SetStringItem(index, 1, str(right))
            self.SetStringItem(index, 2, line)
            if color:
                self.SetItemBackgroundColour(index, color)
            if isinstance(left, int):
                left += 1
                self.last_left = left
            if isinstance(right, int):
                right += 1
            index += 1
        if isinstance(left, int):
            self.last_left = left


if __name__ == "__main__":
    def get_lines(paragraphs=1):
        lorem_ipsum = u"""\
Lorem ipsum dolor sit amet, consectetuer adipiscing elit.  Vivamus mattis
commodo sem.  Phasellus scelerisque tellus id lorem.  Nulla facilisi.
Suspendisse potenti.  Fusce velit odio, scelerisque vel, consequat nec,
dapibus sit amet, tortor.  Vivamus eu turpis.  Nam eget dolor.  Integer
at elit.  Praesent mauris.  Nullam non nulla at nulla tincidunt malesuada.
Phasellus id ante.  Sed mauris.  Integer volutpat nisi non diam.  Etiam
elementum.  Pellentesque interdum justo eu risus.  Cum sociis natoque
penatibus et magnis dis parturient montes, nascetur ridiculus mus.  Nunc
semper.  In semper enim ut odio.  Nulla varius leo commodo elit.  Quisque
condimentum, nisl eget elementum laoreet, mauris turpis elementum felis, ut
accumsan nisl velit et mi.

And some Russian: \u041f\u0438\u0442\u043e\u043d - \u043b\u0443\u0447\u0448\u0438\u0439 \u044f\u0437\u044b\u043a \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044f!

"""
        text = ""
        for i in range(paragraphs):
            text += lorem_ipsum
        return text.splitlines()
    
    old_lines = get_lines(2)
    new_lines = get_lines(2)
    new_lines[3] = "dapibus SIT amet, tortor.  Vivamus REMOVED.  Nam eget dolor.  Integer ADDED"
    del new_lines[6]
    new_lines[10:10] = ["blah blah"]
    
    new_lines[22] = new_lines[22].replace("a", "A")
    new_lines[23] = new_lines[23].replace(" ", "_")
    
#    blocks = diff_blocks(old_lines, new_lines)
#    for block in blocks:
#        print block
#        for group in block:
#            print "type: %s" % group['type']
#            print "base: %s" % group['base']
#            print "changed: %s" % group['changed']
#            print


    class Frame(wx.Frame):
        def __init__(self, *args, **kwargs):
            super(self.__class__, self).__init__(*args, **kwargs)
            self.diff = DiffCtrl(self, -1)
            self.CreateStatusBar()
            
            self.diff.load(old_lines, new_lines)

    app = wx.App(False)
    frame = Frame(None, size=(600, 700))
    frame.Show()
    app.MainLoop()
