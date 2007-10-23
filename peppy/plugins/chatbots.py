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
from peppy.menu import *

from peppy.nltk_lite.chat import *

from peppy.about import AddCopyright
AddCopyright("Natural Language Toolkit", "http://nltk.sourceforge.net/", "University of Pennsylvania", "2001-2006", "Eliza and the other chatbot implementations from")


def action(self, index=-1, multiplier=1):
    """Dynamically created method for the Chatbot classes"""
    self.frame.open(self.bot_url)

def getActionClass(name):
    """Create a subclass of Action used to activate a chatbot.

    For each chatbot passed in to this function, return a dynamically
    created class that can be used as a menu item.
    """
    clsname = "Chatbot%s" % name.title()
    attrs = {
        "bot_url": "shell:%s" % name,
        "alias": _("chatbot-%s") % name,
        "name": _("Psychoanalyst (%s)" % name.title()),
        "tooltip": "Chat with the %s chatbot" % name,
        "default_menu": (("Tools/Games", -900), 900),
        "action": action,
        }

    # Create the new class using SelectAction as the base class and
    # using the attributes specified by the dictionary.
    cls = type(clsname, SelectAction.__mro__, attrs)
    return cls



class ChatPlugin(IPeppyPlugin):
    def supportedShells(self):
        return chatbots.keys()

    def getPipe(self,filename):
        if filename in chatbots.keys():
            return ChatWrapper(*chatbots[filename])

    # will become a dictionary mapping the bot name to the class
    actions = None

    def getActions(self):
        """Create a global menu item for each chatbot.

        Since we don't want to hard-code the chatbots, we have to
        dynamically create an Action class for each chatbot.  This is
        used to create the menu.  The class and menu creation is only
        done once, subsequent passes through here returns the cached
        menu.
        """
        if ChatPlugin.actions is None:
            actions = {}
            bots = chatbots.keys()
            bots.sort()
            for bot in chatbots.keys():
                actioncls = getActionClass(bot)
                actions[bot] = actioncls
            ChatPlugin.actions = actions

        actions = ChatPlugin.actions.values()
        return actions

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
    

