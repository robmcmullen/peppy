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


# Import from the Standard Library
from datetime import datetime
import unittest
from unittest import TestCase

# Import from itools
import peppy.vfs as vfs



class TarTestCase(TestCase):
    """
    Test the whole API for the filesystem layer, "tar://..."
    """
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test00_existance(self):
        self.assertEqual(True, vfs.exists('tar:vfs/sample.tar.bz2'))
        self.assertEqual(True, vfs.exists('tar:vfs/sample.tar.gz'))
        self.assertEqual(False, vfs.exists('tar:vfs/hello.txt'))

    def test01_type_checking(self):
        self.assertEqual(True, vfs.is_file('file:vfs/sample.tar.bz2'))
        self.assertEqual(False, vfs.is_file('tar:vfs/sample.tar.bz2'))
        self.assertEqual(True, vfs.is_file('tar:vfs/sample.tar.bz2/small.py'))
        self.assertEqual(True, vfs.is_folder('tar:vfs/sample.tar.bz2/dir1/'))
        self.assertEqual(True, vfs.is_file('tar:vfs/sample.tar.bz2/dir1/hello1.txt'))
        self.assertEqual(True, vfs.is_file('tar:vfs/sample.tar.gz/dir1/hello1.txt'))
        self.assertEqual(True, vfs.is_folder('tar:vfs/sample.tar.bz2/dir1/dir2'))

    def test11_reading(self):
        file = vfs.open('tar:vfs/sample.tar.gz/dir1/hello1.txt')
        self.assertEqual(file.read(), 'hello world\n')

    def test30_get_names(self):
        names = vfs.get_names('tar:vfs/sample.tar.bz2')
        self.assertEqual(True, 'hello.txt' in names)
        self.assertEqual(True, 'dir1' in names)
        names = vfs.get_names('tar:vfs/sample.tar.bz2/dir1')
        self.assertEqual(True, 'only-in-dir1.txt' in names)
        self.assertEqual(True, 'dir2' in names)
        names = vfs.get_names('tar:vfs/sample.tar.bz2/dir1/dir2')
        self.assertEqual(True, 'small.py' in names)
        self.assertEqual(False, 'hello.txt' in names)
        self.assertEqual(False, 'hello1.txt' in names)

    def test31_traverse(self):
        for x in vfs.traverse('tar:vfs/sample.tar.bz2'):
            #print("traversing %s" % x)
            self.assertEqual(vfs.exists(x), True)

if __name__ == '__main__':
    unittest.main()
