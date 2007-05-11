#!/usr/bin/env python
"""
Test the packing and unpacking of structrecord

"""



import os,os.path,sys,re,time,commands
from optparse import OptionParser
from peppy.lib.structrecord import *

from cStringIO import StringIO

from nose.tools import raises
def eq_(a,b):
    try:
        assert a==b
    except:
        import inspect
        caller=inspect.stack()[1]
        message='%s != %s' % (str(a),str(b))
        tb=sys.exc_info()[2]
        # This doesn't work: can't assign to traceback objects.
##        tb1=tb
##        while tb1.tb_next is not None:
##            tb1=tb1.tb_next
##        tb1.tb_next=None
        raise AssertionError,message,tb
    return True

class ExampleData(object):
    def __init__(self, **kw):
        for k,v in kw.iteritems():
            setattr(self,k,v)

@raises(FieldTypedefError)
def testEmptyTypedef():
    rec=Record(typedef=())
            

@raises(FieldAbortError)
def testAbort1():
    rec=Record(typedef=(
        CookedInt(FormatField('len','3s')),
        Abort('checkpoint1'),
        ))
    fh=StringIO("000")
    rec.unserialize(fh) # raises exception here
    #self.assertRaises(FieldAbortError,rec.unserialize,fh)
    eq_(rec.len,0)

@raises(FieldAbortError)
def testAbort2():
    rec=Record(typedef=(
        CookedInt(FormatField('len','3s')),
        If(lambda s:s.len==0,Abort('checkpoint1')),
        ))
    fh=StringIO("000")
    rec.unserialize(fh) # raises exception here
    #self.assertRaises(FieldAbortError,rec.unserialize,fh)
    eq_(rec.len,0)

def testAbort3():
    rec=Record(typedef=(
        CookedInt(FormatField('len','3s')),
        If(lambda s:s.len==0,Abort('checkpoint1')),
        ))
    fh=StringIO("001")
    rec.unserialize(fh)
    eq_(rec.len,1)

@raises(FieldAbortError)
def testAbort4():
    rec=Record(typedef=(
        CookedInt(FormatField('len','3s')),
        If(lambda s:s.len==0,Abort('checkpoint1')),
        CookedInt(FormatField('stop','3s')),
        If(lambda s:s.stop==1,Abort('checkpoint2')),
        CookedInt(FormatField('notreached','3s')),
        ))
    fh=StringIO("001001999")
    rec.unserialize(fh)
    #self.assertRaises(FieldAbortError,rec.unserialize,fh)
    eq_(rec.len,1)
    eq_(rec.stop,1)
    eq_(rec.notreached,None)


class RecordSetupMixin(object):
    typedef=()
    raw=""
    values=ExampleData()
    
    def setUp(self):
        self.rec=Record(typedef=self.__class__.typedef)
        
    def tearDown(self):
        pass

class BaseTest(RecordSetupMixin):
    def compareObjObj(self,obj,data):
        for name,datavalue in data.__dict__.iteritems():
            if name=='_': continue
            #print "name=%s" % str(name)
            assert hasattr(obj,name),"%s not in object" % name
            objvalue=getattr(obj,name)
            if isinstance(datavalue,ExampleData):
                assert isinstance(objvalue,Record),"%s should be a Record" % name
                self.compareObjObj(objvalue,datavalue)
            elif isinstance(datavalue,list):
                eq_(len(objvalue),len(datavalue))
                # compare individual entries
                for obji,datai in zip(objvalue,datavalue):
                    if isinstance(datai,ExampleData):
                        self.compareObjObj(obji,datai)
                    else:
                        #print "obji=%s datai=%s" % (obji,datai)
                        eq_(obji,datai)
            else:
                eq_(objvalue,datavalue)
                #print "checked %s=%s" % (name,datavalue)
        #print "obj %s validated." % obj
            
    def storeObjObj(self,obj,data):
        for name,datavalue in data.__dict__.iteritems():
            if name=='_': continue
            #print "name=%s" % str(name)
            if isinstance(datavalue,ExampleData):
                #print "datavalue=%s" % datavalue
                if not hasattr(obj,name):
                    # This happens if we are creating a list of
                    # conditional objects, where the objects
                    # themselves have subobjects.  The subobjects
                    # aren't created by the Record's init process,
                    # because the list object contains an empty list.
                    newobj=NoOp("subdummy")
                    setattr(obj,name,newobj)
                self.storeObjObj(getattr(obj,name),datavalue)
            elif isinstance(datavalue,list):
                sublist=[]
                setattr(obj,name,sublist)
                for valuei in datavalue:
                    #print "storing %s in list %s" % (valuei,str(name))
                    if isinstance(valuei,ExampleData):
                        #print "storing ExampleData object %s in list %s" % (valuei,str(name))
                        obji=NoOp("dummy")
                        self.storeObjObj(obji,valuei)
                        sublist.append(obji)
                    else:
                        sublist.append(valuei)
            else:
                setattr(obj,name,datavalue)
                #print "set %s=%s" % (name,datavalue)
        #print "obj %s set." % obj
            

    def test1_Unpack(self):
        #print
        #print "#"*5+"unpacking %s" % self.__class__.__name__
        #print self.__class__.values
        fh=StringIO(self.__class__.raw)
        self.rec.unserialize(fh)
        #print self.__class__.values
        self.compareObjObj(self.rec,self.__class__.values)
