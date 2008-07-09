.. _preferences:

*****************************
Customization and Preferences
*****************************

There are two ways to change preferences in peppy.  First is to use the Edit
-> Preferences menu (or Peppy -> Preferences menu if you're on Mac OS X).
Most settings are available here, although there are a few that can't be set
through the GUI.  Those settings that can't must be modified by hand in the
configuration directory.


Configuration Files
===================

Peppy maintains a configuration directory on a per-user basis.  Where
it is located depends on which platform you are using: (if you're
familiar with wxWindows, it's the directory that's returned from the
``wx.StandardPaths.GetUserDataDir()`` method)

 * unix/linux: ``$HOME/.peppy``
 * windows: ``C:/Documents and Settings/username/Application Data/Peppy``
 * mac: ``~/Library/Application Support/Peppy``

There are a variety of files in that directory, used to store various bits of
data for persistence between runs of peppy.  The user configuration file is
peppy.cfg, and the settings saved by the application go in preferences.cfg.
Don't use preferences.cfg for your user settings, as they are overwritten
when settings are saved after exiting the main application.  Put all your
hand-edited changes in peppy.cfg instead.

The preferences are stored in `Windows INI`__ format.

__ http://en.wikipedia.org/wiki/INI_file

Internationalization (i18n)
===========================

Several national languages are available thanks to the members of Launchpad who
have been kind enough to translate my English into other languages.  In the
preferences dialog, click on the General tab and choose the Languages item.
You can select from any of the languages in the list, and the user interface
will change immediately.  No need to restart the application!


Changing Text Styles
====================

The wxPython StyledTextCtrl uses a single font for the main text, and can
optionally use a separate font for the line numbers.  These fonts are set in
the Preferences dialog: in the General tab, choose the Fonts item and select
the primary editing font (for the main text) and the secondary editing font
(for the line numbers).

Font colors and styles are changed using the Edit -> Text Styles dialog.  This
associates particular syntax elements of the text file with styles and colors
specified here.


Key Bindings
============

There are three styles of key binding supported by peppy: windows style, Mac
style, and emacs style.  These are controlled by preference settings in the
Preferences menu, in the General tab under the Keyboard item.  This setting
controls the default key bindings for all actions; actions may still be
overridden manually.




Configuring Key Bindings
------------------------

User specified key bindings should be stored in the peppy.cfg file in the
user's preferences directory.

In the ``peppy.cfg`` file, the section ``KeyboardConf`` controls user overrides
to the default keybindings.

An example of the section might be::

    [KeyboardConf]
    key_bindings = "emacs"
    NextWord = C-N
    PreviousWord = C-P
    Paste = C-V

Breaking it down by parts:

[KeyboardConf]
  This is the section header that denotes a keyboard configuration block

key_bindings = "emacs"
  The ``key_bindings`` variable controls the default keyboard configuration.
  If this variable is not present, the default configuration is automatically
  determined based on the platform.  To set this variable, it should use one
  of the following values: "emacs", "win", or "mac".

NextWord = C-n
  The remaining entries in the section are keybindings.  The format of each
  line is ``ActionName = keybinding``, where ``ActionName`` is the
  class name of the action you wish to rebind.  Currently, the easiest way
  to discover these name is to run peppy with the ``--show-key-bindings``
  argument, which will display all of the current keybindings to the console
  in a format usable for the ``KeyboardConf`` section of the preferences.
  You can also use the menu item ``Help -> Show Key Bindings``, or when all
  else fails you can look at the source code.  (A GUI to change the keybindings
  is ticket #53 on the roadmap.  Feel free to add suggestions there.)
  
  To specify keystrokes, consult the section below.



Describing Keystrokes
---------------------

To modify the key bindings, Key bindings are specified using a special
shorthand showing the modifiers of the key and the key itself.  Modifiers are:

 * **S** - Shift
 * **C** - Control on win/unix, Command on mac
 * **M** - Meta or Alt on win/unix, Option on mac

Keys are then specified using a string listing the modifier characters
separated by the - character, and then the unshifted character itself.
Unmodified keys are also possible -- if the keystroke doesn't contain a -
character it is used as a literal character.  For example:

 * **x** - the letter X
 * **s** - the letter S
 * **S-s** - shift S
 * **C-a** - control A
 * **S-/** - shift slash (note that you can't specify a ? directly -- keys are recognized by their unshifted state in wx)
 * **M-C-q** - alt control Q

Multiple keystrokes are separated by spaces:

 * **C-x C-s** - control X followed by control S
 * **C-x 5 2** - control X followed by the number 5 followed by the number 2

Special characters are given by their text equivalent:

 * **TAB** - the tab key
 * **S-UP** - shift up arrow

Here's a list of special characters (note that if you're familiar with
wxPython, this is really just the `WXK_` name with the `WXK_` prefix removed):

  BACK TAB RETURN ESCAPE SPACE DELETE START LBUTTON RBUTTON CANCEL MBUTTON
  CLEAR PAUSE CAPITAL PRIOR NEXT END HOME LEFT UP RIGHT DOWN SELECT PRINT
  EXECUTE SNAPSHOT INSERT HELP NUMPAD0 NUMPAD1 NUMPAD2 NUMPAD3 NUMPAD4 NUMPAD5
  NUMPAD6 NUMPAD7 NUMPAD8 NUMPAD9 MULTIPLY ADD SEPARATOR SUBTRACT DECIMAL
  DIVIDE F1 F2 F3 F4 F5 F6 F7 F8 F9 F10 F11 F12 F13 F14 F15 F16 F17 F18 F19
  F20 F21 F22 F23 F24 NUMLOCK SCROLL PAGEUP PAGEDOWN NUMPAD_SPACE NUMPAD_TAB
  NUMPAD_ENTER NUMPAD_F1 NUMPAD_F2 NUMPAD_F3 NUMPAD_F4 NUMPAD_HOME NUMPAD_LEFT
  NUMPAD_UP NUMPAD_RIGHT NUMPAD_DOWN NUMPAD_PRIOR NUMPAD_PAGEUP NUMPAD_NEXT
  NUMPAD_PAGEDOWN NUMPAD_END NUMPAD_BEGIN NUMPAD_INSERT NUMPAD_DELETE
  NUMPAD_EQUAL NUMPAD_MULTIPLY NUMPAD_ADD NUMPAD_SEPARATOR NUMPAD_SUBTRACT
  NUMPAD_DECIMAL NUMPAD_DIVIDE





