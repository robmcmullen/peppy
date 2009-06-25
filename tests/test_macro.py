import os,sys,re
import cPickle as pickle
import __builtin__
__builtin__._ = unicode

from peppy.plugins.macro import *

# Normally the file registration is accomplished in the plugin activation
vfs.register_file_system('macro', MacroFS)

import peppy.vfs as vfs
from peppy.vfs.itools.vfs.memfs import MemDir

from nose.tools import *

class TestMacro(object):
    def setup(self):
        macro = PythonScriptableMacro("actions", "name")
        MacroFS.addMacro(macro)
        macro = PythonScriptableMacro("other actions", "name")
        MacroFS.addMacro(macro)
        macro = PythonScriptableMacro("other actions", "different name")
        MacroFS.addMacro(macro)
    
    def teardown(self):
        MacroFS.root = MemDir()
    
    def testPickle(self):
        bytes = MacroSaveData.packVersion1()
        MacroFS.root = MemDir()
        RecentMacros.setStorage([])
        names = vfs.get_names("macro:")
        assert "name" not in names
        
        version, data = pickle.loads(bytes)
        MacroSaveData.unpackVersion1(data)
        names = vfs.get_names("macro:")
        assert "name" in names


class TestMacroFS(object):
    def setup(self):
        MacroFS.root = MemDir()
        macro = PythonScriptableMacro("actions", "name")
        MacroFS.addMacro(macro)
        macro = PythonScriptableMacro("other actions", "name")
        MacroFS.addMacro(macro)
        macro = PythonScriptableMacro("other actions", "different name")
        MacroFS.addMacro(macro)
    
    def teardown(self):
        MacroFS.root = MemDir()
    
    def testNames(self):
        names = vfs.get_names("macro:")
        assert "name" in names
        assert "name<1>" in names
        assert "different name" in names
        assert "different name<1>" not in names
    
    def testNotFound(self):
        names = vfs.get_names("macro:")
        assert "wxyz" not in names
        assert_raises(OSError, vfs.get_names, "macro:sir not appearing in this film")
    
    def testMacroSubdir(self):
        macro = PythonScriptableMacro("actions", "python1")
        MacroFS.addMacro(macro, "Python")
        names = vfs.get_names("macro:")
        assert "python1" not in names
        names = vfs.get_names("macro:Python")
        assert "python1" in names
    
    def testMacroSubdirAndRename(self):
        """Checking to see that a macro will get renamed if a directory is
        attempted to be created with the same name.
        
        Note that the MacroFS behaves like a normal filesystem when accessed
        using the regular filesystem commands.  Only when adding macros using
        the addMacro method will this happen.
        """
        macro = PythonScriptableMacro("actions", "Python")
        MacroFS.addMacro(macro)
        names = vfs.get_names("macro:")
        assert "Python" in names
        macro = PythonScriptableMacro("actions", "python1")
        MacroFS.addMacro(macro, "Python")
        names = vfs.get_names("macro:")
        assert "Python<1>" in names
        names = vfs.get_names("macro:Python")
        assert "python1" in names
