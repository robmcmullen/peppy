###############################################################################
# Name: colorsetter.py                                                        #
# Purpose: Color Picker/Setter Control                                        #
# Author: Cody Precord <cprecord@editra.org>                                  #
# Copyright: (c) 2008 Cody Precord <staff@editra.org>                         #
# License: wxWindows License                                                  #
###############################################################################

"""
Editra Control Library: ColorSetter

       
"""

__author__ = "Cody Precord <cprecord@editra.org>"
__svnid__ = "$Id: colorsetter.py 54470 2008-07-02 23:26:27Z CJP $"
__revision__ = "$Revision: 54470 $"

#-----------------------------------------------------------------------------#
# Imports
import wx
import wx.lib.colourselect as csel

#-----------------------------------------------------------------------------#
# Globals

_ = wx.GetTranslation
#-----------------------------------------------------------------------------#

def HexToRGB(hex_str):
    """Returns a list of red/green/blue values from a
    hex string.
    @param hex_str: hex string to convert to rgb

    """
    hexval = hex_str
    if hexval[0] == u"#":
        hexval = hexval[1:]
    ldiff = 6 - len(hexval)
    hexval += ldiff * u"0"
    # Convert hex values to integer
    red = int(hexval[0:2], 16)
    green = int(hexval[2:4], 16)
    blue = int(hexval[4:], 16)
    return [red, green, blue]

csEVT_COLORSETTER = wx.NewEventType()
EVT_COLORSETTER = wx.PyEventBinder(csEVT_COLORSETTER, 1)
class ColorSetterEvent(wx.PyCommandEvent):
    """Event to signal that text needs updating"""
    def __init__(self, etype, eid, value=None):
        """Creates the event object"""
        wx.PyCommandEvent.__init__(self, etype, eid)
        self._value = value

    def GetValue(self):
        """Returns the value from the event.
        @return: the value of this event

        """
        return self._value

#-----------------------------------------------------------------------------#

