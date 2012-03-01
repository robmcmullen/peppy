#-----------------------------------------------------------------------------
# Name:        processmanager.py
# Purpose:     global list of processes and a list control to manage them
#
# Author:      Rob McMullen
#
# Created:     2007
# RCS-ID:      $Id: $
# Copyright:   (c) 2007 Rob McMullen
# License:     wxWidgets
#-----------------------------------------------------------------------------
"""Process management support

This module provides process management support in the form of a
global process manager.  This provides the ability to display and
control all processes from one place.

A similar class is Boa Constructor's wxPopen at http://boa-constructor.cvs.sourceforge.net/boa-constructor/boa/wxPopen.py?revision=1.6&view=markup

Converted to threads using wxWidgets licensed code from Editra:
http://svn.wxwidgets.org/viewvc/wx/wxPython/3rdParty/Editra/src/eclib/outbuff.py?view=markup
"""

import os, sys, types, errno, time, threading, signal, subprocess, weakref
from Queue import Queue, Empty
# Platform specific modules needed for killing processes
if subprocess.mswindows:
    import msvcrt
    import ctypes
else:
    import shlex

import wx
import wx.stc

try:
    from peppy.debug import *
except:
    def dprint(txt=""):
        print txt

    class debugmixin(object):
        debuglevel = 0
        def dprint(self, txt=""):
            if self.debuglevel > 0 and txt:
                dprint(txt)
            return True

if __name__ == "__main__":
    import __builtin__
    __builtin__._ = str


_GlobalProcessManager = None

def ProcessManager():
    global _GlobalProcessManager

    if _GlobalProcessManager is None:
        _GlobalProcessManager = _ProcessManager()

    return _GlobalProcessManager


class JobOutputMixin(object):
    def startupFailureCallback(self, job, text):
        dprint("Couldn't run '%s':\n error: %s" % (job.cmd, text))

    def startupCallback(self, job):
        dprint("Started process %d" % job.pid)

    def stdoutCallback(self, job, text):
        dprint("stdout: '%s'" % text)
    
    def stderrCallback(self, job, text):
        dprint("stderr: '%s'" % text)
    
    def finishedCallback(self, job):
        dprint("Finished with pid=%d" % job.pid)


class JobOutputSaver(object):
    def __init__(self, finishCallback):
        self.start = None
        self.finish = None
        self.exit_code = None
        self.stdout = []
        self.stderr = []
        self.callback = finishCallback
    
    def __str__(self):
        lines = []
        if self.start:
            lines.append("Started %s" % (time.asctime(time.localtime(self.start))))
        if self.stdout:
            lines.append("stdout:")
            lines.append(self.getOutputText())
        if self.stderr:
            lines.append("stderr:")
            lines.append(self.getErrorText())
        if self.finish:
            lines.append("Finished %s" % (time.asctime(time.localtime(self.finish))))
        lines.append("Exit code = %s" % self.exit_code)
        return os.linesep.join(lines)
    
    def getOutputText(self):
        return "".join(self.stdout)
    
    def getErrorText(self):
        return "".join(self.stderr)
    
    def startupFailureCallback(self, p, text):
        self.callback(self)

    def startupCallback(self, p):
        self.starttime = time.time()

    def stdoutCallback(self, p, text):
        self.stdout.append(text)
        
    def stderrCallback(self, p, text):
        self.stderr.append(text)
        
    def finishedCallback(self, p):
        self.finish = time.time()
        self.exit_code = p.exit_code
        self.callback(self)


