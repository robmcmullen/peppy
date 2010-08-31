#----------------------------------------------------------------------
# Name:        commaseparatedlist.py
# Purpose:     Composite controls that provide an Edit button next to
#              a wxTextCtrl.  The Edit button launches a dialog that
#              can be used to edit a comma separated list.
#
# Author:      Rob McMullen
#              template from filebrowsebutton.py by Mike Fletcher
#
# RCS-ID:      $Id: $
# Copyright:   (c) 2008 Rob McMullen
# License:     wxPython
#----------------------------------------------------------------------

import os, types

import wx
import wx.grid as Grid


def getEntriesFromCSV(text):
    """Return entries from a line of comma-separated values"""
    return [t.strip() for t in text.split(',')]


class CSVTable(Grid.PyGridTableBase):
    def __init__(self, text, grid):
        Grid.PyGridTableBase.__init__(self)
        self.grid = grid
        
        self.parseCSV(text)
        
        self._debug=False
        self._col_labels = None
        self._rows = 0
        self._cols = 0
        
        self.ResetView()

    def parseCSV(self, text):
        self.values = getEntriesFromCSV(text)
    
    def GetNumberRows(self):
        return len(self.values)

    def GetRowLabelValue(self, row):
        return "%d" % (row + 1)

    def GetNumberCols(self):
        return 1

    def GetColLabelValue(self, col):
        return "Value"

    def IsEmptyCell(self, row, col):
        if row >= len(self.values):
            return False
        return True

    def GetValue(self, row, col):
        return str(self.values[row])

    def SetValue(self, row, col, value):
        self.values[row] = value

    def ResetView(self, values=None):
        """
        (Grid) -> Reset the grid view.   Call this to
        update the grid if rows and columns have been added or deleted
        """
        oldrows = self._rows
        oldcols = self._cols
        
        if values:
            self.values = values
        
        self.grid.BeginBatch()

        for current, new, delmsg, addmsg in [
            (oldrows, self.GetNumberRows(), Grid.GRIDTABLE_NOTIFY_ROWS_DELETED, Grid.GRIDTABLE_NOTIFY_ROWS_APPENDED),
            (oldcols, self.GetNumberCols(), Grid.GRIDTABLE_NOTIFY_COLS_DELETED, Grid.GRIDTABLE_NOTIFY_COLS_APPENDED),
        ]:

            if new < current:
                msg = Grid.GridTableMessage(self,delmsg,new,current-new)
                self.grid.ProcessTableMessage(msg)
            elif new > current:
                msg = Grid.GridTableMessage(self,addmsg,new-current)
                self.grid.ProcessTableMessage(msg)
                self.UpdateValues()
        self.grid.EndBatch()

        self._rows = self.GetNumberRows()
        self._cols = self.GetNumberCols()

        self.grid.AdjustScrollbars()
        self.grid.ForceRefresh()

    def UpdateValues(self):
        """Update all displayed values"""
        # This sends an event to the grid table to update all of the values
        msg = Grid.GridTableMessage(self, Grid.GRIDTABLE_REQUEST_VIEW_GET_VALUES)
        self.grid.ProcessTableMessage(msg)
    
    def GetCSV(self):
        return ", ".join([str(i) for i in self.values])


