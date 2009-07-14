# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os, shutil, time, new, re

import wx
import wx.stc
from wx.lib.pubsub import Publisher

from peppy.actions import *
from peppy.actions.base import *
from peppy.actions.minibuffer import *
from peppy.fundamental import *
from peppy.lib.userparams import *
from peppy.lib.textutil import *


class RecordedTextAction(RecordedAction):
    def __init__(self, actioncls, text):
        self.actioncls = actioncls
        self.text = text
    
    def __str__(self):
        return "%s: %s" % (self.actioncls.__name__, self.text)
    
    def performAction(self, system_state):
        action = self.actioncls(system_state.frame, mode=system_state.mode)
        dprint(action.__class__.__name__)
        action.actionString(self.text)
    
    def getScripted(self):
        return "%s(frame, mode=mode).actionString(%s)" % (self.actioncls.__name__, repr(self.text))


class CoalesceTextMacroMixin(object):
    @classmethod
    def canCoalesce(cls, actioncls):
        return hasattr(actioncls, 'getRecordableText')
    
    @classmethod
    def coalesce(self, first, second):
        first_text = first.actioncls.getRecordableText(first)
        second_text = second.actioncls.getRecordableText(second)
        text = first_text + second_text
        record = RecordedTextAction(SelfInsertString, text)
        return record
    
    @classmethod
    def getRecordableText(cls, recorded_action):
        """Used by action coalescing to return the text that would have been
        inserted.
        
        If this method is present, the action will be able to be coalesced with
        any text insertions from SelfInsertCommand.
        """
        raise NotImplementedError


class SelfInsertString(CoalesceTextMacroMixin, MacroAction):
    """Macro action used to coalesce multiple L{SelfInsertCommand} actions
    into a single action.
    
    The use of this coalescing action saves space and time in the replay and
    serialization of the actions.
    """
    def actionString(self, text):
        # See hacks described in SelfInsertCommand.actionKeystroke
        mode = self.mode
        if mode.GetSelectionStart() != mode.GetSelectionEnd():
            mode.ReplaceSelection("")
        mode.AddText(text)
        mode.EnsureCaretVisible()
        mode.CmdKeyExecute(wx.stc.STC_CMD_CHARLEFT)
        mode.CmdKeyExecute(wx.stc.STC_CMD_CHARRIGHT)
    
    @classmethod
    def getRecordableText(cls, recorded_action):
        """Used by action coalescing to return the text that would have been
        inserted.
        
        If this method is present, the action will be able to be coalesced with
        any text insertions from SelfInsertCommand.
        """
        # The text for the SelfInsertString is stored 
        return recorded_action.text


class SelfInsertCommand(CoalesceTextMacroMixin, TextModificationAction):
    """Default action to insert the character that was typed"""
    name = "Self Insert Command"
    key_bindings = {'default': 'default',}
    
    def actionKeystroke(self, evt, multiplier=1, **kwargs):
        mode = self.mode
        uchar = unichr(evt.GetUnicodeKey())
        if mode.spell and mode.classprefs.spell_check and uchar in mode.word_end_chars:
            # We are catching the event before the character is added to the
            # text, so we know the cursor is at the end of the word.
            mode.spell.checkWord(atend=True)
        #dprint("char=%s, unichar=%s, multiplier=%s, text=%s" % (evt.GetKeyCode(), evt.GetUnicodeKey(), multiplier, uchar))
        
        # To make the undo coalescing work correctly, first have to replace
        # the selection with an empty string and then add the text.  Multiple
        # ReplaceSelections don't coalesce with each other, meaning that
        # it takes an undo for each character inserted rather than a single
        # undo for all the text that has been typed without repositioning
        # the cursor.  I don't know how to force ReplaceSelection calls to
        # coalesce using the python interface to scintilla.
        if mode.GetSelectionStart() != mode.GetSelectionEnd():
            mode.ReplaceSelection("")
        
        # Can't just use AddText to insert the characters, because apparently
        # some internal scintilla cursor command isn't updated unless
        # evt.Skip is called -- the Scintilla cursor movement commands like
        # STC_CMD_LINEDOWN think that the cursor is still on the position
        # where the cursor began the undo action.  So, unless the special
        # case of inserting a quoted character is found, we use a hack of
        # adding a string of one less than the characters typed and letting
        # the evt.Skip add the last one, thereby allowing the internal cursor
        # position to be updated.
        if hasattr(evt, 'is_quoted'):
            text = uchar * multiplier
            mode.AddText(text)
            mode.EnsureCaretVisible()
            # This hack to move the cursor left then right causes the internal
            # cursor position to be updated so that subsequent cursor up or
            # down commands works correctly.
            mode.CmdKeyExecute(wx.stc.STC_CMD_CHARLEFT)
            mode.CmdKeyExecute(wx.stc.STC_CMD_CHARRIGHT)
        else:
            if multiplier > 1:
                text = uchar * (multiplier - 1)
                mode.AddText(text)
                mode.EnsureCaretVisible()
            evt.Skip()
    
    @classmethod
    def getRecordableText(cls, recorded_action):
        evt = recorded_action.evt
        uchar = unichr(evt.GetUnicodeKey())
        text = uchar * recorded_action.multiplier
        return text




