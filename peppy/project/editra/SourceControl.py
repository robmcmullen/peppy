#!/usr/bin/env python
 
"""
Generic Source Control Object

The SourceControl object creates an API to invoke source control commands
from Python rather than the command-line.  All of the sub-process commands
are handled by the SourceControl object so that logging and sub-process
settings are centralized.  This is an abstract class.  Subclasses must
implement all of the methods at the end of this class definition that simply
raise a NotImplementedError.  Each of the methods to be overridden have
a docstring at the top describing what it needs to do.

The concrete subclasses of SourceControl also need to define two variables
in the class: command and name.  Command is the default command line utility
that is used for all source control operations (i.e., cvs, svn, etc.).  
This can also be overridden by the user in the config dialog.  The name
attribute is simply a string that is displayed in the config dialog when
changing settings.  For example, 'Subversion' would be for the subversion
system, 'CVS' for the CVS system, etc.

If you have created a new source control system subclass, it can be added
to the Projects pane in the ConfigDialog package.  Simply import the 
new subclass and add it in the ConfigData's __init__ method using 
the addSCSystem method.

See Also: CVS.py, GIT.py, and SVN.py

"""

__author__ = "Kevin D. Smith <Kevin.Smith@sixquickrun.com>"
__revision__ = "$Revision: 751 $"
__scid__ = "$Id: SourceControl.py 751 2009-01-30 05:41:59Z CodyPrecord $"

#-----------------------------------------------------------------------------#
# Imports
import os
import locale
import codecs
import types
import fnmatch
import subprocess
import sys
try: import wx
except: pass

try: sorted
except:
    def sorted(arr):
        arr = list(arr)
        arr.sort()
        return arr

try: reversed
except:
    def reversed(arr):
        arr = list(arr)
        arr.reverse()
        return arr

#-----------------------------------------------------------------------------#

if sys.platform.lower().startswith('win'):            
    STARTUPINFO = subprocess.STARTUPINFO()
    STARTUPINFO.dwFlags |= subprocess.STARTF_USESHOWWINDOW
else:
    STARTUPINFO = None

#-----------------------------------------------------------------------------#