class ColorSetter(wx.Panel):
    """Control for setting and selecting a color to describe the
    various styling of the text control.

    """
    def __init__(self, parent, id_, color=wx.NullColor):
        """Create the control, it is a composite of a colourSelect and
        and a text control.
        @keyword label: the hex string value to go in the text portion

        """
        wx.Panel.__init__(self, parent, id_)

        if isinstance(color, tuple):
            color = wx.Color(*color)

        # Attributes
        self._label = color.GetAsString(wx.C2S_HTML_SYNTAX)
        self._txt = wx.TextCtrl(self,
                                value=self._label,
                                style=wx.TE_CENTER,
                                validator=HexValidator())
        txtheight = self._txt.GetTextExtent('#000000')[1]
        self._txt.SetMaxSize((-1, txtheight + 4))
        self._txt.SetToolTip(wx.ToolTip(_("Enter a hex color value")))
        self._cbtn = csel.ColourSelect(self, colour=color,
                                       size=(20, 20))
        self._DoLayout()

        # Event Handlers
        self.Bind(csel.EVT_COLOURSELECT, self.OnColour)
        self._txt.Bind(wx.EVT_KEY_UP, self.OnTextChange)
        self._txt.Bind(wx.EVT_TEXT_PASTE, self.OnTextChange)
        self._txt.Bind(wx.EVT_KEY_DOWN, self.OnValidateTxt)

    def __PostEvent(self):
        """Notify the parent window of any value changes to the control"""
        value = self._cbtn.GetValue()
        if not isinstance(value, wx.Color):
            value = wx.Color(*value)

        evt = ColorSetterEvent(csEVT_COLORSETTER, self.GetId(), value)
        wx.PostEvent(self.GetParent(), evt)

    def __UpdateValues(self):
        """Update the values based on the current state of the text control"""
        cpos = self._txt.GetInsertionPoint()
        hexstr = self._txt.GetValue().replace('#', '').strip()
        valid = ''
        for char in hexstr:
            if char in '0123456789abcdefABCDEF':
                valid = valid + char

        if len(valid) > 6:
            valid = valid[:6]

        valid = '#' + valid
        self._txt.SetValue(valid)
        self._txt.SetInsertionPoint(cpos)
        valid = valid + (u'0' * (6 - len(valid)))
        self._cbtn.SetValue(HexToRGB(valid))

    def _DoLayout(self):
        """Layout the controls"""
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self._txt, 0, wx.EXPAND|wx.ALIGN_CENTER_VERTICAL)
        sizer.Add((5, 5), 0)
        sizer.Add(self._cbtn, 0, wx.ALIGN_LEFT|wx.ALIGN_CENTER_VERTICAL)
        self.SetSizer(sizer)

    def GetColour(self):
        """Returns the colour value of the control
        @return: wxColour object

        """
        return self._cbtn.GetValue()

    def GetLabel(self):
        """Gets the hex value from the text control
        @return: string '#123456'
        @note: ensures a full 6 digit hex value is returned, padding
               with zero's where necessary

        """
        hexstr = self._txt.GetValue()
        hexstr = hexstr.replace('#', '').replace(' ', '')
        hexstr = '#' + hexstr + ('0' * (6 - len(hexstr)))
        return hexstr

    def OnColour(self, evt):
        """Update the button and text control value
        when a choice is made in the colour dialog.
        @param evt: EVT_COLOURSELECT

        """
        e_val = evt.GetValue()[0:3]
        red = hex(e_val[0])
        green = hex(e_val[1])
        blue = hex(e_val[2])
        hex_str = "#%s%s%s" % (red[2:].zfill(2).upper(),
                               green[2:].zfill(2).upper(),
                               blue[2:].zfill(2).upper())
        self._txt.SetValue(hex_str)
        self._cbtn.SetValue(wx.Color(e_val[0], e_val[1], e_val[2]))
        self.__PostEvent()

    def OnTextChange(self, evt=None):
        """Catch when text changes in the text control and update
        button accordingly.
        @keyword evt: event that called this handler

        """
        self.__UpdateValues()
        self.__PostEvent()

    def OnUpdateUI(self, evt):
        """Cleanup any bad characters and formating in the display
        @param evt: UpdateUI

        """
        ret = u''
        for char in self._txt.GetValue().replace('#', ''):
            if char in '0123456789abcdefABCDEF':
                ret = ret + char

        if ret != self._txt.GetValue():
            cpos = self._txt.GetInsertionPoint()
            self._txt.SetValue(u'#' + ret)
            self._txt.SetInsertionPoint(cpos)

    def OnValidateTxt(self, evt):
        """Validate text to ensure only valid hex characters are entered
        @param evt: wxEVT_KEY_DOWN

        """
        code = evt.GetKeyCode()
        if code in [wx.WXK_DELETE, wx.WXK_BACK, wx.WXK_LEFT, wx.WXK_RIGHT] or \
           evt.CmdDown():
            evt.Skip()
            return

        key = unichr(code)
        if (key.isdigit() and evt.ShiftDown()) or \
           evt.AltDown() or evt.MetaDown():
            return

        if key in "0123456789ABCDEFabcdef#" and \
           (len(self._txt.GetValue().lstrip("#")) < 6 or \
            self._txt.GetStringSelection()):
            evt.Skip()

    def SetLabel(self, label):
        """Set the label value of the text control
        @param label: hex string to set label to

        """
        self._txt.SetValue(label)
        self.__UpdateValues()

    def SetValue(self, colour):
        """Set the color value of the button
        @param colour: wxColour or 3 tuple to set colour value to

        """
        self._cbtn.SetValue(colour)
        red, green, blue = colour[0:3]
        hex_str = "#%s%s%s" % (hex(red)[2:].zfill(2).upper(),
                               hex(green)[2:].zfill(2).upper(),
                               hex(blue)[2:].zfill(2).upper())
        self._txt.SetValue(hex_str)

#-----------------------------------------------------------------------------#

class HexValidator(wx.PyValidator):
    """Validate Hex strings for the color setter"""
    def __init__(self):
        """Initialize the validator

        """
        wx.PyValidator.__init__(self)

        # Event Handlers
        self.Bind(wx.EVT_CHAR, self.OnChar)

    def Clone(self):
        """Clones the current validator
        @return: clone of this object

        """
        return HexValidator()

    def Validate(self, win):
        """Validate an window value
        @param win: window to validate

        """
        return win.GetValue() in '#0123456789abcdefABCDEF'

    def OnChar(self, event):
        """Process values as they are entered into the control
        @param event: event that called this handler

        """
        key = event.GetKeyCode()
        if event.CmdDown() or key < wx.WXK_SPACE or key == wx.WXK_DELETE or \
           key > 255 or chr(key) in '0123456789abcdefABCDEF':
            event.Skip()
            return

        if not wx.Validator_IsSilent():
            wx.Bell()

        return