##        for name in self.__class__.values:
##            #print "%s: rec=%s should be=%s" % (name,repr(self.__class__.values[name]),repr(self.__class__.values[name]))
##            eq_(self.__class__.values[name],self.__class__.values[name])

    def test2_Pack(self):
        #print
        #print "#"*5+"packing %s" % self.__class__.__name__
        #print "testPack: values=%s" % self.__class__.values
        self.storeObjObj(self.rec,self.__class__.values)
        fh=StringIO()
        self.rec.serialize(fh)
        bytes=fh.getvalue()
        #print repr(bytes)
        eq_(len(self.__class__.raw),len(bytes))
        eq_(len(self.__class__.raw),self.rec.size())
        eq_(self.__class__.raw,bytes)

    def test3_Size(self):
        self.storeObjObj(self.rec,self.__class__.values)
        size=self.rec.size()
        eq_(len(self.__class__.raw),size)
        
  


class Subtest2b(Record):
    typedef=(
        FormatField('testb1','<b'),
        FormatField('testb2','<b'),
        )

class Subtest2h(Record):
    typedef=(
        FormatField('testh1','<h'),
        FormatField('testh2','<h'),
        )

class SubtestDoubleParentNum(Record):
    typedef=(
        ComputeUnpack('numdoubled',lambda vals:vals._.num*2),
        )

class Switch1(Record):
    typedef=(
        SLInt32('value'),
        )

class Switch2(Record):
    typedef=(
        List(SLInt16('value'),2),
        )

class Switch3(Record):
    typedef=(
        MetaField('value',lambda vals:vals._.len),
        )



class TestInts1(BaseTest):
    typedef=(
        FormatField('testi1','<i'),
        SLInt32('testi2'),
        SBInt32('testi3'),
        )
    raw="\x12\x34\x56\x78\x23\x45\x67\x53\x32\x54\x76\x48"
    values=ExampleData(
        testi1=0x78563412,
        testi2=0x53674523,
        testi3=0x32547648,
        )
    
class TestSub1(BaseTest):
    typedef=(
        FormatField('testisub1','<i'),
        FormatField('testisub2','<i'),
        Subtest2h('sub'),
        )
    raw="\x12\x34\x56\x78\x23\x45\x67\x53\x48\x76\x54\x32"
    values=ExampleData(
        testisub1=0x78563412,
        testisub2=0x53674523,
        sub=ExampleData(testh1=0x7648,testh2=0x3254),
        )

class Testwrapperh(BaseTest):
    typedef=(
        FormatField('testh1','>h'),
        FormatField('testh2','>h'),
        Wrapper(FormatField('testh3','>h')),
        )
    raw="\x10\x43\x25\x75\x39\x22"
    values=ExampleData(
        testh1=0x1043,
        testh2=0x2575,
        testh3=0x3922,
        )

