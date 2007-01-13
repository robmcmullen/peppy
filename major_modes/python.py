import os,struct
import keyword

import wx
import wx.stc as stc

from menudev import *
from buffers import *

from views import *
from plugin import *
from major_modes.fundamental import FundamentalMode

from debug import *

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
        

class UsePythonMajorMode(FrameAction):
    name = "Change to Python Major Mode"
    tooltip = "Change to python editor"
    icon = "icons/folder_page.png"
    keyboard = "C-X C-P"

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.changeMajorMode(PythonMode)



if wx.Platform == '__WXMSW__':
    faces = { 'times': 'Times New Roman',
              'mono' : 'Courier New',
              'helv' : 'Arial',
              'other': 'Comic Sans MS',
              'size' : 10,
              'size2': 8,
             }
else:
    faces = { 'times': 'Times',
              'mono' : 'Courier',
              'helv' : 'Helvetica',
              'other': 'new century schoolbook',
              'size' : 10,
              'size2': 8,
             }

class PythonMode(PythonIndentMixin,PythonElectricReturnMixin,FundamentalMode):
    pluginkey = 'python'
    keyword='Python'
    icon='icons/py.ico'
    regex="\.(py|pyx)$"
    lexer=stc.STC_LEX_PYTHON

    defaultsettings={
        'menu_actions':[
            [[('&Python',0.5)],ShiftLeft,0.2],
            [ShiftRight],
            ],
        'toolbar_actions':[
            [ShiftLeft,0.5],
            [ShiftRight],
            ],
        }

    def getKeyWords(self):
        return [(0," ".join(keyword.kwlist))]

    def styleSTC(self):
        self.format=os.linesep
        
        s=self.stc

        face1 = 'Arial'
        face2 = 'Times New Roman'
        face3 = 'Courier New'
        pb = 10

        # Show mixed tabs/spaces
        s.SetProperty("tab.timmy.whinge.level", "1")
        
        # Global default styles for all languages
        s.StyleSetSpec(stc.STC_STYLE_DEFAULT,     "face:%(mono)s,size:%(size)d" % faces)
        s.StyleClearAll()  # Reset all to be like the default

        # Global default styles for all languages
        s.StyleSetSpec(stc.STC_STYLE_DEFAULT,     "face:%(mono)s,size:%(size)d" % faces)
        s.StyleSetSpec(stc.STC_STYLE_LINENUMBER,  "back:#C0C0C0,face:%(mono)s,size:%(size2)d" % faces)
        s.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, "face:%(other)s" % faces)
        s.StyleSetSpec(stc.STC_STYLE_BRACELIGHT,  "fore:#FFFFFF,back:#0000FF,bold")
        s.StyleSetSpec(stc.STC_STYLE_BRACEBAD,    "fore:#000000,back:#FF0000,bold")

        # Python styles
        # Default 
        s.StyleSetSpec(stc.STC_P_DEFAULT, "fore:#000000,face:%(mono)s,size:%(size)d" % faces)
        # Comments
        s.StyleSetSpec(stc.STC_P_COMMENTLINE, "fore:#007F00,face:%(mono)s,size:%(size)d" % faces)
        # Number
        s.StyleSetSpec(stc.STC_P_NUMBER, "fore:#007F7F,size:%(size)d" % faces)
        # String
        s.StyleSetSpec(stc.STC_P_STRING, "fore:#7F007F,face:%(mono)s,size:%(size)d" % faces)
        # Single quoted string
        s.StyleSetSpec(stc.STC_P_CHARACTER, "fore:#7F007F,face:%(mono)s,size:%(size)d" % faces)
        # Keyword
        s.StyleSetSpec(stc.STC_P_WORD, "fore:#00007F,bold,size:%(size)d" % faces)
        # Triple quotes
        s.StyleSetSpec(stc.STC_P_TRIPLE, "fore:#7F0000,size:%(size)d" % faces)
        # Triple double quotes
        s.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, "fore:#7F0000,size:%(size)d" % faces)
        # Class name definition
        s.StyleSetSpec(stc.STC_P_CLASSNAME, "fore:#0000FF,bold,underline,size:%(size)d" % faces)
        # Function or method name definition
        s.StyleSetSpec(stc.STC_P_DEFNAME, "fore:#007F7F,bold,size:%(size)d" % faces)
        # Operators
        s.StyleSetSpec(stc.STC_P_OPERATOR, "bold,size:%(size)d" % faces)
        # Identifiers
        s.StyleSetSpec(stc.STC_P_IDENTIFIER, "fore:#000000,face:%(mono)s,size:%(size)d" % faces)
        # Comment-blocks
        s.StyleSetSpec(stc.STC_P_COMMENTBLOCK, "fore:#7F7F7F,face:%(mono)s,size:%(size)d" % faces)
        # End of line where string is not closed
        s.StyleSetSpec(stc.STC_P_STRINGEOL, "fore:#000000,face:%(mono)s,back:#E0C0E0,eol,size:%(size)d" % faces)


        # line numbers in the margin
        s.SetMarginType(0, stc.STC_MARGIN_NUMBER)
        s.SetMarginWidth(0, 30)
        s.StyleSetSpec(stc.STC_STYLE_LINENUMBER, "size:%d,face:%s" % (pb, face1))

        # turn off symbol margin
        s.SetMarginWidth(1, 0)

        # turn off folding margin
        s.SetMarginWidth(2, 0)

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
        import pype.parsers
        flist=pype.parsers.slower_parser(self.stc.GetText(),'\n',3,lambda:None)
        self.dprint(flist)
        return flist


global_menu_actions=[
    [[('&Test',0.1)],UsePythonMajorMode,0.9],
]

class PythonPlugin(MajorModeMatcherBase,debugmixin):
    implements(IMajorModeMatcher)

    def scanEmacs(self,emacsmode,vars):
        if emacsmode in ['python',PythonMode.keyword]:
            return MajorModeMatch(PythonMode,exact=True)
        return None

    def scanShell(self,bangpath):
        if bangpath.find('python')>-1:
            return MajorModeMatch(PythonMode,exact=True)
        return None

    def scanFilename(self,filename):
        if filename.endswith('.py'):
            return MajorModeMatch(PythonMode,exact=True)
        return None
