###############################################################################
# Name: Cody Precord                                                          #
# Purpose: SourceControl implementation for Bazaar                            #
# Author: Cody Precord <cprecord@editra.org>                                  #
# Copyright: (c) 2008 Cody Precord <staff@editra.org>                         #
# License: wxWindows License                                                  #
###############################################################################

"""Bazaar implementation of the SourceControl object """

__author__ = "Cody Precord <cprecord@editra.org>"
__revision__ = "$Revision: 867 $"
__scid__ = "$Id: BZR.py 867 2009-05-06 12:10:55Z CodyPrecord $"

#------------------------------------------------------------------------------#
# Imports
import os
import datetime
import re
import time

# Local imports
from SourceControl import SourceControl, DecodeString

#------------------------------------------------------------------------------#

class BZR(SourceControl):
    """ Bazaar source control class """
    name = 'Bazaar'
    command = 'bzr'
    ccache = list()     # Cache of paths that are under bazaar control
    repocache = dict()

    def __repr__(self):
        return 'BZR.BZR()'
        
    def getAuthOptions(self, path):
        """ Get the repository authentication info """
        output = []
        return output
    
    def getRepository(self, path):
        """ Get the repository of a given path """
        if path in self.repocache:
            return self.repocache[path]

        if not os.path.isdir(path):
            root = os.path.split(path)[0]
        else:
            root = path

        while True:
            if not root:
                break

            if os.path.exists(os.path.join(root, '.bzr')):
                break
            else:
                root = os.path.split(root)[0]

        # Cache the repo of this path for faster lookups next time
        self.repocache[path] = root
        return root
    
    def isControlled(self, path):
        """ Is the path controlled by BZR? """
        t1 = time.time()
        # Check for cached paths to speed up lookup
        if path in self.ccache:
            return True

        if not os.path.isdir(path):
            root = os.path.split(path)[0]
        else:
            root = path

        last = False
        while True:
            if os.path.exists(os.path.join(root, '.bzr')):
                # If a containing directory of the given path has a .bzr
                # directory in it run status to find out if the file is being
                # tracked or not.
                retval = False
                out = self.run(root + os.sep, ['status', '-S', path])
                if out:
                    lines = out.stdout.readline()
                    if lines.startswith('?'):
                        fname = lines.split(None, 1)[1].strip()
                        fname = fname.rstrip(os.sep)
                        retval = not path.endswith(fname)
                    else:
                        retval = True
                    self.closeProcess(out)

                if retval:
                    self.ccache.append(path)
                return retval
            elif last:
                break
            else:
                root, tail = os.path.split(root)
                # If tail is None or '' then this has gotten to the root
                # so mark it as the last run
                if not tail:
                    last = True

        return False

    def add(self, paths):
        """ Add paths to the repository """
        root, files = self.splitFiles(paths)
        out = self.run(root, ['add'] + files)
        self.logOutput(out)
        self.closeProcess(out)
        
    def checkout(self, paths):
        """ Checkout files at the given path """
        root, files = self.splitFiles(paths)
        out = self.run(root, ['checkout',], files)
        self.logOutput(out)
        self.closeProcess(out)
        
    def commit(self, paths, message=''):
        """ Commit paths to the repository """
        root, files = self.splitFiles(paths)
        out = self.run(root, ['commit', '-m', message] + files)
        self.logOutput(out)
        self.closeProcess(out)
                                   
    def diff(self, paths):
        """ Run the diff program on the given files """
        root, files = self.splitFiles(paths)
        out = self.run(root, ['diff'] + files)
        self.closeProcess(out)

    def makePatch(self, paths):
        """ Make a patch of the given paths """
        root, files = self.splitFiles(paths)
        patches = list()
        for fname in files:
            out = self.run(root, ['diff', fname])
            lines = [ line for line in out.stdout ]
            self.closeProcess(out)
            patches.append((fname, ''.join(lines)))
        return patches

    def history(self, paths, history=None):
        """ Get the revision history of the given paths """
        if history is None:
            history = []

        root, files = self.splitFiles(paths)
        for fname in files:
            out = self.run(root, ['log', fname])
            logstart = False
            if out:
                for line in out.stdout:
                    self.log(line)
                    if line.strip().startswith('-----------'):
                        logstart = False
                        current = dict(path=fname, revision=None, 
                                       author=None, date=None, log=u'')
                        history.append(current)
                    elif line.startswith('message:'):
                        logstart = True
                    elif logstart:
                        current['log'] += DecodeString(line)
                    elif line.startswith('revno:'):
                        current['revision'] = DecodeString(line.split(None, 1)[-1].strip())
                    elif line.startswith('committer:'):
                        author = line.split(None, 1)[-1]
                        current['author'] = DecodeString(author.strip())
                    elif line.startswith('timestamp:'):
                        date = line.split(None, 1)[-1]
                        current['date'] = self.str2datetime(date.strip())
                    else:
                        pass
            self.logOutput(out)
            self.closeProcess(out)
        return history
    
    def str2datetime(self, tstamp):
        """ Convert a timestamp string to a datetime object """
        parts = tstamp.split()
        ymd = [int(x.strip()) for x in parts[1].split('-')]
        hms = [int(x.strip()) for x in parts[2].split(':')]
        date = ymd + hms
        return datetime.datetime(*date)
        
    def remove(self, paths):
        """ Recursively remove paths from repository """
        root, files = self.splitFiles(paths)
        out = self.run(root, ['remove', '--force'] + files)
        self.logOutput(out)
        
    def status(self, paths, recursive=False, status=dict()):
        """ Get BZR status information from given file/directory """
        codes = {' ':'uptodate', 'N':'added', 'C':'conflict', 'D':'deleted',
                 'M':'modified'}
        root, files = self.splitFiles(paths)
        # -S gives output similar to svn which is a little easier to work with
        out = self.run(root, ['status', '-S'] + files)
        repo = self.getRepository(paths[0])
        relpath = root.replace(repo, '', 1).lstrip(os.sep)
        unknown = list()
        if out:
            for line in out.stdout:
                self.log(line)
                txt = line.lstrip(' +-')

                # Split the status code and relative file path
                code, fname = txt.split(None, 1)
                fname = fname.replace(u'/', os.sep).strip().rstrip(os.sep)
                fname = fname.replace(relpath, '', 1).lstrip(os.sep)
                code = code.rstrip('*')

                # Skip unknown files
                if code == '?':
                    unknown.append(fname)
                    continue

                # Get the absolute file path
                current = dict()

                try:
                    current['status'] = codes[code]
                    status[fname] = current
                except KeyError:
                    pass

            # Find up to date files
            unknown += status.keys()
            for path in os.listdir(root):
                if path not in unknown:
                    status[path] = dict(status='uptodate')

            self.logOutput(out)
        return status

    def update(self, paths):
        """ Recursively update paths """
        root, files = self.splitFiles(paths)
        out = self.run(root, ['update'] + files)
        self.logOutput(out)
            
    def revert(self, paths):
        """ Recursively revert paths to repository version """
        root, files = self.splitFiles(paths)
        if not files:
            files = ['.']
        out = self.run(root, ['revert'] + files)
        self.logOutput(out)

    def fetch(self, paths, rev=None, date=None):
        """ Fetch a copy of the paths' contents """
        output = []
        for path in paths:
            if os.path.isdir(path):
                continue
            root, files = self.splitFiles(path)
            
            options = []
            if rev:
                options.append('-r')
                options.append(str(rev))

            if date:
                # Date format YYYY-MM-DD,HH:MM:SS
                options.append('-r')
                options.append('date:%s' % date)
            
            out = self.run(root, ['cat'] + options + files)
            if out:
                output.append(out.stdout.read())
                self.logOutput(out)
            else:
                output.append(None)
        return output
