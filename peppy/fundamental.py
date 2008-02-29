# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os, shutil, time, new, re

import wx
import wx.stc
from wx.lib.pubsub import Publisher

from peppy.actions import *
from peppy.major import *
from peppy.lib.foldexplorer import *
from peppy.lib.stcspellcheckmixin import *

from peppy.editra import *
from peppy.editra.stcmixin import *


class SpellingSuggestionAction(ListAction):
    name = "Spelling..."
    inline = True
    menumax = 5
    tooltip = "Spelling suggestions for the current word"

    def getItems(self):
        # Because this is a popup action, we can save stuff to this object.
        # Otherwise, we'd save it to the major mode
        self.words = self.mode.spellGetSuggestions(self.mode.check_spelling[0])
        if self.words:
            return self.words
        return [_('No suggestions')]
    
    def isEnabled(self):
        return hasattr(self, 'words') and len(self.words) > 0

    def action(self, index=-1, multiplier=1):
        #dprint(self.words[index])
        s = self.mode
        c = s.check_spelling
        s.SetTargetStart(c[1])
        s.SetTargetEnd(c[2])
        s.ReplaceTarget(self.words[index])


class FoldingReindentMixin(object):
    """Experimental class to use STC Folding to reindent a line.
    
    Currently not supported.
    """
    def reindentLine(self, linenum=None, dedent_only=False):
        """Reindent the specified line to the correct level.

        Given a line, use Scintilla's built-in folding to determine
        the indention level of the current line.
        """
        if linenum is None:
            linenum = self.GetCurrentLine()
        linestart = self.PositionFromLine(linenum)

        # actual indention of current line
        ind = self.GetLineIndentation(linenum) # columns
        pos = self.GetLineIndentPosition(linenum) # absolute character position

        # folding says this should be the current indention
        fold = self.GetFoldLevel(linenum)&wx.stc.STC_FOLDLEVELNUMBERMASK - wx.stc.STC_FOLDLEVELBASE
        self.dprint("ind = %s (char num=%d), fold = %s" % (ind, pos, fold))
        self.SetTargetStart(linestart)
        self.SetTargetEnd(pos)
        self.ReplaceTarget(self.GetIndentString(fold))


class ParagraphInfo(object):
    """Summary object about the currently selected paragraph.
    
    This object is built up as the paragraph mixin is searching through the
    file looking for the boundaries of the paragraph.  It is then used as
    input to the paragraph fill and other commands.
    """
    def __init__(self, stc, linenum):
        """Initialize the structure by specifying a line that belongs to the
        paragraph.
        """
        self.s = stc
        self.cursor_linenum = linenum
        line = self.s.GetLine(linenum)
        self.leader_pattern, line, self.trailer = self.s.splitCommentLine(line)
        
        # The line list is maintained in reverse when searching backward,
        # then is reversed before being added to the final list
        self._startlines = [line]
        self._endlines = []
        self._lines = []
        
        # set initial region start and end positions
        self.start = self.s.PositionFromLine(linenum)
        self.end = self.s.GetLineEndPosition(linenum)
        
    def addStartLine(self, linenum, line):
        """Add the line to the list and update the starting position"""
        self._startlines.append(line)
        self.start = self.s.PositionFromLine(linenum)
        
    def addEndLine(self, linenum, line):
        """Add the line to the list and update the starting position"""
        self._endlines.append(line)
        self.end = self.s.GetLineEndPosition(linenum)
        
    def getLines(self):
        """Get the list of lines in the paragraph"""
        if not self._lines:
            # The starting lines are stored in reverse order for easy appending
            self._startlines.reverse()
            self._lines.extend(self._startlines)
            self._lines.extend(self._endlines)
        return self._lines


class FundamentalSTC(EditraSTCMixin, PeppySTC):
    """Subclass of PeppySTC providing the Editra mixin
    
    Needed for the Editra styling dialog.  FIXME: perhaps move the editra stuff
    right into PeppySTC?
    """
    def __init__(self, parent, *args, **kwargs):
        PeppySTC.__init__(self, parent, *args, **kwargs)
        EditraSTCMixin.__init__(self, wx.GetApp().fonts.getStyleFile())