class Testwrappertestisub(BaseTest):
    typedef=(
        FormatField('testisub1','<i'),
        FormatField('testisub2','<i'),
        Wrapper(Subtest2h('sub')),
        )
    raw="\x12\x34\x56\x78\x23\x45\x67\x53\x48\x76\x54\x32"
    values=ExampleData(
        testisub1=0x78563412,
        testisub2=0x53674523,
        sub=ExampleData(testh1=0x7648,
                     testh2=0x3254,
                     )
        )


class Teststring1(BaseTest):
    typedef=(
        FormatField('test1','3s'),
        )
    raw="001"
    values=ExampleData(
        test1="001",
        )
    

class Testconvert1(BaseTest):
    typedef=(
        CookedInt(FormatField('test1','3s')),
        CookedInt(FormatField('test2','3s'),"%+03d"),
        )
    raw="001+45"
    values=ExampleData(
        test1=1,
        test2=45,
        )
     
class Testconvert2(BaseTest):
    typedef=(
        CookedFloat(FormatField('test1','10s'),'%+10.6f'),
        CookedFloat(FormatField('test2','11s'),'%+11.6f'),
        )
    raw="+34.334000-112.345600"
    values=ExampleData(
        test1=34.334,
        test2=-112.3456
        )
     

class Testlist1(BaseTest):
    typedef=(
        List(FormatField('testh','>h'),3),
        )
    raw="\x10\x43\x25\x75\x39\x22"
    values=ExampleData(
        testh=[0x1043,0x2575,0x3922,],
        )
     
class Testlist2(BaseTest):
    typedef=(
        List(List(FormatField('testb','>b'),3),2),
        )
    raw="\x10\x43\x25\x75\x39\x22"
    values=ExampleData(
        testb=[[0x10,0x43,0x25],[0x75,0x39,0x22],],
        )
    
class Testlist3(BaseTest):
    typedef=(
        List(Tuple(SLInt8('testb'),3),2),
        )
    raw="\x10\x43\x25\x75\x39\x22"
    values=ExampleData(
        testb=[[0x10,0x43,0x25],[0x75,0x39,0x22],],
        )
    

class Testmetalist1(BaseTest):
    typedef=(
        FormatField('num','>b'),
        MetaList(FormatField('testh','>h'),lambda vals:vals.num),
        )
    raw="\x03\x10\x43\x25\x75\x39\x22"
    values=ExampleData(
        num=3,
        testh=[0x1043,0x2575,0x3922,],
        )
     

class Testlistsub1(BaseTest):
    typedef=(
        List(Subtest2b('sub'),3),
        )
    raw="\x10\x43\x25\x75\x39\x22"
    values=ExampleData(
        sub=[ExampleData(testb1=0x10,testb2=0x43),
             ExampleData(testb1=0x25,testb2=0x75),
             ExampleData(testb1=0x39,testb2=0x22),
             ],
        )
     
         
class Testmetalist2(BaseTest):
    typedef=(
        FormatField('num','>b'),
        MetaList(Subtest2b('sub'),lambda vals:vals.num),
        )
    raw="\x03\x10\x43\x25\x75\x39\x22"
    values=ExampleData(
        num=3,
        sub=[ExampleData(testb1=0x10,testb2=0x43),
             ExampleData(testb1=0x25,testb2=0x75),
             ExampleData(testb1=0x39,testb2=0x22),
             ],
        )
    
class Testmetalistrecord1(BaseTest):
    typedef=(
        FormatField('num','>b'),
        MetaList(Record('sub',typedef=(FormatField('testb1','<b'),FormatField('testb2','<b'))),lambda vals:vals.num),
        )
    raw="\x03\x10\x43\x25\x75\x39\x22"
    values=ExampleData(
        num=3,
        sub=[ExampleData(testb1=0x10,testb2=0x43),
             ExampleData(testb1=0x25,testb2=0x75),
             ExampleData(testb1=0x39,testb2=0x22),
             ],
        )
    

class Testmetalistonpack1(BaseTest):
    typedef=(
        ComputePack(FormatField('num','>b'),lambda vals:len(vals.sub)),
        MetaList(Subtest2b('sub'),lambda vals:vals.num),
        )
    raw="\x03\x10\x43\x25\x75\x39\x22"
    values=ExampleData(
        num=3,
        sub=[ExampleData(testb1=0x10,testb2=0x43),
             ExampleData(testb1=0x25,testb2=0x75),
             ExampleData(testb1=0x39,testb2=0x22),
             ],
        )
    

