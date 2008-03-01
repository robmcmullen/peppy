# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Utility functions for interacting with vim

These text utilities have no dependencies on any other part of peppy, and
therefore may be used independently of peppy.

The vim modeline parsing was borrowed from U{PyPE<http://pype.sourceforge.net>}
"""
import re

def applyVIMModeline(stc, linelist):
    """Scan the given text for vim settings.
    
    Modelines in vim (described in U{vim
    documentation<http://vimdoc.sourceforge.net/htmldoc/options.html#modeline>})
    are parsed into a dictionary, where the keys are the full names of the vim
    settings.
    
    Borrowed from Josiah Carlson's U{PyPE<http://pype.sourceforge.net>}
    
    @param stc: styled text control that will be used to apply settings
    @param linelist: list of lines to consider
    """
    DBG = True
    sre = re.compile('(?:^|\s+)vim?:(?:\s*set?\s+)?(.+):')
    
    #hcl ->  Highlight Current Line
    #ut -> Use Tabs
    #siw -> Set Indent Width
    #stw -> Set Tab Width
    ## #mc -> Match Case
    
    options = {
        'cursorline':'hcl',
        'cul':'hcl',
        'nocursorline':'!hcl',
        'nocul':'!hcl',
        'expandtab':'!ut',
        'et':'!ut',
        'noexpandtab':'ut',
        'noet':'ut',
        'shiftwidth':'siw',
        'sw':'siw',
        'softtabstop':'siw',
        'sts':'siw', #(shiftwidth preferred)
        'tabstop':'stw',
        'ts':'stw',
        'tw': 'tw',
        'textwidth': 'tw',
        ## 'ignorecase':'mc',
        ## 'ic':'mc',
        ## 'noignorecase':'mc',
        ## 'noic':'mc',
    }
    
    toggle = ('ut', 'hcl')
    
    values = {}
    saw_sw = 0
    
    for line in linelist:
        if DBG: print "checking line %s" % line
        set_command = sre.search(line.rstrip())
        if not set_command:
            continue
        
        commands = set_command.group(1).replace(':', ' ')
        if DBG: print "set command:", commands
        
        for o in commands.lower().split():
            o = o.replace(':', '=')
            if DBG: print "option:", o, 
            inv = 0
            value = None
            if o.startswith('inv'):
                o = o[3:]
                inv = 1
            if '!' in o:
                inv = not inv
                option = o.replace('!', '')
            elif '=' in o:
                option, value = o.split('=', 1)
            else:
                option = o
            if option not in options:
                if DBG: print "bad option", option
                continue
            key = options[option]
            ks = key.strip('!')
            if DBG: print "maps to:", ks
            
            if ks in toggle and value is None:
                key = '!'*inv + key
                if key[:2] == '!!':
                    towrite = towrite[2:]
                if DBG: print "updating toggle", key
                values[ks] = '!' not in key
            elif ks not in toggle and value:
                try:
                    value = int(value)
                except ValueError:
                    print "huh:", value
                    continue
                if key == 'siw' and option in ('shiftwidth','sw'):
                    saw_sw = 1
                elif saw_sw and key == 'siw':
                    continue
                if DBG: print "setting", ks, '<-', value
                values[ks] = value
            else:
                if DBG: print "insane value!", ks, value
                continue
    if DBG: print values.items()
    if 'hcl' in values:
        stc.SetCaretLineVisible(values['hcl'])
    if 'ut' in values:
        stc.SetUseTabs(values['ut'])
        stc.SetProperty("tab.timmy.whinge.level", "10"[bool(values['ut'])])
    if 'siw' in values:
        stc.SetIndent(values['siw'])
    if 'stw' in values:
        stc.SetTabWidth(values['stw'])
    if 'tw' in values:
        stc.SetEdgeColumn(values['tw'])

def createVIMModeline(stc):
    entries = []
    if stc.GetCaretLineVisible():
        entries.append("hcl")
    entries.append("sw=%d" % stc.GetIndent())
    entries.append("ts=%d" % stc.GetTabWidth())
    edge = stc.GetEdgeColumn()
    if edge > 0:
        entries.append("tw=%d" % edge)
    text = " vim: %s:" % ' '.join(entries)
    return text
