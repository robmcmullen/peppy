#!/usr/bin/python
import time
import os
import re
import parser
import compiler
import traceback
import symbol
import token
from compiler import ast
from compiler import consts
#from plugins import exparse
import exparse

todoexp = re.compile('(>?[a-zA-Z0-9 ]+):(.*)', re.DOTALL)

_bad_todo = dict.fromkeys('if elif else def cdef class try except finally for while lambda'.split())
_bad_urls = dict.fromkeys('http ftp mailto news gopher telnet file'.split())

def is_url(left, right, ml=0):
    if left.lstrip().lower() in _bad_urls and right[:2] == '//':
        return 1
#    if not ml and _pype.STRICT_TODO and left[:1] != '>':
#        return 1
    return 0

def detectLineEndings(text):
    crlf_ = text.count('\r\n')
    lf_ = text.count('\n')
    cr_ = text.count('\r')
    mx = max(lf_, cr_)
    if not mx:
        return os.linesep
    elif crlf_ >= mx/2:
        return '\r\n'
    elif lf_ is mx:
        return '\n'
    else:# cr_ is mx:
        return '\r'

def leading(line):
    return len(line)-len(line.lstrip())

#------------------------------- C/C++ parser --------------------------------

defn = '(?:is+)*(?:is+\*+s+)?(?:is*::s*)?cs*\(a\)\s*{'
rep = [('a', '(?:\b|b|b(?:,s*b)*)'),
       ('b', '(?:i?[ \t\*&]*is*(?:\[[^\]]*\])*)'),
       ('c', '(?:i|operator[^\w]+)'),
       ('d', '(?:(?:is+)*(?:is+\*+s+)?is*;f*)'),
       ('i', '(?:[a-zA-Z_]\w*)'),
       ('s', '[ \t]'),
       ('f', '\s'),
       ('y', '(?:[dD][eE][fF][iI][nN][eE])')]

fcn = '(#ys+i\(i(?:,s*i)*\))|(?:(cs*\([^\)]*\))[^{;\)]*[;{])'
sdef = '(c)s*\('

for i,j in rep:
    try:
        _ = re.compile(j)
    except:
        print j
        raise
    fcn = fcn.replace(i,j)
    sdef = sdef.replace(i,j)

fcnre = re.compile(fcn)
sdefre = re.compile(sdef)

badstarts = []
for i in 'if for while switch case return'.split():
    badstarts.append(i+'(')
    badstarts.append(i+' ')
    badstarts.append(i+'\t')

ops = '+-=<>?%!~^&(|/"\''

def c_parser(source, line_ending, flat, wxYield):
    posn = 0
    lc = 1
    post = 0
    out = []
    docs = {}
    for i in fcnre.finditer(source):
        fcn = i.group(0).replace('\n', ' ')
        
        #update line count
        lc += post + source.count('\n', posn, i.start())
        post = 0
        post = source.count('\n', i.start(), i.end())
        posn = i.end()
        
        sm = sdefre.search(fcn)
        short = sm.group(1)
        
        #check for function-like macros
        if fcn.lower().startswith('#define'):
            out.append((fcn, (short.lower(), lc, short), 0, []))
            docs.setdefault(short, []).append(fcn[sm.start():])
            continue
        
        #handle the 'badstarts'
        cont = 0
        for j in badstarts:
            if fcn.startswith(j):
                cont = 1
                break
        if cont:
            continue
        
        #handle function calls
        pp = fcn.rfind(')')
        if fcn.endswith(';'):
            xx = fcn[pp+1:-1]
            if not xx.strip():
                continue
            for j in ops:
                if j in xx:
                    cont = 1
                    break
            if cont:
                continue
        
        #get the start of the definition
        linestart = source.rfind('\n', 0, i.start()) + 1 #yes, I really want this
        
        fcns = source[linestart:i.start()]
        dfcns = dict.fromkeys(fcns)
        
        #check for operators in the beginning; for things like...
        #x = fcncall(...) * X;
        for j in ops:
            if j in dfcns:
                cont = 1
                break
        if cont:
            continue
        
        if '[' not in short:
            docs.setdefault(short, []).append(fcn[sm.start():pp+1])
        #use the entire definition
        fcn = ' '.join(fcns.split() + fcn[:pp+1].split())
        out.append((fcn, (short.lower(), lc, short), 0, []))
    
    texp = todoexp
    todo = []
    line_no = 0
    for line in source.split(line_ending):
        line_no += 1
        ls = line.strip()
        if ls[:2] == '//':
            r = texp.match(ls, 2)
            if not r:
                continue
            
            tpl = r.groups()
            if is_url(*tpl):
                continue
            if tpl[0][:1] == '>':
                tpl = tpl[0][1:], tpl[1]
            todo.append((tpl[0].strip().lower(),
                      line_no,
                      tpl[1].count('!'),
                      tpl[1].strip()))
        #elif ...
    
    return out, docs.keys(), docs, todo