def mslex(cmdline):
       """Build an argv list from a Microsoft shell style cmdline str
        following the MS C runtime rules.
       
       Licensed under the Python license from: 
       https://fisheye3.atlassian.com/browse/jython/trunk/jython/Lib/subprocess.py?hb=true
        """
       whitespace = ' \t'
       # count of preceding '\'
       bs_count = 0
       in_quotes = False
       arg = []
       argv = []

       for ch in cmdline:
           if ch in whitespace and not in_quotes:
               if arg:
                   # finalize arg and reset
                   argv.append(''.join(arg))
                   arg = []
               bs_count = 0
           elif ch == '\\':
               arg.append(ch)
               bs_count += 1
           elif ch == '"':
               if not bs_count % 2:
                   # Even number of '\' followed by a '"'. Place one
                   # '\' for every pair and treat '"' as a delimiter
                   if bs_count:
                       del arg[-(bs_count / 2):]
                   in_quotes = not in_quotes
               else:
                   # Odd number of '\' followed by a '"'. Place one '\'
                   # for every pair and treat '"' as an escape sequence
                   # by the remaining '\'
                   del arg[-(bs_count / 2 + 1):]
                   arg.append(ch)
               bs_count = 0
           else:
               # regular char
               arg.append(ch)
               bs_count = 0
 
       # A single trailing '"' delimiter yields an empty arg
       if arg or in_quotes:
           argv.append(''.join(arg))
 
       return argv
   
   
class ReadThread(threading.Thread):
    def __init__(self, name, fh, job, callback):
        threading.Thread.__init__(self)
        
        self._name = name
        self._fh = fh
        self._job = job
        self._callback = callback
        self._queue = Queue()
    
    def _do_callback(self, result):
        # Ignore encoding errors and return an empty line instead
        try:
            result = result.decode(sys.getfilesystemencoding())
        except UnicodeDecodeError:
            result = os.linesep

        #print("sending %s to %s" % (result, callback))
        wx.CallAfter(self._callback, self._job, result)
    
    #---- Public Member Functions ----#
    def run(self):
        for line in iter(self._fh.readline, ''):
            self._queue.put(line)
        self._fh.close()
    
    def read_queue(self):
        """Called from parent thread to get any data queued up.
        
        """
        try:
            while True:
                line = self._queue.get_nowait()
                #dprint("%s-->%s<--" % (self._name, line.rstrip()))
                self._do_callback(line)
        except Empty:
            #dprint("%s empty" % self._name)
            pass


