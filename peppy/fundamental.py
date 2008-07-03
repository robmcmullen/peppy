# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os, shutil, time, new, re

import wx
import wx.stc
from wx.lib.pubsub import Publisher

from peppy.major import *
from peppy.lib.autoindent import *
from peppy.lib.foldexplorer import *
from peppy.lib.vimutil import *
from peppy.lib.emacsutil import *
from peppy.lib.kateutil import *

from peppy.editra import *
from peppy.editra.stcmixin import *



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


class FundamentalMode(FoldExplorerMixin, EditraSTCMixin,
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
    
    #: STC Marker number used for bookmarks
    bookmark_marker_number = 1
    
    #: Default characters that end a word and signal the spell checker
    word_end_chars = ' .!?\'\"'

    #: Default class preferences that relate to all instances of this major mode
    default_classprefs = (
        StrParam('editra_style_sheet', '', 'Mode specific filename in the config directory containing Editra style sheet information.  Used to override default styles with custom styles for this mode.'),
        BoolParam('use_tab_characters', False,
                  'True: insert tab characters when tab is pressed.  False: insert the equivalent number of spaces instead.', local=True),
        IntParam('tab_size', 8, 'Number of spaces in each expanded tab', local=True),
        IntParam('indent_size', 4, 'Number of spaces in each indent level', local=True),
        IndexChoiceParam('tab_highlight_style',
                         ['ignore', 'inconsistent', 'mixed', 'spaces are bad', 'tabs are bad'],
                         1, 'Highlight bad intentation', local=True),
        BoolParam('line_numbers', True, 'Show line numbers in the margin?', local=True),
        IntParam('line_number_margin_width', 40, 'Margin width in pixels', local=True),
        BoolParam('symbols', False, 'Show symbols margin', local=True),
        IntParam('symbols_margin_width', 16, 'Symbols margin width in pixels', local=True),
        BoolParam('folding', False, 'Show the code folding margin?', local=True),
        IntParam('folding_margin_width', 16, 'Code folding margin width in pixels', local=True),
        BoolParam('wrapping', False, 'If set, use line wrapping; otherwise show horizontal scrollbars', local=True),
        BoolParam('word_wrap', False, 'If set, wrap lines at word boundries; otherwise wrap at right margin', local=True),
        BoolParam('backspace_unindents', True, local=True),
        BoolParam('indentation_guides', True, 'Show indentation guides at multiples of the indent_size', local=True),
        IntParam('highlight_column', 30, 'Column at which to highlight the indention guide.', local=True),
        IntParam('edge_column', 80, 'Column at which to show the edge (i.e. long line) indicator', local=True),
        KeyedIndexChoiceParam('edge_indicator',
                              [(wx.stc.STC_EDGE_NONE, 'none'),
                               (wx.stc.STC_EDGE_LINE, 'line'),
                               (wx.stc.STC_EDGE_BACKGROUND, 'background'),
                               ], 'line', help='Long line indication mode', local=True),
        IntParam('caret_blink_rate', 0, help='Blink rate in milliseconds or 0 to stop blinking', local=True),
        IndexChoiceParam('caret_width',
                         [(1, '1 Pixel'), (2, '2 Pixels'), (3, '3 Pixels'),],
                         2, help='Caret width in pixels', local=True),
        BoolParam('caret_line_highlight', False, help='Highlight the line containing the cursor?', local=True),
        BoolParam('view_eol', False, 'Show line-ending cr/lf characters?', local=True),
        KeyedIndexChoiceParam('view_whitespace',
                              [(wx.stc.STC_WS_INVISIBLE, 'none'),
                               (wx.stc.STC_WS_VISIBLEALWAYS, 'visible'),
                               (wx.stc.STC_WS_VISIBLEAFTERINDENT, 'after indent'),
                               ], 'none', help='Visible whitespace mode', local=True),
        IntParam('font_zoom', 0, 'Change the text size relative to the standard font size', local=True),
        BoolParam('spell_check', True, 'Spell check the document (if pyenchant is available)'),
        BoolParam('spell_check_strings_only', True, 'Only spell check strings and comments'),
        IntParam('vim_settings_lines', 20, 'Number of lines from start or end of file to search for vim modeline comments'),
        BoolParam('case_sensitive_search', False, 'Case of search string must match exactly if True; otherwise mixed case requires exact match and lower case matches all', local=True),
        BoolParam('case_matching_replace', True, 'Case will be modified to match if True; otherwise case will be left as was found', local=True),
        )
    
    autoindent = NullAutoindent()

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
        
        self.spell = None

    def createWindowPostHook(self):
        """Apply settings for the STC"""
        start = time.time()
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
        
        # If the editra filetype exists but doesn't match the editra synonym,
        # then we know the mode won't work.
        if cls.editra_synonym and file_type != cls.editra_synonym:
            return False
        
        # Same with the mode keyword: if there's no editra synonym the keyword
        # is used to match against the editra filetype.  If the editra type
        # doesn't match the keyword, the mode won't work.  However, if the
        # mode is specifically labeled as a generic mode (matches text/plain),
        # we *do* want to allow this mode to match.
        if not cls.editra_synonym and not cls.verifyMimetype('text/plain') and file_type != cls.keyword:
            return False
        
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
        self.Bind(wx.stc.EVT_STC_MARGINCLICK, self.OnMarginClick)

    def OnChar(self, evt):
        """Handle all events that result from typing characters in the stc.
        
        Automatic spell checking is handled here.
        """
        
        # Make sure that we have the focus before processing chars.
        if self.FindFocus() != self:
            return

        uchar = unichr(evt.GetKeyCode())
        if self.autoindent.electricChar(self, uchar):
            # If the autoindenter handles the char, it will insert the char.
            # So, we don't call Skip in this case and the processing ends
            # here.
            return
        if self.spell and self.classprefs.spell_check and uchar in self.word_end_chars:
            # We are catching the event before the character is added to the
            # text, so we know the cursor is at the end of the word.
            self.spell.checkWord(atend=True)
        evt.Skip()
    
    def createStatusIcons(self):
        linesep = self.getLinesep()
        if linesep == '\r\n':
            self.status_info.addIcon("icons/windows.png", "DOS/Windows line endings")
        elif linesep == '\r':
            self.status_info.addIcon("icons/apple.png", "Old-style Apple line endings")
        else:
            self.status_info.addIcon("icons/tux.png", "Unix line endings")
        if self.spell and self.spell.hasDictionary():
            self.status_info.addIcon("icons/book_open.png", "Dictionary available for %s" % self.spell.getLanguage())
    
    def getTemplateCallback(self):
        """If a template is desired, this function will return a functor that
        applies the template for this major mode.
        
        """
        if self.GetLength() == 0:
            return self.resetText
        return None

    def applySettings(self):
        start = time.time()
        self.dprint("starting applySettings")
        self.applyDefaultSettings()
        self.dprint("applyDefaultSettings done in %0.5fs" % (time.time() - start))
        
        # Try to find the editra style corresponding to the major mode.  If
        # there is no mode corresponding to the major mode name, let the
        # Editra styling system choose the style based on the filename
        if self.editra_synonym is not None:
            file_type = self.editra_synonym
        else:
            file_type = self.keyword
        if not self.isEditraLanguage(file_type):
            ext, file_type = MajorModeMatcherDriver.getEditraType(self.buffer.url)
            self.dprint("ext=%s file_type=%s" % (ext, file_type))
            if file_type == 'generic' or file_type is None:
                file_type = 'Plain Text'
            self.dprint("ext=%s file_type=%s" % (ext, file_type))
            
        self.editra_lang = file_type
        self.SetStyleFont(wx.GetApp().fonts.classprefs.primary_editing_font)
        self.SetStyleFont(wx.GetApp().fonts.classprefs.secondary_editing_font, False)
        self.dprint("font styling done in %0.5fs" % (time.time() - start))
        self.ConfigureLexer(self.editra_lang)
        self.dprint("styleSTC (if True) done in %0.5fs" % (time.time() - start))
        self.has_stc_styling = True
        self.setEmacsAndVIM()
        self.setSpelling()
        self.dprint("applySettings returning in %0.5fs" % (time.time() - start))
    
    def applyDefaultSettings(self):
        # We use our own right click popup menu, so disable the builtin
        self.UsePopUp(0)
        
        # turn off symbol margin
        if self.locals.symbols:
            self.SetMarginWidth(1, self.locals.symbols_margin_width)
        else:
            self.SetMarginWidth(1, 0)

        # turn off folding margin
        if self.locals.folding:
            self.SetMarginWidth(2, self.locals.folding_margin_width)
        else:
            self.SetMarginWidth(2, 0)

        self.SetProperty("fold", "1")
        self.SetBackSpaceUnIndents(self.locals.backspace_unindents)
        self.SetHighlightGuide(self.locals.highlight_column)

        self.setWordWrap()
        self.setLineNumbers()
        self.setFolding()
        self.setTabStyle()
        self.setEdgeStyle()
        self.setCaretStyle()
        self.setViewEOL()
        self.setWhitespace()
        
        # Added call to colourise because some parameter might have changed
        # that requires a styling update.  E.g.  if the tab highlighting style
        # has changed.
        self.Colourise(0, self.GetTextLength())

    def setWordWrap(self, enable=None, style=None):
        if enable is not None:
            self.locals.wrapping = enable
        if style is not None:
            self.locals.word_wrap = style
        if self.locals.wrapping:
            if self.locals.word_wrap:
                self.SetWrapMode(wx.stc.STC_WRAP_WORD)
            else:
                self.SetWrapMode(wx.stc.STC_WRAP_CHAR)
            self.SetWrapVisualFlags(wx.stc.STC_WRAPVISUALFLAG_END)
        else:
            self.SetWrapMode(wx.stc.STC_WRAP_NONE)

    def setLineNumbers(self,enable=None):
        if enable is not None:
            self.locals.line_numbers=enable
        if self.locals.line_numbers:
            self.SetMarginType(0, wx.stc.STC_MARGIN_NUMBER)
            self.SetMarginWidth(0, self.locals.line_number_margin_width)
        else:
            self.SetMarginWidth(0, 0)
        self.SetMarginMask(0, ~wx.stc.STC_MASK_FOLDERS)
        self.MarkerDefine(self.bookmark_marker_number, wx.stc.STC_MARK_ARROWS)

    def setFolding(self,enable=None):
        if enable is not None:
            self.locals.folding=enable
        if self.locals.folding:
            self.SetMarginType(2, wx.stc.STC_MARGIN_SYMBOL)
            self.SetMarginMask(2, wx.stc.STC_MASK_FOLDERS)
            self.SetMarginSensitive(2, True)
            self.SetMarginWidth(2, self.locals.folding_margin_width)
            # Marker definitions from PyPE
            self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEREND,     wx.stc.STC_MARK_BOXPLUSCONNECTED,  "white", "black")
            self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEROPENMID, wx.stc.STC_MARK_BOXMINUSCONNECTED, "white", "black")
            self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERMIDTAIL, wx.stc.STC_MARK_TCORNER,  "white", "black")
            self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERTAIL,    wx.stc.STC_MARK_LCORNER,  "white", "black")
            self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERSUB,     wx.stc.STC_MARK_VLINE,    "white", "black")
            self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDER,        wx.stc.STC_MARK_BOXPLUS,  "white", "black")
            self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEROPEN,    wx.stc.STC_MARK_BOXMINUS, "white", "black")
            #self.Bind(wx.stc.EVT_STC_MARGINCLICK, self.OnMarginClick)
        else:
            self.SetMarginWidth(2, 0)
            #self.Unbind(wx.stc.EVT_STC_MARGINCLICK)

    def OnMarginClick(self, evt):
        lineClicked = self.LineFromPosition(evt.GetPosition())
        if evt.GetMargin() == 0:
            # FIXME: This doesn't actually work because I don't want to make
            # margin 0 sensitive.  Making it sensitive then requires managing
            # all the selection stuff myself.  But, don't want to add margin 1
            # unnecessarily...  A conundrum.
            self.MarkerAdd(lineClicked, self.bookmark_marker_number)
        elif evt.GetMargin() == 2:
            # handle folding and unfolding
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
        self.SetIndentationGuides(self.locals.indentation_guides)
        self.SetIndent(self.locals.indent_size)
        self.SetTabWidth(self.locals.tab_size)
        self.SetProperty('tab.timmy.whinge.level', str(self.locals.tab_highlight_style))
        self.SetUseTabs(self.locals.use_tab_characters)

    def setEdgeStyle(self):
        self.SetEdgeMode(self.locals.edge_indicator)
        if self.locals.edge_indicator == wx.stc.STC_EDGE_NONE:
            self.SetEdgeColumn(0)
        else:
            self.SetEdgeColumn(self.locals.edge_column)

    def setCaretStyle(self):
        self.SetCaretPeriod(self.locals.caret_blink_rate)
        self.SetCaretLineVisible(self.locals.caret_line_highlight)
        self.SetCaretWidth(self.locals.caret_width)

    def setViewEOL(self, enable=None):
        if enable is not None:
            self.locals.view_eol = enable
        self.SetViewEOL(self.locals.view_eol)
    
    def setWhitespace(self):
        self.SetViewWhiteSpace(self.locals.view_whitespace)
    
    def setEmacsAndVIM(self):
        lines = self.getFileLocalComments()
        settings = applyVIMModeline(self, lines)
        emacs_settings, emacs_locals = applyEmacsFileLocalSettings(self)
        settings.extend(emacs_settings)
        kate_settings, kate_locals = applyKateVariables(self, lines)
        settings.extend(kate_settings)
        
        # Map the STC function to the local variable name so the local variables
        # can be properly updated to whatever VIM or EMACS set them to
        mapping = {'Indent': 'indent_size',
                   'TabWidth': 'tab_size',
                   'UseTabs': 'use_tab_characters',
                   'EdgeColumn': 'edge_column',
                   'CaretWidth': 'caret_width',
                   'CaretLineVisible': 'caret_line_indicator',
                   'SetViewWhiteSpace': 'view_whitespace',
                   }
        for setting in settings:
            if setting in mapping:
                value = getattr(self, "Get%s" % setting)()
                #dprint("Setting %s to %s" % (mapping[setting], value))
                setattr(self.locals, mapping[setting], value)

    def getFileLocalComments(self):
        start = min(self.GetLineCount(), self.classprefs.vim_settings_lines)
        lines = range(0, start)
        ending = max(start, self.GetLineCount() - self.classprefs.vim_settings_lines)
        lines.extend(range(ending, self.GetLineCount()))
        text = []
        for linenum in lines:
            line = self.GetLine(linenum)
            match = self.comment_regex.match(line)
            if match.group(1).endswith(self.start_line_comment):
                #dprint("line %d: %s" % (linenum, str(match.groups())))
                text.append(line)
        return text
    
    ##### Revert hooks
    def getViewPositionData(self):
        return {'top': self.GetFirstVisibleLine(),
                'pos': self.GetCurrentPos(),
                }
    
    def setViewPositionData(self, data):
        if 'top' in data:
            line = min(data['top'], self.GetLineCount() - 1)
            self.ScrollToLine(line)
        if 'pos' in data:
            pos = min(data['pos'], self.GetLength() - 1)
            self.GotoPos(pos)
    
    
    ##### Styling code
    
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
    def setSpelling(self):
        spelling_classes = []
        Publisher().sendMessage('spelling.provider', spelling_classes)
        if spelling_classes:
            self.spell = spelling_classes[0](self, check_region=self.isSpellCheckRegion)
            self.spell.clearAll()
            if self.classprefs.spell_check:
                self.spell.startIdleProcessing()

    def getPopupActions(self, evt, x, y):
        pos = self.PositionFromPoint(wx.Point(x, y))
        # Save the word that should be spell-checked so that the spell checking
        # action won't have to figure out which word to check
        self.check_spelling = self.getWordFromPosition(pos)
        #dprint(self.check_spelling)
        action_classes = []
        Publisher().sendMessage('fundamental.context_menu', action_classes)
        return action_classes

    def idlePostHook(self):
        if self.spell and self.classprefs.spell_check:
            self.spell.processIdleBlock()
    
    def isSpellCheckRegion(self, pos):
        if self.classprefs.spell_check_strings_only:
            style = self.GetStyleAt(pos)
            return self.isStyleComment(style) or self.isStyleString(style)
        return True

    def updateRegion(self, start, end):
        self.Colourise(start, end)
        self.spell.checkRange(start, end)
