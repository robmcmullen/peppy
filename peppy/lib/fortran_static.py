#!/usr/bin/env python
"""Program to statically analyze Fortran code

"""

import sys, os, os.path, re, copy
from optparse import OptionParser
from StringIO import StringIO
from logging import debug, info, warning

import gprof2dot

from peppy.lib.serializer import PickleSerializerMixin

debugmode = False

comment_cre = re.compile(r"^[c*!].+$", re.IGNORECASE)
program_unit_cre = re.compile("^      (PROGRAM|SUBROUTINE|INTEGER FUNCTION|REAL FUNCTION|DOUBLE PRECISION FUNCTION|LOGICAL FUNCTION|CHARACTER\*1 FUNCTION|FUNCTION|BLOCK DATA)\s*([a-zA-Z0-9_]+)\s*(\(([a-zA-Z0-9_,]+)\))?", re.IGNORECASE)
subroutine = re.compile("(?: +|\))CALL\s+([a-zA-Z0-9_]+)", re.IGNORECASE)
stop = re.compile("(?: +|\))STOP\s*(.+)?", re.IGNORECASE)
external = re.compile("^ +EXTERNAL\s+(.+)$", re.IGNORECASE)
data = re.compile("^ +DATA\s+(.+)$", re.IGNORECASE)
common = re.compile("^ +COMMON/([a-zA-Z0-9_]+)/\s*(.+)$", re.IGNORECASE)
do_loop = re.compile("^ +DO\s*([0-9]+)?\s*([A-Z0-9_]+)\s*=(.+)$", re.IGNORECASE)
if_clauses = re.compile("^ +(IF|ELSE\s*IF)(.+)$", re.IGNORECASE)
gotos = re.compile("^.*(GOTO|GO TO)(.+)$", re.IGNORECASE)
indentation = re.compile("^((    )+)(.+)$", re.IGNORECASE)

def split(filename):
    fh = open(filename)
    out = None
    for line in fh:
        match = program_unit_cre.match(line)
        if match:
            print "%s %s" % (match.group(1), match.group(2))
            current = "%s.f" % match.group(2).lower()
            out = open(current, "wb")
        if out:
            out.write(line)

class FixedFormatLineReader(object):
    def __init__(self, filename):
        self.fh = open(filename)
        self.comments = 0
    
    def __call__(self):
        compound = []
        for line in self.fh:
            if len(line) < 6:
                self.comments += 1
                continue
            match = comment_cre.match(line)
            if match:
                self.comments += 1
                continue
            if line[5] == " " and compound:
                whole = self.joinCompound(compound)
                yield whole
                self.comments = 0
                compound = []
            compound.append(line)
        if compound:
            whole = self.joinCompound(compound)
            yield whole
    
    def joinCompound(self, compound):
        first = True
        whole = ""
        for line in compound:
            if len(line) > 72:
                line = line[0:72]
            if first:
                line = line.rstrip()
            else:
                line = line[6:].strip()
            whole += line
            first = False
        return whole.lower()


