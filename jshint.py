#coding: utf8

import sublime, sublime_plugin
import PyV8
import sys, re, platform
from core import package_file

JSHINT_VIEW_NAME = 'jshint_view'
class JsHintCommand(sublime_plugin.WindowCommand):
	def __init__(self, window):
		self.panel = window.get_output_panel(JSHINT_VIEW_NAME)
		self.panel.set_name(JSHINT_VIEW_NAME)
		self.window = window
		ctx = PyV8.JSContext()
		ctx.enter()
		jshint_file = file(package_file("jshint.js"))
		source = jshint_file.read()
		self.jshint = ctx.eval(source)
		jshint_file.close()		

	def run(self):
		view = self.window.active_view()
		jsscopes = view.find_by_selector('source.js - entity.name.tag.script.html - punctuation.definition.tag.html')

		self.window.run_command("show_panel", {"panel": "output."+JSHINT_VIEW_NAME})
		#self.window.focus_view(self.panel)
		self.panel.set_read_only(False)
		edit = self.panel.begin_edit()
		self.panel.erase(edit, sublime.Region(0, self.panel.size()))
		self.panel.insert(edit, self.panel.size(), view.file_name() + '\n')
		self.panel.insert(edit, self.panel.size(), "parsing...")
		settings = sublime.load_settings('JSHINT.sublime-settings')
		hint_options = dump_settings(settings, 
										["asi", "bitwise", "boss","browser","couch","curly","debug","devel","dojo","eqeqeq","eqnull","es5","esnext","evil","expr","forin","funcscope","globalstrict","immed","iterator","jquery","lastsemic","latedef","laxbreak","loopfunc","mootools","multistr","newcap","noarg","node","noempty","nonew","nonstandard","nomen","onevar","onecase","passfail","plusplus","proto","prototypejs","regexdash","regexp","rhino","undef","scripturl","shadow","smarttabs","strict","sub","supernew","trailing","validthis","white","wsh"])
		self.panel.end_edit(edit)
		self.panel.set_read_only(True)

		def show_errors():
			self.panel.set_read_only(False)
			edit = self.panel.begin_edit()
			self.panel.insert(edit, self.panel.size(), "done" + '\n\n')
			count_warnings = 0

			for scope in jsscopes:
				source = view.substr(scope)
				if(self.jshint(source, hint_options)):
					pass
				else:
					result = self.jshint.data()
					for error in result.errors:
						if(error):
							keys = dir(error)
							evidence = character = line = ''
							
							details = []
							if('line' in keys):
								details.append(' line : ' + str(error.line + view.rowcol(scope.begin())[0]))
							if('character' in keys):
								details.append(' character : ' + str(error.character))
							if('evidence' in keys):
								details.append(' near : ' + error.evidence.decode("UTF-8"));
							if(settings.get("warnings") or 'id' in keys and not re.compile("^warning ").match(error.id)):
								self.panel.insert(edit, self.panel.size(), error.id + ' : ' + error.reason + ' ,'.join(details) + ' \n')
							if(re.compile("^warning ").match(error.id)):
								count_warnings = count_warnings + 1

			line_errors = self.panel.find_all('^error.*')
			self.panel.add_regions('jshint_errors', line_errors, "invalid")

			self.panel.insert(edit, self.panel.size(), '\n' + str(len(line_errors)) + ' errors, ' + str(count_warnings) + ' warnings\n\n')

			if(not settings.get("warnings")):
				self.panel.insert(edit, self.panel.size(), '(You can set `warnings` to true via `JSHINT.sublime-settings` to show warning details)\n\n')

			self.panel.end_edit(edit)
			self.panel.set_read_only(True)
			self.window.focus_view(self.panel)
		
		sublime.set_timeout(show_errors, 1)


def dump_settings(settings, keys):
	ret = {}
	for key in keys:
		ret.update({key : settings.get(key)})
	return ret;

def on_syntax_error(view, context, scope):
	source = view.substr(scope)
	try:
		if(platform.system() == 'Windows'):
			try:
				source = source.encode('utf-8')
			except:
				source = source.encode('gbk')
		context.eval(source)
	except Exception,ex:
		if('name' in dir(ex) and ex.name == 'SyntaxError'):
			err_region = sublime.Region(scope.begin() + ex.startPos, scope.begin() + ex.endPos)
			view.add_regions('v8_errors', [err_region], "invalid")	
			if('message' in dir(ex)):
				sublime.status_message(ex.message)

def get_file_view(window, file_name):
    for file_view in window.views():
    	if(file_view.file_name() == file_name):
    		return file_view

class EventListener(sublime_plugin.EventListener):
	def __init__(self):
		ctx = PyV8.JSContext()
		ctx.enter()
		self.ctx = ctx
		self.file_view = None
	
	def on_deactivated(self, view):
	    if self.file_view:
	    	self.file_view.erase_regions('jshint_errors')
	    			    	    		
	def on_selection_modified(self, view):
	    if view.name() != JSHINT_VIEW_NAME:
	      return
	  
	    window = sublime.active_window()
	    file_name = view.substr(view.line(0))

	    file_view = get_file_view(window, file_name)
	    self.file_view = file_view
	  	  
	    if(file_view):
		    region = view.line(view.sel()[0])
		    text = view.substr(region);

		    m = re.compile('.*line : (\d+) , character : (\d+)').match(text)
		    if(m):
		    	view.add_regions('jshint_focus', [region], "string")
		    	(row, col) = m.groups()
		    	point = file_view.text_point(int(row) - 1, 0)
		    	line = file_view.line(point)
		    	file_view.add_regions('jshint_errors', [line], "invalid")	
    			window.focus_view(file_view)
    			file_view.run_command("goto_line", {"line": row})
	      		
	def on_modified(self, view):
		sublime.set_timeout((lambda view,context : (lambda: realtimeHint(view, context)))(view, self.ctx), 1)
		

def realtimeHint(view, ctx):
	jsscopes = view.find_by_selector('source.js - entity.name.tag.script.html - punctuation.definition.tag.html')
	if(not jsscopes):
		return

	view.erase_regions('v8_errors')
	sublime.status_message('')

	for scope in jsscopes:
		on_syntax_error(view, ctx, scope)
		