class Testmetalistcompute(BaseTest):
    typedef=(
        ComputePack(FormatField('num','>b'),lambda vals:len(vals.sub)),
        ComputeUnpack('computed',lambda vals:vals.num*1000),
        MetaList(Subtest2b('sub'),lambda vals:vals.num),
        )
    raw="\x03\x10\x43\x25\x75\x39\x22"
    values=ExampleData(
        num=3,
        computed=3000,
        sub=[ExampleData(testb1=0x10,testb2=0x43),
             ExampleData(testb1=0x25,testb2=0x75),
             ExampleData(testb1=0x39,testb2=0x22),
             ],
        )
    
class Testifcompute(BaseTest):
    typedef=(
        ComputePack(SBInt8('NBANDS'),lambda s:s.BANDS<10 and s.BANDS or int(0)),
        If(lambda s:s.NBANDS==0,ComputePack(SBInt16('XBANDS'),lambda s:s.BANDS),debug=False),
        ComputeUnpack('BANDS',lambda s:s.NBANDS==0 and s.XBANDS or s.NBANDS),
        )
    raw="\x00\x39\x22"
    values=ExampleData(
        NBANDS=0,
        XBANDS=0x3922,
        BANDS=0x3922,
        )
    
class Testifcompute2(BaseTest):
    typedef=(
        ComputePack(SBInt8('NBANDS'),lambda s:s.BANDS<10 and s.BANDS or int(0)),
        If(lambda s:s.NBANDS==0,ComputePack(SBInt16('XBANDS'),lambda s:s.BANDS),debug=False),
        ComputeUnpack('BANDS',lambda s:s.NBANDS==0 and s.XBANDS or s.NBANDS),
        )
    raw="\x03"
    values=ExampleData(
        NBANDS=3,
        XBANDS=None,
        BANDS=3,
        )

class Testifcompute3(BaseTest):
    typedef=(
        ComputePack(SBInt8('NBANDS'),lambda s:s.BANDS<10 and s.BANDS or int(0)),
        If(lambda s:s.NBANDS==0,ComputePack(SBInt16('XBANDS'),lambda s:s.BANDS),debug=False),
        ComputeUnpack('BANDS',lambda s:s.NBANDS==0 and s.XBANDS or s.NBANDS),
        )
    raw="\x00\x39\x22"

    def testPack(self):
        self.rec.BANDS=0x3922
        fh=StringIO()
        self.rec.serialize(fh)
        bytes=fh.getvalue()
        #print repr(bytes)
        eq_(len(self.__class__.raw),len(bytes))
        eq_(len(self.__class__.raw),self.rec.size())
        eq_(self.__class__.raw,bytes)
        eq_(self.rec.XBANDS,0x3922)
        
    def testPack1(self):
        self.rec.BANDS=3
        fh=StringIO()
        self.rec.serialize(fh)
        bytes=fh.getvalue()
        #print repr(bytes)
        eq_(1,len(bytes))
        eq_(1,self.rec.size())
        eq_("\x03",bytes)
        eq_(self.rec.NBANDS,3)
        
    def testSize1(self):
        # tests that computed structure is only 1 byte, that the If
        # statement is providing the correct value.
        self.rec.BANDS=3
        eq_(1,self.rec.size())
        eq_(self.rec.NBANDS,3)
        


class Testmetalistmetafield1(BaseTest):
    typedef=(
        SLInt8('num'),
        MetaList(SLInt8('lengths'),lambda vals:vals.num),
        MetaList(MetaField('strings',lambda vals:vals._.lengths[vals._listindex]),lambda vals:vals.num),
        )
    raw="\x03\x02\x05\x04hitheredude"
    values=ExampleData(
        num=3,
        lengths=[2,5,4],
        strings=["hi","there","dude"],
        )
    
class Testmetalistmetalist1(BaseTest):
    typedef=(
        SLInt8('numouter'),
        SLInt8('numinner'),
        MetaList(MetaList(SLInt8('data'),lambda vals:vals._.numinner),lambda vals:vals.numouter),
        )
    raw="\x02\x03\x10\x43\x25\x75\x39\x22"
    values=ExampleData(
        numouter=2,
        numinner=3,
        data=[[0x10,0x43,0x25],[0x75,0x39,0x22],],
        )

