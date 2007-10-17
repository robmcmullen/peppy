# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
import os,re
import urllib2
from cStringIO import StringIO

import wx
import wx.stc
import wx.lib.newevent

from peppy.yapsy.plugins import *
from peppy.major import *
from peppy.menu import *
from peppy.iofilter import *
from peppy.fundamental import *
from peppy.stcinterface import PeppySTC

class ShellHandler(urllib2.BaseHandler):
    def find_pipe(self, url):
        plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
        for plugin in plugins:
            if url in plugin.supportedShells():
                fh=plugin.getPipe(url)
                return fh
        raise IOError("shell %s not found" % url)
        
    def shell_open(self, req):
        url = req.get_selector()
        dprint(url)
    
        fh = self.find_pipe(url)
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

    def __init__(self, parent, **kwargs):
        PeppySTC.__init__(self, parent, **kwargs)
        self.pipe=None
        self.waiting=False
        self.promptPosEnd=0
        self.filter=1
        self.more=0

    def open(self, url, progress_message):
        """Save the file handle, which is really the mpd connection"""
        self.pipe = url.getDirectReader()
        self.readFrom(self.pipe)
        length=self.GetTextLength()
        self.SetCurrentPos(length)
        self.AddText('\n')
        self.prompt()
        
        self.pipe.setNotifyWindow(self, ShellUpdateEvent)
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

    def process(self):
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

    def GetModify(self):
        return False


class ShellViewerSTC(FundamentalSTC):
    """This is the viewer STC that is the front-end to the user.
    
    This STC handles the display and interaction, overriding
    FundamentalMode's electricReturn in order to handle the user
    interaction. 
    """
    def electricReturn(self):
        # Call the reference stc's (i.e. the ShellSTC instance)
        # process command, because it is the reference STC that
        # knows how to communicate with the shell process
        self.refstc.process()


class ShellMode(FundamentalMode):
    debuglevel=0
    
    keyword='Shell'
    icon='icons/application_xp_terminal.png'
    regex = None
    
    stc_class = ShellSTC
    stc_viewer_class = ShellViewerSTC
    
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
        


class ShellPlugin(IPeppyPlugin):
    def getURLHandlers(self):
        return [ShellHandler]
    
    def getMajorModes(self):
        yield ShellMode