class Callable(object):
    func_before_paren = re.compile("([a-zA-Z0-9_]+)\s*$")
        
    def __init__(self, name, callable_type, argument_string):
        self.name = name
        self.callable_type = callable_type
        if argument_string:
            self.argument_string = argument_string
            self.argument_list = set(argument_string.split(","))
        else:
            self.argument_string = ""
            self.argument_list = set()
        self.body = []
        self.callees = set()
        self.called_by = set()
        self.common_blocks = set()
        self.stops = []
        
        self.gprof = None
        self.displayed = False
        self.displayed_edges = set()
        self.num_comments = 0
        self.num_data = 0
        self.loc = 0
        self.num_if_clauses = 0
        self.num_gotos = 0
        self.num_do_loops = 0
        self.num_calls = 0
        self.num_levels = [0]*10
    
    def __str__(self):
        return "%s %s(%s): %s lines, %d loc (%d data), %d comment lines, common blocks %s, calls %s" % (self.callable_type, self.name, self.argument_string, len(self.body), self.loc, self.num_data, self.num_comments, str(self.getCommonBlocks()), str(self.getCallees()))
    
    @classmethod
    def csv_header(self, sep="|"):
        return sep.join(["Procedure Type", "Name", "Num Args", "Executable Lines", "L1 Indent", "L2 Indent", "L3 Indent", "L4 Indent", "L5 Indent", ">L5 Indent", "Data Statements", "Comment Lines", "Do Loops", "If Clauses", "GOTOs", "Num Common Blocks", "Num Calls", "Unique Calls", "Num Called By", "Argument List", "Common Blocks", "Calls", "Called By"])
    
    def csv(self, sep="|"):
        commons = self.getCommonBlocks()
        callees = self.getCallees()
        called_by = self.getCalledBy()
        return sep.join([
            self.callable_type,
            self.name,
            str(len(self.argument_list)),
            str(self.loc),
            str(self.num_levels[1]),
            str(self.num_levels[2]),
            str(self.num_levels[3]),
            str(self.num_levels[4]),
            str(self.num_levels[5]),
            str(reduce(lambda a,b:a+b,self.num_levels[6:])),
            str(self.num_data),
            str(self.num_comments),
            str(self.num_do_loops),
            str(self.num_if_clauses),
            str(self.num_gotos),
            str(len(commons)),
            str(self.num_calls),
            str(len(callees)),
            str(len(called_by)),
            self.argument_string,
            ",".join(commons),
            ",".join(callees),
            ",".join(called_by),
            ])
    
    def isFunction(self):
        return self.callable_type.endswith("function")
    
    def isBlockData(self):
        return self.callable_type == "block data"
    
    def hasCallees(self):
        return bool(self.callees)
    
    def hasStops(self):
        return bool(self.stops)
    
    def getCallees(self):
        c = list(self.callees)
        c.sort()
        return c
    
    def getCommonBlocks(self):
        c = list(self.common_blocks)
        c.sort()
        return c
    
    def getCalledBy(self):
        c = list(self.called_by)
        c.sort()
        return c
    
    def addBody(self, line, comments=0):
        self.body.append(line)
        # Remove any line numbers from matches
        line = "      " + line[6:]
        match = external.match(line)
        if match:
            possible = match.group(1).strip()
            print("External: %s" % possible)
            for each in possible.split(","):
                each = each.strip()
                if each in self.argument_list:
                    print("External %s in arg list." % each)
                else:
                    print("External %s must be function." % each)
                    self.num_calls += 1
                    self.callees.add(each)
        match = data.match(line)
        if match:
            self.num_data += 1
        else:
            self.loc += 1
        match = common.match(line)
        if match:
            name = match.group(1).strip().lower()
            self.common_blocks.add(name)
        match = do_loop.match(line)
        if match:
            self.num_do_loops += 1
        match = if_clauses.match(line)
        if match:
            self.num_if_clauses += 1
        match = gotos.match(line)
        if match:
            self.num_gotos += 1
        self.num_comments += comments
        line = line[6:]
        match = indentation.match(line)
        if match:
            level = len(match.group(1))/4
            #print "INDENT: %s, level=%d" % (match.group(1), level)
            self.num_levels[level] += 1
    
    def scan(self, functions):
        print("Scanning %s" % self.name)
        #print("  Possible functions: %s" % functions)
        for line in self.body:
            match = subroutine.search(line)
            if match:
                callee = match.group(1)
                self.num_calls += 1
                self.callees.add(callee)
            match = stop.search(line)
            if match:
                reason = match.group(1)
                if not reason:
                    reason = "Reason for STOP unspecified"
                print("Stop!!! %s" % reason)
                self.stops.append(reason)
            if "(" in line:
                #print("Scanning line: %s" % line)
                self.scanLineForFunction(line, functions)
    
    def scanLineForFunction(self, line, functions):
        # open paren seems to be the only way to tell if a function call
        # happens.  You can't check for "=" because the return value might be
        # used in a comparison
        parts = line.split("(")
        #print(parts)
        for part in parts[:-1]:
            match = self.func_before_paren.search(part)
            if match:
                possible = match.group(1).strip()
                #print possible
                if possible in functions:
                    print "Found function %s in %s" % (possible, line)
                    self.num_calls += 1
                    self.callees.add(possible)
    
    def writeDot(self, fh, callee_map, exclude, no_callees=False):
        names = list(self.callees)
        names.sort()
        for callee in names:
            if callee not in exclude and callee not in self.displayed_edges:
                try:
                    c = callee_map[callee]
                    if c.hasCallees() or no_callees:
