#!/usr/bin/env python

import os, os.path, glob, po2dict, shutil
from optparse import OptionParser

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
    usage="usage: %prog [-o file]"
    parser=OptionParser(usage=usage)
    parser.add_option("-o", action="store", dest="output",
                      default="peppy/i18n", help="output directory")
    (options, args) = parser.parse_args()

    processDir(options.output)
