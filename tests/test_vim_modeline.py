# vim: ts=8:sw=2:tw=50:
import os,sys,re
from cStringIO import StringIO

import wx
import wx.stc

from peppy.stcbase import *
from peppy.lib.vimutil import *

from tests.mock_wx import getPlainSTC

from nose.tools import *

class TestVIM(object):
  tests = [
    ('<!-- vim:set ts=2 sts=2 sw=2 tw=0: -->', [('GetTabWidth', 2), ('GetIndent', 2), ('GetEdgeColumn', 0)]),
    ('# vim:set sw=2 et:', [('GetIndent', 2)]),
    ('# vim: sts=4 sw=4 :', [('GetIndent', 4)]),
    ('// vim:ts=8:sw=4:sts=4:', [('GetTabWidth', 8), ('GetIndent', 4)]),
    ('/* vim:set ts=8 sts=4 sw=4:', [('GetTabWidth', 8), ('GetIndent', 4)]),
    ('/* vim: set ft=c : */', []),
    ('# vim: set noet sw=8 ts=8 sts=0 wm=0 tw=0:', [('GetTabWidth', 8), ('GetIndent', 8), ('GetEdgeColumn', 0)]),
    ('# Makefile for VIM on OS/2 using EMX    vim:ts=8:sw=8:tw=78:', [('GetTabWidth', 8), ('GetIndent', 8), ('GetEdgeColumn', 78)]),
    ('# vim:set ai et sts=2 sw=2 tw=0:', [('GetIndent', 2), ('GetEdgeColumn', 0)]),
    ('/* vim: set sw=8: -*- Mode: C; tab-width: 8; indent-tabs-mode: t; c-basic-offset: 8 -*- */', [('GetIndent', 8)]),
    ('vim:tw=76:sw=4:et:', [('GetIndent', 4), ('GetEdgeColumn', 76)]),
    ('/* vi:set tabstop=4 shiftwidth=4 nowrap: */', [('GetTabWidth', 4), ('GetIndent', 4)]),
    ('/* vi:set tabstop=4 shiftwidth=4 noexpandtab: */', [('GetTabWidth', 4), ('GetIndent', 4)]),
    ]

  def setUp(self):
    self.stc = getPlainSTC()
        
  def checkSettings(self, test):
    lines = test[0]
    if isinstance(lines, str):
      lines = [lines]
    applyVIMModeline(self.stc, lines)
    for fcn, val in test[1]:
      eq_((fcn, getattr(self.stc, fcn)()), (fcn, val))

  def testSettings(self):
    for test in self.tests:
      yield self.checkSettings, test

  def testCreateModeline(self):
    applyVIMModeline(self.stc, ['/* vim:set ts=8 sts=4 sw=4 tw=75:'])
    line = createVIMModeline(self.stc)
    applyVIMModeline(self.stc, ['vim: set ts=0 sts=0 sw=0 tw=0'])
    applyVIMModeline(self.stc, [line])
    eq_(self.stc.GetTabWidth(), 8)
    eq_(self.stc.GetIndent(), 4)
    eq_(self.stc.GetEdgeColumn(), 75)

