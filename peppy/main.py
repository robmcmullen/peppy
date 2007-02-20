#!/usr/bin/env python
"""
Main application program.
"""

import os,os.path,sys,re,time,commands,glob,random

import wx

from menu import *
from buffers import *
from debug import *
from trac.core import *
from about import *


class NewTab(SelectAction):
    name = "New &Tab"
    tooltip = "Open a new Tab"
    icon = wx.ART_FILE_OPEN

    def action(self, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.open("about:blank")

class New(SelectAction):
    name = "&New File..."
    tooltip = "New file"
    icon = "icons/page.png"

    def action(self, pos=-1):
        self.frame.open("about:untitled")
        
class OpenFile(SelectAction):
    name = "&Open File..."
    tooltip = "Open a file"
    icon = "icons/folder_page.png"
    keyboard = "C-X C-F"

    def action(self, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))

        wildcard="*"
        cwd=os.getcwd()
        dlg = wx.FileDialog(
            self.frame, message="Open File", defaultDir=cwd, 
            defaultFile="", wildcard=wildcard, style=wx.OPEN)

        # Show the dialog and retrieve the user response. If it is the
        # OK response, process the data.
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            paths = dlg.GetPaths()

            for path in paths:
                self.dprint("open file %s:" % path)
                # Force the loader to use the file: protocol
                self.frame.open("file:%s" % path)

        # Destroy the dialog. Don't do this until you are done with it!
        # BAD things can happen otherwise!
        dlg.Destroy()

class OpenURL(SelectAction):
    name = "Open URL..."
    tooltip = "Open a file through a URL"
    icon = "icons/folder_page.png"
    keyboard = "C-X C-A"

    def action(self, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))

        wildcard="*"
        cwd=os.getcwd()
        dlg = wx.TextEntryDialog(
            self.frame, message="Open URL", defaultValue="",
            style=wx.OK|wx.CANCEL)

        # Show the dialog and retrieve the user response. If it is the
        # OK response, process the data.
        if dlg.ShowModal() == wx.ID_OK:
            # This returns a Python list of files that were selected.
            url = dlg.GetValue()

            self.dprint("open url %s:" % url)
            self.frame.open(url)

        # Destroy the dialog. Don't do this until you are done with it!
        # BAD things can happen otherwise!
        dlg.Destroy()


class Exit(SelectAction):
    name = "E&xit"
    tooltip = "Quit the program."
    keyboard = "C-X C-C"
    
    def action(self, pos=-1):
        self.frame.app.quit()

