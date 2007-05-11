# peppy Copyright (c) 2006-2007 Rob McMullen
# Licenced under the GPL; see http://www.flipturn.org/peppy for more info
"""StructRecord -- a binary record packer/unpacker

This module unpacks binary records into objects, and packs objects
into binary records.  Similar in spirit to Construct (on the web at
construct.wikispaces.com), but assembles parsed data into objects
instead of construct's unnamed data structures.

Allows conditionals, recursive definition of structures, and custom
pack/unpack classes.  A class to store unparsed binary data needs a
class attribute named 'typedef' that is a tuple that defines the
structure of the binary record.  The tuple contains a description of
the entities in the binary record, in order that they occur in the
file.

Simple example for parsing 3 32-bit integers of varying endianness:

    class TestParse:
        typedef=(
            FormatField('testi1','<i'),
            SLInt32('testi2'),
            SBInt32('testi3'),
            )

More complicated examples include conditionals, cases, lists, and nested
structures.  For more examples, see the unit tests.
"""


import os,sys,re
import struct
from cStringIO import StringIO
import copy
import pprint

try:
    from peppy.debug import *
except:
    import inspect
    
    def dprint(str=''):
        caller=inspect.stack()[1]
        namespace=caller[0].f_locals
        if 'self' in namespace:
            cls=namespace['self'].__class__.__name__+'.'
        else:
            cls=''
        logfh.write("%s:%d %s%s: %s%s" % (os.path.basename(caller[1]),caller[2],cls, caller[3],str,os.linesep))
        return True

    class debugmixin(object):
        debuglevel=0

        def dprint(self,str='',level=1):
            if not hasattr(self,'debuglevel') or self.debuglevel>=level:
                caller=inspect.stack()[1]
                logfh.write("%s:%d %s.%s: %s%s" % (os.path.basename(caller[1]),caller[2],caller[0].f_locals['self'].__class__.__name__,caller[3],str,os.linesep))
            return True
    

debug=True

# base indent level when printing stuff
base_indent="    "

def repr1(name,value,indent):
    if isinstance(value,Field):
        txt=value._getString(indent)
    elif isinstance(value,list):
        stuff=[]
        for item in value:
            if isinstance(item,Field):
                stuff.append(item._getString(indent+base_indent))
            else:
                stuff.append("%s%s" % (indent+base_indent,repr(item)))
        if len(stuff)>10:
            stuff[2:-2]=["\n%s..." % (indent+base_indent)]
        txt="%s%s = [\n%s\n%s]" % (indent,name,",\n".join(stuff),indent)
    else:
        txt="%s%s = %s" % (indent,name,repr(value))
    return txt
    

class FieldError(Exception):
    pass

class FieldTypedefError(Exception):
    pass

class FieldLengthError(FieldError):
    pass

class FieldNameError(FieldError):
    pass

class FieldAbortError(FieldError):
    pass

class Field(debugmixin):
    debuglevel=0
    
    def __init__(self,name,default=None):
        if name is not None and name.startswith("_"):
            raise FieldNameError("attribute names may not start with '_'")
        self._name=name
        self._default=default

    def getCopy(self,obj):
        return copy.copy(self)

    def storeDefault(self,obj):
        # make a copy of the default value, in case the default
        # specified is not a primitive object.
        setattr(obj,self._name,copy.copy(self._default))
        
    def getNumBytes(self,obj):
        return 0

    def read(self,fh,obj):
        expected=self.getNumBytes(obj)
        data=fh.read(expected)
        if len(data)<expected:
            raise EOFError("End of unserializable data in %s" % self._name)
        return data

    def unpack(self,fh,obj):
        raise NotImplementedError()

    def pack(self,fh,obj):
        raise NotImplementedError()

    def _getString(self,indent=""):
        names=self.__dict__.keys()
        names.sort()
        lines=["%s%s %s:" % (indent,repr(self),self._name)]
        for name in names:
            # ignore all keys that start with an underscore
            if not name.startswith("_"):
                value=self.__dict__[name]
                lines.append(repr1(name,value,indent+base_indent))
        if "_" in self.__dict__.keys():
            lines.append("%s_ = %s" % (indent+base_indent,repr(self.__dict__["_"])))
        return "\n".join(lines)
                                 

    def __str__(self):
        #pp=pprint.PrettyPrinter(indent=4)
        #return pp.pformat(self)
        return self._getString()


