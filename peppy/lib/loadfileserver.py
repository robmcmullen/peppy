"""
Server and client code for passing a string to a running application.
Adapted from the SimpleServer code at
http://www.technovelty.org/code/python/socketserver.html
"""

import os,os.path,sys
import wx

import SocketServer, time, select, sys, socket
from threading import Thread


# The LoadFileRequestHandler class uses this to parse command lines.
class LoadFileCommandProcessor:
    def __init__(self,proxy):
        self.proxy=proxy

    def process(self, line, request):
        """Process a command"""
        args = line.split(' ')
        command = args[0].lower()
        args = args[1:]

        print "Request for file: %s" % command
        wx.CallAfter(self.proxy.loadFile,command)
        return True

# LoadFileServer extends the TCPServer, using the threading mix in
# to create a new thread for every request.
class LoadFileServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):

    # This means the main server will not do the equivalent of a
    # pthread_join() on the new threads.  With this set, Ctrl-C will
    # kill the server reliably.
    daemon_threads = True

    # By setting this we allow the server to re-bind to the address by
    # setting SO_REUSEADDR, meaning you don't have to wait for
    # timeouts when you kill the server and the sockets don't get
    # closed down correctly.
    allow_reuse_address = True

    def __init__(self, server_address, RequestHandlerClass, processor, message=''):
        SocketServer.TCPServer.__init__(self, server_address, RequestHandlerClass)
        self.processor = processor
        self.message = message

# The RequestHandler handles an incoming request.  We have extended in
# the LoadFileServer class to have a 'processor' argument which we can
# access via the passed in server argument, but we could have stuffed
# all the processing in here too.
class LoadFileRequestHandler(SocketServer.BaseRequestHandler):

    def __init__(self, request, client_address, server):
        SocketServer.BaseRequestHandler.__init__(self, request, client_address, server)

    def handle(self):
        # If you send data, it is expected to be read or it won't get
        # processed
        # self.request.send(self.server.message)

        ready_to_read, ready_to_write, in_error = select.select([self.request], [], [], None)

        text = ''
        done = False
        while not done:

            if len(ready_to_read) == 1 and ready_to_read[0] == self.request:
                data = self.request.recv(1024)

                if not data:
                    break
                elif len(data) > 0:
                    text += str(data)

                    while text.find("\n") != -1:
                        line, text = text.split("\n", 1)
                        line = line.rstrip()

                        command = self.server.processor.process(line,
                                                                self.request)
                        # return code ignored.  Serve forever!

        self.request.close()

    def finish(self):
       """Nothing"""

        
class ThreadedLoadFileServer(Thread):
    def __init__(self,proxy,host='127.0.0.1',port=55555):
        self.proxy=proxy
        self.host=host
        self.port=port
        Thread.__init__(self)

        # Make this a daemon thread so that the prog shuts down this
        # thread when the main thread exits.
        self.setDaemon(True)

    def run(self):
        # Start up a server on localhost, port 55555; each time a new
        # request comes in it will be handled by a
        # LoadFileRequestHandler class; we pass in a
        # LoadFileCommandProcessor class that will be able to be
        # accessed in request handlers via server.processor; and a
        # hello message (that currently isn't used).
        server = LoadFileServer((self.host,self.port),
                                LoadFileRequestHandler,
                                LoadFileCommandProcessor(self.proxy),
                                'pyhsi load file server.\n\r')
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            return

class LoadFileProxy(object):
    def __init__(self,host='127.0.0.1',port=55555):
        self.host=host
        self.port=port
        self.socket=None
        self.threadedServer=None
        
    def find(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((self.host, self.port))
            self.socket=s
            return True
        except socket.error:
            self.socket=None
        return False

    def start(self,proxy):
        self.threadedServer=ThreadedLoadFileServer(proxy)
        self.threadedServer.start()

    def stop(self):
        pass
        
    def send(self,name):
        try:
            # do not change files of form [prot]://[path]
            if name.find('://') == -1:
                name = os.path.abspath(name)
            name+=os.linesep
            bytes=self.socket.send(name)
            print "sent: %s (%d bytes of %d)" % (name,bytes,len(name))
            return True
        except socket.error:
            pass
        return False

    def close(self):
        self.socket.close()



class TestFrame(wx.Frame):
    def __init__(self,name="Socket Listener Test"):
        wx.Frame.__init__(self,None, -1, name)

    def loadFile(self,name):
        frame=TestFrame(name)
        frame.Show(1)
        wx.StaticText(frame, -1, name, (45, 15))


if __name__ == '__main__':
    from optparse import OptionParser

    usage="usage: %prog [-v] file [files...]"
    parser=OptionParser(usage=usage)
    parser.add_option("-v", action="store_true", dest="verbose")
    (options, args) = parser.parse_args()
    print options
    
    server=LoadFileProxy()
    if server.find():
        sent=False
        for name in args:
            if server.send(name):
                sent=True
            else:
                print "Not sent: %s" % name
                sent=False
                break
        # If the server has sent anything, need to read it here or the
        # close will cause:
        #
        # error: (10053, 'Software caused connection abort') and
        # testing it under windows showed that the send was never
        # completed.
        server.close()
    else:
        app = wx.PySimpleApp()
        # frame = wx.Frame(None, -1, "Socket Listener Test")
    
        frame = TestFrame()
        frame.Show(1)
        server.start(frame)
        app.MainLoop()
