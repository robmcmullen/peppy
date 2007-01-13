#!/usr/bin/env python

"""
peppy - (ap)Proximated (X)Emacs Powered by Python.

This is a wxPython/Scintilla-based editor written in and extensible
through Python. It attempts to provide an XEmacs-like multi-window,
multi-tabbed interface.

Plugins
=======

There are currently two plugin types that can be used to extend peppy:
L{ProtocolPlugin<plugin.ProtocolPlugin>}s and
L{ViewPlugin<plugin.ViewPlugin>}s.

@author: $author
@version: $version
"""

import os,os.path,sys,re,time,commands,glob,random

import wx

from menudev import *
from buffers import *
from iofilter import SetAbout
from debug import *

# setup.py requires that these be defined, and the OnceAndOnlyOnce
# principle is used here.  This is the only place where these values
# are defined in the source distribution, and everything else that
# needs this should grab it from here.
__version__ = "svn-devel"
__author__ = "Rob McMullen"
__author_email__ = "robm@users.sourceforge.net"
__url__ = "http://www.flipturn.org/peppy/"
__download_url__ = "http://www.flipturn.org/peppy/archive/"
__description__ = "(ap)Proximated (X)Emacs Powered by Python"
__keywords__ = "text editor, wxwindows, scintilla"
__license__ = "GPL"

