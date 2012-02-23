(function(){

	var selector = require('selector');
	if(document){
		document.__proto__.querySelectorAll = function(s){
			return selector.query(this, s);				
		};
		document.__proto__.querySelector = function(s){
			return selector.query(this, s)[0];
		};
		if(document.documentElement){
			document.documentElement.__proto__.querySelectorAll = function(s){
				return selector.query(this, s);
			}
			document.documentElement.__proto__.querySelector = function(s){
				return selector.query(this, s)[0];
			}
		}
	}

})();