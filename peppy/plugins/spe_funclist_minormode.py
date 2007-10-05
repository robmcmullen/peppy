# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info

"""Function list minor mode from SPE.

Any major mode that supplies information in its getFunctionList method
will be able to work with this minor mode.
"""

import os, re

from wx.lib.evtmgr import eventManager

from peppy.yapsy.plugins import *
from peppy.minor import *
from peppy.debug import *
from peppy.menu import *
from peppy.lib.iconstorage import *

from peppy.spe.realtime import TreeCtrl
from peppy.spe import *


def getLexedItems(stc, classes):
    length = stc.GetTextLength()*2
    text = stc.GetStyledText(0, length)
    bits = (2**stc.GetStyleBits()) -1
    print "seaching for %s" % classes

    i=1 # styling bytes are the odd bytes
    parsed = []
    while i<length:
        # get the style, stripping off the the indicator bits
        style = ord(text[i]) & bits
        if style in classes:
            # it's a style we're interested in, so gather
            # characters until the style changes.
            found = i-1
            i+=2
            while i < length:
                s = ord(text[i]) & bits
                if style != s:
                    parsed.append((found, i-1, style, text[found:i-1:2]))
                    break
                i+=2
        else:
            i+=2
    print parsed



RE_DOCSTRING            = re.compile(r'(\n|\n__doc__\s*=(\s*|\s*\\\s*\n))("""([^"]*)"""|\'\'\'([^\']*)\'\'\'|"([^"]*)"|\'([^\']*)\')')
RE_DOCSTRING_FIRST      = re.compile(r'(|__doc__\s*=(\s*|\s*\\\s*\n))("""([^"]*)"""|\'\'\'([^\']*)\'\'\'|"([^"]*)"|\'([^\']*)\')')
RE_TODO                 = re.compile('.*#[ ]*TODO[ ]*:(.+)', re.IGNORECASE)
RE_SEPARATOR            = re.compile('^.*(#-{3})')
RE_SEPARATOR_HIGHLIGHT  = re.compile('^.*(#{4})')
RE_ENCODING             = re.compile('coding[:=]\s*([-\w.]+)', re.IGNORECASE)

