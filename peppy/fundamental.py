# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
import os, shutil

import wx
import wx.stc
from wx.lib.pubsub import Publisher

from peppy.mainmenu import Paste
from peppy.menu import *

from peppy.lib.processmanager import *

from peppy.actions.minibuffer import *
from peppy.actions.gotoline import *
from peppy.actions.pypefind import *
import peppy.boa as boa


class OpenFundamental(SelectAction):
    name = _("&Open Sample Text")
    tooltip = _("Open some sample text")
    icon = wx.ART_FILE_OPEN

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.frame.open("about:demo.txt")

class WordWrap(ToggleAction):
    alias = _("word-wrap")
    name = _("&Word Wrap")
    tooltip = _("Toggle word wrap in this view")
    icon = wx.ART_TOOLBAR

    def isChecked(self):
        return self.mode.classprefs.word_wrap
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s" % (id(self),self.name))
        self.mode.setWordWrap(not self.mode.classprefs.word_wrap)
    
class LineNumbers(ToggleAction):
    alias = _("line-numbers")
    name = _("&Line Numbers")
    tooltip = _("Toggle line numbers in this view")
    icon = wx.ART_TOOLBAR

    def isChecked(self):
        return self.mode.classprefs.line_numbers
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s" % (id(self),self.name))
        self.mode.setLineNumbers(not self.mode.classprefs.line_numbers)

class Folding(ToggleAction):
    alias = _("code-folding")
    name = _("&Folding")
    tooltip = _("Toggle folding in this view")
    icon = wx.ART_TOOLBAR

    def isChecked(self):
        return self.mode.classprefs.folding
    
    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s" % (id(self),self.name))
        self.mode.setFolding(not self.mode.classprefs.folding)

class BeginningOfBuffer(SelectAction):
    alias = _("beginning-of-buffer")
    name = _("Cursor to first character in the buffer")
    tooltip = _("Move the cursor to the start of the buffer")
        
    def action(self, index=-1, multiplier=1):
        self.mode.stc.DocumentStart()

class EndOfBuffer(SelectAction):
    alias = _("end-of-buffer")
    name = _("Cursor to end of the buffer")
    tooltip = _("Move the cursor to the end of the buffer")
        
    def action(self, index=-1, multiplier=1):
        self.mode.stc.DocumentEnd()

class ScintillaCmdKeyExecute(BufferModificationAction):
    cmd = 0

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.mode.stc.CmdKeyExecute(self.cmd)

class BeginningOfLine(ScintillaCmdKeyExecute):
    alias = _("beginning-of-line")
    name = _("Cursor to Start of Line")
    tooltip = _("Move the cursor to the start of the current line")
    cmd = wx.stc.STC_CMD_HOMEDISPLAY
        
class BeginningTextOfLine(ScintillaCmdKeyExecute):
    alias = _("beginning-text-of-line")
    name = _("Cursor to first non-blank character in the line")
    tooltip = _("Move the cursor to the start of the current line")
    key_bindings = {'emacs': 'C-A',}
    cmd = wx.stc.STC_CMD_VCHOME
        
class EndOfLine(ScintillaCmdKeyExecute):
    alias = _("end-of-line")
    name = _("Cursor to End of Line")
    tooltip = _("Move the cursor to the end of the current line")
    key_bindings = {'emacs': 'C-E',}
    cmd = wx.stc.STC_CMD_LINEEND

class PreviousLine(ScintillaCmdKeyExecute):
    alias = _("previous-line")
    name = _("Cursor to previous line")
    tooltip = _("Move the cursor up a line")
    key_bindings = {'emacs': 'C-P',}
    cmd = wx.stc.STC_CMD_LINEUP

class NextLine(ScintillaCmdKeyExecute):
    alias = _("next-line")
    name = _("Cursor to next line")
    tooltip = _("Move the cursor down a line")
    key_bindings = {'emacs': 'C-N',}
    cmd = wx.stc.STC_CMD_LINEDOWN


class WordOrRegionMutateMixin(object):
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
        s.EndUndoAction()
        s.GotoPos(end)

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        self.mutateSelection(self.mode.stc)
            
class CapitalizeWord(WordOrRegionMutateMixin, BufferModificationAction):
    """Title-case the current word and move the cursor to the start of
    the next word.
    """
    alias = _("capitalize-region-or-word")
    name = _("Capitalize word")
    tooltip = _("Capitalize current word")
    key_bindings = {'emacs': 'M-C',}

    def mutate(self, txt):
        """Change to title case -- first letter capitalized, rest
        lower case.
        """
        return txt.title()