class NoOp(Field):
    debuglevel=0
    
    def unpack(self,fh,obj):
        setattr(obj,self._name,None)
        
    def pack(self,fh,obj):
        pass
        
class Abort(Field):
    debuglevel=0
    
    def unpack(self,fh,obj):
        raise FieldAbortError(self._name)
        
    def pack(self,fh,obj):
        raise FieldAbortError(self._name)
        

class MetaField(Field):
    debuglevel=0
    
    def __init__(self,name,func,default=None):
        Field.__init__(self,name,default)
        self._func=func

    def getNumBytes(self,obj):
        return self._func(obj)

    def unpack(self,fh,obj):
        try:
            data=self.read(fh,obj)
            setattr(obj,self._name,data)
        except Exception:
            dprint("FAILED: %s" % self)
            raise

    def pack(self,fh,obj):
        try:
            value=getattr(obj,self._name)
            fh.write(value)
        except Exception:
            dprint("FAILED: %s" % self)
            raise

class Skip(MetaField):
    debuglevel=0
    count=0
    
    def __init__(self,func,padding='\0',write=None):
        Skip.count+=1
        self._padding=padding
#        MetaField.__init__(self,"skip%d" % Skip.count,func,None)
        MetaField.__init__(self,None,func,None)
        self._writefunc=write

    def storeDefault(self,obj):
        pass
    
    def unpack(self,fh,obj):
        offset=self.getNumBytes(obj)
        # skip over the data entirely; don't even try to read it
        fh.seek(offset,1)
        
    def pack(self,fh,obj):
        if self._writefunc:
            self._writefunc(obj,fh,self.getNumBytes(obj))
        else:
            data=self._padding*self.getNumBytes(obj)
            fh.write(data)

class CString(Field):
    debuglevel=0
    
    def __init__(self,name,func=None,default=None):
        Field.__init__(self,name,default)
        self._func=func
        self._terminator='\x00'

        # _length is the number of bytes in the binary file, not the
        # number of bytes in the string.  This means that _length
        # INCLUDES THE TERMINATOR CHARACTER(S)!!!
        self._length=None

    def getNumBytes(self,obj):
        if self._func is not None:
            return self._func(obj)
        if self._length is not None:
            return self._length
        raise FieldLengthError('CString %s has unknown length until unpacked')

    def unpack(self,fh,obj):
        data=StringIO()
        self._length=0
        if self._func is not None:
            maxlen=self._func(obj)
        else:
            maxlen=-1 # Note: any negative number evaluates to True
        while maxlen:
            char=fh.read(1)
            self._length+=1
            maxlen-=1
            if char==self._terminator:
                break
            data.write(char)
        setattr(obj,self._name,data.getvalue())

        # If a length function has been specified and we're not there
        # yet, space foreward, skipping over junk
        if maxlen>0:
            fh.read(maxlen)

    def pack(self,fh,obj):
        value=getattr(obj,self._name)
        terminators=self._terminator

        # check if a field length is specified.
        if self._func is not None:
            maxlen=self._func(obj)
            valuelen=len(value) # don't include space for the terminator here
            if valuelen>=maxlen:
                value=value[0:maxlen-len(terminators)]
            elif valuelen<maxlen:
                # pad the binary file with extra terminators if necessary
                terminators=self._terminator*(maxlen-valuelen)
        fh.write(value)
        fh.write(terminators) # terminator always added here
        self._length=len(value)+len(terminators)




class FormatField(Field):
    debuglevel=0
    
    def __init__(self,name,fmt,default=None):
        Field.__init__(self,name,default)
        self._fmt=fmt
        self._size=struct.calcsize(fmt)

    def getNumBytes(self,obj):
        return self._size

    def unpack(self,fh,obj):
        try:
            data=self.read(fh,obj)
            setattr(obj,self._name,struct.unpack(self._fmt,data)[0])
        except Exception:
            dprint("FAILED: %s" % self)
            raise

    def pack(self,fh,obj):
        try:
            value=getattr(obj,self._name)
            if self._fmt.endswith('s'):
                if len(value)<self._size:
                    value+=' '*(self._size-len(value))
                elif len(value)>self._size:
                    value=value[0:self._size]
            fh.write(struct.pack(self._fmt,value))
        except Exception:
            dprint("FAILED: %s" % self)
            raise