class SpellingSuggestionAction(ListAction):
    """Spelling suggestions for the current word
    
    Used in popup menus to provide a list of alternate spellings of the word
    under the cursor
    """
    name = "Spelling..."
    inline = True
    menumax = 5

    def getItems(self):
        # Because this is a popup action, we can save stuff to this object.
        # Otherwise, we'd save it to the major mode
        if self.mode.spell:
            self.words = self.mode.spell.getSuggestions(self.mode.check_spelling[0])
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

class ClassprefsTooltipMixin(object):
    def getTooltip(self, id=None, name=None):
        if self.tooltip is None:
            param = self.mode.classprefsFindParam(self.local_setting)
            self.__class__.tooltip = unicode(_(param.help))
        return self.tooltip

class FundamentalSettingToggleMixin(ClassprefsTooltipMixin):
    """Abstract class used to implement a toggle button for a setting of
    FundamentalMode.
    """
    local_setting = None

    def isChecked(self):
        return getattr(self.mode.locals, self.local_setting)
    
    def action(self, index=-1, multiplier=1):
        value = self.isChecked()
        setattr(self.mode.locals, self.local_setting, not value)
        self.mode.applyDefaultSettings()

class FundamentalRadioMixin(ClassprefsTooltipMixin):
    """Abstract class used to implement a set of radio buttons for a setting of
    FundamentalMode.
    """
    local_setting = None
    text_list = None
    value_list = None

    def getValue(self):
        return getattr(self.mode.locals, self.local_setting)
    
    def getChoices(self):
        param = self.mode.classprefsFindParam(self.local_setting)
        cls = self.__class__
        cls.text_list = param.choices
        if hasattr(param, 'index_to_value'):
            # handle IndexChoiceParam
            cls.value_list = [param.index_to_value[i] for i in range(len(param.choices))]
        else:
            # handle KeyedIndexChoiceParam
            cls.value_list = param.keys

    def getIndex(self):
        if self.text_list is None:
            self.getChoices()
        return self.value_list.index(self.getValue())
                                           
    def getItems(self):
        if self.text_list is None:
            self.getChoices()
        return self.text_list

    def action(self, index=-1, multiplier=1):
        value = self.value_list[index]
        setattr(self.mode.locals, self.local_setting, value)
        self.mode.applyDefaultSettings()

class FundamentalBooleanRadioMixin(ClassprefsTooltipMixin):
    local_setting = None
    local_true = None
    local_false = None

    def getIndex(self):
        # True is shown first
        if getattr(self.mode.locals, self.local_setting):
            return 0
        return 1
                                           
    def getItems(self):
        return [self.local_true, self.local_false]

    def action(self, index=-1, multiplier=1):
        state = (index == 0)
        setattr(self.mode.locals, self.local_setting, state)
        self.mode.applyDefaultSettings()