class UpcaseWord(WordOrRegionMutateMixin, BufferModificationAction):
    """Upcase the current word and move the cursor to the start of the
    next word.
    """
    alias = _("upcase-region-or-word")
    name = _("Upcase word")
    tooltip = _("Upcase current word")
    key_bindings = {'emacs': 'M-U',}

    def mutate(self, txt):
        """Change to all upper case.
        """
        return txt.upper()

class DowncaseWord(WordOrRegionMutateMixin, BufferModificationAction):
    """Downcase the current word and move the cursor to the start of the
    next word.
    """
    alias = _("downcase-region-or-word")
    name = _("Downcase word")
    tooltip = _("Downcase current word")
    key_bindings = {'emacs': 'M-L',}

    def mutate(self, txt):
        """Change to all lower case.
        """
        return txt.lower()


class BraceHighlightMixin(object):
    """Brace highlighting mixin for code modes.

    Highlight matching braces or flag mismatched braces.  This is
    called during the EVT_STC_UPDATEUI event handler.

    Code taken from StyledTextCtrl_2 from the wxPython demo.  Should
    probably implement this as a dynamic method of the text control or
    the Major Mode, controllable by a setting.
    """
    def braceHighlight(self):
        s = self.stc

        # check for matching braces
        braceAtCaret = -1
        braceOpposite = -1
        charBefore = None
        caretPos = s.GetCurrentPos()

        if caretPos > 0:
            charBefore = s.GetCharAt(caretPos - 1)
            styleBefore = s.GetStyleAt(caretPos - 1)

        # check before
        if charBefore and chr(charBefore) in "[]{}()" and styleBefore == wx.stc.STC_P_OPERATOR:
            braceAtCaret = caretPos - 1

        # check after
        if braceAtCaret < 0:
            charAfter = s.GetCharAt(caretPos)
            styleAfter = s.GetStyleAt(caretPos)

            if charAfter and chr(charAfter) in "[]{}()" and styleAfter == wx.stc.STC_P_OPERATOR:
                braceAtCaret = caretPos

        if braceAtCaret >= 0:
            braceOpposite = s.BraceMatch(braceAtCaret)

        if braceAtCaret != -1  and braceOpposite == -1:
            s.BraceBadLight(braceAtCaret)
        else:
            s.BraceHighlight(braceAtCaret, braceOpposite)
        


class ShiftLeft(ScintillaCmdKeyExecute):
    alias = _("unindent-region")
    name = _("Shift &Left")
    tooltip = _("Unindent a line region")
    icon = 'icons/text_indent_remove_rob.png'
    cmd = wx.stc.STC_CMD_BACKTAB

class ShiftRight(ScintillaCmdKeyExecute):
    alias = _("indent-region")
    name = _("Shift &Right")
    tooltip = _("Indent a line or region")
    icon = 'icons/text_indent_rob.png'
    cmd = wx.stc.STC_CMD_TAB


class StandardCommentMixin(debugmixin):
    def comment(self, add=True):
        """Comment or uncomment a region.

        Comment or uncomment a region.

        @param add: True to add comments, False to remove them
        """
        s = self.stc
        eol_len = len(s.getLinesep())
        if add:
            func = s.addLinePrefixAndSuffix
        else:
            func = s.removeLinePrefixAndSuffix
        
        s.BeginUndoAction()
        line, lineend = s.GetLineRegion()
        assert self.dprint("lines: %d - %d" % (line, lineend))
        try:
            selstart, selend = s.GetSelection()
            assert self.dprint("selection: %d - %d" % (selstart, selend))

            start = selstart
            end = s.GetLineEndPosition(line)
            while line <= lineend:
                start = func(start, end, self.start_line_comment, self.end_line_comment)
                line += 1
                end = s.GetLineEndPosition(line)
            s.SetSelection(selstart, start - eol_len)
        finally:
            s.EndUndoAction()

class CommentRegion(BufferModificationAction):
    alias = _("comment-region")
    name = _("&Comment Region")
    tooltip = _("Comment a line or region")
    icon = 'icons/text_indent_rob.png'
    key_bindings = {'emacs': 'C-C C-C',}

    def action(self, index=-1, multiplier=1):
        dprint(multiplier)
        if hasattr(self.mode, 'comment') and self.mode.comment is not None:
            self.mode.comment(multiplier != 4)