class JobThread(threading.Thread):
    def __init__(self, job, cmd, stdin=None, cwd=None, env=None):
        """Initialize the ProcessThread object
        Example:
          >>> myproc = ProcessThread(myframe, '/usr/local/bin/python',
                                     'hello.py', '--version', '/Users/me/home/')
          >>> myproc.start()

        @param jobout: JobOutputMixin used to process data
        @param cmd: Command string to execute as a subprocess.
        @keyword cwd: Directory to execute process from or None to use current
        @keyword env: Environment to run the process in (dictionary) or None to
                      use default.
        """
        threading.Thread.__init__(self)

        self._job = job
        self._cmd = cmd
        self._stdin = stdin
        self._abort = False          # Abort Process
        self._proc = None           # Process handle
        self._cwd = cwd             # Path at which to run from
        self._sig_abort = signal.SIGTERM    # default signal to kill process

        # Make sure the environment is sane it must be all strings
        if env is not None:
            nenv = dict(env) # make a copy to manipulate
            for k, v in env.iteritems():
                if isinstance(v, types.UnicodeType):
                    nenv[k] = v.encode(sys.getfilesystemencoding())
                elif not isinstance(v, basestring):
                    nenv.pop(k)
            self._env = nenv
        else:
            self._env = None

        # Setup
        self.setDaemon(True)

    def _kill_process(self):
        """Kill the subprocess
        """
        pid = self._proc.pid
        # Dont kill if the process if it is the same one we
        # are running under (i.e we are running a shell command)
        if pid == os.getpid():
            return

        if wx.Platform != '__WXMSW__':
            # Try to kill the group
            try:
                os.kill(pid, self._sig_abort)
            except OSError, msg:
                pass

            # If still alive shoot it again
            if self._proc.poll() is not None:
                try:
                    os.kill(-pid, signal.SIGKILL)
                except OSError, msg:
                    pass

            # Try and wait for it to cleanup
            try:
                os.waitpid(pid, os.WNOHANG)
            except OSError, msg:
                pass

        else:
            # 1 == PROCESS_TERMINATE
            handle = ctypes.windll.kernel32.OpenProcess(1, False, pid)
            ctypes.windll.kernel32.TerminateProcess(handle, -1)
            ctypes.windll.kernel32.CloseHandle(handle)

    #---- Public Member Functions ----#
    def abort(self, sig=signal.SIGTERM):
        """Abort the running process and return control to the main thread"""
        self._sig_abort = sig
        self._abort = True

    def run(self):
        """Run the process until finished or aborted. Don't call this
        directly instead call self.start() to start the thread else this will
        run in the context of the current thread.
        @note: overridden from Thread

        """
        # Popen needs a sequence instead of a command line argument string, so
        # it must be parsed.  shlex is used on unix, mslex (function above)
        # used on windows.  Other platform specific code is processed here
        # as well.
        command = self._cmd.strip()
        if subprocess.mswindows:
            command = mslex(command.encode(sys.getfilesystemencoding()))
            
            # these flags are needed to tell MSW not to open up another window
            # for the process.
            suinfo = subprocess.STARTUPINFO()
            suinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        else:
            # shlex does not support unicode
            command = shlex.split(command.encode(sys.getfilesystemencoding()))
            suinfo = None
        
        err = None
        try:
            # Note: for py2exe to work correctly, stdin, stdout, and stderr
            # must all use subprocess.PIPE even if they are not intended to be
            # used.  For example, stdin is closed immediately after starting
            # the subprocess if no data is to be sent.
            self._proc = subprocess.Popen(command,
                                          stdin=subprocess.PIPE,
                                          stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE,
                                          shell=False,
                                          cwd=self._cwd,
                                          env=self._env,
                                          startupinfo=suinfo)
            self._job.pid = self._proc.pid
            if self._stdin is not None:
                #print(self._stdin)
                self._proc.stdin.write(self._stdin)
            self._proc.stdin.close()
        except OSError, msg:
            # NOTE: throws WindowsError on Windows which is a subclass of
            #       OSError, so it will still get caught here.
            err = msg
            self._job.pid = -1
            wx.CallAfter(self._job.jobout.startupFailureCallback, self._job, err)
            
        if err is None:
            wx.CallAfter(ProcessManager().jobStartedCallback, self._job)
            wx.CallAfter(self._job.jobout.startupCallback, self._job)

            # Read from stdout while there is output from process
            out_q = ReadThread("stdout", self._proc.stdout, self._job, self._job.jobout.stdoutCallback)
            out_q.start()
            err_q = ReadThread("stderr", self._proc.stderr, self._job, self._job.jobout.stderrCallback)
            err_q.start()
            try:
                while self._proc.poll() is None:
                    out_q.read_queue()
                    err_q.read_queue()
                    if self._abort:
                        self._kill_process()
                    time.sleep(.2)
                    #dprint("Poll: %s" % str(self._proc.poll()))
            except wx.PyDeadObjectError:
                # Our parent window is dead so kill process and return
                self._kill_process()
                return
            #dprint("Waiting for process to finish...")
            # Notify of error in running the process
            try:
                self._job.exit_code = self._proc.wait()
            except OSError:
                self._job.exit_code = -1
            #dprint("Reading any final output...")
            err_q.read_queue()
            #dprint("Waiting for stderr thread join...")
            err_q.join()
            #dprint("Waiting for stdout thread join...")
            out_q.read_queue()
            out_q.join()

            # Notify that process has exited
            # Pack the exit code as the events value
            wx.CallAfter(self._job.jobout.finishedCallback, self._job)
            wx.CallAfter(ProcessManager().jobFinishedCallback, self._job)


