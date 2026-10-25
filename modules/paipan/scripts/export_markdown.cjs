#!/usr/bin/env node
'use strict';
const fs=require('node:fs'),path=require('node:path'),{randomUUID}=require('node:crypto');
const {markdown}=require('./markdown.cjs');
function main(args=process.argv.slice(2)){
 if(args.length===1&&args[0]==='--help'){console.log('node export_markdown.cjs --json INPUT.json --markdown OUTPUT.md');return;}
 const options={};for(let i=0;i<args.length;i+=2){const k=args[i],v=args[i+1];if(!['--json','--markdown'].includes(k)||!v||v.startsWith('--')||options[k])throw new Error('参数缺失、重复或不支持');options[k]=v;}
 if(!options['--json']||!options['--markdown'])throw new Error('必须提供 --json 和 --markdown');
 const source=path.resolve(options['--json']),target=path.resolve(options['--markdown']);
 if(source===target||path.extname(target).toLowerCase()!=='.md')throw new Error('输出必须是独立 .md 文件');
 if(fs.existsSync(target))throw new Error('Markdown 已存在，不覆盖：'+target);
 const data=JSON.parse(fs.readFileSync(source,'utf8'));
 const relative=path.relative(path.dirname(target),source).split(path.sep).join('/');
 const text=markdown(data,relative);
 fs.mkdirSync(path.dirname(target),{recursive:true});const temp=path.join(path.dirname(target),'.qimen-md-'+randomUUID()+'.tmp');
 try{fs.writeFileSync(temp,text,{encoding:'utf8',flag:'wx'});fs.linkSync(temp,target);}finally{if(fs.existsSync(temp))fs.unlinkSync(temp);}
 return {markdown:target,json:source,snapshotId:data.snapshotId??null,legacy:data.schemaVersion===undefined};
}
module.exports={main};
if(require.main===module)try{const result=main();if(result)console.log(JSON.stringify(result,null,2));}catch(error){console.error('导出失败：'+error.message);process.exitCode=1;}