class FundamentalIntRadioMixin(ClassprefsTooltipMixin, MinibufferMixin):
    local_setting = None
    local_values = None
    allow_other = True
    other_name = _("other")
    minibuffer = IntMinibuffer
    
    def getIndex(self):
        val = getattr(self.mode.locals, self.local_setting)
        try:
            return self.local_values.index(val)
        except ValueError:
            if self.allow_other:
                # Other is always last, after the local values
                return len(self.local_values)
            return 0
                                           
    def getItems(self):
        items = [str(i) for i in self.local_values]
        if self.allow_other:
            items.append(self.other_name)
        return items

    def action(self, index=-1, multiplier=1):
        if index < len(self.local_values):
            setattr(self.mode.locals, self.local_setting, self.local_values[index])
            self.mode.applyDefaultSettings()
        else:
            self.showMinibuffer(self.mode)
    
    def processMinibuffer(self, minibuffer, mode, value):
        dprint(value)
        setattr(self.mode.locals, self.local_setting, value)
        self.mode.applyDefaultSettings()


class LineNumbers(FundamentalSettingToggleMixin, ToggleAction):
    """Toggle the display of line numbers in the left margin
    
    """
    local_setting = 'line_numbers'
    alias = "line-numbers"
    name = "&Line Numbers"
    default_menu = ("View", -300)

class Wrapping(FundamentalSettingToggleMixin, ToggleAction):
    """Toggle line wrapping and the horizontal scrollbar
    
    When this is set, lines will be wrapped at the edge column (defined in the
    preferences dialog; defaults to 80 characters) and no horizontal scrollbar
    will be used.  When it is not set, the horizontal scrollbar will appear.
    
    Note that unless L{WordWrap} is turned on, the lines will be wrapped at the
    column without regard for word boundaries.
    """
    local_setting = 'wrapping'
    alias = "wrapping"
    name = "&Line Wrapping"
    default_menu = ("View", 301)

class WordWrap(FundamentalSettingToggleMixin, ToggleAction):
    """Toggle word wrop when line wrapping is on
    
    If line wrapping is on (see L{Wrapping}}, setting this forces the lines to
    be broken at whitespace or word boundaries.  If this is not set, the lines
    are broken at character boundaries.
    """
    local_setting = 'word_wrap'
    alias = "word-wrap"
    name = "&Wrap Words"
    default_menu = ("View", 302)

    def isEnabled(self):
        return self.mode.locals.wrapping

class Folding(FundamentalSettingToggleMixin, ToggleAction):
    """Toggle the code folding margin
    
    Code folding provides the ability to hide logical units of the text.  These
    logical units are typically broken up by either indentation level or by
    matching sets of braces, depending on the major mode.
    """
    local_setting = 'folding'
    alias = "code-folding"
    name = "&Folding"
    default_menu = ("View", 304)

class ViewEOL(FundamentalSettingToggleMixin, ToggleAction):
    """Show end-of-line characters
    
    Usually, end-of-line characters are not displayed, even when
    L{ViewWhitespace} is turned on.  Setting this option forces the end-of-
    line characters to be visible, and is useful for detecting mixed CR/LF
    characters.
    """
    local_setting = 'view_eol'
    alias = "view-eol"
    name = "EOL Characters"
    default_menu = ("View", 305)

class ViewWhitespace(FundamentalRadioMixin, RadioAction):
    """Show whitespace characters
    
    With this option set, spaces appear a small faint dots and tab characters
    appear as horizontal arrows.  Otherwise, whitespace characters are not
    visible at all.
    """
    local_setting = 'view_whitespace'
    name = "Show Whitespace"
    default_menu = ("View", 305.5)

class LongLineIndicator(FundamentalRadioMixin, RadioAction):
    """Show the long line indicator
    
    Long lines can be ignored by choosing 'none', or an indicator can be used.
    If the 'line' setting is chosen, a vertical line at the edge column is
    displayed.  If 'background' is chosen, the background of the text after
    the edge column is changed.
    
    The edge column is set in the preferences dialog.
    """
    local_setting = 'edge_indicator'
    name = "Show Long Lines"
    default_menu = ("View", 305.7)

