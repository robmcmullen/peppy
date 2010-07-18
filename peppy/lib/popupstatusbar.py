#-----------------------------------------------------------------------------
# Name:        popupstatusbar.py
# Purpose:     Google Chrome-like status bar that shows status messages in
#              a popup window for a limited period of time before disappearing
#
# Author:      Rob McMullen
#
# Created:     2010
# RCS-ID:      $Id: $
# Copyright:   (c) 2010 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""PopupStatusBar.

This file contains the PopupStatusBar class and a sample test program.
"""

import time
import wx
import wx.stc

class FakePopupWindow(wx.MiniFrame):
    def __init__(self, parent, style=None):
        super(FakePopupWindow, self).__init__(parent, style = wx.NO_BORDER |wx.FRAME_FLOAT_ON_PARENT | wx.FRAME_NO_TASKBAR)
        #self.Bind(wx.EVT_KEY_DOWN , self.OnKeyDown)
        self.Bind(wx.EVT_CHAR, self.OnChar)
        self.Bind(wx.EVT_SET_FOCUS, self.OnFocus)

    def OnChar(self, evt):
        #print("OnChar: keycode=%s" % evt.GetKeyCode())
        self.GetParent().GetEventHandler().ProcessEvent(evt)

    def Position(self, position, size):
        #print("pos=%s size=%s" % (position, size))
        self.Move((position[0]+size[0], position[1]+size[1]))
        
    def SetPosition(self, position):
        #print("pos=%s" % (position))
        self.Move((position[0], position[1]))
        
    def ActivateParent(self):
        """Activate the parent window
        @postcondition: parent window is raised

        """
        parent = self.GetParent()
        parent.Raise()
        parent.SetFocus()

    def OnFocus(self, evt):
        """Raise and reset the focus to the parent window whenever
        we get focus.
        @param evt: event that called this handler

        """
        #dprint("OnFocus: set focus to %s" % str(self.GetParent()))
        self.ActivateParent()
        evt.Skip()


if wx.Platform == "__WXMAC__":
    PopupClass = FakePopupWindow
else:
    PopupClass = wx.PopupWindow


class PopupStatusBar(PopupClass):
    """Transient status bar that displays status text in a popup
    
    Unlike a wx.StatusBar window that uses a constant amount of screen real-
    estate, the PopupStatusBar displays status info in a temporary popup
    that is displayed on the bottom of the frame.
    
    Status text can be displayed in two types: status text that is overwritten
    by each new status text update, and messages that are displayed in a list.
    
    Status text is always displayed at the bottom of the popup, and is
    overwritten with updates to the status text.  Status text is designed to
    be used for repetitive updates in response to an event; for example, to
    update coordinates when the mouse is moved.
    
    Messages are intended for more important communications to the user, for
    example as a status report in response to some action, or as a warning or
    error message.
    
    All messages have a decay time, where after that time is expired the
    message is removed from the status popup.  Messages are displayed with the
    most recent message on the bottom of the list and older messages toward
    the top.  Each new message is inserted at the bottom of the popup and
    pushes the existing messages up.
    
    To display menu help text like the wx.StatusBar does by default, capture
    the wx.EVT_MENU_HIGHLIGHT event and send the help text to the status bar
    using a method like:
    
    def OnMenuHighlight(self, evt):
        menu_id = evt.GetMenuId()
        if menu_id >= 0:
            help_text = self.GetMenuBar().GetHelpString(menu_id)
            if help_text:
                self.popup_status.showStatusText(help_text)

    """
    def __init__(self, frame, delay=5000, style=wx.BORDER_SIMPLE):
        """Creates (but doesn't show) the PopupStatusBar
        
        @param frame: the parent frame
        
        @kwarg delay: (optional) delay in milliseconds before each message
        decays
        """
        PopupClass.__init__(self, frame, style)
        self.SetBackgroundColour("#B6C1FF")
        
        self.stack = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.stack)
        
        self.timer = wx.Timer(self)
        self.delay = delay
        self.Bind(wx.EVT_TIMER, self.OnTimer)
        
        # Take over the frame's EVT_MENU_HIGHLIGHT
        frame.Bind(wx.EVT_MENU_HIGHLIGHT, self.OnMenuHighlight)
        
        # List of display times
        self.display_times = []
        self.last_is_status = False
        self.hold_status = False
        self.Hide()
    
    def showMessage(self, text):
        """Display a message in the status popup.
        
        This method is intended to be used for messages of some importance to
        the user.  These messages stay in the popup until the decay time for
        the message passes, whereupon it is removed from the popup.
        
        This forces the popup to be displayed if it isn't currently displayed.
        If the popup is displayed, the existing messages are moved up and
        this message is inserted at the bottom.
        
        @param text: message to display
        """
        self._addItemAtBottom(text, False)
        self.hold_status = False
    
    def showStatusText(self, text, hold=False):
        """Display a status text string in the status popup.
        
        This method is intended to display text in response to a large number
        of updates to a similar actions, for example: updating x,y coordinates
        in response to mouse movement.  It is undesirable to keep these
        messages in the list as the list would quickly grow to display many
        lines.  Instead, status text updates replace any previous status
        updates at the bottom of the popup.
        
        This forces the popup to be displayed if it isn't currently displayed.
        If the popup is displayed and other messages are present, the existing
        messages are moved up and this status text is inserted at the bottom.
        
        @param text: message to display
        """
        self._addItemAtBottom(text, True)
        self.hold_status = hold
    
    def _addItemAtBottom(self, text, is_status):
        text = text.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")
        st = wx.StaticText(self, -1, text)
        if self.last_is_status:
            old_time, old_st = self.display_times[-1]
            self.stack.Replace(old_st, st)
            old_st.Destroy()
            self.display_times[-1] = (time.time() * 1000, st)
        else:
            self.stack.Add(st, 0, wx.EXPAND)
            self.display_times.append((time.time() * 1000, st))
        self.last_is_status = is_status
        self.positionAndShow()
        if not self.timer.IsRunning():
            self.timer.Start(self.delay, True)

    def positionAndShow(self):
        self.Hide()
        self.stack.Fit(self)
        #self.stack.SetSizeHints(self)
        self.Layout()
        frame = self.GetParent()
        frame_offset = frame.GetClientAreaOrigin()
        frame_pos = frame.ClientToScreenXY(frame_offset[0], frame_offset[1])
        frame_size = frame.GetClientSizeTuple()
        win_size = self.GetSizeTuple()
        #print("frame pos: %s, size=%s  popup size=%s" % (str(frame_pos), str(frame_size), str(win_size)))
        x = frame_pos[0]
        y = frame_pos[1] + frame_size[1] - win_size[1]
        self.Position((x, y), (0,0))
        if win_size[0] > frame_size[0]:
            cropped_size = (frame_size[0], win_size[1])
            #print("Cropped! %s" % str(cropped_size))
            self.SetSize(cropped_size)
        self.Show(True)
    
    def clear(self):
        """Remove all messages and hide the popup"""
        while self.display_times:
            expired_time, expired_text = self.display_times.pop(0)
            self.stack.Remove(expired_text)
            expired_text.Destroy()
        self.Hide()
        self.last_is_status = False
        self.hold_status = False
        
    def OnTimer(self, evt):
        if not self.display_times:
            # It is possible the timer could go off after the call to clear(),
            # so if the list is empty, return without restarting the timer
            return
        current = time.time() * 1000
        #print("Timer at %f" % current)
        remove = True
        if (self.last_is_status and len(self.display_times) == 1):
            last_time, last_text = self.display_times[0]
            expires = last_time + self.delay
            #print("expires at: %d current=%d" % (expires, current))
            if self.hold_status:
                # recreate list to keep display current
                self.display_times = [(time.time() * 1000, last_text)]
                remove = False
            elif last_time + self.delay > current:
                remove = False
        if remove:
            expired_time, expired_text = self.display_times.pop(0)
            self.stack.Remove(expired_text)
            expired_text.Destroy()
        if self.display_times:
            remaining = self.delay - (current - self.display_times[0][0])
            #print("Next timer: %f" % remaining)
            #print("\n".join("%f" % d[0] for d in self.display_times))
            if remaining < 1:
                remaining = 1
            self.timer.Start(remaining, True)
            self.positionAndShow()
        else:
            self.clear()
        
    def OnMenuHighlight(self, evt):
        menu_id = evt.GetMenuId()
        if menu_id >= 0:
            help_text = self.GetParent().GetMenuBar().GetHelpString(menu_id)
            if help_text:
                self.showStatusText(help_text)
            else:
                print("unknown menu id: %d" % menu_id)
    


if __name__ == "__main__":
    class TestSTC(wx.stc.StyledTextCtrl):
        def __init__(self, *args, **kwargs):
            wx.stc.StyledTextCtrl.__init__(self, *args, **kwargs)
            self.Bind(wx.stc.EVT_STC_UPDATEUI, self.OnUpdateUI)
            
        def OnUpdateUI(self, evt):
            """Specific OnUpdateUI callback for those modes that use an actual
            STC for their edit window.
            
            Adds things like fold level and style display.
            """
            linenum = self.GetCurrentLine()
            pos = self.GetCurrentPos()
            col = self.GetColumn(pos)
            status = "Line: %d Column: %d Position: %d" % (linenum, col, pos)
            print status
            self.GetParent().status.showStatusText(status)
            evt.Skip()

    class Frame(wx.Frame):
        def __init__(self, *args, **kwargs):
            super(self.__class__, self).__init__(*args, **kwargs)
            
            self.menubar = wx.MenuBar()
            self.SetMenuBar(self.menubar)  # Adding the MenuBar to the Frame content.
            menu = wx.Menu()
            self.menubar.Append(menu, "File")
            self.menuAdd(menu, "Open", "Open File", self.OnOpenFile)
            self.menuAdd(menu, "Quit", "Exit the program", self.OnQuit)
            menu = wx.Menu()
            self.menubar.Append(menu, "Edit")

            self.stc = TestSTC(self, -1)
            self.stc.Bind(wx.stc.EVT_STC_START_DRAG, self.OnPrintEvent)
            self.stc.Bind(wx.stc.EVT_STC_DRAG_OVER, self.OnPrintEvent)
            self.stc.Bind(wx.EVT_LEFT_DCLICK, self.OnDoubleClick)
            self.Bind(wx.EVT_MENU_HIGHLIGHT, self.OnMenuHighlight)

            self.stc.SetText("""\
    This is some sample text...  Double click for a popup.
            
    Lorem ipsum dolor sit amet, consectetuer adipiscing elit.  Vivamus mattis
    commodo sem.  Phasellus scelerisque tellus id lorem.  Nulla facilisi.
    Suspendisse potenti.  Fusce velit odio, scelerisque vel, consequat nec,
    dapibus sit amet, tortor.  Vivamus eu turpis.  Nam eget dolor.  Integer
    at elit.  Praesent mauris.  Nullam non nulla at nulla tincidunt malesuada.
    Phasellus id ante.  Sed mauris.  Integer volutpat nisi non diam.  Etiam
    elementum.  Pellentesque interdum justo eu risus.  Cum sociis natoque
    penatibus et magnis dis parturient montes, nascetur ridiculus mus.  Nunc
    semper.  In semper enim ut odio.  Nulla varius leo commodo elit.  Quisque
    condimentum, nisl eget elementum laoreet, mauris turpis elementum felis, ut
    accumsan nisl velit et mi.

    And some Russian: \u041f\u0438\u0442\u043e\u043d - \u043b\u0443\u0447\u0448\u0438\u0439 \u044f\u0437\u044b\u043a \u043f\u0440\u043e\u0433\u0440\u0430\u043c\u043c\u0438\u0440\u043e\u0432\u0430\u043d\u0438\u044f!""")
            
            self.status = PopupStatusBar(self)

        def OnPrintEvent(self, evt):
            print evt
            for name in dir(evt):
                try:
                    if name.startswith("Get"):
                        print "attr=%s val=%s" % (name, getattr(evt, name)())
                except:
                    pass
                
        def OnDoubleClick(self, evt):
            print("x=%d y=%d" % (evt.GetX(), evt.GetY()))
            pos = self.stc.PositionFromPointClose(evt.GetX(), evt.GetY())
            print("pos=%d" % pos)
            if pos != wx.stc.STC_INVALID_POSITION:
                line = self.stc.LineFromPosition(pos)
                text = self.stc.GetLine(line)
                print("text=%s" % text)
                self.status.showMessage(text)
            
        def OnMenuHighlight(self, evt):
            print(evt)
            menu_id = evt.GetMenuId()
            if menu_id >= 0:
                help_text = self.menubar.GetHelpString(menu_id)
                self.status.showStatusText("Menu id %s: %s" % (menu_id, help_text))
            
        def menuAdd(self, menu, name, desc, fcn, id=-1, kind=wx.ITEM_NORMAL):
            if id == -1:
                id = wx.NewId()
            a = wx.MenuItem(menu, id, name, desc, kind)
            menu.AppendItem(a)
            wx.EVT_MENU(self, id, fcn)
            menu.SetHelpString(id, desc)
        
        def OnOpenFile(self, evt):
            dlg = wx.FileDialog(self, "Choose a text file",
                               defaultDir = "",
                               defaultFile = "",
                               wildcard = "*")
            if dlg.ShowModal() == wx.ID_OK:
                print("Opening %s" % dlg.GetPath())
                self.loadFile(dlg.GetPath())
            dlg.Destroy()
        
        def loadFile(self, filename):
            fh = open(filename)
            self.stc.SetText(fh.read())

        def OnQuit(self, evt):
            self.Close(True)

    app = wx.App(False)
    frame = Frame(None)
    frame.Show()
    app.MainLoop()
