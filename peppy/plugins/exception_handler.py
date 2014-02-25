# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
# Copyright (c) 2008 Cody Precord <staff@editra.org>
# License: wxWindows License
import os, sys, platform, traceback, time, codecs, locale, webbrowser

import wx
import wx.stc
from wx.lib.pubsub import Publisher

import peppy.vfs as vfs

from peppy import __version__, __url__, __bug_report_email__
from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.debug import *

from peppy.about import AddCopyright

AddCopyright("Editra", "http://www.editra.org", "Cody Precord", "2005-2009", "The error reporting dialog from")


def EnvironmentInfo():
    """Returns a string of the systems information
    @return: System information string

    """
    info = list()
    info.append("#---- Notes ----#")
    info.append("Please provide additional information about the crash here")
    info.extend(["", ""])
    info.append("#---- System Information ----#")
    info.append("%s Version: %s" % ('Peppy', __version__))
    info.append("Operating System: %s" % wx.GetOsDescription())
    if sys.platform == 'darwin':
        info.append("Mac OSX: %s" % platform.mac_ver()[0])
    info.append("Python Version: %s" % sys.version)
    info.append("wxPython Version: %s" % wx.version())
    info.append("wxPython Info: (%s)" % ", ".join(wx.PlatformInfo))
    info.append("Python Encoding: Default=%s  File=%s" % \
                (sys.getdefaultencoding(), sys.getfilesystemencoding()))
    info.append("wxPython Encoding: %s" % wx.GetDefaultPyEncoding())
    info.append("System Architecture: %s %s" % (platform.architecture()[0], \
                                                platform.machine()))
    info.append("Byte order: %s" % sys.byteorder)
    info.append("Frozen: %s" % str(getattr(sys, 'frozen', 'False')))
    info.append("#---- End System Information ----#")
    info.append("")
    return os.linesep.join(info)

def ExceptionHook(exctype, value, trace):
    """Handler for all unhandled exceptions
    @param exctype: Exception Type
    @param value: Error Value
    @param trace: Trace back info

    """
    ftrace = FormatTrace(exctype, value, trace)

    if ErrorDialog.ignore(ftrace):
        print("Ignoring %s: %s" % (exctype, value))
        return

    # Ensure that error gets raised to console as well
    print ftrace

    # If abort has been set and we get here again do a more forcefull shutdown
    if ErrorDialog.ABORT:
        os._exit(1)

    # Make sure the user gets control of the mouse if it has been captured
    capture = wx.Window.GetCapture()
    if capture:
        capture.ReleaseMouse()

    # Prevent multiple reporter dialogs from opening at once
    if not ErrorDialog.REPORTER_ACTIVE and not ErrorDialog.ABORT:
        ErrorDialog(ftrace)

def FormatTrace(etype, value, trace):
    """Formats the given traceback
    @return: Formatted string of traceback with attached timestamp

    """
    exc = traceback.format_exception(etype, value, trace)
    return u"".join(exc)

def TimeStamp():
    """Create a formatted time stamp of current time
    @return: Time stamp of the current time (Day Month Date HH:MM:SS Year)
    @rtype: string

    """
    now = time.localtime(time.time())
    now = time.asctime(now)
    return now

#-----------------------------------------------------------------------------#

class ErrorReporter(object):
    """Crash/Error Reporter Service
    @summary: Stores all errors caught during the current session.

    """
    instance = None
    _first = True
    def __init__(self):
        """Initialize the reporter
        @note: The ErrorReporter is a singleton.

        """
        # Ensure init only happens once
        if self._first:
            object.__init__(self)
            self._first = False
            self._sessionerr = list()
        else:
            pass

    def __new__(cls, *args, **kargs):
        """Maintain only a single instance of this object
        @return: instance of this class

        """
        if not cls.instance:
            cls.instance = object.__new__(cls, *args, **kargs)
        return cls.instance

    def AddMessage(self, msg):
        """Adds a message to the reporters list of session errors
        @param msg: The Error Message to save

        """
        if msg not in self._sessionerr:
            self._sessionerr.append(msg)

    def GetErrorStack(self):
        """Returns all the errors caught during this session
        @return: formatted log message of errors

        """
        return (os.linesep * 2).join(self._sessionerr)

    def GetLastError(self):
        """Gets the last error from the current session
        @return: Error Message String

        """
        if len(self._sessionerr):
            return self._sessionerr[-1]
        
#-----------------------------------------------------------------------------#