class UncommentRegion(BufferModificationAction):
    alias = _("uncomment-region")
    name = _("&Uncomment Region")
    tooltip = _("Uncomment a line or region")
    icon = 'icons/text_indent_rob.png'

    def action(self, index=-1, multiplier=1):
        if hasattr(self.mode, 'comment') and self.mode.comment is not None:
            self.mode.comment(False)


class StandardReturnMixin(debugmixin):
    def findIndent(self, linenum):
        """Find proper indention of next line given a line number.

        This is designed to be overridden in subclasses.  Given the
        current line, figure out what the indention should be for the
        next line.
        """
        return self.stc.GetLineIndentation(linenum)
        
    def electricReturn(self):
        """Add a newline and indent to the proper tab level.

        Indent to the level of the line above.
        """
        s = self.stc
        linesep = s.getLinesep()

        # reindent current line (if necessary), then process the return
        pos = self.reindent()
        
        linenum = s.GetCurrentLine()
        #pos = s.GetCurrentPos()
        col = s.GetColumn(pos)
        linestart = s.PositionFromLine(linenum)
        line = s.GetLine(linenum)[:pos-linestart]
    
        #get info about the current line's indentation
        ind = s.GetLineIndentation(linenum)

        dprint("format = %s col=%d ind = %d" % (repr(linesep), col, ind)) 

        s.SetTargetStart(pos)
        s.SetTargetEnd(pos)
        if col <= ind:
            newline = linesep+s.GetIndentString(col)
        elif not pos:
            newline = linesep
        else:
            ind = self.findIndent(linenum)
            newline = linesep+s.GetIndentString(ind)
        s.ReplaceTarget(newline)
        s.GotoPos(pos + len(newline))

class ElectricReturn(BufferModificationAction):
    alias = _("electric-return")
    name = _("Electric Return")
    tooltip = _("Indent the next line following a return")
    icon = 'icons/text_indent_rob.png'
    key_bindings = {'default': 'RET',}

    def action(self, index=-1, multiplier=1):
        self.mode.electricReturn()


class ReindentBase(debugmixin):
    def reindent(self, linenum=None):
        """Reindent the specified line to the correct level.

        Given a line, indent to the previous line
        """
        s = self.stc
        if linenum is None:
            linenum = s.GetCurrentLine()
        if linenum == 0:
            # first line is always indented correctly
            return s.GetCurrentPos()
        
        linestart = s.PositionFromLine(linenum)

        # actual indention of current line
        indcol = s.GetLineIndentation(linenum) # columns
        pos = s.GetCurrentPos()
        indpos = s.GetLineIndentPosition(linenum) # absolute character position
        col = s.GetColumn(pos)
        dprint("linestart=%d pos=%d indpos=%d col=%d indcol=%d" % (linestart, pos, indpos, col, indcol))

        indstr = self.getReindentString(linenum, linestart, pos, indpos, col, indcol)
        if indstr is None:
            return pos
        
        # the target to be replaced is the leading indention of the
        # current line
        s.SetTargetStart(linestart)
        s.SetTargetEnd(indpos)
        s.ReplaceTarget(indstr)

        # recalculate cursor position, because it may have moved if it
        # was within the target
        after = s.GetLineIndentPosition(linenum)
        dprint("after: indent=%d cursor=%d" % (after, s.GetCurrentPos()))
        if pos < linestart:
            return pos
        newpos = pos - indpos + after
        if newpos < linestart:
            # we were in the indent region, but the region was made smaller
            return after
        elif pos < indpos:
            # in the indent region
            return after
        return newpos

    def getReindentString(self, linenum, linestart, pos, indpos, col, indcol):
        return None


class StandardReindentMixin(ReindentBase):
    def getReindentString(self, linenum, linestart, pos, indpos, col, indcol):
        s = self.stc
        
        # look at indention of previous line
        prevind, prevline = s.GetPrevLineIndentation(linenum)
        if (prevind < indcol and prevline < linenum-1) or prevline < linenum-2:
            # if there's blank lines before this and the previous
            # non-blank line is indented less than this one, ignore
            # it.  Make the user manually unindent lines.
            return None

        # previous line is not blank, so indent line to previous
        # line's level
        return s.GetIndentString(prevind)


