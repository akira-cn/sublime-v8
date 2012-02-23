/*
	Copyright (c) Baidu Youa Wed QWrap
	version: $version$ $release$ released
	author: 月影、JK
*/

/**
 * Helper管理器，核心模块中用来管理Helper的子模块
 * @module core
 * @beta
 * @submodule core_HelperH
 */

/**
 * @class HelperH
 * <p>一个Helper是指同时满足如下条件的一个对象：</p>
 * <ol><li>Helper是一个不带有可枚举proto属性的简单对象（这意味着你可以用for...in...枚举一个Helper中的所有属性和方法）</li>
 * <li>Helper可以拥有属性和方法，但Helper对方法的定义必须满足如下条件：</li>
 * <div> 1). Helper的方法必须是静态方法，即内部不能使用this。</div>
 * <div> 2). 同一个Helper中的方法的第一个参数必须是相同类型或相同泛型。</div>
 * <li> Helper类型的名字必须以Helper或大写字母H结尾。 </li>
 * <li> 对于只满足第一条的JSON，也算是泛Helper，通常以“U”（util）结尾。 </li>
 * <li> 本来Util和Helper应该是继承关系，但是JavaScript里我们把继承关系简化了。</li>
 * </ol>
 * @singleton
 * @namespace QW
 * @helper
 */