def slower_parser(source, _1, flat, _2):
    try:
        out, docstring = exparse.parse(source)
    except:
        #parse error, defer to faster parser
        return faster_parser(source, '\n', flat, _2)

    texp = todoexp
    bad_todo = _bad_todo
    todo = []
    for line_no, line in enumerate(source.split('\n')):
        ls = line.lstrip()
        if ls[:1] == '#':
            r = texp.match(ls, 1 + ls.startswith('##'))
            if r:
                tpl = r.groups()
                if tpl[0].split()[0] in bad_todo or is_url(*tpl):
                    continue
                if tpl[0][:1] == '>':
                    tpl = tpl[0][1:], tpl[1]
                todo.append((tpl[0].strip().lower(),
                        line_no+1,
                        tpl[1].count('!'),
                        tpl[1].strip()))
    
    return out, docstring.keys(), docstring, todo
#
def faster_parser(source, line_ending, flat, wxYield):
    texp = todoexp
    bad_todo = _bad_todo
    lines = source.split(line_ending)
    docstring = {} #new_kwl()
    todo = []
    
    out = []
    stk = []
    line_no = 0
##    SEQ = ('def ','class ')
    
    FIL = lambda A:A[1][2]
    
    def fun(i, line, ls, line_no, stk):
        try: wxYield()
        except: pass
        na = ls.find('(')
        ds = ls.find(':')
        if na == -1:
            na = ds
        if na != -1:
            if ds == -1:
                ds = na
            fn = ls[len(i):ds].strip()
            if fn:
                lead = len(line)-len(ls)
                while stk and (stk[-1][2] >= lead):
                    prev = stk.pop()
                    if stk: stk[-1][-1].append(prev)
                    else:   out.append(prev)
                nam = i+fn
                nl = nam.lower()
                f = ls[len(i):na].strip()
                
                if f in ('__init__', '__new__') and len(stk):
                    docstring.setdefault(stk[-1][1][-1], []).append("%s %s.%s"%(fn, '.'.join(map(FIL, stk)), f))
                stk.append((nam, (f.lower(), line_no, f), lead, []))
                docstring.setdefault(f, []).append("%s %s"%(fn, '.'.join(map(FIL, stk))))
                
    
    for line in lines:
        line_no += 1
        ls = line.lstrip()

        if ls[:4] == 'def ':
            fun('def ', line, ls, line_no, stk)
        elif ls[:5] == 'cdef ':
            fun('cdef ', line, ls, line_no, stk)
        elif ls[:6] == 'class ':
            fun('class ', line, ls, line_no, stk)
        elif ls[:1] == '#':
            r = texp.match(ls, 1 + ls.startswith('##'))
            if r:
                tpl = r.groups()
                if tpl[0].split()[0] in bad_todo or is_url(*tpl):
                    continue
                if tpl[0][:1] == '>':
                    tpl = tpl[0][1:], tpl[1]
                todo.append((tpl[0].strip().lower(),
                        line_no+1,
                        tpl[1].count('!'),
                        tpl[1].strip()))

        #elif ls[:3] == '#>>':
        #    fun('#>>', line, ls, line_no, stk)

    while len(stk)>1:
        a = stk.pop()
        stk[-1][-1].append(a)
    out.extend(stk)
    if flat == 0:
        return out, docstring.keys()
    elif flat==1:
        return docstring
    elif flat==2:
        return out, docstring.keys(), docstring
    else:
        return out, docstring.keys(), docstring, todo

def fast_parser(*args, **kwargs):
    return slower_parser(*args, **kwargs)

## (full, (lower, lineno, upper), indent, contents)

