"""
wxPython Custom Widget Collection 20060207
Written By: Edward Flick (eddy -=at=- cdf-imaging -=dot=- com)
            Michele Petrazzo (michele -=dot=- petrazzo -=at=- unipex -=dot=- it)
            Will Sadkin (wsadkin-=at=- nameconnector -=dot=- com)
Copyright 2006 (c) CDF Inc. ( http://www.cdf-imaging.com )

Refactored by Rob McMullen as part of peppy (http://peppy.flipturn.org)

Contributed to the wxPython project under the wxPython project\'s license.
"""
import locale, wx, sys, cStringIO


class FakePopupWindow(wx.MiniFrame):
    def __init__(self, parent, style=None):
        super(FakePopupWindow, self).__init__(parent, style = wx.NO_BORDER |wx.FRAME_FLOAT_ON_PARENT
                              | wx.FRAME_NO_TASKBAR)
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
        print("On Focus: set focus to %s" % str(self.GetParent()))
        self.ActivateParent()
        evt.Skip()


class HighlightListBox(wx.VListBox):
    """Virtual List Box used to highlight partial matches in the ListCtrl"""
    def __init__(self, *args, **kwargs):
        wx.VListBox.__init__(self, *args, **kwargs)
        self.Bind(wx.EVT_SET_FOCUS, self.OnFocus)
        self.widths = []
        self.heights = []
        self.popup_width = 0
        self.largest_width = 0
        self.font = self.GetFont()
        self.bold_font = wx.Font(self.font.GetPointSize(), 
                                 self.font.GetFamily(),
                                 self.font.GetStyle(), wx.BOLD)
        
        # Since GetTextExtents is an expensive operation, we create a cache
        # here to store extents for the entire lifetime of this instance
        self.text_cache = {}
        self.bold_cache = {}
        
    def OnFocus(self, evt):
        """Raise and reset the focus to the parent window whenever
        we get focus.
        @param evt: event that called this handler

        """
        focus = self.GetParent().GetParent()
        #print("On Focus: set focus to %s" % str(focus))
        focus.SetFocus()
        evt.Skip()

    def setChoices(self, choices):
        """Resets the pulldown to contain a new list of possible matches
        
        @param choices: a list of text strings
        """
        self.choices = choices
        self.clearBold()
        self.SetItemCount(len(choices))
        
    def setBold(self, index, start, count):
        """Make an item show matched text at a given position
        
        Highlights a potential match by making showing part of the text using
        a bold font.
        
        @param index: index number of the item
        @param start: character position of first bold character
        @param count: number of bold characters
        """
        self.bold[index] = (start, start+count)
        self._calcWidth(index)
        #print(self.bold[index])
        self.RefreshLine(index)
        
    def clearBold(self):
        """Resets the entire list to clear any bold text.
        """
        self.bold = [None] * len(self.choices)
        self.calcWidths()
        if len(self.choices) > 0:
            self.RefreshLines(0, len(self.choices) - 1)
    
    def _calcWidth(self, index):
        """Calculate the widths of an individual entry.
        
        This is an internally used method that recalculates the widths of all
        the parts of a single entry -- the non-bold part before a match, the
        bold part of the match itself, and the non-bold part that hasn't been
        matched yet.
        
        @param index: index number of the item
        """
        height = 0
        width = 0
        text1, bold, text2 = self.getTextParts(index)
        if text1:
            try:
                w1, h1 = self.text_cache[text1]
            except KeyError:
                self.SetFont(self.font)
                w1, h1 = self.GetTextExtent(text1)
                self.text_cache[text1] = (w1, h1)
        else:
            w1, h1 = 0, 0
        
        if bold:
            try:
                w2, h2 = self.bold_cache[bold]
            except KeyError:
                self.SetFont(self.bold_font)
                w2, h2 = self.GetTextExtent(bold)
                self.bold_cache[bold] = (w2, h2)
        else:
            w2, h2 = 0, 0
        
        if text2:
            try:
                w3, h3 = self.text_cache[text2]
            except KeyError:
                self.SetFont(self.font)
                w3, h3 = self.GetTextExtent(text2)
                self.text_cache[text2] = (w3, h3)
        else:
            w3, h3 = 0, 0
        total = w1 + w2 + w3
        self.heights[index] = (max(h1, h2), h1, h2, h3)
        self.widths[index] = (total, w1, w2, w3)
        #print("_calcWidth: index=%d widths=%s" % (index, str(self.widths[index])))
        if self.largest_width is None:
            self.calc_scroll = (text1, bold, w1, w2)
            self.largest_width = total
        elif self.largest_width >= 0:
            if text1 == self.calc_scroll[0] and bold == self.calc_scroll[1]:
                if total > self.largest_width:
                    self.largest_width = total
            else:
                # found an entry that doesn't have the same prefix, so we can't
                # scroll the whole list
                self.largest_width = -1
        #print("%d: largest_width=%d text1=%s bold=%s" % (index, self.largest_width, text1, bold))
    
    def calcWidths(self):
        """Calculate the widths of all entries in the list
        
        Creates data structures used by the text positioning code when the
        choices are wide enough that they can't be shown in their entirety.
        This sets up the offset value so that the text can be drawn to show
        the part of the match that is at the end of the string so the user can
        see what's coming up next.
        """
        self.popup_width, dum = self.GetClientSizeTuple()
        count = len(self.choices)
        self.widths = [None] * count
        self.heights = [None] * count
        self.largest_width = None
        #print("calcWidths: %d items" % count)
        for i in range(count):
            self._calcWidth(i)
        
    def getTextParts(self, n):
        """Return the non-bold and bold parts of the text
        
        @returns tuple of non-bold, bold, non-bold text
        """
        if hasattr(self, 'bold') and self.bold[n] is not None:
            text = self.choices[n]
            start = self.bold[n][0]
            end = self.bold[n][1]
            return (text[0:start], text[start:end], text[end:])
        return (self.choices[n], "", "")
    
    # This method must be overridden.  When called it should draw the
    # n'th item on the dc within the rect.  How it is drawn, and what
    # is drawn is entirely up to you.
    def OnDrawItem(self, dc, rect, n):
        if self.GetSelection() == n:
            c = wx.SystemSettings.GetColour(wx.SYS_COLOUR_HIGHLIGHTTEXT)
        else:
            c = self.GetForegroundColour()
        dc.SetTextForeground(c)
        text1, bold, text2 = self.getTextParts(n)
        if self.largest_width > self.popup_width:
            x = rect.x + self.popup_width - self.largest_width
        else:
            x = rect.x + 2
        if text1:
            dc.SetFont(self.font)
            h = self.heights[n][1]
            y = rect.y + (rect.height - h) / 2
            dc.DrawText(text1, x, y)
            x += self.widths[n][1]
        if bold:
            dc.SetFont(self.bold_font)
            h = self.heights[n][2]
            y = rect.y + (rect.height - h) / 2
            dc.DrawText(bold, x, y)
            x += self.widths[n][2]
        if text2:
            dc.SetFont(self.font)
            h = self.heights[n][3]
            y = rect.y + (rect.height - h) / 2
            dc.DrawText(text2, x, y)

    # This method must be overridden.  It should return the height
    # required to draw the n'th item.
    def OnMeasureItem(self, n):
        return self.heights[n][0] + 5

    def selectNextMatch(self):
        """Set the selection to the next match in the list.
        
        A match is determined by any item that exists in the bold list.  The
        selection will wrap around to the top of the list.
        """
        start = self.GetSelection()
        index = start + 1
        count = self.GetLineCount()
        while index < count:
            if self.bold[index] is not None:
                break
            index += 1
        if index >= count:
            index = 0
            while index < start:
                if self.bold[index] is not None:
                    break
                index += 1
            if index == start and self.bold[index] is None:
                index += 1
                if index >= count:
                    index = 0
        if index < count:
            self.SetSelection(index)
    
    def selectPrevMatch(self):
        """Set the selection to the previous match in the list.
        
        A match is determined by any item that exists in the bold list.  The
        selection will wrap around to the bottom of the list.
        """
        start = self.GetSelection()
        index = start - 1
        count = self.GetLineCount()
        while index >= 0:
            if self.bold[index] is not None:
                break
            index -= 1
        if index < 0:
            index = count - 1
            while index > start:
                if self.bold[index] is not None:
                    break
                index -= 1
            if index == start and self.bold[index] is None:
                index -= 1
                if index < 0:
                    index = count - 1
        if index >= 0:
            self.SetSelection(index)

    def getLargestCommon(self, input):
        """Get the largest common string from the list of already matched strings.
        
        Using the list of strings that already have been matched, see if there
        are any more characters that can be matched that are in common among
        all of the strings.
        """
        found = None
        start = len(input)
        most = None
        for index, bold in enumerate(self.bold):
            if bold is not None:
                text = self.choices[index][bold[0]:]
                if found is None:
                    # get first match
                    found = text
                    most = len(found)
                else:
                    most = min(most, len(text))
                    for j in range(start, most):
                        if text[j] != found[j]:
                            most = j
                            break
                #print "after %d %s: found=%s most=%d" % (index, text, found, most)
        if not found:
            found = input
        else:
            found = found[0:most]
        return found


