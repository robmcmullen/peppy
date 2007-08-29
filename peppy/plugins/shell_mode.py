# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
import os,re
import urllib2

import wx
import wx.stc
import wx.lib.newevent

from cStringIO import StringIO

from peppy import *
from peppy.major import *
from peppy.menu import *
from peppy.iofilter import *
from peppy.trac.core import *
from peppy.fundamental import FundamentalMode
from peppy.stcinterface import PeppySTC

class ShellPipePlugin(Interface):
    """
    Interface for shells that take a line of input and return a response.
    """

    def supportedShells():
        """
        Return a list of shells that this interface supports, e.g. a
        bash shell should return ['bash'] or python should return
        ['python'].
        """
        
    def getPipe(filename):
        """
        Return a file-like object that is the interface to the shell.
        Typically this will act like a pipe to an object: stuff that
        is written to this file handle will get sent through the pipe
        to the shell, and when data is available it can be read from
        this object.
        """

class ShellHandler(urllib2.BaseHandler):
    def shell_open(self, req):
        url = req.get_selector()
        dprint(url)

        comp_mgr = ComponentManager()
        handler = ShellPlugin(comp_mgr)
        fh = handler.find(url)
        fh.geturl = lambda :"shell:%s" % url
        fh.info = lambda :{'Content-type': 'text/plain',
                            'Content-length': 0,
                            'Last-modified': 'Sat, 17 Feb 2007 20:29:30 GMT',
                            }        
        return fh


# This creates a new Event class and a EVT binder function used when
# new shell when new data is available to be read.
(ShellUpdateEvent, EVT_SHELL_UPDATE) = wx.lib.newevent.NewEvent()


class ShellSTC(PeppySTC):
    """
    Specialized STC used as the buffer of a shell mode.  Note, setting
    the cursor position on this STC doesn't affect the views directly.
    This is the data storage STC, not the viewing STC.
    """
    debuglevel=0

    def __init__(self, parent, copy=None):
        PeppySTC.__init__(self, parent, copy=copy)
        self.pipe=None
        self.waiting=False
        self.promptPosEnd=0
        self.filter=1
        self.more=0

    def open(self, url):
        """Save the file handle, which is really the mpd connection"""
        self.pipe = url.getDirectReader()
        self.readFrom(self.pipe)
        length=self.GetTextLength()
        self.SetCurrentPos(length)
        self.AddText('\n')
        self.prompt()
        
        self.pipe.setNotifyWindow(self)
        self.Bind(EVT_SHELL_UPDATE,self.OnReadable)

    def prompt(self):
        if self.filter:
            skip = False
            if self.more:
                prompt = self.pipe.ps2
            else:
                prompt = self.pipe.ps1
            pos = self.GetCurLine()[1]
            if pos > 0:
                self.AddText('\n')
            if not self.more:
                self.promptPosEnd = self.GetCurrentPos()
            if not skip:
                self.AddText(prompt)
        if not self.more:
            self.promptPosEnd = self.GetCurrentPos()
            # Keep the undo feature from undoing previous responses.
            self.EmptyUndoBuffer()

    def send(self,cmd):
        self.pipe.write(cmd)
        self.waiting=True

    def OnReadable(self,evt=None):
        text=self.pipe.read()
        if len(text)>0:
            text=text.rstrip('\n\r')
            self.AddText(text)
            self.AddText('\n')
            self.prompt()
            self.waiting=False
            # Send ShellUpdate event to viewer STCs to tell them to
            # update their cursor positions.
            self.sendEvents(ShellUpdateEvent)

    def process(self,viewer):
        startpos = self.promptPosEnd
        endpos = self.GetTextLength()
        
        tosend = self.GetTextRange(startpos, endpos) + '\n'
        
        self.SetCurrentPos(endpos)
        self.AddText('\n')
        self.promptPosEnd = endpos + 1
        self.SetCurrentPos(self.promptPosEnd)
        self.send(tosend)
        

    def OnModified(self, evt):
        PeppySTC.OnModified(self,evt)

# FIXME: this is hidden by Fundamental's ElectricReturn action...  To
# workaround this, have to create an electric return mixin for ShellMode
# A better way to work around is to have the most recent major mode with
# a duplicate key binding override the superclass's action for that
# keybinding.
class ProcessShellLine(SelectAction):
    debuglevel = 0
    
    name = "Process a shell command"
    tooltip = "Process a shell command."
    key_bindings = {'default': 'RET', }

    def action(self, pos=-1):
        assert self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        viewer=self.frame.getActiveMajorMode()
        if viewer:
            viewer.buffer.stc.process(viewer)

class ShellReturnMixin(object):
    def electricReturn(self):
        self.buffer.stc.process(self)

class ShellMode(ShellReturnMixin, FundamentalMode):
    debuglevel=0
    
    keyword='Shell'
    icon='icons/application_xp_terminal.png'
    regex = None
    
    stc_class = ShellSTC
    
    @classmethod
    def verifyProtocol(cls, url):
        if url.protocol == 'shell':
            return True
        return False

    def createWindowPostHook(self):
        assert self.dprint("In shell.")
        self.stc.Bind(wx.stc.EVT_STC_MODIFIED, self.OnUpdate)

        #Use an event listener to update the cursor position when the
        #underlying shell has changed.
        self.stc.Bind(EVT_SHELL_UPDATE, self.OnUpdateCursorPos)
        self.OnUpdateCursorPos()

    def OnUpdateCursorPos(self,evt=None):
        assert self.dprint("cursor position = %d" % self.buffer.stc.GetCurrentPos())
        self.stc.GotoPos(self.buffer.stc.GetCurrentPos())
        self.stc.EnsureCaretVisible()
        self.stc.ScrollToColumn(0)

    def OnUpdate(self,evt=None):
        assert self.dprint("Updated!")
        


class ShellPlugin(MajorModeMatcherBase,debugmixin):
    implements(IMajorModeMatcher)
    implements(IKeyboardItemProvider)
    implements(IURLHandler)
    shells=ExtensionPoint(ShellPipePlugin)

    def getURLHandlers(self):
        return [ShellHandler]
    
    def find(self, url):
        for shell in self.shells:
            if url in shell.supportedShells():
                fh=shell.getPipe(url)
                return fh
        raise IOError("shell %s not found" % url)        
    
    def possibleModes(self):
        yield ShellMode
    
    default_keys=(("Shell",ProcessShellLine),
                  )
    def getKeyboardItems(self):
        for mode,action in self.default_keys:
            yield (mode,action)
