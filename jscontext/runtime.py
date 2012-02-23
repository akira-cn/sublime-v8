#JavaScript HTML Context for PyV8

from PyV8 import JSClass
from logger import logger
import re, threading, hashlib

import urllib,urllib2

from w3c import parseString, Document, HTMLElement
from commonjs import CommonJS

import browser

from StringIO import StringIO
import gzip

class JSR(CommonJS, browser.HtmlWindow):
	def __init__(self, url_or_dom, charset=None, headers={}, body={}, timeout=2):
		urllib2.socket.setdefaulttimeout(timeout)
		jsonp = False

		if(isinstance(url_or_dom, Document)):
			url = "localhost:document"
			dom = url_or_dom

		elif(url_or_dom.startswith('<')):
			url = "localhost:string"
			dom = parseString(url_or_dom)

		else: #url
			url = url_or_dom
			if(not re.match(r'\w+\:\/\/', url)):
				url = "http://" + url

			request = urllib2.Request(url, urllib.urlencode(body), headers=headers) 
			response = urllib2.urlopen(url)
			
			contentType = response.headers.get('Content-Type')

			if(contentType):
				#print contentType
				t = re.search(r'x-javascript|json', contentType)
				if(t):
					jsonp = True
				m = re.match(r'^.*;\s*charset=(.*)$', contentType)
				if(m):
					charset = m.group(1) 
				#print charset

			if(not charset):
				charset = 'utf-8' #default charset
				# guess charset from httpheader

			html = response.read()
			encoding = response.headers.get('Content-Encoding')

			if(encoding and encoding == 'gzip'):
			    buf = StringIO(html)
			    f = gzip.GzipFile(fileobj=buf)
			    html = f.read()	
			    			
			self.__html__ = html
			html = unicode(html, encoding=charset, errors='ignore')
			dom = parseString(html)	

		navigator = browser.matchNavigator(headers.get('User-Agent') or '')
			
		browser.HtmlWindow.__init__(self, url, dom, navigator)
		CommonJS.__init__(self)
		
		self.console = JSConsole(self._js_logger)
		
		for module in "base, array.h, function.h, helper.h, object.h, string.h, date.h, custevent, selector, dom_retouch".split(","):
			self.execute(self.require, [module.strip()])
		
		if(jsonp):
			code = "window.data=" + html.encode('utf-8')
			self.execute(code)
			#print code

		self._js_logger.info('JavaScript runtime ready.')

	_js_timer_map = {}

	def _js_execTimer(self, id, callback, delay, repeat = False):
		code = '(function f(){ _js_timers[' + str(id) + '][1].code();'
		if(repeat):
			code = code + '_js_execTimer(' + str(id) + ', f, ' + str(delay) + ', true);'
		code = code + '})();'

		#thread locking
		self._js_timer_map[id] = threading.Timer(delay / 1000.0, lambda: self.execute(code))
		self._js_timer_map[id].start()

	def setTimeout(self, callback, delay):
		timerId = super(JSR, self).setTimeout(callback, delay)
		self._js_execTimer(timerId, callback, delay, False)
		return timerId

	def clearTimeout(self, timerId):
		if(timerId in self._js_timer_map):
			self._js_timer_map[timerId].cancel()
			self._js_timer_map[timerId] = None
			super(JSR, self).clearTimeout(timerId)

	def setInterval(self, callback, delay):
		timerId = super(JSR, self).setInterval(callback, delay)
		self._js_execTimer(timerId, callback, delay, True)
		return timerId		
	
	def clearInterval(self, timerId):
		if(timerId in self._js_timer_map):
			self._js_timer_map[timerId].cancel()
			self._js_timer_map[timerId] = None
			super(JSR, self).clearTimeout(timerId)

	def md5(self, str):
		return hashlib.md5(str).hexdigest()

class JSConsole(JSClass):
	def __init__(self, logger):
		self._js_logger = logger
	def log(self, msg):
		self._js_logger.info(str(msg).decode('utf-8'))