class Close(SelectAction):
    name = "&Close"
    tooltip = "Close current file"
    icon = "icons/cross.png"

    def isEnabled(self):
        return self.frame.isOpen()

    def action(self, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.close()

class Save(SelectAction):
    name = "&Save..."
    tooltip = "Save the current file"
    icon = "icons/disk.png"
    keyboard = "C-X C-S"

    def isEnabled(self):
        mode=self.frame.getActiveMajorMode()
        if mode:
            if mode.buffer.readonly:
                return False
            return True
        return False

    def action(self, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        self.frame.save()

class SaveAs(SelectAction):
    name = "Save &As..."
    tooltip = "Save as a new file"
    icon = "icons/disk_edit.png"
    keyboard = "C-X C-W"
    
    def isEnabled(self):
        return self.frame.isOpen()

    def action(self, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))

        mode=self.frame.getActiveMajorMode()
        paths=None
        if mode and mode.buffer:
            saveas=mode.buffer.getFilename()

            # Do this in a loop so that the user can get a chance to
            # change the filename if the specified file exists.
            while True:
                # If we come through this loop again, saveas will hold
                # a complete pathname.  Shorten it.
                saveas=os.path.basename(saveas)
                
                wildcard="*.*"
                cwd=os.getcwd()
                dlg = wx.FileDialog(
                    self.frame, message="Save File", defaultDir=cwd, 
                    defaultFile=saveas, wildcard=wildcard, style=wx.SAVE)

                retval=dlg.ShowModal()
                if retval==wx.ID_OK:
                    # This returns a Python list of files that were selected.
                    paths = dlg.GetPaths()
                dlg.Destroy()

                if retval!=wx.ID_OK:
                    break
                elif len(paths)==1:
                    saveas=paths[0]
                    self.dprint("save file %s:" % saveas)

                    # If new filename exists, make user confirm to
                    # overwrite
                    if os.path.exists(saveas):
                        dlg = wx.MessageDialog(self.frame, "%s\n\nexists.  Overwrite?" % saveas, "Overwrite?", wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION )
                        retval=dlg.ShowModal()
                        dlg.Destroy()
                    else:
                        retval=wx.ID_YES
                    if retval==wx.ID_YES:
                        mode.buffer.save(saveas)
                        break
                elif paths!=None:
                    raise IndexError("BUG: probably shouldn't happen: len(paths)!=1 (%s)" % str(paths))



class Undo(SelectAction):
    name = "Undo"
    tooltip = "Undo"
    icon = "icons/arrow_turn_left.png"
    keyboard = "C-/"
    
    def isEnabled(self):
        viewer=self.frame.getActiveMajorMode()
        if viewer: return viewer.stc.CanUndo()
        return False

    def action(self, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        viewer=self.frame.getActiveMajorMode()
        if viewer: return viewer.stc.Undo()


class Redo(SelectAction):
    name = "Redo"
    tooltip = "Redo"
    icon = "icons/arrow_turn_right.png"
    keyboard = "C-S-/"
    
    def isEnabled(self):
        viewer=self.frame.getActiveMajorMode()
        if viewer: return viewer.stc.CanRedo()
        return False

    def action(self, pos=-1):
        self.dprint("id=%x name=%s pos=%s" % (id(self),self.name,str(pos)))
        viewer=self.frame.getActiveMajorMode()
        if viewer: return viewer.stc.Redo()

class Cut(SelectAction):
    name = "Cut"
    tooltip = "Cut"
    icon = "icons/cut.png"

    def isEnabled(self):
        viewer=self.frame.getActiveMajorMode()
        if viewer: return viewer.stc.CanCut()
        return False

    def action(self, pos=-1):
        viewer=self.frame.getActiveMajorMode()
        if viewer:
            dprint("rectangle=%s" % viewer.stc.SelectionIsRectangle())
            return viewer.stc.Cut()

class Copy(SelectAction):
    name = "Copy"
    tooltip = "Copy"
    icon = "icons/page_copy.png"

    def isEnabled(self):
        viewer=self.frame.getActiveMajorMode()
        if viewer: return viewer.stc.CanCopy()
        return False

    def action(self, pos=-1):
        viewer=self.frame.getActiveMajorMode()
        if viewer:
            dprint("rectangle=%s" % viewer.stc.SelectionIsRectangle())
            return viewer.stc.Copy()

class Paste(SelectAction):
    name = "Paste"
    tooltip = "Paste"
    icon = "icons/paste_plain.png"

    def isEnabled(self):
        viewer=self.frame.getActiveMajorMode()
        self.dprint("mode=%s stc=%s paste=%s" % (viewer,viewer.stc,viewer.stc.CanPaste()))
        if viewer: return viewer.stc.CanPaste()
        return False

    def action(self, pos=-1):
        viewer=self.frame.getActiveMajorMode()
        if viewer:
            dprint("rectangle=%s" % viewer.stc.SelectionIsRectangle())
            return viewer.stc.Paste()

class Preferences(SelectAction):
    name = "Preferences..."
    tooltip = "Preferences, settings, and configurations..."
    icon = "icons/wrench.png"

    def isEnabled(self):
        return False

    def action(self, pos=-1):
        pass
    

class GlobalMenu(Component):
    """Trac plugin that provides the global menubar and toolbar.

    This provides the base menubar and toolbar that all major modes
    build upon.
    """
    implements(IMenuItemProvider)
    implements(IToolBarItemProvider)

    default_menu=((None,Menu("File").first()),
                  ("File",MenuItem(New).first()),
                  ("File",MenuItem(OpenFile).after("&New File...")),
                  ("File",MenuItem(OpenURL).after("&Open File...")),
                  ("File",Separator("opensep").after("Open URL...")),
                  ("File",MenuItem(Save).after("opensep")),
                  ("File",MenuItem(SaveAs).after("opensep")),
                  ("File",MenuItem(Close).after("opensep")),
                  ("File",Separator("quit").after("opensep")),
                  ("File",MenuItem(Exit).last()),
                  (None,Menu("Edit").after("File").first()),
                  ("Edit",MenuItem(Undo).first()),
                  ("Edit",MenuItem(Redo).first()),
                  ("Edit",Separator("cut").first()),
                  ("Edit",MenuItem(Cut).first()),
                  ("Edit",MenuItem(Copy).first()),
                  ("Edit",MenuItem(Paste).first()),
                  ("Edit",Separator("paste").first()),
                  ("Edit",Separator("lastsep").last()),
                  ("Edit",MenuItem(Preferences).after("lastsep")),
                  (None,Menu("View").before("Major Mode")),
                  ("View",MenuItem(NewTab).first()),
                  ("View",Separator("tabs").first()),
                  ("View",MenuItem(NewFrame).first()),
                  ("View",MenuItem(DeleteFrame).first()),
                  ("View",Separator("begin").first()),
                  ("View",Separator("plugins").after("begin")),
                  ("View",MenuItem(FramePluginShow).after("plugins")),
                  ("View",MenuItem(FrameList).last()),
                  ("View",Separator("end").last()),
                  (None,Menu("Buffers").before("Major Mode")),
                  ("Buffers",MenuItem(BufferList).first()),
                  (None,Menu("Major Mode").hide()),
                  (None,Menu("Minor Mode").hide().after("Major Mode")),
                  (None,Menu("Help").last()),
                  )
    def getMenuItems(self):
        for menu,item in self.default_menu:
            yield (None,menu,item)

    default_tools=((None,Menu("File").first()),
                  ("File",MenuItem(New).first()),
                  ("File",MenuItem(OpenFile).first()),
                  ("File",Separator("save").first()),
                  ("File",MenuItem(Save).first()),
                  ("File",MenuItem(SaveAs).first()),
                  ("File",MenuItem(Close).first()),
                  (None,Menu("Edit").after("File").first()),
                  ("Edit",MenuItem(Cut).first()),
                  ("Edit",MenuItem(Copy).first()),
                  ("Edit",MenuItem(Paste).first()),
                  ("Edit",Separator("cut").first()),
                  ("Edit",MenuItem(Undo).first()),
                  ("Edit",MenuItem(Redo).first()),
                  )
    def getToolBarItems(self):
        for menu,item in self.default_tools:
            yield (None,menu,item)



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
        
    def getHash(self):
        return len(DebugClass.itemlist)

    def getItems(self):
        return [item['name'] for item in DebugClass.itemlist]

    def isChecked(self, index):
        return DebugClass.itemlist[index]['checked']

    def action(self, index=-1):
        """
        Turn on or off the debug logging for the selected class
        """
        self.dprint("DebugClass.action: id(self)=%x name=%s index=%d id(itemlist)=%x" % (id(self),self.name,index,id(DebugClass.itemlist)))
        kls=DebugClass.itemlist[index]['item']
        DebugClass.itemlist[index]['checked']=not DebugClass.itemlist[index]['checked']
        if DebugClass.itemlist[index]['checked']:
            kls.debuglevel=1
        else:
            kls.debuglevel=0
        self.dprint("class=%s debuglevel=%d" % (kls,kls.debuglevel))

class DebugGlobalActions(Component):
    implements(IMenuItemProvider)

    default_menu=((None,Menu("Debug").after("Minor Mode").before("Help")),
                  ("Debug",MenuItem(DebugClass).first()),
                  )
    def getMenuItems(self):
        for menu,item in self.default_menu:
            yield (None,menu,item)



class Peppy(BufferApp, ClassSettingsMixin):
    """Main application object.

    This handles the initialization of the debug parameters for
    objects and loads the configuration file, plugins, configures the
    initial keyboard mapping, and other lower level initialization
    from the BufferApp superclass.
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
    
    initialconfig={'BufferFrame':{'width':800,
                                  'height':600,
                                  'plugins':'filebrowser',
                                  },
                   'Peppy':{'plugins':'peppy.plugins.python_mode,peppy.plugins.hexedit_mode,peppy.plugins.shell_mode,peppy.plugins.image_mode,peppy.plugins.openrecent,peppy.plugins.pype_compat,peppy.plugins.pype_funclist_minormode,peppy.plugins.pype_filebrowser,peppy.plugins.sizereporter_minormode,peppy.plugins.chatbots,peppy.plugins.graphviz_mode,peppy.plugins.boa_stcstyleeditor,peppy.plugins.makefile_mode,peppy.plugins.lexerdebug_mode',
                            'recentfiles':'recentfiles.txt',
                            },
                   }
    
    def OnInit(self):
        """Main application initialization.

        Called by the wx framework and used instead of the __init__
        method in a wx application.
        """
        if self.verbose:
            self.setVerbosity()
        BufferApp.OnInit(self)

        ClassSettingsMixin.__init__(self)
        self.setConfigDir("peppy")
        self.setInitialConfig(self.initialconfig)
        self.loadConfig("peppy.cfg")

        # set verbosity on any new plugins that may have been loaded
        # and set up the debug menu
        self.setVerbosity(menu=DebugClass,reset=self.verbose)

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

    def loadConfigPostHook(self):
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
        modes in the plugins subdirectory.  An even better way
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
        self.saveConfig("peppy.cfg")
        return True


def run(options={},args=None):
    """Start an instance of the application.

    @param options: OptionParser option class
    @param args: command line argument list
    """
    
    if options.logfile:
        debuglog(options.logfile)
    Peppy.verbose=options.verbose
    app=Peppy(redirect=False)
    frame=BufferFrame(app)
    frame.Show(True)
    bad=[]
    if args:
        for filename in args:
            try:
                frame.open(filename)
            except IOError:
                bad.append(filename)

    if len(BufferList.storage)==0:
        frame.titleBuffer()
        
    if len(bad)>0:
        frame.SetStatusText("Failed loading %s" % ", ".join([f for f in bad]))
    
    app.MainLoop()

def main():
    """Main entry point for editor.

    This is called from a script outside the package, parses the
    command line, and starts up a new wx.App.
    """
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



if __name__ == "__main__":
    main()
