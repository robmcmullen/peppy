# -*- mode:Python;  cursor-type: (bar. 1)-*-
import os, sys, re, shutil
sys.path.append('..')

from nose.tools import *

import editra.GIT as GIT
import editra.SVN as SVN
scms = ['GIT', 'SVN']

def setup_module():
    print "Setting up repository"
    for name in scms:
        scratch = "%s-test-scratch" % name
        if os.path.exists(scratch):
            shutil.rmtree(scratch)
        shutil.copytree('%s-test-setup' % name, scratch)

def teardown_module():
    print "Tearing down repository"
    for name in scms:
        scratch = "%s-test-scratch" % name
        if os.path.exists(scratch):
            shutil.rmtree(scratch)

class SCMBase(object):
    scm_name = None

    def setUp(self):
        self.root = os.path.abspath('%s-test-scratch' % self.scm_name)
        repo = '%s-test-repository' % self.scm_name
        if os.path.exists(repo):
            self.repository = repo
        else:
            self.repository = self.root
        scm_object = "%s.%s()" % (self.scm_name, self.scm_name)
        self.scm = eval(scm_object)
    
    def testIsControlledBySCM(self):
        eq_(self.scm.isControlled(self.root), True)
    
    def testFindRepository(self):
        repo = os.path.normpath(self.scm.getRepository(self.root))
        print(repo)
        eq_(os.path.basename(repo), os.path.basename(self.repository))
    
    def testStatus(self):
        status = self.scm.status([self.root], status=dict())
        assert 'README' in status
        eq_(status['README']['status'], 'uptodate')
        assert 'subdir' in status
        eq_(status['subdir']['status'], 'uptodate')
    
    def testRecursiveStatus(self):
        status = self.scm.status([self.root], recursive=True, status=dict())
        assert 'README' in status
        eq_(status['README']['status'], 'uptodate')
        print(status)
        assert 'subdir' in status
        eq_(status['subdir']['status'], 'uptodate')
        assert 'subdir/README.subdir' in status
        eq_(status['subdir/README.subdir']['status'], 'uptodate')
    
    def testNotUnderControl(self):
        testfile = 'not-under-source-code-control'
        testpath = os.path.join(self.root, testfile)
        status = self.scm.status([testpath], status=dict())
        assert testfile not in status
    
    def testFileLifeCycle(self):
        testfile = 'lifecycle-test.txt'
        testpath = os.path.join(self.root, testfile)
        fh = open(testpath, 'wb')
        fh.write("Blah!")
        fh.close()
        self.scm.add([testpath])
        status = self.scm.status([self.root], status=dict())
        assert testfile in status
        eq_(status[testfile]['status'], 'added')
        self.scm.commit([testpath], 'testFileLifeCycle commit')
        status = self.scm.status([self.root], status=dict())
        assert testfile in status
        eq_(status[testfile]['status'], 'uptodate')
        fh = open(testpath, 'wb')
        fh.write("Blah blah!")
        fh.close()
        status = self.scm.status([self.root], status=dict())
        assert testfile in status
        eq_(status[testfile]['status'], 'modified')
        self.scm.remove([testpath])
        status = self.scm.status([self.root], status=dict())
        assert testfile in status
        eq_(status[testfile]['status'], 'deleted')
        self.scm.commit([testpath], 'testFileLifeCycle remove')
        status = self.scm.status([self.root], status=dict())
        assert testfile not in status

class TestGit(SCMBase):
    scm_name = 'GIT'
    
    def testGitExists(self):
        eq_(GIT.checkDirectory(self.root), True)
    

class TestSVN(SCMBase):
    scm_name = 'SVN'