#                        fh.write('  "%s" -> "%s" [style=solid dir="both" arrowtail=dot];\n' % (self.name, callee))
                        fh.write('  "%s" -> "%s" [color="#777777" style=solid arrowsize="0.5"];\n' % (self.name, callee))
                        self.displayed_edges.add(callee)
                except KeyError:
                    print("Unknown callee: %s" % callee)
        if not self.displayed and self.hasCallees():
            if self.hasStops():
                fh.write('  "%s" [color=red];\n' % self.name)
#            else:
#                fh.write('  "%s" [color="#444444"];\n' % self.name)
    
    def findChildren(self, children, callee_map, exclude, no_callees=False):
        names = list(self.callees)
        for callee in names:
            if callee not in exclude:
                try:
                    c = callee_map[callee]
                    if c.hasCallees() or no_callees:
                        children.add(callee)
                        c.findChildren(children, callee_map, exclude)
                except KeyError:
                    print("Unknown callee: %s" % callee)


class FortranStaticAnalysis(PickleSerializerMixin):
    """Static analysis of Fortran code
    
    """
    default_serialized_filename = "fortran.static-analysis"
    
    def __init__(self, name="", serialized_filename=None, regenerate=False, pickledata=None):
        PickleSerializerMixin.__init__(self)
        self.createVersion1()
        self.name = name
        if serialized_filename:
            if not regenerate:
                self.loadStateFromFile(serialized_filename)
            self.serialized_filename = serialized_filename
        elif pickledata is not None:
            self.loadStateFromBytes(pickledata)
        else:
            self.serialized_filename = None
        
    def getSerializedFilename(self):
        if self.serialized_filename is not None:
            return self.serialized_filename
        if self.name:
            return "%s.static-analysis" % self.name
        return self.default_serialized_filename
    
    def createVersion1(self):
        self.name = ""
        self.callables = {}
        self.block_data = set()
    
    def packVersion1(self):
        return (self.name, self.callables, self.block_data)
    
    def unpackVersion1(self, data):
        self.name = data[0]
        self.callables = data[1]
        self.block_data = data[2]
    
    def isEmpty(self):
        return len(self.callables) == 0

    def __str__(self):
        lines = [Callable.csv_header()]
        names = self.callables.keys()
        names.sort()
        for name in names:
            lines.append(self.get_csv_line(name))
        return "\n".join(lines)
    
    def get_csv_line(self, name):
        c = self.callables[name]
        return c.csv()
    
    def write_csv_subset(self, filename, names):
        fh = open(filename, "w")
        header = Callable.csv_header()
        fh.write("%s\n" % header)
        for name in names:
            if name: # skip blank padded entries
                line = self.get_csv_line(name)
                fh.write("%s\n" % line)
        fh.close()
        
    def scan(self, filename):
        current = None
        reader = FixedFormatLineReader(filename)
        for line in reader():
            # More than one function might be in the file
            match = program_unit_cre.match(line)
            if match:
                #print "%s %s(%s)" % (match.group(1), match.group(2), match.group(4))
                if current is not None:
                    print current
                name = match.group(2)
                current = Callable(name, match.group(1), match.group(4))
                if name in self.callables:
                    print "WARNING: %s redefined from %s" % (name, self.callables[name])
                self.callables[name] = current
                
                if match.group(1) == "program":
                    self.name = match.group(2)
            elif current is not None:
                current.addBody(line, reader.comments)
    
    def summary(self):
        num_func = 0
        num_block_data = 0
        num_block_data_loc = 0
        num_loc = 0
        num_comment_lines = 0
        num_do_loops = 0
        num_if_clauses = 0
        num_gotos = 0
        for c in self.callables.values():
            if c.isBlockData():
                num_block_data += 1
                num_block_data_loc += c.loc
            else:
                num_func += 1
                num_loc += c.loc
                num_comment_lines += c.num_comments
                num_do_loops += c.num_do_loops
                num_if_clauses += c.num_if_clauses
                num_gotos += c.num_gotos
            print c.callees
            for name in c.callees:
                try:
                    callee = self.callables[name]
                    if c.name not in callee.called_by:
                        callee.called_by.add(c.name)
                except:
                    pass
        print "Num functions: %d\n  LOC=%d\n  Comments=%d\n  Do Loops=%d\n  If Clauses=%d\n  GOTOs=%d\nNum Block Data: %d\n  LOC=%d" % (num_func, num_loc, num_comment_lines, num_do_loops, num_if_clauses, num_gotos, num_block_data, num_block_data_loc)
    
    def analyze(self):
        functions = self.getFunctionList()
        print("Pass 1: collecting connections...")
        for c in self.callables.values():
            c.scan(functions)
            
        print("Pass 2: finding block data...")
        for c in self.callables.values():
            if c.isBlockData():
                print("Found block data: %s" % c.name)
                self.block_data.add(c)
    
    def getCallableNames(self):
        names = self.callables.keys()
        names.sort()
        return names

    def getCallable(self, name):
        name = name.lower()
        return self.callables[name]

    def getFunctionList(self):
        functions = set()
        for c in self.callables.values():
            if c.isFunction():
                functions.add(c.name)
        print sorted(list(functions))
        return functions
    
    def isolate(self, name):
        """Return a new FortranStaticAnalysis class limiting the results to
        only the specified function and those it calls
        
        """
        s = FortranStaticAnalysis(name)
        s.addCalleesToCallables(name, self)
        return s
    
    def addCalleesToCallables(self, name, other):
        print "adding %s" % name
        the_callable = other.callables[name]
        self.callables[name] = the_callable
        for callee_name in the_callable.callees:
            if callee_name not in self.callables:
                self.addCalleesToCallables(callee_name, other)
    
    def makeSubgraph(self, label, parents, exclude):
        group = set(parents)
        for name in parents:
            try:
                c = self.callables[name]
                c.findChildren(group, self.callables, exclude)
            except KeyError:
                pass
        
        subgraph = """  subgraph "cluster_%s" {
    label="%s";
%s
    }
""" % (label, label, "\n".join(["  \"%s\"" % s for s in sorted(list(group))]))
        return subgraph
    
    def makeDot(self, filename=None, exclude=None, fh=None, rankdir="LR", no_callees=False):
        if exclude is None:
            exclude = set()
        else:
            exclude = set(exclude)
        
        for c in self.block_data:
            exclude.add(c.name)
        if filename is not None:
            fh = open(filename, "wb")
        fh.write("""digraph callgraph {
  size="600,600"
  pad="2"
  rankdir=%s
  center=""
  color="blue"
""" % rankdir)
        self.makeDotEdges(fh, exclude, no_callees)
        
        fh.write("}\n")
        if filename is not None:
            fh.close()
    
    def makeDotEdges(self, fh, exclude, no_callees=False):
        names = self.callables.keys()
        names.sort()
        for name in names:
            if name in exclude:
                continue
            c = self.callables[name]
            if c not in self.block_data:
                c.writeDot(fh, self.callables, exclude, no_callees)
        