class recordwithmeta(Record):
    typedef=(
        MetaList(SLInt8('data'),lambda vals:vals._.numinner),
        )

class Testmetalistmetarecord1(BaseTest):
    typedef=(
        SLInt8('numouter'),
        SLInt8('numinner'),
        MetaList(recordwithmeta('data'),lambda vals:vals.numouter),
        )
    raw="\x02\x03\x10\x43\x25\x75\x39\x22"
    values=ExampleData(
        numouter=2,
        numinner=3,
        data=[[0x10,0x43,0x25],[0x75,0x39,0x22],],
        )
    
class Testmetasizelist1(BaseTest):
    typedef=(
        SLInt8('len'),
        MetaSizeList(CString('strings'),lambda vals:vals.len),
        )
    raw="\x0Ehi\0there\0dude\0"
    values=ExampleData(
        len=14,
        strings=["hi","there","dude"],
        )
    

class Testanchor1(BaseTest):
    typedef=(
        Anchor('start'),
        List(FormatField('testh','>h'),3),
        Anchor('end'),
        ComputeUnpack('computed',lambda vals:vals.end-vals.start),
        )
    raw="\x10\x43\x25\x75\x39\x22"
    values=ExampleData(
        start=0,
        end=6,
        computed=6,
        testh=[0x1043,0x2575,0x3922,],
        )
    
class Testskip1(BaseTest):
    typedef=(
        SBInt8('num'),
        Skip(lambda vals:vals.num,padding="!"),
        SBInt8('stuff')
        )
    raw="\x10!!!!!!!!!!!!!!!!\x11"
    values=ExampleData(
        num=16,
        stuff=17,
        )
    

class Testparent1(BaseTest):
    typedef=(
        Anchor('start'),
        List(FormatField('testh','>h'),3),
        Anchor('end'),
        ComputeUnpack('computed',lambda vals:vals.end-vals.start),
        ComputeUnpack('num',lambda vals:vals.computed),
        SubtestDoubleParentNum('child'),
     )
    raw="\x10\x43\x25\x75\x39\x22"
    values=ExampleData(
        start=0,
        end=6,
        computed=6,
        child=ExampleData(numdoubled=12),
        testh=[0x1043,0x2575,0x3922,],
        )
     

class Testmetafield1(BaseTest):
    typedef=(
        FormatField('num','>b'),
        MetaField('data',lambda vals:vals.num),
        )
    raw="\x08blahblah"
    values=ExampleData(
        num=8,
        data='blahblah',
        )
     

class Testswitch1(BaseTest):
    typedef=(
        FormatField('type','>b'),
        FormatField('len','>b'),
        Switch('data',lambda vals:vals.type,
               {1: Switch1('data'),
                2: Switch2('data'),
                },
               default = Switch3('data')
               )
        )
    raw="\x01\x04\x10\x43\x25\x75"
    values=ExampleData(
        type=1,
        len=4,
        data=ExampleData(value=0x75254310),
        )
     
class Testswitch2(BaseTest):
    typedef=(
        FormatField('type','>b'),
        FormatField('len','>b'),
        Switch('data',lambda vals:vals.type,
               {1: Switch1('data'),
                2: Switch2('data'),
                },
               default = Switch3('data')
               )
        )
    raw="\x02\x04\x10\x43\x25\x75"
    values=ExampleData(
        type=2,
        len=4,
        data=ExampleData(value=[0x4310,0x7525]),
        )
     
class TestswitchDefault(BaseTest):
    typedef=(
        FormatField('type','>b'),
        FormatField('len','>b'),
        Switch('data',lambda vals:vals.type,
               {1: Switch1('data'),
                2: Switch2('data'),
                },
               default = Switch3('data')
               )
        )
    raw="\x10\x04\x10\x43\x25\x75"
    values=ExampleData(
        type=16,
        len=4,
        data=ExampleData(value="\x10\x43\x25\x75"),
        )
     

