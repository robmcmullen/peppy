"""Simple code to extract class & function docstrings from a module.

This code is used as an example in the library reference manual in the
section on using the parser module.  Refer to the manual for a thorough
discussion of the operation of this code.

The code has been extended by Stephen Davies for the Synopsis project. It now
also recognises parameter names and values, and baseclasses. Names are now
returned in order also.

July 25, 2006
Adapted from Synopsis package, assumed GPL-compatible or at least PSF
licensed, given the content of the Synopsis README.quick.
"""

import parser
import symbol
import token
import re

line_end = ((token.NEWLINE, ''), (token.INDENT, ''), (token.DEDENT, ''))

def format(tree, depth=-1):
    """Format the given tree up to the given depth.
    Numbers are replaced with their symbol or token names."""
    if isinstance(tree, int):
        try:
            return symbol.sym_name[tree]
        except KeyError:
            try:
                return token.tok_name[tree]
            except KeyError:
                return tree
    if type(tree) != tuple:
        return tree
    if depth == 0: return '...'
    ret = [format(tree[0])]
    for branch in tree[1:]:
        ret.append(format(branch, depth-1))
    return tuple(ret)

def stringify(tree):
    """Convert the given tree to a string"""
    if isinstance(tree, int): return ''
    if not isinstance(tree, tuple):
        return str(tree)
    strs = []
    for elem in tree:
        strs.append(stringify(elem))
    return ''.join(strs)

def get_docs(source):
    return ModuleInfo(parser.suite(source).totuple(), '')

def parse(content):
    stk = [get_docs(content)]
    names_ = []
    out = []
    outt = []
    docstring = {}
    p = 0
    lineno = 1
    while stk:
        cur = stk.pop()
        if cur is None:
            _ = outt.pop()
            __ = names_.pop()
            if len(outt) == 0:
                out.append(_)
            continue
        elif isinstance(cur, list):
            if len(cur) >= 1:
                stk.append(cur)
                stk.append(cur.pop())
            continue
            
        elif isinstance(cur, ModuleInfo):
            x = ''
        elif isinstance(cur, ClassInfo):
            _name = cur.get_name()
            x = 'class ' + _name
            gbm = cur.get_base_names()
            if gbm:
                x += '(%s)'%(', '.join(gbm))
                
        elif isinstance(cur, FunctionInfo):
            _name = cur.get_name()
            x = 'def %s(%s)'%(_name,
                ', '.join([(i, '%s=%s'%(i,j))[bool(j)]
                            for i,j in zip(cur.get_params(),
                                           cur.get_param_defaults())]))
        else:
            print "huh?"
            continue
        
        if x:
            z = 'def'
            if isinstance(cur, ClassInfo):
                z = 'class'
            g = re.compile("(?:^|\s)%s\s+%s(?:[:\s\(\\\\]|$)"%(z, _name),
                           re.MULTILINE).search(content, p)
            if g:
                #we found the definition
                h = g.group()
                s = g.start()
                s += len(h) - len(h.lstrip())
                lineno += content.count('\n', p, s)
                p = g.end()
            y = (x, (_name.lower(), lineno, _name), len(outt)*4, [])
            if len(outt):
                outt[-1][-1].append(y)
            
            
            doc = cur.get_docstring()
            _ = '.'.join(names_)
            if _:
                _ += '.'
            doc = ('%s%s\n%s'%(_, x.split(None, 1)[-1], doc)).rstrip()
            docstring.setdefault(_name, []).append(doc)
            if _name in ('__init__', '__new__') and outt:
                docstring.setdefault(outt[-1][1][2], []).append(doc)
            
            names_.append(_name)
            outt.append(y)        
            stk.append(None)
        
        names = [j for i,j in cur.get_names_and_info()]
        names.reverse()
        stk.append(names)
    
    if outt:
        out.append(outt[0])
    
    return out, docstring

