'use strict';
const Q=require('./qimen-engine.js');
const {MARKDOWN_VERSION,palaceStates,validateSnapshot,PALACE_FIELDS}=require('./format.cjs');
const ORDER=[4,9,2,3,5,7,8,1,6];
const FIELD_NAMES={number:'宫数',name:'宫名',direction:'方位',earth:'地盘干',sky:'天盘干',hostedEarth:'地盘寄干',hostedSky:'天盘寄干',star:'九星',door:'门',god:'天盘神',earthGod:'地盘神',dark:'暗干',darkBranch:'暗支',bird:'天禽随星标记',empty:'空亡标记',horse:'驿马标记'};
const SETTING_NAMES={timeLevel:'时间层级',pan:'盘式',method:'定局方式',centerHost:'寄宫方式',yangGods:'转盘阳遁八神',intercalationDays:'置闰天数',starDirection:'九星顺逆',doorOrder:'飞盘门序',middleDoor:'飞盘中门',taiChang:'飞盘太常'};
const STATUS={empty:'空值（本宫未排此项）',notApplicable:'本盘／本宫不适用',notImplemented:'当前方法未实现',missing:'数据缺失',error:'数据异常'};
const escape=v=>String(v).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\|/g,'&#124;').replace(/\r?\n/g,'<br>');
function display(p,key,state){if(state!=='present')return STATUS[state];return escape(typeof p[key]==='boolean'?(p[key]?'是':'否'):p[key]);}
function prepare(data){
 if(data.schemaVersion!==undefined){validateSnapshot(data);return {r:data,legacy:false};}
 // Legacy conversion never fabricates snapshot/version metadata or calculates a chart.
 for(const key of ['palaces','settings','layers','darkMode','inactiveSettings','pillars','dingJu','traces','input','profile','yang','ju','activePillar','activeGanZhi','xun','hidden','chiefStar','target','chiefDoor','doorTarget','hostPalace','hostTerm','voidBranches','voidPalaces','horse','horsePalace','birdPalace'])if(!Object.hasOwn(data,key))throw new Error('旧 JSON 缺少必要字段：'+key);
 if(data.palaces.length!==9||data.palaces.some((p,i)=>p.number!==i+1||PALACE_FIELDS.some(k=>!Object.hasOwn(p,k))))throw new Error('旧 JSON 九宫结构不完整');
 if(!['mingfa','unavailable'].includes(data.darkMode))throw new Error('旧 JSON 暗干可用状态不明确');
 if(!data.palaces.every(p=>PALACE_FIELDS.every(k=>typeof p[k]===(k==='number'?'number':['bird','empty','horse'].includes(k)?'boolean':'string'))))throw new Error('旧 JSON 宫位字段类型错误');
 if(!Array.isArray(data.traces)||!data.traces.every(t=>typeof t==='string')||!Array.isArray(data.inactiveSettings)||!Array.isArray(data.voidBranches)||!Array.isArray(data.voidPalaces))throw new Error('旧 JSON 列表字段类型错误');
 if(!['hour','day','month'].includes(data.activePillar)||data.activeGanZhi!==data.pillars[data.activePillar])throw new Error('旧 JSON 起盘柱不一致');
 const normalized=Q.normalizeSettings(data.settings);
 if(Object.keys(Q.DEFAULT_SETTINGS).some(k=>!Object.hasOwn(data.settings,k)||normalized[k]!==data.settings[k]))throw new Error('旧 JSON 设置不完整或未标准化');
 if(!Object.keys(Q.PROFILES).includes(data.profile))throw new Error('旧 JSON profile不支持');
 if(!['stars','stems','doors','gods'].every(k=>typeof data.layers[k]==='boolean')||Object.keys(Q.layerModes(data.settings.pan)).some(k=>data.layers[k]!==Q.layerModes(data.settings.pan)[k]))throw new Error('旧 JSON 飞转层状态不明确');
 if(data.darkMode==='unavailable'&&!data.palaces.every(p=>p.dark===''&&p.darkBranch===''))throw new Error('旧 JSON 未实现暗干字段异常');
 return {r:{...data,palaceStates:palaceStates(data)},legacy:true};
}
function markdown(data,jsonFile){
 const {r,legacy}=prepare(data),states=new Map(r.palaceStates.map(s=>[s.number,s.fields]));
 const p=new Map(r.palaces.map(p=>[p.number,p]));
 const lines=['# 奇门九宫排盘记录','','## 排盘基础信息','',
 `- 排盘时间：${escape(r.input.replace('T',' '))}`,
 `- 时间约定：${legacy?(r.rules?escape(r.rules.timezone+'；'+r.rules.dayBoundary+'换日')+'（旧记录仅明确上述约定）':'旧记录未提供'):'北京时间 UTC+8；23:00换日；立春换年；节换月；分钟粒度'}`,
 `- Profile：${escape(r.profile)}`,
 `- 盘式／定局：${escape(Q.settingLabel('timeLevel',r.settings.timeLevel)+' · '+Q.settingLabel('pan',r.settings.pan)+' · '+Q.settingLabel('method',r.settings.method))}`,
 `- 遁局：${r.yang?'阳':'阴'}遁${r.ju}局；${escape(r.dingJu.term)} ${escape(r.dingJu.yuan)}`,
 `- 四柱：${escape(r.pillars.year)}年／${escape(r.pillars.month)}月／${escape(r.pillars.day)}日／${escape(r.pillars.hour)}时`,
 `- 起盘柱：${escape(r.activePillar)}；${escape(r.activeGanZhi)}`,
 `- 旬首：${escape(r.xun)}遁${escape(r.hidden)}`,
 `- 值符：${escape(r.chiefStar)}，落${r.target}宫；值使：${escape(r.chiefDoor)}，落${r.doorTarget}宫`,
 `- 寄宫：${escape(Q.settingLabel('centerHost',r.settings.centerHost))}；${r.hostPalace===null?'本盘未调用':r.hostPalace+'宫'}；寄宫节气 ${escape(r.hostTerm)}`,
 `- 空亡：${escape(r.voidBranches.join(''))}；落宫 ${r.voidPalaces.join('、')}；驿马：${escape(r.horse)}，${r.horsePalace}宫`,
 `- 天禽位置：${r.birdPalace}宫（${r.layers.stars?'独立飞布':'随寄宫星'}）`,
 `- 实际节气：${escape(r.solar?.current?.term??'旧记录未提供')}；${escape(r.solar?.current?.text??'旧记录未提供')}`,
 '', '## 九宫空间总览','','上南下北，按 `4 9 2 / 3 5 7 / 8 1 6` 排列。','','| 巽四宫 | 离九宫 | 坤二宫 |','|---|---|---|'];
 function overview(number){const c=p.get(number),s=states.get(number);return `${escape(c.name)}${number}宫<br>星：${display(c,'star',s.star)}；门：${display(c,'door',s.door)}<br>天神：${display(c,'god',s.god)}；地神：${display(c,'earthGod',s.earthGod)}<br>天干：${display(c,'sky',s.sky)}；地干：${display(c,'earth',s.earth)}<br>天寄：${display(c,'hostedSky',s.hostedSky)}；地寄：${display(c,'hostedEarth',s.hostedEarth)}`;}
 for(let i=0;i<9;i+=3)lines.push('| '+ORDER.slice(i,i+3).map(overview).join(' | ')+' |');
 lines.push('','## 九宫逐宫详情','');
 for(const number of ORDER){const c=p.get(number),s=states.get(number);lines.push(`### ${c.name}${number}宫`,'','| 字段 | 值 | 状态 |','|---|---|---|');
  for(const key of PALACE_FIELDS)lines.push(`| ${FIELD_NAMES[key]} (${key}) | ${display(c,key,s[key])} | ${s[key]} |`);
  lines.push('');
 }
 lines.push('## 设置与计算说明','','| 设置 | 记录值 | 调用状态 |','|---|---|---|');
 for(const [key,value]of Object.entries(r.settings))lines.push(`| ${SETTING_NAMES[key]} (${key}) | ${escape(Q.settingLabel(key,value))} (${escape(value)}) | ${r.inactiveSettings.includes(key)?'未参与计算':'参与计算'} |`);
 lines.push('','### 引擎计算步骤','');r.traces.forEach((text,i)=>lines.push(`${i+1}. ${escape(text)}`));
 lines.push('','### 状态与已知限制','',`- 暗干层：${escape(r.darkMode)}；${r.darkMode==='unavailable'?'当前方法未实现，空字符串不表示不存在暗干。':'鸣法已实现。'}`,
 '- 星、干、门、神飞布标记：'+escape(JSON.stringify(r.layers)),
 '- 分钟节气表；固定北京时间，不处理真太阳时或其他日界；未完成 Android 整盘逐屏或秒级历算全量对照。',
 '- 空亡驿马按起盘柱通行规则；本记录只包含已计算的盘面事实。');
 for(const note of r.notes||[])lines.push('- '+escape(note));
 if(legacy)lines.push('- 此记录由旧 JSON 转换；缺失的新元数据未补造，未重新排盘。');
 lines.push('','## 数据来源与版本','',`- snapshotId：${escape(r.snapshotId??'旧记录未提供')}`,`- schemaVersion：${escape(r.schemaVersion??'旧记录未提供')}`,
 `- engineVersion：${escape(r.engineVersion??'旧记录未提供')}`,`- 工具版本：${escape(r.generator?.version??'旧记录未提供')}`,`- Markdown 导出器版本：${MARKDOWN_VERSION}`,
 `- 快照生成时间（UTC）：${escape(r.generatedAt??'旧记录未提供')}`,`- 对应 JSON：[${escape(jsonFile)}](${encodeURI(jsonFile)})`,'');
 return lines.join('\n');
}
module.exports={markdown,ORDER,FIELD_NAMES,prepare};
