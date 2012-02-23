#!/usr/bin/env python
#
# Purely event-based I/O for V8 javascript w/ PyV8.
# http://tinyclouds.org/node/
#
import sys, os.path, json

import logging

import threading
import socket, SocketServer, BaseHTTPServer
from urlparse import urlparse

import PyV8

__author__ = "flier.lu@gmail.com"
__version__ = "%%prog 0.1 (Google v8 engine v%s)" % PyV8.JSEngine.version

class File(PyV8.JSClass):
    logger = logging.getLogger('file')
    
    def __init__(self, file=None):
        self.file = file
        
    def open(self, path, mode):        
        self.file = open(path, mode)
        
    def read(self, length, position=None):
        if position:
            self.file.seek(position)
            
        return self.file.read(length)
        
    def write(self, data, position=None):
        if position:
            self.file.seek(position)
            
        return self.file.write(data)
        
    def close(self):
        self.file.close()

class FileSystem(PyV8.JSClass):
    logger = logging.getLogger('filesystem')
    
    def File(self, options={}):
        return File()
    
class ServerRequest(PyV8.JSClass, BaseHTTPServer.BaseHTTPRequestHandler):
    logger = logging.getLogger('web.request')
    
    def __init__(self, request, client_address, server):
        BaseHTTPServer.BaseHTTPRequestHandler.__init__(self, request, client_address, server)
        
    @property
    def uri(self):
        if hasattr(self, '__uri'):
            return self.__uri
        
        o = urlparse(self.path)
        
        params = dict([tuple(v.split('=')) for v in o.query.split('&')]) if o.query else {}
        
        self.__uri = {
            'host' : o.hostname,
            'port' : o.port,
            'user' : o.username,
            'password' : o.password,            
            'path' : o.path,
            'file' : os.path.basename(o.path),
            'directory' : os.path.dirname(o.path),
            'params' : params,
        }

        return self.__uri
    
    @property
    def method(self):
        return self.command
        
    def handle_request(self):
        self.logger.info("handle request from %s:%d" % self.client_address)
        
        self.finished = threading.Event()
        
        try:
            self.server.server.listener(self, ServerResponse(self.server.server, self))
        except PyV8.JSError, e:
            self.logger.warn("fail to execute callback script, %s", str(e))
        except Exception, e:
            self.logger.warn("unknown error occured, %s", str(e))
            
        self.finished.wait()
            
    do_GET = do_POST = do_HEAD = handle_request    
        
class ServerResponse(PyV8.JSClass):
    logger = logging.getLogger('web.response')
    
    def __init__(self, server, handler):
        self.server = server
        self.handler = handler
        
    def sendHeader(self, statusCode, headers):
        self.handler.send_response(statusCode)
        
        for i in range(len(headers)):
            self.handler.send_header(headers[i][0], headers[i][1])
            
        self.handler.end_headers()
    
    def sendBody(self, chunk, encoding='ascii'):        
        self.handler.wfile.write(chunk)
    
    def finish(self):
        self.handler.wfile.close()
        self.handler.finished.set()
    
class WebServer(PyV8.JSClass):
    logger = logging.getLogger('web.server')
    
    __alive = []
    __terminated = False
    
    def __init__(self, listener, options):
        self.listener = listener
        self.options = options
        
    def listen(self, port, hostname=None):        
        self.server = SocketServer.ThreadingTCPServer((hostname or 'localhost', port), ServerRequest)
        self.server.server = self
        
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.setName('WebServer')
        self.thread.setDaemon(True)        
        self.thread.start()
        
        WebServer.__alive.append(self.thread)
        
        self.logger.info("start web server at %s:%d" % self.server.server_address)
    
    def close(self):
        self.server.shutdown()
        
        self.logger.info("shutdown web server at %s:%d" % self.server.server_address)
        
    @staticmethod
    def run():
        while not WebServer.__terminated:
            if WebServer.__alive:
                for thread in WebServer.__alive:
                    if thread.isAlive():
                        thread.join(0.5)
                        
                    if WebServer.__terminated:
                        break
                    
                    if not thread.isAlive():
                        WebServer.__alive.remove(thread)
                        break
                
    @staticmethod
    def stop():
        WebServer.__terminated = True

class Http(PyV8.JSClass):
    logger = logging.getLogger('http')
    
    def createServer(self, listener, options=None):
        return WebServer(listener, options)
    
class Tcp(PyV8.JSClass):
    logger = logging.getLogger('tcp')

