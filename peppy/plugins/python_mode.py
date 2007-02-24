# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Python major mode.
"""

import os,struct
import keyword

import wx
import wx.stc as stc

from peppy import *
from peppy.about import SetAbout
from peppy.menu import *
from peppy.major import *
from peppy.fundamental import FundamentalMode

_sample_file='''\
#!/usr/bin/env python
""" doc string """
import os
from cStringIO import StringIO

globalvar="string"
listvar=[2, 3, 5, 7, 11]
dictvar={\'a\':1, \'b\':2, \'z\'=3333}

class Foo(Bar):
    \'\'\'
    Multi-line
    doc string
    \'\'\'
    classvar=\'stuff\'
    def __init__(self):
        self.baz="zippy"
        if self.baz=str(globalvar):
            ## FIXME! - stuff and things
            open(self.baz)
        else:
            raise TypeError("stuff")
        return
'''
SetAbout('sample.py',_sample_file)


class SamplePython(SelectAction):
    name = "&Open Sample Python"
    tooltip = "Open a sample Python file"
    icon = wx.ART_FILE_OPEN

    def action(self, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.open("about:sample.py")


class PythonIndentMixin(object):
    def indent(self, incr):
        s=self.stc

        # from pype.PythonSTC.Dent()
        self.dprint("indenting by %d" % incr)
        incr *= s.GetIndent()
        self.dprint("indenting by %d" % incr)
        x,y = s.GetSelection()
        if x==y:
            lnstart = s.GetCurrentLine()
            lnend = lnstart
            if incr < 0:
                a = s.GetLineIndentation(lnstart)%(abs(incr))
                if a:
                    incr = -a
            pos = s.GetCurrentPos()
            col = s.GetColumn(pos)
            linestart = pos-col
            a = max(linestart+col+incr, linestart)
        else:
            lnstart = s.LineFromPosition(x)
            lnend = s.LineFromPosition(y-1)
        s.BeginUndoAction()
        try:
            for ln in xrange(lnstart, lnend+1):
                count = s.GetLineIndentation(ln)
                m = (count+incr)
                m += cmp(0, incr)*(m%incr)
                m = max(m, 0)
                s.SetLineIndentation(ln, m)
            if x==y:
                pos = pos + (m-count) - min(0, col + (m-count))
                s.SetSelection(pos, pos)
            else:
                p = 0
                if lnstart != 0:
                    p = s.GetLineEndPosition(lnstart-1) + len(s.format)
                s.SetSelection(p, s.GetLineEndPosition(lnend))
        finally:
            s.EndUndoAction()



class PythonElectricReturnMixin(object):
    def electricReturn(self):
        s=self.stc
        
        # From PyPE: indent the new line to the correct indent
        # (matching the line above or indented further based on syntax)

        #get information about the current cursor position
        linenum = s.GetCurrentLine()
        pos = s.GetCurrentPos()
        col = s.GetColumn(pos)
        linestart = s.PositionFromLine(linenum)
        line = s.GetLine(linenum)[:pos-linestart]
    
        #get info about the current line's indentation
        ind = s.GetLineIndentation(linenum)                    

        xtra = 0

        if col <= ind:
            xtra = None
            if s.GetUseTabs():
                s.ReplaceSelection(viewer.format+(col*' ').replace(s.GetTabWidth()*' ', '\t'))
            else:
                s.ReplaceSelection(viewer.format+(col*' '))
        elif not pos:
            xtra = None
            s.ReplaceSelection(viewer.format)

        else:
            colon = ord(':')
            
            if (line.find(':')>-1):
                for i in xrange(linestart, min(pos, s.GetTextLength())):
                    styl = s.GetStyleAt(i)
                    #self.dprint(styl, s.GetCharAt(i))
                    if not xtra:
                        if (styl==10) and (s.GetCharAt(i) == colon):
                            xtra = 1
                    elif (styl == 1):
                        #it is a comment, ignore the character
                        pass
                    elif (styl == 0) and (s.GetCharAt(i) in [ord(i) for i in ' \t\r\n']):
                        #is not a comment, but is the space before a comment
                        #or the end of a line, ignore the character
                        pass
                    else:
                        #this is not a comment or some innocuous other character
                        #this is a docstring or otherwise, no additional indent
                        xtra = 0
                        #commenting the break fixes stuff like this
                        # for i in blah[:]:
                        #break
                if xtra:
                    #This deals with ending single and multi-line definitions properly.
                    while linenum >= 0:
                        found = []
                        for i in ['def', 'class', 'if', 'else', 'elif', 'while',
                                'for', 'try', 'except', 'finally', 'with', 'cdef']:
                            a = line.find(i)
                            if (a > -1):
                                found.append(a)
                        #self.dprint('fnd', found)
                        if found: found = min(found)
                        else:     found = -1
                        if (found > -1) and\
                        (s.GetStyleAt(s.GetLineEndPosition(linenum)-len(line)+found)==5) and\
                        (s.GetLineIndentation(linenum) == found):
                            ind = s.GetLineIndentation(linenum)
                            break
                        linenum -= 1
                        line = s.GetLine(linenum)
            #if we were to do indentation for ()[]{}, it would be here
            if not xtra:
                #yep, right here.
                fnd = 0
                for i in "(){}[]":
                    if (line.find(i) > -1):
                        fnd = 1
                        break
                if fnd:
                    seq = []
                    #self.dprint("finding stuff")
                    for i in "(){}[]":
                        a = line.find(i)
                        start = 0
                        while a > -1:
                            start += a+1
                            if s.GetStyleAt(start+linestart-1)==10:
                                seq.append((start, i))
                            a = line[start:].find(i)
                    seq.sort()
                    cl = {')':'(', ']': '[', '}': '{',
                        '(':'',  '[': '',  '{': ''}
                    stk = []
                    #self.dprint("making tree")
                    for po, ch in seq:
                        #self.dprint(ch,)
                        if not cl[ch]:
                            #standard opening
                            stk.append((po, ch))
                        elif stk:
                            if cl[ch] == stk[-1][1]:
                                #proper closing of something
                                stk.pop()
                            else:
                                #probably a syntax error
                                #does it matter what is done?
                                stk = []
                                break
                        else:
        #Probably closing something on another line, should probably find
        #the indent level of the opening, but that would require checking
        #multiple previous items for the opening item.
        #single-line dedent.
                            stk = []
                            break
                    if stk:
                        #self.dprint("stack remaining", stk)
                        ind = stk[-1][0]
            if not xtra:
                ls = line.lstrip()
                if (ls[:6] == 'return') or (ls[:4] == 'pass') or (ls[:5] == 'break') or (ls[:8] == 'continue'):
                    xtra = -1
        
        if xtra != None:
            a = max(ind+xtra*s.GetIndent(), 0)*' '
            
            if s.GetUseTabs():
                a = a.replace(s.GetTabWidth()*' ', '\t')
            ## s._tdisable(s.ReplaceSelection, viewer.format+a)
            s.ReplaceSelection(viewer.format+a)



class PythonMode(PythonIndentMixin,PythonElectricReturnMixin,FundamentalMode):
    keyword='Python'
    icon='icons/py.ico'
    regex="\.(py|pyx)$"

    default_settings = {
        'word_wrap': True,
        'minor_modes': 'pype_funclist,funcmenu,spe_funclist',
        'sample_file': _sample_file,
        'stc_lexer': wx.stc.STC_LEX_PYTHON,
        'stc_keywords': 'and as assert break class continue def del elif else except exec finally for from global if import in is lambda not or pass print raise return try while True False self',
        'stc_boa_braces': "{'good': (9, 12), 'bad': (10, 12)}",
        'stc_boa_style_names': {wx.stc.STC_P_DEFAULT: 'Default',
                                wx.stc.STC_P_COMMENTLINE: 'Comment',
                                wx.stc.STC_P_NUMBER : 'Number',
                                wx.stc.STC_P_STRING : 'String',
                                wx.stc.STC_P_CHARACTER: 'Single quoted string',
                                wx.stc.STC_P_WORD: 'Keyword',
                                wx.stc.STC_P_TRIPLE:'Triple quotes',
                                wx.stc.STC_P_TRIPLEDOUBLE: 'Triple double quotes',
                                wx.stc.STC_P_CLASSNAME: 'Class definition',
                                wx.stc.STC_P_DEFNAME: 'Function or method',
                                wx.stc.STC_P_OPERATOR: 'Operators',
                                wx.stc.STC_P_IDENTIFIER: 'Identifiers',
                                wx.stc.STC_P_COMMENTBLOCK: 'Comment blocks',
                                wx.stc.STC_P_STRINGEOL: 'EOL unclosed string'},
        'stc_lexer_styles': {wx.stc.STC_P_NUMBER : 'fore:#074E4E',
                             wx.stc.STC_P_STRING : 'fore:#1D701B',
                             wx.stc.STC_P_CHARACTER: wx.stc.STC_P_STRING,
                             wx.stc.STC_P_WORD: 'fore:#000000,bold',
                             wx.stc.STC_P_TRIPLE: wx.stc.STC_P_STRING,
                             wx.stc.STC_P_TRIPLEDOUBLE: wx.stc.STC_P_STRING,
                             wx.stc.STC_P_CLASSNAME: 'fore:#0000FF,bold,italic',
                             wx.stc.STC_P_DEFNAME: 'fore:#0000ff,bold',
                             wx.stc.STC_P_OPERATOR: 'bold',
                             wx.stc.STC_P_IDENTIFIER: '',
                             wx.stc.STC_P_COMMENTBLOCK: 'fore:%(comment-col)s,bold',
                             wx.stc.STC_P_STRINGEOL: 'fore:#000000,back:#ECD7EC,eolfilled',
                             },
        }

    ##
    # tab the line to the correct indent (matching the line above)
    def electricTab(self):
        s=self.stc
        
        # From PyPE:
        #get information about the current cursor position
        linenum = s.GetCurrentLine()
        pos = s.GetCurrentPos()
        col = s.GetColumn(pos)
        linestart = s.PositionFromLine(linenum)
        line = s.GetLine(linenum)[:pos-linestart]
    
        #get info about the current line's indentation
        ind = s.GetLineIndentation(linenum)

    def getFunctionList(self):
        import peppy.pype.parsers
        flist=peppy.pype.parsers.slower_parser(self.stc.GetText(),'\n',3,lambda:None)
        self.dprint(flist)
        return flist


class PythonPlugin(MajorModeMatcherBase,debugmixin):
    implements(IMajorModeMatcher)
    implements(IMenuItemProvider)
    implements(IToolBarItemProvider)

    def possibleModes(self):
        yield PythonMode
    
    default_menu=((None,None,Menu("Test").after("Minor Mode")),
                  (None,"Test",MenuItem(SamplePython)),
                  ("Python",None,Menu("Python").after("Major Mode")),
                  ("Python","Python",MenuItem(ShiftLeft)),
                  ("Python","Python",MenuItem(ShiftRight)),
                  )
    def getMenuItems(self):
        for mode,menu,item in self.default_menu:
            yield (mode,menu,item)

    default_tools=(("Python",None,Menu("Python").after("Major Mode")),
                   ("Python","Python",MenuItem(ShiftLeft)),
                   ("Python","Python",MenuItem(ShiftRight)),
                   )
    def getToolBarItems(self):
        for mode,menu,item in self.default_tools:
            yield (mode,menu,item)
