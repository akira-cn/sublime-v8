/*
	Copyright (c) Baidu Youa Wed QWrap
	version: $version$ $release$ released
	author: 月影、JK
*/

/**
 * @class FunctionH 核心对象Function的扩展
 * @singleton 
 * @namespace QW
 * @helper
 */
(function() {

	var FunctionH = {
		/**
		 * 函数包装器 methodize，对函数进行methodize化，使其的第一个参数为this，或this[attr]。
		 * @method methodize
		 * @static
		 * @param {function} func要方法化的函数
		 * @param {string} attr (Optional) 属性
		 * @return {function} 已方法化的函数
		 */
		methodize: function(func, attr) {
			if (attr) {
				return function() {
					return func.apply(null, [this[attr]].concat([].slice.call(arguments)));
				};
			}
			return function() {
				return func.apply(null, [this].concat([].slice.call(arguments)));
			};
		},
		/** 对函数进行集化，使其第一个参数可以是数组
		 * @method mul
		 * @static
		 * @param {function} func
		 * @param {bite} opt 操作配置项，缺省 0 表示默认，
		 1 表示getFirst  将只操作第一个元素，
		 2 表示joinLists 如果第一个参数是数组，将操作的结果扁平化返回
		 3 表示getFirstDefined 将操作到返回一个非undefined的结果为止
		 hint: getFirstDefined 配合wrap的 keepReturnValue 可以实现gsetter
		       还可以考虑通过增加getAllValued功能来实现gsetter_all，暂时没有需求，所以不予实现
		 * @return {Object} 已集化的函数
		 */
		mul: function(func, opt) {
			var getFirst = opt == 1,
				joinLists = opt == 2,
				getFirstDefined = opt == 3;

			if (getFirst) {
				return function() {
					var list = arguments[0];
					if (!(list instanceof Array)) {
						return func.apply(this, arguments);
					}
					if (list.length) {
						var args = [].slice.call(arguments);
						args[0] = list[0];
						return func.apply(this, args);
					}
				};
			}
			
			return function() {
				var list = arguments[0];
				if (list instanceof Array) {
					var moreArgs = [].slice.call(arguments),
						ret = [],
						i = 0,
						len = list.length,
						r;
					for (; i < len; i++) {
						moreArgs[0] = list[i];
						r = func.apply(this, moreArgs);
						if (joinLists) {
							if (r != null) {
								ret = ret.concat(r);
							}
						} 
						else if(getFirstDefined) {
							if (r !== undefined){
								return r;
							}	
						}
						else {
							ret.push(r);
						}
					}
					return getFirstDefined?undefined:ret;
				} else {
					return func.apply(this, arguments);
				}
			};
		},
		/**
		 * 函数包装变换
		 * @method rwrap
		 * @static
		 * @param {func} 
		 * @param {Wrap} wrapper 包装对象
		 * @param {number|string} opt 包装选项 0~n 表示包装arguments，this|context 表示包装this，缺省表示包装ret
		 * @param {boolean} keepReturnValue 可选的，true表示尊重returnValue，只有returnValue === undefined时才包装
		 * @return {Function}
		 */
		rwrap: function(func, wrapper, opt, keepReturnValue) {
			if(opt == null) opt = 0;
			return function() {
				var ret = func.apply(this, arguments);
				if(keepReturnValue && ret !== undefined) return ret;
				if (opt >= 0) {
					ret = arguments[opt];
				} else if(opt == "this" || opt == "context"){
					ret = this;
				} 
				return wrapper && !(ret instanceof wrapper) ? new wrapper(ret) : ret;
			};
		},
		/**
		 * 针对Function做拦截器
		 * @method hook
		 * @static
		 * @param {Function} 要拦截的函数
		 * @param {String} where，before和after
		 * @param {Function} 拦截器： function(args|returnValue , callee , where)
		 */
		hook: function(func, where, handler){
			//如果是before拦截器
			if(where == "before"){
				return function(){
					var args = [].slice.call(arguments);
					if(false !== handler.call(this, args, func, where)){
						//如果return false，阻止后续的执行，否则执行
						return func.apply(this, args);
					}
				}
			}else if(where == "after"){
				return function(){
					var args = [].slice.call(arguments);
					var ret = func.apply(this, args);
					//返回after的返回值
					return handler.call(this, ret, func, where);
				}
			}else{
				throw new Error("unknow hooker:" + where);
			}
		},
		/**
		 * 绑定
		 * @method bind
		 * @via https://developer.mozilla.org/en/JavaScript/Reference/Global_Objects/Function/bind
		 * @compatibile ECMA-262, 5th (JavaScript 1.8.5)
		 * @static
		 * @param {func} 要绑定的函数
		 * @obj {object} this_obj
		 * @param {any} arg1 (Optional) 预先确定的参数
		 * @param {any} arg2 (Optional) 预先确定的参数
		 * @return {Function}
		 */
		bind: function(func, obj) {
			var slice = [].slice,
				args = slice.call(arguments, 2),
				nop = function() {},
				bound = function() {
					return func.apply(this instanceof nop ? this : (obj || {}), args.concat(slice.call(arguments)));
				};

			nop.prototype = func.prototype;

			bound.prototype = new nop();

			return bound;
		},
		/**
		 * 懒惰执行某函数：一直到不得不执行的时候才执行。
		 * @method lazyApply
		 * @static
		 * @param {Function} fun  调用函数
		 * @param {Object} thisObj  相当于apply方法的thisObj参数
		 * @param {Array} argArray  相当于apply方法的argArray参数
		 * @param {int} ims  interval毫秒数，即window.setInterval的第二个参数.
		 * @param {Function} checker  定期运行的判断函数。<br/>
			对于不同的返回值，得到不同的结果：<br/>
				返回true或1，表示需要立即执行<br/>
				返回-1，表示成功偷懒，不用再执行<br/>
				返回其它值，表示暂时不执行<br/>
		 * @return {int}  返回interval的timerId
		 */
		lazyApply: function(fun, thisObj, argArray, ims, checker) {
			checker = checker || function() {return true; };
			var timer = function() {
					var verdict = checker();
					if (verdict == 1) {
						fun.apply(thisObj, argArray || []);
					}
					if (verdict == 1 || verdict == -1) {
						clearInterval(timerId);
					}
				},
				timerId = setInterval(timer, ims);
			return timerId;
		}
	};


	exports = FunctionH;

}());