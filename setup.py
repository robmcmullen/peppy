#!/usr/bin/env python

# Relatively generic setup.py that should be easily tailorable to
# other python modules.  It gets most of the parameters from the
# packaged module itself, so this file shouldn't have to be changed
# much.

import os, sys, distutils, glob, zlib
from cStringIO import StringIO
from distutils.core import setup, Extension, Command
from distutils.command.build_py import build_py as _build_py
from distutils import util
platform = util.get_platform()

if sys.version < '2.5':
    raise SystemExit('Sorry, peppy requires at least Python 2.5.')

# Load the root module that contains the version info and descriptive text
prog = 'peppy'
module = __import__(prog)

version = module.__version__



# crunch_data was removed from img2py as of wxPython 2.8.8
def crunch_data(data, compressed):
    # compress it?
    if compressed:
        data = zlib.compress(data, 9)

    # convert to a printable format, so it can be in a Python source file
    data = repr(data)

    # This next bit is borrowed from PIL.  It is used to wrap the text intelligently.
    fp = StringIO()
    data += " "  # buffer for the +1 test
    c = i = 0
    word = ""
    octdigits = "01234567"
    hexdigits = "0123456789abcdef"
    while i < len(data):
        if data[i] != "\\":
            word = data[i]
            i += 1
        else:
            if data[i+1] in octdigits:
                for n in xrange(2, 5):
                    if data[i+n] not in octdigits:
                        break
                word = data[i:i+n]
                i += n
            elif data[i+1] == 'x':
                for n in xrange(2, 5):
                    if data[i+n] not in hexdigits:
                        break
                word = data[i:i+n]
                i += n
            else:
                word = data[i:i+2]
                i += 2

        l = len(word)
        if c + l >= 78-1:
            fp.write("\\\n")
            c = 0
        fp.write(word)
        c += l

    # return the formatted compressed data
    return fp.getvalue()

class build_extra_peppy(_build_py):
    def generate_printable_icon(self, filename, remove, out):
        if filename.endswith('.py') or filename.endswith('.pyc'):
            return
        fh = open(filename, 'rb')
        data = fh.read()
        printable = crunch_data(data, False)
        # Change all windows backslashes to forward slashes
        if filename.startswith(remove):
            filename = filename[len(remove):]
        filename = filename.replace('\\', '/')
        out.write("'%s':\n%s,\n" % (filename, printable))

    def process_icons(self, path, remove, out):
        files = glob.glob('%s/*' % path)
        for path in files:
            if os.path.isdir(path):
                self.process_icons(path, remove, out)
            else:
                self.generate_printable_icon(path, remove, out)

    def create_iconmap(self, filename="peppy/iconmap.py"):
        print self.build_lib
        out = StringIO()
        out.write("""\
from peppy.lib.iconstorage import *

icondict = {
""")
        self.process_icons('peppy/icons', 'peppy/', out)
        out.write("""\
}

addIconsFromDict(icondict)
""")
        pathname = os.path.join(self.build_lib, filename)
        fh = open(pathname, 'wb')
        fh.write(out.getvalue())
        print("created %s" % pathname)
        
    def build_package_data(self):
        self.create_iconmap()
        _build_py.build_package_data(self)


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
    print "packages = %s" % packages
    return packages
packages = findPackages(prog)


# Create the list of scripts to be installed in /usr/bin
if sys.platform.startswith('win'):
    scripts = ['scripts/peppy.bat']
else:
    # Can't include peppy.py at the root level of the distribution or as one
    # of the scripts because python ends up trying to include peppy.py on an
    # "import peppy" statement rather than looking for the peppy directory
    # in site-packages.  So, on unix it is installed as 'peppy' without an
    # extension to work around this.
    if os.path.exists('run.py') and not os.path.exists('scripts/peppy'):
        import shutil
        shutil.copy('run.py', 'scripts/peppy')
    scripts = ['scripts/peppy']


# Any files to be installed outsite site-packages are declared here
data_files = []


# When building a py2exe version of the code, there are some extra files that
# must be included in the distribution list.  This should ONLY be used when
# building py2exe binaries, and not when running a "python setup.py install"
# because this py2exe build process has to put some extra files in special
# places that would end up in invalid locations in C:/Python25/
USE_PY2EXE = False

# FIXME: What's the correct way to tell which build command is being called?
for arg in sys.argv:
    if arg == "py2exe":
        # Support for bundling the application with py2exe
        try:
            import py2exe
            USE_PY2EXE = True
        except:
            pass
        break

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
    
    # py2exe ignores package_data, so the editra files loaded on demand by the
    # style editor need to be included in the data_files entry
    data_files.append(("peppy/editra/styles", glob.glob("peppy/editra/styles/*.ess")))

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
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
<assemblyIdentity
    version="0.64.1.0"
    processorArchitecture="x86"
    name="Controls"
    type="win32"
/>
<description>Peppy - (ap)Proximated (X)Emacs Powered by Python</description>
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
<trustInfo xmlns="urn:schemas-microsoft-com:asm.v3">
    <security>
        <requestedPrivileges>
            <requestedExecutionLevel
                level="AsInvoker"
                uiAccess="false"/>
        </requestedPrivileges>
    </security>
</trustInfo>
</assembly>
"""

# Define any extensions in setup_extensions.py
try:
    from setup_extensions import *
except:
    ext_modules = None


setup(cmdclass={'build_py': build_extra_peppy,},
      name = prog,
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
      zip_safe = False,
      scripts = scripts,
      packages = packages,
      package_data = {
          'peppy.plugins': ['*.peppy-plugin' ],
          'peppy.plugins.eggs': ['*.egg' ],
          'peppy.project': ['*.peppy-plugin' ],
          'peppy.hsi': ['*.peppy-plugin' ],
          'peppy.major_modes': ['*.peppy-plugin' ],
          'peppy.editra': ['styles/*.ess'],
          },
      ext_modules = ext_modules,

      # FIXME: the excludes option still doesn't work.  py2exe still
      # picks up a bunch of unnecessary stuff that I'm trying to get
      # rid of.
      options = {'py2exe': {'unbuffered': True,
                            'optimize': 2,
                            'excludes': ['Tkinter', 'Tkconstants', 'tcl', '_tkinter', 'numpy.f2py', 'matplotlib', 'doctest'],
                            }
                 },
      windows = [{"script": "py2exe/peppy.py",
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
