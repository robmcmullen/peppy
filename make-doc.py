#!/usr/bin/env python

import os,sys,re,os.path,time
from cStringIO import StringIO
from datetime import date
from optparse import OptionParser
from string import Template

module=None

namespace={
    'prog':None,
    'author':None,
    'author_email':None,
    'url':None,
    'description':None,
    'long_description': None,
    'packages': None,
    'cvs_version':None,
    'release_version':None,
    'version':None,
    'codename': None,
    'release_date':None, # should stat the file instead
    'release_file':None,
    'today':date.today().strftime("%d %B %Y"),
    'year':date.today().strftime("%Y"),
    'yearstart':'2006',
    'htmlBody':'',
    'preBody':'',
    }

def findLongDescription():
    # skip the opening one-line description and grab the first paragraph
    # out of the module's docstring to use as the long description.
    long_description = ''
    lines = module.__doc__.splitlines()
    for firstline in range(len(lines)):
        # skip until we reach a blank line
        if len(lines[firstline])==0 or lines[firstline].isspace():
            break
    if firstline<len(lines):
        firstline+=1
    for lastline in range(firstline,len(lines)):
        # stop when we reach a blank line
        if len(lines[lastline])==0 or lines[lastline].isspace():
            break
    long_description = " ".join(lines[firstline:lastline])
    namespace['long_description'] = long_description

def findPackages(mil=False):
    packages = []

    # find packages to be installed
    path = os.path.dirname(module.__file__)
    def addmodules(arg, dirname, names):
        if '__init__.py' in names:
            prefix = os.path.commonprefix((path, dirname))
            mod = "%s%s" % (module.__name__, dirname[len(prefix):].replace(os.sep,'.'))
            if mod not in packages:
                packages.append(mod)
    os.path.walk(path, addmodules, None)
    print "packages = %s" % packages
    if mil == False and 'peppy.hsi.mil' in packages:
        packages.remove('peppy.hsi.mil')
    namespace['packages'] = str(packages)

def setnamespace(mil=False):
    if module:
        defaults={
            'prog':'__name__',
            'version': '__version__',
            'codename': '__codename__',
            'author':'__author__',
            'author_email':'__author_email__',
            'url':'__url__',
            'download_url':'__download_url__',
            'description':'__description__',
            'license': '__license__',
            'keywords': '__keywords__',
            'coconuts': '__sir_not_appearing_in_this_film__',
            }
        
        for key,val in defaults.iteritems():
            if hasattr(module, val):
                namespace[key]=getattr(module, val)
            # print "%s=%s" % (key,val)
    
    findLongDescription()
    findPackages(mil)
    
    if int(namespace['yearstart'])<int(namespace['year']):
        namespace['yearrange']=namespace['yearstart']+'-'+namespace['year']
    else:
        namespace['yearrange']=namespace['year']



def store(keyword,infile):
    if isinstance(infile,str):
        fh=open(infile)
    else:
        fh=infile
    txt=fh.read()
    t=Template(txt)
    out=t.safe_substitute(namespace)
    namespace[keyword]=out

def remap(keyword,value):
    if value.startswith('$'):
        value=namespace[value[1:]]
    namespace[keyword]=value

def parse(infile):
    if isinstance(infile,str):
        fh=open(infile)
    else:
        fh=infile
    txt=fh.read()
    t=Template(txt)
    out=t.safe_substitute(namespace)
    return out

def parsedocstring(infile):
    if isinstance(infile,str):
        fh=open(infile)
    else:
        fh=infile
    doc=StringIO()
    count=0
    while count<2:
        line=fh.readline()
        if line.find('"""')>=0: count+=1
        doc.write(line)
    unparsed=fh.read()
    t=Template(doc.getvalue())
    out=t.safe_substitute(namespace)
    return out+unparsed

