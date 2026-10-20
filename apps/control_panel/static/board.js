// The board stores intent. Only an executing session can mark work as started.
const escape = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const states = {queued:'Запланировано', running:'В работе', blocked:'Блокеры', review:'На проверке', done:'Готово', cancelled:'Архив'};
const agents = {codex:'Codex', claude:'Claude', mint:'Assistant', human:'Оператор'};
let catalog = [], tasks = [], filter = '', executor = '', projectFilter = '', reload;
let statusFilter = 'active';
let completedOpen = false;
const COLUMN_LIMIT = 8;  // UX-17: a long column shows its first cards; the rest behind «Показать ещё»
const expanded = new Set();
try { completedOpen = localStorage.getItem('pipeline.board.completed-open') === 'true'; } catch {}
try { statusFilter = localStorage.getItem('pipeline.board.status') || 'active'; } catch {}
if (!['active', 'mine', 'all', ...Object.keys(states)].includes(statusFilter)) statusFilter = 'active';
// «Мои решения» (вариант A): results to accept, blockers that need an answer, tasks assigned to Operator.
const mine = t => ['review','blocked'].includes(t.status) || (t.executor === 'human' && !['done','cancelled'].includes(t.status));
const inStatus = (t, id) => id === 'all' || (id === 'active' ? !['done','cancelled'].includes(t.status) : id === 'mine' ? mine(t) : t.status === id);
// #board/mine and other #board/<status> links from Главная select the filter.
export function setBoardStatus(id) {
  if (!['active', 'mine', 'all', ...Object.keys(states)].includes(id)) return;
  statusFilter = id;
  try { localStorage.setItem('pipeline.board.status', statusFilter); } catch {}
}
const request = async (url, body) => {
  const r = await fetch(url, body ? {method:'POST', headers:{'Content-Type':'application/json'},body:JSON.stringify(body)} : {});
  const data = await r.json();
  if (!r.ok) throw new Error(r.status === 404 && url === '/api/board' ? 'Работающий сервер панели ещё не загрузил обновление доски. Нужен перезапуск Pipeline Web.' : (data.detail || r.statusText));
  return data;
};
const date = t => t ? new Date(t * 1000).toLocaleString('ru-RU') : '—';
const project = id => catalog.find(c => c.id === id)?.title || id || 'Проект не выбран';

export async function loadBoard() {
  const data = await request('/api/board');
  try { const registry = await request('/api/board/projects'); catalog = registry.cards; data.work = registry.work; }
  catch (e) { data.registryError = e.message; }
  return data;
}

function matchesContext(t) {
  return (!executor || t.executor === executor) && (!projectFilter || t.project_id === projectFilter) &&
    [t.title, t.description, t.id, project(t.project_id), t.owner].join(' ').toLowerCase().includes(filter.toLowerCase());
}
function matchingTasks() {
  return tasks.filter(t => matchesContext(t) && inStatus(t, statusFilter));
}
function columns() {
  const visible = matchingTasks();
    const stages = Object.entries(states).filter(([id]) => statusFilter === 'all' || (statusFilter === 'active' ? id !== 'cancelled' : statusFilter === 'mine' ? id === 'review' || visible.some(t => t.status === id) : id === statusFilter));
    return `<div class="board-columns compact-kanban ${stages.length === 1 ? 'board-single' : ''}">${stages.map(([id,label]) => {
      const items = id === 'done' && statusFilter === 'active' ? tasks.filter(t => t.status === 'done' && matchesContext(t)) : visible.filter(t => t.status === id);
      const cardList = items.map(t => `<button class="task-card" data-board-open="${escape(t.id)}"><strong>${escape(t.title)}</strong><span class="task-project">${escape(project(t.project_id))}</span><span class="task-meta"><span>${escape(agents[t.executor] || t.executor)}</span><span>${escape(t.priority)}</span></span>${t.blocker ? '<span class="task-blocker">Есть блокер · подробнее в карточке</span>' : ''}${t.status === 'running' && Date.now()/1000 - t.heartbeat_at > 900 ? '<span class="late">Проверить сессию: давно нет отметки</span>' : ''}</button>`);
      const cards = cardList.join('') || '<p class="board-empty">Нет задач</p>';
      const hidden = !expanded.has(id) ? Math.max(0, items.length - COLUMN_LIMIT) : 0;
      const shown = hidden ? cardList.slice(0, COLUMN_LIMIT).join('') + `<button class="ghost board-more" data-board-more="${id}">Показать ещё ${hidden}</button>` : cards;
      if (id === 'done' && statusFilter === 'active') return `<details class="board-column board-completed" data-disclosure-skip ${completedOpen ? 'open' : ''}><summary>${label} <span>${items.length}</span></summary>${shown}</details>`;
      return `<section class="board-column" data-status="${id}" aria-label="${label}"><h2>${label}<span>${items.length}</span></h2>${shown}</section>`;
    }).join('')}</div>`;
}