gpl_text="""
This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program; if not, write to the Free Software Foundation, Inc.,
51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

SetAbout('title.txt',"%s %s\n%s\n\nCopyright (c) 2006 %s (%s)" % ("peppy",__version__,__description__,__author__,__author_email__))
SetAbout('alpha','')
SetAbout('bravo','')
SetAbout('blank','')

class NewTab(FrameAction):
    name = "New &Tab"
    tooltip = "Open a new Tab"
    icon = wx.ART_FILE_OPEN

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.open("about:blank")

class New(FrameAction):
    name = "&New File..."
    tooltip = "New file"
    icon = "icons/page.png"


class OpenFile(FrameAction):
    name = "&Open File..."
    tooltip = "Open a file"
    icon = "icons/folder_page.png"
    keyboard = "C-X C-F"

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.openFileDialog()

class OpenAlpha(FrameAction):
    name = "&Open Alpha..."
    tooltip = "Open an Alpha object"
    icon = wx.ART_FILE_OPEN

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.open("about:alpha")

class OpenBravo(FrameAction):
    name = "&Open Bravo..."
    tooltip = "Open a Bravo object"
    icon = wx.ART_FILE_OPEN

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.open("about:bravo")

class Close(FrameAction):
    name = "&Close"
    tooltip = "Close current file"
    icon = "icons/cross.png"

    def isEnabled(self, state=None):
        return self.frame.isOpen()

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.close()

class Save(FrameAction):
    name = "&Save..."
    tooltip = "Save the current file"
    icon = "icons/disk.png"
    keyboard = "C-X C-S"

    def isEnabled(self, state=None):
        return self.frame.isOpen()

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.save()

class SaveAs(FrameAction):
    name = "Save &As..."
    tooltip = "Save as a new file"
    icon = "icons/disk_edit.png"
    keyboard = "C-X C-W"
    
    def isEnabled(self, state=None):
        return self.frame.isOpen()

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.saveFileDialog()


class Undo(FrameAction):
    name = "Undo"
    tooltip = "Undo"
    icon = "icons/arrow_turn_left.png"
    keyboard = "C-/"
    
    def __init__(self, frame):
        FrameAction.__init__(self, frame)

    def isEnabled(self, state=None):
        viewer=self.frame.getCurrentViewer()
        if viewer: return viewer.stc.CanUndo()
        return False

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        viewer=self.frame.getCurrentViewer()
        if viewer: return viewer.stc.Undo()


class Redo(FrameAction):
    name = "Redo"
    tooltip = "Redo"
    icon = "icons/arrow_turn_right.png"
    keyboard = "C-S-/"
    
    def __init__(self, frame):
        FrameAction.__init__(self, frame)
        
    def isEnabled(self, state=None):
        viewer=self.frame.getCurrentViewer()
        if viewer: return viewer.stc.CanRedo()
        return False

    def action(self, state=None, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        viewer=self.frame.getCurrentViewer()
        if viewer: return viewer.stc.Redo()



class Cut(FrameAction):
    name = "Cut"
    tooltip = "Cut"
    icon = "icons/cut.png"
    
    def __init__(self, frame):
        FrameAction.__init__(self, frame)

class Copy(FrameAction):
    name = "Copy"
    tooltip = "Copy"
    icon = "icons/page_copy.png"
    
    def __init__(self, frame):
        FrameAction.__init__(self, frame)

class Paste(FrameAction):
    name = "Paste"
    tooltip = "Paste"
    icon = "icons/paste_plain.png"
    
    def __init__(self, frame):
        FrameAction.__init__(self, frame)

   
    
class HelpAbout(FrameAction):
    name = "&About..."
    tooltip = "About this program"

    about = "Test program"
    title = "Test program title"
    
    def run(self, state=None, pos=None):
        from wx.lib.wordwrap import wordwrap
        
        info = wx.AboutDialogInfo()
        info.Name = "peppy"
        info.Version = __version__
        info.Copyright = "Copyright (c) 2006 %s (%s)" % (__author__,__author_email__)
        info.Description = wordwrap(
            "This program is a wxPython/Scintilla-based editor written "
            "in and extensible through Python.  Its aim to provide "
            "the user with an XEmacs-like multi-window, multi-tabbed "
            "interface while providing the developer easy ways to "
            "extend the capabilities of the editor using Python "
            "instead of Emacs lisp.\n",
            350, wx.ClientDC(self.frame))
        info.WebSite = (__url__, "peppy home page")
        info.Developers = [ "Rob McMullen",
                            "",
                            "Contributions by:",
                            "Robin Dunn (for wxPython)",
                            "Josiah Carlson (for ideas & code from PyPE)",
                            "Stani Michiels (for ideas & code from SPE)",
                            "Mark James (for the silk icon library)"]

        info.License = wordwrap(gpl_text, 500, wx.ClientDC(self.frame))

        # Then we call wx.AboutBox giving it that info object
        wx.AboutBox(info)





class AlphaView(View):
    pluginkey = 'alpha'
    keyword='Alpha'
    icon = 'icons/world.png'
    regex = "alpha"
    defaultsettings={
        'menu_actions':[
            [[('&Alpha',0.25)],TestRadioList,0.0],
            FrameToggleList,
            ]
        }

    def createEditWindow(self,parent):
        win=wx.Window(parent, -1)
        wx.StaticText(win, -1, self.buffer.name, (45, 45))
        return win


class BravoView(View):
    pluginkey = 'bravo'
    keyword='Bravo'
    icon='icons/bug_add.png'
    regex="bravo"

    def createEditWindow(self,parent):
        win=wx.Window(parent, -1)
        wx.StaticText(win, -1, self.buffer.name, (100,100))
        return win


class BlankView(View):
    pluginkey = 'blank'
    keyword='Blank'
    icon='icons/application.png'
    regex="about:blank"

    def createEditWindow(self,parent):
        win=wx.Window(parent, -1)
        text=self.buffer.stc.GetText()
        wx.StaticText(win, -1, text, (10,10))
        return win

class TitleView(BlankView):
    pluginkey = 'title'
    keyword='Title'
    regex="about:title.txt"
    temporary=True




class DebugClass(FrameToggleList):
    """
    A multi-entry menu list that allows individual toggling of debug
    printing for classes.

    All frames will share the same list, which makes sense since the
    debugging is controlled by class attributes.
    """
    debuglevel=0
    
    name = "DebugClassMenu"
    empty = "< list of classes >"
    tooltip = "Turn on/off debugging for listed classes"
    categories = False

    # File list is shared among all windows
    itemlist = []
    
    def __init__(self, frame):
        FrameToggleList.__init__(self, frame)
        self.itemlist = DebugClass.itemlist
        
    def append(self,kls,text=None):
        """
        Add a class to the list of entries

        @param kls: class
        @type kls: class
        @param text: (optional) name of class
        @type text: text
        """
        if not text:
            text=kls.__name__
        self.itemlist.append({'item':kls,'name':text,'icon':None,'checked':kls.debuglevel>0})
        
    def action(self, state=None, pos=-1):
        """
        Turn on or off the debug logging for the selected class
        """
        self.dprint("DebugClass.action: id(self)=%x name=%s pos=%d id(itemlist)=%x" % (id(self),self.name,pos,id(self.itemlist)))
        kls=self.itemlist[pos]['item']
        if state:
            kls.debuglevel=1
        else:
            kls.debuglevel=0
        self.dprint("class=%s debuglevel=%d" % (kls,kls.debuglevel))




class Peppy(BufferApp,ClassSettingsMixin):
    """
    Main application object.  This handles the initialization of the
    debug parameters for objects and loads the configuration file,
    plugins, configures the initial keyboard mapping, and other lower
    level initialization from the BufferApp superclass.
    """
    debuglevel=0
    verbose=0

    ##
    # This mapping controls the verbosity level required for debug
    # printing to be shown from the class names that match these
    # regular expressions.  Everything not listed here will get turned
    # on with a verbosity level of 1.
    verboselevel={'.*Frame':2,
                  'ActionMenu.*':4,
                  'ActionTool.*':4,
                  '.*Filter':3,
                  }
    
    initialconfig={'MenuFrame':{'width':600,
                                'height':500,
                                },
                   'Peppy':{'plugins':'major_modes.hexedit,major_modes.python,major_modes.shell,plugins.chatbots',
                            },
                   'View':{'linenumbers':True,
                           'wordwrap':False,
                           },
                   'PythonView':{'wordwrap':True,
                                 },
                   }
    
    def OnInit(self):
        """
        Main application initialization.  Called by the wx framework.
        """
        self.debugmenu=DebugClass(None)
        
        if self.verbose:
            self.setVerbosity()
        BufferApp.OnInit(self)

        ClassSettingsMixin.__init__(self)
        self.setConfigDir("peppy")
        self.setInitialConfig(self.initialconfig)
        self.loadConfig("peppy.cfg")
        
        self.addGlobalMenu(global_menu_actions)
        self.addGlobalToolbar(global_toolbar_actions)
        self.addGlobalKeys(global_keyboard_actions)

        self.parseConfig()

        # set verbosity on any new plugins that may have been loaded
        # and set up the debug menu
        self.setVerbosity(menu=self.debugmenu,reset=self.verbose)

        return True

    def getSubclasses(self,parent=debugmixin,subclassof=None):
        """
        Recursive call to get all classes that have a specified class
        in their ancestry.  The call to __subclasses__ only finds the
        direct, child subclasses of an object, so to find
        grandchildren and objects further down the tree, we have to go
        recursively down each subclasses hierarchy to see if the
        subclasses are of the type we want.

        @param parent: class used to find subclasses
        @type parent: class
        @param subclassof: class used to verify type during recursive calls
        @type subclassof: class
        @returns: list of classes
        """
        if subclassof is None:
            subclassof=parent
        subclasses=[]

        # this call only returns immediate (child) subclasses, not
        # grandchild subclasses where there is an intermediate class
        # between the two.
        classes=parent.__subclasses__()
        for kls in classes:
            if issubclass(kls,subclassof):
                subclasses.append(kls)
            # for each subclass, recurse through its subclasses to
            # make sure we're not missing any descendants.
            subs=self.getSubclasses(parent=kls)
            if len(subs)>0:
                subclasses.extend(subs)
        return subclasses

    def setVerboseLevel(self,kls):
        """
        Set the class's debuglevel if the verbosity level is high
        enough.  Matches the class name against list of regular
        expressions in verboselevel to see if extra verbosity is
        needed to turn on debugging output for that class.

        @param kls: class
        @param type: subclass of debugmixin
        """
        level=self.verbose
        for regex,lev in self.verboselevel.iteritems():
            match=re.match(regex,kls.__name__)
            if match:
                if self.verbose<self.verboselevel[regex]:
                    level=0
                break
        kls.debuglevel=level

    def setVerbosity(self,menu=None,reset=False):
        """
        Find all classes that use the debugmixin and set the logging
        level to the value of verbose.

        @param menu: if set, the value of the menu to populate
        @type menu: DebugClass instance, or None
        """
        debuggable=self.getSubclasses()
        debuggable.sort(key=lambda s:s.__name__)
        for kls in debuggable:
            if reset:
                self.setVerboseLevel(kls)
            self.dprint("%s: %d (%s)" % (kls.__name__,kls.debuglevel,kls))
            if menu:
                menu.append(kls)
        #sys.exit()

    def parseConfig(self):
        """
        Main driver for any functions that need to look in the config file.
        """
        self.parseConfigMajorModes()
        self.parseConfigPlugins()
##        if cfg.has_section('debug'):
##            self.parseConfigDebug('debug',cfg)

    def parseConfigMajorModes(self):
        """
        Placeholder for future method to automatically import major
        modes in the major_modes subdirectory.  An even better way
        would be to import the modules only on request when they are
        first needed.
        """
        pass

    def parseConfigPlugins(self):
        """
        Load plugins specified in the config file.
        """
        mods=self.settings.plugins
        self.dprint(mods)
        if mods is not None:
            self.loadPlugins(mods)


    def quitHook(self):
        GlobalSettings.saveConfig("peppy.cfg")
        return True


def run(options={},args=None):
    if options.logfile:
        debuglog(options.logfile)
    Peppy.verbose=options.verbose
    app=Peppy()
    frame=BufferFrame(app)
    frame.Show(True)
    if args:
        for filename in args:
            frame.open(filename)
        
    app.MainLoop()


global_menu_actions=[
    [[('&File',0.0)],OpenFile,0.0],
    [[('&File',0.0),('Open Recent',0.1)],OpenRecent,0.1],
    [[('&File',0.0)],None,0.2], # separator
    [Save,0.8],
    SaveAs,
    Close,
    None, # separator
    [Quit,1.0],
    [[('&Edit',0.1)],Undo,0.1],
    Redo,
    None,
    Cut,
    Copy,
    Paste,
    [[('&View',0.2)],NewTab,0.0],
    [NewWindow,0.1],
    DeleteWindow,
    None,
    [FrameList,0.2],
    None,
    [ShowToolbar,0.3],
    [[('&Buffers',0.3)],BufferList,0.0],
    [[('&Test',1.0)],OpenAlpha,0.1],
    OpenBravo,
    [None,0.2], # separator
    [[('&Debug',1.0)],DebugClass,0.99],
    [[('&Help',1.0)],HelpAbout,1.0],
]

global_toolbar_actions=[
    # toolbar plugins here...
    [New,0.05],
    OpenFile,
    None,
#    [OpenAlpha,0.1],
#    [OpenBravo,
    [Save,0.2],
    SaveAs,
    Close,
    None,
    Cut,
    Copy,
    Paste,
    None,
    Undo,
    Redo,
    None,
    ]

global_keyboard_actions=[]


class AboutPlugin(ViewPluginBase):
    implements(ViewPlugin)

    def scanFilename(self,filename):
        if filename=='about:alpha':
            return ViewMatch(AlphaView,exact=True)
        elif filename=='about:bravo':
            return ViewMatch(BravoView,exact=True)
        elif filename=='about:title.txt':
            return ViewMatch(TitleView,exact=True)
        elif filename=='about:blank':
            return ViewMatch(BlankView,exact=True)
        else:
            return None




if __name__ == "__main__":
    from optparse import OptionParser

    usage="usage: %prog file [files...]"
    parser=OptionParser(usage=usage)
    parser.add_option("-p", action="store_true", dest="profile", default=False)
    parser.add_option("-v", action="count", dest="verbose", default=0)
    parser.add_option("-l", action="store", dest="logfile", default=None)
    (options, args) = parser.parse_args()
    #print options

    if options.profile:
        import profile
        profile.run('run()','profile.out')
    else:
        run(options,args)