class Wrapper(Field):
    debuglevel=0
    
    def __init__(self,proxy):
        Field.__init__(self,proxy._name,proxy._default)
        self._proxy=proxy

    def getProxy(self,obj):
        return self._proxy

    def storeDefault(self,obj):
        proxy=self.getProxy(obj)
        if isinstance(proxy,Record):
            self.dprint("calling %s.storeDefault(obj.%s)" % (str(proxy),proxy._name))
            setattr(obj,self._name,proxy.getCopy(obj))
            self.dprint("copy of %s = %s" % (self._name,getattr(obj,self._name)))
            child=getattr(obj,self._name)
            # set obj._ to be obj for parent object reference
            self.dprint("child=%s" % child.__class__.__name__)
            setattr(child,"_",obj)
        else:
            proxy.storeDefault(obj)
        
    def getNumBytes(self,obj):
        proxy=self.getProxy(obj)
        if isinstance(proxy,Record):
            self.dprint("calling %s.getNumBytes(obj.%s) proxy._name=%s" % (str(proxy),self._name,proxy._name))
            length=proxy.getNumBytes(getattr(obj,self._name))
        else:
            length=proxy.getNumBytes(obj)
        return length

    def unpack(self,fh,obj):
        proxy=self.getProxy(obj)
        if isinstance(proxy,Record):
            # check to see if the proxy object has changed, and if so
            # change the object that's stored in the parent to match
            # the proxy object.
            current=getattr(obj,self._name)
            if not isinstance(current,proxy.__class__):
                self.dprint("proxy has changed from %s to %s" % (current.__class__.__name__,proxy.__class__.__name__))
                self.storeDefault(obj)
            
            self.dprint("calling %s.unpack(obj.%s)" % (str(proxy),proxy._name))
            proxy.unpack(fh,getattr(obj,self._name))
        else:
            proxy.unpack(fh,obj)

    def pack(self,fh,obj):
        proxy=self.getProxy(obj)
        if isinstance(proxy,Record):
            self.dprint("calling %s.pack(obj.%s)" % (str(proxy),proxy._name))
            proxy.pack(fh,getattr(obj,self._name))
        else:
            proxy.pack(fh,obj)


class Switch(Wrapper):
    debuglevel=0
    
    def __init__(self,name,func,switch,default=None):
        if default is None:
            default=NoOp(name)
        Field.__init__(self,name,default)
        # don't use Wrapper.__init__ because it depends on a single
        # proxy object, not a dict.
        self._proxy=switch
        self._func=func

        self.renameSwitch()

    def renameSwitch(self):
        for key,field in self._proxy.iteritems():
            self.dprint("renaming switch %s: from %s to %s" % (str(key),field._name,self._name))
            field._name=self._name
        self._default._name=self._name

    def getProxy(self,obj):
        self.dprint("switch obj=%s" % obj)
        val=self._func(obj)
        if val in self._proxy:
            proxy=self._proxy[val]
        else:
            proxy=self._default
        self.dprint("switch found proxy=%s" % proxy)
        return proxy
        

class UnpackOnly(Wrapper):
    debuglevel=0
    
    def __init__(self,proxy):
        Wrapper.__init__(self,proxy)

    def unpack(self,fh,obj):
        Wrapper.unpack(self,fh,obj)

    def pack(self,fh,obj):
        pass

class PackOnly(Wrapper):
    debuglevel=0
    
    def __init__(self,proxy):
        Wrapper.__init__(self,proxy)

    def unpack(self,fh,obj):
        pass

    def pack(self,fh,obj):
        Wrapper.pack(self,fh,obj)

class Modify(Field):
    debuglevel=0
    
    def __init__(self,func):
        Field.__init__(self,None)
        self._func=func

    def storeDefault(self,obj):
        return
        
    def getNumBytes(self,obj):
        return 0

    def unpack(self,fh,obj):
        self._func(obj)

    def pack(self,fh,obj):
        self._func(obj)

class ModifyUnpack(Modify):
    debuglevel=0
    
    def pack(self,fh,obj):
        pass

class ModifyPack(Modify):
    debuglevel=0
    
    def unpack(self,fh,obj):
        pass


class ComputeUnpack(Field):
    debuglevel=0
    
    def __init__(self,name,func,default=None):
        Field.__init__(self,name,default)
        self._func=func

    def unpack(self,fh,obj):
        setattr(obj,self._name,self._func(obj))

    def pack(self,fh,obj):
        pass

