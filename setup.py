#!/usr/bin/env python

# Relatively generic setup.py that should be easily tailorable to
# other python modules.  It gets most of the parameters from the
# packaged module itself, so this file shouldn't have to be changed
# much.

import os,sys,distutils, glob
from distutils.core import setup, Extension

if sys.version < '2.5':
    raise SystemExit('Sorry, peppy requires at least Python 2.5.')

# Load the root module that contains the version info and descriptive text
prog = 'peppy'
module = __import__(prog)

version = module.__version__

# Find the long description based on the doc string of the root module
def findLongDescription():
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
    return " ".join(lines[firstline:lastline])
long_description = findLongDescription()


# Determine the list of pure-python packages
def findPackages(name):
    packages = []
    # find packages to be installed
    path = os.path.abspath(name)
    def addmodules(arg, dirname, names):
        if '__init__.py' in names:
            prefix = os.path.commonprefix((path, dirname))
            mod = "%s%s" % (name, dirname[len(prefix):].replace(os.sep,'.'))
            if mod not in packages:
                packages.append(mod)
    os.path.walk(path, addmodules, None)
    #print "packages = %s" % packages
    return packages
packages = findPackages(prog)


# Create the list of scripts to be installed in /usr/bin
scripts = ['scripts/peppy']
from distutils import util
if util.get_platform()[:3] == 'win':
    # or if we're on windows, use batch files instead
    scripts = [script + '.bat' for script in scripts]


# Create the data files for Editra's styling stuff
data_files = [("peppy/editra/styles", glob.glob("peppy/editra/styles/*.ess")),
              ("peppy/editra/tests", glob.glob("peppy/editra/tests/*")),
              ("peppy/editra/syntax", glob.glob("peppy/editra/syntax/*.*"))]


# Support for bundling the application with py2exe
try:
    import py2exe
    USE_PY2EXE = True
except:
    USE_PY2EXE = False
    
if USE_PY2EXE:
    if os.path.exists('peppy/lib/stcspellcheck.py'):
        # Add pyenchant dictionaries to data files if we find the STCSpellCheck
        # code and we're on windows
        print("Found spell checker; including pyenchant")
        try:
            import enchant
            data_files.extend(enchant.utils.win32_data_files())
        except ImportError:
            pass

    # py2exe can't scan inside zipped eggs to find dependencies.  All plugins
    # must be unpacked into a directory in order for py2exe to find any
    # additional dependencies that are in the eggs but not in the main
    # application
    packages.extend(findPackages('eggs'))
    
    try:
        import peppy.py2exe_plugins_count
        packages.extend(peppy.py2exe_plugins_count.setuptools_packages)
    except ImportError:
        # skip it if it can't find import the file
        pass
    except AttributeError:
        # skip it if there are no setuptools packages listed in the file
        pass

# Manifest file to allow py2exe to use the winxp look and feel
manifest = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1"
manifestVersion="1.0">
<assemblyIdentity
    version="0.64.1.0"
    processorArchitecture="x86"
    name="Controls"
    type="win32"
/>
<description>Your Application</description>
<dependency>
    <dependentAssembly>
        <assemblyIdentity
            type="win32"
            name="Microsoft.Windows.Common-Controls"
            version="6.0.0.0"
            processorArchitecture="X86"
            publicKeyToken="6595b64144ccf1df"
            language="*"
        />
    </dependentAssembly>
</dependency>
</assembly>
"""


setup(name = prog,
      version = version,
      description = module.__description__,
      long_description = long_description,
      keywords = module.__keywords__,
      license = module.__license__,
      author = module.__author__,
      author_email = module.__author_email__,
      url = module.__url__,
      download_url = module.__download_url__,
      platforms = 'any',
      scripts = scripts,
      packages = packages,

      # FIXME: the excludes option still doesn't work.  py2exe still
      # picks up a bunch of unnecessary stuff that I'm trying to get
      # rid of.
      options = {'py2exe': {'unbuffered': True,
                            'optimize': 2,
                            'excludes': ['Tkinter', 'Tkconstants', 'tcl', '_tkinter', 'numpy.f2py', 'matplotlib', 'doctest'],
                            }
                 },
      windows = [{"script": "peppy.py",
                  "other_resources": [(24,1,manifest)],
                  "icon_resources": [(2, "../graphics/peppy48.ico")],
                  }
                 ],
      data_files = data_files,
      classifiers=['Development Status :: 3 - Alpha',
                   'Environment :: MacOS X',
                   'Environment :: Win32 (MS Windows)',
                   'Environment :: X11 Applications',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: GNU General Public License (GPL)',
                   'Operating System :: MacOS :: MacOS X',
                   'Operating System :: Microsoft :: Windows',
                   'Operating System :: POSIX',
                   'Operating System :: POSIX :: Linux',
                   'Operating System :: Unix',
                   'Programming Language :: Python',
                   'Topic :: Software Development :: Documentation',
                   'Topic :: Text Editors',
                   ]
      )
