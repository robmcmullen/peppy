# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Shell plugin and wrapper around the nltk_lite chatbots.
"""

import os,re

import wx

from cStringIO import StringIO

from peppy import *
from peppy.trac.core import *
from peppy.major_modes.shell import *

import peppy.nltk_lite.chat.eliza
import peppy.nltk_lite.chat.zen
import peppy.nltk_lite.chat.iesha
import peppy.nltk_lite.chat.rude

class ChatShell(Component):
    implements(ShellPipePlugin)

    def __init__(self):
        self.modules={'eliza':[nltk_lite.chat.eliza.eliza,
                               "Hello.  How are you feeling today?"],
                      'zen':[nltk_lite.chat.zen.zen,
                             "Welcome, my child."],
                      'iesha':[nltk_lite.chat.iesha.iesha,
                               "hi!! i'm iesha! who r u??!"],
                      'rude':[nltk_lite.chat.rude.rude,
                              "I suppose I should say hello."],
                      }

    def supportedShells(self):
        return self.modules.keys()

    def getPipe(self,filename):
        if filename in self.modules.keys():
            return ChatWrapper(*self.modules[filename])


class ChatWrapper(debugmixin):
    debuglevel=0
    ps1="> "
    ps2=">> "
    
    def __init__(self,chatbot,greeting):
        self.therapist=chatbot
        self.greeting=greeting
        self.pending=StringIO()
        self.pending.write(self.greeting)
        self._notify_window=None
        
    def setNotifyWindow(self,win):
        self._notify_window=win

    def read(self):
        txt=self.pending.getvalue()
        self.pending=StringIO()
        return txt

    def write(self,s):
        while s[-1] in "!.": s = s[:-1]
        response=self.therapist.respond(s)
        self.dprint("'%s' -> '%s'" % (s,response))
        self.pending.write(response)
        wx.PostEvent(self._notify_window,ShellUpdateEvent())
    

if __name__ == "__main__":
    s = ""
    therapist = ChatWrapper('eliza',"Hello.  How are you feeling today?");
    print therapist.read()
    while s != "quit":
        try:
            s = raw_input(">")
        except EOFError:
            s = "quit"
            print s
        therapist.write(s)
        print therapist.read()
    

