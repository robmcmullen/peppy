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
"""

import os, sys, struct, Queue, threading, time, socket
from cStringIO import StringIO

import wx
import wx.stc
from wx.lib.pubsub import Publisher
from wx.lib.evtmgr import eventManager

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


_GlobalProcessManager = None

def ProcessManager():
    global _GlobalProcessManager

    if _GlobalProcessManager is None:
        _GlobalProcessManager = _ProcessManager()
        wx.GetApp().Bind(wx.EVT_END_PROCESS, ProcessManager().OnProcessEnded)

    return _GlobalProcessManager


class JobOutputMixin(object):
    def startupFailureCallback(self, p):
        dprint("Couldn't run %s" % p.cmd)

    def startupCallback(self, p):
        dprint("Started process %d" % p.pid)

    def stdoutCallback(self, p, text):
        dprint("stdout: '%s'" % text)
    
    def stderrCallback(self, p, text):
        dprint("stderr: '%s'" % text)
    
    def finishedCallback(self, p):
        dprint("Finished with pid=%d" % p.pid)


class Job(debugmixin):
    debuglevel = 0
    
    def __init__(self, cmd, job_output):
        self.pid = None
        self.process = None
        self.cmd = cmd
        self.jobout = job_output
        self.handler = wx.GetApp()
        self.stdout = None
        self.stderr = None

    def run(self, text=""):
        assert self.dprint()
        self.process = wx.Process(self.handler)
        self.process.Redirect();
        self.pid = wx.Execute(self.cmd, wx.EXEC_ASYNC, self.process)
        if self.pid==0:
            assert self.dprint("startup failed")
            self.process = None
            wx.CallAfter(self.jobout.startupFailureCallback, self)
        else:
            wx.CallAfter(self.jobout.startupCallback, self)
            
            size = len(text)
            fh = self.process.GetOutputStream()
            assert self.dprint("sending text size=%d to %s" % (size,fh))
            if size > 1000:
                for i in range(0,size,1000):
                    last = i+1000
                    if last>size:
                        last=size
                    assert self.dprint("sending text[%d:%d] to %s" % (i,last,fh))
                    fh.write(text[i:last])
                    assert self.dprint("last write = %s" % str(fh.LastWrite()))
            elif len(text) > 0:
                fh.write(text)
            self.process.CloseOutput()
            self.stdout = self.process.GetInputStream()
            self.stderr = self.process.GetErrorStream()

    def kill(self):
        assert self.dprint()
        if self.process is not None:
            if wx.Process.Kill(self.pid, wx.SIGTERM) != wx.KILL_OK:
                wx.Process.Kill(self.pid, wx.SIGKILL)
            self.process = None

    def readStream(self, stream, callback):
        assert self.dprint()
        if stream and stream.CanRead():
            text = stream.read()
            wx.CallAfter(callback, self, text)

    def readStreams(self):
        assert self.dprint()
        if self.process is not None:
            self.readStream(self.stdout, self.jobout.stdoutCallback)
            self.readStream(self.stderr, self.jobout.stderrCallback)

    def OnCleanup(self, evt):
        """Cleanup handler on process exit.

        This must be called as part of the event loop, otherwise the
        process doesn't exist and it causes crashes in wx when trying
        to read the last bit of data from the streams.
        """
        assert self.dprint()
        self.readStreams()
        if self.process and self.process.Exists(self.pid):
            self.process.Destroy()
            self.process = None
        wx.CallAfter(self.jobout.finishedCallback, self)

class _ProcessManager(debugmixin):
    """Display a list of all subprocesses.
    """
    debuglevel = 0
    autoclean = True
    
    jobs = []
    job_lookup = {}

    def idle(self):
        for job in self.jobs:
            if job.process:
                job.readStreams()
    
    def run(self, cmd, job_output, input=""):
        job = Job(cmd, job_output)
        self.jobs.append(job)
        assert self.dprint("Running job %s" % cmd)
        job.run(input)
        if job.pid > 0:
            self.job_lookup[job.pid] = job
            Publisher().sendMessage('peppy.processmanager.started', job)
        return job

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
        self.finished(job)

    def removeJob(self, job):
        if job.pid in self.job_lookup:
            assert self.dprint("removing pid=%d" % job.pid)
            del self.job_lookup[job.pid]
            jobs = [j for j in self.jobs if j != job]
            self.jobs = jobs

    def finished(self, job):
        assert self.dprint("sending peppy.processmanager.finished")
        Publisher().sendMessage('peppy.processmanager.finished', job)
        

class ProcessList(wx.ListCtrl, debugmixin):
    """Display all processes
    """

    def __init__(self, parent, **kwargs):
        wx.ListCtrl.__init__(self, parent, style=wx.LC_REPORT, **kwargs)
        self.createColumns()

        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.OnItemActivated)
        Publisher().subscribe(self.msgStarted, 'peppy.processmanager.started')
        Publisher().subscribe(self.msgFinished, 'peppy.processmanager.finished')
        self.reset()

    def OnIdle(self, evt):
        ProcessManager().idle()
        evt.Skip()

    def msgStarted(self, msg):
        job = msg.data
        self.reset()

    def msgFinished(self, msg):
        job = msg.data
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
            self.SetStringItem(index, 1, str(job.process is not None))
            self.SetStringItem(index, 2, job.cmd)

            index += 1

        if index < list_count:
            for i in range(index, list_count):
                # don't have to increment the index to DeleteItem
                # because the list gets shorter by one each time.
                self.DeleteItem(index)

        if index > 0:
            self.resizeColumns()

    def resizeColumns(self):
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
            
            mainsizer = wx.BoxSizer(wx.VERTICAL)
            listsizer = wx.BoxSizer(wx.HORIZONTAL)
            sizer = wx.BoxSizer(wx.VERTICAL)
            
            b = wx.Button(self, -1, "Start")
            sizer.Add(b, 0, wx.EXPAND|wx.ALL, 2)
            b.Bind(wx.EVT_BUTTON, self.OnStart)
            
            b = wx.Button(self, -1, "Kill")
            sizer.Add(b, 0, wx.EXPAND|wx.ALL, 2)
            b.Bind(wx.EVT_BUTTON, self.OnKill)
            
            b = wx.Button(self, -1, "Cleanup")
            sizer.Add(b, 0, wx.EXPAND|wx.ALL, 2)
            b.Bind(wx.EVT_BUTTON, self.OnCleanup)
            
            b = wx.Button(self, -1, "Quit")
            sizer.Add(b, 0, wx.EXPAND|wx.ALL, 2)
            b.Bind(wx.EVT_BUTTON, self.OnQuit)
            
            self.list = ProcessList(self)
            listsizer.Add(sizer, 0, wx.EXPAND|wx.ALL, 0)
            listsizer.Add(self.list, 1, wx.EXPAND|wx.ALL, 0)
            
            self.cmd = wx.TextCtrl(self, -1, '')
            mainsizer.Add(self.cmd, 0, wx.EXPAND, 0)
            
            mainsizer.Add(listsizer, 1, wx.EXPAND|wx.ALL, 0)

            self.out = wx.TextCtrl(self, -1, '',
                                   style=wx.TE_MULTILINE|wx.TE_READONLY|wx.TE_RICH2)

            self.cmd.SetValue("python -u")
            
            mainsizer.Add(self.out, 1, wx.EXPAND|wx.ALL, 10)

            self.SetSizer(mainsizer)
            self.SetAutoLayout(True)
        
        def stdoutCallback(self, job, text):
            dprint()
            self.out.AppendText("job=%s text=%s" % (job.pid, text))
    
        def OnStart(self, evt):
            p = ProcessManager().run(self.cmd.GetValue(), self, """\
import time

for x in range(2):
    print 'blah'
    time.sleep(1)
""")
            dprint("OnStart: pid=%d" % p.pid)
            
        def OnKill(self, evt):
            print "kill highlighted process"
            self.list.kill()

        def OnCleanup(self, evt):
            print "cleanup list & remove completed jobs"
            self.list.cleanup()

        def OnQuit(self, evt):
            sys.exit(1)
            

    def test():
        app = wx.PySimpleApp()
        f = jobframe()
        f.Show()

        def spin(p):
            while not p.finished:
                wx.Yield()
                time.sleep(0.01)

        app.MainLoop()

    test()
