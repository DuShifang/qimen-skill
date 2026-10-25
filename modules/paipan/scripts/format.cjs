'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:util');
const schema=JSON.parse(fs.readFileSync(path.join(__dirname,'../assets/paipan.schema.json'),'utf8'));
const SCHEMA_VERSION='1.0.0',TOOL_VERSION='0.5.0',MARKDOWN_VERSION='1.0.0';
const TIME_CONVENTIONS={timezone:'UTC+8',utcOffsetMinutes:480,dayBoundary:'23:00',yearBoundary:'立春',monthBoundary:'节',precision:'分钟',calendarDataVersion:'de440s-minute-1898-2101-v1'};
const PALACE_FIELDS=['number','name','direction','earth','sky','hostedEarth','hostedSky','star','door','god','earthGod','dark','darkBranch','bird','empty','horse'];
function palaceStates(result){
 return result.palaces.map(p=>({number:p.number,fields:Object.fromEntries(PALACE_FIELDS.map(key=>{
  let state;
  if(!Object.hasOwn(p,key))state='missing';
  else if((key==='dark'||key==='darkBranch')&&result.darkMode==='unavailable')state='notImplemented';
  else if((['hostedSky','hostedEarth','bird'].includes(key)&&result.layers.stars)
   ||(p.number===5&&((['sky','star'].includes(key)&&!result.layers.stars)
   ||(key==='door'&&(!result.layers.doors||result.settings.middleDoor!=='use'))
   ||(['god','earthGod'].includes(key)&&(!result.layers.gods||result.settings.taiChang==='omit')))))state='notApplicable';
  else state=p[key]===''?'empty':'present';
  return [key,state];
 }))}));
}
// Dependency-free validator for the exact JSON Schema keywords used by this interface.
// It is not a general JSON Schema implementation; the schema is also tested independently.
function validateSchema(value,node=schema,location='$'){
 const fail=message=>{throw new Error(location+': '+message);};
 if(node.$ref){const key=node.$ref.split('/').at(-1);return validateSchema(value,schema.$defs[key],location);}
 if(node.type){const types=Array.isArray(node.type)?node.type:[node.type];
  const ok=types.some(t=>t==='null'?value===null:t==='array'?Array.isArray(value):t==='object'?value!==null&&typeof value==='object'&&!Array.isArray(value):t==='integer'?Number.isInteger(value):t==='number'?typeof value==='number'&&Number.isFinite(value):typeof value===t);
  if(!ok)fail('expected '+types.join('/'));
 }
 if(Object.hasOwn(node,'const')&&!assert.isDeepStrictEqual(value,node.const))fail('invalid constant');
 if(node.enum&&!node.enum.some(v=>assert.isDeepStrictEqual(v,value)))fail('invalid enum');
 if(typeof value==='string'){
  if(node.minLength!==undefined&&[...value].length<node.minLength)fail('string too short');
  if(node.pattern&&!new RegExp(node.pattern,'u').test(value))fail('pattern mismatch');
 }
 if(typeof value==='number'){
  if(node.minimum!==undefined&&value<node.minimum)fail('below minimum');
  if(node.maximum!==undefined&&value>node.maximum)fail('above maximum');
 }
 if(Array.isArray(value)){
  if(node.minItems!==undefined&&value.length<node.minItems)fail('array too short');
  if(node.maxItems!==undefined&&value.length>node.maxItems)fail('array too long');
  if(node.uniqueItems&&value.some((v,i)=>value.slice(0,i).some(w=>assert.isDeepStrictEqual(v,w))))fail('duplicate items');
  if(node.items)value.forEach((v,i)=>validateSchema(v,node.items,location+'['+i+']'));
  if(node.contains&&!value.some(v=>{try{validateSchema(v,node.contains,location);return true;}catch{return false;}}))fail('missing required array member');
 }
 if(value&&typeof value==='object'&&!Array.isArray(value)){
  for(const key of node.required||[])if(!Object.hasOwn(value,key))fail('missing '+key);
  for(const [key,v]of Object.entries(value)){
   if(node.properties&&Object.hasOwn(node.properties,key))validateSchema(v,node.properties[key],location+'.'+key);
   else if(node.additionalProperties===false)fail('unexpected '+key);
   else if(node.additionalProperties&&typeof node.additionalProperties==='object')validateSchema(v,node.additionalProperties,location+'.'+key);
  }
 }
 for(const sub of node.allOf||[])validateSchema(value,sub,location);
 return value;
}
function validateSnapshot(r){
 validateSchema(r);
 const check=(ok,message)=>{if(!ok)throw new Error('快照数据不一致：'+message);};
 const Q=require('./qimen-engine.js');
 check(r.engineVersion===Q.version,'unsupported engineVersion');
 check(r.snapshotId.startsWith('qimen_'+r.input.replace('T','_').replace(':','')+'_'+r.profile+'_'),'snapshot identity');
 check(assert.isDeepStrictEqual(r.settings,Q.normalizeSettings(r.settings)),'settings normalization');
 check(r.profile===`${r.settings.timeLevel}-${r.settings.pan}${r.settings.timeLevel==='shijia'?'-'+r.settings.method:''}`,'profile');
 check(assert.isDeepStrictEqual(r.layers,Q.layerModes(r.settings.pan)),'layers');
 check(assert.isDeepStrictEqual(r.timeConventions,TIME_CONVENTIONS),'time conventions');
 check(r.date.timestamp===Q.parseBeijing(r.input).timestamp,'input/date');
 check(r.activeGanZhi===r.pillars[r.activePillar]&&r.hour===r.pillars.hour,'active pillar');
 check(r.yang===r.dingJu.yang&&r.ju===r.dingJu.ju,'dingJu');
 check(r.palaces.every((p,i)=>p.number===i+1),'palace order');
 for(const [array,field]of Object.entries({earth:'earth',sky:'sky',stars:'star',doors:'door',heavenGods:'god',earthGods:'earthGod',dark:'dark',darkBranches:'darkBranch'}))check(r.palaces.every((p,i)=>p[field]===r[array][i]),array);
 check(assert.isDeepStrictEqual(r.palaceStates,palaceStates(r)),'field availability');
 check(r.palaces.every(p=>r.darkMode!=='unavailable'||(p.dark===''&&p.darkBranch==='')),'unimplemented dark values');
 check(r.palaceStates.every(s=>Object.entries(s.fields).every(([key,state])=>{
  if(state!=='notApplicable')return true;
  const value=r.palaces[s.number-1][key];return typeof value==='boolean'?value===false:value==='';
 })),'notApplicable values');
 const l=r.layers,usesHost=!l.stars||!l.doors||!l.gods||r.settings.middleDoor==='host';
 const inactive=[...(!l.stars?['starDirection']:[]),...(!l.doors?['doorOrder','middleDoor']:[]),...(!l.gods?['taiChang']:[]),...((l.gods||!r.yang)?['yangGods']:[]),...(!usesHost?['centerHost']:[]),...(r.settings.method!=='zhirun'?['intercalationDays']:[])];
 check(assert.isDeepStrictEqual(r.inactiveSettings,inactive),'inactive settings');
 check(r.palaces.every(p=>p.empty===r.voidPalaces.includes(p.number)&&p.horse===(p.number===r.horsePalace)),'void/horse marks');
 return r;
}
module.exports={SCHEMA_VERSION,TOOL_VERSION,MARKDOWN_VERSION,TIME_CONVENTIONS,PALACE_FIELDS,palaceStates,validateSchema,validateSnapshot};
