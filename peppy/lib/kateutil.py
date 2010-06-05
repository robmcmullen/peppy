# peppy Copyright (c) 2006-2010 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Utility functions for interacting with kate

These text utilities have no dependencies on any other part of peppy, and
therefore may be used independently of peppy.

The KDE wiki has a description of how U{Kate
variables<http://wiki.kde.org/tiki-index.php?page=Configuring%20Kate%20with%20variables>} are stored.
"""
import re
import wx.stc

def kateTruth(value):
    value = value.lower()
    return value == '1' or value == 'on' or value == 'true'

def kateParseLine(line):
    """Find the kate variables on the line

    Kate variables always start with 'kate:' and variable/value pairs are
    separated by whitespace and end with a semicolon:
    
    kate: VARIABLENAME VALUE; [ VARIABLENAME VALUE; ... ]

    @param line: first x bytes of the file to be loaded
    @return: dict of the name/value pairs.
    """
    match = re.search(r'\s*kate:\s*(.+)', line)
    vars = {}
    if match:
        varstring = match.group(1)
        if varstring:
            try:
                for nameval in varstring.split(';'):
                    s = nameval.strip()
                    if s:
                        name,val=s.split(' ', 1)
                        vars[name.strip()]=val.strip()
            except:
                pass
    return vars

# mapping for the kate identifier to the name of the stc getter/setter function
# that uses integers.  For this to work correctly, the integer must mean the
# same in the kate context as it does to the stc.
int_mapping = {
    'tab-width': 'TabWidth',
    'indent-width': 'Indent',
    }

# boolean mapping of kate identifier to the stc getter/setter function.  The
# boolean value must have the same sense as the stc getter/setter expects
bool_mapping = {
    }

# convenience mapping that maps the kate identifier to the opposite sense of
# the stc getter/setter.
not_bool_mapping = {
    'space-indent': 'UseTabs',
    }

def applyKateVariables(stc, linelist):
    """Scan the text for kate settings that will be applied to the stc
    
    Kate uses U{Kate variables<http://wiki.kde.org/tiki-index.php?page=Configuring%20Kate%20with%20variables>}

    to customize major modes on a per-file basis.  According to the Kate
    documentation, only the first 10 and last 10 lines are scanned for the
    presence of the variables, which must be of the form:
    
    kate: VARIABLENAME VALUE; [ VARIABLENAME VALUE; ... ]
    
    Kate uses a lot of different variables, and I think some can depend on the
    major mode.  Any that aren't recognized here are passed back to the major
    mode for it to do additional processing.
    
    @param stc: styled text control that will be used to apply settings
    @param linelist: list of text lines limiting the search
    
    @return: list of settings affected.  Settings changed are reported as the
    name of the wx.stc method used for each setting, with the 'Set' removed.
    If the tab width is changed, the setting is reported as 'TabWidth'.
    """
    settings_changed = []
    
    vars = {}
    for line in linelist:
        vars.update(kateParseLine(line))
    
    for name, setting in int_mapping.iteritems():
        if name in vars:
            # Construct the name of the stc setting function and set the value
            func = getattr(stc, "Set%s" % setting)
            func(int(vars[name]))
            settings_changed.append(setting)
    
    for name, setting in bool_mapping.iteritems():
        if name in vars:
            func = getattr(stc, "Set%s" % setting)
            func(kateTruth(vars[name]))
            settings_changed.append(setting)
    for name, setting in not_bool_mapping.iteritems():
        if name in vars:
            func = getattr(stc, "Set%s" % setting)
            func(not kateTruth(vars[name]))
            settings_changed.append(setting)
    
    # check for more complicated settings
    if 'show-tabs' in vars:
        if kateTruth(vars['show-tabs']):
            stc.SetViewWhiteSpace(wx.stc.STC_WS_VISIBLEALWAYS)
        else:
            stc.SetViewWhiteSpace(wx.stc.STC_WS_INVISIBLE)
        settings_changed.append('ViewWhiteSpace')
    
    return settings_changed, vars

def kateTruthFromBool(value):
    if value:
        return 'on'
    return 'off'

def serializeKateVariables(stc, column_width=-1):
    """Serialize the current stc's settings into kate-compatible variables
    
    Using the current settings of the stc, this generates a text string that
    encodes all the settings that can be converted into kate identifiers.
    """
    settings = {}
    
    for name, setting in int_mapping.iteritems():
        # Construct the name of the stc setting function and set the value
        func = getattr(stc, "Get%s" % setting)
        settings[name] = "%d" % func()
    for name, setting in bool_mapping.iteritems():
        func = getattr(stc, "Get%s" % setting)
        settings[name] = "%s" % kateTruthFromBool(func())
    for name, setting in not_bool_mapping.iteritems():
        func = getattr(stc, "Get%s" % setting)
        settings[name] = "%s" % (kateTruthFromBool(not func()))
        
    # check for more complicated settings
    val = stc.GetViewWhiteSpace()
    if val == wx.stc.STC_WS_VISIBLEALWAYS:
        settings['show-tabs'] = 'on'
    else:
        settings['show-tabs'] = 'off'
    
    names = settings.keys()
    names.sort()
    text = "kate:"
    count = 0
    for name in names:
        var = " %s %s;" % (name, settings[name])
        if column_width > 0 and count + len(var) > column_width:
            text += "\nkate:"
            count = 5
        text += var
        count += len(var)
    return text
