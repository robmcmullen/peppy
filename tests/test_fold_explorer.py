import os,sys,re
from cStringIO import StringIO

import wx.stc
from tests.mock_wx import *

from peppy.stcbase import *
from peppy.plugins.python_mode import *
from peppy.plugins.find_replace import *

from nose.tools import *

def genSampleCode(num_classes, num_funcs):
    lines = []
    if isinstance(num_classes, int):
        num_classes = range(num_classes)
    if isinstance(num_funcs, int):
        num_funcs = range(num_funcs)
    for i in num_classes:
        lines.append("class Class%d:" % i)
        for j in num_funcs:
            lines.append("    def func%d:" % j)
            lines.append("        pass")
    return os.linesep.join(lines) + os.linesep

class TestFoldExpansion(object):
    def setUp(self):
        self.stc = getSTC(stcclass=PythonMode, lexer="Python")
    
    def getSampleFolds(self, num_classes, num_funcs, expanded):
        self.stc.SetText(genSampleCode(num_classes, num_funcs))
        self.stc.Colourise(0, self.stc.GetTextLength())
        folds = self.stc.computeFoldHierarchy(expanded=expanded)
        print folds
        return folds

    def testBasic(self):
        folds1 = self.getSampleFolds(2, 3, True)
        folds2 = self.getSampleFolds(2, 4, False)
        self.stc.copyFoldHierarchyTreeExpansion(folds1, folds2)
        eq_(folds1.children[0].expanded, folds2.children[0].expanded)
        eq_(folds1.children[1].expanded, folds2.children[1].expanded)
    
    def testInsert(self):
        folds1 = self.getSampleFolds([1, 3], 3, True)
        folds2 = self.getSampleFolds([1, 2, 3], 4, False)
        self.stc.copyFoldHierarchyTreeExpansion(folds1, folds2)
        dprint(folds2.children[0])
        eq_(folds2.children[0].expanded, True)
        dprint(folds2.children[1])
        eq_(folds2.children[1].expanded, False)
        dprint(folds2.children[2])
        eq_(folds2.children[2].expanded, True)
    
    def testRemoved1(self):
        folds1 = self.getSampleFolds([1, 2, 3], 3, True)
        folds2 = self.getSampleFolds([1, 3], 4, False)
        self.stc.copyFoldHierarchyTreeExpansion(folds1, folds2)
        dprint(folds2.children[0])
        eq_(folds2.children[0].expanded, True)
        dprint(folds2.children[1])
        eq_(folds2.children[1].expanded, True)
    
    def testRemoved2(self):
        folds1 = self.getSampleFolds([1, 2, 3, 4], 3, True)
        folds2 = self.getSampleFolds([1, 4], 4, False)
        self.stc.copyFoldHierarchyTreeExpansion(folds1, folds2)
        dprint(folds2.children[0])
        eq_(folds2.children[0].expanded, True)
        dprint(folds2.children[1])
        eq_(folds2.children[1].expanded, True)
