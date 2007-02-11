#!/usr/bin/env python

# Relatively generic setup.py that should be easily tailorable to
# other python modules.  It gets most of the parameters from the
# packaged module itself, so this file shouldn't have to be changed
# much.

import os,sys,distutils
from distutils.core import setup

if sys.version < '2.3':
    raise SystemExit('Sorry, peppy requires at least Python 2.3 because wxPython does.')

# ignore a warning about large int constants in Python 2.3.*
if sys.version >= '2.3' and sys.version < '2.4':
    import warnings
    warnings.filterwarnings('ignore', "hex/oct constants", FutureWarning)

# python looks in current directory first, so we'll be sure to get our
# freshly unpacked version here.
import peppy

module=peppy

# skip the opening one-line description and grab the first paragraph
# out of the module's docstring to use as the long description.
long_description = ''
lines = module.__doc__.splitlines()
for firstline in range(len(lines)):
    # skip until we reach a blank line
    if len(lines[firstline])==0 or lines[firstline].isspace():
        break
if firstline<len(lines):
    firstline+=1
for lastline in range(firstline,len(lines)):
    # stop when we reach a blank line
    if len(lines[lastline])==0 or lines[lastline].isspace():
        break
long_description = os.linesep.join(lines[firstline:lastline])

##print "Summary:"
##print "package: %s %s" % (module.__name__,str(module.__version__))
##print "description: %s" % module.__description__
##print "long description:"
##print long_description
##print
##print "author: %s" % module.__author__
##print "email: %s" % module.__author_email__
##print "url: %s" % module.__url__
##print "download: %s" % module.__download_url__,
##print

setup(name = module.__name__,
      version = str(module.__version__),
      description = module.__description__,
      long_description = long_description,
      keywords = module.__keywords__,
      license = module.__license__,
      author = module.__author__,
      author_email = module.__author_email__,
      url = module.__url__,
      download_url = module.__download_url__,
      platforms='any',
      scripts=['scripts/peppy'],
      packages=['peppy',
                'peppy.actions',
                'peppy.major_modes',
                'peppy.minor_modes',
                'peppy.nltk_lite',
                'peppy.nltk_lite.chat',
                'peppy.nltk_lite.chat.nltk_lite',
                'peppy.plugins',
                'peppy.pype',
                'peppy.trac'],
      package_data={'peppy': ['icons/*'],
                    },
      
      classifiers=['Development Status :: 3 - Alpha',
                   'Environment :: MacOS X',
                   'Environment :: Win32 (MS Windows)',
                   'Environment :: X11 Applications',
                   'Intended Audience :: Developers',
                   'Framework :: Trac',
                   'License :: OSI Approved :: GNU General Public License (GPL)',
                   'Operating System :: MacOS :: MacOS X',
                   'Operating System :: Microsoft :: Windows',
                   'Operating System :: POSIX',
                   'Operating System :: POSIX :: Linux',
                   'Operating System :: Unix',
                   'Programming Language :: Python',
                   'Topic :: Software Development :: Documentation',
                   'Topic :: Text Editors',
                   'Topic :: Text Editors :: Documentation',
                   ]
      )
