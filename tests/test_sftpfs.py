# -*- coding: UTF-8 -*-
# Copyright (C) 2006-2007 Juan David Ibáñez Palomar <jdavid@itaapy.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

# Import from the future
from __future__ import with_statement

# Import from the Standard Library
from datetime import datetime, timedelta
import unittest
from unittest import TestCase

# Import from itools
import peppy.vfs as vfs


import os, threading, time


class FileSystemTestCases(object):
    """Test the whole API for the filesystem layer using the specified root
    
    """
    root = None
    
    def setUp(self):
        if vfs.exists(self.root + 'tmp'):
            vfs.remove(self.root + 'tmp')
        vfs.make_folder(self.root + 'tmp')
        file = vfs.make_file(self.root + 'tmp/blah.txt')
        file.write("BLAH!!!")
        file.close()

    def tearDown(self):
        if vfs.exists(self.root + 'tmp'):
            vfs.remove(self.root + 'tmp')
        if vfs.exists(self.root + 'tmp2'):
            vfs.remove(self.root + 'tmp2')
        if vfs.exists(self.root + 'testfile.txt'):
            vfs.remove(self.root + 'testfile.txt')

    def test00_existence(self):
        assert vfs.exists(self.root + "README")
        assert vfs.can_read(self.root + "README")
        assert vfs.can_write(self.root + "README")
        assert not vfs.exists(self.root + 'fdsfsf')
        
        # All the following should be synonyms
        exists = vfs.exists(self.root + 'README')
        self.assertEqual(exists, True)
        exists = vfs.exists(self.root + '//README')
        self.assertEqual(exists, True)
        exists = vfs.exists(self.root + '///README')
        self.assertEqual(exists, True)

    def test01_type_checking(self):
        is_file = vfs.is_file(self.root + 'README')
        self.assertEqual(is_file, True)
        is_file = vfs.is_file(self.root)
        self.assertEqual(is_file, False)
        is_folder = vfs.is_folder(self.root)
        self.assertEqual(is_folder, True)
        is_folder = vfs.is_folder(self.root + 'README')
        self.assertEqual(is_folder, False)

    def test10_creation(self):
        file = vfs.make_file(self.root + 'testfile.txt')
        file.write("one\n")
        file.close()
        self.assertEqual(vfs.is_file(self.root + 'testfile.txt'), True)
        
        url = self.root + 'tmp/dir'
        vfs.make_folder(url)
        self.assertEqual(vfs.is_folder(url), True)
        
        url = self.root + 'tmp/dir/file1'
        fh = vfs.make_file(url)
        fh.write("this is file1")
        fh.close()
        self.assertEqual(vfs.is_file(url), True)
        
        url = self.root + 'tmp/dir/zero'
        fh = vfs.make_file(url)
        fh.close()
        self.assertEqual(vfs.is_file(url), True)
        
        # this should raise an OSError because it's trying to make a file out
        # of an existing folder
        url = self.root + 'tmp/dir'
        self.assertRaises(OSError, vfs.make_file, url)
        
        # this should raise an OSError because it's trying to make a file in
        # another file
        url = self.root + 'tmp/dir/file1/file2'
        self.assertRaises(OSError, vfs.make_file, url)

    def test11_reading(self):
        file = vfs.make_file(self.root + 'testfile.txt')
        file.write("one\n")
        file.close()        
        file = vfs.open(self.root + 'testfile.txt')
        self.assertEqual(file.read(), 'one\n')

    def test12_append(self):
        file = vfs.make_file(self.root + 'testfile.txt')
        file.write("one\n")
        file.close()        
        file = vfs.open(self.root + 'testfile.txt', vfs.APPEND)
        file.write("two\n")
        file.close()
        file = vfs.open(self.root + 'testfile.txt')
        self.assertEqual(file.read(), 'one\ntwo\n')
        file = vfs.open(self.root + 'testfile.txt', vfs.WRITE)
        file.write("three\n")
        file.close()
        file = vfs.open(self.root + 'testfile.txt')
        self.assertEqual(file.read(), 'three\n')

    def test13_folder_creation(self):
        file = vfs.make_file(self.root + 'testfile.txt')
        file.write("one\n")
        file.close()        
        url = self.root + 'testfile.txt/dir'
        self.assertRaises(OSError, vfs.make_folder, url)
        
        # This should raise an OSError because we're trying to make a file
        # inside another file
        file = vfs.make_file(self.root + 'tmp/blah1')
        file.write("blah1\n")
        file.close()
        self.assertRaises(OSError, vfs.make_folder, self.root + 'tmp/blah1/bad1')
        
        # This should raise OSError because we're trying to make a file with
        # the same name as an existing folder
        url = self.root + 'tmp/blah2'
        file = vfs.make_file(url)
        file.write("blah2\n")
        file.close()
        self.assertEqual(True, vfs.exists(url))
        self.assertRaises(OSError, vfs.make_file, self.root + 'tmp/blah2')

    def test20_move_file(self):
        vfs.copy(self.root + 'tmp/blah.txt', self.root + 'tmp/blah.txt.bak')
        vfs.move(self.root + 'tmp/blah.txt.bak', self.root + 'tmp/blah.txt.old')
        file = vfs.open(self.root + 'tmp/blah.txt.old')
        self.assertEqual(file.read(), 'BLAH!!!')
        self.assertEqual(vfs.exists(self.root + 'tmp/blah.txt.bak'), False)

    def test21_copy_file(self):
        url = self.root + 'tmp/dir/'
        vfs.make_folder(url)
        vfs.copy(self.root + 'tmp/blah.txt', url)
        file = vfs.open(url + 'blah.txt')
        self.assertEqual(file.read(), 'BLAH!!!')
        vfs.copy(self.root + 'tmp/blah.txt', url + 'blah2.txt')
        file = vfs.open(url + 'blah2.txt')
        self.assertEqual(file.read(), 'BLAH!!!')

    def test29_remove(self):
        url = self.root + 'tmp/dir'
        vfs.make_folder(url)
        vfs.remove(url)
        self.assertEqual(vfs.exists(url), False)
        # Create hierarchy
        vfs.make_folder(self.root + 'tmp3')
        vfs.exists(self.root + 'tmp3')
        vfs.make_folder(self.root + 'tmp3/folder')
        vfs.exists(self.root + 'tmp3/folder')
        vfs.make_folder(self.root + 'tmp3/folder/a')
        vfs.exists(self.root + 'tmp3/folder/a')
        fh = vfs.make_file(self.root + 'tmp3/folder/a/hello.txt')
        fh.write("blah")
        fh.close()
        vfs.exists(self.root + 'tmp3/folder/a/hello.txt')
        # Remove and test
        vfs.remove(self.root + 'tmp3/folder')
        self.assertEqual(vfs.exists(self.root + 'tmp3/folder'), False)

    def test30_get_names(self):
        filenames = vfs.get_names(self.root)
        print(filenames)
        assert 'README' in filenames
        assert 'demo_sftp.py' in filenames
        assert 'wxyz' not in filenames
        self.assertRaises(OSError, vfs.get_names, self.root + 'zzzzz')
