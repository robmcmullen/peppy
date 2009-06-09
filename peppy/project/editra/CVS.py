#!/usr/bin/env python

""" CVS impimentation of SourceControl object """

__author__ = "Kevin D. Smith <Kevin.Smith@sixquickrun.com>"
__revision__ = "$Revision: 595 $"
__scid__ = "$Id: CVS.py 595 2008-09-01 03:21:13Z CodyPrecord $"

import re, os, datetime
from SourceControl import SourceControl, DecodeString

class CVS(SourceControl):
    """ Concurent Versioning System implementation for the
    Projects Plugin.

    """

    name = 'CVS'
    command = 'cvs'
    
    def __repr__(self):
        return 'CVS.CVS()'
    
    def getRepository(self, path):
        """ Get the repository of a given path """
        if not self.isControlled(path):
            return
        if not os.path.isdir(path):
            path = os.path.dirname(path)
        repfile = os.path.join(path, 'CVS', 'Root')
        if not os.path.isfile(repfile):
            return
        return open(repfile, 'r').read().strip()
    
    def isControlled(self, path):
        """ Is the path controlled by CVS? """
        if os.path.isdir(path):
            if os.path.isfile(os.path.join(path, 'CVS', 'Entries')):
                return True
        path, basename = os.path.split(path)
        cvsdir = os.path.join(path,'CVS')
        if os.path.isdir(cvsdir):
            try:
                for line in open(os.path.join(cvsdir,'Entries')):
                    if '/' not in line:
                        continue
                    filename = line.split('/', 2)[1]
                    if filename == basename:
                        return True
            except (IOError, OSError):
                pass
        return False

    def add(self, paths):
        """ Add files to the repository """
        root, files = self.splitFiles(paths, forcefiles=True)
        dirs = sorted([x for x in files if os.path.isdir(x)])
        files = sorted([x for x in files if not os.path.isdir(x)])
        # Add all directories individually first
        for d in dirs:
            droot = root
            if d == '.':
                droot, d = os.path.split(droot)
                if not d:
                    droot, d = os.path.split(droot)                
            out = self.run(droot, ['add', d])
            self.logOutput(out)
        # Add all files
        if files:
            out = self.run(root, ['add'] + files)
            self.logOutput(out)                
        
    def checkout(self, paths):
        """ Check out the files at the given paths """
        root, files = self.splitFiles(paths, forcefiles=True)
        out = self.run(root, ['checkout'] + files)
        self.logOutput(out)
            
    def commit(self, paths, message=''):
        """ Commit all files with message """
        root, files = self.splitFiles(paths)
        out = self.run(root, ['commit', '-R', '-m', message] + files)
        self.logOutput(out)
            
    def diff(self, paths):
        """ Do a diff on two files in the repository """
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

    def history(self, paths, history=None):
        """ Get the revision history for the given files """
        if history is None:
            history = []
        root, files = self.splitFiles(paths)
        for i, fname in enumerate(files):
            rep = open(os.path.join(root, 'CVS', 'Repository')).read().strip().replace('/', os.sep)
            files[i] = os.path.join(rep, fname)

        for fname in files:
            out = self.run(root, ['rlog', fname])
            if out:
                revision_re = re.compile(r'^revision\s+(\S+)')
                dasl_re = re.compile(r'^date:\s+(\S+\s+\S+)(?:\s+\S+)?;\s+author:\s+(\S+);\s+state:\s+(\S+);')
                current = None
                for line in out.stdout:
                    self.log(line)
                    if line.startswith('----------'):
                        current = {'path':fname}
                        history.append(current)
                        line = out.stdout.next()
                        self.log(line)
                        current['revision'] = DecodeString(revision_re.match(line).group(1))
                        current['sortkey'] = [int(x) for x in current['revision'].split('.')]
                        line = out.stdout.next()
                        self.log(line)
                        m = dasl_re.match(line)
                        current['date'] = self.str2datetime(m.group(1))
                        current['author'] = DecodeString(m.group(2))
                        current['state'] = DecodeString(m.group(3))
                        line = out.stdout.next()
                        self.log(line)
                        current['log'] = DecodeString(line)
                    elif line.startswith('========'):
                        current = None
                    elif current is not None:
                        current['log'] += DecodeString(line)
                self.logOutput(out)
        history.sort(key=lambda x:x['sortkey'])
        history.reverse()
        return history
        
    def remove(self, paths):
        """ Recursively remove paths from source control """
        # Reverse paths so that files get deleted first
        for path in reversed(sorted(paths)):
            root, files = self.splitFiles(path)
            out = self.run(root, ['remove', '-R', '-f'] + files)
            self.logOutput(out)
            
    def status(self, paths, recursive=False, status=dict()):
        """
        Get the status of all given paths
        
        Required Arguments:
        paths -- list of paths to get the status of
        
        Keyword Arguments:
        recursive -- boolean indicating if the status should be recursive
        status -- dictionary containing status information.  This value
            is also the return value
        
        """
        rec = []
        if recursive:
            rec = ['-R']
        root, files = self.splitFiles(paths)
        out = self.run(root, ['status', '-l'] + rec + files, mergeerr=True)
        if out:
            status_re = re.compile(r'^File:\s+(\S+|.+)\s+Status:\s+(.+)\s*$')        
            rep_re = re.compile(r'^\s*Working revision:\s*(\S+)')        
            rrep_re = re.compile(r'^\s*Repository revision:\s*(\S+)')        
            tag_re = re.compile(r'^\s*Sticky Tag:\s*(\S+)')        
            date_re = re.compile(r'^\s*Sticky Date:\s*(\S+)')        
            options_re = re.compile(r'^\s*Sticky Options:\s*(\S+)')
            directory_re = re.compile(r'^cvs server: Examining (\S+)')
            fdir = ''        
            for line in out.stdout:
                self.log(line)
                if status_re.match(line):
                    m = status_re.match(line)
                    key, value = m.group(1), m.group(2) 
                    if fdir and fdir != '.':
                        key = os.path.join(fdir, key)
                    value = value.replace('-','').replace(' ','').lower()
                    current = status[key] = {}
                    if 'modified' in value:
                        current['status'] = 'modified'
                    elif 'added' in value:
                        current['status'] = 'added'
                    elif 'uptodate' in value:
                        current['status'] = 'uptodate'
                    elif 'remove' in value:
                        current['status'] = 'deleted'
                    elif 'conflict' in value:
                        current['status'] = 'conflict'
                    elif 'merge' in value:
                        current['status'] = 'merge'
                elif directory_re.match(line):
                    fdir = directory_re.match(line).group(1)
                elif rep_re.match(line):
                    current['revision'] = rep_re.match(line).group(1)
                elif rrep_re.match(line):
                    current['rrevision'] = rrep_re.match(line).group(1)
                elif tag_re.match(line):
                    current['tag'] = tag_re.match(line).group(1)
                    if current['tag'] == '(none)':
                        del current['tag']
                elif date_re.match(line):
                    current['date'] = date_re.match(line).group(1)
                    if current['date'] == '(none)':
                        del current['date']
                elif options_re.match(line):
                    current['options'] = options_re.match(line).group(1)
                    if current['options'] == '(none)':
                        del current['options']
            self.logOutput(out)
        return status
    
    def str2datetime(self, s):
        """ Convert a time stamp string to a datetime object """
        return datetime.datetime(*[int(x)
                                 for x in re.split(r'[\s+/:-]', s.strip()) if x])

    def update(self, paths):
        """ Recursively update paths """
        root, files = self.splitFiles(paths)
        out = self.run(root, ['update', '-R'] + files)
        self.logOutput(out)
            
    def revert(self, paths): 
        """ Revert paths to repository versions """
        for path in paths:
            root, files = self.splitFiles(path, forcefiles=True,
                                          type=self.TYPE_FILE)
            for fname in files:
                out = self.fetch([os.path.join(root, fname)])[0]
                if out is not None:
                    open(os.path.join(root, fname), 'w').write(out)
    
    def fetch(self, paths, rev=None, date=None):
        """ Fetch a copy of the paths from the repository """
        output = []
        for path in paths:
            if os.path.isdir(path):
                continue
            root, files = self.splitFiles(path)
            for i, fname in enumerate(files):
                rep = open(os.path.join(root, 'CVS', 'Repository')).read().strip().replace('/', os.sep)
                files[i] = os.path.join(rep, fname)
                
            options = []
            if rev:
                options.append('-r')
                options.append(rev)
            if date:
                options.append('-D')
                options.append(date)            
            
            out = self.run(root, ['checkout', '-p'] + options + files)
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
if __name__ == '__main__':
    cvs = CVS()
    print cvs.status(['.'], recursive=True)
    print cvs.history(['/Users/kesmit/pp/resolve/ods/src/odscol.c'])
