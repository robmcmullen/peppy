# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os,re
import urllib2
from cStringIO import StringIO

import wx
import wx.stc
import wx.lib.newevent

import peppy.vfs as vfs

from peppy.yapsy.plugins import *
from peppy.major import *
from peppy.menu import *
from peppy.fundamental import *
from peppy.stcbase import PeppySTC


class ShellFS(vfs.BaseFS):
    @classmethod
    def find_pipe(cls, reference):
        shell = str(reference.path)
        plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
        for plugin in plugins:
            if shell in plugin.supportedShells():
                fh=plugin.getPipe(shell)
                return fh
        raise IOError("shell %s not found" % url)
        
    @staticmethod
    def exists(reference):
        shell = str(reference.path)
        plugins = wx.GetApp().plugin_manager.getActivePluginObjects()
        for plugin in plugins:
            if shell in plugin.supportedShells():
                return True
        return False

    @staticmethod
    def is_file(reference):
        return True

    @classmethod
    def is_folder(cls, reference):
        return False

    @staticmethod
    def can_read(reference):
        return True

    @staticmethod
    def can_write(reference):
        return False

    @staticmethod
    def get_size(reference):
        return 0

    @classmethod
    def open(cls, ref, mode=None):
        fh = cls.find_pipe(ref)
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

    def open(self, buffer, progress_message):
        """Save the file handle, which is really the mpd connection"""
        self.pipe = vfs.open(buffer.url)
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


class ShellMode(FundamentalMode):
    """This is the viewer STC that is the front-end to the user.
    
    This STC handles the display and interaction, overriding
    FundamentalMode's electricReturn in order to handle the user
    interaction. 
    """
    debuglevel=0
    
    keyword='Shell'
    icon='icons/application_xp_terminal.png'
    regex = None
    
    stc_class = ShellSTC
    
    @classmethod
    def verifyProtocol(cls, url):
        if url.scheme == 'shell':
            return True
        return False

    def createWindowPostHook(self):
        assert self.dprint("In shell.")
        self.Bind(wx.stc.EVT_STC_MODIFIED, self.OnUpdate)

        #Use an event listener to update the cursor position when the
        #underlying shell has changed.
        self.Bind(EVT_SHELL_UPDATE, self.OnUpdateCursorPos)
        self.OnUpdateCursorPos()

    def OnUpdateCursorPos(self,evt=None):
        assert self.dprint("cursor position = %d" % self.buffer.stc.GetCurrentPos())
        self.GotoPos(self.buffer.stc.GetCurrentPos())
        self.EnsureCaretVisible()
        self.ScrollToColumn(0)

    def OnUpdate(self,evt=None):
        assert self.dprint("Updated!")
        
    def electricReturn(self):
        # Call the reference stc's (i.e. the ShellSTC instance)
        # process command, because it is the reference STC that
        # knows how to communicate with the shell process
        self.refstc.process()


class ShellPlugin(IPeppyPlugin):
    def activate(self):
        IPeppyPlugin.activate(self)
        vfs.register_file_system('shell', ShellFS)

    def deactivate(self):
        IPeppyPlugin.deactivate(self)
        vfs.deregister_file_system('shell')

    def getMajorModes(self):
        yield ShellMode
