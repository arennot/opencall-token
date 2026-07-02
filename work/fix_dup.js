var fs = require('fs');
var p = 'C:\\Users\\arenn\\Documents\\Codex\\2026-06-30\\opencall-token\\outputs\\opencall-token\\app.js';
var code = fs.readFileSync(p, 'utf8');
// Remove the duplicate helper declarations added by the community patch
var dup = 'function saveLocalOpps(arr){localStorage.setItem(\"oct_localopps\",JSON.stringify(arr))}\n\nconst TYPE_LABELS={opencall:\"公开征稿\",residency:\"驻留项目\",grant:\"资金资助\"};\nconst TYPE_CLASS={opencall:\"oc\",residency:\"rs\",grant:\"gr\"};\nconst today=new Date();';
code = code.replace(dup, 'function saveLocalOpps(arr){localStorage.setItem(\"oct_localopps\",JSON.stringify(arr))}');
fs.writeFileSync(p, code, 'utf8');
console.log('Fixed OK');
