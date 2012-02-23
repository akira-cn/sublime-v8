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
		sys.path.append(MODULE_PATH)

cross_platform();

try:
	import PyV8
except Exception, e:
	raise Exception, '''
		Sorry, the v8 engine are not built correctlly.
		Maybe you need to build v8 follow the guide of lib/PyV8/README.md. 
	''' 

from jscontext.commonjs import CommonJS
CommonJS.append(MODULE_PATH)

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
			r = JsConsoleCommand.core.execute('require("'+str(module)+'")')
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
					r = JsConsoleCommand.core.execute(command.encode('utf-8'))
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


class JSCore(CommonJS):
	def __init__(self, console):
		self.console = console
		def log(msg):
			print msg
			js_print_m(console, msg)
		self.console.log = log
		CommonJS.__init__(self)
	@property 
	def sublime(self):
		return sublime
	@property 
	def window(self):
		return sublime.active_window()
	@property 
	def view(self):
		return sublime.active_window().active_view()
	def alert(self, msg):
		js_print_m(self.console, msg)