def latex_parser(source, line_ending, flat, _):
    texp = todoexp
    lines = source.split(line_ending)
    todo = []
    out = []
    stk = []
    line_no = 0
    sections = ('\\section', '\\subsection', '\\subsubsection')
    
    def f(which, line, ls, line_no, stk):
        if which in sections:
            ind = which.count('sub')
        elif stk:
            ind = 3
        else:
            ind = -1
        while stk and stk[-1][2] >= ind:
            it = stk.pop()
            if stk:
                stk[-1][-1].append(it)
            else:
                out.append(it)
        na = ls.find('{')
        ds = ls.find('}')
        if na > 0 and ds > 0:
            name = ls[na+1:ds].strip()
            if ind >= 0:
                stk.append((ls.rstrip(), (name.lower(), line_no, name), ind, []))
            else:
                out.append((ls.rstrip(), (name.lower(), line_no, name), 0, []))
    
    for line in lines:
        line_no += 1
        ls = line.lstrip()
        
        if ls[:1] == '%':
            r = texp.match(ls, 1)
            if r:
                tpl = r.groups()
                if is_url(*tpl):
                    continue
                if tpl[0][:1] == '>':
                    tpl = tpl[0][1:], tpl[1]
                todo.append((tpl[0].strip().lower(),
                             line_no,
                             tpl[1].count('!'),
                             tpl[1].strip()))
            continue
        elif ls[:6] == '\\label':
            f('\\label', line, ls, line_no, stk)
        for i in sections:
            if ls[:len(i)] == i:
                f(i, line, ls, line_no, stk)
                break
                
        

    while len(stk)>1:
        a = stk.pop()
        stk[-1][-1].append(a)
    out.extend(stk)
    if flat == 0:
        return out, []
    elif flat==1:
        return {}
    elif flat==2:
        return out, [], {}
    else:
        return out, [], {}, todo

#Are there any other non-opening tags?
no_ends = []
for i in ('br p input img area base basefont '
          'col frame hr isindex meta param').split():
    no_ends.append(i+' ')
    no_ends.append(i+'>')
    no_ends.append('/'+i+' ')
    no_ends.append('/'+i+'>')

def ml_parser(source, line_ending, flat, _):
    todo = []
    texp = todoexp
    bad_todo = _bad_todo
    for line_no, line in enumerate(source.split(line_ending)):
        if '<!-- ' in line and ' -->' in line:
            pass
        else:
            continue
        
        posn1 = line.find('<!-- ')
        posn2 = line.find(' -->')
        if posn1 > posn2:
            continue
        
        r = texp.match(line, posn1+5, posn2)
        
        if not r:
            continue
        
        tpl = r.groups()
        if is_url(tpl[0], tpl[1], 1):
            continue
        
        todo.append((tpl[0].strip().lower(),
                    line_no+1,
                    tpl[1].count('!'),
                    tpl[1].strip()))
    
    if flat == 0:
        return [], []
    elif flat==1:
        return {}
    elif flat==2:
        return [], [], {}
    else:
        return [], [], {}, todo

def preorder(h):
    #uses call stack; do we care?
    for i in h:
        yield i[1][2], i
        for j in preorder(i[3]):
            yield j

def _preorder(h):
    #uses explicit stack, may be slower, no limit to depth
    s = [h]
    while s:
        c = s.pop()
        yield c[1][2]
        s.extend(c[3][::-1])

_name_start = dict.fromkeys(iter('abcdefghijklmnopqrstuvwxyzABCDEFGHIJLKMNOPQRSTUVWXYZ_'))
_name_characters = dict(_name_start)
_name_characters.update(dict.fromkeys(iter('0123456789')))

def get_last_word(line):
    nch = _name_characters
    for i in xrange(len(line)):
        if line[-1-i] not in nch:
            break
    
    if line[-1-i] in _name_start:
        return line[-1-i:]
    return ''

'''
([('def foo(x, y=6, *args, **kwargs)', ('foo', 5, 'foo'), 0, []),
  ('class bar',
   ('bar', 9, 'bar'),
   0,
   [('def __init__(self, foo=a, bar={1:2})',
     ('__init__', 10, '__init__'),
     4,
     [])]),
  ('class Baz(object, int)',
   ('baz', 13, 'Baz'),
   0,
   [('def __init__(self, bar=(lambda:None))',
     ('__init__', 14, '__init__'),
     4,
     [('def goo()', ('goo', 16, 'goo'), 8, [])])])],
 '''

if __name__ == '__main__':
    a = '''import a, b, c

#todo: hello world

def foo(x, y=6, *args,
        **kwargs):
    return None

class bar:
    def __init__(self, foo=a, bar={1:2}):
        """blah!"""

class Baz(object, int):
    def __init__(self, bar=(lambda:None)):
        """blah 2"""
        def goo():
            pass
'''
    import pprint
    ## pprint.pprint(get_defs(a,1))
    #pprint.pprint(slower_parser(a, '\n', 3, lambda:None)[0])
    pprint.pprint(slower_parser(a, '\n', 3, lambda:None))