class ComputePack(Wrapper):
    debuglevel=0
    
    def __init__(self,proxy,func):
        Wrapper.__init__(self,proxy)
        self._func=func

    # Have to override getNumBytes because the Wrapper version of this
    # method doesn't compute the value.  When the ComputePack is in an
    # If statement, it needs the value to be computed before checking
    # the condition.
    def getNumBytes(self,obj):
        proxy=self.getProxy(obj)
        value=self._func(obj)
        setattr(obj,proxy._name,value)
        return Wrapper.getNumBytes(self,obj)

    def pack(self,fh,obj):
        proxy=self.getProxy(obj)
        value=self._func(obj)
        setattr(obj,proxy._name,value)
        proxy.pack(fh,obj)

class Anchor(ComputeUnpack):
    debuglevel=0
    
    def __init__(self,name,default=None):
        ComputeUnpack.__init__(self,name,None,default)

    def unpack(self,fh,obj):
        setattr(obj,self._name,fh.tell())

    def pack(self,fh,obj):
        setattr(obj,self._name,fh.tell())


class Pointer(Wrapper):
    debuglevel=0
    
    def __init__(self,proxy,func):
        Wrapper.__init__(self,proxy)
        self._func=func

    def unpack(self,fh,obj):
        save=fh.tell()
        fh.seek(self._func(obj))
        Wrapper.unpack(self,fh,obj)
        fh.seek(save)

    def pack(self,fh,obj):
        save=fh.tell()
        fh.seek(self._func(obj))
        Wrapper.pack(self,fh,obj)
        fh.seek(save)


class ReadAhead(Wrapper):
    debuglevel=0
    
    def __init__(self,proxy):
        Wrapper.__init__(self,proxy)

    def getNumBytes(self,obj):
        return 0

    def unpack(self,fh,obj):
        save=fh.tell()
        Wrapper.unpack(self,fh,obj)
        fh.seek(save)

    def pack(self,fh,obj):
        pass


class IfElse(Wrapper):
    debuglevel=0
    
    def __init__(self,func,ifproxy,elseproxy=None,debug=False):
        Wrapper.__init__(self,ifproxy)
        self._func=func
        if elseproxy is not None:
            self._else=elseproxy
        else:
            self._else=NoOp(self._proxy._name)
        if debug:
            self.debuglevel=1
            self._proxy.debuglevel=1
            self._else.debuglevel=1

    def getProxy(self,obj):
        self.dprint("switch obj=%s" % obj)
        val=self._func(obj)
        if val:
            proxy=self._proxy
        else:
            proxy=self._else
        self.dprint("switch found proxy=%s" % proxy._name)
        return proxy

class If(IfElse):
    pass

class Adapter(Wrapper):
    debuglevel=0
    
    def __init__(self,proxy):
        Wrapper.__init__(self,proxy)

    def decode(self,value,obj):
        raise NotImplementedError

    def unpack(self,fh,obj):
        proxy=self.getProxy(obj)
        proxy.unpack(fh,obj)
        converted=self.decode(getattr(obj,proxy._name),obj)
        setattr(obj,proxy._name,converted)

    def encode(self,value,obj):
        raise NotImplementedError

    def pack(self,fh,obj):
        proxy=self.getProxy(obj)
        save=getattr(obj,proxy._name)
        converted=self.encode(save,obj)
        setattr(obj,proxy._name,converted)
        proxy.pack(fh,obj)
        setattr(obj,proxy._name,save)


