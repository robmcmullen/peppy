# peppy Copyright (c) 2006-2008 Rob McMullen
# Licenced under the GPLv2; see http://peppy.flipturn.org for more info
"""

"""

import os


class ProgressUpdater(object):
    """Base class for reporting progress updates for a set of tasks.
    
    """
    def __init__(self):
        self.__num_tasks = 1
        self.__current_task = 0
        self.__work_item_max = 100
    
    def setNumberOfWorkItems(self, num):
        """Set the number of work items to perform for this task.
        
        This is typically set before starting any of the percent complete
        calculations.
        """
        self.__num_tasks = num
    
    def finishedWorkItem(self):
        """Increment the item number.
        
        This should be called after the completion of one of the items in
        the set of work items.
        """
        self.__current_task += 1
        self.__work_item_max = 100
    
    def calcPercentComplete(self, cur, max):
        """Compute the total percentage complete across all work items
        
        The total percentage complete is divided equally across work items,
        regardless of the amount of time each work item takes.  E.g.  if
        there are 5 work items, each work item accounts for 20% of the total
        percentage complete even if the first item takes 5 seconds and the
        second takes 2 minutes.
        """
        if max < 0:
            max = self.__work_item_max
        else:
            self.__work_item_max = max
        start = 100.0 * self.__current_task / self.__num_tasks
        end = 100.0 * (self.__current_task + 1) / self.__num_tasks
        width = end - start
        perc = start + (width * cur / max)
        return perc
    
    def updateStatus(self, cur=-1, max=-1, text=None):
        """Callback for work item processing to report progress
        
        The current and maximum count are in arbitrary units.  The maximum
        may be changed at any time, however this will adjust the percentage
        complete and if used in a GUI may result in the progress bar shrinking
        rather than monotonically increasing as expected.
        
        The first time this method is called for a work item, max should be
        specified.  After that, max will default to the last value used for
        the work item.
        """
        perc = self.calcPercentComplete(cur, max)
        print("task #%d: %d of %d.  Overall percent complete = %f  %s" % (self.__current_task, cur, max, perc, text))
    
    def reportSuccess(self, text, data=None):
        """Callback for successful completion
        
        @param text: text to be displayed to the user
        
        @param data: data (if any) resulting from the work items.  Typically
        subclasses would use this result to display the results of the
        calculations.
        """
        print("Success!  %s" % text)
    
    def reportFailure(self, text):
        """Callback for unsuccessful completion
        
        @param text: error text to be displayed to the user
        """
        print("Failure.  %s" % text)


class ThreadStatus(ProgressUpdater):
    """Subclass of ProgressUpdater using wx.CallAfter to report thread status
    back to the GUI thread
    
    """
    def updateStatus(self, cur=-1, max=-1, text=None):
        import wx
        perc = self.calcPercentComplete(cur, max)
        wx.CallAfter(self.updateStatusGUI, perc, text)
    
    def updateStatusGUI(self, perc, text):
        """Callback to be overridden in the subclass that will run in the
        GUI thread.
        
        @param perc: (floating point) percent complete
        
        @param text: text to be displayed to user (or None)
        """
        print("Overall percent complete = %f  %s" % (perc, text))
    
    def reportSuccess(self, text, data=None):
        import wx
        wx.CallAfter(self.reportSuccessGUI, text, data)
    
    def reportSuccessGUI(self, text, data):
        """Success callback (to be overridden in the subclass) that will run in
        the GUI thread.
        
        @param text: text to be displayed to user (or None)
        
        @param data: data (if any) resulting from the work items.  Typically
        subclasses would use this result to display the results of the
        calculations.
        """
        print("Thread reports success!  %s" % text)
    
    def reportFailure(self, text):
        import wx
        wx.CallAfter(self.reportFailureGUI, text)
    
    def reportFailureGUI(self, text):
        """Failure callback (to be overridden in the subclass) that will run in
        the GUI thread.
        
        @param text: error text to be displayed to the user
        """
        print("Thread reports success!  %s" % text)
