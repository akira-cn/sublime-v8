/*
	Copyright (c) Baidu Youa Wed QWrap
	version: $version$ $release$ released
	author: JK
*/


(function() {
	var mix = require("object.h").mix,
		indexOf = require("array.h").indexOf;

	//----------QW.CustEvent----------
	/**
	 * @class CustEvent 自定义事件
	 * @namespace QW
	 * @param {object} target 事件所属对象，即：是哪个对象的事件。
	 * @param {string} type 事件类型。备用。
	 * @param {object} eventArgs (Optional) 自定义事件参数
	 * @returns {CustEvent} 自定义事件
	 */
	var CustEvent = function(target, type, eventArgs) {
		this.target = target;
		this.type = type;
		//这里的设计自定义事件和dom事件一样，必须要尊重target和type，即不能让eventArgs覆盖掉target和type，否则很难管理
		mix(this, eventArgs || {}); 
	};

	mix(CustEvent.prototype, {
		/**
		 * @property {Object} target CustEvent的target
		 */
		target: null,
		/**
		 * @property {Object} currentTarget CustEvent的currentTarget，即事件派发者
		 */
		currentTarget: null,
		/**
		 * @property {String} type CustEvent的类型
		 */
		type: null,
		/**
		 * @property {boolean} returnValue fire方法执行后的遗留产物。(建议规则:对于onbeforexxxx事件，如果returnValue===false，则不执行该事件)。
		 */
		returnValue: undefined,
		/**
		 * 设置event的返回值为false。
		 * @method preventDefault
		 * @returns {void} 无返回值
		 */
		preventDefault: function() {
			this.returnValue = false;
		}
	});
	/**
	 * 为一个对象添加一系列事件，并添加on/un/fire三个方法，参见：QW.CustEventTarget.createEvents
	 * @static
	 * @method createEvents
	 * @param {Object} obj 事件所属对象，即：是哪个对象的事件。
	 * @param {String|Array} types 事件名称。
	 * @returns {void} 无返回值
	 */


	/**
	 * @class CustEventTargetH  CustEventTarget的Helper
	 * @singleton 
	 * @namespace QW
	 */

	var CustEventTargetH = {
		/**
		 * 添加监控
		 * @method on 
		 * @param {string} sEvent 事件名称。
		 * @param {Function} fn 监控函数，在CustEvent fire时，this将会指向oScope，而第一个参数，将会是一个CustEvent对象。
		 * @return {boolean} 是否成功添加监控。例如：重复添加监控，会导致返回false.
		 * @throw {Error} 如果没有对事件进行初始化，则会抛错
		 */
		on: function(target, sEvent, fn) {
			var cbs = (target.__custListeners && target.__custListeners[sEvent]) || QW.error("unknown event type", TypeError);
			if (indexOf(cbs, fn) > -1) {
				return false;
			}
			cbs.push(fn);
			return true;
		},
		/**
		 * 取消监控
		 * @method un
		 * @param {string} sEvent 事件名称。
		 * @param {Function} fn 监控函数
		 * @return {boolean} 是否有效执行un.
		 * @throw {Error} 如果没有对事件进行初始化，则会抛错
		 */
		un: function(target, sEvent, fn) {
			var cbs = (target.__custListeners && target.__custListeners[sEvent]) || QW.error("unknown event type", TypeError);
			if (fn) {
				var idx = indexOf(cbs, fn);
				if (idx < 0) {
					return false;
				}
				cbs.splice(idx, 1);
			} else {
				cbs.length = 0;
			}
			return true;

		},
		/**
		 * 事件触发。触发事件时，在监控函数里，this将会指向oScope，而第一个参数，将会是一个CustEvent对象，与Dom3的listener的参数类似。<br/>
		 如果this.target['on'+this.type],则也会执行该方法,与HTMLElement的独占模式的事件(如el.onclick=function(){alert(1)})类似.<br/>
		 如果createEvents的事件类型中包含"*"，则所有事件最终也会落到on("*").
		 * @method fire 
		 * @param {string | sEvent} sEvent 自定义事件，或事件名称。 如果是事件名称，相当于传new CustEvent(this,sEvent,eventArgs).
		 * @param {object} eventArgs (Optional) 自定义事件参数
		 * @return {boolean} 以下两种情况返回false，其它情况下返回true.
		 1. 所有callback(包括独占模式的onxxx)执行完后，custEvent.returnValue===false
		 2. 所有callback(包括独占模式的onxxx)执行完后，custEvent.returnValue===undefined，并且独占模式的onxxx()的返回值为false.
		 */
		fire: function(target, sEvent, eventArgs) {
			if (sEvent instanceof CustEvent) {
				var custEvent = mix(sEvent, eventArgs);
				sEvent = sEvent.type;
			} else {
				custEvent = new CustEvent(target, sEvent, eventArgs);
			}

			var cbs = (target.__custListeners && target.__custListeners[sEvent]) || QW.error("unknown event type", TypeError);
			if (sEvent != "*") {
				cbs = cbs.concat(target.__custListeners["*"] || []);
			}

			custEvent.returnValue = undefined; //去掉本句，会导致静态CustEvent的returnValue向后污染
			custEvent.currentTarget = target;
			var obj = custEvent.currentTarget;
			if (obj && obj['on' + custEvent.type]) {
				var retDef = obj['on' + custEvent.type].call(obj, custEvent); //对于独占模式的返回值，会弱影响event.returnValue
			}

			for (var i = 0; i < cbs.length; i++) {
				cbs[i].call(obj, custEvent);
			}
			return custEvent.returnValue !== false && (retDef !== false || custEvent.returnValue !== undefined);
		},
		/**
		 * 为一个对象添加一系列事件，并添加on/un/fire三个方法<br/>
		 * 添加的事件中自动包含一个特殊的事件类型"*"，这个事件类型没有独占模式，所有事件均会落到on("*")事件对应的处理函数中
		 * @static
		 * @method createEvents
		 * @param {Object} obj 事件所属对象，即：是哪个对象的事件。
		 * @param {String|Array} types 事件名称。
		 * @returns {any} target
		 */
		createEvents: function(target, types) {
			types = types || [];
			if (typeof types == "string") {
				types = types.split(",");
			}
			var listeners = target.__custListeners;
			if (!listeners) {
				listeners = target.__custListeners = {};
			}
			for (var i = 0; i < types.length; i++) {
				listeners[types[i]] = listeners[types[i]] || []; //可以重复create，而不影响之前的listerners.
			}
			listeners['*'] = listeners["*"] || [];
			return target;
		}
	};

	/**
	 * @class CustEventTarget  自定义事件Target，有以下序列方法：createEvents、on、un、fire；参见CustEventTargetH
	 * @namespace QW
	 */

	var CustEventTarget = function() {
		this.__custListeners = {};
	};
	var methodized = require('helper.h').methodize(CustEventTargetH); 
	mix(CustEventTarget.prototype, methodized);

	CustEvent.createEvents = function(target, types) {
		CustEventTargetH.createEvents(target, types); 
		return mix(target, methodized);//尊重对象本身的on。
	};

	exports = CustEvent;

}());