# -*- coding: UTF-8 -*-
# Copyright (C) 2007 Rob McMullen <robm@users.sourceforge.net>
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
from datetime import datetime
import unittest
from unittest import TestCase

# Import from itools
import peppy.vfs as vfs



class MemTestCase(TestCase):
    """
    Test the whole API for the filesystem layer, "mem://..."
    """
    def setUp(self):
        vfs.make_folder('mem:tmp')
        file = vfs.make_file('mem:tmp/blah.txt')
        file.write("BLAH!!!")
        file.close()

    def tearDown(self):
        if vfs.exists('mem:tmp'):
            vfs.remove('mem:tmp')

    def test00_existence(self):
        exists = vfs.exists('mem:tmp')
        self.assertEqual(exists, True)
        exists = vfs.exists('mem:fdsfsf')
        self.assertEqual(exists, False)

    def test01_type_checking(self):
        is_file = vfs.is_file('mem:tmp/blah.txt')
        self.assertEqual(is_file, True)
        is_file = vfs.is_file('mem:tmp')
        self.assertEqual(is_file, False)
        is_folder = vfs.is_folder('mem:tmp')
        self.assertEqual(is_folder, True)
        is_folder = vfs.is_folder('mem:tmp/blah.txt')
        self.assertEqual(is_folder, False)
        mimetype = vfs.get_mimetype('mem:tmp/blah.txt')
        self.assertEqual(mimetype, 'text/plain')

    def test10_creation(self):
        file = vfs.make_file('mem:testfile.txt')
        file.write("one\n")
        file.close()        
        self.assertEqual(vfs.is_file('mem:testfile.txt'), True)
        url = 'mem:test/dir'
        vfs.make_folder(url)
        self.assertEqual(vfs.is_folder(url), True)
        url = 'mem:dir1/dir2/dir3/file1'
        fh = vfs.make_file(url)
        fh.write("this is file1")
        fh.close()
        self.assertEqual(vfs.is_file(url), True)
        
        # this should raise an OSError because it's trying to make a file out
        # of an existing folder
        url = 'mem:dir1/dir2/dir3'
        self.assertRaises(OSError, vfs.make_file, url)
        
        # this should raise an OSError because it's trying to make a file in
        # another file
        url = 'mem:dir1/dir2/dir3/file1/file2'
        self.assertRaises(OSError, vfs.make_file, url)

    def test11_reading(self):
        file = vfs.open('mem:testfile.txt')
        self.assertEqual(file.read(), 'one\n')

    def test12_append(self):
        file = vfs.open('mem:testfile.txt', vfs.APPEND)
        file.write("two\n")
        file.close()
        file = vfs.open('mem:testfile.txt')
        self.assertEqual(file.read(), 'one\ntwo\n')
        file = vfs.open('mem:testfile.txt', vfs.WRITE)
        file.write("three\n")
        file.close()
        file = vfs.open('mem:testfile.txt')
        self.assertEqual(file.read(), 'three\n')

    def test13_folder_creation(self):
        url = 'mem:testfile.txt/dir'
        self.assertEqual(vfs.is_folder(url), False)
        self.assertRaises(OSError, vfs.make_folder, url)
        
        # This should raise an OSError because we're trying to make a file
        # inside another file
        file = vfs.make_file('mem:blah1')
        file.write("blah1\n")
        file.close()
        self.assertRaises(OSError, vfs.make_folder, 'mem:blah1/bad1')
        
        # This should raise OSError because we're trying to make a file with
        # the same name as an existing folder
        url = 'mem:blah2/file2'
        file = vfs.make_file(url)
        file.write("blah2\n")
        file.close()
        self.assertEqual(True, vfs.exists(url))
        self.assertRaises(OSError, vfs.make_file, 'mem:blah2')

    def test20_move_file(self):
        vfs.copy('mem:testfile.txt', 'mem:testfile.txt.bak')
        vfs.move('mem:testfile.txt.bak', 'mem:testfile.txt.old')
        file = vfs.open('mem:testfile.txt.old')
        self.assertEqual(file.read(), 'three\n')
        self.assertEqual(vfs.exists('mem:testfile.txt.bak'), False)

    def test21_copy_file(self):
        vfs.copy('vfs/hello.txt', 'mem:/tmp/hello.txt')
        with vfs.open('mem:/tmp/hello.txt') as file:
            self.assertEqual(file.read(), 'hello world\n')
        vfs.make_folder('mem:/tmp/folder-test')
        vfs.copy('vfs/hello.txt', 'mem:/tmp/folder-test')
        with vfs.open('mem:/tmp/folder-test/hello.txt') as file:
            self.assertEqual(file.read(), 'hello world\n')

    def test22_copy_folder(self):
        vfs.copy('vfs', 'mem:/tmp/folder-copy')
        with vfs.open('mem:/tmp/folder-copy/hello.txt') as file:
            self.assertEqual(file.read(), 'hello world\n')
        vfs.make_folder('mem:/tmp/folder-dest')
        vfs.copy('vfs', 'mem:/tmp/folder-dest')
        with vfs.open('mem:/tmp/folder-dest/vfs/hello.txt') as file:
            self.assertEqual(file.read(), 'hello world\n')

    def test29_remove(self):
        url = 'mem:testfile.txt.old'
        vfs.remove(url)
        self.assertEqual(vfs.exists(url), False)
        url = 'mem:test/dir'
        vfs.make_folder(url)
        vfs.remove(url)
        self.assertEqual(vfs.exists(url), False)
        # Create hierarchy
        vfs.make_folder('mem:tests/folder')
        vfs.make_folder('mem:tests/folder/a')
        vfs.make_file('mem:tests/folder/a/hello.txt')
        # Remove and test
        vfs.remove('mem:tests/folder')
        self.assertEqual(vfs.exists('mem:tests/folder'), False)


    def test30_get_names(self):
        self.assertEqual('blah.txt' in vfs.get_names('mem:tmp'), True)

    def test31_traverse(self):
        for x in vfs.traverse('mem:'):
            self.assertEqual(vfs.exists(x), True)

if __name__ == '__main__':
    unittest.main()