class Job(debugmixin):
    debuglevel = 0
    
    # Use the unicode rightward double arrow as a delimiter
    arrow = u"\u21d2 "
    started = _("Started %s on")
    cwd = _("cwd = ")
    exit = _("exit code = %s")
    finished = _("Finished %s on")
    
    def __init__(self, cmd, working_dir, job_output):
        # The process ID is set by thread when process is created, and the exit
        # code is set by the thread when the process finishes.
        self.pid = None
        self.exit_code = 0
        
        self.process = None
        self.cmd = cmd
        self.working_dir = working_dir
        self.jobout = job_output
    
    @classmethod
    def matchCwd(cls, line):
        """Evaluate if the line contains an embedded working directory specifier
        
        """
        if line.startswith(cls.arrow):
            start = len(cls.arrow)
            #dprint(line[start:])
            if line[start:].startswith(_(cls.cwd)):
                cwd = line[start + len(cls.cwd):].strip()
                return cwd
        return ""
    
    def getStartMessage(self):
        return "%s%s %s\n%s%s%s\n" % (self.arrow, self.started % self.cmd, time.asctime(time.localtime(time.time())), self.arrow, self.cwd, self.working_dir)

    def getFinishMessage(self):
        return "%s%s\n%s%s %s" % (self.arrow, self.exit % self.exit_code, self.arrow, self.finished % self.cmd, time.asctime(time.localtime(time.time())))

    def run(self, text=""):
        assert self.dprint("Running %s in %s" % (self.cmd, self.working_dir))
        # Note: gfortran will buffer output unless GFORTRAN_UNBUFFERED_ALL=y in
        # the environment.  However, using:
        #    self.process = JobThread(self, self.cmd, stdin=text, cwd=self.working_dir, env={"GFORTRAN_UNBUFFERED_ALL":"y"})
        # seems to fail using wx on python 2.6 with an XDisplay error because
        # the JobThread creates a blank environment with only that gfortran
        # env var in it.
        self.process = JobThread(self, self.cmd, stdin=text, cwd=self.working_dir)
        self.process.start()

    def kill(self):
        assert self.dprint()
        if self.process is not None:
            self.process.abort()

    def isRunning(self):
        return self.process and self.process.isAlive()

class _ProcessManager(debugmixin):
    """Display a list of all subprocesses.
    """
    debuglevel = 0
    autoclean = True
    timer = None
    
    jobs = []
    job_lookup = {}
    
    # Record of ProcessList instances that need to be updated
    lists = []
    
    def run(self, cmd, working_dir, job_output, stdin=None):
        job = Job(cmd, working_dir, job_output)
        job.run(stdin)
        return job
    
    def registerList(self, listctrl):
        ref = weakref.ref(listctrl)
        self.lists.append(ref)
    
    def updateLists(self, msg_callable, job):
        current = self.lists[:]
        alive = []
        for listctrl_ref in current:
            listctrl = listctrl_ref()
            if listctrl is not None:
                try:
                    msg_callable(listctrl, job)
                    alive.append(listctrl_ref)
                except wx.PyDeadObjectError:
                    self.dprint("Caught dead object.  Removing")
            else:
                if self.debuglevel > 0:
                    self.dprint("Caught deleted object.  Removing")
        self.lists = alive
    
    def jobStartedCallback(self, job):
        self.jobs.append(job)
        assert self.dprint("started job %s" % job)
        if job.isRunning():
            self.job_lookup[job.pid] = job
            self.updateLists(self.updateListStarted, job)
            self.sendStartedMessage(job)
    
    def updateListStarted(self, listctrl, job):
        listctrl.msgStarted(job)
    
    def sendStartedMessage(self, job):
        from wx.lib.pubsub import Publisher
        Publisher().sendMessage('processmanager.started', job)

    def jobFinishedCallback(self, job):
        assert self.dprint("process ended! pid=%d" % job.pid)
        if job:
            self.cleanup(job)

    def kill(self, pid):
        job = self.lookup(pid)
        if job:
            job.kill()

    def lookup(self, pid):
        if pid in self.job_lookup:
            return self.job_lookup[pid]
        return None

    def getJobs(self):
        # return a copy!
        return [j for j in self.jobs]

    def OnProcessEnded(self, evt):
        pid = evt.GetPid()
        assert self.dprint("process ended! pid=%d" % pid)
        job = self.lookup(pid)
        if job:
            job.OnCleanup(evt)
            wx.CallAfter(self.cleanup, job)
        # evt.Skip() # Don't call Skip here, or it causes a crash!

    def cleanup(self, job):
        assert self.dprint("in cleanup")
        if self.autoclean:
            self.removeJob(job)
        self.updateLists(self.updateListFinished, job)
        self.sendFinishedMessage(job)

    def removeJob(self, job):
        if job.pid in self.job_lookup:
            assert self.dprint("removing pid=%d" % job.pid)
            del self.job_lookup[job.pid]
            jobs = [j for j in self.jobs if j != job]
            self.jobs = jobs
    
    def updateListFinished(self, listctrl, job):
        listctrl.msgFinished(job)

    def sendFinishedMessage(self, job):
        from wx.lib.pubsub import Publisher
        Publisher().sendMessage('processmanager.finished', job)
        

