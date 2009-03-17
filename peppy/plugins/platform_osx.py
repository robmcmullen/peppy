# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os, re, threading
from cStringIO import StringIO

import wx
import wx.aui
import wx.stc
from wx.lib.pubsub import Publisher

import peppy.vfs as vfs

from peppy.frame import WindowList, BufferFrame

from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.menu import *
from peppy.lib.userparams import *

from peppy.stcbase import *
from peppy.major import EmptyMode
from peppy.debug import *
from peppy.buffers import *


class MacHiddenFrame(BufferFrame):
    """Special frame used to keep the OS X application open even if there are
    no visible frames on the screen.  On other platforms, the application
    quits when the last frame is deleted, but on OS X the application
    typically stays active with the ability to load files or handle files
    dropped onto the dock.
    """
    preferences_tab = None
    
    def initPositionAndSize(self):
        pos = (9000, 9000)
        size = (int(self.classprefs.width), int(self.classprefs.height))
        return pos, size
    
    def initRegisterWindow(self):
        # The Mac hidden frame isn't registered, so it doesn't show up in the
        # Window menu
        WindowList.setHiddenFrame(self)
    
    def initLoad(self, buffer, urls):
        wx.CallAfter(self.titleBuffer)
    
    def loadSidebars(self):
        pass

    def isOSXMinimalMenuFrame(self):
        return True
    
    def titleBuffer(self):
        BufferFrame.open(self, "about:osx_menu")
    
    def open(self, *args, **kwargs):
        """Convenience function overriding BufferFrame.open to open URLs in
        a new frame.
        
        This may be a temporary solution -- actions that set osx_minimal_menu
        may find that this leads to unexpected consequences if they are
        expecting all methods of BufferFrame to have this implicit behavior.
        """
        frame = BufferFrame(['about:blank'])
        wx.CallAfter(frame.open, *args, **kwargs)


class MacHiddenMode(EmptyMode):
    """
    The most minimal major mode: a blank screen
    """
    keyword = "MacHidden"
    icon='icons/apple.png'
    
    stc_class = NonResidentSTC
    
    preferences_tab = None

    @classmethod
    def verifyProtocol(cls, url):
        # Use the verifyProtocol to hijack the loading process and
        # immediately return the match if we're trying to load
        # about:blank
        if url.scheme == 'about' and url.path == 'osx_menu':
            return True
        return False


class PlatformOSX(IPeppyPlugin):
    """Plugin that provides OS X support
    """
    def activateHook(self):
        Publisher().subscribe(self.loadHiddenFrame, 'peppy.before_initial_frame_creation')
    
    def deactivateHook(self):
        Publisher().unsubscribe(self.loadHiddenFrame)
    
    def isOSX(self):
        return wx.Platform == '__WXMAC__'
    
    def loadHiddenFrame(self, msg):
        if self.isOSX():
            MacHiddenFrame()

    def getMajorModes(self):
        if self.isOSX():
            yield MacHiddenMode