class SourceControl(object):
    """Source control representation base class"""
    TYPE_FILE = 1
    TYPE_DIRECTORY = 2
    TYPE_ANY = 3   

    filters = []

    # Default command
    command = ''

    # Name to use in config panel
    name = ''  

    # Username, password, and environments for given repositories
    repositories = {}
    
    def getRelativePaths(self, paths):
        """
        Find the common root to the given list of paths
        
        Required Arguments:
        paths -- list of paths to find the root of
        
        Returns: two element tuple.  The first element is a string containing
            the common root directory.  The second element is a list of 
            relative paths to the files in the original path list
        
        """
        if not paths:
            return '', []
            
        if len(paths) == 1:
            if os.path.isdir(paths[0]):
                return paths[0], ['.']
            else:
                return os.path.dirname(paths[0]), [os.path.basename(paths[0])]
        
        paths = list(reversed(sorted([x.split(os.sep) for x in paths])))
        # Remove empty strings caused by trailing '/'
        for path in paths:
            while path and not path[-1]:
                path.pop()

        # Find the common prefix
        end = False
        root = []                
        while paths[0]:
            segment = paths[0][0]
            for path in paths:
                if not path:
                    end = True
                    break
                elif path[0] != segment:
                    end = True
                    break
            if end:
                break

            root.append(segment)
            for path in paths:
                path.pop(0)
                
        # Create paths from lists
        addRoot = False
        if not root[0]:
            addRoot = True
        root = os.path.join(*root)
        if addRoot:
            root = os.path.sep + root
            
        for i, path in enumerate(paths):
            if path:
                paths[i] = os.path.join(*path)
            else:
                paths[i] = '.'
                
        return root, paths

    def splitFiles(self, paths, forcefiles=False, type=None, topdown=True):
        """ 
        Split path into a working directory and list of files 
        
        Required Arguments:
        paths -- path or list of paths to split
        forcefiles -- boolean indicating if the list of recursive files
            should be returned explicitly
        type -- type of files/directories to return
        topdown -- boolean indicating if the files should be listed
            before directories
            
        Returns: two element tuple where the first element is the 
            starting directory and the second element is a list of the
            files in that directory tree.  The file list will be
            empty if forcefiles is False and the path passed in is a 
            directory.
        
        """
        # Multiple paths were passed in
        if isinstance(paths, (list, tuple)):
            newpaths = []
            for path in paths:
                root, files = self.splitFiles(path, forcefiles=forcefiles,
                                              type=type, topdown=topdown)
                if files:
                    for f in files:
                        newpaths.append(os.path.join(root, f))
                else:
                    newpaths.append(root)
            return self.getRelativePaths(newpaths)
        
        # Single path was passed in
        path, root, files = paths, paths, []
        if not os.path.isdir(path):
            root, files = os.path.split(path)
            files = self.filterPaths([files])
        elif forcefiles:
            files = self.getPathList([path], type, topdown)
        return root, files

    def addRootOption(self, directory, options):
        """ Add the repository root option to the command """
        return options

    def getRepositorySettings(self, path):
        """ Get the settings from all configured repository paths """
        settings = {}
    
        # Load default environment
        if 'Default' in self.repositories:
            recursiveupdate(settings, self.repositories['Default'])

        # Load environment for repository
        repository = self.getRepository(path)
        if repository:
            for key, value in sorted(self.repositories.items()):
                if key == 'Default':
                    continue

                if repository.startswith(key):
                    recursiveupdate(settings, value)
        return settings

    def run(self, directory, options, env=dict(), mergeerr=False):
        """ Run a CVS command in the given directory with given options """
        self.log('%s %s %s\n' % (directory, self.command, ' '.join(options)))
        environ = os.environ.copy()
        # Add repository settings        
        environ.update(self.getRepositorySettings(directory).get('env', {}))
        # Merge passed in environment
        environ.update(env)
        try:
            stderr = subprocess.PIPE
            if mergeerr:
                stderr = subprocess.STDOUT
            return subprocess.Popen([self.command] +
                                    self.addRootOption(directory, options),
                                    cwd=directory,
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=stderr,
                                    env=environ,
                                    startupinfo=STARTUPINFO)
        except OSError: 
            pass
        
    def filterPaths(self, paths):
        """" Filter out paths based on class filters """
        newpaths = []
        for path in paths:
            if path.endswith('\r'):
                continue
            bailout = False
            for pattern in self.filters:
                if fnmatch.fnmatchcase(path, pattern):
                    bailout = True
                    break
            if not bailout:
                newpaths.append(path)
        return newpaths

    def getPathList(self, paths, type=None, topdown=True):
        """ 
        Return the full list of files and directories 
        
        If the list of paths contains a file, that file is added to
        the output list.  If the path is a directory, that directory
        and everything in that directory is added recursively.

        Required Arguments:
        paths -- list of file paths
        type -- constant indicating which type of objects to return
            Can be one of: TYPE_FILE, TYPE_DIRECTORY, TYPE_ANY
        topdown -- topdown argument passed to os.walk
        
        """
        newpaths = []
        if type is None:
            type = self.TYPE_ANY

        for path in paths:
            if os.path.isdir(path):
                if not path.endswith(os.path.sep):
                    path += os.path.sep
                # Add current directory if parent directory is CVS controlled
                if self.isControlled(os.path.join(path, '..')):
                    if type != self.TYPE_FILE:
                        newpaths.append(os.path.basename(path))
                # Add all files/directories recursively
                for root, dirs, files in os.walk(path, topdown):
                    root = root[len(path):]
                    if type != self.TYPE_FILE:
                        for dirname in dirs:
                            newpaths.append(os.path.join(root, dirname))
                    if type != self.TYPE_DIRECTORY:
                        for fname in files:
                            newpaths.append(os.path.join(root, fname))
            elif type != self.TYPE_DIRECTORY:
                newpaths.append(os.path.basename(path))
        return self.filterPaths(newpaths)

    def log(self, s):
        """Log output either to Editra's log or stdout"""
        try:
            wx.GetApp().GetLog()('[projects]' + s)
        except:
            sys.stdout.write(s)

    def logOutput(self, p, close=True):
        """ Read and print stdout/stderr """
        if not p:
            return

        flush = write = None
        try: 
            write = wx.GetApp().GetLog()
        except:
            write = sys.stdout.write
            try: flush = sys.stdout.flush
            except AttributeError: pass

        while write:
            err = out = None
            if p.stderr:
                err = p.stderr.readline()
                if err:
                    write('[projects][err] ' + err)
                    if flush:
                        flush()

            if p.stdout:
                out = p.stdout.readline()
                if out:
                    write('[projects][info] ' + out)
                    if flush:
                        flush()

                if not err and not out:
                    return

        if close:
            self.closeProcess(p)

    def closeProcess(self, p):
        """Close a processes pipes"""
        try: p.stdout.close()
        except: pass
        try: p.stderr.close()
        except: pass
        try: p.stdin.close()
        except: pass