class IndentationGuides(FundamentalSettingToggleMixin, ToggleAction):
    """Show the indentation guides
    
    Indentation guides are faint vertical lines displayed at each tab stop.
    """
    local_setting = 'indentation_guides'
    name = "Indentation Guides"
    default_menu = ("View", 306)

class IndentSize(FundamentalIntRadioMixin, RadioAction):
    """Set the number of spaces per logical indent
    
    This defines the number of spaces that make up a unit of indentation, or
    equivalently in old typewriter terms: the number of spaces per tab stop.
    This is independent of the number of spaces per tab character controlled
    by L{SpacesPerTab}.  For instance you can have tab characters equivalent
    to 8 spaces by setting L{SpacesPerTab} to 8, but IndentSize could be 4.
    """
    local_setting = 'indent_size'
    local_values = [2, 4, 8]
    allow_other = True
    name = "Indentation Size"
    minibuffer_label = "Number of spaces per indent:"
    default_menu = ("View", 306.5)

class IndentWithTabsOrSpaces(FundamentalBooleanRadioMixin, RadioAction):
    """Select whether to use tabs or spaces as the indent character
    
    Peppy will attempt to indent the text using all spaces or all tab
    characters.  Only if it is not possible to perform the indent using all
    tabs will peppy pad the end of the indentation with spaces.
    """
    local_setting = 'use_tab_characters'
    local_true = 'tab characters'
    local_false = 'spaces'
    name = "Indent Character"
    default_menu = ("View", 307)

class SpacesPerTab(FundamentalIntRadioMixin, RadioAction):
    """Set the number of spaces per tab character
    
    This setting controls the horizontal size of a single tab character.  When
    a tab character is displayed on the screen, it is expanded to the same
    width as the number of spaces set here.
    """
    local_setting = 'tab_size'
    local_values = [2, 4, 8]
    allow_other = True
    name = "Spaces Per Tab"
    minibuffer_label = "Number of spaces per tab:"
    default_menu = ("View", 306.7)

class GuessIndentSize(SelectAction):
    """Guess the tab size of the current document or selection and set the
    view parameters
    
    Scans the selected region (or the whole document if there is no selection)
    and tries to guess the size of the indentation and what style of
    indentation is used.  If it can determine the indentation, it sets the
    view parameters to match.
    """
    name = "Guess Indent Size"
    default_menu = ("View", 309)

    def action(self, index=-1, multiplier=1):
        s = self.mode
        (start, end) = s.GetSelection()
        if start==end:
            text = s.GetText()
        else:
            text = s.GetTextRange(start, end)
        size = guessSpacesPerIndent(text)
        if size == 0:
            s.locals.use_tab_characters = True
            self.frame.SetStatusText("Indenting with tab characters")
        elif size > 0:
            s.locals.use_tab_characters = False
            s.locals.indent_size = size
            self.frame.SetStatusText("%d spaces per indent, indenting with spaces" % (size))
        else:
            self.frame.SetStatusText("Can't determine indent size from document")
        s.setTabStyle()

class TabHighlight(FundamentalRadioMixin, RadioAction):
    """Set the indentation highlight style
    
    The leading whitespace can be highlighted to show differences in the
    types of whitespace.  While it is not recommended practice to mix tabs
    and spaces when indenting, you will encounter some files that have this
    characteristic.  Some languages, like Python, are very sensitive to
    whitespace and as such is recommended to use only one style of whitespace
    character.  This option can help identify problem intentation.
    """
    local_setting = 'tab_highlight_style'
    name = "Show Indentation"
    default_menu = ("View", 305.7)

class CaretWidth(FundamentalRadioMixin, RadioAction):
    """Set the pixel width of the caret
    
    """
    local_setting = 'caret_width'
    name = "Caret Width"
    default_menu = ("View", 310)

class CaretLineHighlight(FundamentalSettingToggleMixin, ToggleAction):
    """Highlight the line containing the caret using a different background
    
    """
    local_setting = 'caret_line_highlight'
    name = "Highlight Caret Line"
    default_menu = ("View", 311)