##
##    def test31_traverse(self):
##        for x in vfs.traverse(self.root + ''):
##            self.assertEqual(vfs.exists(x), True)
##
##    def test32_copy_folder(self):
##        vfs.copy(self.root + 'tmp', self.root + 'tmp2')
##        with vfs.open(self.root + 'tmp2/blah.txt') as file:
##            self.assertEqual(file.read(), 'BLAH!!!')
##        vfs.make_folder(self.root + 'tmp2/folder-dest')
##        vfs.copy(self.root + 'tmp', self.root + 'tmp2/folder-dest')
##        with vfs.open(self.root + 'tmp2/folder-dest/tmp/blah.txt') as file:
##            self.assertEqual(file.read(), 'BLAH!!!')
##
##    def test40_permissions(self):
##        perms = vfs.get_permissions(self.root + 'tmp/blah.txt')
##        self.assertEqual(perms.is_mode_set('u', 'r'), True)
##        self.assertEqual(perms.is_mode_set('u', 'w'), True)
##        self.assertEqual(perms.is_mode_set('g', 'r'), True)
##        self.assertEqual(perms.is_mode_set('g', 'w'), False)
##        self.assertEqual(perms.is_mode_set('o', 'r'), True)
##        self.assertEqual(perms.is_mode_set('o', 'w'), False)

class SimpleSFTPFSTestCase(FileSystemTestCases, TestCase):
    root = 'sftp://sftptest:test@localhost/demo_sftp_folder/'



if __name__ == '__main__':
    unittest.main()
    server.stop()