class SPEFuncList(MinorMode, TreeCtrl):
    keyword="spe_funclist"

    default_classprefs = (
        IntParam('best_width', 150),
        IntParam('best_height', 500),
        IntParam('min_width', 100),
        IntParam('min_height', 100),
        )
    
    @classmethod
    def worksWithMajorMode(self, mode):
        if hasattr(mode, 'getFunctionList'):
            return True
        return False
    
    def __init__(self, major, parent):
        self.parentPanel = SPECompat
        TreeCtrl.__init__(self, parent=parent,
                          style=wx.TR_HAS_BUTTONS|wx.TR_HIDE_ROOT)

        self.major = major
        self.explore = self

        self.explore.SetBackgroundColour(wx.WHITE)
        self.root = self.explore.AddRoot('Right click to locate')
        
        icons = getIconStorage()
        icons.assign(self.explore)

        self.fl=self.major.getFunctionList()
        self.source = self.major.stc
        self.updateExploreGeneric()

        eventManager.Register(self.onSourceChange,wx.stc.EVT_STC_CHANGE,self.source)
        eventManager.Register(self.onSourceFromExplore,wx.EVT_TREE_ITEM_ACTIVATED,self.explore)
        if not info.DARWIN:
            #Mac has already always triangles
            eventManager.Register(self.onToggleExploreTree,wx.EVT_LEFT_DOWN,self.explore)
        eventManager.Register(self.onSourceFromExplore,wx.EVT_TREE_ITEM_MIDDLE_CLICK,self.explore)
        eventManager.Register(self.onSourceFromExplore,wx.EVT_TREE_ITEM_RIGHT_CLICK,self.explore)

    def paneInfoHook(self, paneinfo):
        paneinfo.Caption("SPE Function List")
        if not self.fl[0]:
            paneinfo.Hide()

    def deletePreHook(self):
        eventManager.DeregisterListener(self.onSourceChange)
        eventManager.DeregisterListener(self.onSourceFromExplore)
        if not info.DARWIN:
            eventManager.DeregisterListener(self.onToggleExploreTree)
        

    def updateExploreGeneric(self):
        if self.major.keyword == 'Python':
            self.updateExplore()
        else:
            classes = {wx.stc.STC_P_CLASSNAME: 'Class definition',
                       wx.stc.STC_P_DEFNAME: 'Function or method',
                       }
            getLexedItems(self.source, classes)


    def updateExplore(self,uml=0):
        """Updates explore in sidebar."""
        #get text
        try:
            text=self.source.GetText().split('\n')
        except:
            return
        #initialize
        if uml:         
            self.umlClass   = None
            previous    = 0
        classes         = {}
        n               = len(text)
        tryMode         = 0
        hierarchyIndex  = 0
        hierarchy       = [(-1,self.root)]
        separators      = []
        self.encoding   = None
        self.explore.CollapseAndReset(self.root)
        for line in range(len(text)):
            l           = text[line].strip()
            first       = l.split(' ')[0]
            sepa_hit    = RE_SEPARATOR.match(l)
            sepb_hit    = RE_SEPARATOR_HIGHLIGHT.match(l)
            encode_hit  = False
            if line < 3:
                if line == 0 and isUtf8(l):
                    self.encoding = "utf8"
                    encode_hit = True
                else:
                    enc = RE_ENCODING.search(l)
                    if enc:
                        self.encoding = str(enc.group(1))
                        encode_hit = True
            if first in ['class','def','import'] or encode_hit or (first == 'from' and 'import' in l):
                if 1 or l.find('(')!=-1 or l.find(':') !=-1 or first in ['from','import'] or encode_hit:
                    #indentation--------------------------------------------
                    indentation         = max(0,len(text[line])-
                        len(text[line].lstrip())-tryMode*4)
                    #situate in hierachy------------------------------------
                    hierarchyIndex      = 0
                    while hierarchyIndex+1<len(hierarchy) and \
                            hierarchy[hierarchyIndex+1][0]<indentation:
                        hierarchyIndex  += 1
                    hierarchy=hierarchy[:hierarchyIndex+1]
                    if uml and hierarchyIndex<=previous: 
                        umlAdd(classes,self.umlClass)
                        self.umlClass    = None
                    #get definition-----------------------------------------
                    if encode_hit:
                        l = self.encoding
                    else:
                        l = l.split('#')[0].strip()
                    i=1
                    if not(first in ['import','from'] or encode_hit):
                        search  = 1
                        rest    = ' '
                        while search and l[-1] != ':' and i+line<n:
                            #get the whole multi-line definition
                            next = text[line+i].split('#')[0].strip()
                            if next.find('class')==-1 and next.find('def')==-1 and next.find('import')==-1:
                                rest    += next
                                i       += 1
                            else:
                                search = 0
                        if rest[-1] == ':':l+= rest
                    #put in tree with color---------------------------------
                    l=l.split(':')[0].replace('class ','').replace('def ','').strip()
                    if separators: 
                        self.appendSeparators(separators,hierarchy,hierarchyIndex,uml)
                        separators      = []
                    if l:
                        item                = self.explore.AppendItem(hierarchy[hierarchyIndex][1],l,data=line)
                        intensity=max(50,255-indentation*20)
                        if encode_hit:
                            colour              = wx.Colour(intensity-50,0,intensity-50)
                            icon                = iconExpand = 'encoding.png'
                        elif first == 'class':
                            if uml:
                                umlAdd(classes,self.umlClass)
                                self.umlClass   = sm.uml.Class(name=l,data=line)
                                previous        = hierarchyIndex
                            colour              = wx.Colour(intensity,0,0)
                            icon                = 'class.png'
                            iconExpand          = 'class.png'
                        elif first in ['import','from']:
                            colour              = wx.Colour(0,intensity-50,0)
                            icon                = iconExpand = 'import.png'
                        else:
                            if uml and self.umlClass: self.umlClass.append(l)
                            colour          = wx.Colour(0,0,intensity)
                            icon            = iconExpand = 'def.png'
                        self.explore.SetItemTextColour(item,colour)
                        self.explore.SetItemImage(item,
                            self.parentPanel.iconsListIndex[icon],
                            which=wx.TreeItemIcon_Normal)
                        if first=='class':
                            self.explore.SetItemImage(item,
                                self.parentPanel.iconsListIndex[iconExpand],
                                which       = wx.TreeItemIcon_Expanded)
                        hierarchy.append((indentation,item))
            elif sepa_hit:
                #separator
                pos = sepa_hit.end()
                colours=l[pos:].split('#')
                if len(colours)==3:
                    s       = sm.rstrip(colours[0],'_')
                    fore    = '#'+colours[1][:6]
                    back    = '#'+colours[2][:6]
                else:
                    s=sm.rstrip(l[pos:],'-')
                    fore=wx.Colour(128,128,128)
                    back=None
                if s.strip(): separators.append((s,line,fore,back))
            elif sepb_hit:
                #highlighted separator (yellow)
                pos = sepb_hit.end()
                s   = sm.rstrip(l[pos:],'-')
                if s.strip(): separators.append((s,line,wx.Colour(0,0,0),wx.Colour(255,255,0)))
            elif first=='try:':
                tryMode         += 1
            elif first[:6]=='except':
                tryMode         = max(0,tryMode-1)
            elif first[:7]=='finally':
                tryMode         = max(0,tryMode-1)
        self.appendSeparators(separators,hierarchy,hierarchyIndex,uml)
        if uml: umlAdd(classes,self.umlClass)
        #expand root of explore
        #self.explore.Expand(self.root)
        #if self.parentPanel.exploreVisible: ...
        assert self.dprint(hierarchy)
        self.explore.Update()
        return classes

    def appendSeparators(self,separators,hierarchy,hierarchyIndex,uml):
        explore = self.explore
        for separator in separators:
            label,line,fore,back=separator
            sep=explore.AppendItem(hierarchy[hierarchyIndex][1],label,data=line)
            explore.SetItemBold(sep)
            explore.SetItemTextColour(sep,fore)
            if back:explore.SetItemBackgroundColour(sep,back)
            explore.SetItemImage(sep,self.parentPanel.iconsListIndex['separator.png'])
            if uml and self.umlClass: self.umlClass.append(label,t=sm.uml.SEPARATOR)

    def onSourceChange(self,event):
        self.eventChanged = True

    def onSourceFromExplore(self,event):
        """Jump to source line by clicking class or function in explore."""
        line=self.explore.GetPyData(event.GetItem())
        self.scrollTo(line,select='line')
            
    def onToggleExplore(self,event):
        """Toggle item between collapse and expand."""
        self.explore.Toggle(event.GetItem())
            
    def onToggleExploreTree(self,event):
        event.Skip()
        self.toggleExploreSelection = True
        
    def onToggleExploreSelection(self):
        self.explore.Toggle(self.explore.GetSelection())
        
    def scrollTo(self,line=0,column=0,select='pos',scroll=0):
        source  = self.source
        source.EnsureVisible(line)
        #line    = source.VisibleFromDocLine(line)
        linePos = source.PositionFromLine(line)
        pos     = linePos+column
        if select=='line':
            source.SetSelection(linePos, source.GetLineEndPosition(line))
        else: #select=='pos':
            source.GotoPos(pos)
        source.ScrollToLine(line)
        source.ScrollToColumn(0)
        source.SetFocus()



class SPEFuncListPlugin(IPeppyPlugin):
    def getMinorModes(self):
        yield SPEFuncList