class FontZoom(ClassprefsTooltipMixin, MinibufferAction):
    """Set the font size relative to the default font (-10 to 20)
    """
    alias = "font-zoom"
    name = "Set Font Zoom..."
    default_menu = (("View/Font Size", 320), -900)
    minibuffer = IntMinibuffer
    minibuffer_label = "Font Zoom:"
    
    local_setting = 'font_zoom'

    def getInitialValueHook(self):
        return str(self.mode.GetZoom())

    def processMinibuffer(self, minibuffer, mode, zoom):
        """
        Callback function used to set the stc to the correct line.
        """
        self.mode.locals.font_zoom = zoom
        mode.SetZoom(zoom)

class FontZoomIncrease(SelectAction):
    """Increase the size of the font in the current view
    
    """
    name = "Increase Size"
    default_menu = ("View/Font Size", 100)
    icon = "icons/zoom_in.png"
    key_bindings = {'emacs': 'C-NUMPAD_ADD',}

    def action(self, index=-1, multiplier=1):
        self.mode.locals.font_zoom += 1
        self.mode.SetZoom(self.mode.locals.font_zoom)

class FontZoomDecrease(SelectAction):
    """Decrease the size of the font in the current view
    
    """
    name = "Decrease Size"
    default_menu = ("View/Font Size", 101)
    icon = "icons/zoom_out.png"
    key_bindings = {'emacs': 'C-NUMPAD_SUBTRACT',}

    def action(self, index=-1, multiplier=1):
        self.mode.locals.font_zoom -= 1
        self.mode.SetZoom(self.mode.locals.font_zoom)


class SelectBraces(TextModificationAction):
    """Select all text between braces
    
    Creates a selection by finding the nearest matching set of brace-like
    characters (i.e.  parethesis, square brackets or curly brackets) around
    the current cursor position.
    """
    alias = "select-braces"
    name = "Select Braces"
    icon = None
    default_menu = ("Edit", 126)
    default_toolbar = False
    key_bindings = None
    global_id = None

    def action(self, index=-1, multiplier=1):
        self.mode.selectBraces()


class EOLModeSelect(BufferBusyActionMixin, RadioAction):
    """Switch line endings
    
    Converts all line endings to the specified line ending.  This can be used
    if there are multiple styles of line endings in the file.
    """
    name = "Line Endings"
    inline = False
    localize_items = True
    default_menu = ("Transform", -999)

    items = ['Unix (LF)', 'DOS/Windows (CRLF)', 'Old-style Apple (CR)']
    modes = [wx.stc.STC_EOL_LF, wx.stc.STC_EOL_CRLF, wx.stc.STC_EOL_CR]

    def getIndex(self):
        eol = self.mode.GetEOLMode()
        return EOLModeSelect.modes.index(eol)
                                           
    def getItems(self):
        return EOLModeSelect.items

    def action(self, index=-1, multiplier=1):
        self.mode.ConvertEOLs(EOLModeSelect.modes[index])
        Publisher().sendMessage('resetStatusBar')


class WordCount(SelectAction):
    """Word count in regoin or document
    
    Counts the characters, words, and lines in the current document (or
    selected region if there is a selection.
    """
    name = "&Word Count"
    default_menu = ("Tools", -500)
    key_bindings = {'default': "M-=", }

    def action(self, index=-1, multiplier=1):
        s = self.mode
        (start, end) = s.GetSelection()
        if start==end:
            text = s.GetText()
        else:
            text = s.GetTextRange(start, end)
        chars = len(text)
        words = len(text.split())
        lines = len(text.splitlines())
        self.frame.SetStatusText("%d chars, %d words, %d lines" % (chars, words, lines))


class RevertEncoding(SelectAction):
    """Revert the file using a different encoding
    
    This prompts for a new encoding and reloads the file using that encoding.
    This may be necessary if the encoding is not specified in the first few
    lines of the text, or specified incorrectly.
    """
    alias = "revert-encoding"
    name = "Revert With Encoding"
    default_menu = ("File", 901)
    default_toolbar = False
    
    def action(self, index=-1, multiplier=1):
        minibuffer = TextMinibuffer(self.mode, self, label="Revert using encoding:",
                                    initial = self.mode.buffer.stc.encoding)
        self.mode.setMinibuffer(minibuffer)

    def processMinibuffer(self, minibuffer, mode, text):
        #dprint("Revert to encoding %s" % text)
        # see if it's a known encoding
        try:
            'test'.encode(text)
            # if we get here, it's valid
            self.mode.buffer.revert(text)
            if text != self.mode.buffer.stc.encoding:
                self.mode.setStatusText("Failed converting to %s; loaded as binary (probably not what you want)" % text)
        except LookupError:
            self.mode.setStatusText("Unknown encoding %s" % text)