function statusTabs() {
  return Object.entries({active:'Активные', mine:'Мои решения', ...states, all:'Все'}).map(([id,label]) => {
    const count = tasks.filter(matchesContext).filter(t => inStatus(t, id)).length;
    return `<button class="ghost" data-board-status="${id}" aria-pressed="${id === statusFilter}"${id === 'mine' ? ' title="На проверке, с блокером и назначенные вам"' : ''}>${label} <span>${count}</span></button>`;
  }).join('');
}

export function renderBoard(data) {
  tasks = data.tasks || [];
  if (projectFilter && !tasks.some(t => t.project_id === projectFilter)) projectFilter = '';
  return `<div class="board-intro"><button data-board-new>＋ Новая задача</button><details><summary>Как работать с задачами</summary><p>Добавь задачу и передай её в сессию исполнителя. Подробности, блокеры и результат открываются нажатием на карточку.</p></details></div>
    <div class="board-toolbar"><label>Поиск<input id="board-search" value="${escape(filter)}" placeholder="Задача, проект, агент…"></label>
      <label>Исполнитель<select id="board-agent"><option value="">Все</option>${Object.entries(agents).map(([id,name]) => `<option value="${id}" ${executor === id ? 'selected' : ''}>${name}</option>`).join('')}</select></label>
      <label>Проект<select id="board-project"><option value="">Все проекты</option>${[...new Set(tasks.map(t => t.project_id).filter(Boolean))].sort((a,b) => project(a).localeCompare(project(b),'ru')).map(id => `<option value="${escape(id)}" ${projectFilter === id ? 'selected' : ''}>${escape(project(id))}</option>`).join('')}</select></label>
      <span class="note">${tasks.filter(t => t.status !== 'cancelled').length} задач · ${tasks.filter(t => t.status === 'cancelled').length} в архиве</span></div>
    ${data.registryError ? `<p class="err">NameNode недоступен: ${escape(data.registryError)}. Данные задач сохранены.</p>` : ''}
    <div class="board-statuses" role="group" aria-label="Статус задач">${statusTabs()}</div>
    <div class="board-list">${columns()}</div>
    <p class="note">Занятые проекты и личные блокировки — во вкладке <a href="#projects">Проекты</a>.</p>
    `;
}

function dialog(title, html) {
  let d = document.querySelector('#board-dialog');
  if (!d) { d = document.createElement('dialog'); d.id = 'board-dialog'; document.body.append(d); }
  d.innerHTML = `<div class="board-dialog-head"><h2>${escape(title)}</h2><button class="ghost" data-board-close aria-label="Закрыть">✕</button></div>${html}<p id="board-error" role="alert"></p>`;
  if (!d.open) d.showModal();
  return d;
}

function editForm(task = {}) {
  const locked = task.status === 'running';
  dialog(task.id ? `Изменить ${task.id}` : 'Новая задача', `<form id="board-form" data-id="${escape(task.id || '')}" data-version="${task.version || 0}">
    <label>Что сделать<input name="title" required maxlength="200" value="${escape(task.title || '')}" autofocus></label>
    <label>Проект NameNode<select name="project_id"><option value="">Выбрать позже</option>${catalog.map(c => `<option value="${escape(c.id)}" ${c.id === task.project_id ? 'selected' : ''}>${escape(c.title)}</option>`).join('')}</select></label>
    <div class="board-form-row"><label>Исполнитель<select name="executor">${Object.entries(agents).map(([id,name]) => `<option value="${id}" ${id === (task.executor || 'codex') ? 'selected' : ''}>${name}</option>`).join('')}</select></label>
      <label>Приоритет<select name="priority">${['P0','P1','P2','P3'].map(p => `<option ${p === (task.priority || 'P2') ? 'selected' : ''}>${p}</option>`).join('')}</select></label></div>
    <label>Желаемая модель<input name="model" maxlength="200" value="${escape(task.model || '')}" placeholder="Пусто — текущая модель сессии"></label>
    <p class="note">Здесь сохраняется выбор. Переключение и доступность модели проверяются в сессии перед работой.</p>
    <label>Описание<textarea name="description" rows="4" maxlength="12000">${escape(task.description || '')}</textarea></label>
    <label>Как поймём, что готово<textarea name="acceptance" rows="3" maxlength="12000">${escape(task.acceptance || '')}</textarea></label>
    <button type="submit" ${locked ? 'disabled' : ''}>${task.id ? 'Сохранить' : 'Добавить на доску'}</button></form>`);
}

