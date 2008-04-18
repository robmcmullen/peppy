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
from peppy.fundamental import *

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
    """
    key_needs_focus = True
    
    @classmethod
    def worksWithMajorMode(cls, mode):
        return hasattr(mode, 'CanUndo')

class TextModificationAction(BufferBusyActionMixin, SelectAction):
    """Base class for any action that changes the bytes in the buffer.

    This uses the BufferBusyActionMixin to disable any action that
    would change the buffer when the buffer is in the process of being
    modified by a long-running process.
    """
    key_needs_focus = True
    
    @classmethod
    def worksWithMajorMode(cls, mode):
        return isinstance(mode, FundamentalMode)

class ScintillaCmdKeyExecute(TextModificationAction):
    """Base class for an action that uses one of the scintilla key commands.
    
    Scintilla has a number of messages that operate on the text but don't have
    direct method calls.  This base class can be used as a simple wrapper
    around one of these scintilla messages.
    
    @see: http://www.yellowbrain.com/stc/keymap.html#exec
    """
    cmd = 0
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
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
        word = s.GetTextRange(pos, end)
        s.SetTargetStart(pos)
        s.SetTargetEnd(end)
        s.ReplaceTarget(self.mutate(word))
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
        word = s.GetTextRange(pos, end)
        s.SetTargetStart(pos)
        s.SetTargetEnd(end)
        s.ReplaceTarget(self.mutate(word))
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
        text = s.GetTextRange(pos, end)
        s.SetTargetStart(pos)
        s.SetTargetEnd(end)
        #dprint("range: %d - %d" % (pos, end))
        lines = text.splitlines(True) # keep line endings on
        #dprint(lines)
        newlines = self.mutateLines(lines)
        #dprint(newlines)
        text = "".join(newlines)
        s.ReplaceTarget(text)
        end = pos + len(text)
        s.updateRegion(pos, end)
        s.GotoPos(end + offset)
        s.SetSelection(pos, end + offset)
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
