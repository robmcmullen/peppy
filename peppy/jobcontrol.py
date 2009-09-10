# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""Process Control Mixin
"""

import os, stat, sys, re, time

import wx
import wx.stc
from wx.lib.pubsub import Publisher

import peppy.vfs as vfs
from peppy.stcbase import *
from peppy.debug import *
from peppy.sidebar import *
from peppy.context_menu import ContextMenuMixin

from peppy.lib.userparams import *
from peppy.lib.processmanager import *


class JobControlMixin(JobOutputMixin, ClassPrefs):
    """Process handling mixin to run scripts based on the current major mode.
    
    This mixin provides some common interfacing to run scripts that are
    tied to a major mode.  An interpreter classpref is provided that links
    a major mode to a binary file to run scripts in that mode.  Actions
    like RunScript and StopScript are tied to the presense of this mixin
    and will be automatically enabled when they find a mode has the
    interpreter_exe classpref.
    """
    #: Is the full path required to be specified in interpreter_exe?
    full_path_required = False
    
    default_classprefs = (
        UserListParamStart('interpreter', ['interpreter_exe', 'interpreter_args'], 'Current interpreter profile', 'Profile name for an interpreter for this major mode.  Multiple profiles may be created that can call different interpreter programs or the same interepreter with different arguments.'),
        PathParam('interpreter_exe', '', 'Program that can interpret this text and return results on standard output', fullwidth=True),
        StrParam('interpreter_args', '', 'Standard arguments to be used with the interpreter', fullwidth=True),
        UserListParamEnd('interpreter'),
        BoolParam('autosave_before_run', True, 'Automatically save without prompting before running script'),
        IndexChoiceParam('output_log',
                         ['use minor mode', 'use sidebar'],
                         1, 'Does the output stay in the tab (minor mode) or visible to all tabs in the frame (major mode)'),
        )
    
    def getInterpreterProfiles(self):
        """Return the list of interpreter profile names currently available
        
        @returns: tuple containing the list of items and the integer index
        pointing to the default item.
        """
        return self.classprefs._getAllSubscripts("interpreter_exe", "interpreter")
    
    def setDefaultInterpreterProfile(self, index):
        """Set the default interpreter profile to the specified index
        
        @param index: integer index into the list of profiles that sets the new
        default profile.
        """
        items, default = self.getInterpreterProfiles()
        #dprint(items[index])
        self.classprefs.interpreter = items[index]
        self.classprefs._updateDependentKeywords("interpreter")

    def getInterpreterArgs(self):
        """Hook to pass arguments to the command interpreter"""
        # FIXME: Why did I put interpreterArgs as an instance attribute?
        #dprint(hasattr(self, "interpreterArgs"))
        if hasattr(self, "interpreterArgs"):
            return self.interpreterArgs
        return self.classprefs.interpreter_args

    def getScriptPath(self):
        """Hook to specify the filename to be run by the interpreter.
        
        This defaults to the full pathname of the buffer on the local machine,
        but this method can be used as a hook to modify the filename to point
        to an arbitrary location.
        """
        return self.buffer.getFilename()

    def getScriptArgs(self):
        """Hook to specify any arguments passed to the script itself.
        
        scriptArgs are saved as an instance attribute so they can be used as
        defaults the next time you run the script.
        """
        #dprint(hasattr(self, "scriptArgs"))
        if hasattr(self, "scriptArgs"):
            return self.scriptArgs
        return ""
    
    def getCommandLine(self, bangpath=None):
        """Return the entire command line of the job to be started.
        
        If allowed by the operating system, the script is parsed for a
        bangpath and will be executed directly if it exists.  Otherwise,
        the command interpreter will be used to start the script.
        """
        if self.buffer.url.scheme != "file":
            msg = "You must save this file to the local filesystem\nbefore you can run it through the interpreter."
            dlg = wx.MessageDialog(wx.GetApp().GetTopWindow(), msg, "Save the file!", wx.OK | wx.ICON_ERROR )
            retval=dlg.ShowModal()
            return
        script = self.getScriptPath()
        if bangpath:
            if wx.Platform == '__WXMSW__':
                # MSW doesn't pass to a shell, so simulate a bangpath by pulling
                # out the script name and using that as the interpreter.
                interpreter = bangpath.rstrip()
                tmp = interpreter.lower()
                i = interpreter.find(".exe")
                if i > -1:
                    args = interpreter[i + 4:]
                    interpreter = interpreter[:i + 4]
                else:
                    args = self.getInterpreterArgs()
                cmd = '"%s" %s "%s" %s' % (interpreter, args,
                                       script, self.getScriptArgs())
            else:
                # Rather than calling the script directly, simulate how the
                # operating system uses the bangpath by calling the bangpath
                # program with the path to the script supplied as the argument
                script = script.replace(' ', '\ ')
                cmd = "%s %s %s" % (bangpath, script, self.getScriptArgs())
        else:
            interpreter = self.getInterpreterExe()
            if wx.Platform == '__WXMSW__':
                interpreter = '"%s"' % interpreter
                script = '"%s"' % script
            else:
                # Assuming that Mac is like GTK...
                interpreter = interpreter.replace(' ', '\ ')
                script = script.replace(' ', '\ ')
                pass
            cmd = "%s %s %s %s" % (interpreter, self.getInterpreterArgs(),
                                   script, self.getScriptArgs())
        #dprint(cmd)
        return cmd
    
    def bangpathModificationHook(self, path):
        """Hook method to modify the bang path as read from the first line in
        the script.
        
        Note that the passed-in string will have already had the "#!" characters
        stripped off, so only the pathname and arguments will exist.
        """
        return path
    
    def getInterpreterExe(self):
        """Provided for subclasses to modify the interpreter executable as
        given in the classprefs.
        """
        return self.classprefs.interpreter_exe
        
    def startInterpreter(self, argstring=None):
        """Interface used by actions to start the interpreter.
        
        This method is the outside interface to the job control mixin to
        start the interpreter.  See the RunScript action for an example
        of its usage in practice.
        """
        if argstring is not None:
            self.scriptArgs = argstring
            
        bangpath = None
        first = self.GetLine(0)
        if first.startswith("#!"):
            bangpath = self.bangpathModificationHook(first[2:].rstrip())
            
        msg = None
        path = self.getInterpreterExe()
        if bangpath is None:
            if not path:
                msg = "No interpreter executable set.\n\nMust set the executable name in preferences or\ninclude a #! specifier as the first line in the file."
            elif self.full_path_required:
                if os.path.exists(path):
                    if os.path.isdir(path):
                        msg = "Interpreter executable:\n\n%s\n\nis not a valid file.  Locate the\ncorrect executable in the preferences." % path
                else:
                    msg = "Interpreter executable not found:\n\n%s\n\nLocate the correct path to the executable\nin the preferences." % path

        if msg:
            self.frame.showErrorDialog(msg, "Problem with interpreter executable")
        elif hasattr(self, 'process'):
            self.frame.setStatusText("Already running a process.")
        elif self.saveScript():
            cmd = self.getCommandLine(bangpath)
            self.prepareOutputHook()
            wx.CallAfter(self.startCommandLine, cmd)
    
    def prepareOutputHook(self):
        """Hook for subclass to do something to initialize the output log
        
        """
        pass
    
    def saveScript(self):
        """Save the file before executing the script.
        
        @return True if save successful, False otherwise.
        """
        if not self.isInterpreterURLSchemeValid():
            return False
        elif self.buffer.modified and not self.classprefs.autosave_before_run:
            msg = "You must save this file before you\ncan run it through the interpreter."
            self.frame.showErrorDialog(msg, "Save the file!")
            return False
        else:
            if not self.save():
                self.frame.showErrorDialog("Error attempting to save file:\n\n%s\n\nInterpreter was not started." % self.status_info.getLastMessage(), "File Save Error")
                return False
        return True
    
    def isInterpreterURLSchemeValid(self):
        """Check that the interpreter can process the URL scheme
        
        Defaults to only being able to process file:// URLs
        """
        if self.buffer.url.scheme != "file":
            msg = u"%s\n\nis not a regular file on your hard disk.\nThe URL must start with file:// to be run\nby this interpreter." % unicode(self.buffer.url)
            self.frame.showErrorDialog(msg, "URL Scheme Error!")
            return False
        return True
    
    def expandCommandLine(self, cmd):
        """Expand the command line to include the filename of the buffer"""
        filename = self.buffer.url.path.get_name()
        if '%' in cmd:
            cmd = cmd % filename
        else:
            cmd = "%s %s" % (cmd, filename)
        return cmd
    
    def startCommandLine(self, cmd, expand=False):
        """Attempt to create a process using the command line"""
        if expand:
            cmd = self.expandCommandLine(cmd)
        if self.classprefs.output_log == 0:
            output = self
        else:
            output = JobOutputSidebarController(self.frame, self.registerProcess, self.deregisterProcess)
        ProcessManager().run(cmd, self.buffer.cwd(), output)

    def registerProcess(self, job):
        self.process = job
    
    def deregisterProcess(self, job):
        del self.process
    
    def stopInterpreter(self):
        """Interface used by actions to kill the currently running job.
        
        This method is the outside interface to the job control mixin to
        stop the currently running job.  See the StopScript action for an
        example of its usage in practice.
        """
        if hasattr(self, 'process'):
            self.process.kill()
    
    def startupCallback(self, job):
        """Callback from the JobOutputMixin when a job is successfully
        started.
        """
        self.process = job
        self.log = self.findMinorMode("OutputLog")
        if self.log:
            text = "\n" + job.getStartMessage()
            self.log.showMessage(text)

    def stdoutCallback(self, job, text):
        """Callback from the JobOutputMixin for a block of text on stdout."""
        if self.log:
            self.log.showMessage(text)

    def stderrCallback(self, job, text):
        """Callback from the JobOutputMixin for a block of text on stderr."""
        if self.log:
            self.log.showMessage(text)

    def finishedCallback(self, job):
        """Callback from the JobOutputMixin when the job terminates."""
        assert self.dprint()
        del self.process
        if self.log:
            text = "\n" + job.getFinishMessage()
            self.log.showMessage(text)