async function detail(id) {
  const t = await request(`/api/board/${id}`);
  const editable = t.status !== 'running';
  const actions = {queued:['handoff','edit','block','cancel'],running:['block'],blocked:['edit','return','cancel'],review:['approve','return','edit'],done:['return','edit'],cancelled:['edit']}[t.status] || [];
  const labels = {handoff:'Передать в сессию',edit:'Изменить',block:'Указать блокер',cancel:'В архив',approve:'Принять результат',return:'Вернуть в очередь'};
  dialog(t.title, `<p class="note">${escape(t.id)} · ${escape(states[t.status])} · ${escape(t.priority)}</p>
    <dl class="board-detail"><dt>Проект</dt><dd>${escape(project(t.project_id))}</dd><dt>Назначено</dt><dd>${escape(agents[t.executor])} / ${escape(t.model || 'текущая модель сессии')}</dd>
    ${t.owner ? `<dt>Сессия</dt><dd>${escape(t.owner)}<br>${escape(t.session_ref)}<br>Модель по отметке исполнителя: ${escape(t.actual_model)}</dd>` : ''}</dl>
    <h3>Задача</h3><p class="board-prose">${escape(t.description || 'Описание не добавлено.')}</p>
    <h3>Критерий готовности</h3><p class="board-prose">${escape(t.acceptance || 'Не указан.')}</p>
    ${t.blocker ? `<h3>Блокер</h3><p class="board-prose task-blocker">${escape(t.blocker)}</p>` : ''}
    ${t.evidence ? `<h3>Результат и проверка</h3><pre class="board-prose">${escape(t.evidence)}</pre>` : ''}
    <div class="board-actions">${actions.map(action => `<button ${action !== 'handoff' && action !== 'approve' ? 'class="ghost"' : ''} data-board-action="${action}" data-id="${escape(t.id)}" data-version="${t.version}">${labels[action]}</button>`).join('')}</div>
    <details><summary>История (${t.events.length})</summary>${t.events.map(e => `<div class="board-event"><b>${escape(e.action)}</b> · ${escape(date(e.at))}<br>${escape(e.actor)}<pre>${escape(JSON.stringify(e.detail, null, 2))}</pre></div>`).join('')}</details>`);
}

export function initBoard(refresh) {
  reload = refresh;
  document.addEventListener('toggle', e => {
    if (!e.target.matches('.board-completed')) return;
    completedOpen = e.target.open;
    try { localStorage.setItem('pipeline.board.completed-open', String(completedOpen)); } catch {}
  }, true);
  document.addEventListener('input', e => {
    if (e.target.id === 'board-search') filter = e.target.value;
    else if (e.target.id === 'board-agent') executor = e.target.value;
    else if (e.target.id === 'board-project') projectFilter = e.target.value;
    else return;
    document.querySelector('.board-list').innerHTML = columns();
    document.querySelector('.board-statuses').innerHTML = statusTabs();
  });
  document.addEventListener('submit', async e => {
    if (e.target.id !== 'board-form') return;
    e.preventDefault();
    const f = e.target, button = f.querySelector('[type=submit]');
    button.disabled = true;
    try {
      const data = Object.fromEntries(new FormData(f));
      await request(f.dataset.id ? `/api/board/${f.dataset.id}` : '/api/board', f.dataset.id ? {action:'edit',version:Number(f.dataset.version),data} : data);
      document.querySelector('#board-dialog').close(); await reload();
    } catch (err) { document.querySelector('#board-error').textContent = err.message; }
    finally { button.disabled = false; }
  });
  document.addEventListener('click', async e => {
    const b = e.target.closest('button'); if (!b) return;
    try {
      if (b.hasAttribute('data-board-status')) {
        statusFilter = b.dataset.boardStatus;
        try { localStorage.setItem('pipeline.board.status', statusFilter); } catch {}
        document.querySelectorAll('[data-board-status]').forEach(el => el.setAttribute('aria-pressed', String(el.dataset.boardStatus === statusFilter)));
        document.querySelector('.board-list').innerHTML = columns();
      }
      else if (b.dataset.boardMore) { expanded.add(b.dataset.boardMore); document.querySelector('.board-list').innerHTML = columns(); }
      else if (b.hasAttribute('data-board-new')) editForm();
      else if (b.hasAttribute('data-board-close')) document.querySelector('#board-dialog').close();
      else if (b.dataset.boardOpen) await detail(b.dataset.boardOpen);
      else if (b.hasAttribute('data-board-copy')) {
        const text = document.querySelector('#board-handoff');
        try { await navigator.clipboard.writeText(text.value); b.textContent = 'Скопировано'; }
        catch { text.focus(); text.select(); b.textContent = 'Выделено — нажми Ctrl+C'; }
      }
      else if (b.dataset.boardAction) {
        const action = b.dataset.boardAction, id = b.dataset.id;
        if (action === 'edit') { editForm(await request(`/api/board/${id}`)); return; }
        if (action === 'handoff') {
          const h = await request(`/api/board/${id}/handoff`);
          dialog('Передать задачу в сессию', `<p>Скопируй запрос в сессию назначенного агента. Работа ещё не запущена.</p><textarea id="board-handoff" rows="12" readonly>${escape(h.prompt)}</textarea><button data-board-copy>Скопировать запрос</button>`); return;
        }
        const data = {};
        if (['block','return'].includes(action)) { data.reason = prompt(action === 'block' ? 'Что мешает работе? Это не останавливает запущенный процесс.' : 'Что нужно доработать?'); if (!data.reason) return; }
        b.disabled = true;
        await request(`/api/board/${id}`, {action,version:Number(b.dataset.version),data});
        await detail(id); await reload();
      }
    } catch (err) { const target = document.querySelector('#board-error'); if (target) target.textContent = err.message; else alert(err.message); b.disabled = false; }
  });
}