#        parents = ["cd1", "cd1a", "cd2", "cd2a", "cd2b", "cd2c", "cd2e",
#                   "cd3", "cd3a", "cd4", "cd5"]
#        subgraph = self.makeSubgraph("Tape 5 Input", parents, exclude)
#        fh.write(subgraph)
        
#        parents = ["dgrd"]
#        subgraph = self.makeSubgraph("DGRD", parents, exclude)
#        fh.write(subgraph)
        
#        parents = ["trans"]
#        subgraph = self.makeSubgraph("Trans", parents, exclude)
#        fh.write(subgraph)
#        
#        parents = ["geodrv", "geoerr"]
#        subgraph = self.makeSubgraph("Geometry", parents, exclude)
#        fh.write(subgraph)
    
    def makeCSV(self, filename):
        fh = open(filename, "w")
        fh.write(str(self))
        fh.close()


class FortranDotWriter(gprof2dot.DotWriter):
    def begin_graph(self, title):
        self.write('digraph "%s" {\n' % title)
        self.write('  size="500,500"\n')
        self.write('  pad="2"\n')

    def graph(self, profile, theme, stats, exclude, title="profile"):
        for function in profile.functions.itervalues():
            if function.name.endswith("_"):
                function.name = function.name[:-1]
                if function.name == "MAIN_":
                    function.name = stats.name
                    function.display_time = profile[gprof2dot.TIME]
                    function.events = {}
                    
                print function.name
                
                try:
                    callee = stats.callables[function.name]
                    callee.gprof = function
                    print function.name, callee
                except KeyError:
                    pass

        self.begin_graph(title)

        fontname = theme.graph_fontname()

        self.attr('graph', fontname=fontname, ranksep=0.25, nodesep=0.125, rankdir=theme.rankdir)
        self.attr('node', fontname=fontname, shape="box", style="filled", fontcolor="white", width=0, height=0)
        self.attr('edge', fontname=fontname)

