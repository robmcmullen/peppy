# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""Sidebar for debug printing.

Sidebar that shows classes that have debug printing capability.

FIXME: this doesn't yet update between frames, so items may be out of
sync if this is shown on two different frames.
"""

import os

from peppy.yapsy.plugins import *
from peppy.menu import *
from peppy.sidebar import *

from wx.lib.pubsub import Publisher


class DebugClass(ToggleListAction):
    """A multi-entry menu list that allows individual toggling of debug
    printing for classes.

    All frames will share the same list, which makes sense since the
    debugging is controlled by class attributes.
    """
    debuglevel=0
    
    name = "DebugClassMenu"
    empty = "< list of classes >"
    tooltip = "Turn on/off debugging for listed classes"
    default_menu = "Debug"
    categories = False
    inline = True

    # File list is shared among all windows
    itemlist = []

    @staticmethod
    def append(kls,text=None):
        """Add a class to the list of entries

        @param kls: class
        @type kls: class
        @param text: (optional) name of class
        @type text: text
        """
        if not text:
            text=kls.__name__
        DebugClass.itemlist.append({'item':kls,'name':text,'icon':None,'checked':kls.debuglevel>0})

    @staticmethod
    def setup(msg):
        app = wx.GetApp()
        debuggable=getAllSubclassesOf()
        debuggable.sort(key=lambda s:s.__name__)
        for kls in debuggable:
            if app.verbose:
                app.setVerboseLevel(kls)
            #assert dprint("%s: %d (%s)" % (kls.__name__,kls.debuglevel,kls))
            DebugClass.append(kls)

        
    def getHash(self):
        return len(DebugClass.itemlist)

    def getItems(self):
        return [item['name'] for item in DebugClass.itemlist]

    def isChecked(self, index):
        return DebugClass.itemlist[index]['checked']

    def action(self, index=-1, multiplier=1):
        """
        Turn on or off the debug logging for the selected class
        """
        assert self.dprint("DebugClass.action: id(self)=%x name=%s index=%d id(itemlist)=%x" % (id(self),self.name,index,id(DebugClass.itemlist)))
        kls=DebugClass.itemlist[index]['item']
        DebugClass.itemlist[index]['checked']=not DebugClass.itemlist[index]['checked']
        if DebugClass.itemlist[index]['checked']:
            kls.debuglevel=1
        else:
            kls.debuglevel=0
        assert self.dprint("class=%s debuglevel=%d" % (kls,kls.debuglevel))

Publisher().subscribe(DebugClass.setup, 'peppy.startup.complete')


class DebugClassList(Sidebar, wx.CheckListBox, debugmixin):
    """Turn debug printing on or off for the listed classes.

    This is a global plugin that is used to turn on or off debug
    printing for all the classes that subclass from L{debugmixin}.
    """
    debuglevel = 0
    
    keyword = "debug_list"
    caption = "Debug Printing"

    default_classprefs = (
        IntParam('best_width', 200),
        IntParam('best_height', 500),
        IntParam('min_width', 100),
        IntParam('min_height', 100),
        BoolParam('show', False),
        )
    
    def __init__(self, parent):
##        self.browser=wx.TextCtrl(parent, -1, "Stuff" , style=wx.TE_MULTILINE)
        self.debuglist = DebugClass(parent)
        items = self.debuglist.getItems()
        wx.CheckListBox.__init__(self, parent, choices=items, pos=(9000,9000))
        
        assert self.dprint(items)
        for i in range(len(items)):
            self.Check(i, self.debuglist.isChecked(i))
        self.Bind(wx.EVT_CHECKLISTBOX, self.OnCheckListBox)

    def OnCheckListBox(self, evt):
        index = evt.GetSelection()
        self.debuglist.action(index)
        assert self.dprint("index=%d checked=%s" % (index, self.debuglist.isChecked(index)))
        self.Check(index, self.debuglist.isChecked(index))

class DebugClassPlugin(IPeppyPlugin):
    """Plugin to show all classes capable of debug printing.

    This plugin manages the debug list and the debug menu.  Note that
    if we're running in optimize mode (python -O), this plugin won't
    be active because it won't do anything.  Debug print statements
    are hidden behind asserts, and asserts are removed when running in
    optimize mode.
    """
    use_menu = False

    def getSidebars(self):
        # Don't show the sidebar in optimize mode (__debug == False)
        if __debug__:
            yield DebugClassList
        else:
            raise StopIteration

    def getActions(self):
        # Don't show menu if in optimize mode
        if self.use_menu and __debug__:
            yield DebugClass
        else:
            raise StopIteration
