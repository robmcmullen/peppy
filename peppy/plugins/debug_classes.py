# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Sidebar for debug printing.

Sidebar that shows classes that have debug printing capability.

FIXME: this doesn't yet update between frames, so items may be out of
sync if this is shown on two different frames.
"""

import os, gc

from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.sidebar import *

from wx.lib.pubsub import Publisher

USE_DEBUG_LEAK = False
if USE_DEBUG_LEAK:
    gc.enable()
    gc.set_debug(gc.DEBUG_LEAK)

class DebugGarbage(SelectAction):
    alias = "debug-gc"
    name = "Garbage Objects"
    tooltip = "Show uncollectable objects"
    default_menu = (("Tools/Debug", -1000), 500)
    key_bindings = {'emacs': "C-X C-D", }

    def action(self, index=-1, multiplier=1):
        assert self.dprint("id=%x name=%s index=%s" % (id(self),self.name,str(index)))
        # force collection
        print "\nGARBAGE:"
        gc.collect()

        print "\nGARBAGE OBJECTS:"
        for x in gc.garbage:
            s = str(x)
            if len(s) > 80: s = s[:80]
            print type(x),hex(id(x)),":", s
        print "--summary: %d objects" % (len(gc.garbage))


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
    default_menu = (("Tools/Debug", -1000), 500)
    categories = False
    inline = True

    # File list is shared among all windows
    itemlist = []
    
    # Initial debug activation from the command line
    initial_activation = []

    @staticmethod
    def append(kls, name=None):
        """Add a class to the list of entries

        @param kls: class object for debuggable class
        @param name: (optional) name of class
        """
        if not name:
            name = kls.__name__
        if name in DebugClass.initial_activation:
            dprint("Activating %s for debug printing" % name)
            kls.debuglevel = 1
        DebugClass.itemlist.append({'item':kls, 'name':name, 'icon':None, 'checked':kls.debuglevel>0})

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

    @staticmethod
    def setInitialActivation(names):
        """Find the class object from the text name"""
        active = {}
        for name in names:
            active[name] = True
        DebugClass.initial_activation = active
        
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
    default_classprefs = (
        BoolParam('use_menu', False, 'Place the debug class list in the menu bar'),
    )

    def addCommandLineOptions(self, parser):
        parser.add_option("--dbg", action="append",
                          dest="debug_classes", default=[])

    def processCommandLineOptions(self, options):
        if options.debug_classes:
            dprint(options.debug_classes)
            DebugClass.setInitialActivation(options.debug_classes)
    
    def getSidebars(self):
        # Don't show the sidebar in optimize mode (__debug == False)
        if __debug__:
            yield DebugClassList
        else:
            raise StopIteration

    def getActions(self):
        # Don't show menu if in optimize mode
        if __debug__:
            yield DebugGarbage
            if self.classprefs.use_menu:
                yield DebugClass
        else:
            raise StopIteration