(function() {

	var FunctionH = require('function.h'),
		create = require('object.h').create,
		isPlainObject = require('object.h').isPlainObject,
		Methodized = function() {};

	var HelperH = {
		/**
		 * 对于需要返回wrap对象的helper方法，进行结果包装
		 * @method rwrap
		 * @static
		 * @param {Helper} helper Helper对象
		 * @param {Class} wrapper 将返回值进行包装时的包装器(WrapClass)
		 * @param {Object} wrapConfig 需要返回Wrap对象的方法的配置
		 * @return {Object} 方法已rwrap化的<strong>新的</strong>Helper
		 */
		rwrap: function(helper, wrapper, wrapConfig) {
			//create以helper为原型生成了一个新的对象，相当于复制了helper的所有属性，不过新对象属性方法的改变不会对helper产生影响
			var ret = create(helper); 
			wrapConfig = wrapConfig || 'operator';

			for (var i in helper) {
				var wrapType = wrapConfig,
					fn = helper[i];
				if(fn instanceof Function){
					if (typeof wrapType != 'string') {
						wrapType = wrapConfig[i] || '';
					}
					if ('queryer' == wrapType) { //如果方法返回查询结果，对返回值进行包装
						ret[i] = FunctionH.rwrap(fn, wrapper, "returnValue");
					} else if ('operator' == wrapType) { //如果方法只是执行一个操作
						if (helper instanceof Methodized) { //如果是methodized后的,对this直接返回
							ret[i] = FunctionH.rwrap(fn, wrapper, "this");
						} else {
							ret[i] = FunctionH.rwrap(fn, wrapper, 0); //否则对第一个参数进行包装，针对getter系列
						}
					} else if('gsetter' == wrapType){
						if (helper instanceof Methodized){
							ret[i] = FunctionH.rwrap(fn, wrapper, "this", true);					
						}else{
							ret[i] = FunctionH.rwrap(fn, wrapper, 0, true);						
						}
					}
				}
			}
			return ret;
		},
		/**
		 * 根据配置，产生gsetter新方法，它根椐参数的长短来决定调用getter还是setter
		 * @method gsetter
		 * @static
		 * @param {Helper} helper Helper对象
		 * @param {Object} gsetterConfig 需要返回Wrap对象的方法的配置
		 * @return {Object} 方法已gsetter化的<strong>新的</strong>helper
		 */
		gsetter: function(helper, gsetterConfig) {
			//create以helper为原型生成了一个新的对象，相当于复制了helper的所有属性，不过新对象属性方法的改变不会对helper产生影响
			var ret = create(helper);
			gsetterConfig = gsetterConfig || {};

			for (var i in gsetterConfig) {
				ret[i] = (function(config, extra) {
					return function() {
						var offset = arguments.length;
						
						//如果没有methodize过，那么多出来的第一个参数要扣减回去	
						offset -= extra;	
						if (isPlainObject(arguments[extra])) { 
							offset++; //如果第一个参数是json，则当作setter，所以offset+1
						}
						return ret[config[Math.min(offset, config.length - 1)]].apply(this, arguments);
					};
				}(gsetterConfig[i], helper instanceof Methodized ? 0 : 1 )); 
			}
			return ret;
		},

		/**
		 * 对helper的方法，进行mul化，使其可以处理第一个参数是数组的情况
		 * @method mul
		 * @static
		 * @param {Helper} helper Helper对象
		 * @param {json|string} mulConfig 如果某个方法的mulConfig类型和含义如下：
		 getter 或getter_first_all //同时生成get--(返回fist)、getAll--(返回all)
		 getter_first	//生成get--(返回first)
		 getter_all		//生成get--(返回all)
		 queryer		//生成get--(返回concat all结果)
		 gsetter 		//生成gsetter--(如果是getter返回first，如果是setter，作为operator)
		 * @return {Object} 方法已mul化的<strong>新的</strong>Helper
		 */
		mul: function(helper, mulConfig) {
			//create以helper为原型生成了一个新的对象，相当于复制了helper的所有属性，不过新对象属性方法的改变不会对helper产生影响
			var ret = create(helper);
			mulConfig = mulConfig || {};

		
			var getAll = 0,
				getFirst = 1,
				joinLists = 2,
				getFirstDefined = 3;

			for (var i in helper) {
				var fn = helper[i];
				if (fn instanceof Function) {
					var mulType = mulConfig;
					if (typeof mulType != 'string') {
						mulType = mulConfig[i] || '';
					}

					if ("getter" == mulType || "getter_first" == mulType || "getter_first_all" == mulType) {
						//如果是配置成gettter||getter_first||getter_first_all，那么需要用第一个参数
						ret[i] = FunctionH.mul(fn, getFirst);
					} else if ("getter_all" == mulType) {
						ret[i] = FunctionH.mul(fn, getAll);
					} else if ("gsetter" == mulType) {
						ret[i] = FunctionH.mul(fn, getFirstDefined);
					} else {
						//queryer的话需要join返回值，把返回值join起来的说
						//例如W(els).query('div') 每一个el返回一个array，如果不join的话就会变成 [array1, array2, array3...]
						ret[i] = FunctionH.mul(fn, joinLists); 
					}
					//... operator分支这里不出现，因为operator的返回值被rwrap果断抛弃了。。

					if ("getter" == mulType || "getter_first_all" == mulType) {
						//如果配置成getter||getter_first_all，那么还会生成一个带All后缀的方法
						ret[i + "All"] = FunctionH.mul(fn, getAll);
					}
				}
			}
			return ret;
		},
		/**
		 * 对helper的方法，进行methodize化，使其的第一个参数为this，或this[attr]。
		 * @method methodize
		 * @static
		 * @param {Helper} helper Helper对象，如DateH
		 * @param {optional} attr (Optional)属性
		 * @param {boolean} preserveEveryProps (Optional) 是否保留Helper上的属性（非Function的成员），默认不保留
		 * @return {Object} 方法已methodize化的对象
		 */
		methodize: function(helper, attr, preserveEveryProps) {
			var ret = new Methodized(); //因为 methodize 之后gsetter和rwrap的行为不一样  

			for (var i in helper) {
				var fn = helper[i];

				if (fn instanceof Function) {
					ret[i] = FunctionH.methodize(fn, attr);
				}else if(preserveEveryProps){	
					//methodize默认不保留非Function类型的成员
					//如特殊情况需保留，可将preserveEveryProps设为true
					ret[i] = fn;
				}
			}
			return ret;
		}
	};

	exports = HelperH;
}());