class FundamentalMode(FoldExplorerMixin, STCSpellCheckMixin, EditraSTCMixin,
                      PeppySTC, MajorMode):
    """Major mode for editing generic text files.
    
    This is the most generic major mode used for editing text files.  This uses
    a L{PeppySTC} as the editing window, and is linked to a L{Buffer} object
    that in turn is linked to the backend storage of a L{PeppyBaseSTC}.
    
    All major modes that are edit text using an STC should be subclasses of
    this mode.  Major modes that provide editing windows that aren't an STC
    (like the HexEdit view or an image viewer) will not be subclasses of
    this mode; rather, they will be subclasses of L{MajorMode} and will only
    use an STC as the backend storage within the L{Buffer} attribute that is
    associated with every major mode.
    
    The STC uses the Editra system for styling text and fonts; it is based
    on matching the filename or extension with values from its database.
    Documentation on the Editra interface is forthcoming.
    
    C{FundamentalMode} is a subclass of L{PeppySTC}, so all of the STC methods
    are availble here for user interfacing.  In addition, some mixins are
    used, like the L{BraceHighlightMixin} to provide language customizable
    brace highlighting, and the L{StandardParagraphMixin} used to determine
    the start and end of a paragraph based on the major mode.
    
    Two mixins in particular will need attention when subclassing
    FundamentalMode for new types of text files: L{StandardReturnMixin} and
    L{StandardReindentMixin}.  The L{StandardReturnMixin} provides handling
    for the return key and indenting the following line to the correct tab
    stop.  The L{StandardReindentMixin} is used to indent a line to its proper
    column based on the language supported by the major mode.  FundamentalMode
    subclasses should override both of these classes and provide them as
    mixins in order to customize the major mode.
    
    Because the L{FundamentalMode} serves as the base class for all
    text editing modes, there are many defaults specified in the
    L{default_classprefs} class attribute.  These defaults are based on
    the L{ClassPrefs} metaclass that associates keywords with values and
    serializes them to the peppy configuration file.  ClassPrefs are a
    transparent way to handle the application preferences, and you'll find
    them used all over peppy.  But, as their name suggests, ClassPrefs belong
    to the class, not the instance, so this is not for instance variable
    storage.  See the L{ClassPrefs} documentation for more information.
    """
    keyword = 'Fundamental'
    
    #: If the editra file_type (defined as the LANG_* keywords in the editra source file peppy/editra/synglob.py) doesn't match the class attribute 'keyword', specify the editra file type here.  In other words, None here means that the editra file_type *does* match the keyword
    editra_synonym = None

    #: Default comment characters in case the Editra styling database doesn't have any information about the mode
    start_line_comment = ''
    end_line_comment = ''
    
    #: Default characters that end a word and signal the spell checker
    word_end_chars = ' .!?\'\"'

    #: Default class preferences that relate to all instances of this major mode
    default_classprefs = (
        StrParam('editra_style_sheet', '', 'Mode specific filename in the config directory containing\nEditra style sheet information.  Used to override\ndefault styles with custom styles for this mode.'),
        BoolParam('use_tab_characters', False,
                  'True: insert tab characters when tab is pressed\nFalse: insert the equivalent number of spaces instead.'),
        IntParam('tab_size', 4, 'Number of spaces in each tab'),
        IndexChoiceParam('tab_highlight_style',
                         ['ignore', 'inconsistent', 'mixed', 'spaces are bad', 'tabs are bad'],
                         4, 'Highlight bad intentation'),
        BoolParam('line_numbers', True, 'Show line numbers in the margin?'),
        IntParam('line_number_margin_width', 40, 'Margin width in pixels'),
        BoolParam('symbols', False, 'Show symbols margin'),
        IntParam('symbols_margin_width', 16, 'Symbols margin width in pixels'),
        BoolParam('folding', False, 'Show the code folding margin?'),
        IntParam('folding_margin_width', 16, 'Code folding margin width in pixels'),
        BoolParam('wrapping', False, 'True: use line wrapping\nFalse: show horizontal scrollbars'),
        BoolParam('word_wrap', False, 'True: wrap lines at word boundries\nFalse: wrap at right margin'),
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
        BoolParam('view_eol', False, 'Show line-ending cr/lf characters?'),
        BoolParam('spell_check', True, 'Spell check the document (if pyenchant\nis available'),
        BoolParam('spell_check_strings_only', True, 'Only spell check strings and comments'),
        )
    
    def __init__(self, parent, wrapper, buffer, frame):
        """Create the STC and apply styling settings.

        Everything that subclasses from FundamentalMode will use an
        STC instance for displaying the user interaction window.
        """
        MajorMode.__init__(self, parent, wrapper, buffer, frame)
        start = time.time()
        self.dprint("starting PeppySTC at %0.5fs" % start)
        PeppySTC.__init__(self, parent, refstc=self.buffer.stc)
        self.dprint("PeppySTC done in %0.5fs" % (time.time() - start))
        EditraSTCMixin.__init__(self, wx.GetApp().fonts.getStyleFile())
        self.dprint("EditraSTCMixin done in %0.5fs" % (time.time() - start))
        STCSpellCheckMixin.__init__(self)
        self.dprint("STCSpellCheckMixin done in %0.5fs" % (time.time() - start))

        self.applySettings()
        self.dprint("applySettings done in %0.5fs" % (time.time() - start))
        
        self.buffer.startChangeDetection()

    @classmethod
    def verifyEditraType(cls, ext, file_type):
        cls.dprint("ext=%s file_type=%s" % (ext, file_type))
        if file_type is None:
            # Not recognized at all by Editra.
            return False
        
        # file_type is a human readable string given in peppy.editra.synglob.py
        # If file_type is the same as the major mode keyword or an alias,
        # mark this as a specific match.
        if file_type == cls.keyword or file_type == cls.editra_synonym:
            cls.dprint("Specific match of %s" % file_type)
            return ext
        
        # Otherwise, if the file type is recognized but not specific to this
        # mode, mark it as generic.
        cls.dprint("generic match of %s" % file_type)
        return "generic"
    
    @classmethod
    def verifyMimetype(cls, mimetype):
        """Verify that the mimetype is text/plain.
        
        The class attribute mimetype is not used so that subclasses that extend
        Fundamental but forget to declare a MIME type won't also get added to
        the list of modes that handle text/plain.
        
        This default implementation will call L{MajorMode.verifyMimetype} if not
        overridden by the subclass.
        """
        # check for the class here so that subclasses don't automatically also
        # get associated with text/plain
        if cls == FundamentalMode:
            return mimetype == 'text/plain'
        else:
            return MajorMode.verifyMimetype(mimetype)
    
    def createEventBindingsPostHook(self):
        self.Bind(wx.EVT_CHAR, self.OnChar)
    
    def OnChar(self, evt):
        """Handle all events that result from typing characters in the stc.
        
        Automatic spell checking is handled here.
        """
        uchar = unichr(evt.GetKeyCode())
        if self.classprefs.spell_check and uchar in self.word_end_chars:
            self.spellCheckWord()
        evt.Skip()
    
    def createStatusIcons(self):
        linesep = self.getLinesep()
        if linesep == '\r\n':
            self.status_info.addIcon("icons/windows.png", "DOS/Windows line endings")
        elif linesep == '\r':
            self.status_info.addIcon("icons/apple.png", "Old-style Apple line endings")
        else:
            self.status_info.addIcon("icons/tux.png", "Unix line endings")

    def applySettings(self):
        start = time.time()
        self.dprint("starting applySettings at %0.5fs" % start)
        self.applyDefaultSettings()
        self.dprint("applyDefaultSettings done in %0.5fs" % (time.time() - start))
        
        ext, file_type = MajorModeMatcherDriver.getEditraType(self.buffer.url)
        self.dprint("ext=%s file_type=%s" % (ext, file_type))
        if file_type == 'generic' or file_type is None:
            if self.editra_synonym is not None:
                file_type = self.editra_synonym
            elif self.keyword is not 'Fundamental':
                file_type = self.keyword
            else:
                file_type = ext
        self.editra_lang = file_type
        self.dprint("ext=%s file_type=%s" % (ext, file_type))
        self.SetStyleFont(wx.GetApp().fonts.classprefs.primary_editing_font)
        self.SetStyleFont(wx.GetApp().fonts.classprefs.secondary_editing_font, False)
        self.dprint("font styling done in %0.5fs" % (time.time() - start))
        self.ConfigureLexer(self.editra_lang)
        self.dprint("styleSTC (if True) done in %0.5fs" % (time.time() - start))
        self.has_stc_styling = True
        if self.classprefs.spell_check:
            self.spellStartIdleProcessing()
        else:
            self.spellClearAll()
        self.dprint("applySettings returning in %0.5fs" % (time.time() - start))
    
    def applyDefaultSettings(self):
        # We use our own right click popup menu, so disable the builtin
        self.UsePopUp(0)
        
        # turn off symbol margin
        if self.classprefs.symbols:
            self.SetMarginWidth(1, self.classprefs.symbols_margin_width)
        else:
            self.SetMarginWidth(1, 0)

        # turn off folding margin
        if self.classprefs.folding:
            self.SetMarginWidth(2, self.classprefs.folding_margin_width)
        else:
            self.SetMarginWidth(2, 0)

        self.SetProperty("fold", "1")
        self.SetBackSpaceUnIndents(self.classprefs.backspace_unindents)
        self.SetIndentationGuides(self.classprefs.indentation_guides)
        self.SetHighlightGuide(self.classprefs.highlight_column)

        self.setWordWrap()
        self.setLineNumbers()
        self.setFolding()
        self.setTabStyle()
        self.setEdgeStyle()
        self.setCaretStyle()
        self.setViewEOL()

    def setWordWrap(self, enable=None, style=None):
        if enable is not None:
            self.classprefs.wrapping = enable
        if style is not None:
            self.classprefs.word_wrap = style
        if self.classprefs.wrapping:
            if self.classprefs.word_wrap:
                self.SetWrapMode(wx.stc.STC_WRAP_WORD)
            else:
                self.SetWrapMode(wx.stc.STC_WRAP_CHAR)
            self.SetWrapVisualFlags(wx.stc.STC_WRAPVISUALFLAG_END)
        else:
            self.SetWrapMode(wx.stc.STC_WRAP_NONE)

    def setLineNumbers(self,enable=None):
        if enable is not None:
            self.classprefs.line_numbers=enable
        if self.classprefs.line_numbers:
            self.SetMarginType(0, wx.stc.STC_MARGIN_NUMBER)
            self.SetMarginWidth(0,  self.classprefs.line_number_margin_width)
        else:
            self.SetMarginWidth(0,0)

    def setFolding(self,enable=None):
        if enable is not None:
            self.classprefs.folding=enable
        if self.classprefs.folding:
            self.SetMarginType(2, wx.stc.STC_MARGIN_SYMBOL)
            self.SetMarginMask(2, wx.stc.STC_MASK_FOLDERS)
            self.SetMarginSensitive(2, True)
            self.SetMarginWidth(2, self.classprefs.folding_margin_width)
            # Marker definitions from PyPE
            self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEREND,     wx.stc.STC_MARK_BOXPLUSCONNECTED,  "white", "black")
            self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEROPENMID, wx.stc.STC_MARK_BOXMINUSCONNECTED, "white", "black")
            self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERMIDTAIL, wx.stc.STC_MARK_TCORNER,  "white", "black")
            self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERTAIL,    wx.stc.STC_MARK_LCORNER,  "white", "black")
            self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERSUB,     wx.stc.STC_MARK_VLINE,    "white", "black")
            self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDER,        wx.stc.STC_MARK_BOXPLUS,  "white", "black")
            self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEROPEN,    wx.stc.STC_MARK_BOXMINUS, "white", "black")
            self.Bind(wx.stc.EVT_STC_MARGINCLICK, self.OnMarginClick)
        else:
            self.SetMarginWidth(2, 0)
            self.Unbind(wx.stc.EVT_STC_MARGINCLICK)

    def OnMarginClick(self, evt):
        # fold and unfold as needed
        if evt.GetMargin() == 2:
            if evt.GetShift() and evt.GetControl():
                self.FoldAll()
            else:
                lineClicked = self.LineFromPosition(evt.GetPosition())
                if self.GetFoldLevel(lineClicked) & wx.stc.STC_FOLDLEVELHEADERFLAG:
                    if evt.GetShift():
                        self.SetFoldExpanded(lineClicked, True)
                        self.Expand(lineClicked, True, True, 1)
                    elif evt.GetControl():
                        if self.GetFoldExpanded(lineClicked):
                            self.SetFoldExpanded(lineClicked, False)
                            self.Expand(lineClicked, False, True, 0)
                        else:
                            self.SetFoldExpanded(lineClicked, True)
                            self.Expand(lineClicked, True, True, 100)
                    else:
                        self.ToggleFold(lineClicked)

    def setTabStyle(self):
        self.SetIndent(self.classprefs.tab_size)
        self.SetProperty('tab.timmy.whinge.level', str(self.classprefs.tab_highlight_style))
        self.SetUseTabs(self.classprefs.use_tab_characters)

    def setEdgeStyle(self):
        self.SetEdgeMode(self.classprefs.edge_indicator)
        if self.classprefs.edge_indicator == wx.stc.STC_EDGE_NONE:
            self.SetEdgeColumn(0)
        else:
            self.SetEdgeColumn(self.classprefs.edge_column)

    def setCaretStyle(self):
        self.SetCaretPeriod(self.classprefs.caret_blink_rate)
        self.SetCaretLineVisible(self.classprefs.caret_line_highlight)
        self.SetCaretWidth(self.classprefs.caret_width)

    def setViewEOL(self, enable=None):
        if enable is not None:
            self.classprefs.view_eol = enable
        self.SetViewEOL(self.classprefs.view_eol)
    
    def braceHighlight(self):
        """Highlight matching braces or flag mismatched braces.
        
        Code taken from StyledTextCtrl_2 from the wxPython demo.  Should
        probably implement this as a dynamic method of the text control or
        the Major Mode, controllable by a setting.
        """
        # check for matching braces
        braceAtCaret = -1
        braceOpposite = -1
        braceStyle = None
        charBefore = None
        caretPos = self.GetCurrentPos()

        # check before
        if caretPos > 0:
            charBefore = self.GetCharAt(caretPos - 1)
            braceStyle = self.GetStyleAt(caretPos - 1)
            #dprint("before: char=%s style=%d" % (charBefore, braceStyle))

            if charBefore and chr(charBefore) in "[]{}()":
                braceAtCaret = caretPos - 1

        # check after
        if braceAtCaret < 0:
            charAfter = self.GetCharAt(caretPos)
            braceStyle = self.GetStyleAt(caretPos)
            #dprint("after: char=%s style=%d" % (charAfter, braceStyle))

            if charAfter and chr(charAfter) in "[]{}()":
                braceAtCaret = caretPos

        if braceAtCaret >= 0:
            braceOpposite = self.BraceMatch(braceAtCaret)

        if braceAtCaret != -1  and braceOpposite == -1:
            self.BraceBadLight(braceAtCaret)
        else:
            if braceStyle != self.GetStyleAt(braceOpposite):
                self.BraceBadLight(braceAtCaret)
            else:
                self.BraceHighlight(braceAtCaret, braceOpposite)

    def OnUpdateUI(self, evt):
        """Specific OnUpdateUI callback for those modes that use an actual
        STC for their edit window.
        
        Adds things like fold level and style display.
        """
        self.braceHighlight()
        assert self.dprint("OnUpdateUI for view %s, frame %s" % (self.keyword,self.frame))
        linenum = self.GetCurrentLine()
        pos = self.GetCurrentPos()
        col = self.GetColumn(pos)
        self.status_info.setText("L%d C%d F%d S%d %d" % (linenum+self.classprefs.line_number_offset,
            col+self.classprefs.column_number_offset,
            self.GetFoldLevel(linenum)&wx.stc.STC_FOLDLEVELNUMBERMASK - wx.stc.STC_FOLDLEVELBASE,
            self.GetStyleAt(pos), pos),1)
        self.idle_update_menu = True
        self.OnUpdateUIHook(evt)
        if evt is not None:
            evt.Skip()

    def showInitialPosition(self, url):
        if url.fragment:
            line = int(url.fragment)
            line -= self.classprefs.line_number_offset
            self.GotoLine(line)
            self.EnsureVisible(line)

    ##### Comment handling
    def setCommentDelimiters(self, start='', end=''):
        """Set instance-specific comment characters and comment regex
        
        If the instance uses different comment characters that the class
        attributes, set the instance attributes here which will override
        the class attributes.
        
        A regex is created that will match a line with the comment characters.
        The regex returns a 3-tuple of whitespace followed by the opening
        comment character, the body of the line, and then the closing comment
        including any trailing whitespace.  If the language doesn't have a
        closing comment character, the final tuple element will always be
        an empty string.
        
        This is typically called by the Editra stc mixin to set the
        comment characters encoded by the Editra style manager.
        """
        self.start_line_comment = start
        self.end_line_comment = end
        if start:
            if end:
                regex = r"^(\s*(?:%s)*)(.*?)((?:%s)*\s*$)" % ("\\" + "\\".join(start), "\\" + "\\".join(end))
                self.dprint(regex)
                self.comment_regex = re.compile(regex)
            else:
                regex = r"^(\s*(?:%s)*)(.*)($)" % ("\\" + "\\".join(start))
                self.dprint(regex)
                self.comment_regex = re.compile(regex)
        else:
            regex = r"^(\s*)(.*)($)"
            self.dprint(regex)
            self.comment_regex = re.compile(regex)
        
    def commentRegion(self, add=True):
        """Default implementation of block commenting and uncommenting
    
        This class provides the default implementation of block commenting.
        Blocks are commented by adding a comment string at the beginning of
        the line, and an optional comment string at the end of each line in
        the block.
    
        Typically the comment characters are known to the Editra styling system
        and are therefore automatically added to the FundamentalMode subclass
        by a call to L{setCommentDelimiters}.

        @param add: True to add comments, False to remove them
        """
        eol_len = len(self.getLinesep())
        if add:
            func = self.addLinePrefixAndSuffix
        else:
            func = self.removeLinePrefixAndSuffix
        
        self.BeginUndoAction()
        line, lineend = self.GetLineRegion()
        assert self.dprint("lines: %d - %d" % (line, lineend))
        try:
            selstart, selend = self.GetSelection()
            assert self.dprint("selection: %d - %d" % (selstart, selend))

            start = selstart
            end = self.GetLineEndPosition(line)
            while line <= lineend:
                start = func(start, end, self.start_line_comment, self.end_line_comment)
                line += 1
                end = self.GetLineEndPosition(line)
            self.SetSelection(selstart, start - eol_len)
        finally:
            self.EndUndoAction()
            
    def splitCommentLine(self, line):
        """Split the line into the whitespace leader and body of the line.
        
        Return a tuple containing the leading whitespace and comment
        character(s), the body of the line, and any trailing comment
        character(s)
        """
        match = self.comment_regex.match(line)
        if match is None:
            return ("", line, "")
        self.dprint(match.groups())
        return match.group(1, 2, 3)


    ##### Indentation
    def findIndent(self, linenum):
        """Find proper indention of next line given a line number.

        This is designed to be overridden in subclasses.  Given the current
        line and assuming the current line is indented correctly, figure out
        what the indention should be for the next line.
        
        @param linenum: line number
        @return: integer indicating number of columns to indent the following
        line
        """
        return self.GetLineIndentation(linenum)

    def getReindentColumn(self, linenum, linestart, pos, indpos, col, indcol):
        """Determine the correct indentation of the first not-blank character
        of the line.
        
        This routine should be overridden in subclasses; this provides a
        default implementation of line reindentatiot that simply reindents the
        line to the indentation of the line above it.  Subclasses with more
        specific knowledge of the text being edited will be able to use the
        syntax of previous lines to indent the line properly.
        
        linenum: current line number
        linestart: position of character at column zero of line
        pos: position of cursor
        indpos: position of first non-blank character in line
        col: column number of cursor
        indcol: column number of first non-blank character
        
        return: the number of columns to indent, or None to leave as-is
        """
        # look at indention of previous line
        prevind, prevline = self.GetPrevLineIndentation(linenum)
        if (prevind < indcol and prevline < linenum-1) or prevline < linenum-2:
            # if there's blank lines before this and the previous
            # non-blank line is indented less than this one, ignore
            # it.  Make the user manually unindent lines.
            return None

        # previous line is not blank, so indent line to previous
        # line's level
        return prevind

    def reindentLine(self, linenum=None, dedent_only=False):
        """Reindent the specified line to the correct level.

        This method should be overridden in subclasses to provide the proper
        indention based on the type of text file.  The default implementation
        provided here will indent to the previous line.
        
        This operation is typically bound to the tab key, but regardless to the
        actual keypress to which it is bound is *only* called in response to a
        user keypress.
        
        @return: the new cursor position, in case the cursor has moved as a
        result of the indention.
        """
        if linenum is None:
            linenum = self.GetCurrentLine()
        if linenum == 0:
            # first line is always indented correctly
            return self.GetCurrentPos()
        
        linestart = self.PositionFromLine(linenum)

        # actual indention of current line
        indcol = self.GetLineIndentation(linenum) # columns
        pos = self.GetCurrentPos()
        indpos = self.GetLineIndentPosition(linenum) # absolute character position
        col = self.GetColumn(pos)
        self.dprint("linestart=%d indpos=%d pos=%d col=%d indcol=%d" % (linestart, indpos, pos, col, indcol))

        newind = self.getReindentColumn(linenum, linestart, pos, indpos, col, indcol)
        if newind is None:
            return pos
        if dedent_only and newind > indcol:
            return pos
            
        # the target to be replaced is the leading indention of the
        # current line
        indstr = self.GetIndentString(newind)
        self.dprint("linenum=%d indstr='%s'" % (linenum, indstr))
        self.SetTargetStart(linestart)
        self.SetTargetEnd(indpos)
        self.ReplaceTarget(indstr)

        # recalculate cursor position, because it may have moved if it
        # was within the target
        after = self.GetLineIndentPosition(linenum)
        self.dprint("after: indent=%d cursor=%d" % (after, self.GetCurrentPos()))
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

    def electricReturn(self):
        """Add a newline and indent to the proper tab level.

        Indent to the level of the line above.  This is the entry point action
        when the return key is pressed.  At a minimum it should insert the
        appropriate line end character (cr, crlf, or lf depending on the
        current state of the STC), but provides the opportunity to indent the
        line as well.
    
        The default action is to simply copy the indent level of the previous
        line.
        """
        linesep = self.getLinesep()
        
        self.BeginUndoAction()
        # reindent current line (if necessary), then process the return
        #pos = self.reindentLine()
        
        linenum = self.GetCurrentLine()
        pos = self.GetCurrentPos()
        col = self.GetColumn(pos)
        linestart = self.PositionFromLine(linenum)
        line = self.GetLine(linenum)[:pos-linestart]
    
        #get info about the current line's indentation
        ind = self.GetLineIndentation(linenum)

        self.dprint("format = %s col=%d ind = %d" % (repr(linesep), col, ind)) 

        self.SetTargetStart(pos)
        self.SetTargetEnd(pos)
        if col <= ind:
            newline = linesep+self.GetIndentString(col)
        elif not pos:
            newline = linesep
        else:
            ind = self.findIndent(linenum + 1)
            newline = linesep+self.GetIndentString(ind)
        self.ReplaceTarget(newline)
        self.GotoPos(pos + len(newline))
        if self.classprefs.spell_check:
            self.spellCheckWord(pos)
        self.EndUndoAction()


    ##### Paragraphs
    def findParagraphStart(self, linenum, info):
        """Check to see if a previous line should be included in the
        paragraph match.
        
        Routine designed to be overridden by subclasses to evaluate
        if a line should be included in the list of lines that belong with
        the current paragraph.
        
        Add the line to the ParagraphInfo class using addStartLine if it
        belongs.
        
        Return True if findParagraph should continue searching; otherwise
        return False
        """
        leader, line, trailer = self.splitCommentLine(self.GetLine(linenum))
        self.dprint(line)
        if leader != info.leader_pattern or len(line.strip())==0:
            return False
        info.addStartLine(linenum, line)
        return True
    
    def findParagraphEnd(self, linenum, info):
        """Check to see if a following line should be included in the
        paragraph match.
        
        Routine designed to be overridden by subclasses to evaluate
        if a line should be included in the list of lines that belong with
        the current paragraph.
        
        Add the line to the ParagraphInfo class using addEndLine if it belongs.
        
        Return True if findParagraph should continue searching; otherwise
        return False
        """
        leader, line, trailer = self.splitCommentLine(self.GetLine(linenum))
        self.dprint(line)
        if leader != info.leader_pattern or len(line.strip())==0:
            return False
        info.addEndLine(linenum, line)
        return True
        
    def findParagraph(self, start, end=-1):
        if end == -1:
            end = start
        linenum = self.LineFromPosition(start)
        info = ParagraphInfo(self, linenum)
        
        # find the start of the paragraph by searching backwards till the
        # prefix changes or we find a line with only whitespace in it
        while linenum > 0:
            linenum -= 1
            if not self.findParagraphStart(linenum, info):
                break
        
        endlinenum = self.LineFromPosition(end)
        if endlinenum > info.cursor_linenum:
            # find all the lines in the middle, doing the best to strip off any
            # leading comment chars from the line
            linenum = info.cursor_linenum
            while linenum < endlinenum:
                linenum += 1
                leader, line, trailer = self.splitCommentLine(self.GetLine(linenum))
                info.addEndLine(linenum, line)
                
        # Now, find the end of the paragraph by searching forward until the
        # comment prefix changes or we find only white space
        lastlinenum = self.GetLineCount()
        self.dprint("start=%d count=%d end=%d" % (info.cursor_linenum, lastlinenum, endlinenum))
        while endlinenum < lastlinenum:
            endlinenum += 1
            if not self.findParagraphEnd(endlinenum, info):
                break
        return info


    ##### Code folding for function lists
    def OnFoldChanged(self, evt):
        """Callback to process fold events.
        
        This callback is initiated from within the event handler of PeppySTC.
        The events could be used to optimize the fold algorithm, but
        currently this data is not used by anything.
        """
        stc_class_info = self.getSharedClassInfo(self.__class__)
        if 'fold_hierarchy' in stc_class_info:
            #dprint("changed fold at line=%d, pos=%d" % (evt.Line, evt.Position))
            stc_class_info['fold_changed'].append(evt.Line)
    
    def getFoldHierarchy(self):
        """Get the current fold hierarchy, returning the existing copy if there
        are no changes, or updating if necessary.
        """
        stc_class_info = self.getSharedClassInfo(self.__class__)
        if 'fold_hierarchy' not in stc_class_info or stc_class_info['fold_changed'] or self.GetLineCount() != stc_class_info['fold_line_count']:
            #dprint("Fold hierarchy has changed.  Updating.")
            self.updateFoldHierarchy()
        fold_hier = stc_class_info['fold_hierarchy']
        return fold_hier

    def updateFoldHierarchy(self):
        """Create the fold hierarchy using Stani's fold explorer algorithm.

        Scintilla's folding code is used to generate the function lists in
        some major modes.  Scintilla doesn't support code folding in all its
        supported languages, so major modes that aren't supported may mimic
        this interface to provide similar functionality.
        """
        # FIXME: Turn this into a threaded operation if it takes too long
        t = time.time()
        self.Colourise(0, self.GetTextLength())
        self.dprint("Finished colourise: %0.5f" % (time.time() - t))
        
        # Note that different views of the same buffer *using the same major
        # mode* will have the same fold hierarchy.  So, we use the stc's
        # getSharedClassInfo interface to store data common to all views of
        # this buffer that use this major mode.
        stc_class_info = self.getSharedClassInfo(self.__class__)
        stc_class_info['fold_hierarchy'] = self.computeFoldHierarchy()
        stc_class_info['fold_changed'] = []
        
        # Note: folding events aren't fired when only blank lines are inserted
        # or deleted, so we keep track of the line count as a secondary method
        # to indicate the folding needs to be recalculated
        stc_class_info['fold_line_count'] = self.GetLineCount()
        
        return stc_class_info['fold_hierarchy']
    
    def getFoldEntryFunctionName(self, line):
        """Check if line should be included in a list of functions.
        
        Used as callback function by the fold explorer mixin: if the line should
        be included in a list of functions, return True here.  Because the
        scintilla folding includes a lot of other data than function calls, we
        have to cull the full list to only include lines that we want.
        
        @param line: line number of the fold entry
        
        @return: text string that should be used as function name, or "" if it
        should be skipped in the function menu
        """
        return ""


    ### Spell checking utilities
    def getPopupActions(self, x, y):
        pos = self.PositionFromPoint(wx.Point(x, y))
        self.check_spelling = self.getWordFromPosition(pos)
        #dprint(self.check_spelling)
        action_classes = [SpellingSuggestionAction]
        Publisher().sendMessage('fundamental.context_menu', action_classes)
        return action_classes

    def idlePostHook(self):
        if self.classprefs.spell_check:
            self.spellProcessIdleBlock()
    
    def spellIsSpellCheckRegion(self, pos):
        if self.classprefs.spell_check_strings_only:
            style = self.GetStyleAt(pos)
            return self.isStyleComment(style) or self.isStyleString(style)
        return True
