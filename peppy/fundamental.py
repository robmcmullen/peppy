# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
import os, shutil

import wx
import wx.stc as stc

from peppy import *
from peppy.menu import *

from peppy.actions.minibuffer import *
from peppy.actions.gotoline import *
from peppy.actions.pypefind import *
import peppy.boa as boa

class OpenFundamental(SelectAction):
    name = "&Open Sample Text"
    tooltip = "Open some sample text"
    icon = wx.ART_FILE_OPEN

##    def isEnabled(self):
##        return not self.frame.isOpen()

    def action(self, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.open("about:demo.txt")

class WordWrap(ToggleAction):
    name = "&Word Wrap"
    tooltip = "Toggle word wrap in this view"
    icon = wx.ART_TOOLBAR

    def isChecked(self):
        viewer=self.frame.getActiveMajorMode()
        if viewer:
            return viewer.settings.word_wrap
        return False
    
    def action(self, pos=-1):
        self.dprint("id=%x name=%s" % (id(self),self.name))
        viewer=self.frame.getActiveMajorMode()
        if viewer:
            viewer.setWordWrap(not viewer.settings.word_wrap)
    
class LineNumbers(ToggleAction):
    name = "&Line Numbers"
    tooltip = "Toggle line numbers in this view"
    icon = wx.ART_TOOLBAR

    def isChecked(self):
        viewer=self.frame.getActiveMajorMode()
        if viewer:
            return viewer.settings.line_numbers
        return False
    
    def action(self, pos=-1):
        self.dprint("id=%x name=%s" % (id(self),self.name))
        viewer=self.frame.getActiveMajorMode()
        if viewer:
            viewer.setLineNumbers(not viewer.settings.line_numbers)
    
class BeginningOfLine(SelectAction):
    name = "Cursor to Start of Line"
    tooltip = "Move the cursor to the start of the current line"
    keyboard = 'C-A'

    def action(self, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        viewer=self.frame.getActiveMajorMode()
        if viewer:
            s=viewer.stc
            pos = s.GetCurrentPos()
            col = s.GetColumn(pos)
            s.GotoPos(pos-col)
        

class EndOfLine(SelectAction):
    name = "Cursor to End of Line"
    tooltip = "Move the cursor to the end of the current line"
    keyboard = 'C-E'

    def action(self, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        viewer=self.frame.getActiveMajorMode()
        if viewer:
            s=viewer.stc
            line = s.GetCurrentLine()
            s.GotoPos(s.GetLineEndPosition(line))


class WordOrRegionMutate(SelectAction):
    """No-op base class to operate on a word or the selected region.
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
            s.CmdKeyExecute(stc.STC_CMD_WORDRIGHT)
            end = s.GetCurrentPos()
        word = s.GetTextRange(pos, end)
        s.SetTargetStart(pos)
        s.SetTargetEnd(end)
        s.ReplaceTarget(self.mutate(word))
        s.EndUndoAction()
        s.GotoPos(end)

    def action(self, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        viewer=self.frame.getActiveMajorMode()
        if viewer:
            self.mutateSelection(viewer.stc)
            
class CapitalizeWord(WordOrRegionMutate):
    """Title-case the current word and move the cursor to the start of
    the next word.
    """

    name ="Capitalize word"
    tooltip = "Capitalize current word"
    keyboard = 'M-C'

    def mutate(self, txt):
        """Change to title case -- first letter capitalized, rest
        lower case.
        """
        return txt.title()

class UpcaseWord(WordOrRegionMutate):
    """Upcase the current word and move the cursor to the start of the
    next word.
    """

    name ="Upcase word"
    tooltip = "Upcase current word"
    keyboard = 'M-U'

    def mutate(self, txt):
        """Change to all upper case.
        """
        return txt.upper()

class DowncaseWord(WordOrRegionMutate):
    """Downcase the current word and move the cursor to the start of the
    next word.
    """

    name ="Downcase word"
    tooltip = "Downcase current word"
    keyboard = 'M-L'

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
        if charBefore and chr(charBefore) in "[]{}()" and styleBefore == stc.STC_P_OPERATOR:
            braceAtCaret = caretPos - 1

        # check after
        if braceAtCaret < 0:
            charAfter = s.GetCharAt(caretPos)
            styleAfter = s.GetStyleAt(caretPos)

            if charAfter and chr(charAfter) in "[]{}()" and styleAfter == stc.STC_P_OPERATOR:
                braceAtCaret = caretPos

        if braceAtCaret >= 0:
            braceOpposite = s.BraceMatch(braceAtCaret)

        if braceAtCaret != -1  and braceOpposite == -1:
            s.BraceBadLight(braceAtCaret)
        else:
            s.BraceHighlight(braceAtCaret, braceOpposite)
        


class StandardIndentMixin(object):
    def indent(self, incr):
        """Indent or unindent a region.

        Indent (or unindent) a region.  The absolute value of the incr
        parameter is the number of tab stops to indent (or unindent).
        Source code started life from pype.PythonSTC.Dent(); modified
        by me.

        It is assumed that this is to be mixin in to a FundamentalMode
        subclass.

        @param incr: integer indicating multiplier and direction of
        indent: >0 indents, <0 removes indentation
        """
        s = self.stc
        
        self.dprint("indenting by %d" % incr)
        incr *= s.GetIndent()
        self.dprint("indenting by %d" % incr)
        s.BeginUndoAction()
        lnstart, lnend = s.GetLineRegion()
        try:
            for ln in xrange(lnstart, lnend+1):
                count = s.GetLineIndentation(ln)
                m = (count+incr)
                m += cmp(0, incr)*(m%incr)
                m = max(m, 0)
                s.SetLineIndentation(ln, m)
        finally:
            s.EndUndoAction()


class ShiftLeft(MajorAction):
    name = "Shift &Left"
    tooltip = "Unindent a line region"
    icon = 'icons/text_indent_remove_rob.png'
    keyboard = 'S-TAB'

    def majoraction(self, mode, pos=-1):
        if hasattr(mode, 'indent') and mode.indent is not None:
            mode.indent(-1)

class ShiftRight(MajorAction):
    name = "Shift &Right"
    tooltip = "Indent a line or region"
    icon = 'icons/text_indent_rob.png'
    keyboard = 'TAB'

    def majoraction(self, mode, pos=-1):
        if hasattr(mode, 'indent') and mode.indent is not None:
            mode.indent(1)



class StandardCommentMixin(debugmixin):
    def comment(self, add=True):
        """Comment or uncomment a region.

        Comment or uncomment a region.

        @param add: True to add comments, False to remove them
        """
        s = self.stc
        
        s.BeginUndoAction()
        line, lineend = s.GetLineRegion()
        self.dprint("lines: %d - %d" % (line, lineend))
        try:
            selstart, selend = s.GetSelection()
            self.dprint("selection: %d - %d" % (selstart, selend))

            start = selstart
            end = s.GetLineEndPosition(line)
            while line <= lineend:
                start = self.commentLine(start, end)
                line += 1
                end = s.GetLineEndPosition(line)
            s.SetSelection(selstart, start - s.eol_len)
        finally:
            s.EndUndoAction()

class CommentRegion(MajorAction):
    name = "&Comment Region"
    tooltip = "Comment a line or region"
    icon = 'icons/text_indent_rob.png'
    keyboard = 'C-C C-C'

    def majoraction(self, mode, pos=-1):
        if hasattr(mode, 'comment') and mode.comment is not None:
            mode.comment(True)


class ElectricReturn(MajorAction):
    name = "Electric Return"
    tooltip = "Indent the next line following a return"
    icon = 'icons/text_indent_rob.png'
    keyboard = 'RET'

    def majoraction(self, viewer, pos=-1):
        viewer.electricReturn()




class FundamentalMode(MajorMode, BraceHighlightMixin, StandardIndentMixin,
                      StandardCommentMixin):
    """
    The base view of most (if not all) of the views that use the STC
    to directly edit the text.  Views (like the HexEdit view or an
    image viewer) that only use the STC as the backend storage are
    probably not based on this view.
    """
    keyword='Fundamental'
    regex=".*"

    start_line_comment = ''
    end_line_comment = ''

    # increment after every style change
    style_number = 0

    default_settings = {
        'tab_size': 4,
        'line_numbers': True,
        'line_number_margin_width': 40,
        'symbols': False,
        'symbols_margin_width': 16,
        'folding': False,
        'folding_margin_width': 16,
        'word_wrap': False,
        'sample_file': "Fundamental mode is the base for all other modes that use the STC to view text.",
        'has_stc_styling': True,
        'stc_lexer': wx.stc.STC_LEX_NULL,
        'stc_keywords': "",
        'stc_boa_braces': "{}",
        'stc_boa_style_names': {},
        'stc_lexer_styles': {},

        # Note: 1 tends to be the comment style, but not in all cases.
        'stc_lexer_default_styles': {0: '',
                                     1: 'fore:%(comment-col)s,italic',
                                     wx.stc.STC_STYLE_DEFAULT: 'face:%(mono)s,size:%(size)d',
                                     wx.stc.STC_STYLE_LINENUMBER: 'face:%(ln-font)s,size:%(ln-size)d',
                                     
                                     wx.stc.STC_STYLE_BRACEBAD: '',
                                     wx.stc.STC_STYLE_BRACELIGHT: '',
                                     wx.stc.STC_STYLE_CONTROLCHAR: '',
                                     wx.stc.STC_STYLE_INDENTGUIDE: '',
                                     }
        }
    
    def createEditWindow(self,parent):
        self.dprint("creating new Fundamental window")
        self.createSTC(parent)
        win=self.stc
        win.Bind(wx.EVT_KEY_DOWN, self.frame.OnKeyPressed)
        return win

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
        self.stc=MySTC(parent,refstc=self.buffer.stc)
        self.format=os.linesep
        self.current_style = self.__class__.style_number

        self.applyDefaultSettings()
        if self.styleSTC():
            self.settings.has_stc_styling = True
        else:
            # If the style file fails to load, it probably means that
            # the style definition doesn't exist in the style file.
            # So, add the default style settings supplied by the major
            # mode to the file and try again.
            self.styleDefault()
            if self.styleSTC():
                self.settings.has_stc_styling = True
            else:
                # If the file still doesn't load, fall back to a style
                # that hopefully does exist.  The boa stc styling
                # dialog won't be available.
                self.settings.has_stc_styling = False
                self.styleSTC('text')

    def createWindowPostHook(self):
        # SetIndent must be called whenever a new document is loaded
        # into the STC
        self.stc.SetIndent(self.settings.tab_size)
        #self.dprint("indention=%d" % self.stc.GetIndent())

        self.stc.SetIndentationGuides(1)

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
        if not self.settings.stc_lexer:
            dprint("no STC styling information for major mode %s" % self.keyword)
            return
        boa.updateConfigFile(self.frame.app, self)

    def applyDefaultSettings(self):
        # turn off symbol margin
        if self.settings.symbols:
            self.stc.SetMarginWidth(1, self.settings.symbols_margin_width)
        else:
            self.stc.SetMarginWidth(1, 0)

        # turn off folding margin
        if self.settings.folding:
            self.stc.SetMarginWidth(2, self.settings.folding_margin_width)
        else:
            self.stc.SetMarginWidth(2, 0)

        self.setWordWrap()
        self.setLineNumbers()

    def setWordWrap(self,enable=None):
        if enable is not None:
            self.settings.word_wrap=enable
        if self.settings.word_wrap:
            self.stc.SetWrapMode(stc.STC_WRAP_CHAR)
            self.stc.SetWrapVisualFlags(stc.STC_WRAPVISUALFLAG_END)
        else:
            self.stc.SetWrapMode(stc.STC_WRAP_NONE)

    def setLineNumbers(self,enable=None):
        if enable is not None:
            self.settings.line_numbers=enable
        if self.settings.line_numbers:
            self.stc.SetMarginType(0, stc.STC_MARGIN_NUMBER)
            self.stc.SetMarginWidth(0,  self.settings.line_number_margin_width)
        else:
            self.stc.SetMarginWidth(0,0)

    def styleSTC(self, lang=None):
        """Style the STC using the information in the styling config file.

        Call the boa method of styling the stc that reads the styling
        information (including the lexer type) out of its format
        config file.

        @param lang: language keyword to look up in the file
        """
        self.current_style = self.__class__.style_number

        config=boa.getUserConfigFile(self.frame.app)
        if lang is None:
            lang = self.keyword
            
        try:
            boa.initSTC(self.stc, config, lang)
        except SyntaxError:
            dprint("no STC style defined for %s" % lang)
            return False
        return True

    def changeStyle(self):
        """Change the style of this mode and all others like it"""

        self.__class__.style_number += 1
        self.styleSTC()

    def focusPostHook(self):
        if self.current_style != self.__class__.style_number:
            self.styleSTC()

    def OnUpdateUIHook(self, evt):
        self.braceHighlight()

    def commentLine(self, start, end):
        """Add comment to the line specified by start and end.

        Generic method that uses the start_line_comment and
        end_line_comment class attributes to comment a line.  This is
        to be called within a loop that adds comment characters to the
        line.  start and end are assumed to be the endpoints of the
        current line, so no further checking of the line is necessary.

        @param start: first character in line
        @param end: last character in line before line ending

        @returns: new position of last character before line ending
        """
        self.dprint("commenting %d - %d: '%s'" % (start, end, self.stc.GetTextRange(start,end)))
        slen = len(self.start_line_comment)
        self.stc.InsertText(start, self.start_line_comment)
        end += slen

        elen = len(self.end_line_comment)
        if elen > 0:
            self.stc.InsertText(end, self.start_line_comment)
            end += elen
        return end + self.stc.eol_len

    def electricReturn(self):
        """
        Indent the next line to the appropriate level.  This is called
        instead of letting the STC handle a return press on its own.
        """
        pass



class FundamentalPlugin(MajorModeMatcherBase,debugmixin):
    implements(IMajorModeMatcher)
    implements(IMenuItemProvider)
    implements(IToolBarItemProvider)
    implements(IKeyboardItemProvider)
    
    def scanMagic(self,buffer):
        """
        If the buffer looks like it is a text file, flag it as a
        potential Fundamental.
        """
        if not buffer.guessBinary:
            return MajorModeMatch(FundamentalMode,generic=True)
        return None

    default_menu=((None,None,Menu("Test").after("Minor Mode")),
                  (None,"Test",MenuItem(OpenFundamental).first()),
                  ("Fundamental","Edit",MenuItem(WordWrap)),
                  ("Fundamental","Edit",MenuItem(LineNumbers)),
                  ("Fundamental","Edit",MenuItem(FindText)),
                  ("Fundamental","Edit",MenuItem(ReplaceText)),
                  ("Fundamental","Edit",MenuItem(GotoLine)),
                  ("Fundamental",None,Menu("Cmds").after("Edit")),
                  ("Fundamental","Cmds",MenuItem(ShiftLeft)),
                  ("Fundamental","Cmds",MenuItem(ShiftRight)),
                  ("Fundamental","Cmds",Separator("shift").last()),
                  ("Fundamental","Cmds",MenuItem(CommentRegion)),
                  )
    def getMenuItems(self):
        for mode,menu,item in self.default_menu:
            yield (mode,menu,item)

    default_tools=(("Fundamental",None,Menu("Cmds").after("Major Mode")),
                   ("Fundamental","Cmds",MenuItem(ShiftLeft)),
                   ("Fundamental","Cmds",MenuItem(ShiftRight)),
                   )
    def getToolBarItems(self):
        for mode,menu,item in self.default_tools:
            yield (mode,menu,item)

    default_keys=(("Fundamental",BeginningOfLine),
                  ("Fundamental",EndOfLine),
                  ("Fundamental",CapitalizeWord),
                  ("Fundamental",UpcaseWord),
                  ("Fundamental",DowncaseWord),
                  )
    def getKeyboardItems(self):
        for mode,action in self.default_keys:
            yield (mode,action)


if __name__ == "__main__":
    app=testapp(0)
    frame=RootFrame(app.main)
    frame.Show(True)
    app.MainLoop()

