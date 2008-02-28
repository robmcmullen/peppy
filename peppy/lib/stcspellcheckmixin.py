#-----------------------------------------------------------------------------
# Name:        stcspellcheckmixin.py
# Purpose:     Spell checking mixin for the wx.StyledTextControl using pyenchant
#
# Author:      Rob McMullen
#
# Created:     2008
# RCS-ID:      $Id: $
# Copyright:   (c) 2008 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
#
# Originally based on code from Luke-SDK, which includes the following
# copyright notice:
# 
# Copyright (c) 2007 Eur Ing Christopher Thoday, cthoday@mail.berlios.de.
#
# Permission to use, copy, modify and distribute this software and its
# documentation for any purpose and without fee is hereby granted, provided
# that the above copyright notice appear in all copies and that both
# the copyright notice and this permission notice appear in supporting
# documentation.
#
# Christopher Thoday makes no representations about the suitability of this
# software for any purpose.  It is provided "as is" without express or implied
# warranty.

"""Spell checking mixin for the wx.StyledTextControl using pyenchant

This module was insipred by the spell check function from Christopher Thoday's
U{Luke SDK<http://luke-sdk.berlios.de/>}.

Spell checking is provided by the pyenchant library, which is an external
dependency not part of wxPython.  Packages are available for Mac, Unix, and
windows at U{http://pyenchant.sourceforge.net}

Currently provides:
 - spell checking of entire buffer, currently visible page, or selection region
 - user specified indicator number (0 - 2), style, and color
 - language can be changed on the fly
 - update the spelling as you type
 - check the document in either idle time or in a background thread

@author: Rob McMullen
@version: 1.0

Changelog::
    1.0:
        - First public release
    1.1:
        - Added helper function to use idle processing time to check document
        - Added word checking function for use in instant spell checking
"""

import locale
import wx
import wx.stc
try:
    import enchant
except ImportError:
    pass

