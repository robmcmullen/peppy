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

import wx

from peppy.debug import *
from peppy.lib.multikey import KeyAccelerator
from peppy.lib.iconstorage import *
from peppy.lib.userparams import getAllSubclassesOf


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


class MacroPlaybackState(object):
    """Persistent object through the lifetime of the macro playback that can
    be used to store information needed by multiple actions in the macro list.
    
    The state will include at least the frame instance and major mode instance
    that the L{RecordedAction} can use to instantiate an action object.
    """
    def __init__(self, frame, mode):
        self.frame = frame
        self.mode = mode


class RecordedAction(debugmixin):
    """Base class for a recorded action
    
    Actions are recorded for later playback by storing the class of the action
    and any metadata needed by the action to reproduce the effects of the
    action.  The instance of the action is not stored because it includes
    transient information like the current frame and major mode instances that
    would not be serializable.
    """
    def __init__(self, action, multiplier):
        self.actioncls = action.__class__
        self.multiplier = multiplier
    
    def canCoalesceActions(self, next_record):
        """If the current action can coelesce with the next action, return
        the new action that combines the two.
        """
        if hasattr(self.actioncls, 'canCoalesce'):
            return self.actioncls.canCoalesce(next_record.actioncls)
        return False
    
    def coalesceActions(self, next_record):
        """If the current action can coelesce with the next action, return
        the new action that combines the two.
        """
        return self.actioncls.coalesce(self, next_record)
    
    def performAction(self, playback_state):
        """Perform the action by instantiating the action class using the
        specified system state.
        
        """
        raise NotImplementedError
    
    def getScripted(self):
        """Convert the action into a text string capable of being C{exec}ed to
        reproduce the effect of the recorded action
        
        """
        raise NotImplementedError


class MacroAction(debugmixin):
    """Action used in SelectAction playback, but not directly performed by the
    user.
    
    """
    
    @classmethod
    def getAllKnownActions(cls, subclass=None):
        """Get a list of all known actions
        
        By specifying the subclass, the returned list will be limited to those
        actions that are of the specified subclass.
        """
        if subclass is None:
            subclass = cls
        actions = getAllSubclassesOf(subclass)
        return actions

    def __init__(self, frame, popup_options=None, mode=None):
        self.frame = frame
        if mode is None:
            self.mode = frame.getActiveMajorMode()
        else:
            self.mode = mode
        self.popup_options = popup_options

    def action(self, index=-1, multiplier=1):
        """See L{SelectAction.action}
        """
        pass
    
    def actionKeystroke(self, evt, multiplier=1):
        """See L{SelectAction.actionKeystroke}
        """
        pass

    @classmethod
    def canCoalesce(cls, other_action):
        """Returns whether or not the recorded action can be coalesced with
        another action
        
        @param other_action: class of the other action
        
        @returns: if the current action can be merged with the other action
        forming a new action.
        """
        return False
    
    @classmethod
    def coalesce(cls, first, second):
        """Combines two actions to form a single new action.
        
        """
        raise NotImplementedError


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
    needs_keyboard_focus = False
    
    #: Current keybinding of the action.  This is set by the keyboard configuration loader and shouldn't be modified directly.  Subclasses should leave this set to None.
    keyboard = None
    
    #: Flag to indicate that the user has specified the keybinding of the action, and should therefore override built-in key bindings.  This attribute is set by the keyboard configuration loader and shouldn't be modified directly.  Subclasses should leave this set to None.
    user_keyboard = None
    
    #: If this menu action has a stock wx id, such as wx.ID_ABOUT or wx.ID_PREFERENCES, add it here and the wx menu system can do some special things to it, like automatically give it the correct location on WXMAC.
    stock_id = None
    
    #: If the action doesn't use a stock id, it will automatically get assigned a global id here.  Note that if you are subclassing an action, you should explicitly assign a global id (or None) to your subclass's global_id attribute, otherwise the menu system will get confused and attempt to use the superclass's global_id
    global_id = None

    #: Special case support item for OS X.  Under OS X, it is possible to have a menubar when no windows are open.  If the action is usable when operating on an empty frame (see plugins/platform_osx.py), set osx_minimal_menu to True or override worksWithOSXMinimalMenu
    osx_minimal_menu = None
    
    #: Author's name for credits
    author = None
    
    # The rest of these class attributes aren't for individual class
    # customization
    _use_accelerators = True
    _accelerator_text = None # This is not set by the user

    @classmethod
    def worksWithMajorMode(cls, modecls):
        """Hook to restrict the action to only be displayed with a specific
        major mode
        
        This hook is called by the menu creation code to determine if the
        action should be displayed when showing the major mode's user interface.
        
        @param mode: the major mode class (Note: not the instance)
        
        @returns: True if the action is allowed to be associated with the major
        mode
        """
        return True
    
    @classmethod
    def worksWithOSXMinimalMenu(cls, modecls):
        """Hook that allows the action to appear on the OSX default menu when
        no editing frames are open
        """
        return cls.osx_minimal_menu
    
    @classmethod
    def getHelp(cls):
        #dprint(dir(cls))
        help = u"\n\n'%s' is an action from module %s\nBound to keystrokes: %s\nAlias: %s\nDocumentation: %s" % (cls.__name__, cls.__module__, cls.keyboard, cls.alias, cls.__doc__)
        return help
    
    
    ignore_other_baseclasses = ['MinibufferAction', 'MinibufferRepeatAction']
    
    @classmethod
    def getAllKnownActions(cls, subclass=None):
        """Get a list of all known actions
        
        By specifying the subclass, the returned list will be limited to those
        actions that are of the specified subclass.
        """
        if subclass is None:
            subclass = cls
        actions = getAllSubclassesOf(subclass)
        actions = [a for a in actions if a.__name__ not in cls.ignore_other_baseclasses]
        return actions
    
    def __init__(self, frame, mode=None, popup_options=None):
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
        if mode is None:
            self.mode = frame.getActiveMajorMode()
        else:
            self.mode = mode
        
        # If the action is associated with a popup, some options may be passed
        # into it.  This is also an indicator that the action appears in a
        # popup: if popup_options is None, it's not a popup.  If popup_options
        # is a dict (empty or not), it is in a popup.
        self.popup_options = popup_options
        
        # Flag to indicate whether the keystroke should be displayed in the
        # menu item.  This will be false if the keyboard loader detects that
        # an already existing action is using the same keystroke
        self.keystroke_valid = True

        self.initPreHook()

        self.initPostHook()
    
    def __str__(self):
        return "%s id=%s mode=%s frame=%s" % (self.__class__.__name__, hex(id(self)), self.mode, self.frame)