class FoldingReindentMixin(debugmixin):
    def reindent(self, linenum=None):
        """Reindent the specified line to the correct level.

        Given a line, use Scintilla's built-in folding to determine
        the indention level of the current line.
        """
        s = self.stc
        if linenum is None:
            linenum = s.GetCurrentLine()
        linestart = s.PositionFromLine(linenum)

        # actual indention of current line
        ind = s.GetLineIndentation(linenum) # columns
        pos = s.GetLineIndentPosition(linenum) # absolute character position

        # folding says this should be the current indention
        fold = s.GetFoldLevel(linenum)&wx.stc.STC_FOLDLEVELNUMBERMASK - wx.stc.STC_FOLDLEVELBASE
        dprint("ind = %s (char num=%d), fold = %s" % (ind, pos, fold))
        s.SetTargetStart(linestart)
        s.SetTargetEnd(pos)
        s.ReplaceTarget(s.GetIndentString(fold))


class Reindent(BufferModificationAction):
    alias = _("reindent-region")
    name = _("Reindent")
    tooltip = _("Reindent a line or region")
    icon = 'icons/text_indent_rob.png'
    key_bindings = {'default': 'C-TAB',}

    def action(self, index=-1, multiplier=1):
        s = self.mode.stc

        # save cursor information so the cursor can be maintained at
        # the same relative location in the text after the indention
        pos = self.mode.reindent()
        s.GotoPos(pos)


class PasteAtColumn(Paste):
    alias = _("paste-at-column")
    name = _("Paste at Column")
    tooltip = _("Paste selection indented to the cursor's column")
    icon = "icons/paste_plain.png"

    def action(self, index=-1, multiplier=1):
        self.mode.stc.PasteAtColumn()


class EOLModeSelect(BufferBusyActionMixin, RadioAction):
    name="Line Endings"
    inline=False
    tooltip="Switch line endings"

    items = ['Unix (LF)', 'DOS/Windows (CRLF)', 'Old-style Apple (CR)']
    modes = [wx.stc.STC_EOL_LF, wx.stc.STC_EOL_CRLF, wx.stc.STC_EOL_CR]

    def saveIndex(self,index):
        assert self.dprint("index=%d" % index)

    def getIndex(self):
        eol = self.mode.stc.GetEOLMode()
        return EOLModeSelect.modes.index(eol)
                                           
    def getItems(self):
        return EOLModeSelect.items

    def action(self, index=-1, multiplier=1):
        self.mode.stc.ConvertEOLs(EOLModeSelect.modes[index])
        Publisher().sendMessage('resetStatusBar')