class ApplySettingsSameMode(OnDemandActionNameMixin, SelectAction):
    """Apply view settings to all tabs"""
    name = "As Defaults for %s Mode"
    default_menu = ("View/Apply Settings", 100)

    def getMenuItemName(self):
        """Override in subclass to provide the menu item name."""
        return self.name % self.mode.keyword

    def action(self, index=-1, multiplier=1):
        locals = {}
        locals[self.mode.__class__] = self.mode.classprefsDictFromLocals()
        Publisher().sendMessage('peppy.preferences.changed', locals)
        # Make the local values the defaults so that they'll become persistent
        # by getting saved in the configuration file
        self.mode.classprefsCopyFromLocals()


class ApplySettingsAll(SelectAction):
    """Apply view settings to editors"""
    name = "As Defaults for All Modes"
    default_menu = ("View/Apply Settings", 110)

    def action(self, index=-1, multiplier=1):
        msg_data = {}
        settings = self.mode.classprefsDictFromLocals()
        msg_data[FundamentalMode] = settings
        msg_data['subclass'] = FundamentalMode
        Publisher().sendMessage('peppy.preferences.changed', msg_data)
        
        FundamentalMode.classprefsOverrideSubclassDefaults(settings)


class ApplySettingsKate(SelectAction):
    """Save view settings as kate variables at top of file"""
    name = "As Kate Variables at Top of File"
    default_menu = ("View/Apply Settings", -200)

    def action(self, index=-1, multiplier=1):
        import peppy.lib.kateutil as kateutil
        text = kateutil.serializeKateVariables(self.mode, column_width=self.mode.locals.edge_column)
        lines = []
        for line in text.splitlines():
            lines.append("%s%s%s" % (self.mode.start_line_comment, line, self.mode.end_line_comment))
        text = self.mode.getLinesep().join(lines) + self.mode.getLinesep()
        # Insert below any bangpath line if there is one
        bangpath = self.mode.GetLine(0)
        if bangpath.startswith(u"#!"):
            pos = self.mode.PositionFromLine(1)
        else:
            pos = 0
        self.mode.InsertText(pos, text)
        self.mode.GotoPos(pos)


class FundamentalMenu(IPeppyPlugin):
    """Trac plugin that provides the global menubar and toolbar.

    This provides the base menubar and toolbar that all major modes
    build upon.
    """
    def activateHook(self):
        Publisher().subscribe(self.getFundamentalMenu, 'fundamental.context_menu')
    
    def deactivateHook(self):
        Publisher().unsubscribe(self.getFundamentalMenu)
    
    def getFundamentalMenu(self, msg):
        action_classes = msg.data
        action_classes.extend(((610, SelectBraces), (0, SpellingSuggestionAction)))
        #dprint(action_classes)

    def getMajorModes(self):
        yield FundamentalMode

    def getCompatibleActions(self, modecls):
        if issubclass(modecls, FundamentalMode):
            return [SelfInsertCommand,
                    
                    WordCount, Wrapping, WordWrap, LineNumbers, Folding,
                    ViewEOL,
                    
                    IndentationGuides, IndentSize, IndentWithTabsOrSpaces,
                    SpacesPerTab, GuessIndentSize,
                    
                    CaretLineHighlight, CaretWidth, ViewWhitespace,
                    LongLineIndicator, TabHighlight, RevertEncoding,
                    
                    FontZoom, FontZoomIncrease, FontZoomDecrease,
                    
                    EOLModeSelect, SelectBraces,
                    
                    ApplySettingsSameMode, ApplySettingsAll, ApplySettingsKate,
                    ]
        return []
