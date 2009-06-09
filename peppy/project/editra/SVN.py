#!/usr/bin/env python

"""Subversion implementation of the SourceControl object """

__author__ = "Kevin D. Smith <Kevin.Smith@sixquickrun.com>"
__revision__ = "$Revision: 655 $"
__scid__ = "$Id: SVN.py 655 2008-11-15 00:56:03Z CodyPrecord $"

import re, os, crypto, datetime
from SourceControl import SourceControl, DecodeString

#-----------------------------------------------------------------------------#

class SVN(SourceControl):
    """ Subversion source control class """
    name = 'Subversion'
    command = 'svn'

    def __repr__(self):
        return 'SVN.SVN()'
        
    def getAuthOptions(self, path):
        """ Get the repository authentication info """
        output = []
        options = self.getRepositorySettings(path)
        if options.get('username', ''):
            output.append('--username')
            output.append(options['username'])
        if options.get('password', ''):
            output.append('--password')
            output.append(crypto.Decrypt(options['password'], self.salt))
        return output
    
    def getRepository(self, path):
        """ Get the repository of a given path """
        # Make sure path is under source control
        if not self.isControlled(path):
            return

        # Get the directory of the given path
        if not os.path.isdir(path):
            path = os.path.dirname(path)

        # Check the entries file
        repfile = os.path.join(path, '.svn', 'entries')
        if not os.path.isfile(repfile):
            return

        # Parse entries file for repository
        f = open(repfile, 'r')
        for line in f:
            line = line.strip()
            if line == 'dir':
                for i, line in enumerate(f):
                    if i == 2:
                        f.close()
                        return line.strip()
        else:
            f.close()
    
    def isControlled(self, path):
        """ Is the path controlled by SVN? """
        # If a directory just check if it has a .svn directory
        if os.path.isdir(path):
            if os.path.isfile(os.path.join(path, '.svn', 'entries')):
                return True

        # See if the path is in the entries file
        path, basename = os.path.split(path)
        svndir = os.path.join(path,'.svn')
        if os.path.isdir(svndir):
            try:
                entries = open(os.path.join(svndir,'entries')).read()
                entries = [x.strip().split('\n')[0]
                           for x in entries.split('\x0c') 
                           if x.strip()][1:]
                return basename in entries
            except (IOError, OSError):
                pass
        return False
        
    def add(self, paths):
        """ Add paths to the repository """
        root, files = self.splitFiles(paths)
        if '.' in files:
            root, parent = os.path.split(root)
            if not parent:
                root, parent = os.path.split(root)
            for i, f in enumerate(files):
                files[i] = os.path.join(parent, f)
        out = self.run(root, ['add'] + files)
        self.logOutput(out)
        
    def checkout(self, paths):
        """ Checkout files at the given path """
        root, files = self.splitFiles(paths)
        out = self.run(root, ['checkout', '--non-interactive'] + self.getAuthOptions(root) + files)
        self.logOutput(out)
        
    def commit(self, paths, message=''):
        """ Commit paths to the repository """
        root, files = self.splitFiles(paths)
        out = self.run(root, ['commit', '-m', message, '--non-interactive'] + self.getAuthOptions(root) + files)
        self.logOutput(out)
                                   
    def diff(self, paths):
        """ Run the diff program on the given files """
        root, files = self.splitFiles(paths)
        out = self.run(root, ['diff', '--non-interactive'] + self.getAuthOptions(root) + files)
        self.closeProcess(out)

    def makePatch(self, paths):
        """ Make a patch of the given paths """
        root, files = self.splitFiles(paths)
        patches = list()
        for fname in files:
            out = self.run(root, ['diff', '--non-interactive'] + self.getAuthOptions(root) + [fname])
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
            out = self.run(root, ['log', '--non-interactive'] + \
                                  self.getAuthOptions(root) + [fname])
            pophistory = False
            if out:
                for line in out.stdout:
                    self.log(line)
                    if line.strip().startswith('-----------'):
                        pophistory = True
                        current = {'path':fname}
                        history.append(current)
                        for data in out.stdout:
                            self.log(data)
                            rev, author, date, lines = data.split(' | ')
                            current['revision'] = DecodeString(rev)
                            current['author'] = DecodeString(author)
                            current['date'] = self.str2datetime(date)
                            current['log'] = u''
                            self.log(out.stdout.next())
                            break
                    else:
                        current['log'] += DecodeString(line)
            self.logOutput(out)
            if pophistory:
                history.pop()
        return history
    
    def str2datetime(self, s):
        """ Convert a timestamp string to a datetime object """
        return datetime.datetime(*[int(y) for y in [x for x in re.split(r'[\s+/:-]', s.strip()) if x][:6]])
        
    def remove(self, paths):
        """ Recursively remove paths from repository """
        root, files = self.splitFiles(paths)
        out = self.run(root, ['remove', '--force'] + \
                       self.getAuthOptions(root) + files)
        self.logOutput(out)
        
    def status(self, paths, recursive=False, status=dict()):
        """ Get SVN status information from given file/directory """
        codes = {' ':'uptodate', 'A':'added', 'C':'conflict', 'D':'deleted',
                 'M':'modified'}

        options = ['status', '-v', '--non-interactive']
        if not recursive:
            options.append('-N')

        root, files = self.splitFiles(paths)
        out = self.run(root, options + self.getAuthOptions(root) + files)
        if out:
            for line in out.stdout:
                self.log(line)
                code = line[0]
                if code == '?':
                    continue

                tmp = line[8:].strip().split(' ', 1)
                # svn externals don't have the workrev in the string
                # so skip them
                if len(tmp) != 2:
                    continue

                workrev, line = tmp
                rev, line = line.strip().split(' ', 1)
                author, line = line.strip().split(' ', 1)
                name = line.strip()
                current = status[name] = {}

                try:
                    current['status'] = codes[code]
                except KeyError:
                    pass

            self.logOutput(out)
        return status

    def update(self, paths):
        """ Recursively update paths """
        root, files = self.splitFiles(paths)
        out = self.run(root, ['update', '--non-interactive'] + \
                              self.getAuthOptions(root) + files)
        self.logOutput(out)
            
    def revert(self, paths):
        """ Recursively revert paths to repository version """
        root, files = self.splitFiles(paths)
        if not files:
            files = ['.']

        out = self.run(root, ['revert', '-R'] + files)
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
                if rev[0] == 'r':
                    rev = rev[1:]
                options.append(rev)
            if date:
                options.append('-r')
                options.append('{%s}' % date)
            
            out = self.run(root, ['cat', '--non-interactive'] + \
                                  options + self.getAuthOptions(root) + files)
            if out:
                output.append(out.stdout.read())
                self.logOutput(out)
            else:
                output.append(None)
        return output
        
    def salt(self):
        return '"\x17\x9f/D\xcf'
    salt = property(salt)

#-----------------------------------------------------------------------------#
if __name__ == '__main__':
    svn = SVN()
    svn.add(['/Users/kesmit/pp/editra-plugins/Projects/projects/Icons'])