class TextCtrlAutoComplete(wx.TextCtrl):
    def __init__ (self, parent, choices=None, dropDownClick=True,
                  hideOnNoMatch=True, entryCallback=None, matchFunction=None,
                   mac=False,
                  **therest) :
        """
        Constructor works just like wx.TextCtrl except you can pass in a
        list of choices.  You can also change the choice list at any time
        by calling setChoices.
        """
        if therest.has_key('style'):
            therest['style']=wx.TE_PROCESS_ENTER | wx.TE_PROCESS_TAB |therest['style']
        else:
            therest['style']=wx.TE_PROCESS_ENTER | wx.TE_PROCESS_TAB
        wx.TextCtrl.__init__(self, parent, **therest )
        #Some variables
        self._dropDownClick = dropDownClick
        self._choices = choices
        self._lastinsertionpoint = 0
        self._hideOnNoMatch = hideOnNoMatch
        self._entryCallback = entryCallback
        self._matchFunction = matchFunction
        self._screenheight = wx.SystemSettings.GetMetric( wx.SYS_SCREEN_Y )
        self._tabCount = 0
        self._onlyAtStart = False

        self._mac = mac | bool(wx.Platform == '__WXMAC__')
        if self._mac:
            self.dropdown = FakePopupWindow(self)
        else:
            self.dropdown = wx.PopupWindow( self )

        self.dropdownlistbox = HighlightListBox(self.dropdown)
        if mac:
            self.Bind(wx.EVT_SET_FOCUS, self.OnSetFocus)
        
        self.Bind(wx.EVT_KILL_FOCUS, self.onControlChanged)
        
        self.SetChoices(choices)

        self.Bind(wx.EVT_TEXT, self.OnText)
        self.Bind(wx.EVT_KEY_DOWN, self.onKeyDown)
        #If need drop down on left click
        if dropDownClick:
            self.Bind ( wx.EVT_LEFT_DOWN , self.onClickToggleDown, self )
            self.Bind ( wx.EVT_LEFT_UP , self.onClickToggleUp, self )
        self.dropdown.Bind( wx.EVT_LISTBOX , self.onListItemSelected, self.dropdownlistbox )
        self.dropdownlistbox.Bind(wx.EVT_LEFT_DOWN, self.onListClick)
        self.dropdownlistbox.Bind(wx.EVT_LEFT_DCLICK, self.onListDClick)

    def onListClick(self, evt):
        toSel = self.dropdownlistbox.HitTest( evt.GetPosition() )
        #no values on poition, return
        if toSel == -1: return
        self.dropdownlistbox.SetSelection(toSel)

    def onListDClick(self, evt):
        self._setValueFromSelected()

    def OnText(self, evt):
        text = evt.GetString()
        #print("OnText: %s" % text)
        self.processText(text)
        evt.Skip()
    
    def processText(self, text=None):
        if text is None:
            text = self.GetValue()
        if self._entryCallback:
            self._entryCallback()
        self.dropdownlistbox.clearBold()
        #print("processText: %s" % text)
        if not text:
            # control is empty; hide dropdown if shown:
            if self.dropdown.IsShown():
                self._showDropDown(False)
            return
        best = None
        found = False
        nchar = len(text)
        choices = self._choices
        for numCh, choice in enumerate(choices):
            if self._matchFunction:
                index, count = self._matchFunction(text, choice)
                if count > 0:
                    found = True
                    self.dropdownlistbox.setBold(numCh, index, count)
            else:
                if self._onlyAtStart:
                    if choice.lower().startswith(text.lower()):
                        found = True
                        self.dropdownlistbox.setBold(numCh, 0, nchar)
                else:
                    index = choice.lower().find(text.lower())
                    if index >= 0:
                        found = True
                        self.dropdownlistbox.setBold(numCh, index, nchar)
            if found:
                if best is None:
                    best = numCh
        #print("best = %s" % best)
        if best is not None:
            self._showDropDown(True)
            # added call to calcWidths to allow popup to set the horizontal
            # offset if it turns out that the interesting parts of the
            # completion text would be off the screen to the right
            self.dropdownlistbox.calcWidths()
            self.dropdownlistbox.SetSelection(-1)
            #self.SetFocus()
        else:
            self.dropdownlistbox.SetSelection(-1)
            if self._hideOnNoMatch:
                self._showDropDown(False)
        self._listItemVisible()

    def onKeyDown ( self, event ) :
        """ Do some work when the user press on the keys:
            up and down: move the cursor
            left and right: move the search
        """
        skip = True
        dd = self.dropdownlistbox
        sel = dd.GetSelection()
        visible = self.dropdown.IsShown()
        KC = event.GetKeyCode()
        #print("keycode = %d" % KC)
        if KC == wx.WXK_DOWN :
            if sel < (dd.GetItemCount () - 1) :
                dd.SetSelection ( sel+1 )
                self._listItemVisible()
            self._showDropDown ()
            skip = False
        elif KC == wx.WXK_UP :
            if sel == -1:
                dd.SetSelection(dd.GetLineCount() - 1)
                self._listItemVisible()
            elif sel > 0 :
                dd.SetSelection ( sel - 1 )
                self._listItemVisible()
            self._showDropDown ()
            skip = False
        elif KC == wx.WXK_HOME:
            dd.SetSelection(0)
        elif KC == wx.WXK_END:
            dd.SetSelection(dd.GetLineCount() - 1)
        elif KC == wx.WXK_PAGEDOWN:
            if sel == -1:
                dd.SetSelection(0)
            else:
                first = dd.GetVisibleBegin()
                last = dd.GetVisibleEnd()
                if not dd.IsVisible(last):
                    last -= 1
                dd.ScrollPages(1)
                dd.SetSelection(last)
        elif KC == wx.WXK_PAGEUP:
            if sel == -1:
                dd.SetSelection(dd.GetLineCount() - 1)
            else:
                first = dd.GetVisibleBegin()
                last = dd.GetVisibleEnd()
                dd.ScrollPages(-1)
                dd.SetSelection(first)
        elif KC == wx.WXK_RIGHT:
            # A right arrow at the end of the string is equivalent to a tab
            if self.GetInsertionPoint() == self.GetLastPosition():
                KC = wx.WXK_TAB
        if KC == wx.WXK_TAB:
            #print self._choices
            if self._choices:
                self._showDropDown ()

                # Find the largest common match in the list of choices
                # and expand to that
                input = self.GetValue()
                text = dd.getLargestCommon(input)
                if text != input:
                    self.SetValue(text)
                    self.SetInsertionPointEnd()
                else:
                    self._tabCount = 1
                self._tabCount += 1
                if self._tabCount > 1:
                    # scroll the list on multiple consecutive tabs
                    if event.GetModifiers() & wx.MOD_SHIFT:
                        dd.selectPrevMatch()
                    else:
                        dd.selectNextMatch()
                        
            skip = False
        else:
            self._tabCount = 0
        if visible :
            if event.GetKeyCode() == wx.WXK_RETURN :
                self._setValueFromSelected()
                #skip = False
            if event.GetKeyCode() == wx.WXK_ESCAPE :
                self._showDropDown( False )
                skip = False
        if skip :
            event.Skip()

    def onListItemSelected (self, event):
        self._setValueFromSelected()
        event.Skip()

    def onClickToggleDown(self, event):
        self._lastinsertionpoint = self.GetInsertionPoint()
        event.Skip ()

    def onClickToggleUp ( self, event ) :
        if ( self.GetInsertionPoint() == self._lastinsertionpoint ) :
            self._showDropDown ( not self.dropdown.IsShown() )
        wx.CallAfter(self.setFocusCallback)
        event.Skip ()
    
    def setFocusCallback(self, end=False):
        """Callback for use within wx.CallAfter to prevent focus being set
        after the control has been removed.
        """
        #print("Here in setFocusCallback")
        if self:
            #print("setting focus")
            self.SetFocus()
            if end:
                self.SetInsertionPointEnd()
    
    def OnSetFocus(self, evt):
        #print("OnSetFocus: insertion point = %d" % self.GetLastPosition())
        wx.CallAfter(self.SetInsertionPointEnd)

    def onControlChanged(self, event):
        changed = event.GetEventObject()
        other = event.GetWindow()
        #print("changed=%s other=%s" % (changed, other))
        if self._mac:
            wx.CallAfter(self.setFocusCallback, True)
            event.Skip()
            return
        if self.dropdown.IsShown():
            self._showDropDown( False )
