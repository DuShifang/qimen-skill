'use strict';
const fs=require('node:fs'),path=require('node:path'),{randomUUID}=require('node:crypto');
const Q=require('./qimen-engine.js');
const F=require('./format.cjs'),{markdown}=require('./markdown.cjs');
function buildSnapshot(result){
 const r=structuredClone(result);
 r.engineVersion=Q.version;
 r.rules={method:Q.settingLabel('timeLevel',r.settings.timeLevel)+Q.settingLabel('pan',r.settings.pan)+' · '+Q.settingLabel('method',r.settings.method),timezone:'UTC+8',dayBoundary:'23:00',activePillar:r.activePillar,centerHost:Q.settingLabel('centerHost',r.settings.centerHost),hostPalace:r.hostPalace,bird:r.layers.stars?'天禽独立飞布':'天禽随寄宫星转布',jia:'以旬首六仪代甲',dark:r.darkMode,voidAndHorse:r.activePillar};
 r.schemaVersion=F.SCHEMA_VERSION;
 r.snapshotId='qimen_'+r.input.replace('T','_').replace(':','')+'_'+r.profile+'_'+randomUUID();
 r.timeConventions={...F.TIME_CONVENTIONS};
 r.generator={name:'qimen-paipan',version:F.TOOL_VERSION,markdownVersion:F.MARKDOWN_VERSION};
 r.generatedAt=new Date().toISOString();
 r.palaceStates=F.palaceStates(r);
 return F.validateSnapshot(r);
}
const scriptJSON=v=>JSON.stringify(v).replace(/</g,'\\u003c').replace(/\u2028/g,'\\u2028').replace(/\u2029/g,'\\u2029');
function makeHtml(r){
 const template=fs.readFileSync(path.join(__dirname,'../assets/chart-template.html'),'utf8');
 const replacements={'/*__SOLAR__*/':'globalThis.QimenSolarData='+fs.readFileSync(path.join(__dirname,'solar-terms.json'),'utf8')+';',
  '/*__ENGINE__*/':fs.readFileSync(path.join(__dirname,'qimen-engine.js'),'utf8'),'__INITIAL_INPUT__':r.input,
  '/*__INITIAL_SETTINGS__*/':'globalThis.QimenInitialSettings='+scriptJSON(r.settings)+';',
  '/*__INITIAL_SNAPSHOT__*/':'globalThis.QimenInitialSnapshot='+scriptJSON(r)+';'};
 let html=template;
 for(const [marker,replacement]of Object.entries(replacements)){
  if(html.split(marker).length!==2)throw new Error('HTML 模板标记缺失或重复：'+marker);
  html=html.replace(marker,()=>replacement);
 }
 return html;
}
function writeSnapshot(r,outdir){
 F.validateSnapshot(r);outdir=path.resolve(outdir);fs.mkdirSync(outdir,{recursive:true});
 const finalDir=path.join(outdir,r.snapshotId);
 if(fs.existsSync(finalDir))throw new Error('快照已存在，不覆盖：'+finalDir);
 // Only one same-ID writer may commit at a time; this is local file ownership, not a hash gate.
 const lock=finalDir+'.lock';fs.mkdirSync(lock);
 let stage;
 try{
  if(fs.existsSync(finalDir))throw new Error('快照已存在，不覆盖：'+finalDir);
  stage=fs.mkdtempSync(path.join(outdir,'.qimen-stage-'));
  const names={json:r.snapshotId+'.json',html:r.snapshotId+'.html',markdown:r.snapshotId+'.md'};
  const contents={json:JSON.stringify(r,null,2)+'\n',html:makeHtml(r),markdown:markdown(r,names.json)};
  for(const [key,name]of Object.entries(names)){
   const descriptor=fs.openSync(path.join(stage,name),'wx');
   try{fs.writeFileSync(descriptor,contents[key],'utf8');fs.fsyncSync(descriptor);}finally{fs.closeSync(descriptor);}
  }
  for(const [key,name]of Object.entries(names))if(fs.readFileSync(path.join(stage,name),'utf8')!==contents[key])throw new Error('写入校验失败：'+name);
  F.validateSnapshot(JSON.parse(fs.readFileSync(path.join(stage,names.json),'utf8')));
  fs.renameSync(stage,finalDir);stage=undefined;
  return Object.fromEntries(Object.entries(names).map(([key,name])=>[key,path.join(finalDir,name)]));
 }finally{
  if(stage&&path.dirname(stage)===outdir&&path.basename(stage).startsWith('.qimen-stage-'))fs.rmSync(stage,{recursive:true});
  fs.rmdirSync(lock);
 }
}
module.exports={buildSnapshot,makeHtml,writeSnapshot};
