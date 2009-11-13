# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os, shutil, time

import wx
import wx.stc

from peppy.editra import *
import peppy.editra.util as util
from peppy.debug import *

from profiler import Profile_Get as _PGET
from peppy.editra.eclib.eclutil import HexToRGB


class EditraSTCMixin(ed_style.StyleMgr, debugmixin):
    # When the style sheet doesn't exist the instance var style_set gets set
    # to 'default'.  But, after changes are made and the styles.ess file gets
    # saved to the user's conf directory, any currently loaded buffers don't
    # get automatically changed to point to the new style set.  So, we use
    # this class attribute and check for it in SetSyntax
    global_style_set = ""
    
    def __init__(self, stylefile):
        ed_style.StyleMgr.__init__(self, stylefile)
        
        self.LOG = self.dprint
        self.syntax_set = list()
        self._use_autocomp = False
        self._string_styles = []
        self._comment_styles = []
        self._keyword_styles = []
        self._on_style_needed_event_bound = False
    
    def isStyleString(self, style):
        """Is the style a string?
        
        This is automatically determined from the styling info provided by the
        syntax lists defined by editra.
        
        @return: True/False if style represents a quoted string as determined
        by the scintilla style
        """
        return style in self._string_styles
    
    def getStringStyles(self):
        return self._string_styles
    
    def _alwaysStyleString(self, style):
        """Function to be used in place of isStyleString when lexer is NULL
        """
        return True
        
    def isStyleComment(self, style):
        """Is the style a comment?
        
        This is automatically determined from the styling info provided by the
        syntax lists defined by editra.
        
        @return: True/False if style is a comment
        """
        return style in self._comment_styles

    def getCommentStyles(self):
        return self._comment_styles
    
    def isStyleKeyword(self, style):
        """Is the style a keyword reserved by the language?
        
        This corresponds to stuff flagged by editra as the 'keyword_style',
        designed to be the minimal set of reserved language words used for
        control flow like "if", "then", "for", etc.  This is automatically
        determined from the styling info provided by the syntax lists defined
        by editra.
        
        @return: True/False if style is a comment
        """
        return style in self._keyword_styles

    def FindLexer(self, keyword):
        """Sets Text Controls Lexer Based on File Extension
        @param set_ext: explicit extension to use in search
        @postcondition: lexer is configured for file

        """
        self.ClearDocumentStyle()

        # Configure Lexer from File Extension
        self.ConfigureLexer(keyword)

        # If syntax auto detection fails from file extension try to
        # see if there is an interpreter line that can be parsed.
        if self.GetLexer() in [0, wx.stc.STC_LEX_NULL]:
            interp = self.GetLine(0)
            if interp != wx.EmptyString:
                interp = interp.split(u"/")[-1]
                interp = interp.strip().split()
                if len(interp) and interp[-1][0] != "-":
                    interp = interp[-1]
                elif len(interp):
                    interp = interp[0]
                else:
                    interp = u''
                ex_map = { "python" : "py", "wish" : "tcl", "ruby" : "rb",
                           "bash" : "sh", "csh" : "csh", "perl" : "pl",
                           "ksh" : "ksh", "php" : "php" }
                self.ConfigureLexer(ex_map.get(interp, interp))
        self.Colourise(0, -1)

        # Configure Autocompletion
        # NOTE: must be done after syntax configuration
        if self._use_autocomp:
            self.ConfigureAutoComp()
        return 0
    
    def NullLexer(self):
        self.SetStyleBits(5)
        self.SetIndentationGuides(False)
        self.SetLexer(wx.stc.STC_LEX_NULL)
        self.ClearDocumentStyle()
        self.UpdateBaseStyles()
        
        # Make all styles appear as strings for spelling purposes
        self.isStyleString = self._alwaysStyleString
        
        self.LOG("NULL!!!!")
    
    def SetLexer(self, lexer):
        """Override StyledTextCtrl.SetLexer to handle custom lexers using
        STC_LEX_CONTAINER.
        
        Custom lexers can use EVT_STC_STYLENEEDED to style text on demand.
        """
        if lexer == wx.stc.STC_LEX_CONTAINER:
            # Only set this event if not already bound
            if not self._on_style_needed_event_bound:
                self.Bind(wx.stc.EVT_STC_STYLENEEDED, self.OnStyleNeeded)
                self._on_style_needed_event_bound = True
        else:
            if self._on_style_needed_event_bound:
                self.Unbind(wx.stc.EVT_STC_STYLENEEDED)
                self._on_style_needed_event_bound = False
        wx.stc.StyledTextCtrl.SetLexer(self, lexer)
    
    def OnStyleNeeded(self, evt):
        """Event handler for custom lexer
        
        """
        self.stc_lexer_id.styleText(self, self.GetEndStyled(), evt.GetPosition())

    def ConfigureLexer(self, keyword):
        """Sets Lexer and Lexer Keywords for the specified keyword
        
        @param keyword: a peppy major mode keyword
        """
        import peppy.editra.style_specs as style_specs
        
        custom = None
        if hasattr(self, 'stc_lexer_id') and self.stc_lexer_id is not None:
            lexer = self.stc_lexer_id
            if hasattr(lexer, 'styleText'):
                # Custom lexers use the STC_LEX_CONTAINER lexer type
                custom = self.stc_lexer_id
                lexer = wx.stc.STC_LEX_CONTAINER
        elif keyword in style_specs.stc_lexer_id:
            lexer = style_specs.stc_lexer_id[keyword]
        else:
            dprint("keyword not found: %s" % keyword)
            lexer = wx.stc.STC_LEX_NULL
        
        # Check for special cases for style bits
        if lexer in [ wx.stc.STC_LEX_HTML, wx.stc.STC_LEX_XML]:
            self.SetStyleBits(7)
        elif lexer == wx.stc.STC_LEX_NULL:
            self.NullLexer()
            return True
        elif custom:
            self.SetStyleBits(custom.getStyleBits())
        else:
            self.SetStyleBits(5)
        self.SetLexer(lexer)

        # Set or clear keywords used for extra highlighting
        if self.stc_keywords is not None:
            keywords = self.stc_keywords
        else:
            try:
                keywords = style_specs.keywords[keyword]
            except KeyError:
                dprint("No keywords found for %s" % keyword)
                keywords = []
        self.SetKeyWords(keywords)
        
        # Set or clear Editra style sheet info
        if self.stc_syntax_style_specs is not None:
            synspec = self.stc_syntax_style_specs
        elif custom:
            synspec = custom.getEditraStyleSpecs()
        else:
            try:
                synspec = style_specs.syntax_style_specs[keyword]
            except KeyError:
                dprint("No style specs found for %s" % keyword)
                synspec = []
        self.SetSyntax(synspec)

        # Set or clear extra properties
        if self.stc_extra_properties is not None:
            props = self.stc_extra_properties
        else:
            try:
                props = style_specs.extra_properties[keyword]
            except KeyError:
                dprint("No extra properties found for %s" % keyword)
                props = []
        self.SetProperties(props)

        self.dprint("GetLexer = %d" % self.GetLexer())
        return True
    
    def SetKeyWords(self, kw_lst, orig_interface_keywords=None):
        """Sets the keywords from a list of keyword sets
        @param kw_lst: [ (KWLVL, "KEWORDS"), (KWLVL2, "KEYWORDS2"), ect...]
        @todo: look into if the uniquifying of the list has a more optimal
               solution.

        """
        if orig_interface_keywords is not None:
            # If we get a 2nd argument, assume the keyword list conforms
            # to the standard stc SetKeyWords interface
            wx.stc.StyledTextCtrl.SetKeyWords(self, kw_lst, orig_interface_keywords)
            return
        
        # Parse Keyword Settings List simply ignoring bad values and badly
        # formed lists
        self.keywords = ""
        for keyw in kw_lst:
            if len(keyw) != 2:
                continue
            else:
                if not isinstance(keyw[0], int) or \
                   not isinstance(keyw[1], basestring):
                    continue
                else:
                    self.keywords += keyw[1]
                    wx.stc.StyledTextCtrl.SetKeyWords(self, keyw[0], keyw[1])

        kwlist = self.keywords.split()      # Split into a list of words
        kwlist = list(set(kwlist))          # Uniqueify the list
        kwlist.sort()                       # Sort into alphbetical order
        self.keywords = " ".join(kwlist)    # Put back into a string
        return True
 
    def SetSyntax(self, syn_lst):
        """Sets the Syntax Style Specs from a list of specifications
        @param syn_lst: [(STYLE_ID, "STYLE_TYPE"), (STYLE_ID2, "STYLE_TYPE2")]

        """
        # Parses Syntax Specifications list, ignoring all bad values
        if self.debuglevel > 1:
            import traceback
            dprint("".join(traceback.format_stack()))
        self.UpdateBaseStyles()
        self.LOG(syn_lst)
        valid_settings = list()
        
        for syn in syn_lst:
            if len(syn) != 2:
                self.LOG("[ed_stc][warn] Error setting syntax spec")
                continue
            else:
                self.LOG("setting %s to %s" % (syn[0], self.GetStyleByName(syn[1])))
                self.StyleSetSpec(syn[0], self.GetStyleByName(syn[1]))
                valid_settings.append(syn)
                if syn[1] in ['string_style', 'char_style', 'stringeol_style']:
                    self._string_styles.append(syn[0])
                elif syn[1] in ['comment_style', 'dockey_style', 'error_style']:
                    self._comment_styles.append(syn[0])
                elif syn[1] in ['keyword_style']:
                    self._keyword_styles.append(syn[0])
        self.syntax_set = valid_settings
        return True

    def SetProperties(self, prop_lst):
        """Sets the Lexer Properties from a list of specifications
        @param prop_lst: [ ("PROPERTY", "VAL"), ("PROPERTY2", "VAL2") ]

        """
        # Parses Property list, ignoring all bad values
        for prop in prop_lst:
            if len(prop) != 2:
                continue
            else:
                if not isinstance(prop[0], basestring) or not \
                   isinstance(prop[1], basestring):
                    continue
                else:
                    self.SetProperty(prop[0], prop[1])
        return True
        
    def RefreshStyles(self):
        """Refreshes the colorization of the window by reloading any 
        style tags that may have been modified.
        @postcondition: all style settings are refreshed in the control

        """
        self.Freeze()
        self.StyleClearAll()
        self.UpdateBaseStyles()
        self.SetSyntax(self.syntax_set)
        self.DefineMarkers()
        self.Thaw()
        self.Refresh()

    def StyleDefault(self):
        """Clears the editor styles to default
        @postcondition: style is reset to default

        """
        self.StyleResetDefault()
        self.StyleClearAll()
        self.SetCaretForeground(wx.NamedColor("black"))
        self.Colourise(0, -1)

    def UpdateBaseStyles(self):
        """Updates the base styles of editor to the current settings
        @postcondtion: base style info is updated

        """
        self.dprint("current=%s" % self.style_set)
        self.StyleDefault()
        self.SetMargins(0, 0)
        # Global default styles for all languages
        self.StyleSetSpec(0, self.GetStyleByName('default_style'))
        self.StyleSetSpec(wx.stc.STC_STYLE_DEFAULT, \
                          self.GetStyleByName('default_style'))
        self.StyleSetSpec(wx.stc.STC_STYLE_LINENUMBER, \
                          self.GetStyleByName('line_num'))
        self.StyleSetSpec(wx.stc.STC_STYLE_CONTROLCHAR, \
                          self.GetStyleByName('ctrl_char'))
        self.StyleSetSpec(wx.stc.STC_STYLE_BRACELIGHT, \
                          self.GetStyleByName('brace_good'))
        self.StyleSetSpec(wx.stc.STC_STYLE_BRACEBAD, \
                          self.GetStyleByName('brace_bad'))
        self.StyleSetSpec(wx.stc.STC_STYLE_INDENTGUIDE, \
                          self.GetStyleByName('guide_style'))

        # wx.stc.STC_STYLE_CALLTIP doesnt seem to do anything
        calltip = self.GetItemByName('calltip')
        self.CallTipSetBackground(calltip.GetBack())
        self.CallTipSetForeground(calltip.GetFore())

        sback = self.GetItemByName('select_style')
        # Make sure that the user has specified a valid background color,
        # otherwise the system highlight color will be used.
        if not sback.IsNull() and sback.GetBack():
            sback = sback.GetBack()
        else:
            sback = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHT)
        self.SetSelBackground(True, sback)

        # Setting the whitespace background color overrides the selection
        # color, which looks weird.  I'm only allowing the whitespace
        # foreground to be set by the user; the background will remain the
        # default background.
        wspace = self.GetItemByName('whitespace_style')
        if not wspace.IsNull():
            self.SetWhitespaceForeground(True, wspace.GetFore())

        style = self.GetItemByName('foldmargin_style')
        # The foreground/background settings for the marker column seem to
        # backwards from what the parameters take so use our Fore color for
        # the stcs back and visa versa for our Back color.
        back = style.GetFore()
        rgb = HexToRGB(back[1:])
        back = wx.Colour(red=rgb[0], green=rgb[1], blue=rgb[2])

        fore = style.GetBack()
        rgb = HexToRGB(fore[1:])
        fore = wx.Colour(red=rgb[0], green=rgb[1], blue=rgb[2])

        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEROPEN,
                          wx.stc.STC_MARK_BOXMINUS, fore, back)
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDER,
                          wx.stc.STC_MARK_BOXPLUS,  fore, back)
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERSUB,
                          wx.stc.STC_MARK_VLINE, fore, back)
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERTAIL,
                          wx.stc.STC_MARK_LCORNER, fore, back)
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEREND,
                          wx.stc.STC_MARK_BOXPLUSCONNECTED, fore, back)
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEROPENMID,
                          wx.stc.STC_MARK_BOXMINUSCONNECTED, fore, back)
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERMIDTAIL,
                          wx.stc.STC_MARK_TCORNER, fore, back)
        self.MarkerDefine(0, wx.stc.STC_MARK_SHORTARROW, fore, back)
        self.SetFoldMarginHiColour(True, fore)
        self.SetFoldMarginColour(True, fore)

        self.SetCaretForeground(self.GetDefaultForeColour())
        self.SetCaretLineBack(self.GetItemByName('caret_line').GetBack())
        self.DefineMarkers()
        self.Colourise(0, -1)
    
    def UpdateAllStyles(self, spec_style=None):
        """Refreshes all the styles and attributes of the control
        @param spec_style: style scheme name
        @postcondtion: style scheme is set to specified style

        """
        self.dprint("requested=%s current=%s" % (spec_style, self.style_set))
        if spec_style != self.style_set:
            self.LoadStyleSheet(self.GetStyleSheet(spec_style), force=True)
        self.UpdateBaseStyles()
        self.SetSyntax(self.syntax_set)
        self.DefineMarkers()
        self.Refresh()

    def DefineMarkers(self):
        """Defines the folder and bookmark icons for this control
        @postcondition: all margin markers are defined

        """
        back = self.GetDefaultForeColour()
        fore = self.GetDefaultBackColour()
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEROPEN, 
                          wx.stc.STC_MARK_BOXMINUS, fore, back)
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDER,
                          wx.stc.STC_MARK_BOXPLUS,  fore, back)
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERSUB,     
                          wx.stc.STC_MARK_VLINE, fore, back)
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERTAIL,
                          wx.stc.STC_MARK_LCORNER, fore, back)
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEREND,
                          wx.stc.STC_MARK_BOXPLUSCONNECTED, fore, back)
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDEROPENMID, 
                          wx.stc.STC_MARK_BOXMINUSCONNECTED, fore, back)
        self.MarkerDefine(wx.stc.STC_MARKNUM_FOLDERMIDTAIL, 
                          wx.stc.STC_MARK_TCORNER, fore, back)
        self.MarkerDefine(0, wx.stc.STC_MARK_SHORTARROW, fore, back)
        self.SetFoldMarginHiColour(True, fore)
        self.SetFoldMarginColour(True, fore)

    def FindTagById(self, style_id):
        """Find the style tag that is associated with the given
        Id. If not found it returns an empty string.
        @param style_id: id of tag to look for
        @return: style tag string

        """
        for data in self.syntax_set:
            if style_id == data[0]:
                return data[1]
        return 'default_style'
    
    def GetStyleSheet(self, sheet_name=None):
        """Finds the current style sheet and returns its path. The
        Lookup is done by first looking in the users config directory
        and if it is not found there it looks for one on the system
        level and if that fails it returns None.
        @param sheet_name: style sheet to look for
        @return: full path to style sheet

        """
        if sheet_name:
            style = sheet_name
            if sheet_name.split(u'.')[-1] != u"ess":
                style += u".ess"
        elif _PGET('SYNTHEME', 'str').split(u'.')[-1] != u"ess":
            style = (_PGET('SYNTHEME', 'str') + u".ess").lower()
        else:
            style = _PGET('SYNTHEME', 'str').lower()

        # Get Correct Filename if it exists
        for sheet in util.GetResourceFiles('styles', False, True, title=False):
            if sheet.lower() == style.lower():
                style = sheet
                break
        user = wx.GetApp().fonts.getStylePath(style)
        if os.path.exists(user):
            self.dprint("found user style %s at %s" % (style, user))
            return user
        sysp = os.path.join(util.GetResourceDir('styles'), style)
        if os.path.exists(sysp):
            self.dprint("found system style %s at %s" % (style, sysp))
            return sysp
        self.dprint("didn't find %s" % style)
#        user = os.path.join(ed_glob.CONFIG['STYLES_DIR'], style)
#        sysp = os.path.join(ed_glob.CONFIG['SYS_STYLES_DIR'], style)
#        if os.path.exists(user):
#            return user
#        elif os.path.exists(sysp):
#            return sysp
#        else:
#            return None
