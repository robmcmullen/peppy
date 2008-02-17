#! /usr/bin/env python
# -*- coding: iso-8859-1 -*-

"""Generate python dictionaries catalog from textual translation description.

This program converts a textual Uniforum-style message catalog (.po file) into
a python dictionary 

Based on msgfmt.py by Martin v. Löwis <loewis@informatik.hu-berlin.de>

"""

import sys, re, os, glob
from optparse import OptionParser

class MessageCatalog(object):
    def __init__(self, template):
        self.messages = {}
        self.template = {}
        self.encoding = None
        self.current_encoding = None
        self.loadTemplate(template)
    
    def addAlways(self, id, str, fuzzy):
        "Add a non-fuzzy translation to the dictionary."
        if not fuzzy:
            print ("adding template for %s" % id)
            self.template[id] = True
            if str:
                self.addCheck(id, str, fuzzy)
    
    def addCheck(self, id, str, fuzzy):
        "Add a non-fuzzy translation to the dictionary if it's a valid msgid."
        if id == "":
            match = re.search(r'charset=(\S*)\n', str)
            if match:
                self.current_encoding = match.group(1).lower()
                print("Found encoding %s" % self.current_encoding)
                if not self.encoding:
                    self.encoding = self.current_encoding
            
        if not fuzzy and str:
            if id in self.template and id not in self.messages:
                print ("adding translation for %s" % id)
                if self.current_encoding != self.encoding:
                    str = str.decode(self.current_encoding).encode(self.encoding)
                self.messages[id] = str
            else:
                for prefix in [u'', u'&']:
                    for suffix in [u'', u'...', u':']:
                        if not prefix and not suffix:
                            continue
                        keyword = prefix + id.decode(self.current_encoding) + suffix
                        if keyword in self.template and keyword not in self.messages:
                            print ("adding pre/suffixed translation for %s" % keyword)
                            if self.current_encoding != self.encoding:
                                str = str.decode(self.current_encoding).encode(self.encoding)
                            str = prefix.encode(self.encoding) + str + suffix.encode(self.encoding)
                            self.messages[keyword] = str
                
                

    def generateDict(self):
        "Return the generated dictionary"
        metadata = self.messages['']
        del self.messages['']
        return "# -*- coding: %s -*-\n#This is generated code - do not edit\nencoding = '%s'\ndict = %s"%(self.encoding, self.encoding, self.messages)

    def loadTemplate(self, filename):
        self.add = self.addAlways
        self.addPO(filename)
        self.add = self.addCheck

    def addPO(self, filename):
        ID = 1
        STR = 2

        print("loading translations from %s" % filename)
        try:
            lines = open(filename).readlines()
        except IOError, msg:
            print >> sys.stderr, msg
            sys.exit(1)
        self.current_encoding = 'utf-8'

        section = None
        fuzzy = 0

        # Parse the catalog
        lno = 0
        for l in lines:
            lno += 1
            # If we get a comment line after a msgstr, this is a new entry
            if l[0] == '#' and section == STR:
                self.add(msgid, msgstr, fuzzy)
                section = None
                fuzzy = 0
            # Record a fuzzy mark
            if l[:2] == '#,' and l.find('fuzzy'):
                fuzzy = 1
            # Skip comments
            if l[0] == '#':
                continue
            # Now we are in a msgid section, output previous section
            if l.startswith('msgid'):
                if section == STR:
                    self.add(msgid, msgstr, fuzzy)
                section = ID
                l = l[5:]
                msgid = msgstr = ''
            # Now we are in a msgstr section
            elif l.startswith('msgstr'):
                section = STR
                l = l[6:]
            # Skip empty lines
            l = l.strip()
            if not l:
                continue
            # XXX: Does this always follow Python escape semantics?
            try:
                l = eval(l)
                if section == ID:
                    msgid += l
                elif section == STR:
                    msgstr += l
                else:
                    print >> sys.stderr, 'Syntax error on %s:%d' % (filename, lno), \
                          'before:'
                    print >> sys.stderr, l
                    sys.exit(1)
            except SyntaxError:
                print >> sys.stderr, 'Syntax error on %s:%d' % (filename, lno)
                
        # Add last entry
        if section == STR:
            self.add(msgid, msgstr, fuzzy)
    
    def addMO(self, filename):
        temp = "converted-%s.po" % os.path.basename(filename)
        os.system('msgunfmt -o %s %s' % (temp, filename))
        # if it's a blank catalog, it won't be written, so check for it.
        if os.path.exists(temp):
            self.addPO(temp)
            os.remove(temp)
    
    def addFile(self, filename):
        if filename.endswith('mo'):
            self.addMO(filename)
        else:
            self.addPO(filename)

    def addDir(self, dir, canonical):
        if not canonical:
            return
        
        # If it's a LC_MESSAGES format directory, use all the files in
        # the directory
        choices = [canonical]
        if "_" in canonical:
            choices.append(canonical[0:2])
        for locale in choices:
            lcdir = "%s/%s/LC_MESSAGES" % (dir, locale)
            if os.path.isdir(lcdir):
                files = glob.glob("%s/*" % lcdir)
                print files
                for file in files:
                    self.addFile(file)
            else:
                # not LC_MESSAGES format; only look for canonical format files
                files = glob.glob("%s/*%s*" % (dir, locale))
                print files
                for file in files:
                    if os.path.isfile(file):
                        self.addFile(file)

    def save(self, outfile):
        # Compute output
        output = self.generateDict()

        try:
            open(outfile,"wb").write(output)
        except IOError,msg:
            print >> sys.stderr, msg

