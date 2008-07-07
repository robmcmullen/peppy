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
from datetime import datetime
import unittest
from unittest import TestCase

# Import from itools
import peppy.vfs as vfs



class FileTestCase(TestCase):
    """
    Test the whole API for the filesystem layer, "file://..."
    """

    def test00_exists(self):
        exists = vfs.exists('vfs/hello.txt')
        self.assertEqual(exists, True)
        self.assertEqual(True, vfs.can_read('vfs/hello.txt'))

    def test01_does_not_exist(self):
        exists = vfs.exists('vfs/fdsfsf')
        self.assertEqual(exists, False)

    
    def test02_is_file(self):
        is_file = vfs.is_file('vfs/hello.txt')
        self.assertEqual(is_file, True)


    def test03_is_not_file(self):
        is_file = vfs.is_file('vfs')
        self.assertEqual(is_file, False)


    def test04_is_folder(self):
        is_folder = vfs.is_folder('vfs')
        self.assertEqual(is_folder, True)


    def test05_is_not_folder(self):
        is_folder = vfs.is_folder('vfs/hello.txt')
        self.assertEqual(is_folder, False)


    def test06_make_file(self):
        vfs.make_file('vfs/file')
        self.assertEqual(vfs.is_file('vfs/file'), True)


    def test07_make_folder(self):
        vfs.make_folder('vfs/folder')
        self.assertEqual(vfs.is_folder('vfs/folder'), True)


    def test08_ctime(self):
        ctime = vfs.get_ctime('vfs/file')
        self.assertEqual(ctime.year, datetime.now().year)


    def test09_mtime(self):
        mtime = vfs.get_mtime('vfs/file')
        self.assertEqual(mtime.year, datetime.now().year)


    def test10_atime(self):
        atime = vfs.get_atime('vfs/file')
        self.assertEqual(atime.year, datetime.now().year)


    def test11_get_mimetype(self):
        mimetype = vfs.get_mimetype('vfs/hello.txt')
        self.assertEqual(mimetype, 'text/plain')


    def test12_remove_file(self):
        vfs.remove('vfs/file')
        self.assertEqual(vfs.exists('vfs/file'), False)


    def test13_remove_empty_folder(self):
        vfs.remove('vfs/folder')
        self.assertEqual(vfs.exists('vfs/folder'), False)


    def test14_remove_folder(self):
        # Create hierarchy
        vfs.make_folder('vfs/folder')
        vfs.make_folder('vfs/folder/a')
        vfs.make_file('vfs/folder/a/hello.txt')
        # Remove and test
        vfs.remove('vfs/folder')
        self.assertEqual(vfs.exists('vfs/folder'), False)


    def test15_open_file(self):
        file = vfs.open('vfs/hello.txt')
        self.assertEqual(file.read(), 'hello world\n')


#    def test16_open_file(self):


    def test17_move_file(self):
        vfs.copy('vfs/hello.txt', 'vfs/hello.txt.bak')
        vfs.move('vfs/hello.txt.bak', 'vfs/hello.txt.old')
        file = vfs.open('vfs/hello.txt.old')
        self.assertEqual(file.read(), 'hello world\n')
        self.assertEqual(vfs.exists('vfs/hello.txt.bak'), False)


    def test18_get_names(self):
        self.assertEqual('hello.txt.old' in vfs.get_names('vfs'), True)
        # Remove temporary file
        vfs.remove('vfs/hello.txt.old')


    def test19_traverse(self):
        for x in vfs.traverse('.'):
            self.assertEqual(vfs.exists(x), True)


    def test20_append(self):
        # Initialize
        with vfs.make_file('vfs/toto.txt') as file:
            file.write('hello\n')
        # Test
        with vfs.open('vfs/toto.txt', vfs.APPEND) as file:
            file.write('bye\n')
        self.assertEqual(open('vfs/toto.txt').read(), 'hello\nbye\n')
        # Remove temporary file
        vfs.remove('vfs/toto.txt')


    def test21_write(self):
        # Initialize
        with vfs.make_file('vfs/truncate.txt') as file:
            file.write('hello there\n')
        # Test
        with vfs.open('vfs/truncate.txt', vfs.WRITE) as file:
            file.write('bye\n')
        self.assertEqual(open('vfs/truncate.txt').read(), 'bye\n')
        # Remove temporary file
        vfs.remove('vfs/truncate.txt')



