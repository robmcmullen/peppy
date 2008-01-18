# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os, shutil, time

import wx
import wx.stc

from peppy.editra import *
import peppy.editra.util as util
from peppy.debug import *

class EditraSTCMixin(ed_style.StyleMgr, debugmixin):
    debuglevel = 0
    
    def __init__(self, stylefile):
        ed_style.StyleMgr.__init__(self, stylefile)
        
        self.LOG = self.dprint
        self._synmgr = syntax.SyntaxMgr()
        self.syntax_set = list()
        self._use_autocomp = False

    def FindLexer(self, set_ext=u''):
        """Sets Text Controls Lexer Based on File Extension
        @param set_ext: explicit extension to use in search
        @postcondition: lexer is configured for file

        """
        if set_ext != u'':
            ext = set_ext.lower()
        else:
            ext = util.GetExtension(self.filename).lower()
        self.ClearDocumentStyle()

        # Configure Lexer from File Extension
        self.ConfigureLexer(ext)

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
    
    def ConfigureLexer(self, lang):
        """Sets Lexer and Lexer Keywords for the specifed file extension
        @param file_ext: a file extension to configure the lexer from

        """
        syn_data = self._synmgr.SyntaxData(lang)
        self.LOG(lang)
        self.LOG(syn_data)

        # Set the ID of the selected lexer
        try:
            self.lang_id = syn_data[syntax.LANGUAGE]
        except KeyError:
            self.LOG("[stc][err] Failed to get Lang Id from Syntax package")
            self.lang_id = 0

        lexer = syn_data[syntax.LEXER]
        self.LOG("lexer = %s" % lexer)
        # Check for special cases
        if lexer in [ wx.stc.STC_LEX_HTML, wx.stc.STC_LEX_XML]:
            self.SetStyleBits(7)
        elif lexer == wx.stc.STC_LEX_NULL:
            self.SetStyleBits(5)
            self.SetIndentationGuides(False)
            self.SetLexer(lexer)
            self.ClearDocumentStyle()
            self.UpdateBaseStyles()
            self.setCommentDelimiters()
            self.LOG("NULL!!!!")
            return True
        else:
            self.SetStyleBits(5)

        try:
            keywords = syn_data[syntax.KEYWORDS]
        except KeyError:
            self.LOG("[stc][err] No Keywords Data Found")
            keywords = []
        
        try:
            synspec = syn_data[syntax.SYNSPEC]
        except KeyError:
            self.LOG("[stc] [exception] Failed to get Syntax Specifications")
            synspec = []

        try:
            props = syn_data[syntax.PROPERTIES]
        except KeyError:
            self.LOG("[stc] [exception] No Extra Properties to Set")
            props = []

        try:
            comment = syn_data[syntax.COMMENT]
        except KeyError:
            self.LOG("[stc] [exception] No Comment Pattern to set")
            comment = []

        # Set Lexer
        self.SetLexer(lexer)
        # Set Keywords
        self.SetKeyWords(keywords)
        # Set Lexer/Syntax Specifications
        self.SetSyntax(synspec)
        # Set Extra Properties
        self.SetProperties(props)
        # Set Comment Pattern
        self.setCommentDelimiters(*comment)
        self.LOG("GetLexer = %d" % self.GetLexer())
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
        self.UpdateBaseStyles()
        self.LOG(syn_lst)
        valid_settings = list()
        for syn in syn_lst:
            if len(syn) != 2:
                self.LOG("[ed_stc][warn] Error setting syntax spec")
                continue
            else:
                if not isinstance(syn[0], basestring) or \
                   not hasattr(wx.stc, syn[0]):
                    self.LOG("[ed_stc][warn] Unknown syntax region: %s" % \
                             str(syn[0]))
                    continue
                elif not isinstance(syn[1], basestring):
                    self.LOG("[ed_stc][warn] Poorly formated styletag: %s" % \
                             str(syn[1]))
                    continue
                else:
                    self.LOG("setting %s to %s" % (syn[0], self.GetStyleByName(syn[1])))
                    self.StyleSetSpec(getattr(wx.stc, syn[0]), \
                                      self.GetStyleByName(syn[1]))
                    valid_settings.append(syn)
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
        calltip = self.GetItemByName('calltip')
        self.CallTipSetBackground(calltip.GetBack())
        self.CallTipSetForeground(calltip.GetFore())
        self.SetCaretForeground(self.GetDefaultForeColour())
        self.DefineMarkers()
        self.Colourise(0, -1)
    
    def UpdateAllStyles(self, spec_style=None):
        """Refreshes all the styles and attributes of the control
        @param spec_style: style scheme name
        @postcondtion: style scheme is set to specified style

        """
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
            if style_id == getattr(wx.stc, data[0]):
                return data[1]
        return 'default_style'