class STCSpellCheckMixin(object):
    """Spell checking mixin for use with wx.StyledTextControl.
    
    This mixin shows spelling errors using the styling indicators (e.g.  the
    red squiggly underline) of the styled text control; I find this much more
    convenient than a dialog-box that makes you click through each mistake.
    
    The eventual goal of the module is to provide on-the-fly spell checking
    that will display errors as you type, and also will highlight errors
    during idle time or in a background thread.
    
    This mixin provides spell checking using the pyenchant module.  Without
    pyenchant, this mixin won't do anything useful, but it is still safe to
    be mixed in.  It wraps all calls to pyenchant with try/except blocks to
    catch import errors, and any calls to the spell checking functions will
    return immediately.
    
    In your code that uses this mixin, be sure to call the mixin's constructor
    with code like::
    
        class MySTC(STCSpellCheckMixin, wx.stc.StyledTextCtrl):
            def __init__(self, *args, **kwargs):
                wx.stc.StyledTextCtrl.__init__(self, *args, **kwargs)
                STCSpellingMixin.__init__(self)

    To use the spelling check, use one of the methods L{spellCheckAll},
    L{spellCheckCurrentPage}, or L{spellCheckSelection}.  Clear the spelling
    indicators with L{spellClearAll}.
    """
    def __init__(self, *args, **kwargs):
        """Mixin must be initialized using this constructor.
        
        Keyword arguments are also available instead of calling the
        convenience functions.  For L{spellSetIndicator}, use C{indicator},
        C{indicator_color}, and {indicator_style}; for L{spellSetLanguage},
        use C{language}; and for L{spellSetMinimumWordSize}, use
        C{min_word_size}.  See the descriptions of those methods for more info.
        """
        self.spellSetIndicator(kwargs.get('indicator', 2),
                                  kwargs.get('indicator_color', "#FF0000"),
                                  kwargs.get('indicator_style', wx.stc.STC_INDIC_SQUIGGLE))
        self.spellSetLanguage(kwargs.get('language', "en_US"))
        self.spellSetMinimumWordSize(kwargs.get('min_word_size', 3))
        self._spelling_debug = False
        self._spelling_last_idle_line = -1

    def spellSetIndicator(self, indicator=None, color=None, style=None):
        """Set the indicator styling for misspelled words.
        
        Set the indicator index to use, its color, and the visual style.
        
        @param indicator: indicator number (usually 0, 1, or 2, but may be fewer
        depending on the number of style bits you've chosen for the stc.)
        @param color: string indicating the color of the indicator (e.g.
        "#FF0000" for red)
        @param style: stc indicator style; one of the wx.stc.STC_INDIC_*
        constants (currently wx.stc.STC_INDIC_PLAIN, wx.stc.STC_INDIC_SQUIGGLE,
        wx.stc.STC_INDIC_TT, wx.stc.STC_INDIC_DIAGONAL,
        wx.stc.STC_INDIC_STRIKE, wx.stc.STC_INDIC_HIDDEN,
        wx.stc.STC_INDIC_BOX, wx.stc.STC_INDIC_ROUNDBOX)
        """
        indicators = {0: wx.stc.STC_INDIC0_MASK,
                      1: wx.stc.STC_INDIC1_MASK,
                      2: wx.stc.STC_INDIC2_MASK
                      }
        if indicator is not None:
            if indicator not in indicators:
                indicator = 0
            # The current view may have fewer than 3 indicators
            bitmax = 7 - self.GetStyleBits()
            if indicator > bitmax:
                indicator = bitmax
            self._spelling_indicator = indicator
        self._spelling_indicator_mask = indicators[self._spelling_indicator]
        
        if color is not None:
            self._spelling_color = color
        self.IndicatorSetForeground(self._spelling_indicator,
                                    self._spelling_color)
    
        if style is not None:
            if style > wx.stc.STC_INDIC_MAX:
                style = wx.stc.STC_INDIC_MAX
            self._spelling_style = style
        self.IndicatorSetStyle(self._spelling_indicator,
                               self._spelling_style)
    
    @classmethod
    def spellGetAvailableLanguages(cls):
        """Return a list of supported languages.
        
        Pyenchant supplies a list of its supported languages, so this is just
        a simple wrapper around its C{list_languages} function.  Each item in
        the list is a text string indicating the locale name, e.g.  en_US, ru,
        ru_RU, eo, es_ES, etc.
        
        @return: a list of text strings indicating the supported languages
        """
        try:
            return enchant.list_languages()
        except NameError:
            pass
        return []
    
    def spellSetLanguage(self, lang):
        """Set the language for spelling check.
        
        The string should be in language locale format, e.g.  en_US, ru, ru_RU,
        eo, es_ES, etc.  See L{spellGetAvailableLanguages}.
        
        @param lang: text string indicating the language
        """
        self._spelling_lang = lang
    
    def spellSetMinimumWordSize(self, size):
        """Set the minimum word size that will be looked up in the dictionary.
        
        Words smaller than this size won't be spell checked.
        """
        self._spelling_word_size = size
    
    def spellGetDict(self):
        """Get a dictionary.
        
        Using the language specified in L{spellSetLanguage}, return a
        pyenchant dictionary instance that can be used to check spelling.
        
        Currently, no caching is used -- it returns a new dictionary object
        every time this method is called.
        
        @return: pyenchant dictionary if a valid one was found for the current
        language, or None if there is no dictionary for the language.
        """
        try:
            return enchant.Dict(self._spelling_lang)
        except NameError:
            pass
        return None
    
    def spellClearAll(self):
        """Clear the stc of all spelling indicators."""
        self.StartStyling(0, self._spelling_indicator_mask)
        self.SetStyling(self.GetLength(), 0)
    
    def spellCheckRange(self, start, end):
        """Perform a spell check over a range of text in the document.
        
        This is the main spell checking routine -- it loops over the range
        of text using the L{spellFindNextWord} method to break the text into
        words to check.  Misspelled words are highlighted using the current
        indicator.
        
        @param start: starting position
        @param end: last position to check
        """
        spell = self.spellGetDict()
        if not spell:
            return
        
        # Remove any old spelling indicators
        mask = self._spelling_indicator_mask
        self.StartStyling(start, mask)
        self.SetStyling(end - start, 0)
        
        text = self.GetTextRange(start, end) # note: returns unicode
        unicode_index = 0
        max_index = len(text)
        
        last_index = 0 # last character in text a valid raw byte position
        last_pos = start # raw byte position corresponding to last_index
        while unicode_index < max_index:
            start_index, end_index = self.spellFindNextWord(text, unicode_index, max_index)
            if end_index >= 0:
                if end_index - start_index >= self._spelling_word_size:
                    if self._spelling_debug:
                        print("checking %s at text[%d:%d]" % (repr(text[start_index:end_index]), start_index, end_index))
                    if not spell.check(text[start_index:end_index]):
                        # Because unicode characters are stored as utf-8 in the
                        # stc and the positions in the stc correspond to the
                        # raw bytes, not the number of unicode characters, we
                        # have to find out the offset to the unicode chars in
                        # terms of raw bytes.
                        
                        # find the number of raw bytes from the last calculated
                        # styling position to the start of the word
                        last_pos += len(text[last_index:start_index].encode('utf-8'))
                        
                        # find the length of the word in raw bytes
                        raw_count = len(text[start_index:end_index].encode('utf-8'))
                        
                        if self._spelling_debug:
                            print("styling position corresponding to text[%d:%d] = (%d,%d)" % (start_index, end_index, last_pos, last_pos + raw_count))
                        if self.spellIsSpellCheckRegion(last_pos):
                            self.StartStyling(last_pos, mask)
                            self.SetStyling(raw_count, mask)
                        last_pos += raw_count
                        last_index = end_index
                unicode_index = end_index
            else:
                break

    def spellCheckAll(self):
        """Perform a spell check on the entire document."""
        return self.spellCheckRange(0, self.GetLength())
    
    def spellCheckSelection(self):
        """Perform a spell check on the currently selected region."""
        return self.spellCheckRange(self.GetSelectionStart(), self.GetSelectionEnd())
    
    def spellCheckLines(self, startline=-1, count=-1):
        """Perform a spell check on group of lines.
        
        Given the starting line, check the spelling on a block of lines.  If
        the number of lines in the block is not specified, use the number of
        currently visibile lines.
        
        @param startline: current line, or -1 to use the first visible line
        @param count: number of lines in the block, or -1 to use the number of
        lines visible on screen
        """
        if startline < 0:
            startline = self.GetFirstVisibleLine()
        start = self.PositionFromLine(startline)
        if count < 0:
            count = self.LinesOnScreen()
        endline = startline + count
        if endline > self.GetLineCount():
            endline = self.GetLineCount() - 1
        end = self.GetLineEndPosition(endline)
        if self._spelling_debug:
            print("Checking lines %d-%d, chars %d=%d" % (startline, endline, start, end))
        return self.spellCheckRange(start, end)
    
    def spellCheckCurrentPage(self):
        """Perform a spell check on the currently visible lines."""
        return self.spellCheckLines()
    
    def spellFindNextWord(self, utext, index, length):
        """Find the next valid word to check.
        
        Designed to be overridden in subclasses, this method takes a starting
        position in an array of text and returns a tuple indicating the next
        valid word in the string.
        
        @param utext: array of unicode chars
        @param i: starting index within the array to search
        @param length: length of the text
        @return: tuple indicating the word start and end indexes, or (-1, -1)
        indicating that the end of the array was reached and no word was found
        """
        while index < length:
            if utext[index].isalpha():
                end = index + 1
                while end < length and utext[end].isalpha():
                    end += 1
                return (index, end)
            index += 1
        return (-1, -1)
    
    def spellIsSpellCheckRegion(self, pos):
        """Is the position in a region of the document that should be spell-
        checked?
        
        @return: True if the position should be spell-checked; False if it
        doesn't make sense to spell check that part of the document
        """
        return True
    
    def spellStartIdleProcessing(self):
        """Initialize parameters needed for idle block spell checking.
        
        This must be called before the first call to L{spellProcessIdleBlock}
        or if you wish to restart the spell checking from the start
        of the document.  It initializes parameters needed by the
        L{spellProcessIdleBlock} in order to process the document during idle
        time.
        """
        self._spelling_last_idle_line = 0
        
    def spellProcessIdleBlock(self):
        """Process a block of lines during idle time.
        
        This method is designed to be called during idle processing and will
        spell checks a small number of lines.  The next idle processing event
        will continue from where the previous call left off, and in this way
        over some number of idle events will spell check the entire document.
        
        Once the entire document is spell checked, a flag is set and
        further calls to this method will immediately return.  Calling
        L{spellStartIdleProcessing} will cause the idle processing to start
        checking from the beginning of the document.
        """
        if self._spelling_last_idle_line < 0:
            return
        if self._spelling_debug:
            print("Idle processing page starting at line %d" % self._spelling_last_idle_line)
        self.spellCheckLines(self._spelling_last_idle_line)
        self._spelling_last_idle_line += self.LinesOnScreen()
        if self._spelling_last_idle_line > self.GetLineCount():
            self._spelling_last_idle_line = -1
            return False
        return True

    def spellGetSuggestions(self, word):
        """Get suggestion for the correct spelling of a word.
        
        @param word: word to check
        
        @return: list of suggestions, or an empty list if any of the following
        are true: there are no suggestions, the word is shorter than the
        minimum length, or the dictionary can't be found.
        """
        spell = self.spellGetDict()
        if spell and len(word) >= self._spelling_word_size:
            words = spell.suggest(word)
            if self._spelling_debug:
                print("suggestions for %s: %s" % (word, words))
            return words
        return []
    
    def spellCheckWord(self, pos=None):
        """Check the word at the current or specified position.
        
        @param pos: position of a character in the word (or at the start or end
        of the word), or None to use the current position
        """
        if pos is None:
            pos = self.GetCurrentPos()
        end = self.WordEndPosition(pos, True)
        start = self.WordStartPosition(pos, True)
        if self._spelling_debug:
            print("%d-%d: %s" % (start, end, self.GetTextRange(start, end)))
        self.spellCheckRange(start, end)


