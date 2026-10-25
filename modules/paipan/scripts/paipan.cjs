#!/usr/bin/env node
'use strict';
// Original workflow glue. All chart calculations use our independently written engine.
const Qimen = require('./qimen-engine.js');
const {buildSnapshot,writeSnapshot}=require('./snapshot.cjs');
const PROFILES = Object.keys(Qimen.PROFILES);
const FLAGS = {'--center-host':'centerHost','--yang-gods':'yangGods','--intercalation-days':'intercalationDays',
  '--star-direction':'starDirection','--door-order':'doorOrder','--middle-door':'middleDoor','--tai-chang':'taiChang'};

function main(args=process.argv.slice(2)) {
  if (args.length === 1 && args[0] === '--help') {
    console.log('node paipan.cjs --datetime YYYY-MM-DDTHH:MM --profile PROFILE --outdir DIRECTORY');
    console.log('PROFILE: '+PROFILES.join(', '));
    for(const [flag,key] of Object.entries(FLAGS)) console.log(flag+': '+Qimen.SETTING_CHOICES[key].map(([value,label])=>value+' ('+label+')').join(', '));
    return;
  }
  const options = {};
  for (let i = 0; i < args.length; i += 2) {
    const key = args[i], value = args[i + 1];
    if (!['--datetime','--profile','--outdir',...Object.keys(FLAGS)].includes(key) || !value || value.startsWith('--') || options[key] !== undefined)
      throw new Error('参数缺失、重复或不支持。使用 --help 查看格式。');
    options[key] = value;
  }
  if (!options['--datetime'] || !options['--profile'] || !options['--outdir'])
    throw new Error('必须提供 --datetime、--profile 和 --outdir。');
  if (!PROFILES.includes(options['--profile'])) throw new Error('不支持此 profile。使用 --help 查看已实现的组合。');
  const settings={...Qimen.PROFILES[options['--profile']]};
  for(const [flag,key] of Object.entries(FLAGS)) if(options[flag]!==undefined) settings[key]=key==='intercalationDays'?Number(options[flag]):options[flag];
  // Exactly one calculation; every saved format consumes this result.
  const result = buildSnapshot(Qimen.atTime(options['--datetime'],settings));
  const files=writeSnapshot(result,options['--outdir']);
  return {...files,snapshotId:result.snapshotId,schemaVersion:result.schemaVersion,toolVersion:result.generator.version,datetime:result.input,timezone:'UTC+8',
    profile:result.profile,settings:result.settings,inactiveSettings:result.inactiveSettings,engineVersion:Qimen.version,dun:result.yang?'阳遁':'阴遁',ju:result.ju,
    pillars:result.pillars,activePillar:result.activePillar,activeGanZhi:result.activeGanZhi,dingJu:result.dingJu,chiefStar:{name:result.chiefStar,palace:result.target},
    chiefDoor:{name:result.chiefDoor,palace:result.doorTarget},notes:result.notes};
}
module.exports={main};
if(require.main===module)try {const output=main();if(output)console.log(JSON.stringify(output,null,2));} catch (error) { console.error('排盘失败：' + error.message); process.exitCode = 1; }
