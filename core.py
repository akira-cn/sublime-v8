#coding: utf8

import sublime, sublime_plugin
import sys,os,re

MODULE_PATH = os.getcwd()

def cross_platform():
	platform = sublime.platform()
	settings = sublime.load_settings('cross_platform.sublime-settings')
	platform_supported = settings.get(platform)
	if(not platform_supported):
		raise Exception, '''
			Sorry, the v8 engine for this platform are not built yet. 
			Maybe you need to build v8 follow the guide of lib/PyV8/README.md. 
		'''
	lib_path = platform_supported.get('lib_path')
	if(not lib_path in sys.path):
		sys.path.append(os.path.join(MODULE_PATH, lib_path))

cross_platform();

try:
	import PyV8
except Exception, e:
	raise Exception, '''
		Sorry, the v8 engine are not built correctlly.
		Maybe you need to build v8 follow the guide of lib/PyV8/README.md. 
	''' 

def package_file(filename):
	return os.path.join(MODULE_PATH, filename)	

JSCONSOLE_VIEW_NAME = 'jsconsole_view'
class JsConsoleCommand(sublime_plugin.WindowCommand):
	def __init__(self, window):
		self.console = window.get_output_panel(JSCONSOLE_VIEW_NAME)
		self.console.set_name(JSCONSOLE_VIEW_NAME)
		self.window = window
		version = sublime.load_settings('package-metadata.json').get('version') or 'dev'
		js_print_m(self.console, "#JavaScript Console (build:" + version + ")")
		JsConsoleCommand.core = JSCore(self.console)
		JsConsoleCommand.ctx = PyV8.JSContext(JsConsoleCommand.core)
		JsConsoleCommand.js = PyV8.JSEngine()
	def run(self):
		if(not 'history' in dir(JsConsoleCommand)):
			JsConsoleCommand.history = []
			JsConsoleCommand.history_index = -1
		
		self.window.run_command("show_panel", {"panel": "output."+JSCONSOLE_VIEW_NAME})
		self.console.set_syntax_file(package_file('Console.tmLanguage'))
		self.window.focus_view(self.console)

def js_print_m(view, msg):
	edit = view.begin_edit()
	view.insert(edit, view.size(), (str(msg) + "\n>>> ").decode('utf-8'))
	view.end_edit(edit)

class JsCommandCommand(sublime_plugin.TextCommand):
	def run(self, edit, module, command, args = []):
		try:
			JsConsoleCommand.ctx.enter()
			r = JsConsoleCommand.ctx.eval('load("'+str(module)+'")')
			JsConsoleCommand.ctx.leave()
			apply(getattr(r, command), [self.view, edit]+args)
		except Exception, ex:
			print ex

class JsExecCommand(sublime_plugin.TextCommand):
	def __init__(self, view):
		self.view = view
	def run(self, edit):
		sel = self.view.sel()[0]
		line = self.view.line(sel.begin())
		if(line.end() == int(self.view.size())):
			command = self.view.substr(line)[4:].strip()
			if(command):
				self.view.insert(edit, self.view.size(), '\n')
				JsConsoleCommand.history.append(command) 
				JsConsoleCommand.history_index = len(JsConsoleCommand.history) - 1
				try:
					JsConsoleCommand.ctx.enter()
					r = JsConsoleCommand.ctx.eval(command.encode('utf-8'))
					JsConsoleCommand.ctx.leave()
					js_print_m(self.view, r)
				except Exception, ex:
					js_print_m(self.view, ex)
				finally:
					self.view.run_command("goto_line", {"line": self.view.rowcol(self.view.size())[0]+1})
					self.view.sel().clear()
					self.view.sel().add(self.view.size())

class KeyBackspace(sublime_plugin.TextCommand):
	def run(self, edit):
		sel = self.view.sel()[0]
		begin = sel.begin()
		end = sel.end()
		if(self.view.rowcol(begin)[1] > 4 and self.view.line(begin).contains(self.view.line(self.view.size()))):
			if(begin == end):
				self.view.run_command("left_delete")
			else:
				self.view.replace(edit, sel, '')

class JsHistoryBackward(sublime_plugin.TextCommand):
	def run(self, edit):
		sel = self.view.sel()[0]
		line = self.view.line(sel.begin())
		if(line.contains(self.view.line(self.view.size())) and JsConsoleCommand.history_index >= 0):
			command = JsConsoleCommand.history[JsConsoleCommand.history_index]
			self.view.replace(edit, line, ">>> " + command)
			JsConsoleCommand.history_index = JsConsoleCommand.history_index - 1
			self.view.sel().clear()
			self.view.sel().add(self.view.size())