#    def __del__(self):
#        self.dprint("DELETING action %s" % self.getName())

    def initPreHook(self):
        pass

    def initPostHook(self):
        pass
    
    def getSubIds(self):
        return []

    @classmethod
    def setAcceleratorText(cls, force_emacs=False):
        """Sets the accelerator text for this class
        
        The accelerator text is set for the entire class rather than the action
        to save time.  Accelerator text doesn't change for each instance, and
        in addition only changes when the user changes the language of the
        user interface.
        
        The keyboard plugin is used to change the accelerator text, because
        the user may have changed the keyboard definition through the
        configuration files.
        """
        # If keyboard is the string 'default', that means that the action is
        # the default keyboard command for the major mode and there shouldn't
        # be an accelerator for it.  The default command shouldn't appear
        # in the menu at any rate, and I could instead check for a value in
        # default_menu.  However, this not be the right thing to do if at
        # some point in the future I get around to writing customizable menu
        # ordering functionality.
        if cls.keyboard and cls.keyboard != 'default':
            if isinstance(cls.keyboard, list):
                key_sequence = cls.keyboard[0]
            else:
                key_sequence = cls.keyboard
            keystrokes = KeyAccelerator.split(key_sequence)
            
            if wx.Platform == '__WXMAC__' and len(keystrokes) == 1:
                if keystrokes[0].flags & wx.ACCEL_CTRL:
                    # Don't attempt to put any accelerator that contains the
                    # Ctrl key in the menubar on a mac.  Rather, force it to
                    # be placed in the menubar as an emacs style keybinding.
                    force_emacs = True
            
            # Special handling if we are using a stock wx id -- wx automatically
            # places a stock icon and a default accelerator in the menu item.
            # We may have to adjust this depending on a few things...
            if cls.stock_id is not None:
                if len(keystrokes) == 1:
                    # If it's a stock ID with a single keystroke, it must
                    # be placed in standard menu format (not emacs format)
                    # because wx will place the stock accelerator there and we
                    # need to override it
                    force_emacs = False
                elif cls.global_id is None or cls.global_id == cls.stock_id:
                    # Can't use a stock id if we're also using emacs
                    # keybindings, because the stock id forces the standard
                    # one character key binding and we'll end up with an emacs
                    # style keybinding also appearing in the menu.  So, by
                    # forcing the ID to have a new ID number, wx won't insert
                    # its default stuff.
                    cls.global_id = wx.NewId()
            
            cls._accelerator_text = KeyAccelerator.getAcceleratorText(key_sequence, force_emacs)
                        
            #dprint("%s %s %s" % (cls.__name__, str(keystrokes), cls._accelerator_text))
            return len(keystrokes)
        else:
            cls._accelerator_text = ""
        return 0
    
    def addKeyBindingToAcceleratorList(self, accel_list):
        if self.keyboard == 'default':
            window = self.mode.getKeyboardCapableControls()[0]
            self.dprint("******** Setting default action to %s for %s" % (self, window))
            accel_list.addDefaultKeyAction(self, window)
        elif self.keyboard is not None:
            accel_list.addKeyBinding(self.keyboard, self)
    
    @classmethod
    def getName(cls):
        if cls.name:
            return unicode(cls.name)
        return unicode(cls.__name__)
    
    def getDefaultMenuItemName(self):
        if self._use_accelerators and self.__class__.keyboard and self.keystroke_valid and self.popup_options is None:
            return u"%s%s" % (_(self.getName()), self._accelerator_text)
        return self.getName()

    def getMenuItemNameWithoutAccelerator(self):
        if self._use_accelerators and self.__class__.keyboard and self.keystroke_valid and self.popup_options is None:
            acc = self._accelerator_text.strip()
            return u"%s (%s)" % (_(self.getName()), acc)
        return _(self.getName())

    @classmethod
    def getDefaultTooltip(cls, id=None, name=None):
        if cls.tooltip is None:
            if cls.__doc__ is not None:
                lines = cls.__doc__.splitlines()
                index = 0
                for line in lines:
                    if len(line.strip()) == 0:
                        break
                    index += 1
                cls.tooltip = unicode(u" ".join([line.strip() for line in lines[0:index]]))
                cls.tooltip = cls.tooltip.strip()
                
                # Remove a trailing period, but not a trailing ellipsis
                if cls.tooltip.endswith(".") and not cls.tooltip.endswith("..."):
                    cls.tooltip = cls.tooltip[:-1]
            else:
                cls.tooltip = u""
        text = unicode(cls.tooltip)
        if cls.debuglevel > 0:
            if id is None:
                id = cls.global_id
            if name is None:
                name = cls.getName()
            text += u"('%s', id=%d)" % (_(name), id)
        return text

    def insertIntoMenu(self, menu, accel):
        self.widget = wx.MenuItem(menu, self.global_id, self.getDefaultMenuItemName(), self.getDefaultTooltip())
        #storeWeakref('menuitem', self.widget)
        if self.icon:
            bitmap = getIconBitmap(self.icon)
            self.widget.SetBitmap(bitmap)
        menu.AppendItem(self.widget)
        accel.addMenuItem(self.global_id, self)

    def insertIntoToolbar(self, toolbar, accel):
        self.tool=toolbar
        help = _(self.getName()).replace('&','')
        toolbar.AddLabelTool(self.global_id, self.getName(), getIconBitmap(self.icon), shortHelp=help, longHelp=self.getDefaultTooltip())
        accel.addMenuItem(self.global_id, self)

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
    
    # Trick to force subclasses to declare this method in a subclass while still
    # keeping around the definition of action for documentation purposes.
    action = None
    
    def actionOSXMinimalMenu(self, index=-1, multiplier=1):
        self.action(index, multiplier)

    def actionWorksWithCurrentFocus(self):
        """Utility function to determine whether the action is allowed based
        on the keyboard focus.
        
        Not all actions are allowable when the keyboard doesn't have focus on
        the major mode.  For example, when the focus is on a minibuffer and
        there is a key bound to a major mode action, pressing that key while
        in the minibuffer shouldn't perform that action in the major mode.
        
        In the case of macro processing, however, the focus may not be on the
        major mode (for example, the focus may be on the MacroList springtab)
        but the action should still be allowed to take place.  So, only when
        macro processing is *not* happening will the current focus check take
        place.  When macro processing is happening, all actions are allowed.
        """
        if self.needs_keyboard_focus and not self.mode.isProcessingMacro() and self.mode.FindFocus() != self.mode:
            return False
        return True

    def actionKeystroke(self, evt, multiplier=1):
        assert self.dprint("%s called by keybindings -- multiplier=%s" % (self, multiplier))
        # Make sure that the action is enabled before allowing it to be called
        # using the keybinding
        if not self.actionWorksWithCurrentFocus():
            evt.Skip()
            return
        if self.isEnabled():
            try:
                if self.frame.isOSXMinimalMenuFrame():
                    self.actionOSXMinimalMenu(0, multiplier)
                else:
                    self.action(0, multiplier)
            except ActionNeedsFocusException:
                evt.Skip()

    def showEnable(self):
        state = self.isEnabled()
        if self.widget is not None:
            if self.debuglevel > 1:
                assert self.dprint(u"menu item %s (widget id=%d) enabled=%s" % (self.getName(), self.global_id, state))
            if self.widget.IsEnabled() != state:
                self.widget.Enable(state)
                
                # If the item is disabled, force the use of the label without
                # an accelerator.  Placing the accelerator in a disabled menu
                # item short circuits that character from working in a multi-
                # key combo or as a quoted character
                if state:
                    self.widget.SetItemLabel(self.getDefaultMenuItemName())
                else:
                    self.widget.SetItemLabel(self.getMenuItemNameWithoutAccelerator())
        if self.tool is not None:
            if self.debuglevel > 1:
                assert self.dprint(u"menu item %s (widget id=%d) enabled=%s tool=%s" % (self.getName(), self.global_id, state, self.tool))
            if self.tool.GetToolEnabled(self.global_id) != state:
                self.tool.EnableTool(self.global_id, state)

    def isEnabled(self):
        """Override this to provide the enable/disable state of the item.
        
        The menu system will call this method before the menu is drawn (or
        periodically during idle time for toolbar items) to determine whether
        or not the item should be disabled (grayed out).
        
        Default is to always enable the item.
        """
        return True
    
    
    # Some actions are recordable and can be played back as macro commands.
    @classmethod
    def isRecordable(cls):
        """Returns whether or not the action is recordable
        
        """
        return True
    
    @classmethod
    def canCoalesce(cls, other_action):
        """Returns whether or not the recorded action can be coalesced with
        another action
        
        @param other_action: class of the other action
        
        @returns: if the current action can be merged with the other action
        forming a new action.
        """
        return False
    
    @classmethod
    def coalesce(cls, first, second):
        """Combines two actions to form a single new action.
        
        """
        raise NotImplementedError
    

