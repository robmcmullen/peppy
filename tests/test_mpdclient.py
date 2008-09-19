import os,sys,re

from peppy.lib.mpdclient2 import *

from nose.tools import *

from utils import *

class mock_talker(socket_talker):
    def __init__(self, cmd, text):
        self.lines = text.splitlines()
        self.lines.reverse()
        self.done = True
        self.current_line = ''

    def putline(self, line):
        self.done = False

    def get_line(self):
        if not self.current_line and len(self.lines) > 0:
            self.current_line = self.lines.pop()
        if not self.current_line:
            raise EOFError
        if self.current_line == "OK" or self.current_line.startswith("ACK"):
            self.done = True
        return self.current_line

class mock_connection(mpd_connection):
    def __init__(self, cmd, text):
        self.needs_reopen = False
        self.talker = mock_talker(cmd, text)
        self.send = command_sender(self.talker)
        self.fetch = response_fetcher(self.talker)
        self.do = sender_n_fetcher(self.send, self.fetch)        


class Test_lsinfo:
    def setup(self):
        self.mpd = mock_connection("lsinfo Test", """\
directory: Test/Download
file: Test/Queen-_Mr._Farenheit.mp3
Time: 212
Artist: Queen
Genre: Other
file: Test/Queen_-_Don_t_Stop_Me_Now.mp3
Time: 210
Artist: Queen
Title: Dont Stop Me Now
Album: Greatest Hits 1
Date: 1978
Genre: Pop
OK
""")
        
    def test_1(self):
        items = self.mpd.lsinfo('Test')
        eq_(3, len(items))
        eq_('directory', items[0]['type'])
        eq_('file', items[1]['type'])
        eq_('file', items[2]['type'])
        print items
        
class Test_update:
    def setup(self):
        self.mpd = mock_connection("update", """\
updating_db: 3
OK
""")

    def test_1(self):
        items = self.mpd.update()
        eq_(None, items)
        