#        for function in profile.functions.itervalues():
        names = stats.callables.keys()
        names.sort()
        for name in names:
            if name in exclude:
                continue
            try:
                fstat_caller = stats.callables[name]
                fstat_caller.displayed = True
            except:
                fstat_caller = None
                continue
            if fstat_caller in stats.block_data:
                continue
            
            function = fstat_caller.gprof
            if function:
                self.writeNode(function, fstat_caller, stats, exclude)
            else:
                fstat_caller.writeDot(self.fp, stats.callables, exclude)

        stats.makeDotEdges(self.fp, exclude)

        self.end_graph()
    
    def writeNode(self, function, fstat_caller, stats, exclude):
        if fstat_caller and not fstat_caller.hasCallees():
            return

        labels = []
        if function.process is not None:
            labels.append(function.process)
        if function.module is not None:
            labels.append(function.module)
        labels.append(function.name)
        for event in gprof2dot.TOTAL_TIME_RATIO, gprof2dot.TIME_RATIO:
            if event in function.events:
                label = event.format(function[event])
                labels.append(label)
        if hasattr(function, "display_time"):
            labels.append(u"%ss" % (function.display_time,))
        elif function.called is not None:
            labels.append(u"%u\xd7" % (function.called,))
            

        if function.weight is not None:
            weight = function.weight
        else:
            weight = 0.0

        label = '\n'.join(labels)
        self.node(function.name, 
            label = label, 
            color = self.color(theme.node_bgcolor(weight)), 
            fontcolor = self.color(theme.node_fgcolor(weight)), 
            fontsize = "%.2f" % theme.node_fontsize(weight),
        )
        
        order = []
        for call in function.calls.itervalues():
            callee = profile.functions[call.callee_id]
            if callee.name in exclude:
                continue
            order.append((callee.name, call, callee))
        order.sort()
                        
        for name, call, callee in order:
            try:
                fstat_callee = stats.callables[name]
                if not fstat_callee.hasCallees():
                    continue
            except:
                continue
            labels = []
            for event in gprof2dot.TOTAL_TIME_RATIO, gprof2dot.CALLS:
                if event in call.events:
                    label = event.format(call[event])
                    labels.append(label)

            if call.weight is not None:
                weight = call.weight
            elif callee.weight is not None:
                weight = callee.weight
            else:
                weight = 0.0

            label = '\n'.join(labels)

            self.edge(function.name, callee.name, 
                label = label, 
                color = self.color(theme.edge_color(weight)), 
                fontcolor = self.color(theme.edge_color(weight)),
                fontsize = "%.2f" % theme.edge_fontsize(weight), 
                penwidth = "%.2f" % theme.edge_penwidth(weight), 
                labeldistance = "%.2f" % theme.edge_penwidth(weight), 
                arrowsize = "%.2f" % theme.edge_arrowsize(weight),
            )
            if fstat_caller:
                fstat_caller.displayed_edges.add(callee.name)

