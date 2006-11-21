import os,struct

import wx
import wx.stc as stc
import wx.grid as Grid
from wx.lib.evtmgr import eventManager
import wx.lib.newevent

from menudev import *
from buffers import *

from fundamental import FundamentalView

from debug import *


class OpenHexEditor(FrameAction):
    name = "&Open Hex Editor..."
    tooltip = "Open a Hex Editor"
    icon = wx.ART_FILE_OPEN

##    def isEnabled(self, state=None):
##        return not self.frame.isOpen()

    def action(self, state=None, pos=-1):
        self.dprint("exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.open("icons/py.ico")

class HexEditMajorMode(FrameAction):
    name = "Change to HexEdit Major Mode"
    tooltip = "Change to binary editor"
    icon = "icons/folder_page.png"
    keyboard = "C-X C-H"

    def action(self, state=None, pos=-1):
        self.dprint("exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.changeMajorMode(HexEditView)




class HugeTable(Grid.PyGridTableBase,debugmixin):

    def __init__(self,stc,format="16c"):
        Grid.PyGridTableBase.__init__(self)

        self.setFormat(format)
        self.setSTC(stc)
        
        self.odd=Grid.GridCellAttr()
        self.odd.SetBackgroundColour("sky blue")
        self.even=Grid.GridCellAttr()
        self.even.SetBackgroundColour("sea green")

        self._debug=False

    def setFormat(self,format):
        if format:
            self.format=format
            self.nbytes=struct.calcsize(self.format)
            self._hexcols=self.nbytes
            self.parseFormat(self.format)
            self._cols=self._hexcols+self._textcols

    def parseFormat(self,format):
        self.types=[]
        mult=None
        endian='='
        for c in format:
            self.dprint("checking %s" % c)
            if c>='0' and c<='9':
                if mult==None:
                    mult=0
                mult=mult*10+ord(c)-ord('0')
            elif c in ['x','c','b','B','h','H','i','I','l','L','f','d']:
                if mult==None:
                    self.types.append(endian+c)
                elif mult>0:
                    self.types.extend([endian+c]*mult)
            elif c in ['@','=','<','>','!']:
                endian=c
            else:
                self.dprint("ignoring %s" % c)
        self.sizes=[]
        self.offsets=[]
        offset=0
        for c in self.types:
            size=struct.calcsize(c)
            self.sizes.append(size)
            self.offsets.append(offset)
            offset+=size
            
        self._textcols=len(self.types)
        self.dprint("format = %s" % self.types)
        self.dprint("sizes = %s" % self.sizes)
        self.dprint("offsets = %s" % self.offsets)
        
    def setSTC(self, stc):
        self.stc=stc
        self.dprint("stc = %s" % self.stc        )
        self._rows=((self.stc.GetTextLength()-1)/self.nbytes)+1
        self.dprint(" rows=%d cols=%d" % (self._rows,self._cols))

##    def GetAttr(self, row, col, kind):
##        attr = [self.even, self.odd][row % 2]
##        attr.IncRef()
##        return attr

    def getTextCol(self,col):
        return col-self._hexcols
    
    def getLoc(self, row, col):
        if col<self._hexcols:
            loc = row*self.nbytes + col
        else:
            loc = row*self.nbytes + self.offsets[self.getTextCol(col)]
        return loc

    def getNumberHexCols(self):
        return self._hexcols
    
    def getNumberTextCols(self):
        return self._textcols
    
    def getCursorPosition(self, loc, refcol=0):
        """Get cursor position from byte offset from start of file.
        Optionally take a column parameter that tells us which side of
        the grid we're on, the hex side or the calculated side.
        """
        row=loc/self.nbytes
        col=loc%self.nbytes
        if col>=self._hexcols:
            # convert col to the correct column in the text representation
            pass
        return (row,col)
   
    def getNextCursorPosition(self, row, col):
        if col<self._hexcols:
            col+=1
            if col>=self._hexcols:
                if row<self._rows-1:
                    row+=1
                    col=0
                else:
                    col=self._hexcols-1
        else:
            col+=1
            if col>=self._cols:
                if row<self._rows-1:
                    row+=1
                    col=self._hexcols
                else:
                    col=self._cols-1
        return (row,col)
   
    def getPrevCursorPosition(self, row, col):
        if col<self._hexcols:
            col-=1
            if col<0:
                if row>0:
                    row-=1
                    col=self._hexcols-1
                else:
                    col=0
        else:
            col-=1
            if col<=self._hexcols:
                if row>0:
                    row-=1
                    col=self._cols-1
                else:
                    col=self._hexcols
        return (row,col)
   
    def GetNumberRows(self):
        self.dprint("rows = %d" % self._rows)
        return self._rows

    def GetRowLabelValue(self, row):
        return "%04x" % (row*self.nbytes)

    def GetNumberCols(self):
        self.dprint("cols = %d" % self._cols)
        return self._cols

    def GetColLabelValue(self, col):
        self.dprint("col=%x" % col)
        if col<self._hexcols:
            return "%x" % col
        else:
            return "Values"

    def IsEmptyCell(self, row, col):
        if col<self._hexcols:
            if self.getLoc(row,col)>self.stc.GetTextLength():
                return True
            else:
                return False
        else:
            return False

    def GetValue(self, row, col):
        if col<self._hexcols:
            loc = self.getLoc(row,col)
            s = "%02x" % self.stc.GetCharAt(loc)
            self.dprint(s)
            return s
        else:
            startpos = self.getLoc(row,col)
            textcol = self.getTextCol(col)
            endpos = startpos+self.sizes[textcol]
            data = self.stc.GetStyledText(startpos,endpos)[::2]
            self.dprint("row=%d col=%d textcol=%d start=%d end=%d data=%d structlen=%d" % (row,col,textcol,startpos,endpos,len(data),self.nbytes))
            s = struct.unpack(self.types[textcol],data)
            return str(s[0])

    def SetValue(self, row, col, value):
        if col<self._hexcols:
            val=int(value,16)
            if val>=0 and val<256:
                c=chr(val)
                loc = self.getLoc(row,col)
                self.stc.SetSelection(loc,loc+1)
                self.stc.ReplaceSelection('')
                self.stc.AddStyledText(c+'\0')
            else:
                self.dprint('SetValue(%d, %d, "%s")=%d out of range.' % (row, col, value,val))
        else:
            self.dprint('SetValue(%d, %d, "%s") ignored.' % (row, col, value))

    def ResetView(self, grid, stc, format=None):
        """
        (Grid) -> Reset the grid view.   Call this to
        update the grid if rows and columns have been added or deleted
        """
        oldrows=self._rows
        oldcols=self._cols
        if format:
            self.setFormat(format)
        self.setSTC(stc)
        
        grid.BeginBatch()

        for current, new, delmsg, addmsg in [
            (oldrows, self._rows, Grid.GRIDTABLE_NOTIFY_ROWS_DELETED, Grid.GRIDTABLE_NOTIFY_ROWS_APPENDED),
            (oldcols, self._cols, Grid.GRIDTABLE_NOTIFY_COLS_DELETED, Grid.GRIDTABLE_NOTIFY_COLS_APPENDED),
        ]:

            if new < current:
                msg = Grid.GridTableMessage(self,delmsg,new,current-new)
                grid.ProcessTableMessage(msg)
            elif new > current:
                msg = Grid.GridTableMessage(self,addmsg,new-current)
                grid.ProcessTableMessage(msg)
                self.UpdateValues(grid)

        # update the scrollbars and the displayed part of the grid
        grid.SetMargins(0,0)
        font=grid.GetDefaultCellFont()
        dc=wx.MemoryDC()
        dc.SetFont(font)
        (width,height)=dc.GetTextExtent("MM")
        self.dprint("font extents=(%d,%d)" % (width,height))
        for col in range(self._hexcols):
            grid.SetColMinimalWidth(col,10)
            grid.SetColSize(col,width)
        (width,height)=dc.GetTextExtent("MMMMMMMMMM")
        for col in range(self._hexcols,self._cols,1):
            grid.SetColMinimalWidth(col,10)
            grid.SetColSize(col,width)

        grid.EndBatch()

        self._rows = self.GetNumberRows()
        self._cols = self.GetNumberCols()
##        # update the column rendering plugins
##        self._updateColAttrs(grid)

        grid.AdjustScrollbars()
        grid.ForceRefresh()


    def UpdateValues(self, grid):
        """Update all displayed values"""
        # This sends an event to the grid table to update all of the values
        msg = Grid.GridTableMessage(self, Grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        grid.ProcessTableMessage(msg)


class HexDigitMixin(object):
    keypad=[ wx.WXK_NUMPAD0, wx.WXK_NUMPAD1, wx.WXK_NUMPAD2, wx.WXK_NUMPAD3, 
             wx.WXK_NUMPAD4, wx.WXK_NUMPAD5, wx.WXK_NUMPAD6, wx.WXK_NUMPAD7, 
             wx.WXK_NUMPAD8, wx.WXK_NUMPAD9
             ]
    
    def isValidHexDigit(self,key):
        return key in HexDigitMixin.keypad or (key>=ord('0') and key<=ord('9')) or (key>=ord('A') and key<=ord('F')) or (key>=ord('a') and key<=ord('f'))

    def getValidHexDigit(self,key):
        if key in HexDigitMixin.keypad:
            return chr(ord('0') + key - wx.WXK_NUMPAD0)
        elif (key>=ord('0') and key<=ord('9')) or (key>=ord('A') and key<=ord('F')) or (key>=ord('a') and key<=ord('f')):
            return chr(key)
        else:
            return None
        
# TextCtrl validator based on Validator.py from the wxPython demo
class HexValidator(wx.PyValidator,HexDigitMixin):
    def __init__(self):
        wx.PyValidator.__init__(self)
        self.Bind(wx.EVT_CHAR, self.OnChar)

    def Clone(self):
        return HexValidator()

    def OnChar(self, event):
        key = event.GetKeyCode()

        if key < wx.WXK_SPACE or key == wx.WXK_DELETE or key > 255:
            event.Skip()
            return

        if self.isValidHexDigit(key):
            event.Skip()
            return

        # Returning without calling even.Skip eats the event before it
        # gets to the text control
        return

class HexTextCtrl(wx.TextCtrl,HexDigitMixin,debugmixin):
    debuglevel=0
    
    def __init__(self,parent,id,parentgrid):
        wx.TextCtrl.__init__(self,parent, id, validator = HexValidator(),
                             style=wx.TE_PROCESS_TAB|wx.TE_PROCESS_ENTER)
        self.dprint("parent=%s" % parent)
        self.SetInsertionPoint(0)
        self.SetMaxLength(2)
        self.Bind(wx.EVT_TEXT, self.OnText)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.parentgrid=parentgrid
        self.userpressed=False

    def editingNewCell(self,value):
        self.SetValue(value)
        self.SetFocus()
        self.SetInsertionPoint(0)
        self.SetSelection(0,2) # select the text
        self.userpressed=False

    def OnKeyDown(self, evt):
        self.dprint("key down before evt=%s" % evt.GetKeyCode())
        if self.isValidHexDigit(evt.GetKeyCode()):
            self.userpressed=True
        evt.Skip()
        
    def OnText(self, evt):
        self.dprint("evt=%s cursor=%d" % (evt.GetString(),self.GetInsertionPoint()))
        
        # NOTE: we check that GetInsertionPoint returns 1 because the
        # insertion point hasn't been updated yet and won't be until
        # after this event handler returns.
        if self.userpressed and len(evt.GetString())>=2 and self.GetInsertionPoint()>=1:
            # FIXME: problem here with a bunch of really quick
            # keystrokes -- the interaction with the
            # underlyingSTCChanged callback causes a cell's changes to
            # be skipped over.  Need some flag in grid to see if we're
            # editing, or to delay updates until a certain period of
            # calmness, or something.
            wx.CallAfter(self.parentgrid.advanceCursor)
        

# cell editor for the hex portion, based on GridCustEditor.py from the
# wxPython demo
class HexCellEditor(Grid.PyGridCellEditor,HexDigitMixin,debugmixin):
    debuglevel=0

    def __init__(self,grid):
        Grid.PyGridCellEditor.__init__(self)
        self.parentgrid=grid


    def Create(self, parent, id, evtHandler):
        """
        Called to create the control, which must derive from wx.Control.
        *Must Override*
        """
        self.dprint("")
        self._tc = HexTextCtrl(parent, id, self.parentgrid)
        self.SetControl(self._tc)


    def SetSize(self, rect):
        """
        Called to position/size the edit control within the cell rectangle.
        If you don't fill the cell (the rect) then be sure to override
        PaintBackground and do something meaningful there.
        """
        self.dprint("rect=%s\n" % rect)
        self._tc.SetDimensions(rect.x, rect.y, rect.width+2, rect.height+2,
                               wx.SIZE_ALLOW_MINUS_ONE)


    def Show(self, show, attr):
        """
        Show or hide the edit control.  You can use the attr (if not None)
        to set colours or fonts for the control.
        """
        self.dprint("show=%s, attr=%s" % (show, attr))
        self.base_Show(show, attr)


    def PaintBackground(self, rect, attr):
        """
        Draws the part of the cell not occupied by the edit control.  The
        base  class version just fills it with background colour from the
        attribute.  In this class the edit control fills the whole cell so
        don't do anything at all in order to reduce flicker.
        """
        self.dprint("MyCellEditor: PaintBackground\n")


    def BeginEdit(self, row, col, grid):
        """
        Fetch the value from the table and prepare the edit control
        to begin editing.  Set the focus to the edit control.
        *Must Override*
        """
        self.dprint("row,col=(%d,%d)" % (row, col))
        self.startValue = grid.GetTable().GetValue(row, col)
        self._tc.editingNewCell(self.startValue)


    def EndEdit(self, row, col, grid):
        """
        Complete the editing of the current cell. Returns True if the value
        has changed.  If necessary, the control may be destroyed.
        *Must Override*
        """
        self.dprint("row,col=(%d,%d)" % (row, col))
        changed = False

        val = self._tc.GetValue()
        
        if val != self.startValue:
            changed = True
            grid.GetTable().SetValue(row, col, val) # update the table

        self.startValue = ''
        self._tc.SetValue('')
        return changed


    def Reset(self):
        """
        Reset the value in the control back to its starting value.
        *Must Override*
        """
        self.dprint("")
        self._tc.SetValue(self.startValue)
        self._tc.SetInsertionPointEnd()


    def IsAcceptedKey(self, evt):
        """
        Return True to allow the given key to start editing: the base class
        version only checks that the event has no modifiers.  F2 is special
        and will always start the editor.
        """
        self.dprint("keycode=%d" % (evt.GetKeyCode()))

        ## We can ask the base class to do it
        #return self.base_IsAcceptedKey(evt)

        # or do it ourselves
        return (not (evt.ControlDown() or evt.AltDown()) and
                evt.GetKeyCode() != wx.WXK_SHIFT)


    def StartingKey(self, evt):
        """
        If the editor is enabled by pressing keys on the grid, this will be
        called to let the editor do something about that first key if desired.
        """
        self.dprint("keycode=%d" % evt.GetKeyCode())
        key = evt.GetKeyCode()
        ch = self.getValidHexDigit(key)

        if ch is not None:
            # For this example, replace the text.  Normally we would append it.
            #self._tc.AppendText(ch)
            self._tc.SetValue(ch)
            self._tc.SetInsertionPointEnd()
        else:
            evt.Skip()


    def StartingClick(self):
        """
        If the editor is enabled by clicking on the cell, this method will be
        called to allow the editor to simulate the click on the control if
        needed.
        """
        self.dprint("")


    def Destroy(self):
        """final cleanup"""
        self.dprint("")
        self.base_Destroy()


    def Clone(self):
        """
        Create a new object which is the copy of this one
        *Must Override*
        """
        self.dprint("")
        return HexCellEditor(self.parentgrid)






# This creates a new Event class and a EVT binder function
(WaitUpdateEvent, EVT_WAIT_UPDATE) = wx.lib.newevent.NewEvent()

from threading import Thread
class WaitThread(Thread):
    def __init__(self, notify_window, delay=0.2):
        Thread.__init__(self)
        self._notify_window = notify_window
        self._wait=1
        self._delay=delay

    def waitMore(self):
        self._wait=2

    def run(self):
        while self._wait>0:
            time.sleep(self._delay)
            self._wait-=1
        wx.PostEvent(self._notify_window,WaitUpdateEvent())



class HugeTableGrid(Grid.Grid,debugmixin):
    debuglevel=0
    
    def __init__(self, parent, stc, format="@4f"):
        Grid.Grid.__init__(self, parent, -1)

        self.table = HugeTable(stc, format)

        # The second parameter means that the grid is to take
        # ownership of the table and will destroy it when done.
        # Otherwise you would need to keep a reference to it and call
        # its Destroy method later.
        self.SetTable(self.table, True)
        self.SetMargins(0,0)
        self.SetColMinimalAcceptableWidth(10)
        self.EnableDragGridSize(False)

        self.RegisterDataType(Grid.GRID_VALUE_STRING, None, None)
        self.SetDefaultEditor(HexCellEditor(self))

        self.Bind(Grid.EVT_GRID_CELL_RIGHT_CLICK, self.OnRightDown)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Bind(EVT_WAIT_UPDATE,self.OnUnderlyingUpdate)
        self.Show(True)

    def Update(self,stc,format=None):
        self.dprint("Need to update grid")
        self.table.ResetView(self,stc,format)

    def OnUnderlyingUpdate(self, ev, loc=None):
        """Data has changed in some other view, so we need to update
        the grid and reset the grid's cursor to the updated position
        if the location is given.
        """
        self.dprint("OnUnderlyingUpdate: slow way of updating the grid -- updating the whole thing.")
        self.dprint(ev)

        self.table.ResetView(self,self.table.stc) # FIXME: this is slow.  Put it in a thread or something.

        if loc is not None:
            (row,col)=self.GetTable().getCursorPosition(loc,self.GetGridCursorCol())
            self.SetGridCursor(row,col)
            self.MakeCellVisible(row,col)

    def OnRightDown(self, ev):
        self.dprint(self.GetSelectedRows())

    def OnKeyDown(self, evt):
        self.dprint("evt=%s" % evt)
        if evt.GetKeyCode() == wx.WXK_RETURN or evt.GetKeyCode()==wx.WXK_TAB:
            if evt.ControlDown():   # the edit control needs this key
                evt.Skip()
                return

            self.DisableCellEditControl()
            if evt.ShiftDown():
                (row,col)=self.GetTable().getPrevCursorPosition(self.GetGridCursorRow(),self.GetGridCursorCol())
            else:
                (row,col)=self.GetTable().getNextCursorPosition(self.GetGridCursorRow(),self.GetGridCursorCol())
            self.SetGridCursor(row,col)
            self.MakeCellVisible(row,col)

        else:
            evt.Skip()
            return

    def advanceCursor(self):
        self.DisableCellEditControl()
        # FIXME: moving from the hex region to the value region using
        # self.MoveCursorRight(False) causes a segfault, so make sure
        # to stay in the same region
        (row,col)=self.GetTable().getNextCursorPosition(self.GetGridCursorRow(),self.GetGridCursorCol())
        self.SetGridCursor(row,col)
        self.EnableCellEditControl()



class HexEditView(FundamentalView):
    pluginkey = 'hexedit'
    keyword='HexEdit'
    icon='icons/tux.png'
    regex="\.(hex|bin|so|dat|ico|emf)"
    filter=BinaryFilter()

    debuglevel=0

    def createEditWindow(self,parent):
        FundamentalView.createEditWindow(self,parent)
        self.dprint("creating new HexEditView window")

        win=HugeTableGrid(parent,self.stc,"16c")        
        #wx.StaticText(self.win, -1, self.buffer.name, (145, 145))

        self.stc.Show(False)

        # Can't use self.stc.SetModEventMask, because we're really
        # interested in the events from buffer.stc not from self.stc.
        # We also can't set the buffer's event flags, because other
        # views may be interested in them.  So, we have to screen
        # events in the callback itself.
        ## self.stc.SetModEventMask(stc.STC_MOD_INSERTTEXT|stc.STC_MOD_DELETETEXT|stc.STC_PERFORMED_USER|stc.STC_PERFORMED_UNDO|stc.STC_PERFORMED_REDO)
        
        # Multiple binds to the same handler, ie multiple HexEditViews
        # trying to do self.buffer.stc.Bind(stc.EVT_STC_MODIFIED,
        # self.underlyingSTCChanged) don't work.  Need to use the
        # event manager for multiple bindings.
        eventManager.Bind(self.underlyingSTCChanged,stc.EVT_STC_MODIFIED,self.buffer.stc)

        # Thread stuff for the underlying change callback
        self.waiting=None

        return win

    def openPostHook(self):
        self.editwin.Update(self.stc)
        
    def transModType(self, modType):
        st = ""
        table = [(stc.STC_MOD_INSERTTEXT, "InsertText"),
                 (stc.STC_MOD_DELETETEXT, "DeleteText"),
                 (stc.STC_MOD_CHANGESTYLE, "ChangeStyle"),
                 (stc.STC_MOD_CHANGEFOLD, "ChangeFold"),
                 (stc.STC_PERFORMED_USER, "UserFlag"),
                 (stc.STC_PERFORMED_UNDO, "Undo"),
                 (stc.STC_PERFORMED_REDO, "Redo"),
                 (stc.STC_LASTSTEPINUNDOREDO, "Last-Undo/Redo"),
                 (stc.STC_MOD_CHANGEMARKER, "ChangeMarker"),
                 (stc.STC_MOD_BEFOREINSERT, "B4-Insert"),
                 (stc.STC_MOD_BEFOREDELETE, "B4-Delete")
                 ]

        for flag,text in table:
            if flag & modType:
                st = st + text + " "

        if not st:
            st = 'UNKNOWN'

        return st

    def underlyingSTCChanged(self,evt):
        # Short-circuit this callback when we are editing this grid.
        # The event is fired regardless of how the data is changed, so
        # without some sort of check, the grid ends up getting
        # modified twice.  If the current view is the active window,
        # we know that we are editing this grid by hand.
        if self.frame.isTopWindow():
            self.dprint("TopWindow!  Skipping underlyingSTCChanged!")
            return
        
        # As the comment in the createWindow method noted, we have to
        # screen for the events we're interested in because we're not
        # allowed to change the events that self.buffer.stc sees.
        etype=evt.GetModificationType()
        if etype&stc.STC_MOD_INSERTTEXT or etype&stc.STC_MOD_DELETETEXT:
            self.dprint("""UnderlyingSTCChanged
            Mod type:     %s
            At position:  %d
            Lines added:  %d
            Text Length:  %d
            Text:         %s\n""" % ( self.transModType(evt.GetModificationType()),
                                      evt.GetPosition(),
                                      evt.GetLinesAdded(),
                                      evt.GetLength(),
                                      repr(evt.GetText()) ))

            #self.win.underlyingUpdate(self.stc,evt.GetPosition())
            if self.waiting:
                if self.waiting.isAlive():
                    self.dprint("found active wait thread")
                    self.waiting.waitMore()
                else:
                    self.waiting.join()
                    self.waiting=None
                    self.dprint("wait thread destroyed")
                    # start a new thread below

            # don't use an else here so that a new thread will be
            # started if we just destroyed the old thread.
            if not self.waiting:
                self.dprint("starting wait thread")
                self.waiting=WaitThread(self.win)
                self.waiting.start()
        


global_menu_actions=[
    [[('&File',0.0)],OpenHexEditor,0.2],
    [[('&Edit',0.1)],HexEditMajorMode,0.9],
]

##global_toolbar_actions=[
##    # toolbar plugins here...
##    [OpenHexEditor,0.1],
##    ]

viewers=[
    HexEditView,
    ]
