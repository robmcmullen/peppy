#!/usr/bin/env python

import os,sys,re,os.path,time, subprocess
from cStringIO import StringIO
from datetime import date
from optparse import OptionParser
from string import Template
from distutils.version import StrictVersion

module=None

def findChangeLogVersion(options):
    fh = open("ChangeLog")
    release_date = date.today().strftime("%d %B %Y")
    version = "0.0.0"
    codename = ""
    for line in fh:
        match = re.match('(\d+-\d+-\d+).*',line)
        if match:
            if options.verbose: print 'found date %s' % match.group(1)
            release_date = date.fromtimestamp(time.mktime(time.strptime(match.group(1),'%Y-%m-%d'))).strftime('%d %B %Y')
        match = re.match('\s+\*\s*[Rr]eleased peppy-([0-9]+\.[0-9]+(?:\.[0-9]+)?) \"(.+)\"',line)
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
    version = StrictVersion("0.0")
    tags = subprocess.Popen(["git-tag", "-l"], stdout=subprocess.PIPE).communicate()[0]
    for tag in tags.splitlines():
        match = re.match(r'([0-9]+\.[0-9]+(?:(?:\.[0-9]+|[ab][0-9]+))?)$', tag)
        if match:
            found = StrictVersion(match.group(1))
            if found > version:
                version = found
            if options.verbose: print "found %s, latest = %s" % (found, version)
    return str(version)

def findReleasesOf(tag, options):
    base = tag + "."
    tags = subprocess.Popen(["git-tag", "-l"], stdout=subprocess.PIPE).communicate()[0]
    releases = []
    for tag in tags.splitlines():
        if tag.startswith(base):
            releases.append(tag)
    if options.verbose: print releases
    return releases

def getCurrentGitMD5s(tag, options):
    text = subprocess.Popen(["git-rev-list", "%s..HEAD" % tag], stdout=subprocess.PIPE).communicate()[0]
    md5s = text.splitlines()
    return md5s

def getCurrentGitPatchlevel(options):
    tag = findLatestInGit(options)
    if tag.endswith("pre"):
        version = tag[:-3]
    else:
        md5s = getCurrentGitMD5s(tag, options)
        patchlevel = len(md5s)
        version = "%s.%d" % (tag, patchlevel)
    if options.verbose: print version
    return tag, version

def getGitChangeLogSuggestions(tag, options):
    if options.verbose: print tag
    subtags = findReleasesOf(tag, options)
    subtags[0:0] = [tag]
    top = "HEAD"
    subtags.reverse()
    suggestions = []
    for version in subtags:
        suggestions.append("Released %s" % version)
        text = subprocess.Popen(["git-log", "--pretty=format:%s", "%s..%s" % (version, top)], stdout=subprocess.PIPE).communicate()[0]
        lines = text.splitlines()
        print lines
        pat = re.compile("Fixed (\#[0-9]+:\s+)?(.+)")
        for line in lines:
            found = pat.match(line)
            if found:
                if found.group(1):
                    suggestions.append("* %s" % found.group(2))
                else:
                    suggestions.append("* fixed %s" % found.group(2))
            else:
                suggestions.append("* %s" % line)
        
        top = version
    return suggestions

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
    parser.add_option("-f", action="store_true",
                      dest="fixed", help="display list of bugs fixed since last major release")
    (options, args) = parser.parse_args()

    changelog_version, dum, codename = findChangeLogVersion(options)
    last_tag, version = getCurrentGitPatchlevel(options)
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
    
    if options.fixed:
        suggestions = getGitChangeLogSuggestions(last_tag, options)
        for line in suggestions:
            print line