class StaticComparison(object):
    def __init__(self, a, b):
        self.a = a
        self.b = b
    
    def compare(self):
        fa = self.a.getCallableNames()
        fb = self.b.getCallableNames()
        print "Comparison:"
        print fa
        print fb
        
        both = sorted(list(set(fa).intersection(set(fb))))
        print "In both: %d" % len(both)
        print both
        
        aonly = sorted(list(set(fa) - set(fb)))
        print "In set A only: %d" % len(aonly)
        print aonly
        
        bonly = sorted(list(set(fb) - set(fa)))
        print "In set B only: %d" % len(bonly)
        print bonly
        
        print "Zipped:"
        if len(aonly) < len(bonly):
            aonly.extend([""] * (len(bonly) - len(aonly)))
        elif len(bonly) < len(aonly):
            bonly.extend([""] * (len(aonly) - len(bonly)))
        if len(both) < len(aonly):
            both.extend([""] * (len(aonly) - len(both)))
        elif len(aonly) < len(both):
            aonly.extend([""] * (len(both) - len(aonly)))
            bonly.extend([""] * (len(both) - len(bonly)))
        print "In both|A only|B only"
        print "\n".join(["|".join(s) for s in zip(both, aonly, bonly)])
        
        fh = open("both.csv", "w")
        header = Callable.csv_header()
        fh.write("%s|%s\n" % (header, header))
        for name in both:
            if name: # skip blank padded entries
                line_a = self.a.get_csv_line(name)
                line_b = self.b.get_csv_line(name)
                fh.write("%s|%s\n" % (line_a, line_b))
        fh.close()
        
        self.a.write_csv_subset("a.csv", aonly)
        self.b.write_csv_subset("b.csv", bonly)