class Dns(PyV8.JSClass):
    logger = logging.getLogger('dns')

class Node(PyV8.JSClass):
    logger = logging.getLogger('node')
    
    def __init__(self):
        self.stdout = File(sys.stdout)
        self.stderr = File(sys.stderr)
        self.stdin = File(sys.stdin)
        self.ARGV = sys.argv
        
        self.fs = FileSystem()
        self.http = Http()
        self.tcp = Tcp()
        self.dns = Dns()
        
    def debug(self, string):
        self.stdout.write(string)
        
    def exit(self, code):
        sys.exit(code)
        
class Timer(object):
    logger = logging.getLogger('timer')
    
    __timeout_id = 0
    __timeout_timers = {}
    
    __interval_id = 0
    __interval_timers = {}    
        
    def setTimeout(self, callback, delay):
        timer = threading.Timer(delay / 1000.0, callback)        
        
        self.__timeout_id += 1
        self.__timeout_timers[self.__timeout_id] = timer
        
        timer.start()
        
        self.logger.info("add #%d timer will call %s after %sms", self.__timeout_id, callback, delay)
    
    def clearTimeout(self, timeoutId):
        if self.__timeout_timers.has_key(timeoutId):
            self.__timeout_timers[timeoutId].cancel()
            
            del self.__timeout_timers[timeoutId]
            
            self.logger.info("cancel #%d timer", timeoutId)
        else:
            self.logger.warn("#%d timer was not found", timeoutId)
    
    def setInterval(self, callback, delay):
        def handler():
            callback()
            
            self.setInterval(self, callback, delay)
            
        timer = threading.Timer(delay / 1000.0, handler)
        
        self.__interval_id += 1
        self.__interval_timers[self.__interval_id] = timer
        
        timer.start()
        
        self.logger.info("add #%d interval timer will call %s every %sms", self.__interval_id, callback, delay)
    
    def clearInterval(intervalId):
        if self.__interval_timers.has_key(intervalId):
            self.__interval_timers[intervalId].cancel()
            
            del self.__interval_timers[intervalId]
            
            self.logger.info("cancel #%d interval timer", intervalId)
        else:
            self.logger.warn("#%d interval timer was not found", intervalId)
        
class Env(PyV8.JSClass, Timer):
    logger = logging.getLogger('env')
    
    def __init__(self):
        self.node = Node()
        
    def puts(self, str):
        self.node.stdout.write(str + '\n')    
        
    def p(self, object):
        self.stdout.write(json.dumps(object))        

class Loader(object):
    logger = logging.getLogger('loader')
    
    def __init__(self):
        self.scripts = []        
        
    def addScript(self, script, filename):
        self.scripts.append((script, filename))
    
    def run(self):
        env = Env()
        
        with PyV8.JSContext(env) as ctxt:
            for filename in self.args:
                try:
                    with open(filename, 'r') as f:
                        ctxt.locals.__filename = filename
                        ctxt.eval(f.read())
                except IOError, e:
                    self.logger.warn("fail to read script from file '%s', %s", filename, str(e))
                except PyV8.JSError, e:
                    self.logger.warn("fail to execute script from file '%s', %s", filename, str(e))
                    
            try:
                WebServer.run()
            except KeyboardInterrupt:
                WebServer.stop()
                    
    def parseCmdline(self):
        from optparse import OptionParser
        
        parser = OptionParser(usage="Usage: %prog [options] <scripts>", version=__version__)
        
        parser.add_option("-q", "--quiet", action="store_const",
                          const=logging.FATAL, dest="logLevel", default=logging.WARN)
        parser.add_option("-v", "--verbose", action="store_const",
                          const=logging.INFO, dest="logLevel")
        parser.add_option("-d", "--debug", action="store_const",
                          const=logging.DEBUG, dest="logLevel")
        parser.add_option("--log-format", dest="logFormat",
                          default="%(asctime)s %(levelname)s %(name)s %(message)s")
        parser.add_option("--log-file", dest="logFile")
        
        self.opts, self.args = parser.parse_args()
        
        logging.basicConfig(level=self.opts.logLevel,
                            format=self.opts.logFormat,
                            filename=self.opts.logFile or 'node.log')        
        
        if len(self.args) == 0:
            parser.error("missing script files")
        
        return True

if __name__ == '__main__':
    loader = Loader()
    
    if loader.parseCmdline():    
        loader.run()