class Testreadahead1(BaseTest):
    typedef=(
        ReadAhead(SBInt8('readahead')),
        SBInt8('type'),
        SBInt8('len'),
        Switch('data',lambda vals:vals.type,
               {1: Switch1('data'),
                2: Switch2('data'),
                },
               default = Switch3('data')
               )
        )
    raw="\x02\x04\x10\x43\x25\x75"
    values=ExampleData(
        readahead=2,
        type=2,
        len=4,
        data=ExampleData(value=[0x4310,0x7525]),
        )
     
class Testreadahead2(BaseTest):
    typedef=(
        ReadAhead(List(SBInt8('readahead'),3)),
        SBInt8('type'),
        SBInt8('len'),
        Switch('data',lambda vals:vals.type,
               {1: Switch1('data'),
                2: Switch2('data'),
                },
               default = Switch3('data')
               )
        )
    raw="\x02\x04\x10\x43\x25\x75"
    values=ExampleData(
        readahead=[2,4,16],
        type=2,
        len=4,
        data=ExampleData(value=[0x4310,0x7525]),
        )
     
class Testcondition1(BaseTest):
    typedef=(
        SLInt32('test1'),
        If(lambda s:s.test1>0,SLInt32('value1')),
        )
    raw="\x01\x00\x00\x00\x02\x00\x00\x00"
    values=ExampleData(
        test1=1,
        value1=2,
        )
    

class Testcondition2(BaseTest):
    typedef=(
        SLInt32('test1'),
        If(lambda s:s.test1<0,SLInt32('value1')),
        )
    raw="\x01\x00\x00\x00"
    values=ExampleData(
        test1=1,
        value1=None,
        )
    
    
class Testcondition2(BaseTest):
    typedef=(
        SLInt32('test1'),
        IfElse(lambda s:s.test1<0,SLInt32('value1'),List(SLInt8('value1'),4)),
        )
    raw="\x01\x00\x00\x00\x02\x03\x04\x05"
    values=ExampleData(
        test1=1,
        value1=[2,3,4,5],
        )
    

class Testconditionlist1(BaseTest):
    typedef=(
        CookedInt(FormatField('num','3s')),
        If(lambda s:s.num>0,MetaList(SLInt16('value1'),lambda s:s.num)),
        )
    raw="005\x01\x00\x02\x00\x03\x00\x04\x00\x05\x00"
    values=ExampleData(
        num=5,
        value1=[1,2,3,4,5],
        )
    

class Testconditionlist2(BaseTest):
    typedef=(
        CookedInt(FormatField('num','3s')),
        If(lambda s:s.num>0,MetaList(CookedInt(FormatField('value1','3s')),lambda s:s.num)),
        )
    raw="005001002003004005"
    values=ExampleData(
        num=5,
        value1=[1,2,3,4,5],
        )
    

class Teststring2(BaseTest):
    typedef=(
        SLInt16('len'),
        FormatField('string1','10s'),
        String('string2',lambda obj: obj.len),
        CString('string3'),
        CString('string4',lambda obj: obj.len),
        )
    raw="\x0a\x00whatever  WHATEVER\0\0stuff\0stuff\0\0\0\0\0"
    values=ExampleData(
        len=10,
        string1='whatever  ',
        string2='WHATEVER\0\0',
        string3='stuff',
        string4='stuff')
    

def NInt(name,length,default=None):
    return CookedInt(FormatField(name,"%ds" % length,default))
def NStr(name,length,default=None):
    return FormatField(name,"%ds" % length,default)

class TRE_PIAPEA(Record):
    typedef=(
        NStr('LASTNME',28),
        NStr('FIRSTNME',28),
        NStr('MIDNME',28),
        NStr('DOB',6),
        NStr('ASSOCTRY',2),
        )
        
class TRE_PIAPEB(Record):
    typedef=(
        NStr('LASTNME',28),
        NStr('FIRSTNME',28),
        NStr('MIDNME',28),
        NStr('DOB',8),
        NStr('ASSOCTRY',2),
        )

TREDict={
    'PIAPEA': TRE_PIAPEA(),
    }

class TRE(Record):
    typedef=(
        NStr('CETAG',6),
        NInt('CEL',5),
        Switch('CEDATA',lambda vals:vals.CETAG,
               TREDict,
               default = MetaField('CEDATA',lambda vals:vals.CEL)
               )
        )

