#-----------------------------------------------------------------------------
# Name:        orderer.py
# Purpose:     pseudo-constraint-solver for ordering of menu items
#
# Author:      Rob McMullen
#
# Created:     2007
# RCS-ID:      $Id: $
# Copyright:   (c) 2007 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""
Mini-constraint-solver to attempt to order menu items by their
relative positions.
"""

import os,sys
from peppy.debug import *
from cStringIO import StringIO

class DelayedOrderer(debugmixin):
    def __init__(self,name=None,hidden=False):
        self.items=[]
        self.constrainlist=[]
        self.name=name
        self.hidden=hidden

    def __str__(self):
        return str(self.name)

    def hasConstraints(self):
        return len(self.constraintlist)>0
        
    def hide(self):
        self.hidden=True
        return self

    def show(self):
        self.hidden=False
        return self

    def before(self,name):
        self.constrainlist.append(('before',name))
        return self

    def after(self,name):
        self.constrainlist.append(('after',name))
        return self

    def first(self):
        self.constrainlist.append(('first',None))
        return self

    def last(self):
        self.constrainlist.append(('last',None))
        return self

    def populate(self,orderer):
        for action,name in self.constrainlist:
            method=getattr(orderer,action)
            if name is not None:
                method(self.name,name)
            else:
                method(self.name)
                



class Orderer(debugmixin):
    def __init__(self,items):
        self.orderer={}
        self.items=[a for a in items] # copy of input items
        self.sorted=[] # sorted list
        self.constraints=[] # skew-symmetric matrix as input to list.sort()
        self.total={}
        self.namemap={}
        for a in self.items:
            self.orderer[a]={}
            self.namemap[str(a)]=a
            self.total[a]=0
            for b in self.items:
                self.orderer[a][b]=0
        self.importConstraints(items)

    def __str__(self):
        s=StringIO()
        colwidth=8
        s.write("".center(colwidth)+"".join([str(b).center(colwidth) for b in self.items])+"\n")
        for a in self.items:
            s.write(str(a).center(colwidth)+"".join([str(self.orderer[a][b]).center(colwidth) for b in self.items])+"\n")
        return s.getvalue()

    def importConstraints(self,items):
        assert self.dprint(self.items)
        assert self.dprint('before')
        assert self.dprint(self)
        for c in items:
            if hasattr(c,'populate'):
                assert self.dprint("calling %s to populate constraints" % c.name)
                c.populate(self)
        assert self.dprint('after')
        assert self.dprint(self)
        
    def before(self,a,b,store=True):
        try:
            a=self.namemap[a]
            b=self.namemap[b]
            assert self.dprint("%s before %s" % (a,b))
            self.orderer[a][b]=-1
            self.orderer[b][a]=1
            if store:
                self.constraints.append((a,b))
        except KeyError:
            if a not in self.namemap:
                assert self.dprint("bad constraint: %s" % a)
            if b not in self.namemap:
                assert self.dprint("bad constraint: %s" % b)
            pass

    def after(self,a,b,store=True):
        try:
            a=self.namemap[a]
            b=self.namemap[b]
            assert self.dprint("%s after %s" % (a,b))
            self.orderer[a][b]=1
            self.orderer[b][a]=-1
            if store:
                self.constraints.append((b,a))
        except KeyError:
            if a not in self.namemap:
                assert self.dprint("bad constraint: %s" % a)
            if b not in self.namemap:
                assert self.dprint("bad constraint: %s" % b)
            pass

    def first(self,a):
        try:
            a=self.namemap[a]
            assert self.dprint("%s before everything" % a)
            for b in self.items:
                if a!=b and self.orderer[a][b]==0:
                    # don't need to store this result because we are
                    # setting all possible values
                    self.before(str(a),str(b),store=False)
        except KeyError:
            if a not in self.namemap:
                assert self.dprint("bad constraint: %s" % a)
            if b not in self.namemap:
                assert self.dprint("bad constraint: %s" % b)
            pass

    def last(self,b):
        try:
            b=self.namemap[b]
            assert self.dprint("%s after everything" % b)
            for a in self.items:
                if a!=b and self.orderer[a][b]==0:
                    # don't need to store this result because we are
                    # setting all possible values
                    self.after(str(b),str(a),store=False)
        except KeyError:
            if a not in self.namemap:
                assert self.dprint("bad constraint: %s" % a)
            if b not in self.namemap:
                assert self.dprint("bad constraint: %s" % b)
            pass

    def fixconstraints(self):
        assert self.dprint("fixing constraints:")
        assert self.dprint('before')
        assert self.dprint(self)
        for a,b in self.constraints:
            # Given a before b, look for any aprime that is also
            # before a (i.e. when aprime compared to a is -1), because
            # that aprime will also be before b
            for aprime in self.items:
                assert self.dprint("  checking [%s][%s]=%d" % (aprime,a,self.orderer[aprime][a]))
                if aprime!=a and self.orderer[aprime][a]==-1:
                    self.orderer[aprime][b]=-1
                    assert self.dprint("  setting [%s][%s]=%d" % (aprime,b,self.orderer[aprime][b]))
                    self.orderer[b][aprime]=1
                    assert self.dprint("  setting [%s][%s]=%d" % (b,aprime,self.orderer[b][aprime]))
        assert self.dprint('after')
        assert self.dprint(self)

        # Check for fully satisfied constraints
        for a in self.items:
            total=0
            for b in self.items:
                total+=self.orderer[a][b]
            self.total[a]=total

        assert self.dprint("totals:")
        assert self.dprint(self.total)
    
    def sorter(self,a,b):
        if self.total[a]<self.total[b]:
            return -1
        elif self.total[a]>self.total[b]:
            return 1
        return 0

    def sort(self):
        self.fixconstraints()
        self.sorted=[a for a in self.items]
        self.sorted.sort(self.sorter)
        return self.sorted
