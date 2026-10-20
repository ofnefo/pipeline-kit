// Projects: catalogue rows + NameNode claims ("кто занял"), Operator's personal locks, card and project file editing.
import { applyDisclosure } from './disclosure.js?v=ux35-20261011';
import { openReportLinks, projectPath } from './report-links.js';
import { renderProjectSessions } from './project-sessions.js?v=c3-20261019s';
const esc = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const request = async (url, body) => {
  const r = await fetch(url, body ? {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)} : {});
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || r.statusText);
  return data;
};
const date = t => t ? new Date(t * 1000).toLocaleString('ru-RU', {day:'2-digit', month:'2-digit', hour:'2-digit', minute:'2-digit'}) : '—';
const labels = {working:'Проекты', pipeline:'Пайплайны', archive:'Архив', smoke:'Smoke', support:'Служебные', all:'Все'};
const TYPES = ['project', 'pipeline', 'system', 'site', 'service', 'repo', 'host'];
const STANDARD = ['Что это', 'Где лежит', 'Репозиторий', 'Запуск и деплой', 'Куда вносить изменения', 'Риски и открытые вопросы', 'Ревью'];
const pipelineLabels = {design:'Дизайн', video:'Видео', music:'Музыка', office:'Офис', web:'Веб', games:'Игры', soft:'Приложения', adb:'Android', osint:'OSINT', other:'Без пайплайна'};
const statusLabels = {active:'В работе', live:'Работает', implementation:'Реализация', dormant:'На паузе', archived:'Архив', brief:'Бриф', concept:'Концепция', delivered:'Передан', maintenance:'Поддержка', migration:'Перенос', 'owner-review':'На согласовании', pending:'Ожидает', placeholder:'Заготовка', 'post-event':'Закрытие проекта', preparing:'Подготовка', setup:'Настройка', redirect:'Перенаправление', 'domain-only':'Только домен', 'awaiting-device-identification':'Ожидает устройство', unclassified:'Не указан'};
let group = 'working', query = '', pipeline = 'all', status = 'all', grouped = true, redraw, lastData;
let collapsedPipelines = new Set();
try { const stored = JSON.parse(localStorage.getItem('pipeline.project-groups.v1') || '[]'); if (Array.isArray(stored)) collapsedPipelines = new Set(stored.filter(k=>pipelineLabels[k])); } catch {}
const saveGroups = () => { try { localStorage.setItem('pipeline.project-groups.v1', JSON.stringify([...collapsedPipelines])); } catch {} };
const pipelineOf = row => {
  const value = String(row.domain || '').toLowerCase();
  if (pipelineLabels[value]) return value;
  const pathType = /(?:^|[/\\])projects[/\\]([^/\\]+)/i.exec(row.local_path || row.path || '')?.[1]?.toLowerCase();
  return pipelineLabels[pathType] ? pathType : value === 'site' ? 'web' : 'other';
};
// UX-42: project page in Studio (#studio/<type>/<name>) for folders workspace/projects\<type>\<name>.
const studioKey = row => row.studio_key || '';
const statusOf = row => String(row.status || '').split(/\s*[·(—]|\s+/)[0] || 'unclassified';
const statusLabel = row => statusLabels[statusOf(row)] || statusOf(row);

export async function loadProjects() {
  const [catalog, work, sessions] = await Promise.all([
    request('/api/projects'),
    request('/api/namenode/work').catch(e => ({work: [], locks: {}, error: e.message})),
    request('/api/agents/projects').catch(() => ({error:'Не удалось проверить проектные сессии. Обновите страницу; если ошибка повторится, передайте её координатору.'})),
  ]);
  return {...catalog, sessions, rows:(catalog.rows || []).map(row=>({...row, local_path:projectPath(row)})), work: work.work || [], locks: work.locks || {}, workError: work.error};
}

const cardIds = row => {
  const m = /NameNode:\s*([^\n]+)/.exec(row.detail || '');
  const ids = m ? m[1].split(/[,;]\s*/).map(s => s.trim()).filter(Boolean) : [];
  if (row.key && !ids.includes(row.key) && /^[a-z0-9][a-z0-9-]+$/.test(row.key)) ids.push(row.key);
  return ids;
};

function claimsFor(row, work) {
  const ids = cardIds(row);
  return work.filter(w => ids.includes(w.card));
}

function claimCell(claims) {
  if (!claims.length) return '<span class="note">свободен</span>';
  return claims.map(w => w.lock
    ? `<span class="pill bad">🔒 Оператор</span> <small>${esc(w.what.replace(/^Заблокировано оператором лично:?\s*/, '') || 'без причины')} · до ${esc(date(w.until))}</small>`
    : `<b>${esc(w.agent)}</b><br><small>${esc(w.what)}</small><br><small class="note">до ${esc(date(w.until))}</small>`).join('<hr class="proj-sep">');
}

function actions(row, claims) {
  const ids = cardIds(row), locked = claims.some(w => w.lock), id = ids[0];
  const out = [];
  // Published report links need an optional delivery adapter.
  if (ids.length) ids.forEach(c => out.push(`<button type="button" class="ghost" data-proj-card="${esc(c)}" title="Открыть карточку NameNode">${esc(ids.length > 1 ? c : 'Карточка')}</button>`));
  if (studioKey(row)) out.push(`<button type="button" class="ghost" data-proj-studio="${esc(studioKey(row))}" title="Чаты, генерации, файлы и монтаж проекта">Студия</button>`);
  if (row.studio_key) out.push(`<button type="button" class="ghost" data-file-browser-open data-file-browser-start="${esc(row.studio_key)}" title="Файлы, плеер, отчёты и история изменений">Файлы и результаты</button>`);
  if (id) out.push(locked
    ? `<button type="button" class="ghost" data-proj-unlock="${esc(id)}">Снять блокировку</button>`
    : `<button type="button" class="ghost" data-proj-lock="${esc(id)}" data-name="${esc(row.name)}">🔒 Заблокировать</button>`);
  else out.push('<span class="note" title="У записи нет карточки NameNode — создайте её, чтобы блокировать">нет карточки</span>');
  return out.join(' ');
}

export function renderProjects(data) {
  lastData = data;
  const rows = data.rows || [], work = data.work || [], locks = data.locks || {};
  const inGroup = r => group === 'all' ? true : group === 'working' ? r.kind === 'project' : r.kind === group;
  const q = query.trim().toLowerCase();
  const matches = r => !q || [r.name, r.key, r.local_path, r.path, r.detail, r.status].some(v => String(v || '').toLowerCase().includes(q));
  const candidates = rows.filter(inGroup);
  const shown = candidates.filter(r => matches(r) && (pipeline === 'all' || pipelineOf(r) === pipeline) && (status === 'all' || statusOf(r) === status));
  shown.sort((a,b) => (grouped ? pipelineLabels[pipelineOf(a)].localeCompare(pipelineLabels[pipelineOf(b)], 'ru') : 0) || a.name.localeCompare(b.name, 'ru'));
  const busy = work.filter(w => !w.lock), lockRows = work.filter(w => w.lock);
  const nameOf = card => (rows.find(r => cardIds(r).includes(card)) || {}).name || card;
  const busyTable = work.length ? `<div class="table-wrap"><table><thead><tr><th>Карточка</th><th>Кто</th><th>Что делает</th><th>До</th><th></th></tr></thead><tbody>${work.map(w => `<tr${w.lock ? ' class="alert"' : ''}><td><b>${esc(nameOf(w.card))}</b><br><small class="note">${esc(w.card)}</small></td><td>${w.lock ? '<span class="pill bad">🔒 Оператор</span>' : esc(w.agent)}</td><td>${esc(w.what)}</td><td>${esc(date(w.until))}</td><td>${w.lock ? `<button type="button" class="ghost" data-proj-unlock="${esc(w.card)}">Снять</button>` : `<button type="button" class="ghost" data-proj-card="${esc(w.card)}">Карточка</button>`}</td></tr>`).join('')}</tbody></table></div>`
    : '<p class="note">Сейчас никто ничего не занял.</p>';
  const lockWarnings = Object.entries(locks).filter(([, l]) => l.warning).map(([id, l]) => `<p class="err">Блокировка ${esc(id)}: ${esc(l.warning)}</p>`).join('');
  let previousPipeline;
  const projectRows = shown.map(r => {
    const cl = claimsFor(r, work), category = pipelineOf(r), index = rows.indexOf(r);
    const heading = grouped && previousPipeline !== category ? `<tr class="project-group"><th colspan="4"><button type="button" class="project-group-toggle" id="project-group-${category}" data-project-group="${category}" aria-expanded="${!collapsedPipelines.has(category)}">${collapsedPipelines.has(category) ? '▸' : '▾'} ${esc(pipelineLabels[category])}<span class="count">${shown.filter(x => pipelineOf(x) === category).length}</span></button></th></tr>` : '';
    previousPipeline = category;
    const occupancy = cl.some(w => w.lock) ? 'Заблокирован' : cl.length ? 'Занят' : '';
    return heading + `<tr class="project-entry${cl.some(w => w.lock) ? ' alert' : ''}" ${grouped && collapsedPipelines.has(category) ? 'hidden' : ''} data-pipeline="${esc(category)}" data-status="${esc(statusOf(r))}"><td><button type="button" class="project-title" data-proj-details="${index}">${esc(r.name)}</button></td><td class="project-pipeline">${esc(pipelineLabels[category])}</td><td>${statusOf(r) === 'unclassified' ? '<span class="muted" title="Статус не указан в реестре">—</span>' : `<span class="pill">${esc(statusLabel(r))}</span>`}${occupancy ? ` <span class="pill ${cl.some(w => w.lock) ? 'bad' : ''}" title="${esc(cl.map(w=>w.agent).join(', '))}">${occupancy}</span>` : ''}</td><td class="project-row-actions">${studioKey(r) ? `<button type="button" class="ghost" data-proj-studio="${esc(studioKey(r))}">Студия</button> ` : ''}${r.local_path && /^E:[\\/]projects[\\/]/i.test(r.local_path) ? `<button type="button" class="ghost" data-file-browser-open data-file-browser-start="${esc(r.local_path.replace(/^E:[\\/]projects[\\/]/i,'').replaceAll('\\','/'))}">Файлы</button>` : ''}</td></tr>`;
  }).join('');
  return `<section id="projects-panel"><div class="board-intro project-intro"><span class="note">${shown.length} из ${candidates.length} проектов</span>
      <span><button type="button" class="ghost" data-proj-new-card>Создать карточку</button></span></div>
    ${data.workError ? `<p class="err">NameNode недоступен: ${esc(data.workError)}. Показан только каталог.</p>` : ''}${lockWarnings}
    <div class="board-toolbar project-toolbar"><label>Раздел<select id="project-filter">${Object.entries(labels).map(([k, v]) => `<option value="${k}" ${k === group ? 'selected' : ''}>${v}</option>`).join('')}</select></label>
      <label>Пайплайн<select id="project-pipeline"><option value="all">Все пайплайны</option>${Object.entries(pipelineLabels).filter(([k]) => candidates.some(r=>pipelineOf(r)===k)).map(([k,v])=>`<option value="${k}" ${pipeline===k?'selected':''}>${v}</option>`).join('')}</select></label>
      <label>Статус<select id="project-status"><option value="all">Все статусы</option>${[...new Set(candidates.map(statusOf))].sort((a,b)=>(statusLabels[a]||a).localeCompare(statusLabels[b]||b,'ru')).map(k=>`<option value="${esc(k)}" ${status===k?'selected':''}>${esc(statusLabels[k]||k)}</option>`).join('')}</select></label>
      <label class="project-search-field">Поиск<input id="project-search" value="${esc(query)}" placeholder="Название проекта…"></label>
      <label>Вид<select id="project-grouping"><option value="pipeline" ${grouped?'selected':''}>По пайплайнам</option><option value="list" ${!grouped?'selected':''}>Общий список</option></select></label>
      ${query || pipeline!=='all' || status!=='all' ? '<button type="button" class="ghost" data-proj-reset>Сбросить</button>' : ''}</div>
    ${data.refresh_error ? `<p class="err">Обновление каталога: ${esc(data.refresh_error)}</p>` : ''}
    <div class="table-wrap"><table class="projects-table"><thead><tr><th>Проект</th><th>Пайплайн</th><th>Статус</th><th>Действия</th></tr></thead><tbody>${projectRows || '<tr><td colspan="4" class="note">Ничего не найдено. Измените или сбросьте фильтры.</td></tr>'}</tbody></table></div>
    <details class="proj-section project-occupancy"><summary>Занято сейчас: ${busy.length} · Блокировок: ${lockRows.length}</summary>${busyTable}<p class="note">Занятость показывает назначенную работу, а не запущенный процесс. Личная блокировка запрещает агентам менять проект до её снятия.</p></details>
    <details class="proj-section"><summary>Проектные сессии</summary>${renderProjectSessions(data.sessions)}</details>
    <details class="proj-section project-catalog-info"><summary>О каталоге${data.refreshing ? ' · обновляется' : ''}</summary><p class="note">Снимок: ${esc(date(Number(data.generated_at)))}</p>${(data.warnings||[]).map(w=>`<p class="note">${esc(w)}</p>`).join('')}</details></section>`;
}

function filterProjects(focusId) {
  const previous = document.getElementById(focusId), position = previous?.selectionStart;
  document.querySelector('#projects-panel').outerHTML = renderProjects(lastData);
  applyDisclosure(document.querySelector('#view'), 'projects');
  const current = document.getElementById(focusId);
  current?.focus();
  if (typeof position === 'number' && current?.setSelectionRange) current.setSelectionRange(position, position);
}

function openProject(index) {
  const row = lastData?.rows?.[Number(index)];
  if (!row) return;
  const claims = claimsFor(row, lastData.work || []);
  dialog(row.name, `<p>${esc(pipelineLabels[pipelineOf(row)])} · ${esc(statusLabel(row))}</p>
    <div class="actions proj-files">${actions(row, claims)}</div>
    <dl class="project-overview"><dt>Папка</dt><dd>${esc(row.local_path || row.path || 'Не указана')}</dd><dt>Занятость</dt><dd>${claimCell(claims)}</dd></dl>
    <details class="proj-section"><summary>Технические сведения и история переноса</summary><p>Статус: ${esc(row.status)}</p><p>Запись: ${esc(row.key)}</p><pre>${esc(row.detail || 'Нет дополнительных сведений')}</pre></details>`, true);
}

// ---------- dialogs ----------

function dialog(title, html, wide) {
  let d = document.querySelector('#proj-dialog');
  if (!d) { d = document.createElement('dialog'); d.id = 'proj-dialog'; document.body.append(d); }
  d.classList.toggle('wide', !!wide);
  d.innerHTML = `<div class="board-dialog-head"><h2>${esc(title)}</h2><button type="button" class="ghost" data-proj-close>✕</button></div>${html}<p id="proj-error" class="err"></p>`;
  if (!d.open) d.showModal();
  return d;
}
const fail = msg => { const t = document.querySelector('#proj-error'); if (t) t.textContent = msg; else alert(msg); };

async function openCard(id) {
  const c = await request(`/api/namenode/card/${encodeURIComponent(id)}`);
  const meta = c.meta || {};
  const metaRows = Object.entries(meta).filter(([k]) => k !== 'id').map(([k, v]) => `<tr><td class="note">${esc(k)}</td><td>${esc(v)}</td></tr>`).join('');
  const work = (c.work || []).map(w => `<li>${esc(w)}</li>`).join('');
  const sections = (c.sections || []).map((s, i) => `<details class="proj-section"${i < 2 ? ' open' : ''}><summary>${esc(s.title)}</summary>
      <textarea rows="${Math.min(14, Math.max(3, s.text.split('\n').length + 1))}" data-section-text="${esc(s.title)}">${esc(s.text)}</textarea>
      <div class="actions"><button type="button" data-proj-save-section="${esc(s.title)}">Сохранить раздел</button></div></details>`).join('');
  dialog(meta.title || id, `
    <p class="note">${esc(id)} · ${esc(meta.type || '')} · ${esc(meta.status || '')} · обновлено ${esc(meta.updated || '—')}${c.locked ? ' · <span class="pill bad">🔒 заблокировано вами</span>' : ''}</p>
    <div id="proj-card" data-id="${esc(id)}" data-updated="${esc(meta.updated || '')}">
    <details class="proj-section"><summary>Мета (${Object.keys(meta).length - 1}) и кто занял</summary><table class="proj-meta"><tbody>${metaRows}</tbody></table>
      <div class="board-form-row"><label>Заголовок<input id="proj-meta-title" value="${esc(meta.title || '')}"></label><label>Статус<input id="proj-meta-status" value="${esc(meta.status || '')}"></label></div>
      <div class="actions"><button type="button" data-proj-save-meta>Сохранить мету</button></div>
      ${work ? `<p><b>Занято:</b></p><ul>${work}</ul>` : '<p class="note">Карточка никем не занята.</p>'}</details>
    ${c.head ? `<pre>${esc(c.head)}</pre>` : ''}
    ${sections}
    <details class="proj-section"><summary>＋ Новый раздел</summary><div class="board-form-row"><label>Название<input id="proj-new-section" placeholder="например, Текущее состояние"></label></div>
      <textarea rows="4" id="proj-new-text"></textarea><div class="actions"><button type="button" data-proj-add-section>Добавить раздел</button></div></details>
    <details class="proj-section"><summary>Журнал (${(c.recent_journal || []).length})</summary><pre>${esc((c.recent_journal || []).join('\n') || 'пусто')}</pre></details>
    <label class="proj-force"><input type="checkbox" id="proj-force"> Принудительно (карточка занята другим агентом — согласуйте с ним)</label>
    <p class="note">Правки пишутся в NameNode от имени <code>operator:web</code> с проверкой, что карточку никто не изменил после открытия.</p></div>`, true);
}

async function saveSection(section, text) {
  const box = document.querySelector('#proj-card');
  const r = await request(`/api/namenode/card/${encodeURIComponent(box.dataset.id)}/section`, {
    section, text, reason: 'правка из Pipeline Web', expect_updated: box.dataset.updated || null,
    force: document.querySelector('#proj-force')?.checked || false,
  });
  box.dataset.updated = r.updated || '';
  return r;
}

async function openFiles(folder) {
  const list = await request(`/api/projects/files?folder=${encodeURIComponent(folder)}`);
  const buttons = list.files.map(f => `<button type="button" class="ghost" data-proj-open-file="${esc(f.path)}">${esc(f.name)} <small class="note">${esc(f.mtime)}</small></button>`).join(' ');
  dialog('Файлы проекта', `<p class="note">${esc(list.folder)}</p><div class="actions proj-files">${buttons || '<span class="note">Текстовых файлов нет.</span>'}
      ${list.can_create ? `<button type="button" data-proj-open-file="${esc(list.folder.replace(/[\\/]$/, ''))}\\project.yaml" data-template="1">＋ project.yaml</button>` : ''}</div>
    <div id="proj-editor"></div>`, true);
}

const TEMPLATE = (folder) => `# project.yaml — паспорт проекта (workspace/projects\\<type>\\<project>)
name: ${folder.split(/[\\/]/).pop()}
type: ${(folder.match(/projects[\\/]([^\\/]+)/) || [])[1] || 'video'}
client: ''
description: ''
status: active
pipelines: []
namenode: []
files: []
changelog:
  - ${new Date().toISOString().slice(0, 10)}: создан из Pipeline Web
`;

async function openFile(path, template) {
  const f = await request(`/api/projects/file?path=${encodeURIComponent(path)}`);
  const text = f.exists ? f.text : (template ? TEMPLATE(path.replace(/[\\/][^\\/]+$/, '')) : '');
  const box = document.querySelector('#proj-editor');
  box.innerHTML = `<p><b>${esc(path)}</b>${f.exists ? '' : ' <span class="pill warn">новый файл</span>'}</p>
    <textarea id="proj-file-text" rows="${Math.min(28, Math.max(8, text.split('\n').length + 2))}" spellcheck="false">${esc(text)}</textarea>
    <div class="actions"><button type="button" data-proj-save-file="${esc(path)}" data-mtime="${f.mtime || 0}">Сохранить</button><span class="note">Перед записью делается копия в PipelineWeb/state/project-file-backups; YAML и JSON проверяются на синтаксис.</span></div>`;
}

function newCardForm() {
  const body = STANDARD.map(s => `## ${s}\n`).join('\n');
  dialog('Новая карточка NameNode', `<form id="proj-new-card">
    <div class="board-form-row"><label>id (латиница-дефис)<input name="id" required pattern="[a-z0-9][a-z0-9-]+" placeholder="project-example"></label>
      <label>Тип<select name="type">${TYPES.map(t => `<option value="${t}">${t}</option>`).join('')}</select></label></div>
    <div class="board-form-row"><label>Заголовок<input name="title" required></label><label>Статус<input name="status" value="active"></label></div>
    <div class="board-form-row"><label>canonical (host:path)<input name="canonical" placeholder="Local node workspace/projects\\video\\..."></label><label>Репозиторий<input name="repo" placeholder="—"></label></div>
    <label>Тело (стандартные разделы обязательны)<textarea name="body" rows="14">${esc(body)}</textarea></label>
    <div class="actions"><button type="submit">Создать</button></div></form>`, true);
}

export function initProjects(refresh) {
  redraw = refresh;
  document.addEventListener('change', e => {
    if (e.target.id === 'project-filter') { group = e.target.value; pipeline = 'all'; status = 'all'; }
    else if (e.target.id === 'project-pipeline') pipeline = e.target.value;
    else if (e.target.id === 'project-status') status = e.target.value;
    else if (e.target.id === 'project-grouping') grouped = e.target.value === 'pipeline';
    else return;
    filterProjects(e.target.id);
  });
  document.addEventListener('input', e => {
    if (e.target.id === 'project-search') { query = e.target.value; clearTimeout(initProjects.t); initProjects.t = setTimeout(()=>{ if(document.querySelector('#projects-panel')) filterProjects('project-search'); }, 180); }
  });
  document.addEventListener('submit', async e => {
    const f = e.target; if (f.id !== 'proj-new-card') return;
    e.preventDefault();
    const d = Object.fromEntries(new FormData(f));
    try {
      await request('/api/namenode/card', {meta: {id: d.id, type: d.type, title: d.title, status: d.status, canonical: d.canonical, repo: d.repo}, body: d.body, reason: 'создано из Pipeline Web'});
      document.querySelector('#proj-dialog').close(); redraw();
    } catch (err) { fail(err.message); }
  });
  document.addEventListener('click', async e => {
    const b = e.target.closest('button'); if (!b) return;
    const ds = b.dataset;
    try {
      if (b.hasAttribute('data-proj-close')) document.querySelector('#proj-dialog')?.close();
      else if (ds.projectGroup) { collapsedPipelines.has(ds.projectGroup) ? collapsedPipelines.delete(ds.projectGroup) : collapsedPipelines.add(ds.projectGroup); saveGroups(); filterProjects('project-group-' + ds.projectGroup); }
      else if (b.hasAttribute('data-proj-details')) openProject(ds.projDetails);
      else if (ds.projStudio) { document.querySelector('#proj-dialog')?.close(); location.hash = '#studio/' + ds.projStudio.split('/').map(encodeURIComponent).join('/'); }
      else if (b.hasAttribute('data-proj-reports')) await openReportLinks({project:lastData?.rows?.find(row => row.key === ds.projReports)});
      else if (b.hasAttribute('data-proj-reset')) { query = ''; pipeline = status = 'all'; filterProjects('project-search'); }
      else if (b.hasAttribute('data-proj-new-card')) newCardForm();
      else if (ds.projCard) await openCard(ds.projCard);
      else if (ds.projFiles) await openFiles(ds.projFiles);
      else if (ds.projOpenFile) await openFile(ds.projOpenFile, !!ds.template);
      else if (ds.projSaveFile) {
        b.disabled = true;
        const r = await request('/api/projects/file', {path: ds.projSaveFile, text: document.querySelector('#proj-file-text').value, expect_mtime: Number(ds.mtime) || null});
        ds.mtime = r.mtime; b.textContent = 'Сохранено'; setTimeout(() => { b.textContent = 'Сохранить'; b.disabled = false; }, 1200);
        fail('');
      }
      else if (ds.projSaveSection) {
        b.disabled = true;
        await saveSection(ds.projSaveSection, document.querySelector(`[data-section-text="${CSS.escape(ds.projSaveSection)}"]`).value);
        b.textContent = 'Сохранено'; setTimeout(() => { b.textContent = 'Сохранить раздел'; b.disabled = false; }, 1200); fail('');
      }
      else if (b.hasAttribute('data-proj-add-section')) {
        const name = document.querySelector('#proj-new-section').value.trim(); if (!name) return fail('Введите название раздела');
        await saveSection(name, document.querySelector('#proj-new-text').value);
        await openCard(document.querySelector('#proj-card').dataset.id);
      }
      else if (b.hasAttribute('data-proj-save-meta')) {
        const box = document.querySelector('#proj-card');
        const r = await request(`/api/namenode/card/${encodeURIComponent(box.dataset.id)}/section`, {
          section: 'Ревью', text: null, reason: 'мета из Pipeline Web', expect_updated: box.dataset.updated || null,
          force: document.querySelector('#proj-force')?.checked || false,
          meta: {title: document.querySelector('#proj-meta-title').value, status: document.querySelector('#proj-meta-status').value},
        });
        box.dataset.updated = r.updated || ''; await openCard(box.dataset.id);
      }
      else if (ds.projLock) {
        const d = dialog(`Заблокировать «${ds.name || ds.projLock}»`, `<p>Карточка <code>${esc(ds.projLock)}</code> получит claim <code>operator:lock</code> на 72 ч (продлевается, пока блокировка не снята). Агенты не будут править проект.</p>
          <label>Причина<input id="proj-lock-reason" placeholder="например, правлю монтаж сам"></label>
          <label class="proj-force"><input type="checkbox" id="proj-lock-force"> Принудительно, даже если карточку занял агент</label>
          <div class="actions"><button type="button" data-proj-lock-go="${esc(ds.projLock)}">Заблокировать</button></div>`);
        d.querySelector('#proj-lock-reason').focus();
      }
      else if (ds.projLockGo) {
        b.disabled = true;
        await request('/api/projects/lock', {card: ds.projLockGo, reason: document.querySelector('#proj-lock-reason').value, force: document.querySelector('#proj-lock-force').checked});
        document.querySelector('#proj-dialog').close(); redraw();
      }
      else if (ds.projUnlock) {
        b.disabled = true;
        await request('/api/projects/unlock', {card: ds.projUnlock});
        document.querySelector('#proj-dialog')?.close(); redraw();
      }
    } catch (err) { fail(err.message); b.disabled = false; }
  });
}
