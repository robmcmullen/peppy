# --------------------------------------------------------------------------- #
# WIDGETSTACK Widget wxPython IMPLEMENTATION
# License: wxWidgets license
#
#
# Python Code By:
#
# Andrea Gavana, @ 03 Apr 2007
# Latest Revision: 03 Apr 2007, 20.00 GMT
#
#
# For All Kind Of Problems, Requests Of Enhancements And Bug Reports, Please
# Write To Me At:
#
# andrea.gavana@gmail.com
# gavana@kpo.kz
#
# Or, Obviously, To The wxPython Mailing List!!!
#
#
# End Of Comments
# --------------------------------------------------------------------------- #


"""
The WidgetStack class provides a stack of widgets of which only the top widget
is user-visible.
The application programmer can move any widget to the top of the stack at any
time using RaiseWidget(), and add or remove widgets using AddWidget() and
RemoveWidget(). It is not sufficient to pass the widget stack as parent to a
widget which should be inserted into the widgetstack. 

VisibleWidget() is the get equivalent of RaiseWidget(); it returns a pointer
to the widget that is currently at the top of the stack.
License And Version:

WidgetStack is freeware and distributed under the wxPython license. 

Latest revision: Andrea Gavana @ 03 Apr 2007, 20.00 GMT

Version 0.1.

"""

__docformat__ = "epytext"
__version__ = "0.1"


#----------------------------------------------------------------------
# Beginning Of WIDGETSTACK wxPython Code
#----------------------------------------------------------------------

import wx

class WidgetStack(wx.Panel):

    def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition, size=wx.DefaultSize,
                 style=0, name="WidgetStack"):
        """
        Default class constructor.        
        """

        # Keep the wx.TAB_TRAVERSAL style for the panel
        style |= wx.TAB_TRAVERSAL
        wx.Panel.__init__(self, parent, id, pos, size, style, name)

        # This is the main sizer that allows us to switch between
        # The widgets in the stack
        self._sizer = wx.BoxSizer(wx.VERTICAL) 
        self.SetSizer(self._sizer) 
 
 
    def AddWidget(self, widget):
        """ Add the specified widget to the stack. """
 
        if widget is None:
            return 

        if widget.GetParent() != self:
            # We are not the parent of this widget?
            widget.Reparent(self)

        if self.HasVisibleWidget():
            # There already is one visible widget, hide the added one
            widget.Show(False)

        # Add the widget to our main container
        self._sizer.Add(widget, 1, wx.EXPAND, 0)

 
    def RemoveWidget(self, widget):
        """ Removes a widget from the stack and destroys it. """
 
        self._sizer.Detach(widget) 
        widget.Destroy() 
 

    def RaiseWidget(self, indexOrWidget):
        """
        Raise a widget, i.e. shows it. indexOrWidget can be the widget index
        in the stack or the widget itself.
        """

        childToRaise = None        
        children = self._sizer.GetChildren()
        
        # Loop over all the sizer's children
        for counter, sizer_item in enumerate(children):
            child = sizer_item.GetWindow()
            if counter == indexOrWidget or child == indexOrWidget:
                # Got it, we found the widget to raise
                childToRaise = child
                break

        if not childToRaise:
            # No correspondance, no child to raise. Go back
            return
        
        oldChild, childIndex = self.VisibleWidget()
        
        # Send a wx.wxEVT_COMMAND_NOTEBOOK_PAGE_CHANGING to the caller
        # I know that maybe wx.wxEVT_COMMAND_NOTEBOOK_PAGE_CHANGING is not the most
        # proper event to send, but at least is consistent with wx.Notebook
        event = wx.NotebookEvent(wx.wxEVT_COMMAND_NOTEBOOK_PAGE_CHANGING, self.GetId())
        event.SetOldSelection(childIndex)
        event.SetSelection(counter)
        event.SetEventObject(self)

        if self.GetEventHandler().ProcessEvent(event) or not event.IsAllowed():
            # We have been blocked by the caller, no widget raising
            return

        # Freeze everything... it helps with flicker.
        self.Freeze()

        # Hide the old child        
        oldChild.Show(False)
        # Show the new widget
        childToRaise.Show(True)
        # Layout the sizer
        self._sizer.Layout()

        # Time to warm up...
        self.Thaw()
        

    def HasVisibleWidget(self):
        """ Returns whether there is a widget shown or not. """

        children = self._sizer.GetChildren()
        
        # Loop over all the sizer's children
        for child in children:
            if child.IsShown():
                return True

        # No widget shown till now        
        return False            
            

    def VisibleWidget(self):
        """ Returns the current visible widget, as a tuple of (widget, index). """

        children = self._sizer.GetChildren()

        # Loop over all the sizer's children        
        for indx, child in enumerate(children):
            if child.IsShown():
                return child, indx

        return None, -1