class JsHistoryForward(sublime_plugin.TextCommand):
	def run(self, edit):
		sel = self.view.sel()[0]
		line = self.view.line(sel.begin())
		if(line.contains(self.view.line(self.view.size())) and JsConsoleCommand.history_index + 2 < len(JsConsoleCommand.history)):
			JsConsoleCommand.history_index = JsConsoleCommand.history_index + 1
			command = JsConsoleCommand.history[JsConsoleCommand.history_index + 1]
			self.view.replace(edit, line, ">>> " + command)
			self.view.sel().clear()
			self.view.sel().add(self.view.size())

class EventListener(sublime_plugin.EventListener):
	def on_selection_modified(self, view):
		if(view.name() != JSCONSOLE_VIEW_NAME):
			return
		
		sel = view.sel()[0]
		if(view.line(sel.begin()).contains(view.line(view.size())) and view.rowcol(sel.begin())[1] > 3):
			view.set_read_only(False)
		else:
			view.set_read_only(True)
	def on_activated(self, view):
		if('core' in dir(JsConsoleCommand) and view.name() != JSCONSOLE_VIEW_NAME):
			window = sublime.active_window()
			JsConsoleCommand.core.setContext(window, view)


class JSCore(PyV8.JSClass):
	def __init__(self, console):
		self.console = JS_Console(console)
		self.sublime = sublime
		self._js_modules = {}
		for (root, dirs, files) in os.walk(sublime.packages_path()):
			#print files
			for _file in files:
				m = re.compile('(.*)\.js$').match(_file)
				if(m):
					self._js_modules.update({m.group(1) : os.path.join(root,_file)})
		window = sublime.active_window()
		view = window.active_view()
		self.setContext(window, view)
	
	def setContext(self, window, view):
		self.window = window
		self.view = view
		docs = view.find_by_selector('text.html')
		if(docs):
			ownerDocumentRegion = docs[0]
			document = view.substr(ownerDocumentRegion)
			from dom import Document
			self.document = Document(document)
		else:
			self.document = None
				
	'''@property
	def window(self):
		return sublime.active_window()
	
	@property
	def view(self):
		return self.window.active_view()
	
	@property
	def document(self):
		view = self.view
		docs = view.find_by_selector('text.html')
		if(docs):
			ownerDocumentRegion = docs[0]
			document = view.substr(ownerDocumentRegion)
			from dom import Document
			return Document(document)
		return None'''
	
	def dir(self, obj):
		return dir(obj)
	def alert(self, msg):
		sublime.error_message(str(msg))
	def require(self, module):
		pass #do nothing but ignore
	def load(self, module, root={'name' : 'root', 'submodules' : [], 'parent' : None}, sort=True):
		modules = self._js_modules
		path = modules.get(module)
		print path
		leaf = {}

		def parents(a):
			ret = []
			while True:
				parent = a.get('parent')
				if(not parent):
					break
				ret.append(parent)
				a = parent
			return ret
		
		def walk(module):
			ret = [module]
			submodules = module.get('submodules')
			for submodule in submodules:
				ret = ret + walk(submodule)
			return ret

		if(path):
			if(not isinstance(path, dict)): #new module
				leaf.update({
						'path' : path,
						'name' : module,
						'parent' : root,
						'submodules' : []
					})
				modules.update({module: leaf})
				root.get('submodules').append(leaf);

				source = file(path, 'r').read()
				requires = re.findall(r"^\s*require\(\'(.*)\'\)", source, re.M)
				if(requires):
					requires = {}.fromkeys([r.strip() for r in ','.join(requires).split(',')]).keys()
				
				for require in requires:
					self.load(require, leaf, False)

			else: #already on the require tree
				leaf = path
				leaf_parents = parents(leaf) #all modules on the require chain
				root_parents = parents(root)

				if(leaf in root_parents):
					raise Exception('confilct module requires')

				if(root == leaf or root in leaf_parents): #leaf alreay on the right branch
					pass  #do nothing
				else:	
					for leaf_parent in leaf_parents:
						if(leaf_parent in root_parents): #found common parents
							submodules = leaf_parent.get('submodules')
							for submodule in submodules:
								if(submodule in leaf_parents): #move the branch to root
									submodules.remove(submodule)
									root.get('submodules').append(submodule)
									break
							break
		
			if(sort):
				ret = walk(root)
				ret.remove(root)
				source = ''
				for r in ret:
					path = r.get('path')
					source = source + file(path).read() + "\n\n"
				source = source + "exports;"
				try:
					s = JsConsoleCommand.js.compile(source)
					return s.run()
				except Exception, ex:
					return ex
		
class JS_Console(PyV8.JSClass):
	def __init__(self, console):
		self._console = console
	def log(self, msg):
		js_print_m(self._console, msg)
