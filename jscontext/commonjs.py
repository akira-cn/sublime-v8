import os, re, platform
from PyV8 import JSContext, JSError

from logger import logger

class CommonJS():
	_js_path = [os.path.dirname(__file__), os.path.join(os.path.dirname(__file__),'core')]
	_js_logger = logger().instance()

	def __init__(self):
		self._js_threadlock = False
		self._js_ctx = JSContext(self)
		self._js_modules = {}
		self._loaded_modules = {}

		for jsroot in CommonJS._js_path:
			for (root, dirs, files) in os.walk(jsroot):
				#print files
				for _file in files:
					m = re.compile('(.*)\.js$').match(_file)
					relpath = os.path.relpath(root, jsroot)
					namespace = re.sub(r'^\.', '', relpath)
					namespace = re.sub(r'^\\', '/', namespace)
					if(namespace):
						namespace = namespace + '/'
					if(m):
						self._js_modules.update({namespace + m.group(1) : os.path.join(root,_file)})

		self.execute("var exports;");				
	
	@staticmethod
	def append(path):
		if(path not in CommonJS._js_path):
			CommonJS._js_path.append(path)

	def require(self, module):
		if(not self._js_modules.has_key(module)):
			raise Exception, "unknown module `" + module + "`"
		path = self._js_modules[module]

		if(not self._loaded_modules.has_key(path)):
			self._js_logger.info("loading module <%s>...", module)
			code = file(path).read()
			try:
				code = code.decode('utf-8')
				if(platform.system() == 'Windows'):
					code = code.encode('utf-8')
				self._js_ctx.eval(code)
			except JSError, ex:
				self._js_logger.error(ex)
				self._js_logger.debug(ex.stackTrace)
				raise Exception, ex
			self._loaded_modules[path] = self._js_ctx.locals.exports
			return self._loaded_modules[path]
		else:
			return self._loaded_modules[path]

	def execute(self, code, args = []):
		self._js_ctx.enter()
		
		# use lock while jscode executing to make mutil-thread work
		while self._js_threadlock: 
			pass
		self._js_threadlock = True
		try:
			if(isinstance(code, basestring)):
				code = code.decode('utf-8')
				if(platform.system() == 'Windows'):
					code = code.encode('utf-8')
				r = self._js_ctx.eval(code)
			else:
				r = apply(code, args)
			return r
		except JSError, ex:
			self._js_logger.error(ex)
			self._js_logger.debug(ex.stackTrace)
			raise Exception, ex
		finally:
			self._js_threadlock = False
			self._js_ctx.leave()