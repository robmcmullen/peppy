# peppy Copyright (c) 2006-2008 Rob McMullen
# Copyright (c) 2009 Christopher Barker
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Some simple text transformation actions.

This plugin is a collection of some simple text transformation actions that
should be applicable to more than one major mode.
"""

import os, glob

import wx

from peppy.yapsy.plugins import *
from peppy.actions.minibuffer import *
from peppy.lib.wordwrap import texwrap

from peppy.actions.base import *
from peppy.actions import *
from peppy.debug import *


class CommentRegion(TextModificationAction):
    """Comment a line or region.
    
    This will use the current mode's comment characters to comment out
    entire blocks of lines.  The comment will start in column zero, and
    if there is an end comment delimiter, it will appear as the last
    character(s) before the end of line indicatior.
    """
    alias = "comment-region"
    name = "&Comment Region"
    default_menu = ("Transform", -600)
    key_bindings = {'emacs': 'C-c C-c',
                    'mac': 'C-3',
                    }

    def action(self, index=-1, multiplier=1):
        self.mode.commentRegion(multiplier != 4)

class UncommentRegion(TextModificationAction):
    """Uncomment a line or region.
    
    This will use the current mode's comment characters to identify the
    lines in the region that have been commented out, and will remove
    the comment character(s) from the line.
    """
    alias = "uncomment-region"
    name = "&Uncomment Region"
    default_menu = ("Transform", 601)
    key_bindings = {'emacs': 'C-u C-c C-c',
                    'mac': 'M-3',
                    }

    def action(self, index=-1, multiplier=1):
        self.mode.commentRegion(False)

class Tabify(LineOrRegionMutateAction):
    """Replace spaces with tabs at the start of lines."""
    alias = "tabify"
    name = "&Tabify"
    default_menu = (("Transform/Whitespace", -800), 100)

    def mutateLines(self, lines):
        out = []
        for line in lines:
            unspace = line.lstrip(' ')
            if len(unspace) < len(line):
                tabs, extraspaces = divmod(len(line) - len(unspace),
                                           self.mode.locals.tab_size)
                out.append((tabs)*'\t' + extraspaces*' ' + unspace)
            else:
                out.append(line)
        return out

class Untabify(LineOrRegionMutateAction):
    """Replace tabs with spaces at the start of lines."""
    alias = "untabify"
    name = "&Untabify"
    default_menu = ("Transform/Whitespace", 110)

    def mutateLines(self, lines):
        out = []
        for line in lines:
            untab = line.lstrip('\t')
            if len(untab) < len(line):
                out.append((len(line) - len(untab))*self.mode.locals.tab_size*' ' + untab)
            else:
                out.append(line)
        return out

class RemoveTrailingWhitespace(LineOrRegionMutateAction):
    """Remove all trailing whitespace
    
    Operates on the current line, or lines that make up the currently selected
    region.
    """
    alias = "remove-trailing-whitespace"
    name = "Remove Trailing Whitespace"
    default_menu = ("Transform/Whitespace", 200)

    def mutateLines(self, lines):
        regex = re.compile('(.*?)([\t ]+)([\r\n]+)?$')
        out = []
        for line in lines:
            match = regex.match(line)
            if match:
                # Remove everything but the line ending (if it exists)
                out.append(match.group(1) + line[match.end(2):])
            else:
                out.append(line)
        return out


class CapitalizeWord(WordOrRegionMutateAction):
    """Title-case the current word or words in the highlighted region.
    
    This will also move the cursor to the start of the next word.
    """
    alias = "capitalize-region-or-word"
    name = "Capitalize"
    key_bindings = {'emacs': 'M-c',}
    default_menu = (("Transform/Case", 810), 100)

    def mutate(self, txt):
        """Change to title case -- first letter capitalized, rest
        lower case.
        """
        return txt.title()

class UpcaseWord(WordOrRegionMutateAction):
    """Upcase the current word or the highlighted region.
    
    This will alse move the cursor to the start of the next word.
    """
    alias = "upcase-region-or-word"
    name = "Upcase"
    key_bindings = {'emacs': 'M-u',}
    default_menu = ("Transform/Case", 101)
    icon = "icons/text_uppercase.png"
    default_toolbar = False

    def mutate(self, txt):
        """Change to all upper case.
        """
        return txt.upper()

class DowncaseWord(WordOrRegionMutateAction):
    """Downcase the current word or the highlighted region.
    
    This will also move the cursor to the start of the next word.
    """
    alias = "downcase-region-or-word"
    name = "Downcase"
    key_bindings = {'emacs': 'M-l',}
    default_menu = ("Transform/Case", 102)
    icon = "icons/text_lowercase.png"
    default_toolbar = False

    def mutate(self, txt):
        """Change to all lower case.
        """
        return txt.lower()

class SwapcaseWord(WordOrRegionMutateAction):
    """Swap the case of the current word or the highlighted region.
    
    This will also move the cursor to the start of the next word.
    """
    alias = "swapcase-region-or-word"
    name = "Swap case"
    default_menu = ("Transform/Case", 103)
    default_toolbar = False

    def mutate(self, txt):
        """Change to the opposite case (upper to lower and vice-versa).
        """
        return txt.swapcase()

class Rot13(RegionMutateAction):
    """Convert the region using the rot13 encoding."""
    alias = "rot13-region"
    name = "Rot13"
    default_menu = ("Transform", -900)

    def mutate(self, txt):
        """Change to all lower case.
        """
        return txt.encode('rot13')


class Backslashify(LineOrRegionMutateAction):
    """Escape the end of line character by adding backslashes.
    
    Add backslashes to the end of every line (except the last one) in the
    region so that the end-of-line character is escaped.  This is useful, for
    instance, within C or C++ C{#define} blocks that contain multiple line
    macros.
    """
    alias = "backslashify"
    name = "Backslashify"
    default_menu = ("Transform", 910)

    def isActionAvailable(self):
        """The action is only available if a region has multiple lines."""
        (pos, end) = self.mode.GetSelection()
        return self.mode.LineFromPosition(pos) < self.mode.LineFromPosition(end) - 1

    def mutateLines(self, lines):
        """Add backslashes to the end of all lines but the last
        """
        out = []
        eol = " \\" + self.mode.getLinesep()
        for line in lines[:-1]:
            out.append(line.rstrip() + eol)
        out.append(lines[-1])
        return out


class UnBackslashify(LineOrRegionMutateAction):
    """Remove backslashes from end of line.
    
    Remove backslashes from the end of every line in the region so that the
    end- of-line character is not escaped anymore.  This is the opposite of
    L{Backslashify}.
    """
    alias = "remove-backslashes"
    name = "Remove Backslashes"
    default_menu = ("Transform", 911)

    def isActionAvailable(self):
        """The action is only available if a region has multiple lines."""
        (pos, end) = self.mode.GetSelection()
        return self.mode.LineFromPosition(pos) < self.mode.LineFromPosition(end) - 1

    def mutateLines(self, lines):
        """Add backslashes to the end of all lines but the last
        """
        out = []
        regex = re.compile(r"(.*?)\s*\\(\s)*$")
        eol = self.mode.getLinesep()
        for line in lines:
            match = regex.match(line)
            if match:
                #dprint(repr(line))
                line = match.group(1)
                if match.group(2):
                    line += match.group(2)
            out.append(line)
        return out


class Reindent(TextModificationAction):
    """Reindent a line or region.
    
    Recalculates the indentation for the selected region, using the current
    major mode's algorithm for indentation.
    """
    alias = "reindent-region"
    name = "Reindent"
    default_menu = ("Transform", 602)
    key_bindings = {'default': 'TAB',}
    key_needs_focus = True

    def action(self, index=-1, multiplier=1):
        s = self.mode
        start, end = s.GetSelection2()
        if start == end:
            s.autoindent.processTab(s)
        else:
            line = s.LineFromPosition(start)
            end = s.LineFromPosition(end)
            s.autoindent.debuglevel = True
            s.BeginUndoAction()
            while line <= end:
                pos = s.autoindent.reindentLine(s, linenum=line)
                line += 1
            s.SetSelection(start, pos)
            s.GetLineRegion()
            s.EndUndoAction()

def RemoveExtraSpace(text, pos):
    """Remove any amount of whitespace at pos, replacing it with a single space.
    
    If pos is at the end or beginning of the line, then remove the whitesapce
    there, rather than leaving a single space.
    
    It is assumed that there is no newline on the end.
    
    returns new_text, new_pos
    """
    # move back in from the end if we are over the end
    if pos >= len(text):
        pos = len(text)-1
        new_pos = len(text)
    else:
        new_pos = pos

    if text[pos].isspace() or text[pos-1].isspace(): # don't do anything if there is not whitespace here.
        left = text[:pos].rstrip()
        right  = text[pos:].lstrip()
        if left and right:
            text = " ".join( (left, right) )
        else:
            text = left or right
        new_pos = len(left)
    return text, new_pos
       

class JustOneSpace(TextModificationAction):
    """Remove extra whitespace

    Replaces any amount of whitespace surrounding the cursor with one space
    except at the begining and ends of lines, where it removes all white space.
    """
    alias = "just-one-space"
    name = "Just One Space"
    default_menu = ("Transform", 602)
    key_bindings = {'default': 'M-SPACE',}
    key_needs_focus = True

    def action(self, index=-1, multiplier=1):
        s = self.mode
        cursor = s.GetCurrentPos()
        line = s.LineFromPosition(cursor)
        start = s.PositionFromLine(line)
        end = s.GetLineEndPosition(line)
        if end > start: # no point in doing anything for a zero-length line
            text = s.GetTextRange(start,end)
            pos = cursor - start
            
            # text is unicode but pos is the cursor position within the line
            # as the utf-8 byte offset, so we need to convert to unicode
            # character index.
            utf_before_cursor = text.encode('utf-8')[:pos]
            unicode_before_cursor = utf_before_cursor.decode('utf-8')
            pos = len(unicode_before_cursor)
            
            new_line, new_pos = RemoveExtraSpace(text, pos)
            
            # new_line is unicode, and new_pos is the unicode character index.
            # Need to convert pos to utf-8 offset for cursor position.
            new_pos = len(new_line[:new_pos].encode('utf-8'))
            
            s.BeginUndoAction()
            s.SetTargetStart(start)
            s.SetTargetEnd(end)
            s.ReplaceTarget(new_line)
            s.SetAnchor(start + new_pos)
            s.SetCurrentPos(start + new_pos)
            s.EndUndoAction()


class FillParagraphOrRegion(ParagraphOrRegionMutateAction):
    """Word-wrap the current paragraph or region.
    
    Reformats the current paragraph or selection by breaking long lines at word
    boundaries.  The lines are at most C{edge_column} characters long, where
    edge_column is defined in the Preferences for the major mode.
    """
    alias = "fill-paragraph-or-region"
    name = "Fill Paragraph"
    default_menu = ("Transform", 603)
    key_bindings = {'default': 'M-q',}

    def mutateParagraph(self, info):
        """Word wrap the current paragraph using the TeX algorithm."""
        prefix = info.leader_pattern
        if len(prefix.rstrip()) == len(prefix) and len(prefix) > 0:
            # no space at the end of the prefix!  Add one
            prefix += " "
        column = self.mode.classprefs.edge_column - len(prefix) - 1
        self.dprint(info.getLines())
        lines = texwrap(info.getLines(), column)
        self.dprint(lines)
        info.replaceLines(lines)
        info.addPrefix(prefix)
        return info.getLines()


class JoinLines(LineOrRegionMutateAction):
    """Join selected lines into a single line separated by spaces."""
    alias = "join-lines"
    name = "Join Lines"
    default_menu = ("Transform", 610)
    key_bindings = {'default': 'M-j',}

    def mutateLines(self, lines):
        if len(lines) <= 1:
            return lines
        out = [lines[0].rstrip()]
        for line in lines[1:]:
            out.append(line.strip())
        line = " ".join(out) + self.mode.getLinesep()
        return [line]


class SortLines(LineOrRegionMutateAction):
    """Sort lines using a simple string comparison sort
    
    The selected lines are reordered lexicographically starting from the first
    character of each line.  Note that whitespace is also considered in the
    sort, so a line starting with " A quick brown fox" will be sorted before
    "A quick brown fox".
    """
    alias = "sort-lines"
    name = "Sort Lines"
    default_menu = (("Transform/Reorder", 820), 100)

    def isActionAvailable(self):
        """The action is makes sense if a region has multiple lines."""
        (pos, end) = self.mode.GetSelection()
        return self.mode.LineFromPosition(pos) < self.mode.LineFromPosition(end) - 1

    def mutateLines(self, lines):
        """Sort the lines using the default string comparison sort
        """
        out = [line for line in lines]
        out.sort()
        return out


class SortLinesByField(MinibufferAction, LineOrRegionMutateAction):
    """Sort lines based on a particular field in the line
    
    The region will be extended to include complete lines if the beginning or
    the end of the region starts in the middle of a line.
    
    Currently, non-printable delimiter characters (e.g.  the tab character) can
    be entered only by pasting into the desired text field.  This is a bug and
    will be fixed in future versions to use the InsertQuotedChar action.
    
    This action subclasses from both L{MinibufferAction} and
    L{LineOrRegionMutateAction}, but because MinibufferAction occurs first in
    the method resolution order, its action method is the one that's used by
    the menu system (the MinibufferAction.action method is hidden).
    """
    alias = "sort-lines-by-field"
    name = "Sort Lines by Field"
    default_menu = ("Transform/Reorder", 110)

    minibuffer = [TextMinibuffer, IntMinibuffer]
    minibuffer_label = ["Text Delimiter", "Sort Field (fields numbered starting from 1)"]
    
    def isActionAvailable(self):
        """The action is makes sense if a region has multiple lines."""
        (pos, end) = self.mode.GetSelection()
        return self.mode.LineFromPosition(pos) < self.mode.LineFromPosition(end) - 1

    def mutateLines(self, lines):
        """Sort the lines by field
        """
        # Create a decorated list that will be sorted so that the new order can
        # be applied to the original list
        order = []
        count = 0
        for line in lines:
            fields = line.split(self.delimiter)
            if self.field < len(fields):
                order.append((fields[self.field].strip(), count))
            else:
                order.append(('', count))
            count += 1
        #dprint(order)
        order.sort()
        out = [lines[index] for text, index in order]
        #dprint(out)
        return out

    def processMinibuffer(self, minibuffer, mode, values):
        dprint(values)
        self.delimiter = values[0]
        self.field = values[1] - 1
        if self.field < 0:
            self.mode.setStatusText("Invalid field number.")
        else:
            # This uses the LineOrRegionMutateAction method to call mutateLines
            # with the correct lines
            self.mutateSelection(self.mode)
        

class ReverseLines(LineOrRegionMutateAction):
    """Reverse the order of lines in the current selection
    
    The region will be extended to include complete lines if the beginning or
    the end of the region starts in the middle of a line.
    """
    alias = "reverse-lines"
    name = "Reverse Lines"
    default_menu = ("Transform/Reorder", -200)

    def isActionAvailable(self):
        """The action is makes sense if a region has multiple lines."""
        (pos, end) = self.mode.GetSelection()
        return self.mode.LineFromPosition(pos) < self.mode.LineFromPosition(end) - 1

    def mutateLines(self, lines):
        """Sort the lines using the default string comparison sort
        """
        out = [line for line in lines]
        out.reverse()
        return out


class ShuffleLines(LineOrRegionMutateAction):
    """Shuffle the selected lines randomly
    
    The region will be extended to include complete lines if the beginning or
    the end of the region starts in the middle of a line.
    """
    alias = "shuffle-lines"
    name = "Shuffle Lines"
    default_menu = ("Transform/Reorder", 210)

    def isActionAvailable(self):
        """The action is makes sense if a region has multiple lines."""
        (pos, end) = self.mode.GetSelection()
        return self.mode.LineFromPosition(pos) < self.mode.LineFromPosition(end) - 1

    def mutateLines(self, lines):
        """Sort the lines using the default string comparison sort
        """
        import random
        
        out = [line for line in lines]
        random.shuffle(out)
        return out


class TransposeChars(TextModificationAction):
    """Interchange the characters around the cursor

    Emacs compatibility command, transposing the two characters around the
    cursor and moving the cursor forward one character.
    
    This is a reverse-engineering of the Emacs function 'transpose-chars'
    with all of its quirks.  At the beginning of a line, it swaps the last
    character on the previous line but doesn't advance the cursor.  At the end
    of a line, it swaps the last two characters and also doesn't advance the
    cursor.  Otherwise, it swaps the characters on either side of the cursor
    and advances the cursor one position.
    """
    alias = "transpose-chars"
    name = "Transpose Characters"
    default_menu = ("Transform/Reorder", -300)
    key_bindings = {'emacs': 'C-t',}
    key_needs_focus = True

    def action(self, index=-1, multiplier=1):
        s = self.mode
        cursor = s.GetCurrentPos()
        linenum = s.LineFromPosition(cursor)
        line_start = s.PositionFromLine(linenum)
        line_end = s.GetLineEndPosition(linenum)
        eol = ''
        originally_at_end = False
        if cursor == line_end and cursor > line_start:
            cursor = s.PositionBefore(cursor)
            originally_at_end = True
        if cursor == line_start:
            # cursor at start of line: move character to end of previous line
            if linenum == 0:
                return
            prev_linenum = linenum - 1
            prev_line_start = s.PositionFromLine(prev_linenum)
            prev_line_end = s.GetLineEndPosition(prev_linenum)
            if line_start == line_end:
                # if the current line is empty, swap with end of previous line
                start1 = s.PositionBefore(prev_line_end)
            else:
                # otherwise, swap with empty string
                start1 = prev_line_end
            end1 = prev_line_end
            eol = s.getLinesep()
        else:
            start1 = s.PositionBefore(cursor)
            end1 = cursor
        
        if cursor == line_start:
            # At the beginning of a line, nothing is swapped into the current
            # line
            start2 = line_start
            end2 = line_start
        if cursor < line_end:
            # normal conditions means the character after the cursor is swapped
            start2 = cursor
            end2 = s.PositionAfter(cursor)
        else:
            # at the end of line, we don't advance to the next line and swap
            # the final two characters.
            start2 = line_end
            end2 = line_end
        
        char1 = s.GetTextRange(start1, end1)
        char2 = s.GetTextRange(start2, end2)
        replacement = char2 + eol + char1
        s.BeginUndoAction()
        s.SetTargetStart(start1)
        s.SetTargetEnd(end2)
        s.ReplaceTarget(replacement)
        s.SetAnchor(end2)
        s.SetCurrentPos(end2)
        s.EndUndoAction()


class TransposeLineDown(TextModificationAction):
    """Transpose line with line below, moving cursor down

    Emacs compatibility command, transposing the current line with the one
    below it, moving the cursor down one line as a side effect.
    """
    alias = "transpose-line-down"
    name = "Transpose Line Down"
    default_menu = ("Transform/Reorder", 301)
    key_bindings = {'emacs': 'C-S-t',}
    key_needs_focus = True

    def action(self, index=-1, multiplier=1):
        s = self.mode
        cursor = s.GetCurrentPos()
        linenum = s.LineFromPosition(cursor)
        if linenum < s.GetLineCount() - 1:
            start1 = s.PositionFromLine(linenum)
            end1 = s.GetLineEndPosition(linenum)
            current_line = s.GetTextRange(start1, end1)
            
            linenum += 1
            start2 = s.PositionFromLine(linenum)
            end2 = s.GetLineEndPosition(linenum)
            next_line = s.GetTextRange(start2, end2)
            
            replacement = next_line + s.getLinesep() + current_line
            s.BeginUndoAction()
            s.SetTargetStart(start1)
            s.SetTargetEnd(end2)
            s.ReplaceTarget(replacement)
            new_cursor = s.PositionFromLine(linenum)
            s.SetAnchor(new_cursor)
            s.SetCurrentPos(new_cursor)
            s.EndUndoAction()


class TextTransformPlugin(IPeppyPlugin):
    """Plugin containing of a bunch of text transformation actions.
    """
    def getActions(self):
        return [CapitalizeWord, UpcaseWord, DowncaseWord, SwapcaseWord,

                Reindent, CommentRegion, UncommentRegion,
                FillParagraphOrRegion, Backslashify, UnBackslashify,

                Tabify, Untabify, RemoveTrailingWhitespace, JoinLines,
                
                Rot13,
                
                SortLines, SortLinesByField, ReverseLines, ShuffleLines,
                TransposeChars, TransposeLineDown,
                
                JustOneSpace,
                ]
