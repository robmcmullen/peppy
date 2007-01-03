import os,sys,inspect

logfh=sys.stderr

__all__ = ['debuglog','dprint','debugmixin']


def debuglog(file):
    global logfh
    logfh=open(file,"w")

def dprint(str):
    import inspect
    caller=inspect.stack()[1]
    logfh.write("%s:%d:%s: %s%s" % (os.path.basename(caller[1]),caller[2],caller[3],str,os.linesep))

class debugmixin(object):
    debuglevel=0
        
    def dprint(self,str,level=1):
        import inspect
        if not hasattr(self,'debuglevel') or self.debuglevel>=level:
            caller=inspect.stack()[1]
            logfh.write("%s:%d %s: %s%s" % (os.path.basename(caller[1]),caller[2],caller[3],str,os.linesep))