class MetaSizeList(Adapter):
    """
    This structure is for when you know the length of the field, but
    you don't know how many elements are in the field.  The elements
    are parsed until the field runs out of bytes.  Upon writing, the
    field length will have to be changed to match the number of
    elements if the number of elements has changed.
    """
    debuglevel=0
        
    def __init__(self,proxy,func):
        Adapter.__init__(self,MetaField(proxy._name,func))
        self._itemproxy=proxy
        #self._debug=True

    # Unpack: call the proxy to get the raw data, then translate to
    # the required user data type
    def decode(self,value,obj):
        proxy=self._itemproxy
        data=[]
        length=len(value)
        self.dprint("overall length=%d, obj=%s" % (length,obj))
        fh=StringIO(value)
        i=0
        while fh.tell()<len(value):
            copy=proxy.getCopy(obj)
            setattr(copy,"_",obj)
            self.dprint("attempting to read primitive object %s.%s" % (obj.__class__.__name__,proxy._name))
            setattr(copy,"_listindex",i)
            proxy.unpack(fh,copy)
            self.dprint("primitive copy=%s" % copy)
            if isinstance(proxy,Record):
                data.append(copy)
            else:
                data.append(getattr(copy,proxy._name))
            i+=1
        return data

    # pack: translate the user data type to the type the proxy can
    # use.  The proxy will then turn it into raw bytes
    def encode(self,value,obj):
        proxy=self._itemproxy
        num=len(value)
        fh=StringIO()
        self.dprint("looping %d times for proxy %s" % (num,proxy._name))
        for i in range(num):
            self.dprint("value[%d]=%s" % (i,value[i]))
            if isinstance(proxy,Record):
                proxy.pack(fh,value[i])
            else:
                setattr(obj,proxy._name,value[i])
                proxy.pack(fh,obj)
        return fh.getvalue()


class CookedInt(Adapter):
    debuglevel=0
    
    def __init__(self,proxy,fmt=None):
        Adapter.__init__(self,proxy)

        # Fail hard if the user tries to use a CookedInt adapter with
        # a meta construct by passing None as the value dict.
        if fmt is not None:
            self._fmt=fmt
        else:
            self._fmt="%0"+str(proxy.getNumBytes(None))+"d"

    # Unpack: call the proxy to get the raw data, then translate to
    # the required user data type
    def decode(self,value,obj):
        self.dprint("converting %s to int" % value)
        try:
            return int(value)
        except ValueError:
            print "failed converting value='%s'" % str(value)
            print self
            print self._proxy
            return 0

    # pack: translate the user data type to the type the proxy can
    # use.  The proxy will then turn it into raw bytes
    def encode(self,value,obj):
        try:
            return self._fmt % value
        except TypeError:
            print "failed converting %s to %s" % (value,self._fmt)
            print self
            print self.proxy
            raise

class CookedFloat(Adapter):
    debuglevel=0
    
    def __init__(self,proxy,fmt):
        Adapter.__init__(self,proxy)

        # Fail hard if the user tries to use a CookedInt adapter with
        # a meta construct by passing None as the value dict.
        self._fmt=fmt

    # Unpack: call the proxy to get the raw data, then translate to
    # the required user data type
    def decode(self,value,obj):
        self.dprint("converting %s to float" % value)
        try:
            return float(value)
        except ValueError:
            print "failed converting value='%s'" % str(value)
            print self
            print self._proxy
            return 0

    # pack: translate the user data type to the type the proxy can
    # use.  The proxy will then turn it into raw bytes
    def encode(self,value,obj):
        return self._fmt % value

class List(Wrapper):
    debuglevel=0
    
    def __init__(self,proxy,num):
        Wrapper.__init__(self,proxy)
        self._num=num
        
    def storeDefault(self,obj):
        proxy=self.getProxy(None)
        setattr(obj,proxy._name,[])
        #proxy.storeDefault(obj)
        ##save=getattr(obj,proxy._name)
        ##setattr(obj,proxy._name,[save])

    def getRepeats(self,obj):
        return self._num

    def getNumBytes(self,obj):
        proxy=self.getProxy(obj)
        # All objects aren't necessarily the same length now