class SuiteInfoBase:
    if 1:
        _docstring = ''
        _name = ''

    def __init__(self, tree = None, env={}):
        self._env = {} ; self._env.update(env)
        self._names = []
        ## self._class_info = {}
        ## self._class_names = []
        ## self._function_info = {}
        ## self._function_names = []
        if tree:
            self._extract_info(tree)
    
    def _extract_info(self, tree):
        # extract docstring
        if len(tree) == 2:
            found, vars = match(DOCSTRING_STMT_PATTERN[1], tree[1])
        else:
            found, vars = match(DOCSTRING_STMT_PATTERN, tree[3])
        if found:
            self._docstring = eval(vars['docstring'])
        # discover inner definitions
        for node in tree[1:]:
            found, vars = match(COMPOUND_STMT_PATTERN, node)
            if found:
                cstmt = vars['compound']
                if cstmt[0] == symbol.funcdef:
                    name = cstmt[2][1]
                    self._names.append((name, FunctionInfo(cstmt, env=self._env)))
                elif cstmt[0] == symbol.classdef:
                    name = cstmt[2][1]
                    self._names.append((name, ClassInfo(cstmt, env=self._env)))
            #found, vars = match(IMPORT_STMT_PATTERN, node)
            #we are going to ignore imports
    def get_docstring(self):
        return self._docstring

    def get_names_and_info(self):
        return self._names
    
    def get_name(self):
        return self._name

class FunctionInfo(SuiteInfoBase):
    def __init__(self, tree = None, env={}):
        self._name = tree[2][1]
        SuiteInfoBase.__init__(self, tree and tree[-1] or None, env)
        self._params = []
        self._param_defaults = []
        if tree[3][0] == symbol.parameters:
            if tree[3][2][0] == symbol.varargslist:
                args = list(tree[3][2][1:])
                while args:
                    if args[0][0] == token.COMMA:
                        pass
                    elif args[0][0] == symbol.fpdef:
                        self._params.append(stringify(args[0]))
                        self._param_defaults.append('')
                    elif args[0][0] == token.EQUAL:
                        del args[0]
                        self._param_defaults[-1] = stringify(args[0])
                    elif args[0][0] == token.DOUBLESTAR:
                        del args[0]
                        self._params.append('**'+stringify(args[0]))
                        self._param_defaults.append('')
                    elif args[0][0] == token.STAR:
                        del args[0]
                        self._params.append('*'+stringify(args[0]))
                        self._param_defaults.append('')
                    else:
                        print "Unknown symbol:",args[0]
                    del args[0]
    
    def get_params(self): return self._params
    def get_param_defaults(self): return self._param_defaults


class ClassInfo(SuiteInfoBase):
    def __init__(self, tree = None, env={}):
        self._name = tree[2][1]
        SuiteInfoBase.__init__(self, tree and tree[-1] or None, env)
        self._bases = []
        if tree[4][0] == symbol.testlist:
            for test in tree[4][1:]:
                found, vars = match(TEST_NAME_PATTERN, test)
                if found and vars.has_key('power'):
                    power = vars['power']
                    if power[0] != symbol.power: continue
                    atom = power[1]
                    if atom[0] != symbol.atom: continue
                    if atom[1][0] != token.NAME: continue
                    name = [atom[1][1]]
                    for trailer in power[2:]:
                        if trailer[2][0] == token.NAME: name.append(trailer[2][1])
                    if self._env.has_key(name[0]):
                        name = self._env[name[0]] + name[1:]
                        self._bases.append(name)
                        #print "BASE:",name
                    else:
                        #print "BASE:",name[0]
                        self._bases.append(name[0])
        else:
            pass

    def get_base_names(self):
        return self._bases

class ModuleInfo(SuiteInfoBase):
    def __init__(self, tree = None, name = "<string>"):
        self._name = name
        SuiteInfoBase.__init__(self, tree)
        if tree:
            found, vars = match(DOCSTRING_STMT_PATTERN, tree[1])
            if found:
                self._docstring = eval(vars["docstring"])

