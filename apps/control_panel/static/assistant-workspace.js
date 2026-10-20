const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const labels = {open:'Открыто',done:'Готово',cancelled:'Отменено',unknown:'Статус не указан'};
// Smoke/test checks of the bot land in the same list; they stay hidden unless asked for.
const SERVICE = /^\s*(\[?smoke\]?|smoke[-_ ]|test[-_ :]|тест[-_ :])|\bsmoke[-_ ]?test\b/i;
let selected = 'open', query = '', showService = false;
const time = iso => { const d = new Date(iso || Date.now()); return d.toLocaleTimeString('ru-RU', {hour:'2-digit', minute:'2-digit'}); };
export async function loadMintWorkspace() {
  const response = await fetch('/api/assistant-workspace', {cache:'no-store'});
  if (response.status === 403) throw new Error('Поручения Assistant открываются только в панели владельца.');
  if (response.status === 503) {
    const body = await response.json().catch(() => ({}));
    return {unavailable: body.service === 'stopped' ? 'stopped' : 'error', checked_at: body.checked_at};
  }
  if (!response.ok) throw new Error('Не удалось получить поручения Assistant. Повторите попытку.');
  return response.json();
}
function offline(data) {
  const stopped = data.unavailable === 'stopped';
  return '<section class="assistant-workspace" data-disclosure-skip><p class="note mint-lead">Рабочие задачи агентов и проектов — на доске <a href="#board">«Задачи»</a>.</p>' +
    '<div class="mint-offline" role="status"><span class="mint-offline-dot" aria-hidden="true"></span><div><b>' + (stopped ? 'Сервис Assistant выключен' : 'Assistant не ответил') + '</b>' +
    '<p>' + (stopped ? 'Поручения появятся здесь, когда помощник снова заработает. Остальные разделы панели работают как обычно.' : 'Список поручений не пришёл. Обычно помогает повторить через минуту.') + '</p>' +
    '<p class="note">Проверено в ' + esc(time(data.checked_at)) + '</p><button type="button" class="ghost" data-view-retry>Проверить снова</button></div></div></section>';
}
export function renderMintWorkspace(data) {
  if (data.unavailable) return offline(data);
  const all = Array.isArray(data.tasks) ? data.tasks : [];
  const service = all.filter(t => SERVICE.test(t.title || '')).length;
  const tasks = all;
  return '<section class="assistant-workspace" data-disclosure-skip><p class="note mint-lead">Рабочие задачи агентов и проектов — на доске <a href="#board">«Задачи»</a>.</p>' +
    '<div class="mint-filters"><label>Поиск<input type="search" data-mint-query placeholder="Название поручения" value="'+esc(query)+'"></label><div class="mint-states" role="group" aria-label="Статус поручений">'+
    Object.entries({open:'Открытые',done:'Готовые',cancelled:'Отменённые',all:'Все'}).map(([key,title])=>'<button type="button" class="ghost" data-mint-filter="'+key+'" aria-pressed="'+(selected===key)+'">'+title+' <span class="count"></span></button>').join('') +
    (service ? '<button type="button" class="ghost" data-mint-service aria-pressed="'+showService+'" title="Проверочные поручения бота">Служебные <span class="count">'+service+'</span></button>' : '') +
    '</div></div><p class="note" data-mint-count role="status"></p><div class="mint-tasks">'+tasks.map(t=>
      '<details class="mint-task"'+(SERVICE.test(t.title||'')?' data-mint-service-row':'')+' data-mint-status="'+esc(t.status)+'" data-mint-title="'+esc((t.title||'').toLocaleLowerCase())+'"><summary><span class="mint-task-title">'+esc(t.title||'Без названия')+'</span><span class="pill">'+esc(labels[t.status]||labels.unknown)+'</span><span class="mint-due">'+esc(t.due_date||'Без срока')+'</span></summary><div class="mint-task-details"><span>Источник: Assistant</span><span>Номер: '+esc(t.id)+'</span></div></details>').join('')+
    '</div><p class="mint-empty" hidden>Поручений по этим условиям нет. Измените фильтр или поиск.</p>'+
    (data.possibly_truncated?'<p class="note">Показаны первые 200 поручений по сроку.</p>':'')+'</section>';
}
export function mountMintWorkspace(view) {
  const input = view.querySelector('[data-mint-query]');
  if (!input) return null;
  function filter() {
    let shown=0; const counts={all:0};
    view.querySelectorAll('.mint-task').forEach(row=>{
      const visible = showService || !row.hasAttribute('data-mint-service-row');
      if (visible) { counts.all++; counts[row.dataset.mintStatus]=(counts[row.dataset.mintStatus]||0)+1; }
      row.hidden = !(visible && (selected==='all'||row.dataset.mintStatus===selected) && row.dataset.mintTitle.includes(query.toLocaleLowerCase()));
      if (!row.hidden) shown++;
    });
    view.querySelectorAll('[data-mint-filter] .count').forEach(c=>{c.textContent=counts[c.parentElement.dataset.mintFilter]||0;});
    view.querySelector('[data-mint-service]')?.setAttribute('aria-pressed', String(showService));
    view.querySelectorAll('[data-mint-filter]').forEach(button=>button.setAttribute('aria-pressed', String(button.dataset.mintFilter===selected)));
    view.querySelector('[data-mint-count]').textContent='Показано: '+shown;
    view.querySelector('.mint-empty').hidden=shown!==0;
  }
  const search=()=>{query=input.value;filter();};
  const click=event=>{
    const button=event.target.closest('[data-mint-filter]');if(button){selected=button.dataset.mintFilter;filter();}
    if(event.target.closest('[data-mint-service]')){showService=!showService;filter();}
  };
  input.addEventListener('input',search);view.addEventListener('click',click);filter();
  return ()=>{input.removeEventListener('input',search);view.removeEventListener('click',click);};
}