#
# Methods that need to be overridden in subclasses        
#
        
    def getRepository(self, path):
        """
        Return the repository for the given path
        
        Required Arguments:
        path -- absolute path to the file or directory
        
        Returns: string containing the repository for the given file
            or directory
        
        """    
        raise NotImplementedError
    
    def isControlled(self, path):
        """ 
        Is the path controlled by source control? 
        
        Required Arguments:
        path -- absolute path to file or directory
        
        Returns: boolean indicating whether or not the file or 
            directory is under source control
        
        """
        raise NotImplementedError
        
    def add(self, paths):
        """ 
        Add paths to the repository 
        
        Required Arguments:
        paths -- list of paths to add to the repository
        
        Returns: nothing
        
        """
        raise NotImplementedError
        
    def checkout(self, paths):
        """ 
        Checks out paths from repository
        
        Required Arguments:
        paths -- list of paths to check out from repository
        
        Returns: nothing
        
        """
        raise NotImplementedError
        
    def commit(self, paths, message=''):
        """ 
        Commit paths to the repository 
        
        Required Arguments:
        paths -- list of paths to commit
        
        Keyword Arguments:
        message -- text for log message
        
        Returns: nothing
        
        """
        raise NotImplementedError
                                   
    def diff(self, paths):
        """
        Diff paths to repository revisions
        
        Required Arguments:
        paths -- list of paths to diff
        
        Returns: nothing
        
        """
        raise NotImplementedError

    def makePatch(self, path):
        """
        Make a patch of the given path against the working revision
        
        Required Arguments:
        path -- path of file to make patch of
        
        Return: list of tuples [(filename, patch text)]


        """
        raise NotImplementedError

    def history(self, paths, history=None):
        """
        Retrieve history of specified paths
        
        Required Arguments:
        paths -- list of paths to retrive the history of
        
        Keyword Arguments:
        history -- list to store the history elements in
        
        Returns: list of dictionaries.  Each dictionary should have at least
            five keys: path (absolute path of the file), revision
            (revision name/number), author (name of person to commit),
            date (string containing date of commit), and log
            (log message of commit).  Other keys may be present, but 
            are not used.
        
        """
        raise NotImplementedError
        
    def remove(self, paths):
        """ 
        Recursively remove paths from repository 
        
        Required Arguments:
        paths -- list of paths to remove.  These can be files or directories.
            If a directory is specified, it is removed recursively.
            
        Returns: nothing
        
        """
        raise NotImplementedError
        
    def status(self, paths, recursive=False, status=None):
        """ 
        Get SVN status information from given paths
        
        Required Arguments:
        paths -- list of paths to get status of.
        
        Keyword Arguments:
        recursive -- by default, only files/directories in the current
            directory are queried.  If recursive is set to True, then
            the directory status should be recursive.
         status -- dictionary to use to hold status information.  
         
         Returns: dictionary containing status information.  The keys
             in the status dictionary are the names of the files/directories
             withinin the given path.  If the given path is a directory, the keys
             will be the names of the files/directories in that directory.
             If the path is a file, the key is the name of that file.  These
             are just filenames, not absolute paths.
        
             Each value in the status dictionary is also a dictionary.
             Only one key is required: 'status'.  The value in the 'status'
             key is one of: 'uptodate', 'added', 'conflict', 'deleted', or 
             'modified'.
             
             Other keys may be used in the future for added information.
        
        """
        raise NotImplementedError

    def update(self, paths):
        """ 
        Recursively update paths 
        
        Required Arguments:
        paths -- list of paths to update to the repository revision.  
           This update should always be recursive.
        
        Returns: nothing
        
        """
        raise NotImplementedError
            
    def revert(self, paths):
        """ 
        Recursively revert paths to repository version 
        
        Required Arguments:
        paths -- list of paths to revert.  This reversion should be done
            recursively.
            
        Returns: nothing
        
        """
        raise NotImplementedError
            
    def fetch(self, paths, rev=None, date=None):
        """ 
        Fetch a copy of the paths' contents 
        
        Required Arguments:
        paths -- list of paths to fetch the contents of
        
        Keyword Arguments:
        rev -- name/number of revision to fetch rather than current
            repository revision
        date -- date of revision to fetch
        
        Returns: list of strings where each string contains the contents
           of a given path.  If the path could not be retrieved, the value
           of that list item should be None.
        
        """
        raise NotImplementedError

def recursiveupdate(dest, src):
    """ Recursively update dst from src """
    for key, value in src.items():
        if key in dest:
            if isinstance(value, dict):
                recursiveupdate(dest[key], value)
            else:
                dest[key] = value
        else:
            dest[key] = value
    return dest

#-----------------------------------------------------------------------------#

def searchBackwards(path, callback):
    """Walk the path backwards looking for the root"""
    # Make sure there's no trailing slash, and the path is sane.
    # TODO should we use os.realpath instead?
    potentialRoot = os.path.normpath(path)
    while 1:
        if callback(potentialRoot):
            # We found it.
            return potentialRoot

        head, tail = os.path.split(potentialRoot)

        if not tail:
            # We checked up to the drive and found nothing.
            break

        # Check back one level.
        potentialRoot = head

    return None

#-----------------------------------------------------------------------------#

def DecodeString(string, encoding=None):
    """Decode the given string to Unicode using the provided
    encoding or the DEFAULT_ENCODING if None is provided.
    @param string: string to decode
    @keyword encoding: encoding to decode string with

    """
    if not encoding:
        encoding =  locale.getpreferredencoding()

    if not isinstance(string, types.UnicodeType):
        try:
            rtxt = codecs.getdecoder(encoding)(string)[0]
        except Exception, msg:
            rtxt = string
        return rtxt
    else:
        # The string is already unicode so just return it
        return string

#-----------------------------------------------------------------------------#

if __name__ == '__main__':
    sc = SourceControl()
    print sc.getRelativePaths(['/u/foo/a', '/u/foo/a/b/c.html'])
    print sc.getRelativePaths(['/u/foo/a/c/d.c', '/u/foo/a/b/c.html'])
    print sc.getRelativePaths([])
    print sc.getRelativePaths(['/u/foo/a/b'])