class CSVEditDialog(wx.Dialog):
    def __init__(self, parent, text, size=wx.DefaultSize, pos=wx.DefaultPosition,
                 style=wx.DEFAULT_DIALOG_STYLE|wx.RESIZE_BORDER,
                 title='Edit Values', cwd=None):
        wx.Dialog.__init__(self, parent, -1, title, size=size, pos=pos, style=style)
        
        self.debug = False
        self.selected = []
        if cwd:
            self.cwd = cwd
        else:
            self.cwd = os.getcwd()
        self.enable_when_selected = []

        sizer = wx.BoxSizer(wx.VERTICAL)

        hsizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.grid = Grid.Grid(self, -1, size=(200, 400))
        self.grid.EnableDragRowSize(False)
        self.grid.Bind(Grid.EVT_GRID_LABEL_LEFT_CLICK, self.OnLabelLeftClick)
        self.grid.Bind(Grid.EVT_GRID_RANGE_SELECT, self.OnRangeSelect)
        self.grid.Bind(wx.EVT_LEFT_UP, self.OnLeftUp)

        self.table = CSVTable(text, self.grid)
        self.grid.SetTable(self.table, True)
        
        hsizer.Add(self.grid, 0, wx.EXPAND)
        
        bag = wx.GridBagSizer(2, 5)
        row = 0
        label = wx.StaticText(self, -1, "First Row:")
        bag.Add(label, (row, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        self.start = wx.TextCtrl(self, -1)
        self.start.Bind(wx.EVT_TEXT, self.OnUserRow)
        bag.Add(self.start, (row, 1), flag=wx.EXPAND)
        row += 1
        
        label = wx.StaticText(self, -1, "Last Row:")
        bag.Add(label, (row, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        self.end = wx.TextCtrl(self, -1)
        self.end.Bind(wx.EVT_TEXT, self.OnUserRow)
        bag.Add(self.end, (row, 1), flag=wx.EXPAND)
        row += 1
        
        label = wx.StaticText(self, -1, "# Selected:")
        bag.Add(label, (row, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        self.count = wx.TextCtrl(self, -1)
        self.count.SetEditable(False)
        bag.Add(self.count, (row, 1), flag=wx.EXPAND)
        row += 1
        
        btn = wx.Button(self, -1, "Select All")
        btn.Bind(wx.EVT_BUTTON, self.OnSelectAll)
        bag.Add(btn, (row, 0), flag=wx.EXPAND)
        row += 1
        
        row += 1
        
        label = wx.StaticText(self, -1, "Operate on Selected Items Using the Buttons Below")
        bag.Add(label, (row, 0), (1,6), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_CENTER)
        row += 1

        label = wx.StaticText(self, -1, "Constant:")
        bag.Add(label, (row, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT)
        self.constant = wx.TextCtrl(self, -1)
        bag.Add(self.constant, (row, 1), flag=wx.EXPAND)
        btn = wx.Button(self, -1, "Set")
        self.enable_when_selected.append(btn)
        btn.Bind(wx.EVT_BUTTON, self.OnConstant)
        bag.Add(btn, (row, 2), flag=wx.EXPAND)
        row += 1
        
        label = wx.StaticText(self, -1, "Linear Range:")
        bag.Add(label, (row, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT)
        label = wx.StaticText(self, -1, "first value:")
        bag.Add(label, (row, 1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        self.linear_range_start = wx.TextCtrl(self, -1)
        bag.Add(self.linear_range_start, (row, 2), flag=wx.EXPAND)
        label = wx.StaticText(self, -1, "last value:")
        bag.Add(label, (row, 3), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        self.linear_range_end = wx.TextCtrl(self, -1)
        bag.Add(self.linear_range_end, (row, 4), flag=wx.EXPAND)
        btn = wx.Button(self, -1, "Set")
        self.enable_when_selected.append(btn)
        btn.Bind(wx.EVT_BUTTON, self.OnLinearRange)
        bag.Add(btn, (row, 5), flag=wx.EXPAND)
        row += 1
        
        label = wx.StaticText(self, -1, "Linear Step:")
        bag.Add(label, (row, 0), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT)
        label = wx.StaticText(self, -1, "start value:")
        bag.Add(label, (row, 1), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        self.linear_step_start = wx.TextCtrl(self, -1)
        bag.Add(self.linear_step_start, (row, 2), flag=wx.EXPAND)
        label = wx.StaticText(self, -1, "increment:")
        bag.Add(label, (row, 3), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_RIGHT)
        self.linear_step = wx.TextCtrl(self, -1)
        bag.Add(self.linear_step, (row, 4), flag=wx.EXPAND)
        btn = wx.Button(self, -1, "Set")
        self.enable_when_selected.append(btn)
        btn.Bind(wx.EVT_BUTTON, self.OnLinearStep)
        bag.Add(btn, (row, 5), flag=wx.EXPAND)
        row += 1
        
        row += 1
        
        label = wx.StaticText(self, -1, "Insert Items Before/After Selection:")
        bag.Add(label, (row, 0), (1, 3), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT)
        btn = wx.Button(self, -1, "Before")
        self.enable_when_selected.append(btn)
        btn.Bind(wx.EVT_BUTTON, self.OnInsertItemsBefore)
        bag.Add(btn, (row, 3), flag=wx.EXPAND)
        btn = wx.Button(self, -1, "After")
        self.enable_when_selected.append(btn)
        btn.Bind(wx.EVT_BUTTON, self.OnInsertItemsAfter)
        bag.Add(btn, (row, 4), flag=wx.EXPAND)
        row += 1
        
        label = wx.StaticText(self, -1, "Delete Selected Items:")
        bag.Add(label, (row, 0), (1, 2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT)
        btn = wx.Button(self, -1, "Remove")
        self.enable_when_selected.append(btn)
        btn.Bind(wx.EVT_BUTTON, self.OnDeleteSelected)
        bag.Add(btn, (row, 2), flag=wx.EXPAND)

        row += 1
        
        row += 1
        
        label = wx.StaticText(self, -1, "Operate on Entire List Using the Buttons Below")
        bag.Add(label, (row, 0), (1,6), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_CENTER)
        row += 1

        label = wx.StaticText(self, -1, "Change Size:")
        bag.Add(label, (row, 0), (1,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT)
        btn = wx.Button(self, -1, "Resize...")
        btn.Bind(wx.EVT_BUTTON, self.OnChangeSize)
        bag.Add(btn, (row, 2), flag=wx.EXPAND)
        row += 1

        label = wx.StaticText(self, -1, "Import From Text File:")
        bag.Add(label, (row, 0), (1,2), flag=wx.ALIGN_CENTER_VERTICAL|wx.ALIGN_LEFT)
        btn = wx.Button(self, -1, "Import...")
        btn.Bind(wx.EVT_BUTTON, self.OnImport)
        bag.Add(btn, (row, 2), flag=wx.EXPAND)
        row += 1

        hsizer.Add(bag, 0, wx.EXPAND)
        
        sizer.Add(hsizer, 1, wx.EXPAND)

        btnsizer = wx.StdDialogButtonSizer()
        
        btn = wx.Button(self, wx.ID_OK)
        btnsizer.AddButton(btn)

        btn = wx.Button(self, wx.ID_CANCEL)
        btnsizer.AddButton(btn)
        btnsizer.Realize()

        sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)

        self.SetSizer(sizer)
        sizer.Fit(self)

        self.Layout()
        
        self.getSelectedEntries()

    def getSelectedEntries(self, update_text=True):
        rows = self.grid.GetSelectedRows()
        cells = self.grid.GetSelectedCells()
        blocktl = self.grid.GetSelectionBlockTopLeft()
        blockbr = self.grid.GetSelectionBlockBottomRight()
        blocks = zip(blocktl, blockbr)
        if self.debug: print("rows=%s cells=%s blocks=%s" % (str(rows), str(cells), str(blocks)))
        
        rows.extend([c[0] for c in cells])
        for blocktl, blockbr in blocks:
            rows.extend(range(blocktl[0], blockbr[0]+1))
        rows = list(set(rows))
        rows.sort()
        if self.debug: print("rows=%s" % str(rows))
        if update_text:
            if rows:
                self.start.ChangeValue(str(rows[0] + 1))
                self.end.ChangeValue(str(rows[-1] + 1))
            else:
                self.start.ChangeValue('')
                self.end.ChangeValue('')
        self.count.ChangeValue(str(len(rows)))
        self.selected = rows
        
        enable = bool(self.selected)
        for ctrl in self.enable_when_selected:
            ctrl.Enable(enable)
    
    def resetSelectedEntries(self, selected=None):
        """Reset the selection to the items given in the list"""
        if selected is None:
            selected = self.selected
        self.grid.ClearSelection()
        for row in selected:
            self.grid.SelectRow(row, True)
        self.getSelectedEntries()
        
    def OnLeftUp(self, evt):
        if self.debug: print("OnLeftUp:\n")
        self.highlighting = False
        evt.Skip()
    
    def OnLabelLeftClick(self, evt):
        if self.debug: print("OnCellLeftClick: (%d,%d) %s" %
                    (evt.GetRow(), evt.GetCol(), evt.GetPosition()))
        self.getSelectedEntries()
        evt.Skip()
    
    def OnRangeSelect(self, evt):
        if evt.Selecting():
            if self.debug: print("OnRangeSelect: top-left %s, bottom-right %s" %
                  (evt.GetTopLeftCoords(), evt.GetBottomRightCoords()))
        self.getSelectedEntries()
        evt.Skip()
    
    def OnSelectAll(self, evt):
        self.grid.SelectAll()
        evt.Skip()
    
    def OnUserRow(self, evt):
        first = self.start.GetValue()
        last = self.end.GetValue()
        try:
            first = int(first) - 1
            last = int(last) - 1
            if first <= last and first > 0 and last < self.grid.GetNumberRows():
                self.grid.ClearSelection()
                self.grid.SelectBlock(first, 0, last, 0, True)
                self.getSelectedEntries(update_text=False)
        except ValueError:
            pass
    
    def OnConstant(self, evt):
        """Event handler when Constant button is pressed -- fill the selected
        entries with whatever value is in the text field
        """
        val = self.constant.GetValue()
        for row in self.selected:
            self.table.SetValue(row, 0, val)
        self.table.UpdateValues()

    def OnLinearRange(self, evt):
        """Fill the selected entries with linearly interpolated values
        """
        try:
            start = float(self.linear_range_start.GetValue())
            end = float(self.linear_range_end.GetValue())
            index = 0
            num = len(self.selected)
            if num > 1:
                num -= 1
                for row in self.selected:
                    val = start + index*(end - start)/num
                    self.table.SetValue(row, 0, str(val))
                    index += 1
            elif num == 1:
                row = self.selected[0]
                # could select either the start or ending value here, since a
                # selection with only one element is both the start and the
                # end.  The least surprising thing would probably be the start
                self.table.SetValue(row, 0, str(start))
            self.table.UpdateValues()
        except ValueError:
            dlg = wx.MessageDialog(self, "Values should be numbers.", "Range Error", wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
        
    def OnLinearStep(self, evt):
        """Fill the selected entries by incrementing a stepsize
        """
        try:
            val = float(self.linear_step_start.GetValue())
            step = float(self.linear_step.GetValue())
            for row in self.selected:
                self.table.SetValue(row, 0, str(val))
                val += step
            self.table.UpdateValues()
        except ValueError:
            dlg = wx.MessageDialog(wx.GetApp().GetTopWindow(), msg, "Values should be numbers.", wx.OK | wx.ICON_ERROR)

    def OnImport(self, evt):
        """Import from a text file.
        
        Values can be separated by commas or on separate lines.
        """
        dlg = wx.FileDialog(self, message="Open Comma Separated Value File", defaultDir=self.cwd, defaultFile="", wildcard="*", style=wx.OPEN)

        # Show the dialog and retrieve the user response. If it is the
        # OK response, process the data.
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            paths = dlg.GetPaths()
            if paths:
                self.importFile(paths[0])
    
    def importFile(self, filename):
        try:
            values = []
            fh = open(filename, 'rb')
            for line in fh:
                vals = getEntriesFromCSV(line)
                for val in vals:
                    if self.debug: print("importing %s" % str(val))
                    if val:
                        values.append(val)
            self.table.ResetView(values=values)
        except IOError:
            dlg = wx.MessageDialog(self, "Error importing file\n%s" % filename, "Import Error.", wx.OK | wx.ICON_ERROR)
            dlg.ShowModal()
        
    def OnChangeSize(self, evt):
        """Resize the grid
        """
        dlg = wx.TextEntryDialog(self, "Enter Number of Items", defaultValue=str(self.table.GetNumberRows()), style=wx.OK|wx.CANCEL)

        if dlg.ShowModal() == wx.ID_OK:
            try:
                num = int(dlg.GetValue())
                values = self.table.values
                if num < len(values):
                    values = values[0:num]
                elif num > len(values):
                    values.extend([0]*(num - len(values)))
                self.table.ResetView(values=values)
            except ValueError:
                dlg = wx.MessageDialog(self, "Need integer as number of items.", "Integer Error", wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
    
    def OnInsertItemsBefore(self, evt):
        """Insert items in the list
        """
        self.insertItems()
    
    def OnInsertItemsAfter(self, evt):
        """Insert items in the list
        """
        self.insertItems(before=False)
    
    def insertItems(self, before=True):
        if not self.selected:
            return
        dlg = wx.TextEntryDialog(self, "Enter Number of Items", defaultValue="1", style=wx.OK|wx.CANCEL)

        if dlg.ShowModal() == wx.ID_OK:
            try:
                num = int(dlg.GetValue())
                values = self.table.values
                if before:
                    pos = self.selected[0]
                else:
                    pos = self.selected[-1] + 1
                values[pos:pos] = [0]*num
                self.table.ResetView(values=values)
                
                selected = []
                for row in self.selected:
                    if row >= pos:
                        row += num
                    selected.append(row)
                self.resetSelectedEntries(selected)
            except ValueError:
                dlg = wx.MessageDialog(self, "Need integer as number of items.", "Integer Error", wx.OK | wx.ICON_ERROR)
                dlg.ShowModal()
        
    def OnDeleteSelected(self, evt):
        """Delete the selected items"""
        if not self.selected:
            return
        values = self.table.values
        newvalues = []
        for index in range(0, len(values)):
            if index not in self.selected:
                newvalues.append(values[index])
        self.table.ResetView(values=newvalues)
        self.resetSelectedEntries([])
    
    def GetValue(self):
        return self.table.GetCSV()


myEVT_CSV_CHANGED = wx.NewEventType()
EVT_CSV_CHANGED = wx.PyEventBinder(myEVT_CSV_CHANGED, 1)

class CSVChangedEvent(wx.PyCommandEvent):
    def __init__(self, obj):
        wx.PyCommandEvent.__init__(self, myEVT_CSV_CHANGED, id=obj.GetId())
        self.SetEventObject(obj)


class CSVCtrl(wx.Panel):
    """
    A control to allow the user to type in a filename or browse with
    the standard file dialog to select file
    """
    def __init__ (self, parent, id= -1,
                  pos = wx.DefaultPosition,
                  size = wx.DefaultSize,
                  style = wx.TAB_TRAVERSAL,
                  labelText= "Values:",
                  buttonText= "Edit",
                  toolTip= "Enter comma separated values by hand, or edit using the dialog",
                  # following are the values for a file dialog box
                  dialogTitle = "Edit Values",
                  initialValue = "",
                  labelWidth = 0
        ):
        """
        :param labelText:      Text for label to left of text field
        :param buttonText:     Text for button which launches the file dialog
        :param toolTip:        Help text
        :param dialogTitle:    Title used in file dialog
        :param labelWidth:     Width of the label
        """
      
        # store variables
        self.labelText = labelText
        self.buttonText = buttonText
        self.toolTip = toolTip
        self.dialogTitle = dialogTitle
        self.initialValue = initialValue
        self.labelWidth = labelWidth

        # create the panel
        self.createPanel(parent, id, pos, size, style)
        self.ChangeValue(initialValue)


    def createPanel(self, parent, id, pos, size, style):
        """Setup the sub-controls within the panel"""
        wx.Panel.__init__(self, parent, id, pos, size, style)
        self.SetMinSize(size) # play nice with sizers

        box = wx.BoxSizer(wx.HORIZONTAL)

        self.label = self.createLabel()
        box.Add(self.label, 0, wx.CENTER)

        self.textControl = self.createTextControl()
        box.Add(self.textControl, 1, wx.LEFT|wx.CENTER, 5)

        self.editButton = self.createEditButton()
        box.Add(self.editButton, 0, wx.LEFT|wx.CENTER, 5)

        # add a border around the whole thing and resize the panel to fit
        outsidebox = wx.BoxSizer(wx.VERTICAL)
        outsidebox.Add(box, 1, wx.EXPAND|wx.ALL, 3)
        outsidebox.Fit(self)

        self.SetAutoLayout(True)
        self.SetSizer(outsidebox)
        self.Layout()
        if type(size) == types.TupleType:
            size = apply(wx.Size, size)
        self.SetDimensions(-1, -1, size.width, size.height, wx.SIZE_USE_EXISTING)

#        if size.width != -1 or size.height != -1:
#            self.SetSize(size)

    def SetBackgroundColour(self, color):
        wx.Panel.SetBackgroundColour(self, color)
        self.label.SetBackgroundColour(color)

    def createLabel(self):
        """Create the label/caption"""
        label = wx.StaticText(self, -1, self.labelText, style=wx.ALIGN_RIGHT)
        font = label.GetFont()
        w, h, d, e = self.GetFullTextExtent(self.labelText, font)
        if self.labelWidth > 0:
            label.SetSize((self.labelWidth+5, h))
        else:
            label.SetSize((w+5, h))
        return label

    def createTextControl(self):
        """Create the text control"""
        textControl = wx.TextCtrl(self, -1)
        textControl.SetToolTipString(self.toolTip)
        textControl.Bind(wx.EVT_TEXT, self.OnChanged)
        textControl.Bind(wx.EVT_COMBOBOX, self.OnChanged)
        return textControl

    def OnChanged(self, evt):
        event = CSVChangedEvent(self)
        self.GetEventHandler().ProcessEvent(event)

    def createEditButton(self):
        """Create the edit-button control"""
        button = wx.Button(self, -1, self.buttonText)
        button.SetToolTipString(self.toolTip)
        button.Bind(wx.EVT_BUTTON, self.OnEdit)
        return button

    def OnEdit(self, event = None):
        """ Going to edit for file... """
        current = self.GetValue()
        
        dlg = CSVEditDialog(self, current)

        if dlg.ShowModal() == wx.ID_OK:
            self.SetValue(dlg.GetValue())
        dlg.Destroy()

    def GetValue(self):
        """
        retrieve current value of text control
        """
        return self.textControl.GetValue()

    def SetValue(self, value):
        """set current value of text control"""
        self.textControl.SetValue(value)

    def ChangeValue(self, value):
        """set current value of text control without firing an event"""
        self.textControl.ChangeValue(value)

    def Enable(self, value=True):
        """ Convenient enabling/disabling of entire control """
        self.label.Enable(value)
        self.textControl.Enable(value)
        return self.editButton.Enable(value)

    def Disable(self):
        """ Convenient disabling of entire control """
        self.Enable(False)

    def GetLabel(self):
        """ Retrieve the label's current text """
        return self.label.GetLabel()

    def SetLabel(self, value):
        """ Set the label's current text """
        rvalue = self.label.SetLabel(value)
        self.Refresh(True)
        return rvalue


if __name__ == '__main__':
    app   = wx.PySimpleApp()
    frame = wx.Frame(None, -1, title='Comma Separated List Test')
    frame.CreateStatusBar()
    
    ctrl = CSVCtrl(frame, -1, initialValue=", ".join([str(i) for i in range(300)]))
    sizer = wx.BoxSizer(wx.VERTICAL)
    sizer.Add(ctrl, 1, wx.EXPAND)
    
    frame.SetAutoLayout(1)
    frame.SetSizer(sizer)
    frame.Show(1)
    
    app.MainLoop()
