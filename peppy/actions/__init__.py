# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""User interface elements (keyboard and GUI)

Actions represent individual commands that can be initiated by the user.
The same action is used to represent the keyboard, menu and toolbar command
because it doesn't matter how the action is called -- if it's the same action,
it's the same class.
    
If an action should behave differently when called from a different user input
method, it should be a different subclass.

An action is represented by a subclass of L{SelectAction}.  The menu system
calls the method L{SelectAction.action} when the action is invoked by
the user.  SelectAction represents a simple menu item, toolbar button, or
keyboard command.  There are subclasses of SelectAction to provide other
user interface elements: L{ToggleAction}, L{RadioAction}, L{ListAction} and
L{ToggleListAction}.

There are also mixins and subclasses available that include some boilerplate
code in order to provide more specific support for types of actions.  For
instance, there is a L{RegionMutateAction} that handles the details of getting
the selection from the STC and provides a single method that the subclass can
override to change the text.  See L{peppy.actions.base} for more convenience
classes and mixins.
"""

from peppy.debug import *
from peppy.lib.wxemacskeybindings import *
from peppy.lib.iconstorage import *


class ActionNeedsFocusException(Exception):
    """If the action needs to be focused to process a keystroke and it receives
    the keystroke while not focused, raise this exception to allow the
    keystroke to propagate to other controls.
    
    For an example, see L{ElectricReturn}, which needs to raise this exception
    when not focused otherwise returns are not processed in L{FindBar}
    
    In general, this is only needed when special keys like Return and Tab are
    bound to actions -- most of the other times, you'll want the action to be
    performed regardless of the focus state.
    """
    pass


class SelectAction(debugmixin):
    """Display a normal menu item, toolbar button, or simple keystroke command.
    
    SelectAction is also the base class of any action (menu item, toolbar item,
    or keyboard command).
    
    An important characteristic of the peppy menu system is that persistent
    data should be stored extrinsically to the action.  Action instances are
    created and destroyed continually as the dynamic menu bar is updated when
    the user changes tabs.  Any instance level variables will be lost when the
    user switches major modes.  Instead of storing information in the action
    itself, reference the information in some other place that is persistent:
    in the major mode instance that is associated with the action, in the
    frame, or in class attributes of the action.
    
    The subclass should override the L{action} method to provide the
    implementation and L{isEnabled} to return the enable/disabled (i.e.  the
    grayed-out) state of the menu item or toolbar item.
    
    Menu items can also be updated dynamically by mixing in the
    L{OnDemandActionMixin} class, or using the L{OnDemandGlobalListAction}
    class.
    """
    #: This is the name of the menu entry as it appears in the menu bar. i18n processing happens within the menu system, so no need to wrap this string in a call to the _ function
    name = None
    
    #: This alias holds an emacs style name that is used during M-X processing. If you don't want this action to have an emacs style name, don't include this or set it equal to None
    alias = ""
    
    #: Tooltip that is displayed when the mouse is hovering over the menu entry.  If the tooltip is None, the tooltip is taken from the first line of the docstring, if it exists.
    tooltip = None
    
    #: The default menu location is specified here as a tuple containing the menu path (separated by / characters) and a number between 1 and 1000 representing the position within the menu.  A negative number means that a separator should appear before the item
    default_menu = ()
    
    #: If there is an icon associated with this action, name it here.  Icons are referred to by path name relative to the peppy directory.  A toolbar entry will be automatically created if the icon is specified here, unless you specify default_toolbar = False
    icon = None
    
    #: Toolbar item will automatically be created unless this is False
    default_toolbar = True
    
    #: Map of platform to default keybinding.  This is used to assign the class attribute keyboard, which is the current keybinding.  Currently, the defined platforms are named "win", "mac", and "emacs".  A platform named 'default' may also be included that will be the default key unless overridden by a specific platform
    key_bindings = None
    
    #: True if the action should be focused to process a keystroke.  Finer-grained control can be obtained by checking some condition within the action method and raising the L{ActionNeedsFocusException}
    key_needs_focus = False
    
    #: Current keybinding of the action.  This is set by the keyboard configuration loader and shouldn't be modified directly.  Subclasses should leave this set to None.
    keyboard = None
    
    #: If this menu action has a stock wx id, such as wx.ID_ABOUT or wx.ID_PREFERENCES, add it here and the wx menu system can do some special things to it, like automatically give it the correct location on WXMAC.
    stock_id = None
    
    #: If the action doesn't use a stock id, it will automatically get assigned a global id here.  Note that if you are subclassing an action, you should explicitly assign a global id (or None) to your subclass's global_id attribute, otherwise the menu system will get confused and attempt to use the superclass's global_id
    global_id = None

    
    # The rest of these class attributes aren't for individual class
    # customization
    _use_accelerators = True
    _accelerator_text = None # This is not set by the user

    @classmethod
    def worksWithMajorMode(cls, mode):
        """Hook to restrict the action to only be displayed with a specific
        major mode
        
        This hook is called by the menu creation code to determine if the
        action should be displayed when showing the major mode's user interface.
        
        @param mode: the major mode instance
        
        @returns: True if the action is allowed to be associated with the major
        mode
        """
        return True
    
    @classmethod
    def getHelp(cls):
        #dprint(dir(cls))
        help = u"\n\n'%s' is an action from module %s\nBound to keystrokes: %s\nAlias: %s\nDocumentation: %s" % (cls.__name__, cls.__module__, cls.keyboard, cls.alias, cls.__doc__)
        return help
    
    def __init__(self, frame, menu=None, toolbar=None):
        self.widget=None
        self.tool=None
        if self.global_id is None:
            if self.stock_id is not None:
                self.__class__.global_id = self.stock_id
            else:
                self.__class__.global_id = wx.NewId()

        # Each action is always associated with a particular frame and
        # major mode
        self.frame = frame
        self.mode = frame.getActiveMajorMode()
##        if self.mode:
##            dprint("%s %s %s" % (self.mode.keyword, menu, toolbar))
##        else:
##            dprint("%s is None! %s %s" % (self.mode, menu, toolbar))

        self.initPreHook()
        
        if menu is not None:
            self.insertIntoMenu(menu)
        if toolbar is not None:
            self.insertIntoToolbar(toolbar)

        self.initPostHook()

#    def __del__(self):
#        self.dprint("DELETING action %s" % self.name)

    def initPreHook(self):
        pass

    def initPostHook(self):
        pass
    
    def getSubIds(self):
        return []

    @classmethod
    def setAcceleratorText(cls, force_emacs=False):
        if cls.keyboard:
            keystrokes = KeyMap.split(cls.keyboard)
            if len(keystrokes) == 1 and (cls.stock_id is not None or not force_emacs):
                # if it has a stock id, always force it to use the our
                # accelerator because wxWidgets will put one there anyway and
                # we need to overwrite it with our definition
                cls._accelerator_text = u"\t%s" % KeyMap.nonEmacsName(keystrokes[0])
            else:
                cls._accelerator_text = u"    %s" % cls.keyboard
                if cls.stock_id is not None and (cls.global_id is None or cls.global_id == cls.stock_id):
                    # Can't use a stock id if we're also using emacs
                    # keybindings, because the stock id injects a one
                    # keystroke accelerator that we can't override unless we
                    # also use a one keystroke accelerator.
                    cls.global_id = wx.NewId()
                        
            #dprint("%s %s %s" % (cls.__name__, str(keystrokes), cls._accelerator_text))
            return len(keystrokes)
        else:
            cls._accelerator_text = ""
        return 0
    
    def getDefaultMenuItemName(self):
        if self._use_accelerators and self.keyboard:
            return u"%s%s" % (_(self.name), self._accelerator_text)
        elif self.name:
            return _(self.name)
        return _(self.__class__.__name__)

    def getDefaultTooltip(self, id=None, name=None):
        if id is None:
            id = self.global_id
        if name is None:
            name = self.name
        if self.tooltip is None:
            if self.__doc__ is not None:
                lines = self.__doc__.splitlines()
                self.__class__.tooltip = unicode(lines[0])
        return u"%s ('%s', id=%d)" % (_(self.tooltip), _(name), id)

    def insertIntoMenu(self, menu):
        self.widget = wx.MenuItem(menu, self.global_id, self.getDefaultMenuItemName(), self.getDefaultTooltip())
        #storeWeakref('menuitem', self.widget)
        if self.icon:
            bitmap = getIconBitmap(self.icon)
            self.widget.SetBitmap(bitmap)
        menu.AppendItem(self.widget)

    def insertIntoToolbar(self, toolbar):
        self.tool=toolbar
        help = _(self.name).replace('&','')
        toolbar.AddLabelTool(self.global_id, self.name, getIconBitmap(self.icon), shortHelp=help, longHelp=self.getDefaultTooltip())

    def action(self, index=-1, multiplier=1):
        """Override this to provide the functionality of the action.
        
        This method gets called when the user initiates the action, whether it
        be from the menu bar, toolbar, or keyboard.
        
        @param index: The index of the item in the list.  This is only useful
        for list or radio items.
        
        @param multiplier: the multiplier supplied by the keyboard handler.
        The keyboard handler allows for emacs-style repeat commands.  For
        some actions, it makes sense to allow repetition of the command.  For
        instance, in a command that uppercases words, the multiplier could be
        4, would mean that the next 4 words get uppercased.  The default is 1.
        """
        pass

    def __call__(self, evt, number=1):
        assert self.dprint("%s called by keybindings -- multiplier=%s" % (self, number))
        # Make sure that the action is enabled before allowing it to be called
        # using the keybinding
        if self.isEnabled():
            if self.key_needs_focus and self.mode.FindFocus() != self.mode:
                evt.Skip()
                return
            try:
                self.action(0, number)
            except ActionNeedsFocusException:
                evt.Skip()

    def showEnable(self):
        state = self.isEnabled()
        if self.widget is not None:
            assert self.dprint(u"menu item %s (widget id=%d) enabled=%s" % (self.name, self.global_id, state))
            self.widget.Enable(state)
        if self.tool is not None:
            assert self.dprint(u"menu item %s (widget id=%d) enabled=%s tool=%s" % (self.name, self.global_id, state, self.tool))
            self.tool.EnableTool(self.global_id, state)

    def isEnabled(self):
        """Override this to provide the enable/disable state of the item.
        
        The menu system will call this method before the menu is drawn (or
        periodically during idle time for toolbar items) to determine whether
        or not the item should be disabled (grayed out).
        
        Default is to always enable the item.
        """
        return True

class ToggleAction(SelectAction):
    """Display a toggle button or toolbar item.
    
    This is used to display a single toggle button that can be displayed in
    either a menu bar or a toolbar.
    
    The subclass should override the L{isChecked} method to return a boolean
    indicating whether or not to display a checkmark (for a menu item) or to
    display the button as toggled-on (for a toolbar).
    """
    def insertIntoMenu(self,menu):
        self.widget=menu.AppendCheckItem(self.global_id, _(self.name), self.getDefaultTooltip())
        #storeWeakref('menuitem', self.widget)

    def insertIntoToolbar(self,toolbar):
        self.tool=toolbar
        toolbar.AddCheckTool(self.global_id, getIconBitmap(self.icon), wx.NullBitmap, shortHelp=_(self.name), longHelp=self.getDefaultTooltip())
        
    def showEnable(self):
        SelectAction.showEnable(self)
        self.showCheck()
        
    def isChecked(self):
        raise NotImplementedError

    def showCheck(self):
        state = self.isChecked()
        if self.widget is not None:
            self.widget.Check(state)
        if self.tool is not None:
            #dprint("%s, %s, %s" % (self.tool, self.global_id, state))
            self.tool.ToggleTool(self.global_id, state)


class ListAction(SelectAction):
    """Display a list of items in a menu bar.
    
    This is used to display a list of items while only requiring a single
    action to display the entire list.
    
    The subclass should override the L{getItems} method to return the list of
    items to display.  These items should be strings.  Overriding L{isEnabled}
    will determine the enable/disable state for all of the items in the list.
    
    If the items change their text strings, you should add the
    L{OnDemandActionMixin} and override the L{getHash} method to indicate when
    the user interface should redraw the menu.
    """
    menumax = 30
    abbrev_width = 16
    inline = False
    
    #: Should the items in the list be localized?  Dynamically generated lists in general won't be, because they represent filenames -- if a filename happened to be named "File" or "Edit" or "Cut" or a common string, they would be transformed to the localized version when they shouldn't be if that's the actual filename.
    localize_items = False
    
    class IdCache(object):
        def __init__(self, first):
            self.first = first
            self.cache = [self.first]
            self.resetIndex()
            
        def resetIndex(self):
            self.index = 0
            
        def getNewId(self):
            if self.index >= len(self.cache):
                id = wx.NewId()
                self.cache.append(id)
            else:
                id = self.cache[self.index]
            self.index += 1
            return id

    def __init__(self, frame, menu=None, toolbar=None):
        # a record of all menu entries at the main level of the menu
        self.toplevel=[]

        # mapping of menu id to position in menu
        self.id2index={}

        # save the top menu
        self.menu=None

        SelectAction.__init__(self,frame,menu,toolbar)
        self.cache = self.IdCache(self.global_id)
    
    def getSubIds(self):
        ids = self.id2index.keys()
        ids.extend(self.toplevel)
        ids.sort()
        return ids
    
    def getIndexOfId(self, id):
        return self.id2index[id]
    
    def insertIntoMenu(self,menu,pos=None):
        self.cache.resetIndex()
        self.menu=menu

        # start off adding entries to the top level menu
        is_toplevel=True

        # Unless specified, add menu items to the end of the menu
        if pos is None:
            pos=menu.GetMenuItemCount()

        if not self.inline:
            # This is a named list, which means that all the items in
            # the list will be placed in a pop-right menu
            child=wx.Menu()
            
            # Inline list should always use a localized name for the pop-right
            # indicator
            self._insertMenu(menu, pos, child, _(self.name),True)
            self.topindex=pos
            pos=0
            menu=child
            is_toplevel=False
        else:
            self.topindex=pos
        
        self._insertItems(menu,pos,is_toplevel)

    def _insertItems(self,menu,pos,is_toplevel=False):
        items = self.getItems()
        
        self.count=0
        if self.menumax>0 and len(items)>self.menumax:
            for group in range(0,len(items),self.menumax):
                last=min(group+self.menumax,len(items))
                str1 = items[group].strip()[0:self.abbrev_width]
                str2 = items[last-1].strip()[0:self.abbrev_width]
                groupname="%s ... %s" % (str1, str2)
                child=wx.Menu()
                i=0
                for name in items[group:last]:
                    self._insert(child,i,name)
                    i+=1
                self._insertMenu(menu,pos,child,groupname,is_toplevel)
                pos+=1
        else:
            for name in items:
                self._insert(menu,pos,name,is_toplevel=is_toplevel)
                pos+=1
                
        self.savehash=self.getHash()

    def _insert(self,menu,pos,name,is_toplevel=False):
        id = self.cache.getNewId()
        try:
            if self.localize_items:
                name = _(name)
            widget=menu.Insert(pos, id, name, self.getDefaultTooltip(id, name))
        except:
            dprint(u"BAD MENU ITEM!!! pos=%d id=%d name='%s'" % (pos, id, name))
            raise
        #storeWeakref('menuitem', widget)
        self.id2index[id]=self.count
        if is_toplevel:
            self.toplevel.append(id)
        self.count+=1

    def _insertMenu(self,menu,pos,child,name,is_toplevel=False):
        id = self.cache.getNewId()
        if self.localize_items:
            name = _(name)
        widget=menu.InsertMenu(pos, id, name, child)
        #storeWeakref('menuitem', widget)
        if is_toplevel:
            self.toplevel.append(id)

    def getHash(self):
        return self.count
    
    def dynamic(self):
        # dynamic menu will be shown if getHash returned None
        if self.savehash != None and self.savehash == self.getHash():
            assert self.dprint("dynamic menu not changed.  Skipping")
            return
        assert self.dprint("toplevel=%s" % self.toplevel)
        assert self.dprint("id2index=%s" % self.id2index)
        assert self.dprint("items in list: %s" % self.menu.GetMenuItems())
        pos=0
        for item in self.menu.GetMenuItems():
            if item.GetId()==self.toplevel[0]:
                break
            pos+=1
        assert self.dprint("inserting items at pos=%d" % pos)
        for id in self.toplevel:
            assert self.dprint("deleting widget %d" % id)
            self.menu.Delete(id)
        self.toplevel=[]
        self.id2index={}
        assert self.dprint("inserting new widgets at %d" % pos)
        self.insertIntoMenu(self.menu,pos)
        # FIXME: it seems that on app exit, frame.menumap can be None, so check
        # for that here
        if self.frame.menumap:
            self.frame.menumap.reconnectEvents()

    def getItems(self):
        raise NotImplementedError

    def getIcons(self):
        raise NotImplementedError

    def showEnable(self):
        if self.toplevel:
            assert self.dprint("Enabling all items: %s" % str(self.toplevel))
            for id in self.toplevel:
                self.menu.Enable(id,self.isEnabled())

class RadioAction(ListAction):
    """Display a group of radio buttons in a menu bar.
    
    This is used to display a list of radio items while only requiring a single
    action to display the entire list.
    
    The subclass should override the L{getItems} method to return the list of
    items to display.  These items should be strings.  Like its L{ListAction}
    parent, the L{isEnabled} method sets the enable state for all the items in
    the radio list.
    
    The subclass should also override L{getIndex} to return the position within
    the list of the selected item in the radio list.
    
    If the items change their text strings, you should add the
    L{OnDemandActionMixin} and override the L{getHash} method to indicate when
    the user interface should redraw the menu.
    """
    menumax=-1
    inline=False

    def __init__(self, frame, menu=None, toolbar=None):
        # mapping of index (that is, position in menu starting from
        # zero) to the wx widget id
        self.index2id={}
        
        ListAction.__init__(self,frame,menu,toolbar)

    def insertIntoMenu(self,menu,pos=None):
        ListAction.insertIntoMenu(self,menu,pos)
        for id,index in self.id2index.iteritems():
            self.index2id[index]=id
        self.showCheck()

    def _insert(self,menu,pos,name,is_toplevel=False):
        id = self.cache.getNewId()
        if self.localize_items:
            name = _(name)
        widget=menu.InsertRadioItem(pos, id, name, self.getDefaultTooltip(id, name))
        #storeWeakref('menuitem', widget)
        self.id2index[id]=self.count
        if is_toplevel:
            self.toplevel.append(id)
        self.count+=1
    
    def showEnable(self):
        ListAction.showEnable(self)
        self.showCheck()
        
    def showCheck(self):
        if self.index2id:
            index=self.getIndex()
            assert self.dprint("checking %d" % (index))
            self.menu.Check(self.index2id[index],True)

    def getIndex(self):
        raise NotImplementedError
    
class ToggleListAction(ListAction):
    """Display a group of toggle buttons in a menu bar.
    
    This is used to display a list of toggle buttons while only requiring a
    single action to display the entire list.
    
    The subclass should override the L{getItems} method to return the list of
    items to display.  These items should be strings.
    
    The method L{isChecked} should be overridden by the subclass to provide the
    checked state for each item.
    
    If the items change their text strings, you should add the
    L{OnDemandActionMixin} and override the L{getHash} method to indicate when
    the user interface should redraw the menu.
    """
    def __init__(self, frame, menu=None, toolbar=None):
        # list of all toggles so we can switch 'em on and off
        self.toggles=[]
        
        ListAction.__init__(self,frame,menu,toolbar)

    def _insert(self,menu,pos,name,is_toplevel=False):
        id = self.cache.getNewId()
        widget=menu.InsertCheckItem(pos,id,name, self.getDefaultTooltip())
        #storeWeakref('menuitem', widget)
        self.id2index[id]=self.count
        if is_toplevel:
            self.toplevel.append(id)
        self.toggles.append(id)
        self.count+=1

    def showEnable(self):
        ListAction.showEnable(self)
        self.showCheck()
        
    def showCheck(self):
        if self.toplevel:
            assert self.dprint("Checking all items: %s" % str(self.toplevel))
            for id in self.toggles:
                self.menu.Check(id,self.isChecked(self.id2index[id]))

    def isChecked(self,index):
        """Override this to show whether the index is checked or not.
        
        @param index: the position in the list (numbered from zero)
        
        @returns: True if checked.
        """
        raise NotImplementedError


class SliderAction(SelectAction):
    """Display a slider toolbar item.
    
    This is used to display a slider (gauge) control in a toolbar.
    
    The subclass should override the L{isChecked} method to return a boolean
    indicating whether or not to display a checkmark (for a menu item) or to
    display the button as toggled-on (for a toolbar).
    """
    icon = True
    
    slider_width = 100
    
    def insertIntoMenu(self,menu):
        """Sliders are not allowed in the menu bar, so nothing will be added to
        the menu."""
        pass
    
    def getSliderValues(self):
        """Return the current, min, and max value for the slider"""
        return 0, 50, 100

    def insertIntoToolbar(self,toolbar):
        """Insert the slider control into the toolbar and set the min/max
        values and initial value.
        """
        self.tool=toolbar
        val, minval, maxval = self.getSliderValues()
        self.slider = wx.Slider(toolbar, -1, val, minval, maxval, size=(self.slider_width, -1))
        #dprint(self.slider)
        toolbar.AddControl(self.slider)
        
        self.slider.Bind(wx.EVT_SCROLL_THUMBTRACK, self.OnSliderMove)
        self.slider.Bind(wx.EVT_SCROLL_CHANGED, self.OnSliderRelease)
        
    def showEnable(self):
        state = self.isEnabled()
        self.slider.Enable(state)
    
    def OnSliderMove(self, evt):
        """Hook method responding to EVT_SCROLL_THUMBTRACK event.
        
        Hook method to be overridden in subclasses if you want to perform some
        update as the slider is changing.
        """
        #dprint(evt.GetPosition())
        pass
    
    def OnSliderRelease(self, evt):
        """Event callback when slider movement is complete."""
        pos = evt.GetPosition()
        self.action(pos)
    
    def updateToolOnDemand(self):
        """Update the state of the tool from the extrinsic source.
        
        This is called through L{UserActionMap.forceToolbarUpdate} when the
        toolbar has been updated.
        """
        val, minval, maxval = self.getSliderValues()
        #dprint("val=%d min=%d max=%d" % (val, minval, maxval))
        self.slider.SetRange(minval, maxval)
        self.slider.SetValue(val)


class OnDemandActionMixin(object):
    """Mixin to provide on-demand updating as the menubar is opened
    
    On-demand actions don't have to be created ahead of time -- the
    updateOnDemand method is called immediately before the menu bar entry
    is opened.
    """
    
    def updateOnDemand(self):
        """Hook called before the menu is displayed.
        
        This method allows the subclass to catch the menu opening event before
        it anything is added to the menu bar.  When used in combination with
        a list, the list may be reordered and menu items can be inserted or
        deleted.
        """
        raise NotImplementedError


class OnDemandActionNameMixin(object):
    """Mixin to provide on-demand naming of the menu item.
    
    The menu item in the menu bar will be changed as a result of the
    EVT_MENU_OPEN event handled by L{UserActionMap.OnMenuOpen}, so no user
    interaction is necessary if only menu bar items are used.
    
    However, if this on demand action has an associated toolbar
    icon, the update must be forced through a direct call to
    L{UserActionMap.forceToolbarUpdate}.  Because toolbars are always visible,
    there is no way to update the toolbar in response to some event.  Unless
    the update is forced manually, the toolbar will remain in its old state.
    """
    
    def updateOnDemand(self):
        """Updates the menu item name.
        
        Because menu items are normally hidden, the EVT_MENU_OPEN event
        that is sent immediately before the menu is displayed can be used
        for the purpose of updating the name.  That's what happens in
        L{UserActionMap.OnMenuOpen}.
        """
        if not self.widget:
            return
        
        name = self.getMenuItemName()
        help = self.getMenuItemHelp(name)
        icon = self.getToolbarIconName()
        if icon:
            icon = getIconBitmap(icon)
            # FIXME: setting the menu bitmap mangles the menu on MSW -- it
            # pushes all menu items not set over to the right, as if the old
            # menu item labels become the accelerator text.
            if icon and wx.Platform != "__WXMSW__":
                self.widget.SetBitmap(icon)
        if name:
            self.widget.SetItemLabel(name)
        self.widget.SetHelp(help)
    
    def updateToolOnDemand(self):
        """Updates the toolbar item.
        
        This is only called through the L{UserActionMap.forceToolbarUpdate}
        method because toolbars must be manually updated at the time they
        are changed.
        """
        if self.tool:
            icon = self.getToolbarIconName()
            if icon:
                icon = getIconBitmap(icon)
                self.tool.SetToolNormalBitmap(self.global_id, icon)
                name = self.getMenuItemName()
                self.tool.SetToolShortHelp(self.global_id, name)
                help = self.getMenuItemHelp(name)
                self.tool.SetToolLongHelp(self.global_id, help)
                
    def getMenuItemName(self):
        """Override in subclass to provide the menu item name."""
        return ""

    def getMenuItemHelp(self, name):
        """Override in subclass to provide the help text.
        
        This is shown in the status line when hovering over the menu item or
        toolbar item.
        """
        return self.getDefaultTooltip(name = name)

    def getToolbarIconName(self):
        """Override in subclass to provide the name of the icon."""
        return ""


class OnDemandGlobalListAction(OnDemandActionMixin, ListAction):
    """On-demand list that shares its items in all menu bars.
    
    Menu items are shared by using class attributes for the storage.  Be aware
    that you either have to, in your subclass of OnDemandGlobalListAction,
    have to explicitly name a class attribute 'storage' and it must be a list,
    or you can call your subclasses class method setStorage and supply it with
    a list.
    """
    # identifier that keeps track whenever ANY instance of
    # OnDemandGlobalListAction changes.  This causes menus to be rebuilt
    # unnecessarily, as most operations aren't expensive, anything more
    # complicated is a waste.  If you want a hash that only tracks your class,
    # create a class attribute 'localhash' in your subclass
    globalhash = 0
    
    # storage for each class.  setStorage should be called before using
    # any methods, or alternatively you can define a class attribute named
    # 'storage' that's a list, which will shadow the None definition here.
    storage = None
    
    @classmethod
    def setStorage(cls, array):
        cls.storage = array
    
    @classmethod
    def trimStorage(cls, num):
        if len(cls.storage) > num:
            cls.storage[num:]=[]

    @classmethod
    def append(cls, item):
        cls.storage.append(item)
        cls.calcHash()

    @classmethod
    def remove(cls, item):
        cls.storage.remove(item)
        cls.calcHash()
    
    @classmethod
    def calcHash(cls):
        """Hash calculation method to determine if menu items have changed.
        
        The default implementation is a simplistic one that changes every time
        calcHash is called, guaranteeing that the menu will be updated the
        next time.
        
        If calcHash sets cls.localhash or cls.globalhash to None, the menu will
        always be updated.
        """
        if hasattr(cls, 'localhash'):
            cls.localhash += 1
        else:
            cls.globalhash += 1

    def getHash(self):
        """Simplistic implementation that only keeps track of additions or deletions.
        
        Should more rigorous hashing be needed, override this.
        """
        if hasattr(self, 'localhash'):
            return self.localhash
        else:
            return self.globalhash
    
    def getItems(self):
        if self.storage is None:
            raise TypeError("The 'storage' class attribute of OnDemandGlobalActionList must be of type 'list' when using the default implementation of getItems")
        return [unicode(item) for item in self.storage]

    def updateOnDemand(self):
        self.dynamic()
