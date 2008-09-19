#!/usr/bin/env python

import os,sys,re,os.path,time, subprocess
from cStringIO import StringIO
from datetime import date
from optparse import OptionParser
from string import Template

module=None

def findChangeLogVersion(options):
    fh=open("ChangeLog")
    release_date = date.today().strftime("%d %B %Y")
    version = "0.0.0"
    codename = ""
    for line in fh:
        match = re.match('(\d+-\d+-\d+).*',line)
        if match:
            if options.verbose: print 'found date %s' % match.group(1)
            release_date = date.fromtimestamp(time.mktime(time.strptime(match.group(1),'%Y-%m-%d'))).strftime('%d %B %Y')
        match = re.match('\s+\*\s*[Rr]eleased peppy-([0-9]+\.[0-9]+\.[0-9]+) \"(.+)\"',line)
        if match:
            if options.verbose: print 'found version %s' % match.group(1)
            version = match.group(1)
            codename = match.group(2)
            break
        release_date = None
    if release_date is None:
        release_date = date.today().strftime("%d %B %Y")
    return version, release_date, codename

def findLatestInGit(options):
    version = ""
    tags = subprocess.Popen(["git-tag", "-l"], stdout=subprocess.PIPE).communicate()[0]
    for tag in tags.splitlines():
        match = re.match(r'([0-9]+\.[0-9]+\.[0-9]+)$', tag)
        if match:
            found = match.group(1)
            if found > version:
                version = found
            if options.verbose: print "found %s, latest = %s" % (found, version)
    return version

def getCurrentGitPatchlevel(options):
    version = findLatestInGit(options)
    text = subprocess.Popen(["git-rev-list", "%s..HEAD" % version], stdout=subprocess.PIPE).communicate()[0]
    md5s = text.splitlines()
    patchlevel = len(md5s)
    version = "%s.%d" % (version, patchlevel)
    if options.verbose: print version
    return version


if __name__=='__main__':
    usage="usage: %prog [-m module] [-o file] [-n variablename file] [-t template] [files...]"
    parser=OptionParser(usage=usage)
    parser.add_option("-v", "--verbose", action="store_true",
                      dest="verbose", help="print debugging info")
    parser.add_option("-m", action="store", dest="module",
                      help="module to import")
    
    parser.add_option("-o", action="store", dest="outputfile",
                      help="output filename")
    parser.add_option("-c", "--codename", action="store",
                      dest="codename", help="codename to use for the new release")
    parser.add_option("--version", action="store_true",
                      dest="version", help="display current version and exit")
    (options, args) = parser.parse_args()

    changelog_version, dum, codename = findChangeLogVersion(options)
    version = getCurrentGitPatchlevel(options)
    if options.version:
        print version
        sys.exit()
    
    if version.startswith(changelog_version):
        if options.codename and options.codename != codename:
            print "Codename mismatch!"
            print "ChangeLog has '%s'" % codename
            print "Command line specified: '%s'" % options.codename
            print "Update version number if you want to change codenames"
            sys.exit()
    elif not options.codename:
        # new version means codename must be specified
        print "Codename must be specified on command line when changing versions"
        sys.exit()

    if options.module:
        module=__import__(options.module)
    
        if not options.outputfile:
            options.outputfile = "%s/_%s_version.py" % (options.module, options.module)

    if options.outputfile:
        print options.outputfile
        text = os.linesep.join(["version = '%s'" % version,
                                "codename = '%s'" % codename])
        fh = open(options.outputfile,"wb")
        fh.write(text)
        fh.close()
