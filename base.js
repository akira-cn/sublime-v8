function mix(des, src, override) {
	if (ObjectH.isArray(src)) {
		for (var i = 0, len = src.length; i < len; i++) {
			ObjectH.mix(des, src[i], override);
		}
		return des;
	}
	for (i in src) {
		//这里要加一个des[i]，是因为要照顾一些不可枚举的属性
		if (override || !(des[i] || (i in des))) { 
			des[i] = src[i];
		}
	}
	return des;
}

function TextCommand(name, onrun){
	var ret = {};
	ret[name] = onrun;
	return ret;
}