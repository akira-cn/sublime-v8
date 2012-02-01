/**
 * Demo
 */
require('base');

exports = TextCommand("HelloWorld", function(view, edit){
	view.insert(edit, 0, "HelloWorld");
	console.log(view.file_name());
});