class ToggleAction(SelectAction):
    """Display a toggle button or toolbar item.
    
    This is used to display a single toggle button that can be displayed in
    either a menu bar or a toolbar.
    
    The subclass should override the L{isChecked} method to return a boolean
    indicating whether or not to display a checkmark (for a menu item) or to
    display the button as toggled-on (for a toolbar).
    """
    def insertIntoMenu(self, menu, accel):
        self.widget=menu.AppendCheckItem(self.global_id, self.getDefaultMenuItemName(), self.getDefaultTooltip())
        #storeWeakref('menuitem', self.widget)
        accel.addMenuItem(self.global_id, self)

    def insertIntoToolbar(self, toolbar, accel):
        self.tool=toolbar
        toolbar.AddCheckTool(self.global_id, getIconBitmap(self.icon), wx.NullBitmap, shortHelp=_(self.getName()), longHelp=self.getDefaultTooltip())
        accel.addMenuItem(self.global_id, self)
        
    def showEnable(self):
        SelectAction.showEnable(self)
        self.showCheck()
        
    def isChecked(self):
        raise NotImplementedError

    def showCheck(self):
        state = self.isChecked()
        if self.widget is not None:
            if self.widget.IsChecked() != state:
                self.widget.Check(state)
        if self.tool is not None:
            #dprint("%s, %s, %s" % (self.tool, self.global_id, state))
            if self.tool.GetToolState(self.global_id) != state:
                self.tool.ToggleTool(self.global_id, state)


