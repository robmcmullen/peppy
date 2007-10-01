# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Shell plugin and wrapper around the nltk_lite chatbots.

Basically this is just an adapter around the nltk_lite chatbots that
provides the pipe-based interfaces that ShellPipe classes expect.
"""

import os,re
from cStringIO import StringIO

import wx

from peppy.yapsy.plugins import *
from peppy.debug import *

from peppy.nltk_lite.chat import *

from peppy.about import AddCopyright
AddCopyright("Natural Language Toolkit", "http://nltk.sourceforge.net/", "2001-2006", "University of Pennsylvania", "Eliza and the other chatbot implementations")

class ChatPlugin(IShellPipePlugin):
    def supportedShells(self):
        return chatbots.keys()

    def getPipe(self,filename):
        if filename in chatbots.keys():
            return ChatWrapper(*chatbots[filename])


class ChatWrapper(debugmixin):
    debuglevel=0
    ps1="> "
    ps2=">> "
    
    def __init__(self,chatbot,greeting):
        self.therapist=chatbot
        self.greeting=greeting
        self.pending=StringIO()
        self.pending.write(self.greeting)
        self._notify_window = None
        self._notify_event = None
        
    def setNotifyWindow(self, win, event):
        self._notify_window = win
        self._notify_event = event

    def read(self, size=0):
        txt=self.pending.getvalue()
        self.pending=StringIO()
        return txt

    def write(self,s):
        while s[-1] in "!.": s = s[:-1]
        response=self.therapist.respond(s)
        assert self.dprint("'%s' -> '%s'" % (s,response))
        self.pending.write(response)
        wx.PostEvent(self._notify_window, self._notify_event())

    def close(self):
        self.pending=StringIO()
        self.pending.write(self.greeting)
    

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
    