class FundamentalMode(BraceHighlightMixin,
                      StandardCommentMixin, StandardReturnMixin,
                      StandardReindentMixin, MajorMode):
    """
    The base view of most (if not all) of the views that use the STC
    to directly edit the text.  Views (like the HexEdit view or an
    image viewer) that only use the STC as the backend storage are
    probably not based on this view.
    """
    keyword = 'Fundamental'

    start_line_comment = ''
    end_line_comment = ''

    default_classprefs = (
        BoolParam('use_tab_characters', False,
                  'True: insert tab characters when tab is pressed\nFalse: insert the equivalent number of spaces instead.'),
        IntParam('tab_size', 4, 'Number of spaces in each tab'),
        ChoiceParam('tab_highlight_style',
                         ['ignore', 'inconsistent', 'mixed', 'spaces are bad', 'tabs are bad'],
                         'mixed', 'Highlight bad intentation'),
        BoolParam('line_numbers', True, 'Show line numbers in the margin?'),
        IntParam('line_number_margin_width', 40, 'Margin width in pixels'),
        BoolParam('symbols', False, 'Show symbols margin'),
        IntParam('symbols_margin_width', 16, 'Symbols margin width in pixels'),
        BoolParam('folding', False, 'Show the code folding margin?'),
        IntParam('folding_margin_width', 16, 'Code folding margin width in pixels'),
        BoolParam('word_wrap', False, 'True: use word wrapping\nFalse: show horizontal scrollbars'),
        BoolParam('backspace_unindents', True),
        BoolParam('indentation_guides', True, 'Show indentation guides at multiples of the tab_size'),
        IntParam('highlight_column', 30, 'Column at which to highlight the indention guide.\nNote: uses the BRACELIGHT color to highlight'),
        IntParam('edge_column', 80, 'Column at which to show the edge (i.e. long line) indicator'),
        KeyedIndexChoiceParam('edge_indicator',
                              [(wx.stc.STC_EDGE_NONE, 'none'),
                               (wx.stc.STC_EDGE_LINE, 'line'),
                               (wx.stc.STC_EDGE_BACKGROUND, 'background'),
                               ], 'line', help='Long line indication mode'),
        IntParam('caret_blink_rate', 0, help='Blink rate in milliseconds\nor 0 to stop blinking'),
        IntParam('caret_width', 2, help='Caret width in pixels'),
        BoolParam('caret_line_highlight', False, help='Highlight the line containing the cursor?'),
        StrParam('sample_file', "Fundamental mode is the base for all other modes that use the STC to view text."),
        ReadOnlyParam('stc_lexer', wx.stc.STC_LEX_NULL),
        StrParam('stc_keywords', ""),
        StrParam('stc_boa_braces', "{}"),
        ReadOnlyParam('stc_boa_style_names', {}),
        ReadOnlyParam('stc_lexer_styles', {}),

        # Note: 1 tends to be the comment style, but not in all cases.
        ReadOnlyParam('stc_lexer_default_styles', {0: '',
                                     1: 'fore:%(comment-col)s,italic',
                                     wx.stc.STC_STYLE_DEFAULT: 'face:%(mono)s,size:%(size)d',
                                     wx.stc.STC_STYLE_LINENUMBER: 'face:%(ln-font)s,size:%(ln-size)d',
                                     
                                     wx.stc.STC_STYLE_BRACEBAD: '',
                                     wx.stc.STC_STYLE_BRACELIGHT: '',
                                     wx.stc.STC_STYLE_CONTROLCHAR: '',
                                     wx.stc.STC_STYLE_INDENTGUIDE: '',
                                     }),
        )

    def createEditWindow(self,parent):
        assert self.dprint("creating new Fundamental window")
        self.createSTC(parent)
        win=self.stc
        return win

    def createStatusIcons(self):
        linesep = self.stc.getLinesep()
        if linesep == '\r\n':
            self.statusbar.addIcon("icons/windows.png", "DOS/Windows line endings")
        elif linesep == '\r':
            self.statusbar.addIcon("icons/apple.png", "Old-style Apple line endings")
        else:
            self.statusbar.addIcon("icons/tux.png", "Unix line endings")

    def createSTC(self,parent):
        """Create the STC and apply styling settings.

        Everything that subclasses from FundamentalMode will use an
        STC instance for displaying the user interaction window.
        
        Styling information is loaded from the stc-styles.rc.cfg files
        that the boa styling editor uses.  This file is located in the
        default configuration directory of the application on a
        per-user basis, and in the peppy/config directory on a
        site-wide basis.
        """
        self.stc=PeppySTC(parent,refstc=self.buffer.stc)
        self.applySettings()

    def applySettings(self):
        self.applyDefaultSettings()
        if self.styleSTC():
            self.has_stc_styling = True
        else:
            # If the style file fails to load, it probably means that
            # the style definition doesn't exist in the style file.
            # So, add the default style settings supplied by the major
            # mode to the file and try again.
            self.styleDefault()
            if self.styleSTC():
                self.has_stc_styling = True
            else:
                # If the file still doesn't load, fall back to a style
                # that hopefully does exist.  The boa stc styling
                # dialog won't be available.
                self.has_stc_styling = False
                self.styleSTC('text')

    def styleDefault(self):
        """Create entry in stc configuration file for this mode.

        If the style definitions don't exist in the stc configuration
        file, use the defaults supplied by the major mode to add them
        to the file.

        FIXME: The format itself is a bit fragile and will cause
        exceptions if a keyword is missing.  Need to have a robust way
        of handling errors in a user-edited style file.

        See the L{peppy.boa.STCStyleEditor} documentation for more
        information on the format of the configuration file.
        """
        if not self.classprefs.stc_lexer:
            dprint("no STC styling information for major mode %s" % self.keyword)
            return
        boa.updateConfigFile(wx.GetApp(), self)

    def applyDefaultSettings(self):
        # turn off symbol margin
        if self.classprefs.symbols:
            self.stc.SetMarginWidth(1, self.classprefs.symbols_margin_width)
        else:
            self.stc.SetMarginWidth(1, 0)

        # turn off folding margin
        if self.classprefs.folding:
            self.stc.SetMarginWidth(2, self.classprefs.folding_margin_width)
        else:
            self.stc.SetMarginWidth(2, 0)

        self.stc.SetProperty("fold", "1")
        self.stc.SetBackSpaceUnIndents(self.classprefs.backspace_unindents)
        self.stc.SetIndentationGuides(self.classprefs.indentation_guides)
        self.stc.SetHighlightGuide(self.classprefs.highlight_column)

        self.setWordWrap()
        self.setLineNumbers()
        self.setFolding()
        self.setTabStyle()
        self.setEdgeStyle()
        self.setCaretStyle()

    def setWordWrap(self,enable=None):
        if enable is not None:
            self.classprefs.word_wrap=enable
        if self.classprefs.word_wrap:
            self.stc.SetWrapMode(wx.stc.STC_WRAP_CHAR)
            self.stc.SetWrapVisualFlags(wx.stc.STC_WRAPVISUALFLAG_END)
        else:
            self.stc.SetWrapMode(wx.stc.STC_WRAP_NONE)

    def setLineNumbers(self,enable=None):
        if enable is not None:
            self.classprefs.line_numbers=enable
        if self.classprefs.line_numbers:
            self.stc.SetMarginType(0, wx.stc.STC_MARGIN_NUMBER)
            self.stc.SetMarginWidth(0,  self.classprefs.line_number_margin_width)
        else:
            self.stc.SetMarginWidth(0,0)

    def setFolding(self,enable=None):
        if enable is not None:
            self.classprefs.folding=enable
        if self.classprefs.folding:
            self.stc.SetMarginType(2, wx.stc.STC_MARGIN_SYMBOL)
            self.stc.SetMarginMask(2, wx.stc.STC_MASK_FOLDERS)
            self.stc.SetMarginSensitive(2, True)
            self.stc.SetMarginWidth(2, self.classprefs.folding_margin_width)
            # Marker definitions from PyPE
            self.stc.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEREND,     wx.stc.STC_MARK_BOXPLUSCONNECTED,  "white", "black")
            self.stc.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEROPENMID, wx.stc.STC_MARK_BOXMINUSCONNECTED, "white", "black")
            self.stc.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERMIDTAIL, wx.stc.STC_MARK_TCORNER,  "white", "black")
            self.stc.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERTAIL,    wx.stc.STC_MARK_LCORNER,  "white", "black")
            self.stc.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERSUB,     wx.stc.STC_MARK_VLINE,    "white", "black")
            self.stc.MarkerDefine(wx.stc.STC_MARKNUM_FOLDER,        wx.stc.STC_MARK_BOXPLUS,  "white", "black")
            self.stc.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEROPEN,    wx.stc.STC_MARK_BOXMINUS, "white", "black")
            self.stc.Bind(wx.stc.EVT_STC_MARGINCLICK, self.onMarginClick)
        else:
            self.stc.SetMarginWidth(2, 0)
            self.stc.Unbind(wx.stc.EVT_STC_MARGINCLICK)

    def setTabStyle(self):
        self.stc.SetIndent(self.classprefs.tab_size)
        self.stc.SetProperty('tab.timmy.whinge.level', self.classprefs.tab_highlight_style)
        self.stc.SetUseTabs(self.classprefs.use_tab_characters)

    def setEdgeStyle(self):
        self.stc.SetEdgeMode(self.classprefs.edge_indicator)
        if self.classprefs.edge_indicator == wx.stc.STC_EDGE_NONE:
            self.stc.SetEdgeColumn(0)
        else:
            self.stc.SetEdgeColumn(self.classprefs.edge_column)

    def setCaretStyle(self):
        self.stc.SetCaretPeriod(self.classprefs.caret_blink_rate)
        self.stc.SetCaretLineVisible(self.classprefs.caret_line_highlight)
        self.stc.SetCaretWidth(self.classprefs.caret_width)

    def onMarginClick(self, evt):
        # fold and unfold as needed
        if evt.GetMargin() == 2:
            if evt.GetShift() and evt.GetControl():
                self.stc.FoldAll()
            else:
                lineClicked = self.stc.LineFromPosition(evt.GetPosition())
                if self.stc.GetFoldLevel(lineClicked) & wx.stc.STC_FOLDLEVELHEADERFLAG:
                    if evt.GetShift():
                        self.stc.SetFoldExpanded(lineClicked, True)
                        self.stc.Expand(lineClicked, True, True, 1)
                    elif evt.GetControl():
                        if self.stc.GetFoldExpanded(lineClicked):
                            self.stc.SetFoldExpanded(lineClicked, False)
                            self.stc.Expand(lineClicked, False, True, 0)
                        else:
                            self.stc.SetFoldExpanded(lineClicked, True)
                            self.stc.Expand(lineClicked, True, True, 100)
                    else:
                        self.stc.ToggleFold(lineClicked)

    def styleSTC(self, lang=None):
        """Style the STC using the information in the styling config file.

        Call the boa method of styling the stc that reads the styling
        information (including the lexer type) out of its format
        config file.

        @param lang: language keyword to look up in the file
        """
        config=boa.getUserConfigFile(wx.GetApp())
        if lang is None:
            lang = self.keyword
            
        try:
            boa.initSTC(self.stc, config, lang)
        except SyntaxError:
            dprint("no STC style defined for %s" % lang)
            return False
        return True

    def OnUpdateUIHook(self, evt):
        self.braceHighlight()

    def getFoldHierarchy(self):
        """Get the fold hierarchy using Stani's fold explorer algorithm.
        """
        # Turn this into a threaded operation if it takes too long
        self.stc.Colourise(0, self.stc.GetTextLength())
        self.stc.computeFoldHierarchy()
        
        # FIXME: Note that different views of the same buffer *using the
        # same major mode* will have the same fold hierarchy.  This should
        # be exploited, but currently it isn't.
        return self.stc.fold_explorer_root



