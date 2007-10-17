# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Tutorial plugin.

This tutorial shows some simple examples about how to start extending Peppy.

It currently includes an action and a minor mode, but will be expanded as
time goes on.  The goal is to show as many common features as I can, so you
won't be surprised as much when you try to create more complicated examples.
"""

import os

import wx

from peppy.yapsy.plugins import *
from peppy.minor import *
from peppy.menu import *


class InsertHelloWorld(SelectAction):
    """Simple example of an action that modifies the buffer
    
    This is an action that depends on the current buffer being a text file,
    and inserts the string "Hello, world" into the text at the current
    position
    """
    # This alias holds an emacs style name that is used during M-X processing
    # If you don't want this action to have an emacs style name, don't
    # include this or set it equal to None
    alias = "insert-hello-world"
    
    # This is the name of the menu entry as it appears in the menu bar
    # i18n processing happens within the menu system, so no need here to
    # wrap this in a call to the _ function
    name = "Hello World Action"
    
    # Tooltip that is displayed when the mouse is hovering over the menu
    # entry
    tooltip = "Insert 'Hello, world' at the current cursor position"
    
    # If there is an icon associated with this action, name it here.  Icons
    # are referred to by path name relative to the peppy directory.  A toolbar
    # entry will be automatically created if the icon is specified here, unless
    # you specify default_toolbar = False
    icon = None
    
    # The default menu location is specified here as a tuple containing
    # the menu path (separated by / characters) and a number between 1 and
    # 1000 representing the position within the menu.  A negative number
    # means that a separator should appear before the item
    default_menu = ("&Help/Tests", -801)
    
    # Key bindings are specified in this dictionary, where any number
    # of platform strings may be specified.  A platform named 'default'
    # may also be included
    key_bindings = {'win': "Ctrl-Alt-F10", 'emacs': "C-F9 C-F9",}
    
    # Don't forget to declare worksWithMajorMode a classmethod!  It is used
    # before the instance of the action is created
    @classmethod
    def worksWithMajorMode(cls, mode):
        """This action requires that we're editing using something with
        the ability to insert a string.
        """
        # This class method is used before creating the action to report
        # if the action will work with the major mode.  We could hard-code
        # the requirement to work with FundamentalMode, but who knows if
        # that will be too limiting in the future.  We can also check for
        # specific attributes of the editing window, which is what I'm
        # doing here.
        return hasattr(mode.editwin, 'AddText')
    
    # The enable state of the menu or toolbar entry is controlled here
    # Actions are created and destroyed all the time, so don't save any
    # state information here -- all state information must be stored
    # extrinsically.
    def isEnabled(self):
        # If the buffer is read-only, we won't be able to insert a string,
        # so only allow insertion if it's not read-only
        return not self.mode.buffer.readonly
    
    # Here's where the action is actually performed.  This same method is
    # called regardless of how the action was initiated by the user: menubar,
    # toolbar, or keyboard
    def action(self, index=-1, multiplier=1):
        # Note: index is only used if the action is part of a list or radio
        # button list, and ignored otherwise.  multiplier is used in response
        # to an emacs-style universal argument -- a keyboard request to
        # repeat the action 'multiplier' number of times.  It's currently
        # possible that multiplier could be zero or negative.
        
        hello = "Hello, world"
        # It doesn't make sense for all actions to respond to the multiplier,
        # so you may ignore it if you wish.  I'll handle it here:
        for i in range(0, multiplier):
            self.mode.editwin.AddText(hello)


class SmileyFaceMinorMode(MinorMode, wx.PyControl):
    """Draws a smiley face centered in the window.
    
    This is a simple example of a minor mode that can be used as a template
    for a minor mode that draws graphics to the window.  It is about as simple
    as a minor mode as you can get.  No user interaction at all, just a window
    that hopefully adds a bit of fun to your day.
    """
    # All minor modes need a unique keyword
    keyword="Smiley"
    
    # classprefs are inherited from all the parent classes that descend from
    # a subclass of ClassPrefs.  The class attribute default_classprefs
    # describes the type, initial default value, and any help text that
    # goes along with a configuration variable.  Any configuration variable
    # can be saved in the main peppy configuration file with the section
    # corresponding to the name of the class.
    
    # In addition to the classprefs listed in the MinorMode superclass,
    # you can define your own classprefs here.  You may also override any
    # classprefs in the parent, although be sure not to change the type or
    # the operations performed by the parent may fail if it is expecting
    # e.g. an integer and you change it to a string.
    default_classprefs = (
        IntParam('pen_width', 3, 'width of pen for drawing lines'),
        StrParam('pen_color', 'black', 'color of lines'),
        StrParam('background_color', 'white', 'background color of window'),
        StrParam('face_color', 'gold', 'color of smiley face'),
    )
    
    # This class method must be defined in all minor modes -- it verifies
    # that this minor mode can interact with the major mode.  Usually it
    # should check for some characteristics in the major mode or attributes
    # of the major mode.
    @classmethod
    def worksWithMajorMode(self, mode):
        # The smiley face has no dependencies on any major mode.  It works
        # with anything, so just return True here.
        return True

    def __init__(self, major, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize):
        # This is just a simple PyControl, so call the superclass __init__
        wx.PyControl.__init__(self, parent, id, pos, size, wx.NO_BORDER)
        
        # and set up the event bindings.  All the work is done in the
        # OnPaint method
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_SIZE, self.OnSize)
        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)

    def OnPaint(self, evt):
        dc = wx.PaintDC(self)
        
        # Figure out the radius of the smiley, taking the pen width into
        # account so we don't go outside the bounds
        size = self.GetClientSize()
        if size.x > size.y:
            radius = size.y/2 - self.classprefs.pen_width
        else:
            radius = size.x/2 - self.classprefs.pen_width
        
        # Always draw the smiley centered in the window
        cx = size.x/2
        cy = size.y/2

        dc.SetBrush(wx.Brush(self.classprefs.face_color))
        dc.SetPen(wx.Pen(self.classprefs.pen_color, self.classprefs.pen_width))
        dc.DrawCircle(cx, cy, radius)
        
        # Choose the eye offsets and draw the vertical lines
        eye_dx = radius/4
        eye_dy = radius/3
        dc.DrawLine(cx - eye_dx, cy - 2*eye_dy, cx - eye_dx, cy - eye_dy)
        dc.DrawLine(cx + eye_dx, cy - 2*eye_dy, cx + eye_dx, cy - eye_dy)
        
        # Draw the smile as an ellipse, slightly offset from center
        radsmile = radius*3/5
        dc.DrawEllipticArc(cx - radsmile, cy, 2 * radsmile, radsmile, 0.0, -180.0)
        
    def OnEraseBackground(self, evt):
        dc = evt.GetDC()
        if not dc:
            dc = wx.ClientDC(self)
            rect = self.GetUpdateRegion().GetBox()
            dc.SetClippingRect(rect)
        dc.SetBackground(wx.Brush(self.classprefs.background_color))
        dc.Clear()

    def OnSize(self, evt):
        self.Refresh()
        evt.Skip()


class TutorialPlugin(IPeppyPlugin):
    """The plugin object for the tutorial.
    
    The plugin object describes the additional functionality that is provided
    by this code.  There are a variety of interface methods provided by the
    superclass IPeppyPlugin, and only the interfaces actually used by the
    plugin need to be defined here.  All others default to no-ops.
    """
    # All actions that you want to be visible to peppy should be returned
    # in getActions
    def getActions(self):
        # You can return a list or yield the items individually
        return [InsertHelloWorld]
    
    # All minor modes defined in the file that you want to be visible to
    # peppy should be returned here
    def getMinorModes(self):
        # We have just one minor mode, so you can return it as a list of one
        # element, or you can yield it.
        yield SmileyFaceMinorMode
