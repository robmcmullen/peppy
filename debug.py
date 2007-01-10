import os,sys,inspect

logfh=sys.stderr

__all__ = ['debuglog','dprint','debugmixin']


def debuglog(file):
    global logfh
    logfh=open(file,"w")

def dprint(str=''):
    caller=inspect.stack()[1]
    namespace=caller[0].f_locals
    if 'self' in namespace:
        cls=namespace['self'].__class__.__name__+'.'
    else:
        cls=''
    logfh.write("%s:%d %s%s: %s%s" % (os.path.basename(caller[1]),caller[2],cls,caller[3],str,os.linesep))

class debugmixin(object):
    debuglevel=0
        
    def dprint(self,str='',level=1):
        if not hasattr(self,'debuglevel') or self.debuglevel>=level:
            caller=inspect.stack()[1]
            logfh.write("%s:%d %s.%s: %s%s" % (os.path.basename(caller[1]),caller[2],caller[0].f_locals['self'].__class__.__name__,caller[3],str,os.linesep))


if __name__=="__main__":
    dprint('testing')
    
    class test(debugmixin):
        debuglevel=1

        def method(self):
            self.dprint('need classname')

    t=test()
    t.method()
