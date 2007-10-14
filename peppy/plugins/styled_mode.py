# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
import os, shutil, time

import wx
import wx.stc
from wx.lib.pubsub import Publisher

from peppy.menu import *
from peppy.fundamental import *
from peppy.major import *
from peppy.stcinterface import *

from peppy.editra import *

class PeppyEditraSTC(PeppySTC, ed_style.StyleMgr):
    def __init__(self, parent, refstc=None):
        PeppySTC.__init__(self, parent, refstc)
        ed_style.StyleMgr.__init__(self, EditraStyledMode.getStyleFile())
        
        self.LOG = dprint
        self._synmgr = syntax.SyntaxMgr()
        
    def ConfigureLexer(self, file_ext):
        """Sets Lexer and Lexer Keywords for the specifed file extension
        @param file_ext: a file extension to configure the lexer from

        """
        syn_data = self._synmgr.SyntaxData(file_ext)
        dprint(file_ext)
        dprint(syn_data)

        # Set the ID of the selected lexer
        try:
            self.lang_id = syn_data[syntax.LANGUAGE]
        except KeyError:
            self.LOG("[stc][err] Failed to get Lang Id from Syntax package")
            self.lang_id = 0

        lexer = syn_data[syntax.LEXER]
        dprint("lexer = %s" % lexer)
        # Check for special cases
        if lexer in [ wx.stc.STC_LEX_HTML, wx.stc.STC_LEX_XML]:
            self.SetStyleBits(7)
        elif lexer == wx.stc.STC_LEX_NULL:
            self.SetStyleBits(5)
            self.SetIndentationGuides(False)
            self.SetLexer(lexer)
            self.ClearDocumentStyle()
            self.UpdateBaseStyles()
            dprint("NULL!!!!")
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
        self._comment = comment
        dprint("GetLexer = %d" % self.GetLexer())
        return True

    def SetKeyWords(self, kw_lst):
        """Sets the keywords from a list of keyword sets
        @param kw_lst: [ (KWLVL, "KEWORDS"), (KWLVL2, "KEYWORDS2"), ect...]
        @todo: look into if the uniquifying of the list has a more optimal
               solution.

        """
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
        dprint(syn_lst)
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
                    dprint("setting %s to %s" % (syn[0], self.GetStyleByName(syn[1])))
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
        #self.CallTipSetBackground(calltip.GetBack())
        #self.CallTipSetForeground(calltip.GetFore())
        self.SetCaretForeground(self.GetDefaultForeColour())
        self.DefineMarkers()
        self.Colourise(0, -1)

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



class EditraStyledMode(FundamentalMode):
    """
    The base view of most (if not all) of the views that use the STC
    to directly edit the text.  Views (like the HexEdit view or an
    image viewer) that only use the STC as the backend storage are
    probably not based on this view.
    """
    debuglevel = 1
    
    keyword = 'Styled'

    start_line_comment = ''
    end_line_comment = ''

    default_classprefs = (
        StrParam('editra_style_sheet', 'styles.ess', 'Filename in the config directory containing\nEditra style sheet information'),
    )
    
    @classmethod
    def verifyFilename(cls, filename):
        """Hook to verify filename matches the default regular
        expression for this mode.

        @param filename: the pathname part of the url (i.e. not the
        protocol, port number, query string, or anything else)

        @returns: True if the filename matches
        """
        name, ext = os.path.splitext(filename)
        if ext.startswith('.'):
            ext = ext[1:]
            dprint("ext = %s, filename = %s" % (ext, filename))
            extreg = syntax.ExtensionRegister()
            dprint(extreg.GetAllExtensions())
            stc_type = extreg.FileTypeFromExt(ext)
            dprint(stc_type)
            if stc_type != synglob.LANG_TXT:
                return ext
        return False
    
    @classmethod
    def getStyleFile(cls):
        filename = wx.GetApp().getConfigFilePath(cls.classprefs.editra_style_sheet)
        dprint(filename)
        return filename
    
    def createEditWindow(self,parent):
        assert self.dprint("creating new EditraStyled window")
        self.createSTC(parent)
        win=self.stc
        return win

    def createSTC(self,parent):
        """Create the STC and apply styling settings.

        Everything that subclasses from EditraStyledMode will use an
        STC instance for displaying the user interaction window.
        
        Styling information is loaded from the stc-styles.rc.cfg files
        that the boa styling editor uses.  This file is located in the
        default configuration directory of the application on a
        per-user basis, and in the peppy/config directory on a
        site-wide basis.
        """
        start = time.time()
        dprint("starting createSTC at %0.5fs" % start)
        self.stc=PeppyEditraSTC(parent,refstc=self.buffer.stc)
        dprint("PeppySTC done in %0.5fs" % (time.time() - start))
        self.applySettings()
        dprint("applySettings done in %0.5fs" % (time.time() - start))

    def applySettings(self):
        start = time.time()
        dprint("starting applySettings at %0.5fs" % start)
        self.applyDefaultSettings()
        #dprint("applyDefaultSettings done in %0.5fs" % (time.time() - start))
        
        self.editra_ext = self.verifyFilename(self.buffer.url.path)
        self.stc.ConfigureLexer(self.editra_ext)
        dprint("styleSTC (if True) done in %0.5fs" % (time.time() - start))
        self.has_stc_styling = True
        dprint("applySettings returning in %0.5fs" % (time.time() - start))

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
            self.stc.Bind(wx.stc.EVT_STC_MARGINCLICK, self.onMarginClick)
        else:
            self.stc.SetMarginWidth(2, 0)
            self.stc.Unbind(wx.stc.EVT_STC_MARGINCLICK)

    def setTabStyle(self):
        self.stc.SetIndent(self.classprefs.tab_size)
        self.stc.SetProperty('tab.timmy.whinge.level', str(self.classprefs.tab_highlight_style))
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


class EditraStyledPlugin(IPeppyPlugin):
    def getMajorModes(self):
        yield EditraStyledMode