class FSTestCase(TestCase):

    def test_linux(self):
        # file://home/toto.txt
        uri = vfs.get_reference('stuff/blah')
#        print "scheme=%s authority=%s path=%s query=%s fragment=%s" % (
#            uri.scheme,
#            uri.authority,
#            uri.path,
#            uri.query,
#            uri.fragment)
        self.assertEqual('stuff/blah', uri.path)
        self.assertEqual('', uri.scheme)

    def test_windows(self):
        # c:\toto.txt
        uri = vfs.get_reference('c:stuff/blah')
        self.assertEqual('c:stuff/blah', uri.path)
        self.assertEqual('file', uri.scheme)
        uri = vfs.get_reference('file:///c:/stuff/blah')
        self.assertEqual('c:/stuff/blah', uri.path)
        self.assertEqual('file', uri.scheme)
        uri = vfs.get_reference('c:/stuff/blah#5')
        self.assertEqual('c:/stuff/blah', str(uri.path))
        self.assertEqual('5', uri.fragment)
        self.assertEqual('file', uri.scheme)
        uri = vfs.get_reference('c:/stuff/blah#whatever')
        self.assertEqual('c:/stuff/blah#whatever', str(uri.path))
        self.assertEqual(None, uri.fragment)
        self.assertEqual('file', uri.scheme)
        
    def test_windows_normalize(self):
        uri = vfs.get_reference('C:/stuff/blah')
        self.assertEqual('c:/stuff/blah', uri.path)
        self.assertEqual('file', uri.scheme)
    
    def test_filesystem_names(self):
        names = vfs.get_file_system_schemes()
        self.assert_('file' in names)
        self.assert_('mem' in names)
    
    def test_dirname(self):
        base = vfs.get_reference('stuff/blah')
        uri = vfs.get_dirname(base)
        self.assertEqual('stuff/', uri.path)
        uri = vfs.get_dirname(uri)
        print "path=%s" % uri.path
        self.assertEqual('./', uri.path)
        base = vfs.get_reference('/stuff/blah/')
        uri = vfs.get_dirname(base)
        self.assertEqual('/stuff/', uri.path)
        uri = vfs.get_dirname(uri)
        print "path=%s" % uri.path
        self.assertEqual('/', uri.path)
        base = vfs.get_reference('file:///stuff/blah/')
        uri = vfs.get_dirname(base)
        print "path=%s" % uri.path
        self.assertEqual('/stuff/', uri.path)
        uri = vfs.get_dirname(uri)
        print "path=%s" % uri.path
        self.assertEqual('/', uri.path)




class FoldersTestCase(TestCase):
 
    def setUp(self):
        self.tests = vfs.open('vfs/')


    def test00_exists(self):
        exists = self.tests.exists('hello.txt')
        self.assertEqual(exists, True)



class CopyTestCase(TestCase):

    def setUp(self):
        vfs.make_folder('vfs-tmp')


    def tearDown(self):
        if vfs.exists('vfs-tmp'):
            vfs.remove('vfs-tmp')


    def test_copy_file(self):
        vfs.copy('vfs/hello.txt', 'vfs-tmp/hello.txt.bak')
        with vfs.open('vfs-tmp/hello.txt.bak') as file:
            self.assertEqual(file.read(), 'hello world\n')


    def test_copy_file_to_folder(self):
        vfs.copy('vfs/hello.txt', 'vfs-tmp')
        with vfs.open('vfs-tmp/hello.txt') as file:
            self.assertEqual(file.read(), 'hello world\n')


    def test_copy_folder(self):
        vfs.copy('vfs', 'vfs-tmp/xxx')
        with vfs.open('vfs-tmp/xxx/hello.txt') as file:
            self.assertEqual(file.read(), 'hello world\n')


    def test_copy_folder_to_folder(self):
        vfs.copy('vfs', 'vfs-tmp')
        with vfs.open('vfs-tmp/vfs/hello.txt') as file:
            self.assertEqual(file.read(), 'hello world\n')


class HttpFSTestCase(TestCase):

    def test_open(self):
        file = vfs.open('http://www.google.com')
        data = file.read()
        file.close()
        self.assertEqual('<html>' in data, True)


if __name__ == '__main__':
    unittest.main()
