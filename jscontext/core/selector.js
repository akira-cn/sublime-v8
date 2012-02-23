/*
	Copyright (c) Baidu Youa Wed QWrap
	version: $version$ $release$ released
	author: JK
*/

/**
 * @class Selector Css Selector相关的几个方法
 * @singleton
 * @namespace QW
 */
(function() {
	var mix = require("object.h").mix;
	var StringH = require("string.h");

	var trim = StringH.trim,
		mulReplace = StringH.mulReplace,
		encode4Js = StringH.encode4Js;

	var Selector = {
		/**
		 * @property {int} queryStamp 最后一次查询的时间戳，扩展伪类时可能会用到，以提速
		 */
		queryStamp: 0,
		/**
		 * @property {Json} _operators selector属性运算符
		 */
		_operators: { //以下表达式，aa表示attr值，vv表示比较的值
			'': 'aa',
			//isTrue|hasValue
			'=': 'aa=="vv"',
			//equal
			'!=': 'aa!="vv"',
			//unequal
			'~=': 'aa&&(" "+aa+" ").indexOf(" vv ")>-1',
			//onePart
			'|=': 'aa&&(aa+"-").indexOf("vv-")==0',
			//firstPart
			'^=': 'aa&&aa.indexOf("vv")==0',
			// beginWith
			'$=': 'aa&&aa.lastIndexOf("vv")==aa.length-"vv".length',
			// endWith
			'*=': 'aa&&aa.indexOf("vv")>-1' //contains
		},
		/**
		 * @property {Json} _pseudos 伪类逻辑
		 */
		_pseudos: {
			"first-child": function(a) {
				return !(a = a.previousSibling) || !a.tagName && !a.previousSibling;
			},
			"last-child": function(a) {
				return !(a = a.nextSibling) || !a.tagName && !a.nextSibling;
			},
			"only-child": function(a) {
				var el;
				return !((el = a.previousSibling) && (el.tagName || el.previousSibling) || (el = a.nextSibling) && (el.tagName || el.nextSibling));
			},
			"nth-child": function(a, nth) {
				return checkNth(a, nth);
			},
			"nth-last-child": function(a, nth) {
				return checkNth(a, nth, true);
			},
			"first-of-type": function(a) {
				var tag = a.tagName;
				var el = a;
				while (el = el.previousSlibling) {
					if (el.tagName == tag) return false;
				}
				return true;
			},
			"last-of-type": function(a) {
				var tag = a.tagName;
				var el = a;
				while (el = el.nextSibling) {
					if (el.tagName == tag) return false;
				}
				return true;
			},
			"only-of-type": function(a) {
				var els = a.parentNode.childNodes;
				for (var i = els.length - 1; i > -1; i--) {
					if (els[i].tagName == a.tagName && els[i] != a) return false;
				}
				return true;
			},
			"nth-of-type": function(a, nth) {
				var idx = 1;
				var el = a;
				while (el = el.previousSibling) {
					if (el.tagName == a.tagName) idx++;
				}
				return checkNth(idx, nth);
			},
			//JK：懒得为这两个伪类作性能优化
			"nth-last-of-type": function(a, nth) {
				var idx = 1;
				var el = a;
				while (el = el.nextSibling) {
					if (el.tagName == a.tagName) idx++;
				}
				return checkNth(idx, nth);
			},
			//JK：懒得为这两个伪类作性能优化
			"empty": function(a) {
				return !a.firstChild;
			},
			"parent": function(a) {
				return !!a.firstChild;
			},
			"not": function(a, sSelector) {
				return !s2f(sSelector)(a);
			},
			"enabled": function(a) {
				return !a.disabled;
			},
			"disabled": function(a) {
				return a.disabled;
			},
			"checked": function(a) {
				return a.checked;
			},
			"focus": function(a) {
				return a == a.ownerDocument.activeElement;
			},
			"indeterminate": function(a) {
				return a.indeterminate;
			},
			"input": function(a) {
				return /input|select|textarea|button/i.test(a.nodeName);
			},
			"contains": function(a, s) {
				return (a.textContent || a.innerText || "").indexOf(s) >= 0;
			}
		},
		/**
		 * @property {Json} _attrGetters 常用的Element属性
		 */
		_attrGetters: (function() {
			var o = {
				'class': 'el.className',
				'for': 'el.htmlFor',
				'href': 'el.getAttribute("href",2)'
			};
			var attrs = 'name,id,className,value,selected,checked,disabled,type,tagName,readOnly,offsetWidth,offsetHeight,innerHTML'.split(',');
			for (var i = 0, a; a = attrs[i]; i++) o[a] = "el." + a;
			return o;
		}()),
		/**
		 * @property {Json} _relations selector关系运算符
		 */
		_relations: {
			//寻祖
			"": function(el, filter, topEl) {
				while ((el = el.parentNode) && el != topEl) {
					if (filter(el)) return el;
				}
				return null;
			},
			//寻父
			">": function(el, filter, topEl) {
				el = el.parentNode;
				return el != topEl && filter(el) ? el : null;
			},
			//寻最小的哥哥
			"+": function(el, filter, topEl) {
				while (el = el.previousSibling) {
					if (el.tagName) {
						return filter(el) && el;
					}
				}
				return null;
			},
			//寻所有的哥哥
			"~": function(el, filter, topEl) {
				while (el = el.previousSibling) {
					if (el.tagName && filter(el)) {
						return el;
					}
				}
				return null;
			}
		},
		/** 
		 * 把一个selector字符串转化成一个过滤函数.
		 * @method selector2Filter
		 * @static
		 * @param {string} sSelector 过滤selector，这个selector里没有关系运算符（", >+~"）
		 * @returns {function} : 返回过滤函数。
		 * @example: 
		 var fun=selector2Filter("input.aaa");alert(fun);
		 */
		selector2Filter: function(sSelector) {
			return s2f(sSelector);
		},
		/** 
		 * 判断一个元素是否符合某selector.
		 * @method test 
		 * @static
		 * @param {HTMLElement} el: 被考察参数
		 * @param {string} sSelector: 过滤selector，这个selector里没有关系运算符（", >+~"）
		 * @returns {function} : 返回过滤函数。
		 */
		test: function(el, sSelector) {
			return s2f(sSelector)(el);
		},
		/** 
		 * 用一个css selector来过滤一个数组.
		 * @method filter 
		 * @static
		 * @param {Array|Collection} els: 元素数组
		 * @param {string} sSelector: 过滤selector，这个selector里的第一个关系符不可以是“+”“~”。
		 * @param {Element} pEl: 父节点。默认是document
		 * @returns {Array} : 返回满足过滤条件的元素组成的数组。
		 */
		filter: function(els, sSelector, pEl) {
			var pEl = pEl || document,
				groups = trim(sSelector).split(",");
			if (groups.length < 2) {
				return filterByRelation(pEl || document, els, splitSelector(sSelector));
			}
			else {//如果有逗号关系符，则满足其中一个selector就通过筛选。以下代码，需要考虑：“尊重els的原顺序”。
				var filteredEls = filterByRelation(pEl || document, els, splitSelector(groups[0]));
				if (filteredEls.length == els.length) { //如果第一个过滤筛完，则直接返回
					return filteredEls;
				}
				for(var j = 0, el; el = els[j++];){
					el.__QWSltFlted=0;
				}
				for(j = 0, el; el = filteredEls[j++];){
					el.__QWSltFlted=1;
				}
				var leftEls = els,
					tempLeftEls;
				for(var i=1;i<groups.length;i++){
					tempLeftEls = [];
					for(j = 0, el; el = leftEls[j++];){
						if(!el.__QWSltFlted) tempLeftEls.push(el);
					}
					leftEls = tempLeftEls;
					filteredEls = filterByRelation(pEl || document, leftEls, splitSelector(groups[i]));
					for(j = 0, el; el = filteredEls[j++];){
						el.__QWSltFlted=1;
					}
				}
				var ret=[];
				for(j = 0, el; el = els[j++];){
					if(el.__QWSltFlted) ret.push(el);
				}
				return ret;
			}
		},
		/** 
		 * 以refEl为参考，得到符合过滤条件的HTML Elements. refEl可以是element或者是document
		 * @method query
		 * @static
		 * @param {HTMLElement} refEl: 参考对象
		 * @param {string} sSelector: 过滤selector,
		 * @returns {array} : 返回elements数组。
		 * @example: 
		 var els=query(document,"li input.aaa");
		 for(var i=0;i<els.length;i++ )els[i].style.backgroundColor='red';
		 */
		query: function(refEl, sSelector) {
			Selector.queryStamp = queryStamp++;
			refEl = refEl || document;
			var els = nativeQuery(refEl, sSelector);
			if (els) return els; //优先使用原生的
			var groups = trim(sSelector).split(",");
			els = querySimple(refEl, groups[0]);
			for (var i = 1, gI; gI = groups[i]; i++) {
				var els2 = querySimple(refEl, gI);
				els = els.concat(els2);
				//els=union(els,els2);//除重有负作用，例如效率或污染，放弃除重
			}
			return els;
		},
		/** 
		 * 以refEl为参考，得到符合过滤条件的一个元素. refEl可以是element或者是document
		 * @method one
		 * @static
		 * @param {HTMLElement} refEl: 参考对象
		 * @param {string} sSelector: 过滤selector,
		 * @returns {HTMLElement} : 返回element，如果获取不到，则反回null。
		 * @example: 
		 var els=query(document,"li input.aaa");
		 for(var i=0;i<els.length;i++ )els[i].style.backgroundColor='red';
		 */
		one: function(refEl, sSelector) {
			var els = Selector.query(refEl, sSelector);
			return els[0];
		}


	};

	__SltPsds = Selector._pseudos; //JK 2010-11-11：为提高效率
	/*
		retTrue 一个返回为true的函数
	*/

	function retTrue() {
		return true;
	}

	/*
		arrFilter(arr,callback) : 对arr里的元素进行过滤
	*/

	function arrFilter(arr, callback) {
		var rlt = [],
			i = 0;
		if (callback == retTrue) {
			if (arr instanceof Array) {
				return arr.slice(0);
			} else {
				for (var len = arr.length; i < len; i++) {
					rlt[i] = arr[i];
				}
			}
		} else {
			for (var oI; oI = arr[i++];) {
				callback(oI) && rlt.push(oI);
			}
		}
		return rlt;
	}

	var elContains,
		hasNativeQuery;
	function getChildren(pEl) { //需要剔除textNode与“<!--xx-->”节点
		var els = pEl.children || pEl.childNodes,
			len = els.length,
			ret = [],
			i = 0;
		for (; i < len; i++) if (els[i].nodeType == 1) ret.push(els[i]);
		return ret;
	}
	function findId(id) {
		return document.getElementById(id);
	}

	(function() {
		var div = document.createElement('div');
		div.innerHTML = '<div class="aaa"></div>';
		hasNativeQuery = false && (div.querySelectorAll && div.querySelectorAll('.aaa').length == 1); //部分浏览器不支持原生querySelectorAll()，例如IE8-
		elContains = div.contains ?	
			function(pEl, el) {
				return pEl != el && pEl.contains(el);
			} : function(pEl, el) {
				return (pEl.compareDocumentPosition(el) & 16);
			};
	}());


	function checkNth(el, nth, reverse) {
		if (nth == 'n') {return true; }
		if (typeof el == 'number') {
			var idx = el; 
		} else {
			var pEl = el.parentNode;
			if (pEl.__queryStamp != queryStamp) {
				var nEl = {nextSibling: pEl.firstChild},
					n = 1;
				while (nEl = nEl.nextSibling) {
					if (nEl.nodeType == 1) nEl.__siblingIdx = n++;
				}
				pEl.__queryStamp = queryStamp;
				pEl.__childrenNum = n - 1;
			}
			if (reverse) idx = pEl.__childrenNum - el.__siblingIdx + 1;
			else idx = el.__siblingIdx;
		}

		switch (nth) {
		case 'even':
		case '2n':
			return idx % 2 == 0;
		case 'odd':
		case '2n+1':
			return idx % 2 == 1;
		default:
			if (!(/n/.test(nth))) return idx == nth;
			var arr = nth.replace(/(^|\D+)n/g, "$11n").split("n"),
				k = arr[0] | 0,
				kn = idx - arr[1] | 0;
			return k * kn >= 0 && kn % k == 0;
		}
	}
	/*
	 * s2f(sSelector): 由一个selector得到一个过滤函数filter，这个selector里没有关系运算符（", >+~"）
	 */
	var filterCache = {};

	function s2f(sSelector, isForArray) {
		if (!isForArray && filterCache[sSelector]) return filterCache[sSelector];
		var pseudos = [],
			//伪类数组,每一个元素都是数组，依次为：伪类名／伪类值
			s = trim(sSelector),
			reg = /\[\s*((?:[\w\u00c0-\uFFFF-]|\\.)+)\s*(?:(\S?=)\s*(['"]*)(.*?)\3|)\s*\]/g,
			//属性选择表达式解析,thanks JQuery
			sFun = [];
		s = s.replace(/\:([\w\-]+)(\(([^)]+)\))?/g,  //伪类
			function(a, b, c, d, e) {
				pseudos.push([b, d]);
				return "";
			}).replace(/^\*/g, 
			function(a) { //任意tagName缩略写法
				sFun.push('el.nodeType==1');
				return '';
			}).replace(/^([\w\-]+)/g,//tagName缩略写法
			function(a) { 
				sFun.push('(el.tagName||"").toUpperCase()=="' + a.toUpperCase() + '"');
				return '';
			}).replace(/([\[(].*)|#([\w\-]+)|\.([\w\-]+)/g,//id缩略写法//className缩略写法
			function(a, b, c, d) { 
				return b || c && '[id="' + c + '"]' || d && '[className~="' + d + '"]';
			}).replace(reg, //普通写法[foo][foo=""][foo~=""]等
			function(a, b, c, d, e) { 
				var attrGetter = Selector._attrGetters[b] || 'el.getAttribute("' + b + '")';
				sFun.push(Selector._operators[c || ''].replace(/aa/g, attrGetter).replace(/vv/g, e || ''));
				return '';
			});
		if (!(/^\s*$/).test(s)) {
			throw "Unsupported Selector:\n" + sSelector + "\n-" + s;
		}
		for (var i = 0, pI; pI = pseudos[i]; i++) { //伪类过滤
			if (!Selector._pseudos[pI[0]]) throw "Unsupported Selector:\n" + pI[0] + "\n" + s;
			//标准化参数 && 把位置下标传进去，可以实现even和odd - by akira
			//__SltPsds[filter](el, match, i, els);
			sFun.push('__SltPsds["' + pI[0] + '"](el,"' + (pI[1] != null?encode4Js(pI[1]):'') + '",i,els)'); 
		}
		if (sFun.length) {
			if (isForArray) {
				return new Function('els', 'var els2=[];for(var i=0,el;el=els[i];i++){if(' + sFun.join('&&') + ') els2.push(el);} return els2;');
			} else {
				return (filterCache[sSelector] = new Function('el, i, els', 'return ' + sFun.join('&&') + ';'));
			}
		} else {
			if (isForArray) {
				return function(els) {
					return arrFilter(els, retTrue);
				};
			} else {
				return (filterCache[sSelector] = retTrue);
			}

		}
	}

	/* 
	* {int} xxxStamp: 全局变量查询标记
	*/
	var queryStamp = 0,
		nativeQueryStamp = 0,
		querySimpleStamp = 0;

	/*
	* nativeQuery(refEl,sSelector): 如果有原生的querySelectorAll，并且只是简单查询，则调用原生的query，否则返回null. 
	* @param {Element} refEl 参考元素
	* @param {string} sSelector selector字符串
	* @returns 
	*/
	function nativeQuery(refEl, sSelector) {
		return null;
		if (hasNativeQuery && /^((^|,)\s*[.\w-][.\w\s\->+~]*)+$/.test(sSelector)) {
			//如果浏览器自带有querySelectorAll，并且本次query的是简单selector，则直接调用selector以加速
			//部分浏览器不支持以">~+"开始的关系运算符
			var oldId = refEl.id,
				tempId,
				arr = [],
				els;
			if (!oldId && refEl.parentNode) { //标准的querySelectorAll中的selector是相对于:root的，而不是相对于:scope的
				tempId = refEl.id = '__QW_slt_' + nativeQueryStamp++;
				try {
					els = refEl.querySelectorAll('#' + tempId + ' ' + sSelector);
				} finally {
					refEl.removeAttribute('id');
				}
			}
			else{
				els = refEl.querySelectorAll(sSelector);
			}
			for (var i = 0, elI; elI = els[i++];) arr.push(elI);
			return arr;
		}
		return null;
	}

	/* 
	* querySimple(pEl,sSelector): 得到以pEl为参考，符合过滤条件的HTML Elements. 
	* @param {Element} pEl 参考元素
	* @param {string} sSelector 里没有","运算符
	* @see: query。
	*/

	function querySimple(pEl, sSelector) {

		querySimpleStamp++;
		/*
			为了提高查询速度，有以下优先原则：
			最优先：原生查询
			次优先：在' '、'>'关系符出现前，优先正向（从左到右）查询
			次优先：id查询
			次优先：只有一个关系符，则直接查询
			最原始策略，采用关系判断，即：从最底层向最上层连线，能连线成功，则满足条件
		*/

		//最优先：原生查询
		var els = nativeQuery(pEl, sSelector);
		if (els) return els; //优先使用原生的

		var sltors = splitSelector(sSelector),
			pEls = [pEl],
			i,
			elI,
			pElI;

		var sltor0;
		//次优先：在' '、'>'关系符出现前，优先正向（从上到下）查询
		while (sltor0 = sltors[0]) {
			if (!pEls.length) return [];
			var relation = sltor0[0];
			els = [];
			if (relation == '+') { //第一个弟弟
				filter = s2f(sltor0[1]);
				for (i = 0; elI = pEls[i++];) {
					while (elI = elI.nextSibling) {
						if (elI.tagName) {
							if (filter(elI)) els.push(elI);
							break;
						}
					}
				}
				pEls = els;
				sltors.splice(0, 1);
			} else if (relation == '~') { //所有的弟弟
				filter = s2f(sltor0[1]);
				for (i = 0; elI = pEls[i++];) {
					if (i > 1 && elI.parentNode == pEls[i - 2].parentNode) continue; //除重：如果已经query过兄长，则不必query弟弟
					while (elI = elI.nextSibling) {
						if (elI.tagName) {
							if (filter(elI)) els.push(elI);
						}
					}
				}
				pEls = els;
				sltors.splice(0, 1);
			} else {
				break;
			}
		}
		var sltorsLen = sltors.length;
		if (!sltorsLen || !pEls.length) return pEls;

		//次优先：idIdx查询
		for (var idIdx = 0, id; sltor = sltors[idIdx]; idIdx++) {
			if ((/^[.\w-]*#([\w-]+)/i).test(sltor[1])) {
				id = RegExp.$1;
				sltor[1] = sltor[1].replace('#' + id, '');
				break;
			}
		}
		if (idIdx < sltorsLen) { //存在id
			var idEl = findId(id);

			if (!idEl) return [];
			for (i = 0, pElI; pElI = pEls[i++];) {
				if (!pElI.parentNode || elContains(pElI, idEl)) {
					els = filterByRelation(pElI, [idEl], sltors.slice(0, idIdx + 1));
					if (!els.length || idIdx == sltorsLen - 1) return els;
					return querySimple(idEl, sltors.slice(idIdx + 1).join(',').replace(/,/g, ' '));
				}
			}
			return [];
		}

		//---------------
		var getChildrenFun = function(pEl) {
			return pEl.getElementsByTagName(tagName);
		},
			tagName = '*',
			className = '';
		sSelector = sltors[sltorsLen - 1][1];
		sSelector = sSelector.replace(/^[\w\-]+/, function(a) {
			tagName = a;
			return "";
		});

		if (hasNativeQuery) {
			sSelector = sSelector.replace(/^[\w\*]*\.([\w\-]+)/, function(a, b) {
				className = b;
				return "";
			});
		}

		if (className) {
			getChildrenFun = function(pEl) {
				return pEl.querySelectorAll(tagName + '.' + className);
			};
		}

		//次优先：只剩一个'>'或' '关系符(结合前面的代码，这时不可能出现还只剩'+'或'~'关系符)
		if (sltorsLen == 1) {
			if (sltors[0][0] == '>') {
				getChildrenFun = getChildren;
				var filter = s2f(sltors[0][1], true);
			} else {
				filter = s2f(sSelector, true);
			}
			els = [];
			for (i = 0; pElI = pEls[i++];) {
				els = els.concat(filter(getChildrenFun(pElI)));
			}
			return els;
		}

		//走第一个关系符是'>'或' '的万能方案
		sltors[sltors.length - 1][1] = sSelector;
		els = [];
		for (i = 0; pElI = pEls[i++];) {
			els = els.concat(filterByRelation(pElI, getChildrenFun(pElI), sltors));
		}
		return els;
	}


	function splitSelector(sSelector) {
		var sltors = [];
		var reg = /(^|\s*[>+~ ]\s*)(([\w\-\:.#*]+|\([^\)]*\)|\[\s*((?:[\w\u00c0-\uFFFF-]|\\.)+)\s*(?:(\S?=)\s*(['"]*)(.*?)\6|)\s*\])+)(?=($|\s*[>+~ ]\s*))/g;
		var s = trim(sSelector).replace(reg, function(a, b, c, d) {
			sltors.push([trim(b), c]);
			return "";
		});
		if (!(/^\s*$/).test(s)) {
			throw "Unsupported Selector:\n" + sSelector + "\n--" + s;
		}
		return sltors;
	}

	/*
	判断一个长辈与子孙节点是否满足关系要求。----特别说明：这里的第一个关系只能是父子关系，或祖孙关系;
	*/

	function filterByRelation(pEl, els, sltors) {
		var sltor = sltors[0],
			len = sltors.length,
			needNotTopJudge = !sltor[0],
			filters = [],
			relations = [],
			needNext = [],
			relationsStr = '';

		for (var i = 0; i < len; i++) {
			sltor = sltors[i];
			filters[i] = s2f(sltor[1], i == len - 1); //过滤
			relations[i] = Selector._relations[sltor[0]]; //寻亲函数
			if (sltor[0] == '' || sltor[0] == '~') needNext[i] = true; //是否递归寻亲
			relationsStr += sltor[0] || ' ';
		}
		els = filters[len - 1](els); //自身过滤

		if (relationsStr == ' ') return els;
		if (/[+>~] |[+]~/.test(relationsStr)) { //需要回溯
			//alert(1); //用到这个分支的可能性很小。放弃效率的追求。

			function chkRelation(el) { //关系人过滤
				var parties = [],
					//中间关系人
					j = len - 1,
					party = parties[j] = el;
				for (; j > -1; j--) {
					if (j > 0) { //非最后一步的情况
						party = relations[j](party, filters[j - 1], pEl);
					} else if (needNotTopJudge || party.parentNode == pEl) { //最后一步通过判断
						return true;
					} else { //最后一步未通过判断
						party = null;
					}
					while (!party) { //回溯
						if (++j == len) { //cache不通过
							return false;
						}
						if (needNext[j]) {
							party = parties[j - 1];
							j++;
						}
					}
					parties[j - 1] = party;
				}
			};
			return arrFilter(els, chkRelation);
		} else { //不需回溯
			var els2 = [];
			for (var i = 0, el, elI; el = elI = els[i++];) {
				for (var j = len - 1; j > 0; j--) {
					if (!(el = relations[j](el, filters[j - 1], pEl))) {
						break;
					}
				}
				if (el && (needNotTopJudge || el.parentNode == pEl)) els2.push(elI);
			}
			return els2;
		}

	}

	exports = Selector
}());