class FundamentalPlugin(IPeppyPlugin):
    def getMajorModes(self):
        yield FundamentalMode
    
    default_menu=((None,(_("&Help"),_("&Samples")),MenuItem(OpenFundamental).first()),
                  ("Fundamental",_("Edit"),MenuItem(PasteAtColumn).after(_("Paste")).before(_("paste"))),
                  ("Fundamental",_("Edit"),MenuItem(FindText)),
                  ("Fundamental",_("Edit"),MenuItem(ReplaceText)),
                  ("Fundamental",_("Edit"),MenuItem(GotoLine)),
                  ("Fundamental",_("Format"),MenuItem(EOLModeSelect)),
                  ("Fundamental",_("Format"),Separator()),
                  ("Fundamental",_("View"),MenuItem(WordWrap)),
                  ("Fundamental",_("View"),MenuItem(LineNumbers)),
                  ("Fundamental",_("View"),MenuItem(Folding)),
                  ("Fundamental",_("View"),Separator(_("cmdsep"))),
                  ("Fundamental",None,Menu(_("&Transform")).after(_("Edit"))),
                  ("Fundamental",_("&Transform"),MenuItem(ShiftLeft)),
                  ("Fundamental",_("&Transform"),MenuItem(ShiftRight)),
                  ("Fundamental",_("&Transform"),MenuItem(Reindent)),
                  ("Fundamental",_("&Transform"),Separator(_("shift")).last()),
                  ("Fundamental",_("&Transform"),MenuItem(CommentRegion)),
                  ("Fundamental",_("&Transform"),MenuItem(UncommentRegion)),
                  )
    def getMenuItems(self):
        for mode,menu,item in self.default_menu:
            yield (mode,menu,item)

    default_tools=(("Fundamental",None,Menu(_("&Transform")).after(_("Major Mode"))),
                   ("Fundamental",_("&Transform"),MenuItem(ShiftLeft)),
                   ("Fundamental",_("&Transform"),MenuItem(ShiftRight)),
                   )
    def getToolBarItems(self):
        for mode,menu,item in self.default_tools:
            yield (mode,menu,item)

    default_keys=(("Fundamental",BeginningTextOfLine),
                  ("Fundamental",EndOfLine),
                  ("Fundamental",PreviousLine),
                  ("Fundamental",NextLine),
                  ("Fundamental",CapitalizeWord),
                  ("Fundamental",UpcaseWord),
                  ("Fundamental",DowncaseWord),
                  ("Fundamental",ElectricReturn),
                  ("Fundamental",BeginningOfBuffer),
                  ("Fundamental",EndOfBuffer),
                  )
    def getKeyboardItems(self):
        for mode,action in self.default_keys:
            yield (mode,action)


if __name__ == "__main__":
    app=testapp(0)
    frame=RootFrame(app.main)
    frame.Show(True)
    app.MainLoop()

