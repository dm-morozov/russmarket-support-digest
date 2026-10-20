import {buildDigest} from './engine.js';
const $=id=>document.getElementById(id);
const labels={1:'1 · начать сейчас',2:'2 · сегодня / проверить',3:'3 · до ближайшего срока',4:'4 · плановая сверка'};
let presets={};
function el(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;}
function clearOutput(message='Данные изменены. Сформируйте новую сводку.'){
  $('results').replaceChildren();$('count').textContent='Ожидает обработки';$('error').hidden=true;
  const n=el('div',undefined,'empty');n.append(el('span','→','empty-number'),el('h3','Сначала — данные, затем вывод'),el('p',message));$('results').append(n);
}
function parseInput(){
  if(new TextEncoder().encode($('payload').value).length>131072)throw new Error('JSON превышает 128 КиБ. Сократите учебную выгрузку.');
  try{return JSON.parse($('payload').value);}catch{throw new Error('Неверный JSON. Проверьте скобки, кавычки и запятые.');}
}
function preview(){
  $('sources').replaceChildren();
  try{const data=parseInput();if(!Array.isArray(data?.cases)||data.cases.length>100)return;
    data.cases.forEach(c=>{const n=el('article',undefined,'source');n.append(el('h3',String(c?.id??'Без ID')),el('p','CRM: '+String(c?.crm?.evidence??'Нет описания')),el('p','Переписка: '+String(c?.chat?.evidence??'Нет описания')));$('sources').append(n);});
  }catch{$('sources').append(el('p','Предпросмотр недоступен: проверьте JSON.','hint'));}
}
function loadPreset(){$('payload').value=JSON.stringify(presets[$('scenario').value],null,2);clearOutput();preview();$('status').textContent='Сценарий загружен. Нажмите кнопку обработки.';}
function render(result){
  $('results').replaceChildren();$('count').textContent='Случаев: '+result.cases.length;
  if(result.context)$('results').append(el('p',result.context,'context'));
  if(!result.cases.length){const n=el('div',undefined,'empty');n.append(el('h3','Случаев нет'),el('p','Добавьте случаи в массив cases. Пустая выгрузка не доказывает отсутствие задач.'));$('results').append(n);return;}
  const urgent=result.cases.filter(c=>c.priority===1),active=result.cases.filter(c=>c.priority<4);
  $('results').append(el('p',active.length?'Начать с: '+(urgent.length?urgent:active.filter(c=>c.priority===active[0].priority)).map(c=>c.id).join(', ')+'. При равном приоритете порядок определяет сотрудник.':'Срочных действий по указанным подтверждениям нет.','order'));
  result.cases.forEach(c=>{const article=el('article',undefined,'case');article.dataset.priority=c.priority;
    const head=el('div',undefined,'case-head');head.append(el('h3',c.id),el('span',labels[c.priority],'tag'));article.append(head,el('p',c.decision,'decision'));
    if(c.review_required)article.append(el('p',c.reasons.join(' '),'review'));
    const facts=el('div',undefined,'facts');[['CRM · запись источника',c.crm.evidence],['Переписка · заявление',c.chat.evidence]].forEach(([label,text])=>{const n=el('div');n.append(el('span',label,'fact-label'),el('p',text||'Нет описания источника'));facts.append(n);});article.append(facts);
    [['Проверить: ',c.checks],['Следующий шаг: ',c.actions]].forEach(([label,values])=>{const n=el('p',undefined,'step');n.append(el('strong',label),document.createTextNode(values.join(' ')));article.append(n);});$('results').append(article);
  });
}
$('scenario').addEventListener('change',loadPreset);
$('payload').addEventListener('input',()=>{clearOutput();preview();$('status').textContent='Есть изменения; предыдущий результат сброшен.';});
$('run').addEventListener('click',()=>{
  $('run').disabled=true;$('error').hidden=true;
  try{render(buildDigest(parseInput()));$('status').textContent='Готово. Рассчитано в браузере; проверьте первоисточники.';}
  catch(error){clearOutput('Сводка не сформирована. Исправьте данные и повторите обработку.');$('error').textContent=error.message;$('error').hidden=false;$('status').textContent='Ошибка данных; подтверждения не созданы.';}
  finally{$('run').disabled=false;}
});
fetch('./examples.json').then(r=>{if(!r.ok)throw new Error('Не удалось загрузить учебные примеры');return r.json();}).then(data=>{presets=data;loadPreset();$('run').disabled=false;}).catch(error=>{$('error').textContent=error.message+'. Обновите страницу или запустите python demo.py локально.';$('error').hidden=false;$('status').textContent='Примеры недоступны';});