#            if self._mac:
#                if changed == self:
#                    wx.CallAfter(self.SetFocus)
#                else:
#                    self._showDropDown( False )
#            else:
#                self._showDropDown( False )
        event.Skip()

    def SetChoices(self, choices):
        """
        Sets the choices available in the popup wx.ListBox.
        The items will be sorted case insensitively.
        """
        if not isinstance(choices, list):
            self._choices = [ x for x in choices]
        else:
            self._choices = choices
        self.dropdownlistbox.setChoices(self._choices)
        #prevent errors on "old" systems
        if sys.version.startswith("2.3"):
            self._choices.sort(lambda x, y: cmp(x.lower(), y.lower()))
        else:
            try:
                self._choices.sort(key=lambda x: locale.strxfrm(x).lower())
            except UnicodeEncodeError:
                self._choices.sort(key=lambda x: locale.strxfrm(x.encode("UTF-8")).lower())
        self._setListSize()

    def GetChoices(self):
        return self._choices

    def SetSelectCallback(self, cb=None):
        self._selectCallback = cb

    def SetEntryCallback(self, cb=None):
        self._entryCallback = cb

    def SetMatchFunction(self, mf=None):
        self._matchFunction = mf

    #-- Internal methods
    def _setValueFromSelected( self ) :
        """
        Sets the wx.TextCtrl value from the selected wx.ListCtrl item.
        Will do nothing if no item is selected in the wx.ListCtrl.
        """
        sel = self.dropdownlistbox.GetSelection()
        if sel > -1:
            itemtext = self._choices[sel]
            self.SetValue (itemtext)
            self.SetInsertionPointEnd ()
            self.SetSelection(-1, -1)
            self._showDropDown ( False )

    def _showDropDown ( self, show = True ) :
        """
        Either display the drop down list (show = True) or hide it (show = False).
        """
        if show :
            size = self.dropdown.GetSize()
            width, height = self . GetSizeTuple()
            x, y = self . ClientToScreenXY ( 0, height )
            if size.GetWidth() != width :
                size.SetWidth(width)
                self.dropdown.SetSize(size)
                self.dropdownlistbox.SetSize(self.dropdown.GetClientSize())
            if (y + size.GetHeight()) < self._screenheight :
                self.dropdown . SetPosition ( wx.Point(x, y) )
            else:
                self.dropdown . SetPosition ( wx.Point(x, y - height - size.GetHeight()) )
        self.dropdown.Show ( show )
        wx.CallAfter(self.setFocusCallback)

    def _listItemVisible( self ) :
        """
        Moves the selected item to the top of the list ensuring it is always visible.
        """
        toSel =  self.dropdownlistbox.GetSelection ()
        if toSel == -1: return
        self.dropdownlistbox.SetSelection( toSel )

    def _setListSize(self):
        choices = self._choices
        longest = 0
        for choice in choices :
            longest = max(len(choice), longest)
        longest += 3
        itemcount = min( len( choices ) , 7 ) + 2
        charheight = self.dropdownlistbox.GetCharHeight()
        charwidth = self.dropdownlistbox.GetCharWidth()
        self.popupsize = wx.Size( charwidth*longest, charheight*itemcount )
        self.dropdownlistbox.SetSize ( self.popupsize )
        self.dropdown.SetClientSize( self.popupsize )