##        setattr(obj,"_listindex",0)
##        return self.getRepeats(obj)*proxy.getNumBytes(obj)
        size=0
        num=self.getRepeats(obj)
        self.dprint("looping %s times for proxy %s (type %s)" % (str(num),proxy._name,proxy.__class__.__name__))
        if isinstance(proxy,Record):
            array=getattr(obj,proxy._name)
            for i in range(num):
                # call superclass unpack that handles Record subclasses
                self.dprint("attempting to get size %s.%s" % (obj.__class__.__name__,proxy._name))
                #copy=proxy.getCopy(obj)
                self.dprint(array[i])
                dup=copy.copy(array[i])
                self.dprint(dup)
                setattr(dup,"_",obj)
                setattr(dup,"_listindex",i)
                self.dprint("obj = %s\ncopy = %s" % (obj,dup))
                size+=proxy.getNumBytes(dup)
        else:
            dup=proxy.getCopy(obj)
            setattr(dup,"_",obj)
            for i in range(num):
                # call superclass unpack that handles Record subclasses
                self.dprint("attempting to get size of primivite object %s.%s" % (obj.__class__.__name__,proxy._name))
                setattr(dup,"_listindex",i)
                size+=Wrapper.getNumBytes(self,dup)
        return size

    def unpack(self,fh,obj):
        proxy=self.getProxy(obj)
        data=[]
        num=self.getRepeats(obj)
        self.dprint("looping %d times for proxy %s" % (num,proxy._name))
        if isinstance(proxy,Record):
            for i in range(num):
                # call superclass unpack that handles Record subclasses
                self.dprint("attempting to read %s.%s" % (obj.__class__.__name__,proxy._name))
                copy=proxy.getCopy(obj)
                setattr(copy,"_",obj)
                setattr(copy,"_listindex",i)
                proxy.unpack(fh,copy)
                data.append(copy)
        else:
            copy=proxy.getCopy(obj)
            setattr(copy,"_",obj)
            for i in range(num):
                # call superclass unpack that handles Record subclasses
                self.dprint("attempting to read primitive object %s.%s" % (obj.__class__.__name__,proxy._name))
                setattr(copy,"_listindex",i)
                Wrapper.unpack(self,fh,copy)
                self.dprint("primitive copy=%s" % copy)
                data.append(getattr(copy,proxy._name))
            
            
        # replace the parent's copy of the proxied object with the new list
        setattr(obj,proxy._name,data)

    def pack(self,fh,obj):
        proxy=self.getProxy(obj)
        save=getattr(obj,proxy._name)
        num=self.getRepeats(obj)
        self.dprint("looping %d times for proxy %s; save=%s" % (num,proxy._name,save))
        for i in range(num):
            self.dprint("save[%d]=%s" % (i,save[i]))
            if isinstance(proxy,Record):
                proxy.pack(fh,save[i])
            else:
                setattr(obj,proxy._name,save[i])
                proxy.pack(fh,obj)
        setattr(obj,proxy._name,save)

class MetaList(List):
    debuglevel=0
    
    def __init__(self,proxy,func):
        List.__init__(self,proxy,func)
        #self._debug=1

    def getRepeats(self,obj):
        return self._num(obj)




##### Derived types

def SLInt8(name,default=0): return FormatField(name,'<b',default)
def SBInt8(name,default=0): return FormatField(name,'>b',default)
def ULInt8(name,default=0): return FormatField(name,'<B',default)
def UBInt8(name,default=0): return FormatField(name,'>B',default)
def SLInt16(name,default=0): return FormatField(name,'<h',default)
def SBInt16(name,default=0): return FormatField(name,'>h',default)
def ULInt16(name,default=0): return FormatField(name,'<H',default)
def UBInt16(name,default=0): return FormatField(name,'>H',default)
def SLInt32(name,default=0): return FormatField(name,'<i',default)
def SBInt32(name,default=0): return FormatField(name,'>i',default)
def ULInt32(name,default=0): return FormatField(name,'<I',default)
def UBInt32(name,default=0): return FormatField(name,'>I',default)
def LFloat32(name,default=0): return FormatField(name,'<f',default)
def BFloat32(name,default=0): return FormatField(name,'>f',default)
def LFloat64(name,default=0): return FormatField(name,'<d',default)
def BFloat64(name,default=0): return FormatField(name,'>d',default)

def Tuple(field,num): return List(field,num)

def String(name,length): return MetaField(name,length)


