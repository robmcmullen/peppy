# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""
Main application class.
"""

import os, sys
import __builtin__

import wx

from configprefs import *
from debug import *

def i18n_gettext(path):
    import gettext

    trans = gettext.GNUTranslations(open(path, 'rb'))
    __builtin__._ = trans.ugettext

def init_i18n(path, lang, catalog):
    gettext_path = os.path.join(path, lang, catalog)
    if os.path.exists(gettext_path):
        i18n_gettext(gettext_path)
    else:
        __builtin__._ = str

def init(options):
    """One time initialization before startup.

    Initialize any values that are needed before the bulk of the code
    is loaded.  Currently, the i18n needs to be loaded before anything
    else.
    """
    c=HomeConfigDir(options.confdir)
    #dprint("found home dir=%s" % c.dir)

    basedir = os.path.dirname(os.path.dirname(__file__))

    try:
        fh = c.open("i18n.cfg")
        cfg = ConfigParser()
        cfg.optionxform = str
        cfg.readfp(fh)
        defaults = cfg.defaults()
    except:
        defaults = {}
    
    locale = defaults.get('locale', 'en')
    path = defaults.get('dir', os.path.join(basedir, 'locale'))

    init_i18n(path, locale, options.i18n_catalog)
    

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
    parser.add_option("--config-name", action="store", dest="confdir", default="peppy")
    parser.add_option("--i18n-catalog", action="store", dest="i18n_catalog", default="peppy")
    parser.add_option("--sample-config", action="store_true", dest="sample_config", default=False)
    (options, args) = parser.parse_args()
    #print options

    init(options)

    from mainapp import run

    if options.profile:
        import profile
        profile.run('run()','profile.out')
    else:
        run(options,args)



if __name__ == "__main__":
    main()
