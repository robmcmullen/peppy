#!/usr/bin/env python
"""Create a test environment to be used for the low level Editra SourceControl
objects.

"""

import os, os.path, shutil

topdir = os.getcwd()

def make_scm_files():
    fh = open('README', 'wb')
    fh.write("text file example\n")
    fh.close()
    os.mkdir('subdir')
    fh = open('subdir/README.subdir', 'wb')
    fh.write("subdir text file example\n")
    fh.close()

def make_non_scm_files():
    fh = open('not-under-source-code-control', 'wb')
    fh.write("not committed\n")
    fh.close()

def git():
    # create the GIT test directory
    scm = "GIT-test-setup"
    if os.path.exists(scm):
        shutil.rmtree(scm)
    os.mkdir(scm)
    os.chdir(scm)
    os.system('git-init')
    make_scm_files()
    make_non_scm_files()
    os.system('git add README')
    os.system('git add subdir')
    os.system('git commit -m "initial commit"')
    os.chdir(topdir)

def svn():
    # create the SVN test directory
    repo = os.path.abspath("SVN-test-repository")
    if os.path.exists(repo):
        shutil.rmtree(repo)
    os.system('svnadmin create %s' % repo)
    
    tmp = 'tmp-svn'
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    os.mkdir(tmp)
    os.chdir(tmp)
    make_scm_files()
    os.chdir(topdir)
    os.system('svn import tmp-svn file://%s -m "Initial import"' % repo)
    scm = "SVN-test-setup"
    if os.path.exists(scm):
        shutil.rmtree(scm)
    os.system('svn checkout file://%s %s' % (repo, scm))
    os.chdir(scm)
    make_non_scm_files()
    
    os.chdir(topdir)
    shutil.rmtree(tmp)

git()
svn()