def processDir(outdir):
    catalogs = ['en_US']
    for poFile in glob.glob('i18n.in/*.po'):
        print poFile
        pyFile = po2dict.make(poFile)
        shutil.move(pyFile, '%s/%s' % (outdir, os.path.basename(pyFile)))
        
        catalogs.append(os.path.splitext(os.path.basename(pyFile))[0])
    
    fh = open('%s/%s' % (outdir, 'peppy_message_catalogs.py'), 'w')
    fh.write("supplied_translations = %s" % str(catalogs))

if __name__ == "__main__":
    usage="usage: %prog [-o file] template po-files"
    parser=OptionParser(usage=usage)
    parser.add_option("-a", action="store", dest="all",
                      default='.', help="process all po files in this directory as locales to be generated")
    parser.add_option("-c", action="store", dest="canonical",
                      default=None, help="canonical name of the locale")
    parser.add_option("-o", action="store", dest="output",
                      default=None, help="output file or directory")
    parser.add_option("-s", action="store_true", dest="system",
                      default=False, help="check system locale directories")
    (options, args) = parser.parse_args()

    if len(args) < 1:
        parser.usage()
    
    if options.all:
        if not options.output:
            options.output = ""
        catalogs = ['en_US']
        files = glob.glob(os.path.join(options.all, "*.po"))
        for file in files:
            canonical = os.path.basename(file)[0:-3]
            print("Processing locale %s" % canonical)
            po = MessageCatalog(args[0])
            po.addFile(file)
            for pofile in args[1:]:
                print("checking %s" % pofile)
                if os.path.isdir(pofile):
                    po.addDir(pofile, canonical)
                else:
                    po.addFile(pofile)
            po.save(os.path.join(options.output, canonical + ".py"))
            catalogs.append(canonical)
        fh = open(os.path.join(options.output, 'peppy_message_catalogs.py'), 'w')
        fh.write("supplied_translations = %s" % str(catalogs))
        
    elif options.canonical:
        po = MessageCatalog(args[0])
        for pofile in args[1:]:
            print("checking %s" % pofile)
            if os.path.isdir(pofile):
                po.addDir(pofile, options.canonical)
            else:
                po.addFile(pofile)
        if options.output:
            po.save(options.output)
        elif options.canonical:
            po.save(options.canonical + ".py")
