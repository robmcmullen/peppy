import os,struct

import wx
import wx.stc as stc
import wx.grid as Grid
from wx.lib.evtmgr import eventManager

from menudev import *
from buffers import *

from fundamental import FundamentalView

class OpenHexEditor(Command):
    name = "&Open Hex Editor..."
    tooltip = "Open a Hex Editor"
    icon = wx.ART_FILE_OPEN

##    def isEnabled(self, state=None):
##        return not self.frame.isOpen()

    def runthis(self, state=None, pos=-1):
        print "exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos))
        self.frame.proxy.open(self.frame,"icons/py.ico")

class HexEditMajorMode(Command):
    name = "Change to HexEdit Major Mode"
    tooltip = "Change to binary editor"
    icon = "icons/folder_page.png"
    keyboard = "C-X C-H"

    def runthis(self, state=None, pos=-1):
        print "exec: id=%x name=%s pos=%s" % (id(self),self.name,str(pos))
        self.frame.changeMajorMode(HexEditView)


menu_plugins=[
    ['main',[('&File',0.0)],OpenHexEditor,0.2],
    ['main',[('&Edit',0.1)],HexEditMajorMode,0.9],
]

##toolbar_plugins=[
##    # toolbar plugins here...
##    ['main',OpenHexEditor,0.1],
##    ]


class HugeTable(Grid.PyGridTableBase):

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
            print "checking %s" % c
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
                print "ignoring %s" % c
        self.sizes=[]
        self.offsets=[]
        offset=0
        for c in self.types:
            size=struct.calcsize(c)
            self.sizes.append(size)
            self.offsets.append(offset)
            offset+=size
            
        self._textcols=len(self.types)
        print "format = %s" % self.types
        print "sizes = %s" % self.sizes
        print "offsets = %s" % self.offsets
        
    def setSTC(self, stc):
        self.stc=stc
        print "stc = %s" % self.stc        
        self._rows=((self.stc.GetTextLength()-1)/self.nbytes)+1
        print " rows=%d cols=%d" % (self._rows,self._cols)

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
        if self._debug: print "GetNumberRows = %d" % self._rows
        return self._rows

    def GetRowLabelValue(self, row):
        return "%04x" % (row*self.nbytes)

    def GetNumberCols(self):
        if self._debug: print "GetNumberCols = %d" % self._cols
        return self._cols

    def GetColLabelValue(self, col):
        if self._debug: print "GetColLabelValue: %x" % col
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
            if self._debug: print s
            return s
        else:
            startpos = self.getLoc(row,col)
            textcol = self.getTextCol(col)
            endpos = startpos+self.sizes[textcol]
            data = self.stc.GetStyledText(startpos,endpos)[::2]
            if self._debug: print "row=%d col=%d textcol=%d start=%d end=%d data=%d structlen=%d" % (row,col,textcol,startpos,endpos,len(data),self.nbytes)
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
                print 'SetValue(%d, %d, "%s")=%d out of range.' % (row, col, value,val)
        else:
            print 'SetValue(%d, %d, "%s") ignored.' % (row, col, value)

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
        print "font extents=(%d,%d)" % (width,height)
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



class HugeTableGrid(Grid.Grid):
    def __init__(self, parent, stc, format="@4f"):
        Grid.Grid.__init__(self, parent, -1)

        self.table = HugeTable(stc, format)

        # The second parameter means that the grid is to take ownership of the
        # table and will destroy it when done.  Otherwise you would need to keep
        # a reference to it and call it's Destroy method later.
        self.SetTable(self.table, True)
        self.SetMargins(0,0)
        self.SetColMinimalAcceptableWidth(10)
        self.EnableDragGridSize(False)

        self.Bind(Grid.EVT_GRID_CELL_RIGHT_CLICK, self.OnRightDown)
        self.Bind(wx.EVT_KEY_DOWN, self.OnKeyDown)
        self.Show(True)

    def Update(self,stc,format=None):
        print "Need to update grid"
        self.table.ResetView(self,stc,format)

    def underlyingUpdate(self,stc,loc=None):
        """Data has changed in some other view, so we need to update
        the grid and reset the grid's cursor to the updated position
        if the location is given.
        """
        print "underlyingUpdate: slow way of updating the grid -- updating the whole thing."

        self.table.ResetView(self,stc) # FIXME: this is slow.  Put it in a thread or something.

        if loc is not None:
            (row,col)=self.GetTable().getCursorPosition(loc,self.GetGridCursorCol())
            self.SetGridCursor(row,col)
            self.MakeCellVisible(row,col)

    def OnRightDown(self, ev):
        print "hello"
        print self.GetSelectedRows()

    def OnKeyDown(self, ev):
        if ev.KeyCode() == wx.WXK_RETURN or ev.KeyCode()==wx.WXK_TAB:
            if ev.ControlDown():   # the edit control needs this key
                ev.Skip()
                return

            self.DisableCellEditControl()
            if ev.ShiftDown():
                (row,col)=self.GetTable().getPrevCursorPosition(self.GetGridCursorRow(),self.GetGridCursorCol())
            else:
                (row,col)=self.GetTable().getNextCursorPosition(self.GetGridCursorRow(),self.GetGridCursorCol())
            self.SetGridCursor(row,col)
            self.MakeCellVisible(row,col)
##            newCol=self.GetGridCursorCol() + 1
##            if (newCol<col):
##                success = self.MoveCursorRight(ev.ShiftDown())
##            else:
##                newRow = self.GetGridCursorRow() + 1
##                if newRow < self.GetTable().GetNumberRows():
##                    self.SetGridCursor(newRow, 0)
##                    self.MakeCellVisible(newRow, 0)
##                else:
##                    # this would be a good place to add a new row if your app
##                    # needs to do that
##                    pass

        else:
            ev.Skip()
            return


class HexEditView(FundamentalView):
    pluginkey = 'hexedit'
    keyword='HexEdit'
    icon='icons/tux.png'
    regex="\.(hex|bin|so|dat|ico|emf)"
    loader=BinaryLoader

    def createWindow(self,parent):
        FundamentalView.createWindow(self,parent)
        print "creating new HexEditView window"

        self.win=HugeTableGrid(parent,self.stc)        
        #wx.StaticText(self.win, -1, self.buffer.name, (145, 145))

        self.stc.Show(False)

        # Multiple binds to the same handler, ie multiple HexEditViews
        # trying to do self.buffer.stc.Bind(stc.EVT_STC_MODIFIED,
        # self.underlyingSTCChanged) don't work.  Need to use the
        # event manager for multiple bindings.
        eventManager.Bind(self.underlyingSTCChanged,stc.EVT_STC_MODIFIED,self.buffer.stc)

    def reparent(self,parent):
        self.win.Reparent(parent)
        self.stc.Reparent(parent)

    def readySTC(self):
        self.win.Update(self.stc)
        
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
        sys.stdout.write("""UnderlyingSTCChanged
        Mod type:     %s
        At position:  %d
        Lines added:  %d
        Text Length:  %d
        Text:         %s\n""" % ( self.transModType(evt.GetModificationType()),
                                  evt.GetPosition(),
                                  evt.GetLinesAdded(),
                                  evt.GetLength(),
                                  repr(evt.GetText()) ))
        self.win.underlyingUpdate(self.stc,evt.GetPosition())
        


viewers=[
    HexEditView,
    ]