ID_SEND = wx.NewId()
ID_IGNORE = wx.NewId()
class ErrorDialog(wx.Dialog):
    """Dialog for showing errors and and notifying Editra.org should the
    user choose so.

    """
    ABORT = False
    REPORTER_ACTIVE = False
    
    user_requested_ignore = {}
    
    @classmethod
    def ignore(cls, message):
        return message in cls.user_requested_ignore
    
    def __init__(self, message):
        """Initialize the dialog
        @param message: Error message to display

        """
        ErrorDialog.REPORTER_ACTIVE = True
        wx.Dialog.__init__(self, None, title=_("Error/Crash Reporter"), 
                           style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER)
        
        # Save message in case the user wants to ignore further occurrences
        self._message = message
        
        # Add timestamp and give message to ErrorReporter
        message = u"*** %s ***%s" % (TimeStamp(), os.linesep) + message
        ErrorReporter().AddMessage(message)

        # Attributes
        self.err_msg = os.linesep.join((EnvironmentInfo(),
                                        "#---- Traceback Info ----#",
                                        ErrorReporter().GetErrorStack(),
                                        "#---- End Traceback Info ----#"))

        # Layout
        self._panel = ErrorPanel(self, self.err_msg)
        self._DoLayout()
        self.SetMinSize(wx.Size(450, 300))

        # Event Handlers
        self.Bind(wx.EVT_BUTTON, self.OnButton)
        self.Bind(wx.EVT_CLOSE, self.OnClose)

        # Auto show at end of init
        self.CenterOnParent()
        self.ShowModal()

    def _DoLayout(self):
        """Layout the dialog and prepare it to be shown
        @note: Do not call this method in your code

        """
        msizer = wx.BoxSizer(wx.VERTICAL)
        msizer.Add(self._panel, 1, wx.EXPAND)
        self.SetSizer(msizer)
        self.SetInitialSize()

    def OnButton(self, evt):
        """Handles button events
        @param evt: event that called this handler
        @postcondition: Dialog is closed
        @postcondition: If Report Event then email program is opened

        """
        e_id = evt.GetId()
        if e_id == wx.ID_CLOSE:
            self.Close()
        elif e_id == ID_SEND:
            msg = "mailto:%s?subject=Peppy Error Report&body=%s"
            msg = msg % (__bug_report_email__, self.err_msg)
            msg = msg.replace("'", '')
            webbrowser.open(msg)
            self.Close()
        elif e_id == wx.ID_ABORT:
            ErrorDialog.ABORT = True
            # Try a nice shutdown first time through
            wx.CallLater(500, wx.GetApp().quit)
            self.Close()
        elif e_id == wx.ID_IGNORE:
            self.user_requested_ignore[self._message] = True
            self.Close()
        else:
            evt.Skip()

    def OnClose(self, evt):
        """Cleans up the dialog when it is closed
        @param evt: Event that called this handler

        """
        ErrorDialog.REPORTER_ACTIVE = False
        self.EndModal(1)
        self.Destroy()
        evt.Skip()

#-----------------------------------------------------------------------------#

class ErrorPanel(wx.Panel):
    """Error Reporter panel"""
    def __init__(self, parent, msg):
        """Create the panel
        @param parent: wx.Window
        @param msg: Error message to display

        """
        wx.Panel.__init__(self, parent)

        self.err_msg = msg
        
        self.__DoLayout()

    def __DoLayout(self):
        """Layout the control"""
        icon = wx.StaticBitmap(self, 
                               bitmap=wx.ArtProvider.GetBitmap(wx.ART_ERROR))
        mainmsg = wx.StaticText(self, 
                                label=_("Error: Something unexpected happened.  You can attempt to continue,\nabort the program, or send an error report."))
        t_lbl = wx.StaticText(self, label=_("Error Traceback:"))
        tctrl = wx.TextCtrl(self, value=self.err_msg, size=(600, -1),
                            style=wx.TE_MULTILINE | wx.TE_READONLY)

        abort_b = wx.Button(self, wx.ID_ABORT, _("Abort"))
        abort_b.SetToolTipString(_("Exit the application"))
        close_b = wx.Button(self, wx.ID_CLOSE, ("Attempt to Continue"))
        send_b = wx.Button(self, ID_SEND, _("... and Send Error Report"))
        send_b.SetDefault()
        ignore_b = wx.Button(self, wx.ID_IGNORE, ("Ignore Reoccurrences"))

        # Layout
        vsizer = wx.BoxSizer(wx.VERTICAL)

        hsizer1 = wx.BoxSizer(wx.HORIZONTAL)
        hsizer1.AddMany([((5, 5), 0), (icon, 0, wx.ALIGN_CENTER_VERTICAL),
                         ((12, 5), 0), (mainmsg, 0), ((5, 5), 0)])

        hsizer2 = wx.BoxSizer(wx.HORIZONTAL)
        hsizer2.AddMany([((5, 5), 0), (tctrl, 1, wx.EXPAND), ((5, 5), 0)])

        bsizer = wx.BoxSizer(wx.HORIZONTAL)
        bsizer.AddMany([((5, 5), 0), (abort_b, 0), ((-1, -1), 1, wx.EXPAND),
                        (close_b, 0), ((5, 5), 0), (send_b, 0), ((5, 5), 0),
                        (ignore_b, 0), ((5, 5), 0)])

        vsizer.AddMany([((5, 5), 0),
                        (hsizer1, 0),
                        ((10, 10), 0),
                        (t_lbl, 0, wx.ALIGN_LEFT),
                        ((3, 3), 0),
                        (hsizer2, 1, wx.EXPAND),
                        ((8, 8), 0),
                        (bsizer, 0, wx.EXPAND),
                        ((8, 8), 0)])

        self.SetSizer(vsizer)
        self.SetAutoLayout(True)


class TestException(SelectAction):
    """Raise an unhandled exception to test the exception handler dialog"""
    name = "Raise Unhandled Exception"
    default_menu = "Tools/Debug"

    def action(self, index=-1, multiplier=1):
        raise RuntimeError("Just a test exception!")


class ExceptionHandler(IPeppyPlugin):
    """Plugin that provides an unhandled exception dialog to provide the user
    with some information in the event of a catastrophic error.
    """
    save_system_excepthook = sys.excepthook
    
    def activateHook(self):
        sys.excepthook = ExceptionHook
    
    def deactivateHook(self):
        sys.excepthook = self.save_system_excepthook

    def getActions(self):
        return [TestException]