if __name__ == "__main__":
    import sys
    try:
        import enchant
    except:
        print("pyenchant not available, so spelling correction won't work.")
        print("Get pyenchant from http://pyenchant.sourceforge.net")
    
    class TestSTC(STCSpellCheckMixin, wx.stc.StyledTextCtrl):
        def __init__(self, *args, **kwargs):
            wx.stc.StyledTextCtrl.__init__(self, *args, **kwargs)
            STCSpellCheckMixin.__init__(self)
            self.SetMarginType(0, wx.stc.STC_MARGIN_NUMBER)
            self.SetMarginWidth(0, 32)
            self.word_end_chars = ' .!?\'\"'
            self.Bind(wx.EVT_CHAR, self.OnChar)

        def OnChar(self, evt):
            """Handle all events that result from typing characters in the stc.
            
            Automatic spell checking is handled here.
            """
            uchar = unichr(evt.GetKeyCode())
            if uchar in self.word_end_chars:
                self.spellCheckWord()
            evt.Skip()
    
    class Frame(wx.Frame):
        def __init__(self, *args, **kwargs):
            super(self.__class__, self).__init__(*args, **kwargs)

            self.stc = TestSTC(self, -1)

            self.CreateStatusBar()
            menubar = wx.MenuBar()
            self.SetMenuBar(menubar)  # Adding the MenuBar to the Frame content.
            menu = wx.Menu()
            menubar.Append(menu, "File")
            self.menuAdd(menu, "Open", "Open File", self.OnOpenFile)
            self.menuAdd(menu, "Quit", "Exit the pragram", self.OnQuit)
            menu = wx.Menu()
            menubar.Append(menu, "Edit")
            self.menuAdd(menu, "Check All", "Spell check the entire document", self.OnCheckAll)
            self.menuAdd(menu, "Check Current Page", "Spell check the currently visible page", self.OnCheckPage)
            self.menuAdd(menu, "Check Selection", "Spell check the selected region", self.OnCheckSelection)
            menu.AppendSeparator()
            self.menuAdd(menu, "Clear Spelling", "Remove spelling correction indicators", self.OnClearSpelling)
            menu = wx.Menu()
            menubar.Append(menu, "Language")
            langs = self.stc.spellGetAvailableLanguages()
            self.lang_id = {}
            for lang in langs:
                id = wx.NewId()
                self.lang_id[id] = lang
                self.menuAdd(menu, lang, "Change dictionary to %s" % lang, self.OnChangeLanguage, id=id)


        def loadFile(self, filename):
            fh = open(filename)
            self.stc.SetText(fh.read())
            self.stc.spellCheckCurrentPage()
        
        def loadSample(self, paragraphs=10):
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
            self.stc.ClearAll()
            for i in range(paragraphs):
                self.stc.AppendText(lorem_ipsum)
            # Call the spell check after the text has had a chance to be
            # displayed and the window resized to the correct size.
            wx.CallAfter(self.stc.spellCheckCurrentPage)

        def menuAdd(self, menu, name, desc, fcn, id=-1, kind=wx.ITEM_NORMAL):
            if id == -1:
                id = wx.NewId()
            a = wx.MenuItem(menu, id, name, desc, kind)
            menu.AppendItem(a)
            wx.EVT_MENU(self, id, fcn)
            menu.SetHelpString(id, desc)
        
        def OnOpenFile(self, evt):
            dlg = wx.FileDialog(self, "Choose a text file",
                               defaultDir = "",
                               defaultFile = "",
                               wildcard = "*")
            if dlg.ShowModal() == wx.ID_OK:
                print("Opening %s" % dlg.GetPath())
                self.loadFile(dlg.GetPath())
            dlg.Destroy()
        
        def OnQuit(self, evt):
            self.Close(True)
        
        def OnCheckAll(self, evt):
            self.stc.spellCheckAll()
        
        def OnCheckPage(self, evt):
            self.stc.spellCheckCurrentPage()
        
        def OnCheckSelection(self, evt):
            self.stc.spellCheckSelection()
        
        def OnClearSpelling(self, evt):
            self.stc.spellClearAll()
        
        def OnChangeLanguage(self, evt):
            id = evt.GetId()
            normalized = locale.normalize(self.lang_id[id])
            try:
                locale.setlocale(locale.LC_ALL, normalized)
                print("Changing locale %s, dictionary set to %s" % (normalized, self.lang_id[id]))
            except locale.Error:
                print("Can't set python locale to %s; dictionary set to %s" % (normalized, self.lang_id[id]))
            self.stc.spellSetLanguage(self.lang_id[id])
            self.stc.spellClearAll()
            self.stc.spellCheckCurrentPage()

    app = wx.App(False)
    frame = Frame(None)
    if len(sys.argv) > 1:
        frame.loadFile(sys.argv[-1])
    else:
        frame.loadSample()
    frame.Show()
    app.MainLoop()
