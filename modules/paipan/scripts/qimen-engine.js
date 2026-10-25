/* 独立编写的奇门排盘引擎。运行时不依赖 APK、服务器或第三方代码。
 * 规则依据和验证范围见《排盘规则与核对说明.md》。节气表：JPL DE440s 离线计算，按最近分钟保存。
 */
(function (root) {
  'use strict';
  const STEMS = [...'甲乙丙丁戊己庚辛壬癸'];
  const BRANCHES = [...'子丑寅卯辰巳午未申酉戌亥'];
  const RING = [1, 8, 3, 4, 9, 2, 7, 6];
  const EARTH_ORDER = [...'戊己庚辛壬癸丁丙乙'];
  const STARS = ['天蓬','天芮','天冲','天辅','天禽','天心','天柱','天任','天英'];
  const DOORS = ['休门','死门','伤门','杜门','','开门','惊门','生门','景门'];
  const GODS = ['值符','螣蛇','太阴','六合','白虎','玄武','九地','九天'];
  const FLY_DOORS = DOORS.map((name,i) => i === 4 ? '中门' : name);
  const NUMBER_RING = [1,2,3,4,5,6,7,8,9];
  const OUTER_NUMBERS = NUMBER_RING.filter(p => p !== 5);
  const SETTING_CHOICES = {
    timeLevel:[['shijia','时家'],['rijia','日家'],['yuejia','月家']],
    pan:[['zhuanpan','转盘'],['feipan','飞盘'],['xingfeimenzhuan','星飞门转'],['shenzhuanfeipan','神转飞盘']],
    method:[['chaibu','拆补'],['zhirun','置闰'],['rijia','日家定局'],['yuejia','月家定局']],
    centerHost:[['kun2','寄坤二'],['eight-season','八节寄宫'],['yang-kun-yin-gen','阳坤阴艮'],['yang-gen-yin-kun','阳艮阴坤'],['four-season','四立四维'],['kan1','寄坎一']],
    yangGods:[['baihu-xuanwu','白虎玄武'],['gouchen-zhuque','勾陈朱雀']],
    intercalationDays:[[7,'7 天'],[8,'8 天'],[9,'9 天'],[10,'10 天']],
    starDirection:[['forward','顺飞'],['reverse','逆飞'],['dun','阳顺阴逆']],
    doorOrder:[['forward','全部顺飞'],['dun','阳顺阴逆']],
    middleDoor:[['use','使用'],['advance','进'],['retreat','退'],['host','寄']],
    taiChang:[['use','使用'],['omit','弃用']]
  };
  const DEFAULT_SETTINGS = {timeLevel:'shijia',pan:'zhuanpan',method:'chaibu',centerHost:'kun2',yangGods:'baihu-xuanwu',
    intercalationDays:8,starDirection:'dun',doorOrder:'forward',middleDoor:'use',taiChang:'use'};
  const NAMES = ['坎','坤','震','巽','中','乾','兑','艮','离'];
  const DIRECTIONS = ['北','西南','东','东南','中','西北','西','东北','南'];
  const TERMS = '冬至 小寒 大寒 立春 雨水 惊蛰 春分 清明 谷雨 立夏 小满 芒种 夏至 小暑 大暑 立秋 处暑 白露 秋分 寒露 霜降 立冬 小雪 大雪'.split(' ');
  const JU_TABLE = [
    [1,7,4],[2,8,5],[3,9,6],[8,5,2],[9,6,3],[1,7,4],
    [3,9,6],[4,1,7],[5,2,8],[4,1,7],[5,2,8],[6,3,9],
    [9,3,6],[8,2,5],[7,1,4],[2,5,8],[1,4,7],[9,3,6],
    [7,1,4],[6,9,3],[5,8,2],[6,9,3],[5,8,2],[4,7,1]
  ];
  // 数据独立保存；浏览器版由 HTML 内嵌，同一份表用于命令行与网页。
  const SOLAR_DATA = typeof module !== 'undefined' && module.exports
    ? require('./solar-terms.json') : root.QimenSolarData;
  const mod = (n, base) => ((n % base) + base) % base;
  const gz = index => STEMS[mod(index,10)] + BRANCHES[mod(index,12)];
  const integer = (value, min, max, label) => {
    if (!Number.isInteger(value) || value < min || value > max) throw new Error(label + '超出范围。');
    return value;
  };
  function cycleIndex(stem, branch) {
    const index = Array.from({length:60}, (_, i) => i).find(i => i % 10 === stem && i % 12 === branch);
    if (index === undefined) throw new Error('干支组合不成立。');
    return index;
  }
  function normalizeSettings(options={}) {
    if (!options || typeof options !== 'object' || Array.isArray(options)) throw new Error('排盘设置须为对象。');
    for (const key of Object.keys(options)) if (!(key in DEFAULT_SETTINGS)) throw new Error('不支持的排盘设置：'+key);
    if(options.method!==undefined && !SETTING_CHOICES.method.some(([value])=>value===options.method)) throw new Error('不支持的定局方法。');
    const settings = {...DEFAULT_SETTINGS,...options};
    if (settings.timeLevel !== 'shijia') settings.method = settings.timeLevel;
    else if (!['chaibu','zhirun'].includes(settings.method)) throw new Error('时家定局请选择拆补或置闰。');
    for (const [key,value] of Object.entries(settings)) {
      if (!SETTING_CHOICES[key].some(choice => choice[0] === value)) throw new Error('排盘设置不支持此值：'+key);
    }
    return settings;
  }
  const settingLabel = (key,value) => SETTING_CHOICES[key].find(choice => choice[0] === value)?.[1] || '';
  const PROFILES = Object.fromEntries(SETTING_CHOICES.timeLevel.flatMap(([timeLevel]) =>
    SETTING_CHOICES.pan.flatMap(([pan]) => (timeLevel==='shijia'?['chaibu','zhirun']:[timeLevel]).map(method =>
      [`${timeLevel}-${pan}${timeLevel==='shijia'?'-'+method:''}`,{timeLevel,pan,method}]))));
  function layerModes(pan) {
    return {stars:pan!=='zhuanpan',stems:pan!=='zhuanpan',doors:['feipan','shenzhuanfeipan'].includes(pan),gods:['feipan','xingfeimenzhuan'].includes(pan)};
  }
  function centerHost(mode,yang,term) {
    if (mode === 'kun2') return 2;
    if (mode === 'kan1') return 1;
    if (mode === 'yang-kun-yin-gen') return yang ? 2 : 8;
    if (mode === 'yang-gen-yin-kun') return yang ? 8 : 2;
    const index = TERMS.indexOf(term);
    if (index < 0) throw new Error('八节／四立寄宫需要明确节气。');
    return mode === 'eight-season' ? RING[Math.floor(index/3)] : [8,4,2,6][Math.floor(mod(index-3,24)/6)];
  }
  function chaiBu(term, dayIndex) {
    integer(dayIndex, 0, 59, '日干支序号');
    const termIndex = TERMS.indexOf(term);
    if (termIndex < 0) throw new Error('未知节气。');
    const headIndex = mod(dayIndex - dayIndex % 5, 60);
    const branch = headIndex % 12;
    const yuanIndex = branch % 3 === 0 ? 0 : branch % 3 === 2 ? 1 : 2;
    return {yang:termIndex < 12, ju:JU_TABLE[termIndex][yuanIndex],
      yuan:['上元','中元','下元'][yuanIndex], head:gz(headIndex), headIndex, term};
  }
  function rotate(values, from, to) {
    const shift = mod(RING.indexOf(to) - RING.indexOf(from), 8);
    const result = Array(9).fill('');
    RING.forEach((palace, i) => { result[RING[mod(i + shift, 8)] - 1] = values[palace - 1]; });
    return result;
  }
  function gods(anchor, direction, names=GODS) {
    const result = Array(9).fill('');
    const start = RING.indexOf(anchor);
    names.forEach((name, i) => { result[RING[mod(start + direction * i, 8)] - 1] = name; });
    return result;
  }
  // 星与干分别排布；“阳顺阴逆”时星盘按遁向，干盘仍按默认顺飞。
  function fly(values, source, target, direction, palaces=NUMBER_RING) {
    const order = palaces.map(p => values[p-1]);
    const from = palaces.indexOf(source), to = palaces.indexOf(target);
    const result = Array(9).fill('');
    order.forEach((_,i) => {result[palaces[mod(to+direction*i,palaces.length)]-1] = order[mod(from+i,order.length)];});
    return result;
  }
  function flyGods(anchor,direction,yang,omit) {
    const names = ['值符','螣蛇','太阴','六合',yang?'勾陈':'白虎','太常',yang?'朱雀':'玄武','九地','九天'];
    if (omit) names.splice(5,1);
    const palaces = omit ? OUTER_NUMBERS : NUMBER_RING;
    if (omit && anchor === 5) anchor = 5+direction;
    const start = palaces.indexOf(anchor), result=Array(9).fill('');
    names.forEach((name,i) => {result[palaces[mod(start+direction*i,palaces.length)]-1]=name;});
    return result;
  }
  function board(yang, ju, hourIndex, options={}, term) {
    if (typeof yang !== 'boolean') throw new Error('阴阳遁需使用布尔值。');
    integer(ju, 1, 9, '局数'); integer(hourIndex, 0, 59, '时干支序号');
    const settings=normalizeSettings(options), layers=layerModes(settings.pan), flight=layers.stars;
    const usesHost=!layers.stars||!layers.doors||!layers.gods||settings.middleDoor==='host';
    const hostPalace=usesHost?centerHost(settings.centerHost,yang,term):null;
    const host=palace => palace===5 ? hostPalace : palace;
    const direction = yang ? 1 : -1;
    const earth = Array(9).fill('');
    EARTH_ORDER.forEach((stem, i) => { earth[mod(ju - 1 + direction * i, 9)] = stem; });
    const xunIndex = Math.floor(hourIndex / 10);
    const hidden = EARTH_ORDER[xunIndex];
    const xun = gz(xunIndex * 10);
    const original = earth.indexOf(hidden) + 1;
    const source = layers.stars ? original : host(original);
    const hourStem = STEMS[hourIndex % 10];
    const targetStem = hourStem === '甲' ? hidden : hourStem;
    const targetRaw = earth.indexOf(targetStem) + 1;
    const target = flight ? targetRaw : host(targetRaw);
    const starDirection = settings.starDirection==='forward' ? 1 : settings.starDirection==='reverse' ? -1 : direction;
    const stars = flight ? fly(STARS,original,target,starDirection) : rotate(STARS,source,target);
    const sky = flight ? fly(earth,original,target,settings.starDirection==='reverse'?-1:1) : rotate(earth,source,target);
    const doorRaw = mod(original - 1 + direction * (hourIndex % 10), 9) + 1;
    const doorSource=layers.doors?original:host(original);
    let doorTarget = layers.doors ? doorRaw : host(doorRaw);
    let doors, heavenGods, earthGods;
    if (layers.doors) {
      const doorDirection=settings.doorOrder==='forward' ? 1 : direction;
      if (settings.middleDoor==='use') doors=fly(FLY_DOORS,original,doorTarget,doorDirection);
      else {
        if (doorTarget===5 && original!==5) doorTarget = settings.middleDoor==='host' ? hostPalace : 5+(settings.middleDoor==='advance' ? direction : -direction);
        const flyingSource=original===5 ? 6 : original;
        const placementTarget=doorTarget===5 ? 6 : doorTarget;
        doors=fly(DOORS,flyingSource,placementTarget,doorDirection,OUTER_NUMBERS);
      }
    } else doors=rotate(DOORS,doorSource,doorTarget);
    if (layers.gods) {
      heavenGods=flyGods(target,direction,yang,settings.taiChang==='omit');
      earthGods=flyGods(original,direction,yang,settings.taiChang==='omit');
    } else {
      const names=yang && settings.yangGods==='gouchen-zhuque' ? GODS.map((name,i)=>i===4?'勾陈':i===5?'朱雀':name) : GODS;
      heavenGods=gods(host(targetRaw),direction,names);earthGods=gods(host(original),direction,names);
    }
    const birdPalace = flight ? stars.indexOf('天禽')+1 : stars.indexOf(STARS[hostPalace-1])+1;
    const voidBranches = [10 - xunIndex * 2, 11 - xunIndex * 2].map(i => BRANCHES[i]);
    const branchPalaces = [1,8,8,3,4,4,9,2,2,7,6,6];
    const voidPalaces = [...new Set(voidBranches.map(b => branchPalaces[BRANCHES.indexOf(b)]))];
    const horseBranchIndex = [2,11,8,5][hourIndex % 12 % 4];
    const horse = BRANCHES[horseBranchIndex];
    const horsePalace = branchPalaces[horseBranchIndex];
    const chiefStar = STARS[original - 1];
    const chiefDoor = (layers.doors ? FLY_DOORS : DOORS)[doorSource - 1];
    // 鸣法暗干按九宫数序排乙至癸，保留旬首原宫（中五不改为寄宫）。
    const darkStemIndices = earth.map((_, i) => mod(hourIndex % 10 - 1 + direction * (i + 1 - original),9) + 1);
    const usesMing=settings.timeLevel==='shijia'&&['zhuanpan','feipan'].includes(settings.pan);
    const dark = usesMing ? darkStemIndices.map(index => STEMS[index]) : Array(9).fill('');
    const darkBranches = usesMing ? darkStemIndices.map(index => BRANCHES[mod(hourIndex % 12 + index - hourIndex % 10,12)]) : Array(9).fill('');
    const palaces = earth.map((stem, i) => ({
      number:i + 1, name:NAMES[i], direction:DIRECTIONS[i], earth:stem, sky:sky[i],
      star:stars[i], door:doors[i], god:heavenGods[i], earthGod:earthGods[i],
      hostedEarth:!flight && i+1===hostPalace ? earth[4] : '', hostedSky:!flight && i+1===birdPalace ? earth[4] : '',
      dark:dark[i], darkBranch:darkBranches[i],
      bird:!flight && i + 1 === birdPalace, empty:voidPalaces.includes(i + 1), horse:i + 1 === horsePalace
    }));
    const inactiveSettings=[...(!layers.stars?['starDirection']:[]),...(!layers.doors?['doorOrder','middleDoor']:[]),...(!layers.gods?['taiChang']:[]),...((layers.gods||!yang)?['yangGods']:[]),...(!usesHost?['centerHost']:[]),...(settings.method!=='zhirun'?['intercalationDays']:[])];
    const activePillar={shijia:'hour',rijia:'day',yuejia:'month'}[settings.timeLevel];
    return {yang, ju, hourIndex, hour:gz(hourIndex), activeIndex:hourIndex,activePillar,activeGanZhi:gz(hourIndex),layers,xun, hidden, original, source,settings,inactiveSettings,hostPalace,darkMode:usesMing?'mingfa':'unavailable',
      targetRaw, target, targetStem, chiefStar, chiefDoor, doorRaw, doorTarget,
      earth, sky, stars, doors, heavenGods, earthGods, dark, darkBranches, birdPalace, palaces,
      voidBranches, voidPalaces, horse, horsePalace,
      traces:[
        `地盘：${yang ? '阳遁顺布' : '阴遁逆布'}，戊起${ju}宫，依戊己庚辛壬癸丁丙乙布九宫。`,
        `旬首：${xun}遁${hidden}；${hidden}在${original}宫。值符${chiefStar}，值使${chiefDoor}。${usesHost?`寄宫规则${settingLabel('centerHost',settings.centerHost)}，本局寄${hostPalace}宫。`:'飞盘本局不调用寄宫。'}`,
        `天盘：起盘柱${gz(hourIndex)}，${hourStem === '甲' ? `以旬首仪${hidden}代甲` : `干${hourStem}`}在地盘${targetRaw}宫；值符落${target}宫。${flight ? `九星${settingLabel('starDirection',settings.starDirection)}，天禽独立；天盘干独立${settings.starDirection==='reverse'?'逆':'顺'}飞布。` : `九星及天盘干沿外圈转布，天禽随${STARS[hostPalace-1]}，中宫干随寄。`}`,
        `门盘：从旬首原宫${original}宫起，按旬内第${hourIndex % 10+1}位${yang?'顺':'逆'}数九宫，原落${doorRaw}宫。${layers.doors ? `门序${settingLabel('doorOrder',settings.doorOrder)}，中门${settingLabel('middleDoor',settings.middleDoor)}；值使记${doorTarget}宫。${original===5&&settings.middleDoor!=='use'?'旬首在中五，值使记名仍保留中门；盘面按八门分布。':''}` : `值使寄后落${doorTarget}宫，八门沿外圈转布。`}`,
        layers.gods ? `神盘：阳顺阴逆飞布；太常${settingLabel('taiChang',settings.taiChang)}${settings.taiChang==='omit'?'，八神跳过中五，值符遇中五按遁向进一宫':''}。` : `八神：天值符起${host(targetRaw)}宫，地值符起${host(original)}宫；${yang?'阳顺':'阴逆'}转布，用${yang ? settingLabel('yangGods',settings.yangGods) : '白虎玄武'}。`,
        usesMing ? `鸣法暗干：以旬首原宫${original}宫为锚点，乙至癸按九宫${yang ? '顺' : '逆'}布；暗支按对应干支差推移。甲时按该九干循环处理。` : '此方法在原软件中有专用附干分支；本版展示星、门、神与天地盘干，专用附干层尚未接入。',
        `空亡与驿马：按${{hour:'时',day:'日',month:'月'}[activePillar]}柱${gz(hourIndex)}，旬空${voidBranches.join('')}，驿马在${horse}（${horsePalace}宫）。`
      ]};
  }
  function parseBeijing(text) {
    const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(text);
    if (!match) throw new Error('请填写完整的公历日期和时间。');
    const [year,month,day,hour,minute] = match.slice(1).map(Number);
    integer(year,1900,2100,'年份（本版 1900—2100）');
    integer(month,1,12,'月份'); integer(hour,0,23,'小时'); integer(minute,0,59,'分钟');
    integer(day,1,new Date(Date.UTC(year,month,0)).getUTCDate(),'日期');
    return {year,month,day,hour,minute, timestamp:Date.UTC(year,month-1,day,hour-8,minute)};
  }
  const termEvents = SOLAR_DATA.years.flatMap((minutes, offset) => {
    const year = SOLAR_DATA.startYear + offset;
    const base = Date.UTC(year,0,1) - 8 * 3600000;
    return minutes.map((minute, i) => {
      const timestamp = base + minute * 60000;
      return {term:TERMS[(i + 1) % 24], termIndex:(i + 1) % 24,
        timestamp, text:formatBeijing(timestamp,' ')};
    });
  });
  const DAY=86400000;
  const civilDay = timestamp => Math.floor((timestamp+8*3600000)/DAY);
  const dayIndexAt = timestamp => mod(civilDay(timestamp)+2440588+49+(new Date(timestamp+8*3600000).getUTCHours()===23?1:0),60);
  function afterDayBoundary(timestamp) {
    return new Date(timestamp+8*3600000).getUTCHours()===23 ? timestamp+3600000 : timestamp;
  }
  function upperHead(timestamp) {
    const adjusted=afterDayBoundary(timestamp);
    return adjusted-mod(dayIndexAt(adjusted),15)*DAY;
  }
  function termInYear(year,term) {
    const event=termEvents.find(event=>event.term===term && event.text.startsWith(String(year)));
    if(!event) throw new Error('置闰定局缺少所需的节气资料。');
    return event;
  }
  // 上元以甲子、己卯、甲午、己酉为首；每元五日，每节十五日。
  // 冬夏至超神达到阈值时，在此前的大雪／芒种重复一个十五日周期。
  function zhiRun(timestamp,days=8) {
    integer(days,7,10,'置闰天数');
    const query=afterDayBoundary(timestamp);
    const now=termEvents.findLast(event=>event.timestamp<=query);
    const year=Number(now.text.slice(0,4));
    const winterYear=['大雪','冬至'].includes(now.term)?year:year-1;
    const winter=termInYear(winterYear,'冬至'), summer=termInYear(year,'夏至');
    const winterHead=upperHead(winter.timestamp), summerHead=upperHead(summer.timestamp);
    const winterLead=civilDay(winter.timestamp)-civilDay(winterHead);
    const summerLead=civilDay(summer.timestamp)-civilDay(summerHead);
    let anchor,termIndex,repeat=false;
    if(winterLead>=days) {
      anchor=upperHead(termInYear(winterYear,'大雪').timestamp);termIndex=23;repeat=true;
      if(civilDay(query)<civilDay(anchor)) {anchor=upperHead(termInYear(winterYear-1,'大雪').timestamp);repeat=false;}
    } else if(summerLead>=days) {
      anchor=upperHead(termInYear(year,'芒种').timestamp);termIndex=11;repeat=true;
      if(civilDay(query)<civilDay(anchor)) {anchor=upperHead(termInYear(year-1,'大雪').timestamp);termIndex=23;repeat=false;}
    } else if(['大雪','冬至'].includes(now.term) && query<winterHead) {
      anchor=upperHead(termInYear(year,'大雪').timestamp);termIndex=23;
    } else {anchor=winterHead;termIndex=0;}
    const elapsed=Math.abs(civilDay(query)-civilDay(anchor));
    const block=Math.floor(elapsed/15), leap=repeat && block===1;
    termIndex=mod(termIndex+(repeat?Math.max(0,block-1):block),24);
    const start=anchor+block*15*DAY;
    const yuanIndex=Math.floor(Math.abs(civilDay(query)-civilDay(start))/5)%3;
    const term=TERMS[termIndex];
    const event=termEvents.filter(event=>event.term===term).reduce((best,event)=>Math.abs(event.timestamp-start)<Math.abs(best.timestamp-start)?event:best);
    const lead=civilDay(event.timestamp)-civilDay(start);
    const relation=lead>0?'超神':lead<0?'接气':'正授';
    const headIndex=dayIndexAt(start);
    return {yang:termIndex<12,ju:JU_TABLE[termIndex][yuanIndex],yuan:['上元','中元','下元'][yuanIndex],
      head:gz(mod(headIndex+yuanIndex*5,60)),headIndex:mod(headIndex+yuanIndex*5,60),term,termIndex,
      upperHead:gz(headIndex),upperHeadDate:formatBeijing(start).slice(0,10),relation,leap,
      label:term+(leap?'置闰':'')+relation,intercalationDays:days,winterLead,summerLead};
  }
  function dailyJu(term,yearBranch) {
    const t=TERMS.indexOf(term);
    integer(yearBranch,0,11,'年支序号');
    if(t<0) throw new Error('日家定局需要有效节气。');
    const b=mod(yearBranch+(t<3?2:1)-1,12)+1, yang=b<7;
    const yuanIndex=Math.floor(mod(t,12)/4);
    const tableRow=2*b-2+(t<12?0:1), labelRow=2*b-2+(yang?1:0);
    return {yang,ju:JU_TABLE[tableRow][yuanIndex],yuan:['上元','中元','下元'][yuanIndex],
      term:TERMS[labelRow],termIndex:labelRow,tableRow,yuanIndex,label:TERMS[labelRow],method:'rijia',yearBranch:BRANCHES[yearBranch]};
  }
  function monthlyJu(term,year) {
    const t=TERMS.indexOf(term);
    integer(year,1900,2100,'月家公历年');
    if(t<0) throw new Error('月家定局需要有效节气。');
    const adjustedYear=year+(t<3?1:0),step=Math.max(1,Math.ceil((adjustedYear-1884)/5));
    const yuanIndex=mod(step,3),termIndex=mod(9+Math.floor(step/3),24);
    return {yang:termIndex<12,ju:JU_TABLE[termIndex][yuanIndex],yuan:['上元','中元','下元'][yuanIndex],
      term:TERMS[termIndex],termIndex,tableRow:termIndex,yuanIndex,label:TERMS[termIndex],method:'yuejia',adjustedYear};
  }
  function atTime(text,options={}) {
    const date = parseBeijing(text);
    const settings=normalizeSettings(options);
    const current = termEvents.findLast(event => event.timestamp <= date.timestamp);
    if (!current) throw new Error('此日期没有可用的节气资料。');
    const next = termEvents.find(event => event.timestamp > date.timestamp) || null;
    const spring = termEvents.find(event => event.term === '立春' && event.text.startsWith(String(date.year)));
    const yearIndex = mod(date.year - (date.timestamp < spring.timestamp ? 1 : 0) - 1984, 60);
    const monthOrdinal = Math.floor(mod(current.termIndex - 3, 24) / 2);
    const monthStem = mod((yearIndex % 10 % 5) * 2 + 2 + monthOrdinal,10);
    const monthBranch = mod(2 + monthOrdinal,12);
    const jdn = Math.floor(Date.UTC(date.year,date.month-1,date.day) / 86400000) + 2440588;
    const dayIndex = mod(jdn + 49 + (date.hour === 23 ? 1 : 0),60);
    const hourBranch = Math.floor((date.hour + 1) / 2) % 12;
    const hourStem = mod((dayIndex % 10 % 5) * 2 + hourBranch,10);
    const hourIndex = cycleIndex(hourStem,hourBranch);
    const monthIndex=cycleIndex(monthStem,monthBranch);
    const cb = settings.timeLevel==='rijia' ? dailyJu(current.term,yearIndex%12)
      : settings.timeLevel==='yuejia' ? monthlyJu(current.term,date.year)
      : settings.method==='chaibu' ? chaiBu(current.term,dayIndex) : zhiRun(date.timestamp,settings.intercalationDays);
    const activeIndex={shijia:hourIndex,rijia:dayIndex,yuejia:monthIndex}[settings.timeLevel];
    const hostTerm=settings.timeLevel==='shijia'?cb.term:current.term;
    const result = board(cb.yang,cb.ju,activeIndex,settings,hostTerm);
    result.hostTerm=hostTerm;
    result.hourIndex=hourIndex;result.hour=gz(hourIndex);
    result.profile = `${settings.timeLevel}-${settings.pan}${settings.timeLevel==='shijia'?'-'+settings.method:''}`; result.mode = 'calendar'; result.input = text; result.date = date;
    result.dingJu=cb;
    if(settings.method==='chaibu') result.chaiBu=cb;
    result.pillars = {year:gz(yearIndex),month:gz(monthIndex),day:gz(dayIndex),hour:gz(hourIndex)};
    result.solar = {current,next, precision:'分钟', source:SOLAR_DATA.source, nearBoundary:termEvents.some(event => Math.abs(event.timestamp - date.timestamp) <= 180000)};
    result.notes=[];
    if(result.solar.nearBoundary)result.notes.push('交节前后 3 分钟：节气表按最近分钟保存，请核对边界，四柱或定局可能不同。');
    if(result.darkMode==='unavailable')result.notes.push('本方法的专用附干层尚未接入；本盘展示星、门、神和天地盘干。');
    result.traces.unshift(settings.timeLevel==='rijia'
      ? `日家定局：年支${BRANCHES[yearIndex%12]}，当前${current.term}；按日家节气映射取${cb.label} ${cb.yuan}、${cb.yang?'阳':'阴'}遁${cb.ju}局，以日柱${gz(dayIndex)}起盘。`
      : settings.timeLevel==='yuejia'
      ? `月家定局：公历${date.year}年，当前${current.term}，修正年份${cb.adjustedYear}；按五年步长取${cb.label} ${cb.yuan}、${cb.yang?'阳':'阴'}遁${cb.ju}局，以月柱${gz(monthIndex)}起盘。`
      : settings.method==='chaibu'
      ? `拆补定局：当前${current.term}，日柱${gz(dayIndex)}；退到最近甲／己符头${cb.head}，属${cb.yuan}，取${cb.yang ? '阳' : '阴'}遁${cb.ju}局。`
      : `置闰定局：阈值${settings.intercalationDays}天，冬至超神${cb.winterLead}天、夏至超神${cb.summerLead}天；本段上元首${cb.upperHeadDate} ${cb.upperHead}，${cb.label} ${cb.yuan}，取${cb.yang?'阳':'阴'}遁${cb.ju}局。`);
    result.traces.unshift(`历法：北京时间 UTC+8；立春换年，节换月，23:00 换日。${date.hour === 23 ? '本时刻日柱按次日计算。' : ''}`);
    return result;
  }
  function formatBeijing(timestamp, separator='T') {
    return new Date(timestamp + 8 * 3600000).toISOString().slice(0,16).replace('T',separator);
  }
  const api = {board,chaiBu,zhiRun,dailyJu,monthlyJu,atTime,parseBeijing,formatBeijing,gz,cycleIndex,normalizeSettings,centerHost,settingLabel,layerModes,PROFILES,SETTING_CHOICES,DEFAULT_SETTINGS,
    STEMS,BRANCHES,RING,TERMS,JU_TABLE,calendar:{minYear:1900,maxYear:2100,precision:'分钟',source:SOLAR_DATA.source},version:'0.4.1'};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  root.Qimen = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
