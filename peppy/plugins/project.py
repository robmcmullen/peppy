# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Project support in peppy

This plugin provides support for projects, including individual templates for
projects, makefile and compilation support, and more.  Eventually.

Templates can exist as global templates, or can exist within projects that
will override the global templates.  Global templates are stored in the peppy
configuration directory, while project templates are stored within the project
directory.
"""
import os

from wx.lib.pubsub import Publisher

from peppy.yapsy.plugins import *
from peppy.actions import *
from peppy.lib.userparams import *

def findGlobalTemplate(subdir, mode, url):
    """Find the global template that belongs to the particular major mode
    
    @param mode: major mode instance
    @param url: url of file that is being created
    """
    filename = str(url)
    names = []
    if '.' in filename:
        ext = filename.split('.')[-1]
        names.append("%s/%s.%s" % (subdir, mode.keyword, ext))
    names.append("%s/%s" % (subdir, mode.keyword))
    for configname in names:
        try:
            dprint("Trying to load template %s" % configname)
            fh = wx.GetApp().config.open(configname)
            template = fh.read()
            return template
        except:
            pass
    template = "# template for %s\n\n" % str(url)
    return template

class ProjectPlugin(IPeppyPlugin):
    default_classprefs = (
        StrParam('project_directory', '.peppy-project', 'Directory used within projects to store peppy specific information'),
        StrParam('template_directory', 'templates', 'Directory used to store template files for given major modes'),
        )

    def initialActivation(self):
        if not wx.GetApp().config.exists(self.classprefs.template_directory):
            wx.GetApp().config.create(self.classprefs.template_directory)

    def activateHook(self):
        Publisher().subscribe(self.getTemplate, 'template.find')

    def deactivateHook(self):
        Publisher().unsubscribe(self.getTemplate)

    def getTemplate(self, msg):
        info = msg.data
        template = findGlobalTemplate(self.classprefs.template_directory, info['mode'], info['url'])
        if template:
            info['templates'].append([1, template])
