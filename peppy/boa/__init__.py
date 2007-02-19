"""Wrapper and utility functions around boa constructor's STC style
setting dialog.

This module provides some configuration file utility functions to
locate and generate the user's configuration file.
"""
import os

import wx

from peppy.boa.STCStyleEditor import STCStyleEditDlg, initSTC

from peppy.debug import dprint

common_defs = {
    'size': 8,
    'mono': 'Bitstream Vera Sans Mono',
    'ln-size': 8,
    'ln-font': 'Arial',
    'backcol': '#FFFFFF',
    'comment-col': '#FF0000',
    'string-col': '#1D701B',
    'identifier-col': '#000000',
    'preprocessor-col': '#000000',
}

common_defs_platforms = {
    'common.defs.gtk': {},
    'common.defs.msw': {'size': 10,
                        'mono': 'Courier New',
                        'ln-font': 'Arial',
                        },
    'common.defs.mac': {'size': 12,
                        'mono': 'Courier',
                        'ln-font': 'Helvetica',
                        },
    }

lines = ["""\
common.styleidnames = {wx.stc.STC_STYLE_DEFAULT: 'Style default', wx.stc.STC_STYLE_LINENUMBER: 'Line numbers', wx.stc.STC_STYLE_BRACELIGHT: 'Matched braces', wx.stc.STC_STYLE_BRACEBAD: 'Unmatched brace', wx.stc.STC_STYLE_CONTROLCHAR: 'Control characters', wx.stc.STC_STYLE_INDENTGUIDE: 'Indent guide'}""",
         "",
         ]




def getUserConfigFile(app):
    """Get pointer to stc style configuration file.

    Returns filename of stc configuration file.  First looks in
    the per-user configuration directory, and if it doesn't exist,
    copies it from the default configuration directory.
    """
    config = app.getConfigFilePath("stc-styles.rc.cfg")
    if os.path.exists(config):
        return config
    return createUserConfigFile(config)

def createUserConfigFile(config):
    try:
        fh = open(config,'w')
        writeUserConfigFile(fh)
        fh.close()
        return config
    except:
        raise
        #FIXME: when write permissions are denied, such as when
        #this is installed to the site-packages directory and the
        #user isn't root, this will cause a failure when
        #styleDefault tries to save to this file.
        #return None

def writeUserConfigFile(fh):
    for key,defs in common_defs_platforms.iteritems():
        for k, v in common_defs.items():
            if not k in defs:
                defs[k] = v
        dprint("%s=%s" % (key,defs))
        fh.write("%s=%s%s" % (key,defs,os.linesep))
    for line in lines:
        dprint("%s" % line)
        fh.write("%s%s" % (line,os.linesep))

def updateConfigFile(app, mode):
    config=getUserConfigFile(app)
    c = wx.FileConfig(localFilename=config, style=wx.CONFIG_USE_LOCAL_FILE)
    c.SetExpandEnvVars(False)
    try:
        for m in iter(mode):
            addMode(c, m)
    except TypeError:
        addMode(c, mode)
    # Note: the configuration file is written when the variable
    # goes out of scope, so you don't explicitly save it
    
def addMode(c, mode):
    keyword = mode.keyword.lower()
    c.SetPath('')
    c.DeleteGroup(keyword)
    c.SetPath(keyword)
    dprint("[%s]" % keyword)
    text=eval(repr(mode.settings.sample_file))
    dprint("displaysrc = %s" % text)
    c.Write('displaysrc', text)
    c.Write('braces', mode.settings.stc_boa_braces)
    c.WriteInt('lexer', mode.settings.stc_lexer)
    c.Write('keywords', mode.settings.stc_keywords)
    c.Write('styleidnames', str(mode.settings.stc_boa_style_names))

    c.SetPath('')
    c.DeleteGroup("style.%s" % keyword)
    c.SetPath("style.%s" % keyword)
    dprint("[style.%s]" % keyword)
    for num, style in mode.settings.stc_lexer_styles.iteritems():
        if isinstance(style,int):
            # style can be an int, which means it is just copying from
            # another style.
            if style in mode.settings.stc_lexer_styles:
                style = mode.settings.stc_lexer_styles[style]
            elif style in mode.settings.stc_lexer_default_styles:
                style = mode.settings.stc_lexer_default_styles[style]
            else:
                # skip if it doesn't appear in either dict
                continue
        dprint("%s = %s" % ("style.%s.%03d" % (keyword,num), style.strip()))
        c.Write("style.%s.%03d" % (keyword,num), style.strip())
    for num, style in mode.settings.stc_lexer_default_styles.iteritems():
        if not num in mode.settings.stc_lexer_styles:
            dprint("%s = %s" % ("style.%s.%03d" % (keyword,num), style.strip()))
            c.Write("style.%s.%03d" % (keyword,num), style.strip())
           
    
        

__all__ = ['getUserConfigFile', 'createUserConfigFile', 'writeUserConfigFile',
           'updateConfigFile', 'STCStyleEditor', 'initSTC']
