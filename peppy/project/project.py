# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
import os, re
import cPickle as pickle

from wx.lib.pubsub import Publisher

import peppy.vfs as vfs

from peppy.buffers import *
from peppy.sidebar import *
from peppy.lib.userparams import *
from peppy.lib.pluginmanager import *
from peppy.lib.processmanager import *



class CTAGS(InstancePrefs):
    """Exuberant CTAGS support for projects.
    
    Exuberant-ctags is a modern update to the classic Unix ctags program.  It
    scans files and creates relationships among the source files of a project.
    
    Peppy uses exuberant-ctags as way to cross-reference files within
    the project.  Rather than writing a similar program in python, it's
    much easier just to call an external program to do the work for you.
    But, because ctags is an external program, it must be installed
    before the ctags functionality can be used.  Check your system's
    package manager for instructions on how to add exuberant-ctags, or see
    U{ctags.sourceforge.net} for instructions.
    """
    # lookup table for kinds of ctags
    kind_of_tag = {
        'c': 'class name',
        'd': 'define',
        'e': 'enumerator',
        'f': 'function',
        'F': 'file name',
        'g': 'enumeration name',
        'm': 'member',
        'p': 'function prototype',
        's': 'structure name',
        't': 'typedef',
        'u': 'union name',
        'v': 'variable',
        }
    
    special_tags = {
        'file:': '(static scope)',
        }
    
    default_prefs = (
        StrParam('ctags_extra_args', '', 'extra arguments for the ctags command', fullwidth=True),
        StrParam('ctags_exclude', '', 'files, directories, or wildcards to exclude', fullwidth=True),
        IndexChoiceParam('tags_file_location',
                         ['project root directory', 'project settings directory'],
                         1, 'Where to store the tags file'),
        )
    
    def getTagFileURL(self):
        if self.tags_file_location == 0:
            base = self.project_top_dir
        else:
            base = self.project_settings_dir
        url = base.resolve2(ProjectPlugin.classprefs.ctags_tag_file_name)
        return url

    def regenerateTags(self):
        # need to operate on the local filesystem
        self.dprint(self.project_top_dir)
        if self.project_top_dir.scheme != "file":
            raise TypeError("Can only process ctags on local filesystem")
        
        ctags = ProjectPlugin.classprefs.ctags_command
        if not ctags:
            Publisher().sendMessage('peppy.log.error', "CTAGS program not set in project settings.")
            return
        
        cwd = str(self.project_top_dir.path)
        ctags_file = str(self.getTagFileURL().path)
        wildcards = self.ctags_exclude.split()
        excludes = " ".join(["--exclude=%s" % w for w in wildcards])
        
        # Put the output file last in this list because extra spaces at the end
        # don't get squashed like they do from the shell.  Ctags will actually
        # try to look for a filename called " ", which fails.
        args = "%s %s %s -o %s" % (ProjectPlugin.classprefs.ctags_args, self.ctags_extra_args, excludes, ctags_file)
        cmd = "%s %s" % (ProjectPlugin.classprefs.ctags_command, args)
        self.dprint(cmd)
        
        output = JobOutputSaver(self.regenerateFinished)
        ProcessManager().run(cmd, cwd, output)
    
    def regenerateFinished(self, output):
        self.dprint(output)
        if output.exit_code == 0:
            self.loadTags()
        else:
            Publisher().sendMessage('peppy.log.error', output.getErrorText())
    
    def loadTags(self):
        url = self.getTagFileURL()
        self.parseCtags(url)
    
    def parseCtags(self, filename):
        self.tags = {}
        tagre = re.compile('(.+)\t(.+)\t(.+);"\t(.+)')
        try:
            fh = vfs.open(filename)
            for line in fh:
                match = tagre.match(line)
                if match:
                    tag = match.group(1)
                    file = match.group(2)
                    addr = match.group(3)
                    fields = match.group(4)
                    self.dprint("tag=%s file=%s addr=%s field=%s" % (tag, file, addr, str(fields)))
                    if tag not in self.tags:
                        self.tags[tag] = []
                    self.tags[tag].append((file, addr, fields))
                    #dprint(self.tags[tag])
                else:
                    self.dprint(line)
        except LookupError, e:
            self.dprint("Tag file %s not found" % filename)
            pass
    
    def getTag(self, tag):
        return self.tags.get(tag, None)
    
    def getTagInfo(self, tag):
        """Get a text description of all the tags associated with the given
        keyword.
        
        Returns a string of text suitable to be used in a grep-style output
        reporter; that is, a bunch of lines starting with the string
        'filename:line number:' followed by descriptive text about each tag.
        """
        tags = self.getTag(tag)
        refs = []
        for t in tags:
            info = "%s:%s: %s  " % (t[0], t[1], tag)
            fields = t[2].split('\t')
            for field in fields:
                if ':' in field:
                    if field in self.special_tags:
                        info += self.special_tags[field]
                    else:
                        info += field + " "
                elif field in self.kind_of_tag:
                    info += "kind:" + self.kind_of_tag[field] + " "
            refs.append(info)
        if refs:
            text = os.linesep.join(refs) + os.linesep
        else:
            text = ''
        return text

    def getSortedTagList(self):
        tags = self.tags.keys()
        tags.sort()
        return tags


