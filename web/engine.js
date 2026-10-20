// Browser implementation of digest.py. No network, storage, eval or dependencies.
// CI compares full output with Python on generated boundary/error fixtures.
const missing = value => value === null || value === undefined;
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const strip = value => value.replace(/^[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/gu, '');
function fail(message) { throw new Error(message); }
function civil(value) {
  if(typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) fail('Требуется календарная дата YYYY-MM-DD');
  const [year, month, day] = value.split('-').map(Number);
  const d = new Date(0); d.setUTCFullYear(year, month-1, day); d.setUTCHours(0,0,0,0);
  if(year < 1 || d.getUTCFullYear() !== year || d.getUTCMonth() !== month-1 || d.getUTCDate() !== day) fail('Некорректная календарная дата');
  return {date:value, milliseconds:d.getTime()};
}
function timestamp(value) {
  if(typeof value !== 'string') fail('Время должно быть строкой ISO 8601');
  const m = /^(\d{4}-\d{2}-\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?(Z|([+-])(\d{2}):(\d{2}))$/.exec(value);
  if(!m) fail('Требуется время YYYY-MM-DDTHH:MM:SS[.ffffff] с UTC-смещением или Z');
  const day=civil(m[1]); const [h,min,sec]=[m[2],m[3],m[4]].map(Number);
  const oh=Number(m[8] || 0), om=Number(m[9] || 0);
  if(h>23 || min>59 || sec>59 || oh>23 || om>59) fail('Некорректное время или UTC-смещение');
  const micro=Number((m[5] || '').padEnd(6,'0'));
  const offset=(oh*60+om)*(m[7]==='-'?-1:1);
  const us=BigInt(day.milliseconds)*1000n + BigInt(h*3600+min*60+sec-offset*60)*1000000n + BigInt(micro);
  const zone=offset===0?'+00:00':m[6];
  return {us, date:day.date, iso:`${day.date}T${m[2]}:${m[3]}:${m[4]}${micro?'.'+String(micro).padStart(6,'0'):''}${zone}`};
}
function review(c, reason) {
  return {...c, priority:2, decision:'Нужна ручная проверка данных', reasons:[reason], review_required:true,
    checks:['Сверить первоисточники CRM и переписки с ответственным.'],
    actions:['Уточнить недостающие или противоречивые сведения; не закрывать операцию и не менять CRM автоматически.']};
}
function analyze(c, now) {
  const crm=c.crm, kind=c.kind;
  if(!['onboarding','dismissal','delivery'].includes(kind)) return review(c,`Для типа «${kind}» нет согласованного правила.`);
  if(c.chat.conflicts_with_crm) return review(c,'При нормализации отмечено противоречие переписки и CRM; текст сам по себе не отменяет подтверждение.');
  if(!strip(crm.evidence) || !strip(c.chat.evidence)) return review(c,'Не хватает описания CRM или переписки; отсутствие сведений не означает отсутствие проблемы.');
  let priority=4, decision='Проверить данные', checks=[], actions=[];
  if(kind==='onboarding') {
    if(missing(crm.first_day) || missing(crm.documents_confirmed)) return review(c,'Не указана дата первого выхода или неизвестно подтверждение документов.');
    if(!crm.documents_confirmed) {
      priority=crm.first_day>now.date?3:2; decision='Нужно вмешательство: документы не подтверждены';
      checks=['Проверить получение, комплектность и пригодность документов у ответственного руководителя.'];
      actions=['Сегодня запросить подтверждение руководителя и недостающие документы; зафиксировать результат в CRM до первого выхода.'];
    } else decision='Вмешательство по документам не требуется';
  } else if(kind==='dismissal') {
    if(missing(crm.last_day) || missing(crm.manager_confirmed)) return review(c,'Не указана дата последнего рабочего дня или неизвестно подтверждение руководителя.');
    if(!crm.manager_confirmed) {
      priority=crm.last_day<=now.date?2:3; decision='Нужно вмешательство: нет подтверждения руководителя';
      checks=['Получить прямое подтверждение ответственного руководителя и проверить дату последнего рабочего дня.'];
      actions=['Связаться с руководителем сегодня и занести подтверждение в CRM; слова сотрудника не считать основанием для закрытия операции.'];
    } else decision='Вмешательство по подтверждению не требуется';
  } else {
    const status=crm.status;
    if(!['in_transit','accepted'].includes(status)) return review(c,`Неизвестный или отсутствующий статус доставки: ${JSON.stringify(status ?? null)}.`);
    const accepted=crm.accepted_at?timestamp(crm.accepted_at):null;
    if(accepted && accepted.us>now.us) fail('Подтверждение приёмки находится в будущем');
    if(status==='in_transit' && accepted) return review(c,'Статус «В пути» противоречит заполненному времени приёмки в CRM.');
    if(status==='accepted' && accepted) {
      priority=4; decision='Вмешательство не требуется: приёмка подтверждена в CRM';
      checks=['При плановой сверке проверить запись приёмки и количество; внеплановое действие не требуется.'];
      actions=['Не включать в срочные задачи; сохранить подтверждение и оставить случай в сводке как завершённый.'];
    } else if(status==='accepted') return review(c,'Статус «Принято» без времени подтверждения приёмки.');
    else {
      if(!crm.due_at) return review(c,'Для незавершённой доставки не указан срок: срочность определить нельзя.');
      const due=timestamp(crm.due_at), eta=c.chat.eta_at?timestamp(c.chat.eta_at):null;
      if(due.us<=now.us || (eta && eta.us>due.us)) {
        priority=1; decision='Нужно вмешательство: срок доставки наступил или есть риск опоздания';
        checks=['Проверить у курьера фактическое местоположение и ETA, у получателя — факт приёмки.'];
        actions=['Приоритетно проверить эту доставку: предупредить ответственного на точке, согласовать новый срок или резервный вариант и зафиксировать задержку в CRM.'];
      } else {
        priority=3; decision='Наблюдать: доставка ещё не подтверждена';
        checks=['Проверить приёмку к согласованному сроку.'];
        actions=['Повторить сверку к сроку доставки; при риске опоздания связаться с ответственным.'];
      }
    }
  }
  if(!checks.length) { checks=['Плановая сверка подтверждений CRM.']; actions=['Сохранить в ежедневной сводке.']; }
  return {...c,priority,decision,reasons:[decision],review_required:false,checks,actions};
}
function compareIds(a,b) {
  const aa=Array.from(a, c=>c.codePointAt(0)), bb=Array.from(b,c=>c.codePointAt(0));
  for(let i=0;i<Math.min(aa.length,bb.length);i++) if(aa[i]!==bb[i]) return aa[i]-bb[i];
  return aa.length-bb.length;
}
export function buildDigest(payload) {
  if(!object(payload)) fail('Вход должен быть JSON-объектом');
  const now=timestamp(payload.as_of);
  if(!Array.isArray(payload.cases)) fail('cases должен быть массивом');
  if(payload.cases.length>100) fail('Демо принимает не более 100 случаев');
  if(typeof (payload.context ?? '') !== 'string' || payload.context===null) fail('context должен быть текстом');
  const cases=payload.cases.map(original=>{
    if(!object(original)) fail('Каждый случай должен быть объектом');
    for(const name of ['id','kind']) if(typeof original[name]!=='string' || !strip(original[name])) fail(`${name} должен быть непустой строкой`);
    const c={...original};
    for(const source of ['crm','chat']) {
      if(!object(c[source])) fail(`${source} должен быть объектом`);
      c[source]={evidence:'',...c[source]};
      if(typeof c[source].evidence!=='string') fail('Описание источников должно быть текстом');
    }
    for(const name of ['documents_confirmed','manager_confirmed']) if(!missing(c.crm[name]) && typeof c.crm[name]!=='boolean') fail(`${name} должен быть bool или null`);
    if(!missing(c.crm.status) && typeof c.crm.status!=='string') fail('status должен быть строкой или null');
    if(typeof (c.chat.conflicts_with_crm===undefined?false:c.chat.conflicts_with_crm)!=='boolean') fail('conflicts_with_crm должен быть bool');
    for(const name of ['first_day','last_day']) if(!missing(c.crm[name])) civil(c.crm[name]);
    for(const [source,name] of [['crm','due_at'],['crm','accepted_at'],['chat','eta_at']]) if(!missing(c[source][name])) timestamp(c[source][name]);
    return c;
  });
  if(new Set(cases.map(c=>c.id)).size!==cases.length) fail('Повторяющийся идентификатор случая');
  const results=cases.map(c=>{
    const result=analyze(c,now);
    if(result.review_required && c.kind==='delivery' && c.crm.due_at) {
      const due=timestamp(c.crm.due_at), eta=c.chat.eta_at?timestamp(c.chat.eta_at):null;
      if(due.us<=now.us || (eta && eta.us>due.us)) {
        result.priority=1; result.reasons.push('Согласованный срок уже наступил или ETA позже срока: ручную проверку нельзя откладывать.');
      }
    }
    return result;
  });
  results.sort((a,b)=>a.priority-b.priority || compareIds(a.id,b.id));
  return {as_of:now.iso,context:payload.context ?? '',cases:results};
}