class Record(Field):
    """baseclass for binary records"""
    debuglevel=0
    
    _defaultstore={}
    
    typedef=()
    
    def __init__(self,name=None,default=None,typedef=None,debuglevel=0):
        if debuglevel>0:
            self.debuglevel=debuglevel
        if name==None: name==self.__class__.__name__
        if typedef is not None:
            if not isinstance(typedef,list) and not isinstance(typedef,tuple):
                typedef=(typedef,)
            self.typedef=typedef
        if self.typedef is None or len(self.typedef)==0:
            raise FieldTypedefError("Missing typedefs for %s %s" % (self.__class__.__name__,name))
            
        Field.__init__(self,name,default)

        self._currentlyprocessing=None
        
        self.storeDefault(self)

    def storeDefault(self,obj):
        self.dprint("storing defaults for %s" % self.__class__.__name__)
        for field in self.typedef:
            self._currentlyprocessing=field
            self.dprint("  typedef=%s" % field)
            if isinstance(field,Record):
                # set temporary reference of subobject to None
                setattr(obj,field._name,field.getCopy(obj))
                self.dprint("  copy of %s = %s" % (field._name,getattr(obj,field._name)))
                child=getattr(obj,field._name)
                # set obj._ to be obj for parent object reference
                self.dprint("  child=%s" % child.__class__.__name__)
                setattr(child,"_",obj)
                #field.storeDefault(child)
            else:
                self.dprint("  primitive object %s, store in %s" % (field._name,obj))
                if isinstance(self._default,dict) and field._name in self._default:
                    if isinstance(field,Wrapper):
                        proxy=field.getProxy(obj)
                        proxy._default=self._default[field._name]
                    else:
                        field._default=self._default[field._name]
                field.storeDefault(obj)
            self.dprint("  setting %s.%s=%s" % (field.__class__.__name__,field._name,field))
        self.dprint("defaults for %s" % (str(obj)))
        self._currentlyprocessing=None


    def getNumBytes(self,obj,subtypedefs=None):
        length=0
        if subtypedefs is not None:
            typedefs=subtypedefs
        else:
            typedefs=self.typedef
        for field in typedefs:
            self._currentlyprocessing=field
            if isinstance(field,Record):
                bytes=field.getNumBytes(getattr(obj,field._name))
                self.dprint("%s.getNumBytes(values[%s])=%d" % (str(field),field._name,bytes))
                length+=bytes
            else:
                bytes=field.getNumBytes(obj)
                self.dprint("%s.getNumBytes(values[%s])=%d" % (str(field),field._name,bytes))
                length+=bytes
##            length+=field.getNumBytes(obj)
        self.dprint("length=%d" % length)
        self._currentlyprocessing=None
        return length
    
    def unpack(self,fh,obj):
        self.dprint("fh.tell()=%s before=%s" % (fh.tell(),obj))
        for field in self.typedef:
            self._currentlyprocessing=field
            self.dprint("field=%s" % str(field))
            if isinstance(field,Record):
                self.dprint("calling %s.unpack(obj.%s)" % (str(field),field._name))
                field.unpack(fh,getattr(obj,field._name))
            else:
                self.dprint("field=%s" % str(field))
                field.unpack(fh,obj)
##            field.unpack(fh,obj)
            self.dprint("unpacked %s=%s" % (field._name,field._name and getattr(obj,field._name) or "None"))
        self.dprint("fh.tell()=%s after=%s" % (fh.tell(),obj))
        self._currentlyprocessing=None

    def pack(self,fh,obj):
        #fh=StringIO()
        for field in self.typedef:
            self._currentlyprocessing=field
            self.dprint("field=%s" % str(field))
            if isinstance(field,Record):
                field.pack(fh,getattr(obj,field._name))
            else:
                self.dprint("packing %s" % field)
                field.pack(fh,obj)
##            self.dprint("packed %s=%s" % (field._name,repr(bytes)))
##            fh.write(bytes)
##        return fh.getvalue()
        self._currentlyprocessing=None
    
    def unserialize(self,fh,partial=False):
        try:
            self.unpack(fh,self)
        except EOFError:
            print "EOFError: failed while processing field %s" % self._currentlyprocessing
            print self
            if not partial:
                raise

        self.unserializePostHook()

    def unserializePostHook(self):
        pass

    def serializePreHook(self):
        pass

    def serialize(self,fh,partial=False):
        self.serializePreHook()
        
        try:
            self.pack(fh,self)
        except struct.error:
            print "struct.error: failed while processing field %s" % self._currentlyprocessing
            print self
            if partial:
                return
            raise

    def size(self):
        return self.getNumBytes(self)

    def sizeSubset(self,start,end):
        typedefs=[]
        i=iter(self.typedef)
        for field in i:
            #print field._name
            if field._name==start:
                self.dprint("starting at field=%s" % field._name)
                typedefs.append(field)
                break
        for field in i:
            self.dprint("including field=%s" % field._name)
            typedefs.append(field)
            if field._name==end:
                self.dprint("stopping at field=%s" % field._name)
                break

        bytes=self.getNumBytes(self,subtypedefs=typedefs)
        self.dprint("total length = %s" % bytes)
        return bytes


class RecordList(list):
    def __init__(self,parent):
        list.__init__(self)
        self.parent=parent
        
    def append(self,item):
        #print "current length=%d" % len(self)
        item._=self.parent
        item._listindex=len(self)
        list.append(self,item)
