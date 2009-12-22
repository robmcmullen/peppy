# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Base classes for actions

These are a collection of useful base classes for creating actions.  They
contain a lot of boilerplate code that handle things like automatically
setting the enable/disable state of the action.

Most of these are designed to be associated with L{FundamentalMode} major modes
(and any modes derived from FundamentalMode).
"""

import wx
import wx.stc

from peppy.actions import *
from peppy.stcbase import *

class BufferBusyActionMixin(object):
    """Mixin to disable an action when the buffer is being modified.

    Buffers can be marked as 'busy' if a long-running action is in process in
    a background thread.  This mixin checks the state of the buffer busy flag
    before allowing it to be enabled in the menu system.
    
    If a subclass needs to supply more information about its enable state,
    override L{isActionAvailable} instead of L{isEnabled}, or else you lose
    the buffer busy test.
    """
    def isEnabled(self):
        return not self.mode.buffer.busy and self.isActionAvailable()

    def isActionAvailable(self):
        """Override this instead of isEnabled when using this mixin
        
        Provides a hook to isEnabled so subclasses can provide more information
        about the enabled state if the buffer is not busy.
        """
        return True

class STCModificationAction(BufferBusyActionMixin, SelectAction):
    """Base class for any action that changes the bytes in the buffer.

    This uses the L{BufferBusyActionMixin} to disable any action that would
    change the buffer when the buffer is in the process of being modified by a
    long-running process.
    
    @skip_translation
    """
    needs_keyboard_focus = True
    
    @classmethod
    def worksWithMajorMode(cls, modecls):
        return hasattr(modecls, 'BeginUndoAction')

class TextModificationAction(BufferBusyActionMixin, SelectAction):
    """Base class for any action that changes the text in the STC.

    This uses the BufferBusyActionMixin to disable any action that
    would change the buffer when the buffer is in the process of being
    modified by a long-running process.
    
    @skip_translation
    """
    needs_keyboard_focus = True
    
    @classmethod
    def worksWithMajorMode(cls, modecls):
        return issubclass(modecls, PeppySTC)
    
    def isModified(self, origtext, newtext):
        """Check to see if any changes have been made in the replacement text
        
        @return: True if changes found, False if not.  If no differences are
        found, the calling method should leave the file unmodified.
        """
        return origtext != newtext

class ScintillaCmdKeyExecute(TextModificationAction):
    """Base class for an action that uses one of the scintilla key commands.
    
    Scintilla has a number of messages that operate on the text but don't have
    direct method calls.  This base class can be used as a simple wrapper
    around one of these scintilla messages.
    
    @see: http://www.yellowbrain.com/stc/keymap.html#exec
    
    @skip_translation
    """
    cmd = 0
    
    @classmethod
    def worksWithMajorMode(cls, modecls):
        return issubclass(modecls, wx.stc.StyledTextCtrl)
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        for i in range(multiplier):
            self.mode.CmdKeyExecute(self.cmd)

class RegionMutateAction(TextModificationAction):
    """Mixin class to operate only on a selected region.
    """

    def isActionAvailable(self):
        """The action is only available if a region is selected."""
        (pos, end) = self.mode.GetSelection()
        return pos != end

    def mutate(self, txt):
        """Operate on specified text and return new text.

        Method designed to be overridden by subclasses to provide the
        text operation desired by the subclass.

        @param txt: input text
        @returns: text resulting from the desired processing
        """
        return txt

    def mutateSelection(self, s):
        """Change the highlighted region.

        Perform some text operation on the region.  If a region is not
        active in the STC, the action will not be performed.

        The operation is performed by the C{mutate} method, which
        subclasses will override to provide the functionality.

        Side effect: moves the cursor to the end of the region.
        
        @param s: styled text control
        """
        (pos, end) = s.GetSelection()
        if pos==end:
            return
        s.BeginUndoAction()
        orig = s.GetTextRange(pos, end)
        s.SetTargetStart(pos)
        s.SetTargetEnd(end)
        newtext = self.mutate(orig)
        if self.isModified(newtext, orig):
            s.ReplaceTarget(newtext)
            s.updateRegion(pos, end)
        s.GotoPos(end)
        s.EndUndoAction()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.mutateSelection(self.mode)
        
class WordOrRegionMutateAction(TextModificationAction):
    """Mixin class to operate on a word or the selected region.
    """

    def mutate(self, txt):
        """Operate on specified text and return new text.

        Method designed to be overridden by subclasses to provide the
        text operation desired by the subclass.

        @param txt: input text
        @returns: text resulting from the desired processing
        """
        return txt

    def mutateSelection(self, s):
        """Change the current word or highlighted region.

        Perform some text operation on the current word or region.  If
        a region is active in the STC, use it; otherwise, use the word
        as defined by the text from the current cursor position to the
        end of the word.  The end of the word is defined by the STC's
        STC_CMD_WORDRIGHT.

        The operation is performed by the C{mutate} method, which
        subclasses will override to provide the functionality.

        Side effect: moves the cursor to the end of the region if it
        operated on the region, or to the start of the next word.
        
        @param s: styled text control
        """
        s.BeginUndoAction()
        (pos, end) = s.GetSelection()
        if pos==end:
            s.CmdKeyExecute(wx.stc.STC_CMD_WORDRIGHT)
            end = s.GetCurrentPos()
        orig = s.GetTextRange(pos, end)
        s.SetTargetStart(pos)
        s.SetTargetEnd(end)
        newtext = self.mutate(orig)
        if self.isModified(orig, newtext):
            s.ReplaceTarget(newtext)
            s.updateRegion(pos, end)
        s.GotoPos(end)
        s.EndUndoAction()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.mutateSelection(self.mode)
        
class LineOrRegionMutateAction(TextModificationAction):
    """Mixin class to operate on a line or the selected region extended
    to include full lines
    """

    def mutateLines(self, lines):
        """Operate on the list of lines and return a new list of lines.

        Method designed to be overridden by subclasses to provide the
        text operation desired by the subclass.

        @param lines: array of lines from the selected region
        @returns: array of lines resulting from the desired processing
        """
        return lines

    def mutateSelection(self, s):
        """Change the current line or highlighted region.

        Perform some text operation on the current line or region.  If
        a region is active in the STC, use it after making sure that it
        is made up of complete lines; otherwise, use the line as defined
        by STC_CMD_HOME and STC_CMD_LINEEND.

        The operation is performed by the C{mutateLines} method, which
        subclasses will override to provide the functionality.

        Side effect: moves the cursor to the end of the region if it
        operated on the region, or to the start of the next line.
        
        @param s: styled text control
        """
        s.BeginUndoAction()
        (pos, end) = s.GetSelection()
        #dprint("original selection: %d - %d" % (pos, end))
        # If end of the selection is on a line by itself, move the end back
        # by one so we don't end up picking up an additional line
        if end > pos and s.GetColumn(end) == 0:
            offset = 1
        else:
            offset = 0
        s.GotoPos(pos)
        s.CmdKeyExecute(wx.stc.STC_CMD_HOME)
        pos = s.GetCurrentPos()
        s.GotoPos(end - offset)
        s.CmdKeyExecute(wx.stc.STC_CMD_LINEEND)
        end = s.GetCurrentPos()
        
        # Check to make sure that we're including the line-end characters from
        # the last line
        line = s.LineFromPosition(end)
        lineend = s.GetLineEndPosition(line)
        if end == lineend:
            end = s.PositionFromLine(line + 1)
            if end < 0:
                end = lineend
        
        text = s.GetTextRange(pos, end)
        s.SetTargetStart(pos)
        s.SetTargetEnd(end)
        #dprint("range: %d - %d, text=-->%s<--" % (pos, end, text))
        lines = text.splitlines(True) # keep line endings on
        #dprint(lines)
        newlines = self.mutateLines(lines)
        if self.isModified(lines, newlines):
            #dprint(newlines)
            text = "".join(newlines)
            s.ReplaceTarget(text)
            end = pos + len(text)
            s.updateRegion(pos, end)
        s.GotoPos(end)
        s.SetSelection(pos, end)
        s.EndUndoAction()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.mutateSelection(self.mode)


class ParagraphOrRegionMutateAction(TextModificationAction):
    """Mixin class to operate on the current paragraph, as defined by the
    current major mode.
    """

    def mutateParagraph(self, info):
        """Operate on the paragraph and return a new list of lines.

        Method designed to be overridden by subclasses to provide the
        text operation desired by the subclass.

        @param info: ParagraphInfo instance representing the currently
        selected paragraph
        @returns: array of lines resulting from the desired processing
        """
        return lines

    def mutateSelection(self, s):
        """Change the current paragraph or highlighted region.

        Perform some text operation on the current line or region.  If
        a region is active in the STC, use it after making sure that it
        is made up of complete lines; otherwise, use the line as defined
        by STC_CMD_HOME and STC_CMD_LINEEND.

        The operation is performed by the C{mutateLines} method, which
        subclasses will override to provide the functionality.

        Side effect: moves the cursor to the end of the region if it
        operated on the region, or to the start of the next line.
        
        @param s: styled text control
        """
        s.BeginUndoAction()
        (pos, end) = s.GetSelection2()
        info = s.findParagraph(pos, end)
        lines = self.mutateParagraph(info)
        s.SetTargetStart(info.start)
        s.SetTargetEnd(info.end)
        text = "\n".join(lines)
        s.ReplaceTarget(text)
        end = info.start + len(text)
        s.updateRegion(info.start, end)
        s.GotoPos(end)
        s.EndUndoAction()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.mutateSelection(self.mode)


class OneLineModificationAction(TextModificationAction):
    """Mixin class to operate a single line.
    
    The line may be selected or it will operate on the line containing the
    cursor
    """

    def isActionAvailable(self):
        """The action is only available if a region is selected."""
        s = self.mode
        (start, end) = s.GetSelection()
        if start == end:
            return True
        start_line = s.LineFromPosition(start)
        end_line = s.LineFromPosition(end)
        if start_line == end_line:
            return True
        elif end_line == start_line + 1 and s.GetColumn(end) == 0:
            return True
        return False

    def mutate(self, txt):
        """Operate on specified text and return new text.

        Method designed to be overridden by subclasses to provide the
        text operation desired by the subclass.

        @param txt: input text
        @returns: text resulting from the desired processing
        """
        return txt
    
    def adjustTarget(self):
        """Adjust the target to encompass more or less text, if necessary
        
        The target will be described by the STC's GetTargetStart and
        GetTargetEnd methods, and will specify a single line.
        """
        return False

    def mutateLine(self, s):
        """Change the highlighted region.

        Perform some text operation on the region.  If a region is not
        active in the STC, the action will not be performed.

        The operation is performed by the C{mutate} method, which
        subclasses will override to provide the functionality.

        Side effect: moves the cursor to the end of the region.
        
        @param s: styled text control
        """
        if not s.GetOneLineTarget():
            return False
        self.adjustTarget()
        pos = s.GetTargetStart()
        end = s.GetTargetEnd()
        orig = s.GetTextRange(pos, end)
        newtext = self.mutate(orig)
        if self.isModified(newtext, orig):
            s.BeginUndoAction()
            count = s.ReplaceTarget(newtext)
            end = pos + count
            s.updateRegion(pos, end)
            s.GotoPos(end)
            s.EndUndoAction()

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.mutateLine(self.mode)
