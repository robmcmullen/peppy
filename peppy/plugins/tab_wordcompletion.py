# -*- coding: UTF-8 -*-
# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
# WordCompletion Copyright (c) 2008 Frank Atle Rød  frankatle@gmail.com
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info

from peppy.yapsy.plugins import *
from peppy.minor import *
from peppy.actions import *
from peppy.buffers import *
import re

from peppy.about import AddAuthor
AddAuthor("Frank Atle R\xc3\xb8d", "for the bash-style tab completion plugin")


class Range:
    def __init__(self, start = 0, end = 0):
        self.start = start
        self.end = end
    def start(self):
        return self.start
    
    def end(self):
        return self.end
    
    def is_empty(self):
        empty = False
        if self.start==0 and self.end==0:
            empty = True
        return empty
    
    def is_valid(self):
        if(self.start < self.end):
            return_value = True
        else:
            return_value = False
        return return_value

class CompleteWordHelper:
    word             = None
    completedPos     = None
    compString       = ""
    matches          = []
    completionNumber = 0
    range            = Range()

class Complete_or_indent(SelectAction):
    alias = "complete_or_indent"
    name = "Complete word"
    tooltip = "complete word at the current cursor position"
    icon = None
    key_bindings = {'win': "Ctrl-Tab", 'emacs': "C-TAB"}
    c = CompleteWordHelper()
    
    @classmethod
    def worksWithMajorMode(cls, modecls):
        return hasattr(modecls, 'AddText')
    
    def isEnabled(self):
        return not self.mode.buffer.busy
    
    def matches(self, word, range):
        if TabCompletionPlugin.classprefs.allOpenDocs:
            #search after keyword in all open documents
            #TODO: make allOpenDocs a settings alternative
            #TODO: only add textbuffers to bufferlist 
            searchtext = ""
            bufferlist = BufferList.getBuffers()
            for i in bufferlist:
                if not i.permanent:
                    searchtext = searchtext + i.stc.GetText() + "\n"
        else:
            searchtext = self.mode.GetText()
        allmatches = re.findall("\\b" + re.escape(word) + "\\w+", searchtext )
        allmatches.append(self.word(range))
        allmatches = set(allmatches)
        allmatches = list(allmatches)
        allmatches.sort()
        return allmatches
    
    def range(self):
        return_word = ""
        linetext,linepos = self.mode.GetCurLine()
        currentpos = self.mode.GetCurrentPos()
        if(linepos != 0 ):
            if not re.search(r'\A\s|\A\W',linetext[linepos:]): #Do not complete if the cursor is in the middle of a word
                return Range()
            linetext = linetext[0:linepos]
            return_word = re.findall("(?:[a-zA-Z0-9_\\.]|->|::)+", linetext)
            if(return_word):
                return_word = return_word[ len(return_word) - 1]
            else:
                return_word = ""
            if(re.search(r'\A\w+', return_word) != None):
                r = Range(currentpos - len(return_word), currentpos)
            else:
                r = Range()
        else:
            r = Range()
        return r
    
    def matchword(self, r):
        _word = self.mode.GetTextRange(r.start, r.end)
        _word = re.sub(r"\.","\.", _word)
        return _word
    
    def word(self, r):
        return self.mode.GetTextRange(r.start, r.end)
    
    def removetext(self, r):
        self.mode.SetTargetStart(r.start)
        self.mode.SetTargetEnd(r.end)
        self.mode.ReplaceTarget("")
        
    
    def complete(self):
        range = self.range()
        
        if(range.is_empty()):
            return False
        
        if(self.c.completedPos == self.mode.GetCurrentPos()):
            if(self.c.compString == self.word(range)):
                self.c.range = range
            else:
                self.c.range = Range(0,0)
        else:
            self.c.range = Range(0,0)
        
        if(self.c.range.is_valid()):
            if(self.c.completionNumber == len(self.c.matches)):
                self.c.completionNumber = 0
                
            self.removetext(range)
            self.c.compString = self.c.matches[self.c.completionNumber]
            self.mode.AddText(self.c.compString)
            self.c.completedPos = self.mode.GetCurrentPos()
            self.c.completionNumber = self.c.completionNumber + 1
        
        else:
            self.c.matches = self.matches(self.matchword(range), range)
            if(len(self.c.matches) > 1):
                self.c.completionNumber = 1
                self.c.compString = self.c.matches[self.c.completionNumber]
                self.c.range = range
                self.removetext(range)
                self.mode.AddText(self.c.compString)
                self.c.completedPos = self.mode.GetCurrentPos()
                self.c.completionNumber = self.c.completionNumber + 1
            else:
                return False
        return True
    
    def action(self, index=-1, multiplier=1):
        if not self.complete():
            self.mode.autoindent.processTab(self.mode)
        
                
class TabCompletionPlugin(IPeppyPlugin):
    default_classprefs = (
        BoolParam('allOpenDocs',True,'Search for completion matches in all documents'),
        )
    def getActions(self):
        return [Complete_or_indent]
    
    