class ProcessList(wx.ListCtrl, debugmixin):
    """Display all processes
    """

    def __init__(self, parent, **kwargs):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT, **kwargs)
        self.createColumns()

        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        ProcessManager().registerList(self)
        self.reset()

    def msgStarted(self, job):
        self.reset()

    def msgFinished(self, job):
        self.reset()

    def createColumns(self):
        self.InsertColumn(0, "PID")
        self.InsertColumn(1, "Running")
        self.InsertColumn(2, "Cmd")

    def reset(self):
        pm = ProcessManager()
        list_count = self.GetItemCount()
        jobs = pm.getJobs()
        index = 0
        for job in jobs:
            if index >= list_count:
                self.InsertStringItem(sys.maxint, str(job.pid))
            else:
                self.SetStringItem(index, 0, str(job.pid))
            self.SetStringItem(index, 1, str(job.isRunning()))
            self.SetStringItem(index, 2, job.cmd)

            index += 1

        if index < list_count:
            for i in range(index, list_count):
                # don't have to increment the index to DeleteItem
                # because the list gets shorter by one each time.
                self.DeleteItem(index)

        if index > 0:
            self.ResizeColumns()

    def ResizeColumns(self):
        for col in range(self.GetColumnCount()):
            self.SetColumnWidth(col, wx.LIST_AUTOSIZE)

    def OnItemActivated(self, evt):
        index = evt.GetIndex()
        pid = int(self.GetItem(index, 0).GetText())
        p = ProcessManager().lookup(pid)
        assert self.dprint(p)
        evt.Skip()

    def kill(self):
        pm = ProcessManager()
        index = self.GetFirstSelected()
        while index != -1:
            assert self.dprint("killing job %d" % (index, ))
            pid = int(self.GetItem(index, 0).GetText())
            pm.kill(pid)
            index = self.GetNextSelected(index)


