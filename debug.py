import os,inspect

def dprint(str):
    import inspect
    caller=inspect.stack()[1]
    print "%s:%d:%s: %s" % (os.path.basename(caller[1]),caller[2],caller[3],str)


class debugmixin(object):
    debuglevel=0
        
    def dprint(self,str,level=1):
        import inspect
        if not hasattr(self,'debuglevel') or self.debuglevel>=level:
            caller=inspect.stack()[1]
            print "%s:%d %s: %s" % (os.path.basename(caller[1]),caller[2],caller[3],str)