class Testtre1(BaseTest):
    typedef=(
        CookedInt(FormatField('len','3s')),
        MetaSizeList(TRE('tres'),lambda vals:vals.len),
        )
    raw="000"
    values=ExampleData(len=0,
                    tres=[])

class Testtre2(BaseTest):
    typedef=(
        CookedInt(FormatField('len','3s')),
        MetaSizeList(TRE('tres'),lambda vals:vals.len),
        )
    raw="657PIAIMB00337050YWHISKBROOM  EYE BALL          ME LOOKING AT PICTURE TAKEN FROM A GOOD SOURCE.                                                                                                                                                                                                                00GBX-137 GREAT                           477YNOPIAPEA00092DURHAM                      JAMES                       A.                          031260USPIAPEA00092DAILEY                      RICHARD                     R.                          062146USPIAPEA00092WEBB                        DAVE                        L.                          061856US"
    values=ExampleData(
        len=657,
        tres=[ExampleData(CETAG='PIAIMB',CEL=337,CEDATA="050YWHISKBROOM  EYE BALL          ME LOOKING AT PICTURE TAKEN FROM A GOOD SOURCE.                                                                                                                                                                                                                00GBX-137 GREAT                           477YNO"),
              ExampleData(CETAG='PIAPEA',CEL=92,
                       CEDATA=ExampleData(ASSOCTRY = 'US',
                                       DOB = '031260',
                                       FIRSTNME = 'JAMES                       ',
                                       LASTNME = 'DURHAM                      ',
                                       MIDNME = 'A.                          ',
                                       )),
              ExampleData(CETAG='PIAPEA',CEL=92,
                       CEDATA=ExampleData(ASSOCTRY = 'US',
                                       DOB = '062146',
                                       FIRSTNME = 'RICHARD                     ',
                                       LASTNME = 'DAILEY                      ',
                                       MIDNME = 'R.                          ',
                                       )),
              ExampleData(CETAG='PIAPEA',CEL=92,
                       CEDATA=ExampleData(ASSOCTRY = 'US',
                                       DOB = '061856',
                                       FIRSTNME = 'DAVE                        ',
                                       LASTNME = 'WEBB                        ',
                                       MIDNME = 'L.                          ',
                                       )),
              ],
        )
    
class Testformatfields(BaseTest):
    typedef=(
        SLInt8('SLInt8'),
        SBInt8('SBInt8'),
        ULInt8('ULInt8'),
        UBInt8('UBInt8'),
        SLInt16('SLInt16'),
        SBInt16('SBInt16'),
        ULInt16('ULInt16'),
        UBInt16('UBInt16'),
        SLInt32('SLInt32'),
        SBInt32('SBInt32'),
        ULInt32('ULInt32'),
        UBInt32('UBInt32'),
        LFloat32('LFloat32'),
        BFloat32('BFloat32'),
        LFloat64('LFloat64'),
        BFloat64('BFloat64'),
        )
    raw=''.join([
        '\xff\xfe\xff\xfe',
        '\xfe\xff\xff\xfe\xfe\xff\xff\xfe',
        '\xfe\xff\xff\xff\xff\xff\xff\xfe\xfe\xff\xff\xff\xff\xff\xff\xfe',
        '\x12\x34\x56\x78\x12\x34\x56\x78',
        '\x12\x34\x56\x78\x12\x34\x56\x78\x12\x34\x56\x78\x12\x34\x56\x78'
        ])
    values=ExampleData(
        SLInt8=-1,
        SBInt8=-2,
        ULInt8=255,
        UBInt8=254,
        SLInt16=-2,
        SBInt16=-2,
        ULInt16=65534,
        UBInt16=65534,
        SLInt32=-2,
        SBInt32=-2,
        ULInt32=256*256*256*256-2,
        UBInt32=256*256*256*256-2,
        LFloat32=1.7378244361449504e+034,
        BFloat32=5.690456613903524e-028,
        LFloat64=4.6919753605233776e+271,
        BFloat64=5.6263470235565435e-221,
        )


    
if __name__ == "__main__":
    import nose
    #os.environ['NOSE_DETAILED_ERRORS']='1'
    nose.runmodule()
