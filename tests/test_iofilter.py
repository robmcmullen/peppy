import os,sys,re

from peppy.iofilter import URLInfo,GetIOFilter
from peppy.stcinterface import NullSTC

from nose.tools import *

class TestURLInfo:
    def testHttp(self):
        url=URLInfo("http://www.flipturn.org")
        eq_(url.protocol,'http')
        eq_(url.netloc,'www.flipturn.org')
        url=URLInfo("http://www.flipturn.org/peppy/")
        eq_(url.protocol,'http')
        eq_(url.netloc,'www.flipturn.org')
        eq_(url.path,'/peppy/')
        url=URLInfo("http://www.flipturn.org/peppy/index.html")
        eq_(url.protocol,'http')
        eq_(url.netloc,'www.flipturn.org')
        eq_(url.path,'/peppy/index.html')
        url=URLInfo("http://www.flipturn.org/peppy/index.html?extra_stuff")
        eq_(url.protocol,'http')
        eq_(url.netloc,'www.flipturn.org')
        eq_(url.path,'/peppy/index.html')
        eq_(url.query_string,'extra_stuff')
        
    def testFile(self):
        url=URLInfo("file:///etc/profile")
        eq_(url.protocol,'file')
        eq_(url.path,'/etc/profile')
        url=URLInfo("file:README.txt")
        eq_(url.protocol,'file')
        eq_(url.path,'README.txt')
        url=URLInfo("file://README.txt")
        eq_(url.protocol,'file')
        eq_(url.netloc+url.path,'README.txt')
        url=URLInfo("README.txt")
        eq_(url.protocol,'file')
        eq_(url.path,'README.txt')
        
    def testWindowsFile(self):
        url=URLInfo("c:/path/to/some/file.txt",usewin=True)
        eq_(url.protocol,'file')
        eq_(url.netloc+url.path,'c:/path/to/some/file.txt')
        url=URLInfo("file://c:/path/to/some/file.txt",usewin=True)
        eq_(url.protocol,'file')
        eq_(url.netloc+url.path,'c:/path/to/some/file.txt')
        url=URLInfo("file:c:/path/to/some/file.txt",usewin=True)
        eq_(url.protocol,'file')
        eq_(url.netloc+url.path,'c:/path/to/some/file.txt')
        
    def testAbout(self):
        url=URLInfo("about:authors")
        eq_(url.protocol,"about")
        eq_(url.path,"authors")

class TestGetIOFilter:
    def testFile(self):
        filter=GetIOFilter("file:LICENSE")
        cwd = os.getcwd()
        eq_(filter.url, "file:%s" % os.path.join(cwd, 'LICENSE'))
        eq_(filter.urlinfo.protocol,'file')
        eq_(filter.protocol.getFilename(filter.urlinfo),'LICENSE')
        stc=NullSTC()
        filter.read(stc)
        text=stc.GetText()
        eq_(text[0:32],'\t\t    GNU GENERAL PUBLIC LICENSE')
        
    def testFileRelative(self):
        filter=GetIOFilter("file://LICENSE")
        cwd = os.getcwd()
        eq_(filter.url, "file:%s" % os.path.join(cwd, 'LICENSE'))
        eq_(filter.urlinfo.protocol,'file')
        eq_(filter.protocol.getFilename(filter.urlinfo),'LICENSE')
        stc=NullSTC()
        filter.read(stc)
        text=stc.GetText()
        eq_(text[0:32],'\t\t    GNU GENERAL PUBLIC LICENSE')
        
    def testFileDefault(self):
        filter=GetIOFilter("LICENSE")
        cwd = os.getcwd()
        eq_(filter.url, "file:%s" % os.path.join(cwd, 'LICENSE'))
        eq_(filter.urlinfo.protocol,'file')
        eq_(filter.protocol.getFilename(filter.urlinfo),'LICENSE')
        stc=NullSTC()
        filter.read(stc)
        text=stc.GetText()
        eq_(text[0:32],'\t\t    GNU GENERAL PUBLIC LICENSE')
        
    def testChatbots(self):
        import peppy.plugins.chatbots
        filter=GetIOFilter("shell:eliza")
        eq_(filter.url, "shell:eliza")
        eq_(filter.urlinfo.protocol,'shell')
        eq_(filter.urlinfo.path,'eliza')

    def testWindowsFile(self):
        filter=GetIOFilter("file://c:/some/path.txt",usewin=True)
        #eq_(filter.url, "file:/c:/some/path.txt")
        eq_(filter.urlinfo.protocol,'file')
        eq_(filter.protocol.getFilename(filter.urlinfo),'c:/some/path.txt')
        filter=GetIOFilter("c:/some/path.txt",usewin=True)
        eq_(filter.urlinfo.protocol,'file')
        eq_(filter.protocol.getFilename(filter.urlinfo),'c:/some/path.txt')
        
