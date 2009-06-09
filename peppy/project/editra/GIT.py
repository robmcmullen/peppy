#!/usr/bin/env python
###############################################################################
# Name: GIT.py                                                                #
# Purpose: Interface for the ProjectsPane to work with the GIT source control #
#          system through.                                                    #
# Author: Cody Precord <cprecord@editra.org>                                  #
# Copyright: (c) 2008 Cody Precord <staff@editra.org>                         #
# License: wxWindows License                                                  #
###############################################################################

""" GIT implimentation of the SourceControl object """

__author__ = "Cody Precord <cprecord@editra.org>"
__svnid__ = "$Id: GIT.py 847 2009-04-27 15:41:23Z CodyPrecord $"
__revision__ = "$Revision: 847 $"

#-----------------------------------------------------------------------------#
# Imports
import os
import sys
import datetime
import re

# Local imports
import SourceControl
DecodeString = SourceControl.DecodeString

#-----------------------------------------------------------------------------#
# Globals
UNKPAT = re.compile('#[ \t]+[a-zA-Z0-9]+') # hmmm
RELPAT = re.compile('#[ \t]+\.{1,2}' + re.escape(os.sep)) # relative paths
COMPAT = re.compile('commit [a-z0-9]{40}') # Commit line in log

#-----------------------------------------------------------------------------#