class KnownProject(object):
    """Special case object for a project that we know the path of, but haven't
    loaded the full information.
    
    """
    def __init__(self, url, name):
        self.url = url
        self.name = name
        
    def getProjectName(self):
        return self.name
    
    def getTopURL(self):
        return self.url
    
    def getKnownProject(self):
        return self



class ProjectInfo(CTAGS):
    """Main project support class for peppy.
    
    A project is simply a directory that contains related files.  The root
    directory of the project is indicated by a project settings directory,
    by default named ".peppy-project".  Any directory on the filesystem that
    contains the project settings directory will become a project directory.
    
    It unsupported and not recommended, but it is possible to nest projects
    inside other projects.  Files in the nested project will only report being
    members of the nested project, not the outer level project.
    """
    default_prefs = (
        StrParam('project_name', '', 'Project name'),
        DirParam('build_dir', '', 'working directory in which to build', fullwidth=True),
        StrParam('build_command', '', 'shell command to build project, relative to working directory', fullwidth=True),
        DirParam('run_dir', '', 'working directory in which to execute the project', fullwidth=True),
        StrParam('run_command', '', 'shell command to execute project, absolute path needed or will search current PATH environment variable', fullwidth=True),
        )
    
    def __init__(self, url):
        self.project_settings_dir = url
        self.project_top_dir = vfs.get_dirname(url)
        self.project_config = None
        self.loadPrefs()
        self.loadTags()
        self.process = None
    
    def __str__(self):
        return "ProjectInfo: settings=%s top=%s" % (self.project_settings_dir, self.project_top_dir)
    
    def getKnownProject(self):
        return KnownProject(self.getTopURL(), self.getProjectName())
    
    def getProjectName(self):
        return self.project_name
    
    def setProjectName(self, name):
        self.project_name = name
        self.savePrefs()
    
    def getTopURL(self):
        return self.project_top_dir
    
    def getSettingsRelativeURL(self, name=""):
        return self.project_settings_dir.resolve2(name)
    
    def getTopRelativeURL(self, name):
        return self.project_top_dir.resolve2(name)
    
    def loadPrefs(self):
        self.project_config = self.project_settings_dir.resolve2(ProjectPlugin.classprefs.project_file)
        try:
            fh = vfs.open(self.project_config)
            if fh:
                self.readConfig(fh)
            for param in self.iterPrefs():
                self.dprint("%s = %s" % (param.keyword, getattr(self, param.keyword)))
            self.dprint(self.configToText())
        except LookupError:
            self.dprint("Project file not found -- using defaults.")
            self.setDefaultPrefs()
    
    def savePrefs(self):
        try:
            fh = vfs.open_write(self.project_config)
            text = self.configToText()
            fh.write(text)
        except:
            self.dprint("Failed writing project config file")
    
    def registerProcess(self, job):
        self.process = job
    
    def deregisterProcess(self, job):
        self.process = None
    
    def isRunning(self):
        return bool(self.process)
    
    def build(self, frame):
        self.dprint("Compiling %s in %s" % (self.build_command, self.build_dir))
        output = JobOutputSidebarController(frame, self.registerProcess, self.deregisterProcess)
        ProcessManager().run(self.build_command, self.build_dir, output)
    
    def run(self, frame):
        self.dprint("Running %s in %s" % (self.run_command, self.run_dir))
        output = JobOutputSidebarController(frame, self.registerProcess, self.deregisterProcess)
        ProcessManager().run(self.run_command, self.run_dir, output)
    
    def stop(self):
        if self.process:
            self.process.kill()


if __name__== "__main__":
    app = wx.PySimpleApp()
    ctags = ProjectInfo(vfs.normalize("/home/rob/src/peppy-git/.peppy-project"))
    print ctags.getTag('GetValue')
    ctags.regenerateTags()