def parsechangelog(infile):
    if isinstance(infile, str):
        fh = open(infile)
    else:
        fh = infile
    doc=StringIO()
    doc.write("<h2>ChangeLog</h2>")
    release_date = ''
    version = ''
    show_items = False
    for line in fh:
        match=re.match('(\d+-\d+-\d+).*',line)
        if match:
            if show_items:
                doc.write("</ul>\n")
                show_items = False
            print 'found date %s' % match.group(1)
            release_date=date.fromtimestamp(time.mktime(time.strptime(match.group(1),'%Y-%m-%d'))).strftime('%d %B %Y')
        else:
            match=re.match('\s+\*\s*[Rr]eleased peppy-([\d\.]+)',line)
            if match:
                print 'found version %s' % match.group(1)
                version=match.group(1)
                doc.write("<h3>%s, released %s</h3>\n<ul>\n" % (version, release_date))
                show_items = True
            else:
                line = line.lstrip()
                if line.startswith('*'):
                    doc.write("<li>%s " % line[1:])
                else:
                    doc.write(line)
    return doc.getvalue()


if __name__=='__main__':
    usage="usage: %prog [-m module] [-o file] [-n variablename file] [-t template] [files...]"
    parser=OptionParser(usage=usage)
    parser.add_option("-m", action="store", dest="module",
                      help="module to import")
    
    parser.add_option("-o", action="store", dest="outputfile",
                      help="output filename")
    parser.add_option("-n", "--name", action="append", nargs=2,
                      dest="namespace", metavar="KEY FILENAME",
                      help="expand the named variable KEY with the contents of FILENAME")
    parser.add_option("-r", "--remapkey", action="append", nargs=2,
                      dest="remapkey", metavar="KEY1 KEY2",
                      help="remap the named variable KEY1 with the value of the named variable KEY2")
    parser.add_option("-k", "--keyvalue", action="append", nargs=2,
                      dest="keyvalue", metavar="KEY VALUE",
                      help="remap the named variable KEY with the supplied constant VALUE, or if VALUE begins with a $, with the value of that named variable.  Note that you probably have to escape the $ from the shell with \\$")
    parser.add_option("-t", "--template", action="store", dest="template",
                      help="filename of template file")
    parser.add_option("-p", "--print-namespace", action="store_true",
                      dest="printnamespace", help="print namespace and exit without processing")
    parser.add_option("--mil", action="store_true", default=False,
                      dest="mil", help="use mil modules")
    parser.add_option("-d", "--docstring-only", action="store_true",
                      dest="docstringonly", help="only variable-expand the named file's docstring only; leave the remaining contents unchanged.")
    parser.add_option("-c", "--changelog", action="store_true",
                      dest="changelog", help="create a changelog input file.")
    (options, args) = parser.parse_args()

    all=''

    if options.module:
        module=__import__(options.module)

    setnamespace(options.mil)

    # Static value setting should happen before anything
    if options.keyvalue:
        for keyword,value in options.keyvalue:
            print "keyword=%s value=%s" % (keyword,value)
            remap(keyword,value)

    if options.namespace:
        for keyword,filename in options.namespace:
            # print "keyword=%s filename=%s" % (keyword,filename)
            store(keyword,filename)

    if options.remapkey:
        for key1,key2 in options.remapkey:
            value=namespace[key2]
            print "keyword=%s value=%s" % (key1,value)
            remap(key1,value)

    if options.template:
        all=parse(options.template)

    if options.printnamespace:
        print namespace
        sys.exit()

    for filename in args:
        if options.docstringonly:
            txt = parsedocstring(filename)
        elif options.changelog:
            txt = parsechangelog(filename)
        else:
            txt = parse(filename)
        if options.outputfile:
            print 'saving to %s' % options.outputfile
            all += txt
        else:
            if filename.endswith('.in'):
                outfile = filename[:-3]
            else:
                outfile = filename+".out"
            fh = open(outfile,"w")
            fh.write(txt)
            fh.close()

    if options.outputfile:
        fh = open(options.outputfile,"w")
        fh.write(all)
        fh.close()
    else:
        print all
        