def match(pattern, data, vars=None):
    """Match `data' to `pattern', with variable extraction.

    pattern
        Pattern to match against, possibly containing variables.

    data
        Data to be checked and against which variables are extracted.

    vars
        Dictionary of variables which have already been found.  If not
        provided, an empty dictionary is created.

    The `pattern' value may contain variables of the form ['varname'] which
    are allowed to match anything.  The value that is matched is returned as
    part of a dictionary which maps 'varname' to the matched value.  'varname'
    is not required to be a string object, but using strings makes patterns
    and the code which uses them more readable.

    This function returns two values: a boolean indicating whether a match
    was found and a dictionary mapping variable names to their associated
    values.
    """
    if vars is None:
        vars = {}
    if type(pattern) is list:       # 'variables' are ['varname']
        vars[pattern[0]] = data
        return 1, vars
    if type(pattern) is not tuple:
        return (pattern == data), vars
    if len(data) != len(pattern):
        return 0, vars
    for pattern, data in map(None, pattern, data):
        same, vars = match(pattern, data, vars)
        if not same:
            break
    return same, vars

def dmatch(pattern, data, vars=None):
    """Debugging match """
    if vars is None:
        vars = {}
    if type(pattern) is list:       # 'variables' are ['varname']
        vars[pattern[0]] = data
        print "dmatch: pattern is list,",pattern[0],"=",data
        return 1, vars
    if type(pattern) is not tuple:
        print "dmatch: pattern is not tuple, pattern =",format(pattern)," data =",format(data)
        return (pattern == data), vars
    if len(data) != len(pattern):
        print "dmatch: bad length. data=",format(data,2)," pattern=",format(pattern,1)
        return 0, vars
    for pattern, data in map(None, pattern, data):
        same, vars = dmatch(pattern, data, vars)
        if not same:
            print "dmatch: not same"
            break
        print "dmatch: same so far"
    print "dmatch: returning",same,vars
    return same, vars


#  This pattern identifies compound statements, allowing them to be readily
#  differentiated from simple statements.
#
COMPOUND_STMT_PATTERN = (
    symbol.stmt,
    (symbol.compound_stmt, ['compound'])
    )


#  This pattern will match a 'stmt' node which *might* represent a docstring;
#  docstrings require that the statement which provides the docstring be the
#  first statement in the class or function, which this pattern does not check.
#
DOCSTRING_STMT_PATTERN = (
    symbol.stmt,
    (symbol.simple_stmt,
     (symbol.small_stmt,
      (symbol.expr_stmt,
       (symbol.testlist,
        (symbol.test,
         (symbol.and_test,
          (symbol.not_test,
           (symbol.comparison,
            (symbol.expr,
             (symbol.xor_expr,
              (symbol.and_expr,
               (symbol.shift_expr,
                (symbol.arith_expr,
                 (symbol.term,
                  (symbol.factor,
                   (symbol.power,
                    (symbol.atom,
                     (token.STRING, ['docstring'])
                     )))))))))))))))),
     (token.NEWLINE, '')
     ))

#  This pattern will match a 'test' node which is a base class
#
TEST_NAME_PATTERN = (
        symbol.test,
         (symbol.and_test,
          (symbol.not_test,
           (symbol.comparison,
            (symbol.expr,
             (symbol.xor_expr,
              (symbol.and_expr,
               (symbol.shift_expr,
                (symbol.arith_expr,
                 (symbol.term,
                  (symbol.factor,
                    ['power']
                  ))))))))))
     )

# This pattern will match an import statement
# import_spec is either:
#   NAME:import, dotted_name
# or:
#   NAME:from, dotted_name, NAME:import, NAME [, COMMA, NAME]*
# hence you must process it manually (second form has variable length)
IMPORT_STMT_PATTERN = (
      symbol.stmt, (
        symbol.simple_stmt, (
          symbol.small_stmt, ['import_spec']
        ), (
          token.NEWLINE, ''
        )
      )
)


#
#  end of file