class GIT(SourceControl.SourceControl):
    """Source control implementation to add GIT support to the 
    Projects Plugin.

    """
    name = 'GIT'
    command = 'git'

    def __repr__(self):
        return 'GIT.GIT()'

    def isControlled(self, path):
        """ Is the path controlled by GIT?
        The repository directory is only kept in the root of the
        project so must check recursively from given path to root
        to make sure if it is controlled or not

        """
        root = self.findRoot(path)
        if root is None:
            return False

        # Path is in repo path so now check if it is tracked or not
        for item in self.untrackedFiles(path):
            if path.startswith(item):
                return False
        else:
            return True

    def findRoot(self, path):
        """Find the repository root for given path"""
        root = SourceControl.searchBackwards(path, checkDirectory)

        if root is None:
            return None
        else:
            return root + os.path.sep

    def add(self, paths):
        """Add paths to repository"""
        pjoin = os.path.join
        isdir = os.path.isdir
        for path in paths:
            root, files = self.splitFiles(path, forcefiles=True)
            dirs = sorted([x for x in files if isdir(pjoin(root, x))])
            files = sorted([x for x in files if not isdir(pjoin(root, x))])
            # Add all directories individually first
            for d in dirs:
                out = self.run(root, ['add', '-n', d])
                self.logOutput(out)
            # Add all files
            if files:
                out = self.run(root, ['add'] + files)
                self.logOutput(out)                
        
    def checkout(self, paths):
        """Checkout the given paths"""
        root, files = self.splitFiles(paths, forcefiles=True)
        out = self.run(root, ['clone'] + files)
        self.logOutput(out)
            
    def commit(self, paths, message=''):
        """ Commit all files with message """
        root, files = self.splitFiles(paths)
        out = self.run(root, ['commit', '-m', message] + files)
        self.logOutput(out)
            
    def diff(self, paths):
        """ Perform a diff on the given files in the repository """
        root, files = self.splitFiles(paths)
        out = self.run(root, ['diff'] + files)
        self.logOutput(out)

    def makePatch(self, paths):
        """ Make patches of the given paths """
        root, files = self.splitFiles(paths)
        patches = list()
        for fname in files:
            out = self.run(root, ['diff', '-u'] + [fname])
            lines = [ line for line in out.stdout ]
            self.closeProcess(out)
            patches.append((fname, ''.join(lines)))
        return patches

    def getRepository(self, path):
        """ Get the base of the repository """
        return self.findRoot(path)

    def history(self, paths, history=None):
        """ Get history of the given paths """
        if history is None:
            history = list()
        for path in paths:
            root, files = self.splitFiles(path)
            for fname in files:
                out = self.run(root, ['log', fname])
                if out:
                    for line in out.stdout:
                        self.log(line)
                        if re.match(COMPAT, line.strip()):
                            current = {'path':fname}
                            history.append(current)
                            current['revision'] = DecodeString(line.split()[-1].strip())
                            current['log'] = ''
                        elif line.startswith('Author: '):
                            current['author'] = DecodeString(line.split(' ', 1)[-1])
                        elif line.startswith('Date: '):
                            current['date'] = self.str2datetime(line.split(' ', 1)[-1].strip())
                        else:
                            current['log'] += DecodeString(line)

        # Cleanup log formatting
        for item in history:
            if 'log' in item:
                item['log'] = item['log'].strip()

        return history

    def remove(self, paths):
        """ Recursively remove paths from source control """
        # Reverse paths so that files get deleted first
        for path in reversed(sorted(paths)):
            root, files = self.splitFiles(path)           
            out = self.run(root, ['rm', '-r', '-f'] + files)
            self.logOutput(out)

    def str2datetime(self, datestr):
        """Convert a date string to a datetime object"""
        parts = datestr.split()[1:]
        months =  ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                   'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        month = months.index(parts[0].lower()) + 1
        day = int(parts[1])
        hms = [int(x) for x in parts[2].split(":")]
        year = int(parts[3])
        return datetime.datetime(year, month, day, *hms)

    def status(self, paths, recursive=False, status=None):
        """Get the status of all given paths """
        # NOTE: uptodate files are not listed in output of status
        codes = {' ':'uptodate', 'N':'added', 'C':'conflict', 'D':'deleted',
                 'M':'modified'}

        def modpath(fname):
            fname = fname.strip().rstrip(os.sep)
            fname = fname.replace(relpath, '', 1).lstrip(os.sep)
            return fname

        root, files = self.splitFiles(paths)
        out = self.run(root, ['status'] + files)
        repo = self.findRoot(root)
        relpath = root.replace(repo, '', 1).lstrip(os.sep)
        unknown = list()
        if out:
            # Check to see that the directory is actually being managed by git.
            # It is possible that the directory is below a git root but not
            # under git's control (for example a build directory).
            for line in out.stderr:
                if "did not match any file" in line:
                    return status
            
            save = []
            for line in out.stdout:
                # save the stdout so it can be parsed again below
                save.append(line)
                
                self.log(line)
                current = dict()
                line = line.lstrip('#').strip()
                if line.startswith('new file:'):
                    fname = line.replace('new file:', '', 1).strip()
                    status[modpath(fname)] = dict(status='added')
                elif line.startswith('modified:'):
                    fname = line.replace('modified:', '', 1).strip()
                    status[modpath(fname)] = dict(status='modified')
                elif line.startswith('deleted:'):
                    fname = line.replace('deleted:', '', 1).strip()
                    status[modpath(fname)] = dict(status='deleted')
                else:
                    continue
            
            # Some untracked files are listed in the git output and don't show
            # up in the git-ls-files below.  Note that the files are relative
            # to the root directory and not the repository directory.
            untracked = self.parseOutputForUntrackedFiles(repo, save)
            for fname in untracked:
                relname = fname.replace(repo, '', 1).lstrip(os.sep)
                unknown.append(relname)

            self.logOutput(out)
            self.closeProcess(out)

        # Find other untracked files that don't show up in the git-status output
        out = self.run(root, ['ls-files', '--others', '-t'] + files)
        if out:
            for line in out.stdout:
                self.log(line)
                if len(line):
                    fname = line.lstrip('?').strip()
                    unknown.append(modpath(fname))
            self.logOutput(out)

        # Find up to date files
        unknown += status.keys()
        for path in os.listdir(root):
            if path not in unknown:
                status[path] = dict(status='uptodate')

        return status

    def untrackedFiles(self, path):
        """ Find the untracked files under the given path """
        root = self.splitFiles(path)[0]
        repo = self.findRoot(root)
        out = self.run(root, ['status'], mergeerr=True)
        unknown = list()
        if out:
            unknown = self.parseOutputForUntrackedFiles(repo, out.stdout)
        return unknown
    
    def parseOutputForUntrackedFiles(self, repo, output):
        """Parse git-status output and return all untracked files"""
        unknown = list()
        start_unknown = False
        for line in output:
            if start_unknown:
                line = line.strip()
                if re.search(UNKPAT, line):
                    tmp = line.split(u"#", 1)
                    tmp = os.path.normpath(os.path.join(repo, tmp[-1].strip()))
                    unknown.append(tmp)
                elif re.search(RELPAT, line):
                    tmp = line.split(u"#", 1)[-1].strip()
                    if tmp == u'.' + os.sep and repo not in unknown:
                        unknown.append(repo)
                    else:
                        btrack = tmp.count(u"..")
                        rpath = repo.rsplit(os.sep, btrack)[0]
                        npath = tmp.split(os.sep, btrack)[-1]
                        unknown.append(os.path.join(rpath, npath))
                # TODO: There are still some bugs in this when the call
                #       comes from the isControlled method. Workaround fix
                #       in UI based on icon status. This still should/needs
                #       to be fixed though...
                continue
            elif line.startswith('# Untracked files:'):
                start_unknown = True
            else:
                pass
        return unknown

    def update(self, paths):
        """ Recursively update paths """
        for path in paths:
            root, files = self.splitFiles(path)
            out = self.run(root, ['pull'] + files)
            self.logOutput(out)
            
    def revert(self, paths): 
        """ Revert paths to repository versions """
        for path in paths:
            root, files = self.splitFiles(path, forcefiles=True, 
                                          type=self.TYPE_FILE)
            for fname in files:
                out = self.run(root, ['checkout'] + fname)
                self.logOutput(out)

    def fetch(self, paths, rev=None, date=None):
        """ Fetch a copy of the paths from the repository """
        output = []
        for path in paths:
            if os.path.isdir(path):
                continue
            root, files = self.splitFiles(path)
            repo = self.findRoot(path)

            # Adjust file names
            files = [ os.path.join(root, f).replace(repo, u'', 1).strip(os.path.sep) for f in files ]
            if rev:
                options = rev + u':%s'
            else:
                options = 'HEAD:%s'

            if date:
                self.logOutput("[git] date not currently supported")

            for f in files:
                out = self.run(root, ['show'] + [options % f])
                if out:
                    content = out.stdout.read() 
                    self.logOutput(out)
                    if content.strip():
                        output.append(content)
                    else:
                        output.append(None)
                else:
                    output.append(None)
        return output

#-----------------------------------------------------------------------------#
# Utility functions
def checkDirectory(directory):
    """Checks if a given directory is the git head"""
    if os.path.isdir(directory):
        if os.path.exists(os.path.join(directory, '.git', 'HEAD')):
            return True
    else:
        return False

#-----------------------------------------------------------------------------#

if __name__ == '__main__':
    git = GIT()
    print git.status(['.'], recursive=True)
    print git.history(['setup.py'])