class ListAction(SelectAction):
    """Display a list of items in a menu bar.
    
    This is used to display a list of items while only requiring a single
    action to display the entire list.
    
    The subclass should override the L{getItems} method to return the list of
    items to display.  These items should be strings or tuples.  Overriding
    L{isEnabled} will determine the enable/disable state for all of the items
    in the list.
    
    If the items are tuples, they are taken to be grouped items to be displayed
    in submenus.  The first item is the string to be displayed and the second
    item is the submenu name.  Submenus will be displayed as an additional
    level of pull-right menus as children of this action.
    
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

    def __init__(self, *args, **kwargs):
        SelectAction.__init__(self, *args, **kwargs)
        self.cache = self.IdCache(self.global_id)
    
    def getSubIds(self):
        ids = self.id2index.keys()
        ids.extend(self.toplevel)
        ids.sort()
        return ids
    
    def getIndexOfId(self, id):
        return self.id2index[id]
    
    def getNonInlineName(self):
        """When the list isn't an inline menu, get the name that should be used
        as the indicator label for the menu.
        """
        return self.getDefaultMenuItemName()
    
    def insertIntoMenu(self, menu, accel, pos=None):
        # a record of all menu entries at the main level of the menu
        self.toplevel=[]

        # mapping of menu id to position in menu
        self.id2index={}
        
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
            self._insertMenu(menu, pos, child, self.getNonInlineName(),True)
            self.topindex=pos
            pos=0
            menu=child
            is_toplevel=False
        else:
            self.topindex=pos
        
        self._insertItems(menu, accel, pos, is_toplevel)

    def _insertItems(self, menu, accel, pos, is_toplevel=False):
        items = self.getItems()
        self.count=0
        if items and (isinstance(items[0], tuple) or isinstance(items[0], list)):
            self._insertGroupedItems(items, menu, accel, pos, is_toplevel)
        else:
            self._insertTextItems(items, menu, accel, pos, is_toplevel)
        self.savehash=self.getHash()
    
    def _insertTextItems(self, items, menu, accel, pos, is_toplevel):
        if self.menumax>0 and len(items)>self.menumax:
            for group in range(0,len(items),self.menumax):
                last=min(group+self.menumax,len(items))
                str1 = items[group].strip()[0:self.abbrev_width]
                str2 = items[last-1].strip()[0:self.abbrev_width]
                groupname="%s ... %s" % (str1, str2)
                child=wx.Menu()
                i=0
                for name in items[group:last]:
                    self._insert(child, accel, i, name)
                    i+=1
                self._insertMenu(menu, pos, child, groupname, is_toplevel)
                pos+=1
        else:
            for name in items:
                self._insert(menu, accel, pos, name, is_toplevel=is_toplevel)
                pos+=1

    def _insertGroupedItems(self, items, menu, accel, pos, is_toplevel=False):
        """Insert a list of grouped items into the menu

        If each item is a tuple in the form (text of the item, group name) the
        items will be grouped into sub-menus.  The menu will be structured so
        that each group name will appear as a submenu of the menu item with
        the items in each group appearing in the order appearing in the list.
        """
        order = []
        found = {}
        for name, group in items:
            if group not in found:
                order.append(group)
                found[group] = (wx.Menu(), 0)
            child, i = found[group]
            self._insert(child, accel, i, name)
            i += 1
            found[group] = (child, i)
        for group in order:
            child, dum = found[group]
            self._insertMenu(menu, pos, child, group, is_toplevel)
            pos += 1

    def _insert(self, menu, accel, pos, name, is_toplevel=False):
        id = self.cache.getNewId()
        try:
            if self.localize_items:
                name = _(name)
            widget=menu.Insert(pos, id, name, self.getDefaultTooltip(id, name))
            accel.addMenuItem(id, self, self.count)
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
    
    def dynamic(self, accel):
        # dynamic menu will be shown if getHash returned None
        if self.savehash != None and self.savehash == self.getHash():
            if self.debuglevel > 1:
                self.dprint("dynamic menu not changed.  Skipping")
            return
        if self.debuglevel > 1:
            self.dprint("toplevel=%s" % self.toplevel)
            self.dprint("id2index=%s" % self.id2index)
            self.dprint("items in list: %s" % self.menu.GetMenuItems())
        pos=0
        if self.toplevel:
            for item in self.menu.GetMenuItems():
                if item.GetId()==self.toplevel[0]:
                    break
                pos+=1
        if self.debuglevel > 1:
            self.dprint("inserting items at pos=%d" % pos)
        for id in self.toplevel:
            if self.debuglevel > 1:
                self.dprint("deleting widget %d" % id)
            self.menu.Delete(id)
        if self.debuglevel > 1:
            self.dprint("inserting new widgets at %d" % pos)
        self.insertIntoMenu(self.menu, accel, pos)

    def getItems(self):
        raise NotImplementedError

    def getIcons(self):
        raise NotImplementedError

    def showEnable(self):
        if self.toplevel:
            if self.debuglevel > 1:
                self.dprint("Enabling all items: %s" % str(self.toplevel))
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

    def insertIntoMenu(self, menu, accel, pos=None):
        # mapping of index (that is, position in menu starting from
        # zero) to the wx widget id
        self.index2id={}
        ListAction.insertIntoMenu(self, menu, accel, pos)
        for id,index in self.id2index.iteritems():
            self.index2id[index]=id
        self.showCheck()

    def _insert(self,menu, accel, pos, name, is_toplevel=False):
        id = self.cache.getNewId()
        if self.localize_items:
            name = _(name)
        widget=menu.InsertRadioItem(pos, id, name, self.getDefaultTooltip(id, name))
        accel.addMenuItem(id, self, self.count)
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
            if self.debuglevel > 1:
                self.dprint("checking %d" % (index))
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
    def insertIntoMenu(self, menu, accel, pos=None):
        # list of all toggles so we can switch 'em on and off
        self.toggles=[]
        ListAction.insertIntoMenu(self, menu, accel, pos)

    def _insert(self, menu, accel, pos, name, is_toplevel=False):
        id = self.cache.getNewId()
        widget=menu.InsertCheckItem(pos,id,name, self.getDefaultTooltip())
        accel.addMenuItem(id, self, self.count)
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
            if self.debuglevel > 1:
                self.dprint("Checking all items: %s" % str(self.toplevel))
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
    
    def insertIntoMenu(self, menu, accel):
        """Sliders are not allowed in the menu bar, so nothing will be added to
        the menu."""
        pass
    
    def getSliderValues(self):
        """Return the current, min, and max value for the slider"""
        return 0, 50, 100

    def insertIntoToolbar(self, toolbar, accel):
        """Insert the slider control into the toolbar and set the min/max
        values and initial value.
        """
        self.tool=toolbar
        self._last_tool_val, self._last_tool_minval, self._last_tool_maxval = self.getSliderValues()
        if self._last_tool_minval == self._last_tool_maxval:
            self._last_tool_maxval += 1
            enable = False
        else:
            enable = True
        self.slider = wx.Slider(toolbar, -1, self._last_tool_val, self._last_tool_minval, self._last_tool_maxval, size=(self.slider_width, -1))
        self.slider.Enable(enable)
        #dprint(self.slider)
        toolbar.AddControl(self.slider)
        
        self.slider.Bind(wx.EVT_SCROLL_THUMBTRACK, self.OnSliderMove)
        self.slider.Bind(wx.EVT_SCROLL_CHANGED, self.OnSliderRelease)
        self.slider.SetToolTip(wx.ToolTip(_(self.getName())))
        
    def showEnable(self):
        state = self.isEnabled()
        if self.slider.IsEnabled() != state:
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
        if self._last_tool_minval != minval or self._last_tool_maxval != maxval:
            if minval == maxval:
                maxval += 1
                self.slider.Enable(False)
            self.slider.SetRange(minval, maxval)
            self._last_tool_minval = minval
            self._last_tool_maxval = maxval
        if self._last_tool_val != val:
            self.slider.SetValue(val)
            self._last_tool_val = val


class OnDemandActionMixin(object):
    """Mixin to provide on-demand updating as the menubar is opened
    
    On-demand actions don't have to be created ahead of time -- the
    updateOnDemand method is called immediately before the menu bar entry
    is opened.
    """
    
    def updateOnDemand(self, accel):
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
    
    def updateOnDemand(self, accel):
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
                if not hasattr(self, "_tool_last_icon") or self._tool_last_icon != icon:
                    dprint("Updating icon to %s" % icon)
                    self._tool_last_icon = icon
                    
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

    def updateOnDemand(self, accel):
        self.dynamic(accel)