if __name__ == '__main__':
    class jobframe(wx.Frame, JobOutputMixin):
        def __init__(self):
            wx.Frame.__init__(self, None, -1, 'Process Manager Test',
                              size=(640,480))
            usercommand = True
            
            mainsizer = wx.BoxSizer(wx.VERTICAL)
            listsizer = wx.BoxSizer(wx.HORIZONTAL)
            sizer = wx.BoxSizer(wx.VERTICAL)
            
            if usercommand:
                b = wx.Button(self, -1, "Start User Command")
                sizer.Add(b, 0, wx.EXPAND|wx.ALL, 2)
                b.Bind(wx.EVT_BUTTON, self.OnStartCmd)
                
                h = wx.BoxSizer(wx.HORIZONTAL)
                cmdlabel = wx.StaticText(self, -1, 'User Command')
                h.Add(cmdlabel, 0, wx.EXPAND, 0)
                self.cmd = wx.TextCtrl(self, -1, '')
                h.Add(self.cmd, 1, wx.EXPAND, 0)
                mainsizer.Add(h, 0, wx.EXPAND, 0)
                self.cmd.SetValue("python -u")
                
                h = wx.BoxSizer(wx.HORIZONTAL)
                cwdlabel = wx.StaticText(self, -1, 'in Working Directory')
                h.Add(cwdlabel, 0, wx.EXPAND, 0)
                self.cwd = wx.TextCtrl(self, -1, '')
                h.Add(self.cwd, 1, wx.EXPAND, 0)
                mainsizer.Add(h, 0, wx.EXPAND, 0)
                self.cwd.SetValue(os.getcwd())
            
            b = wx.Button(self, -1, "Start Sample Python Loop")
            sizer.Add(b, 0, wx.EXPAND|wx.ALL, 2)
            b.Bind(wx.EVT_BUTTON, self.OnStart)
            
            b = wx.Button(self, -1, "Start Sample Python Loop on Windows")
            sizer.Add(b, 0, wx.EXPAND|wx.ALL, 2)
            b.Bind(wx.EVT_BUTTON, self.OnStartWin)
            
            b = wx.Button(self, -1, "Kill")
            sizer.Add(b, 0, wx.EXPAND|wx.ALL, 2)
            b.Bind(wx.EVT_BUTTON, self.OnKill)
            
            #b = wx.Button(self, -1, "Cleanup")
            #sizer.Add(b, 0, wx.EXPAND|wx.ALL, 2)
            #b.Bind(wx.EVT_BUTTON, self.OnCleanup)
            
            b = wx.Button(self, -1, "Quit")
            sizer.Add(b, 0, wx.EXPAND|wx.ALL, 2)
            b.Bind(wx.EVT_BUTTON, self.OnQuit)
            
            self.list = ProcessList(self)
            listsizer.Add(sizer, 0, wx.EXPAND|wx.ALL, 0)
            listsizer.Add(self.list, 1, wx.EXPAND|wx.ALL, 0)
            
            mainsizer.Add(listsizer, 1, wx.EXPAND|wx.ALL, 0)

            self.out = wx.TextCtrl(self, -1, '',
                                   style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_RICH2)
            
            mainsizer.Add(self.out, 1, wx.EXPAND|wx.ALL, 10)

            self.SetSizer(mainsizer)
            self.SetAutoLayout(True)
        
        def stdoutCallback(self, job, text):
            dprint()
            self.out.AppendText("job=%s text=%s" % (job.pid, text))
    
        def stderrCallback(self, job, text):
            dprint()
            self.out.AppendText("stderr! job=%s text=%s" % (job.pid, text))
    
        def startupFailureCallback(self, job, text):
            dprint()
            self.out.AppendText("Couldn't run '%s':\n error: %s" % (job.cmd, text))
    
        def OnStartCmd(self, evt):
            cmd = self.cmd.GetValue()
            dprint("User command: %s" % cmd)
            p = ProcessManager().run(cmd, self.cwd.GetValue(), self)
            dprint("OnStart: %s" % p)
        
        sample_loop = """\
import os, sys, time

for x in range(100):
    print 'loop #%d' % x
    if x%9 == 0:
        sys.stderr.write("error on loop #%d%s" % (x, os.linesep))
    time.sleep(0.2)
"""
        
        def OnStart(self, evt):
            p = ProcessManager().run("python -u", os.getcwd(), self, self.sample_loop)
            dprint("OnStart: %s" % p)
            
        def OnStartWin(self, evt):
            p = ProcessManager().run("C:/Python25/python.exe -u", os.getcwd(), self, self.sample_loop)
            dprint("OnStartWin: %s" % p)
            
        def OnKill(self, evt):
            print "kill highlighted process"
            self.list.kill()

        def OnCleanup(self, evt):
            print "cleanup list & remove completed jobs"
            ProcessManager().cleanup()

        def OnQuit(self, evt):
            sys.exit(1)
            

    def test():
        app = wx.PySimpleApp()
        f = jobframe()
        f.Show()
        app.MainLoop()

    test()