if __name__ == "__main__":
    dynamic_choices = [
                    'aardvark', 'abandon', 'acorn', 'acute', 'adore',
                    'aegis', 'ascertain', 'asteroid',
                    'beautiful', 'bold', 'classic',
                    'daring', 'daft', 'debonair', 'definitive', 'defective',
                    'effective', 'elegant',
                    'http://python.org', 'http://www.google.com',
                    'fabulous', 'fantastic', 'friendly', 'forgiving', 'feature',
                    'really long entry with lots of qqqqqqqqqqq 1',
                    'really long entry with lots of qqqqqqqqqqq 2',
                    'really long entry with lots of qqqqqqqqqqq 3',
                    'sage', 'scarlet', 'scenic', 'seaside', 'showpiece', 'spiffy',
                    'www.wxPython.org', 'www.osafoundation.org',
                    'yyyyyyzqqqq1', 'yyyyyyaqqqq', 'yyyyyyzqqq', 'zqqqq2222', 'zqqqq2228',
                    ]
    app = wx.PySimpleApp()
    frm = wx.Frame(None,-1,"Test",style=wx.TAB_TRAVERSAL|wx.DEFAULT_FRAME_STYLE,
                   size=(300,300))
    panel = wx.Panel(frm)
    stack = wx.BoxSizer(wx.VERTICAL)
    sizer = wx.BoxSizer(wx.HORIZONTAL)
    text = wx.StaticText(panel, -1, "Normal:")
    sizer.Add(text, 0, wx.ALIGN_CENTER)
    normal = TextCtrlAutoComplete(panel, choices=dynamic_choices)
    sizer.Add(normal, 1, wx.EXPAND)
    stack.Add(sizer, 0, wx.EXPAND)
    
    text = wx.StaticText(panel, -1, "\nMac OSX version only works correctly on OSX")
    stack.Add(text, 0, wx.EXPAND)

    sizer = wx.BoxSizer(wx.HORIZONTAL)
    text = wx.StaticText(panel, -1, "Mac OSX:")
    sizer.Add(text, 0, wx.ALIGN_CENTER)
    mac = TextCtrlAutoComplete(panel, mac=True, choices=dynamic_choices)
    sizer.Add(mac, 1, wx.EXPAND)
    stack.Add(sizer, 0, wx.EXPAND)
    
    text = wx.StaticText(panel, -1, "\n\n")
    stack.Add(text, 0, wx.EXPAND)
    
    sizer = wx.BoxSizer(wx.HORIZONTAL)
    text = wx.StaticText(panel, -1, "Long:")
    sizer.Add(text, 0, wx.ALIGN_CENTER)
    count = 15
    long_choices = ['really really long entry with lots of qqqqqqqqqqqs: %d' % i for i in range(count)]
    long = TextCtrlAutoComplete(panel, choices=long_choices)
    sizer.Add(long, 1, wx.EXPAND)
    stack.Add(sizer, 0, wx.EXPAND)
    
    panel.SetAutoLayout(True)
    panel.SetSizer(stack)
    sizer.Fit(panel)
    sizer.SetSizeHints(panel)
    panel.Layout()
    app.SetTopWindow(frm)
    frm.Show()
    app.MainLoop()
