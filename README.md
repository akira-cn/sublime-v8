# sublime-v8
	
	added [Google v8 engine](http://code.google.com/p/v8/) to sublime text 2
	support windows : [sublime-v8 for win32](https://github.com/akira-cn/sublime-v8-win32)
	support mac os : [sublime-v8 for osx](https://github.com/akira-cn/sublime-v8-osx)

## Realtime syntax checking with [PyV8](https://github.com/okoye/PyV8)

	check & mark syntax errors

## Show [jshint](http://www.jshint.com/) result by press ctrl+alt+h key
	
	jshint result can be shown (including errors and warnings)
	with jshint settings in JSHINT.sublime-settings 

## A JavaScript console supported

	a js console shown by press ctrl+alt+j key
	use it like the python console

## Writing plugin in JavaScript:
	
     //example
     require('base');

     exports = TextCommand("HelloWorld", function(view, edit){
         view.insert(edit, 0, "HelloWorld");
         console.log(view.file_name());
     });