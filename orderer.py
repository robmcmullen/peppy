#!/usr/bin/env python

import os,sys
from debug import *
from cStringIO import StringIO

class DelayedOrderer(debugmixin):
    def __init__(self,name=None):
        self.items=[]
        self.constrainlist=[]
        self.name=name

    def __str__(self):
        return self.name

    def hasConstraints(self):
        return len(self.constraintlist)>0
        
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
                
class Menu(DelayedOrderer):
    def __init__(self,name,mode=None):
        DelayedOrderer.__init__(self,name)
        self.mode=mode

class MenuItem(DelayedOrderer):
    pass

class MenuItemGroup(DelayedOrderer):
    def __init__(self,name,*actions):
        DelayedOrderer.__init__(self,name)
        self.actions=actions
        dprint(self.actions)





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
        self.dprint(self.items)
        self.dprint('before')
        self.dprint(self)
        for c in items:
            if hasattr(c,'populate'):
                self.dprint("calling %s to populate constraints" % c.name)
                c.populate(self)
        self.dprint('after')
        self.dprint(self)
        
    def before(self,a,b,store=True):
        a=self.namemap[a]
        b=self.namemap[b]
        self.dprint("%s before %s" % (a,b))
        self.orderer[a][b]=-1
        self.orderer[b][a]=1
        if store:
            self.constraints.append((a,b))

    def after(self,a,b,store=True):
        a=self.namemap[a]
        b=self.namemap[b]
        self.dprint("%s after %s" % (a,b))
        self.orderer[a][b]=1
        self.orderer[b][a]=-1
        if store:
            self.constraints.append((b,a))

    def first(self,a):
        a=self.namemap[a]
        self.dprint("%s before everything" % a)
        for b in self.items:
            if a!=b and self.orderer[a][b]==0:
                # don't need to store this result because we are
                # setting all possible values
                self.before(str(a),str(b),store=False)

    def last(self,b):
        b=self.namemap[b]
        self.dprint("%s after everything" % b)
        for a in self.items:
            if a!=b and self.orderer[a][b]==0:
                # don't need to store this result because we are
                # setting all possible values
                self.after(str(b),str(a),store=False)

    def fixconstraints(self):
        self.dprint("fixing constraints:")
        self.dprint('before')
        self.dprint(self)
        for a,b in self.constraints:
            # Given a before b, look for any aprime that is also
            # before a (i.e. when aprime compared to a is -1), because
            # that aprime will also be before b
            for aprime in self.items:
                self.dprint("  checking [%s][%s]=%d" % (aprime,a,self.orderer[aprime][a]))
                if aprime!=a and self.orderer[aprime][a]==-1:
                    self.orderer[aprime][b]=-1
                    self.dprint("  setting [%s][%s]=%d" % (aprime,b,self.orderer[aprime][b]))
                    self.orderer[b][aprime]=1
                    self.dprint("  setting [%s][%s]=%d" % (b,aprime,self.orderer[b][aprime]))
        self.dprint('after')
        self.dprint(self)

        # Check for fully satisfied constraints
        for a in self.items:
            total=0
            for b in self.items:
                total+=self.orderer[a][b]
            self.total[a]=total

        self.dprint("totals:")
        self.dprint(self.total)
    
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