if __name__ == "__main__":
    usage="usage: %prog unified_diff [...]"
    parser=OptionParser(usage=usage)
    parser.add_option(
        "-o", type="string", dest="output", default="",
        help="Output filename for dot file [default: %default]")
    parser.add_option(
        "-t", action="store_true", dest="test", default=False,
        help="Display extra information useful while testing")
    parser.add_option(
        "--no-callees", action="store_true", dest="no_callees", default=False,
        help="Show ends of subroutine chains; those subroutines that don't call anything else")
    parser.add_option(
        '--strip-fortran',
        action="store_true", dest="strip_fortran", default=False,
        help="strip trailing underscore from GNU Fortran names")
    parser.add_option(
        '--ignore-stops',
        action="store_true", dest="ignore_stops", default=False,
        help="don't include information about stops in the gall graph")
    parser.add_option(
        '--skew',
        type="float", dest="theme_skew", default=1.0,
        help="skew the colorization curve.  Values < 1.0 give more variety to lower percentages.  Value > 1.0 give less variety to lower percentages")
    parser.add_option(
        '-r', '--rankdir',
        type="string", dest="rankdir", default="LR",
        help="rankdir: LR or UR.  The layout order of the nodes in the graph [default %default]")
    parser.add_option(
        '-p', '--profile',
        type="string", dest="prof", default="",
        help="Specify the gprof profile file")
    parser.add_option(
        '-n', '--node-thres', metavar='PERCENTAGE',
        type="float", dest="node_thres", default=0.0,
        help="eliminate nodes below this threshold [default: %default]")
    parser.add_option(
        '-e', '--edge-thres', metavar='PERCENTAGE',
        type="float", dest="edge_thres", default=0.0,
        help="eliminate edges below this threshold [default: %default]")
    parser.add_option(
        "-c", "--compare", action="store_true", dest="compare", default=False,
        help="Enter files for comparison.  Use +a and +b as markers to control files on the argument list that belong to each set")
    parser.add_option(
        "--isolate", type="string", dest="isolate", default="",
        help="Isolate a function and return only information about that function and those it calls]")
    parser.add_option(
        "-s", type="string", dest="serialize_filename", default="",
        help="Use data from serialized filename [default: %default]")
    parser.add_option(
        "-d", dest="dot", default="",
        help="Create graphviz .dot file")
    (options, args) = parser.parse_args()
    Testing=options.test
    if len(args)==0:
        parser.print_usage()
    
    exclude = ['wwarn', 'wwarnf', 'wwarn8', 'wwarnw', 'initcd', 'wrtbuf', 'opnfl', 'errmsg', 'gets01', 'gets05', 'gets15', 'flclos', 'fnames', 'fnambn', 'cool0', 'm3ddb', 'putchr', 'putsng', 'putint', 'putdbl', 'qgausn']
    exclude = ['wwarn', 'wwarnf', 'wwarn8', 'wwarnw', 'initcd', 'wrtbuf', 'opnfl', 'errmsg', 'gets01', 'gets05', 'gets15', ]
    exclude = ['initcd', 'wrtbuf', 'opnfl', 'errmsg', 'gets01', 'gets05', 'gets15', ]
    exclude = ['errmsg', 'gets01', 'gets05', 'gets15', ]
    exclude = ['initcd', 'wrtbuf', 'opnfl',]
    exclude = ['opnfl',]
    exclude = ['wwarn', 'wwarnf', 'wwarn8', 'wwarnw', 'opnfl',]
    
    if options.compare:
        stats_a = FortranStaticAnalysis()
        stats_b = FortranStaticAnalysis()
        stats = stats_a
        for name in args:
            if name == "+a":
                stats = stats_a
            elif name == "+b":
                stats = stats_b
            else:
                stats.scan(name)
        stats_a.analyze()
        stats_a.summary()
        stats_b.analyze()
        stats_b.summary()
        compare = StaticComparison(stats_a, stats_b)
        compare.compare()
    else:
        if options.serialize_filename and os.path.exists(options.serialize_filename):
            stats = FortranStaticAnalysis(serialized_filename=options.serialize_filename)
        else:
            stats = FortranStaticAnalysis()
            for name in args:
                stats.scan(name)
            stats.analyze()
            stats.summary()
            stats.saveStateToFile()
        
        if options.prof:
            theme = gprof2dot.TEMPERATURE_COLORMAP
            if options.theme_skew:
                theme.skew = options.theme_skew
            theme.rankdir = options.rankdir
            fh = open(options.prof, 'rt')
            parser = gprof2dot.GprofParser(fh)
            profile = parser.parse()
            profile.prune(options.node_thres/100.0, options.edge_thres/100.0)
            root, ext = os.path.splitext(options.prof)
            if not options.output:
                options.output = "%s.dot" % root
            fh = open(options.output, 'wb')
            dot = FortranDotWriter(fh)
            dot.graph(profile, theme, stats, exclude, title=root)
            fh.close()
            print(options.output)
            root, ext = os.path.splitext(options.output)
            print("%s.ps" % root)
        elif options.isolate:
            print "Isolating %s" % options.isolate
            i = stats.isolate(options.isolate)
            i.summary()
        elif options.dot:
            if not options.output:
                options.output = "modsrc.dot"
            stats.makeDot(options.output, exclude)
            #print stats
            stats.makeCSV(options.output + ".csv")
        else:
            for name in args:
                callable = stats.getCallable(name)
                print callable
                print "\n".join(callable.body)

