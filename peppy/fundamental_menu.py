# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os, shutil, time, new, re

import wx
import wx.stc
from wx.lib.pubsub import Publisher

from peppy.actions import *
from peppy.actions.minibuffer import *
from peppy.fundamental import *
from peppy.lib.userparams import *
from peppy.lib.textutil import *


class SpellingSuggestionAction(ListAction):
    name = "Spelling..."
    inline = True
    menumax = 5
    tooltip = "Spelling suggestions for the current word"

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

class FundamentalSettingToggle(ClassprefsTooltipMixin, ToggleAction):
    local_setting = None

    def isChecked(self):
        return getattr(self.mode.locals, self.local_setting)
    
    def action(self, index=-1, multiplier=1):
        value = self.isChecked()
        setattr(self.mode.locals, self.local_setting, not value)
        self.mode.applyDefaultSettings()

class FundamentalRadioToggle(ClassprefsTooltipMixin, RadioAction):
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

class FundamentalBooleanRadioToggle(ClassprefsTooltipMixin, RadioAction):
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


class FundamentalIntRadioToggle(ClassprefsTooltipMixin, RadioAction, MinibufferMixin):
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


class LineNumbers(FundamentalSettingToggle):
    local_setting = 'line_numbers'
    alias = "line-numbers"
    name = "&Line Numbers"
    default_menu = ("View", -300)

class Wrapping(FundamentalSettingToggle):
    local_setting = 'wrapping'
    alias = "wrapping"
    name = "&Line Wrapping"
    default_menu = ("View", 301)

class WordWrap(FundamentalSettingToggle):
    local_setting = 'word_wrap'
    alias = "word-wrap"
    name = "&Wrap Words"
    default_menu = ("View", 302)

    def isEnabled(self):
        return self.mode.locals.wrapping

class Folding(FundamentalSettingToggle):
    local_setting = 'folding'
    alias = "code-folding"
    name = "&Folding"
    default_menu = ("View", 304)

class ViewEOL(FundamentalSettingToggle):
    local_setting = 'view_eol'
    alias = "view-eol"
    name = "EOL Characters"
    default_menu = ("View", 305)

class ViewWhitespace(FundamentalRadioToggle):
    local_setting = 'view_whitespace'
    name = "Show Whitespace"
    default_menu = ("View", 305.5)

class LongLineIndicator(FundamentalRadioToggle):
    local_setting = 'edge_indicator'
    name = "Show Long Lines"
    default_menu = ("View", 305.7)

class IndentationGuides(FundamentalSettingToggle):
    local_setting = 'indentation_guides'
    name = "Indentation Guides"
    default_menu = ("View", 306)

class IndentSize(FundamentalIntRadioToggle):
    local_setting = 'indent_size'
    local_values = [2, 4, 8]
    allow_other = True
    name = "Indentation Size"
    minibuffer_label = "Number of spaces per indent:"
    default_menu = ("View", 306.5)

class IndentWithTabsOrSpaces(FundamentalBooleanRadioToggle):
    local_setting = 'use_tab_characters'
    local_true = 'tab characters'
    local_false = 'spaces'
    name = "Indent Character"
    default_menu = ("View", 307)

class TabSize(FundamentalIntRadioToggle):
    local_setting = 'tab_size'
    local_values = [2, 4, 8]
    allow_other = True
    name = "Tab Size"
    minibuffer_label = "Number of spaces per tab:"
    default_menu = ("View", 308)

    def isEnabled(self):
        return self.mode.locals.use_tab_characters

class GuessIndentSize(SelectAction):
    """Guess the tab size of the current document or selection and set the view parameters"""
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

class TabHighlight(FundamentalRadioToggle):
    local_setting = 'tab_highlight_style'
    name = "Show Indentation"
    default_menu = ("View", 305.7)

class CaretWidth(FundamentalRadioToggle):
    local_setting = 'caret_width'
    name = "Caret Width"
    default_menu = ("View", 310)

class CaretLineHighlight(FundamentalSettingToggle):
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
    name = "Increase Size"
    tooltip = "Increase the size of the font in the current view"
    default_menu = ("View/Font Size", 100)
    icon = "icons/zoom_in.png"

    def action(self, index=-1, multiplier=1):
        self.mode.locals.font_zoom += 1
        self.mode.SetZoom(self.mode.locals.font_zoom)

class FontZoomDecrease(SelectAction):
    name = "Decrease Size"
    tooltip = "Decrease the size of the font in the current view"
    default_menu = ("View/Font Size", 101)
    icon = "icons/zoom_out.png"

    def action(self, index=-1, multiplier=1):
        self.mode.locals.font_zoom -= 1
        self.mode.SetZoom(self.mode.locals.font_zoom)


class SelectBraces(TextModificationAction):
    alias = "select-braces"
    name = "Select Braces"
    tooltip = "Select all text between the braces"
    icon = None
    default_menu = ("Edit", 126)
    default_toolbar = False
    key_bindings = None
    global_id = None

    def action(self, index=-1, multiplier=1):
        self.mode.selectBraces()


class EOLModeSelect(BufferBusyActionMixin, RadioAction):
    name = "Line Endings"
    inline = False
    localize_items = True
    tooltip = "Switch line endings"
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
    name = "&Word Count"
    tooltip = "Word count in region or document"
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
    alias = "revert-encoding"
    name = "Revert With Encoding"
    tooltip = "Revert with a different encoding"
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


class ElectricReturn(TextModificationAction):
    alias = "electric-return"
    name = "Electric Return"
    tooltip = "Indent the next line following a return"
    icon = 'icons/text_indent_rob.png'
    key_bindings = {'default': 'RET',}
    key_needs_focus = True

    def action(self, index=-1, multiplier=1):
        if self.mode.spell and self.mode.classprefs.spell_check:
            pos = self.mode.GetCurrentPos()
            self.mode.spell.checkWord(pos)
        self.mode.autoindent.processReturn(self.mode)


class ElectricDelete(TextModificationAction):
    """Delete all whitespace from cursor forwart to the next non-blank character
    """
    alias = "electric-delete"
    name = "Electric Delete"
    key_bindings = {'default': 'DELETE',}
    key_needs_focus = True

    def action(self, index=-1, multiplier=1):
        self.mode.autoindent.electricDelete(self.mode)


class ElectricBackspace(TextModificationAction):
    """Delete all whitespace from cursor back to the last non-blank character
    """
    alias = "electric-backspace"
    name = "Electric Backspace"
    key_bindings = {'default': 'BACK',}
    key_needs_focus = True

    def action(self, index=-1, multiplier=1):
        self.mode.autoindent.electricBackspace(self.mode)


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

    def getCompatibleActions(self, mode):
        if issubclass(mode.__class__, FundamentalMode):
            return [WordCount, Wrapping, WordWrap, LineNumbers, Folding,
                    ViewEOL,
                    
                    IndentationGuides, IndentSize, IndentWithTabsOrSpaces,
                    TabSize, GuessIndentSize,
                    
                    CaretLineHighlight, CaretWidth, ViewWhitespace,
                    LongLineIndicator, TabHighlight, RevertEncoding,
                    
                    FontZoom, FontZoomIncrease, FontZoomDecrease,
                    
                    EOLModeSelect, SelectBraces,
                    
                    ElectricReturn, ElectricDelete, ElectricBackspace,
                    
                    ApplySettingsSameMode, ApplySettingsAll,
                    ]
        return []
