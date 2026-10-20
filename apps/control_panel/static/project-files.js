// Scoped project viewer and file manager. Writes only in «Проекты» (project_files_actions.py): upload, rename/move,
// quarantine instead of delete, folder ZIP, Assistant delivery; every action goes to the panel journal.
import { openReportLinks, deliveryReceiptHTML } from './report-links.js';
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const base = '/api/project-browser';
const url = (route, root, path, extra = '') => `${base}/${route}?root=${encodeURIComponent(root)}&path=${encodeURIComponent(path)}${extra}`;
const api = async (address, options) => { const r = await fetch(address, options); const d = await r.json(); if (!r.ok) throw new Error(typeof d.detail === 'string' ? d.detail : r.statusText); return d; };
const date = t => Number.isFinite(t) ? new Date(t * 1000).toLocaleString('ru-RU') : '—';
const size = n => n == null ? 'Папка' : n >= 1073741824 ? `${(n / 1073741824).toFixed(1)} ГБ` : n >= 1048576 ? `${(n / 1048576).toFixed(1)} МБ` : `${Math.ceil(n / 1024)} КБ`;
const labels = {directory:'Папки',image:'Изображения',video:'Видео',audio:'Аудио',pdf:'PDF',document:'Документы',table:'Таблицы',slides:'Презентации',model:'3D',design:'PSD / AI',text:'Текст',download:'Другие'};
const symbols = {directory:'Папка',image:'IMG',video:'VIDEO',audio:'AUDIO',pdf:'PDF',document:'DOC',table:'XLS',slides:'PPT',model:'3D',design:'DESIGN',text:'TXT',download:'Файл'};
const eventLabel = {create:'Создано',delete:'Удалено',modify:'Изменено',rename:'Переименовано / перемещено',rename_from:'Прежнее имя (пара не получена)',rename_to:'Новое имя (пара не получена)',gap:'Пропуск истории',watch_start:'Наблюдение началось',watch_stop:'Наблюдение остановлено'};
const reasons = {panel_not_running:'Панель не работала; события за этот период неизвестны',history_begins_here:'Начало истории; прежние события неизвестны',notification_overflow:'Переполнение буфера Windows; часть событий потеряна',invalid_notification:'Неполное уведомление Windows',watcher_error:'Ошибка наблюдения',journal_unreadable:'Предыдущий журнал не удалось прочитать',shutdown:'Панель остановлена',error:'Ошибка наблюдения'};
let current = null, rootList = [], listTicket = 0, previewTicket = 0, selected = null, previewData = null;
let deep = false, mode = 'list', query = '', kind = '', sort = 'name', direction = 'asc', searchTimer, initialized = false, disposeModel = null;
let preferences = {}; try {preferences=JSON.parse(localStorage.getItem('project-browser-preferences') || '{}');mode=preferences.mode==='grid'?'grid':'list';}catch{}
const remember = () => {try{localStorage.setItem('project-browser-preferences',JSON.stringify(preferences));}catch{}};
const $ = id => document.getElementById(id);
const post = (route, body) => api(`${base}/${route}`, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
const writable = () => current?.root.id === 'projects';
const canDeliverPreview = item => /\.(jpe?g|png|webp|gif|mp4|mov|mp3|wav|flac)$/i.test(item.name);
const actionLabel = {upload:'Загружено',zip:'Скачан ZIP',mkdir:'Создана папка',rename:'Переименовано',move:'Перенесено',trash:'В карантин',restore:'Восстановлено',deliver:'Запрошена доставка в Telegram'};

function history(data) {
  const status = (data.watchers || []).map(w => ({watching:'Работает',starting:'Запускается',stopped:'Остановлено',error:'Ошибка',shutdown_pending:'Останавливается'}[w.status] || w.status)).join(', ') || 'Наблюдение ещё не запущено';
  return `<p><strong>Наблюдение: ${esc(status)}</strong></p><p class="note">${esc(data.history_note)}</p>${(data.events || []).slice().reverse().slice(0,40).map(e=>`<p><small>${date(e.at)}</small> · ${esc(eventLabel[e.action] || e.action)}<br>${e.action==='rename'?`${esc(e.from)} → ${esc(e.to)}`:esc(e.path || reasons[e.reason] || '')}</p>`).join('') || '<p>Событий пока нет.</p>'}`;
}
function styles() {
  if ($('project-browser-style')) return;
  const s = document.createElement('style'); s.id = 'project-browser-style';
  s.textContent = `
  #project-browser-dialog{width:min(1480px,96vw);max-width:96vw;height:92vh;max-height:92vh;padding:20px;overflow:hidden;box-sizing:border-box;background:var(--bg);color:var(--text)}
  #project-browser-dialog[open]{display:flex;flex-direction:column;gap:12px}
  #project-browser-dialog *{box-sizing:border-box}
  #project-browser-dialog h2,#project-browser-dialog h3,#project-browser-dialog p{margin:0}
  #project-browser-dialog .pf-head,#project-browser-dialog .pf-tools,#project-browser-dialog .pf-crumbs,#project-browser-dialog .pf-actions{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
  #project-browser-dialog .pf-head{justify-content:space-between}
  #project-browser-dialog .pf-head h2{font-size:21px}
  #project-browser-dialog .pf-tools label{display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--muted)}
  #project-browser-dialog .pf-tools input,#project-browser-dialog .pf-tools select{margin:0;min-height:36px}
  #project-browser-dialog .pf-search{flex:1;min-width:170px}
  #project-browser-dialog .pf-search input{width:100%}
  #project-browser-dialog .pf-advanced>div{display:flex;gap:10px;flex-wrap:wrap;margin-top:8px}
  #project-browser-dialog summary{cursor:pointer;color:var(--muted);font-size:12px}
  #project-browser-dialog .pf-crumbs{gap:2px;min-height:32px;overflow-wrap:anywhere;flex-direction:row;justify-content:flex-start}
  #project-browser-dialog .pf-crumbs button{padding:4px 7px;font-size:13px}
  #project-browser-dialog .pf-split{display:grid;grid-template-columns:minmax(300px,38%) minmax(0,1fr);gap:16px;flex:1;min-height:0}
  #project-browser-dialog .pf-library{display:flex;flex-direction:column;min-height:0;min-width:0;border-right:1px solid var(--line);padding-right:16px}
  #project-browser-dialog .pf-library-head{display:flex;flex-wrap:wrap;justify-content:space-between;align-items:center;margin-bottom:8px;gap:8px}#project-browser-dialog #file-browser-count{flex:1 1 160px;min-width:140px}
  #project-browser-dialog .pf-modes{display:flex;gap:4px}
  #project-browser-dialog button[aria-pressed=true]{color:var(--accent);border:1px solid var(--accent);background:var(--panel2)}
  #project-browser-dialog .pf-files{overflow:auto;min-height:0;flex:1;padding:2px}
  #project-browser-dialog .pf-file{display:grid;grid-template-columns:38px minmax(0,1fr);gap:10px;width:100%;padding:10px;text-align:left;color:var(--text);background:transparent;border:1px solid transparent;border-radius:7px;align-items:center;font:inherit}
  #project-browser-dialog .pf-file:hover{background:var(--panel2)}
  #project-browser-dialog .pf-file[aria-pressed=true]{border-color:var(--accent);background:var(--panel2)}
  #project-browser-dialog .pf-icon{display:flex;align-items:center;justify-content:center;background:var(--panel2);color:var(--muted);font-size:10px;min-height:38px;border-radius:4px;overflow:hidden}
  #project-browser-dialog .pf-icon img{width:100%;height:38px;object-fit:cover}
  #project-browser-dialog .pf-name{display:block;overflow-wrap:anywhere;font-size:13px;line-height:1.4}
  #project-browser-dialog .pf-meta{display:block;color:var(--muted);font-size:11px;margin-top:4px;line-height:1.5}
  #project-browser-dialog .pf-tagline{display:block;color:var(--accent);font-size:11px;margin-top:3px;overflow-wrap:anywhere}
  #project-browser-dialog .pf-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(132px,1fr));align-content:start;gap:8px}
  #project-browser-dialog .pf-grid .pf-file{display:flex;flex-direction:column;align-items:stretch;gap:8px;background:var(--panel);padding:8px}
  #project-browser-dialog .pf-grid .pf-icon{height:90px;font-size:17px}
  #project-browser-dialog .pf-grid .pf-icon img{height:90px;object-fit:contain}
  #project-browser-dialog .pf-preview{min-width:0;overflow:auto;display:flex;flex-direction:column;gap:14px;padding:2px 2px 16px}
  #project-browser-dialog .pf-preview h3{font-size:18px;overflow-wrap:anywhere}
  #project-browser-dialog .pf-canvas{min-height:340px;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:16px;overflow:auto;display:flex;align-items:center;justify-content:center}
  #project-browser-dialog .pf-canvas>img,#project-browser-dialog .pf-canvas>video{display:block;max-width:100%;max-height:60vh;object-fit:contain}
  #project-browser-dialog .pf-canvas>iframe{width:100%;height:60vh;border:0;background:white}
  #project-browser-dialog .pf-canvas>audio{width:100%}
  #project-browser-dialog .pf-model{display:block;height:52vh;min-height:320px;padding:0;position:relative;overflow:hidden}
  #project-browser-dialog .pf-model canvas{width:100%;height:100%;display:block;touch-action:none}
  #project-browser-dialog .pf-canvas pre{width:100%;margin:0;white-space:pre-wrap;overflow-wrap:anywhere;align-self:flex-start;font-size:13px}
  #project-browser-dialog .pf-empty{padding:40px 20px;color:var(--muted);text-align:center;line-height:1.7}
  #project-browser-dialog .pf-empty strong{display:block;color:var(--text);font-size:18px;font-weight:500}
  #project-browser-dialog .pf-doc{display:block;color:var(--doc-text);background:var(--doc-bg);padding:28px;line-height:1.65;min-height:340px}
  #project-browser-dialog .pf-doc p{margin:0 0 12px;white-space:pre-wrap}
  #project-browser-dialog .pf-doc table{border-collapse:collapse;width:100%;font-size:12px}
  #project-browser-dialog .pf-doc td{border:1px solid var(--doc-line);padding:7px;white-space:pre-wrap;min-width:80px;max-width:480px;overflow-wrap:anywhere;color:var(--doc-text);background:var(--doc-bg)}
  #project-browser-dialog .pf-doc tr:first-child td{background:var(--doc-head);font-weight:600}
  #project-browser-dialog .pf-sheet{overflow:auto;max-height:57vh;width:100%}
  #project-browser-dialog .pf-slide{border-bottom:1px solid var(--doc-line);padding:16px 0}
  #project-browser-dialog .pf-slide h4{margin:0 0 12px;color:var(--doc-sub)}
  #project-browser-dialog .pf-tags{display:flex;gap:8px;align-items:end;flex-wrap:wrap}
  #project-browser-dialog .pf-tags label{flex:1;min-width:150px;font-size:12px;color:var(--muted)}
  #project-browser-dialog .pf-tags input{width:100%;margin:5px 0 0}
  #project-browser-dialog .pf-history{max-height:25vh;overflow:auto;border-top:1px solid var(--line);padding-top:8px;font-size:12px}
  #project-browser-dialog .pf-history p{margin:8px 0;overflow-wrap:anywhere}
  #project-browser-dialog .pf-page{display:flex;justify-content:space-between;gap:8px;padding-top:8px}
  #project-browser-dialog .pf-muted{font-size:12px;color:var(--muted);overflow-wrap:anywhere}
  #project-browser-dialog button:focus-visible,#project-browser-dialog a:focus-visible,#project-browser-dialog [tabindex]:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
  /* UX-20: actions look the same whether they are links or buttons; the deep-search toggle uses the accent. */
  #project-browser-dialog .pf-actions a{display:inline-flex;align-items:center;min-height:34px;padding:6px 12px;border:1px solid var(--line);border-radius:10px;background:var(--panel2);color:var(--text);text-decoration:none;font-size:13px;cursor:pointer}
  #project-browser-dialog .pf-actions a:hover{border-color:var(--accent)}
  #project-browser-dialog .pf-deep input{width:18px;height:18px;margin:0;accent-color:var(--accent)}#project-browser-dialog .pf-deep span{padding:0 10px;border:1px solid var(--line);border-radius:10px;background:var(--panel2);cursor:pointer}
  #project-browser-dialog .pf-deep{justify-content:flex-end}#project-browser-dialog .pf-deep span{display:flex;align-items:center;gap:6px;min-height:36px;color:var(--text);font-size:13px}
  #project-browser-dialog .pf-menu{position:relative}#project-browser-dialog .pf-menu summary{display:flex;align-items:center;height:100%;padding:8px 14px;border:1px solid var(--line);border-radius:10px;background:var(--panel2);font-weight:600;color:var(--text);list-style:none;cursor:pointer}#project-browser-dialog .pf-menu summary::after{content:' ▾';white-space:pre;color:var(--muted)}#project-browser-dialog .pf-menu summary::-webkit-details-marker{display:none}
  #project-browser-dialog .pf-menu-list{position:absolute;right:0;top:calc(100% + 4px);z-index:5;display:flex;flex-direction:column;min-width:200px;background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:6px;box-shadow:0 8px 24px rgba(0,0,0,.35)}
  #project-browser-dialog .pf-menu-list>*{text-align:left;padding:8px 10px;font-size:13px}
  #project-browser-dialog .pf-files.pf-drop{outline:2px dashed var(--accent);outline-offset:-4px}
  #project-browser-dialog .pf-list p{margin:8px 0;font-size:13px;overflow-wrap:anywhere}
  #project-browser-dialog .pf-file-actions summary{font-size:13px}#project-browser-dialog .pf-file-actions .pf-actions{margin-top:8px}
  @media(max-width:760px){#project-browser-dialog{padding:12px;height:96vh;max-height:96vh;overflow:auto}#project-browser-dialog .pf-split{display:flex;flex-direction:column;flex:none}#project-browser-dialog .pf-library{height:36vh;min-height:230px;border-right:0;padding-right:0}#project-browser-dialog .pf-preview{overflow:visible}#project-browser-dialog .pf-canvas{min-height:240px}#project-browser-dialog .pf-tools label{flex:1}#project-browser-dialog .pf-search{flex-basis:100%}}
  `; document.head.append(s);
}
function dialog() {
  styles(); let d = $('project-browser-dialog');
  if (!d) { d = document.createElement('dialog'); d.id = 'project-browser-dialog'; d.setAttribute('aria-labelledby','pf-title'); document.body.append(d); }
  if (!d.open) d.showModal(); return d;
}
function error(e) { const box = $('project-browser-error'); if (box) box.textContent = e.message || String(e); }
function stopMedia() { $('file-browser-preview')?.querySelectorAll('video,audio').forEach(x=>x.pause());if(disposeModel){disposeModel();disposeModel=null;} }
function shell(d) {
  d.innerHTML = `<div class="pf-head"><h2 id="pf-title">Файлы и результаты</h2><button class="ghost" data-file-browser-close aria-label="Закрыть просмотр файлов">✕</button></div>
    <div class="pf-tools"><label>Источник<select id="file-browser-root"></select></label><label class="pf-search">Поиск<input id="file-browser-filter" type="search" placeholder="Имя файла или тег" value="${esc(query)}"></label><label class="pf-deep"><span><input type="checkbox" id="file-browser-deep" ${deep?'checked':''}> во вложенных</span></label>
    <details class="pf-advanced" data-pf-detail="options" ${preferences.options?'open':''}><summary>Фильтры и порядок</summary><div><label>Тип<select id="file-browser-kind"><option value="">Все типы</option>${Object.entries(labels).map(([k,v])=>`<option value="${k}" ${kind===k?'selected':''}>${v}</option>`).join('')}</select></label>
    <label>Сортировка<select id="file-browser-sort">${[['name','По имени'],['type','По типу'],['modified','По дате'],['size','По размеру']].map(([k,v])=>`<option value="${k}" ${sort===k?'selected':''}>${v}</option>`).join('')}</select></label>
    <button class="ghost" id="file-browser-direction" title="Изменить порядок сортировки">${direction==='asc'?'↑ По возрастанию':'↓ По убыванию'}</button></div></details><button class="ghost" data-file-browser-refresh>Обновить</button></div>
    <nav class="pf-crumbs" id="file-browser-crumbs" aria-label="Путь к папке"></nav>
    <div class="pf-split"><section class="pf-library" aria-label="Файлы в папке"><div class="pf-library-head"><span class="pf-muted" id="file-browser-count">Открываю папку…</span><div class="pf-modes"><button class="ghost" data-file-browser-upload hidden title="Или перетащите файлы в список">Загрузить</button><input type="file" id="file-browser-upload-input" multiple hidden><details class="pf-menu"><summary>Папка</summary><div class="pf-menu-list"><a id="file-browser-zip">Скачать папку ZIP</a><button class="ghost" data-fm="mkdir">Новая папка</button><button class="ghost" data-fm="rename-folder">Переименовать папку</button><button class="ghost" data-fm="move-folder">Перенести папку</button><button class="ghost" data-fm="trash-folder">Папку в карантин</button><button class="ghost" data-fm="trash-list">Карантин</button><button class="ghost" data-fm="journal">Журнал действий</button></div></details></div><div class="pf-modes" aria-label="Вид файлов"><button class="ghost" data-file-browser-mode="list" aria-pressed="${mode==='list'}">Список</button><button class="ghost" data-file-browser-mode="grid" aria-pressed="${mode==='grid'}">Сетка</button></div></div>
    <div id="file-browser-rows" class="pf-files"></div><div id="file-browser-pages" class="pf-page"></div>
    <details class="pf-history" data-pf-detail="history" ${preferences.history?'open':''}><summary>История изменений</summary><div id="file-browser-history"></div></details></section>
    <section id="file-browser-preview" class="pf-preview" aria-label="Предпросмотр" aria-live="polite"><div class="pf-canvas pf-empty"><div><strong>Выберите файл</strong>Здесь откроется изображение, видео или содержимое документа.</div></div></section></div>
    <details data-pf-detail="reports" ${preferences.reports?'open':''}><summary>Путь и отчёты</summary><div class="pf-actions"><a id="file-browser-report">Скачать сводку</a><a href="${base}/report-template">Шаблон отчёта</a><span id="file-browser-folder" class="pf-muted"></span></div></details><p id="project-browser-error" class="err" role="status"></p>`;
}
function renderFiles() {
  if (!current) return;
  const box = $('file-browser-rows'); box.className = `pf-files ${mode==='grid'?'pf-grid':''}`;
  box.innerHTML = current.entries.map((x,i)=>{
    const thumbnail = x.kind==='image' && !/\.(psd|psb|ai|eps)$/i.test(x.name);
    return `<button class="pf-file" ${x.directory?`data-file-browser-path="${esc(x.relative)}"`:`data-file-browser-preview="${i}" aria-pressed="${selected?.relative===x.relative}"`} title="${esc(x.name)}">
    <span class="pf-icon">${thumbnail?`<img loading="lazy" src="${esc(url('media',current.root.id,x.relative))}" alt="">`:esc(symbols[x.kind] || x.name.split('.').pop().toUpperCase().slice(0,5))}</span>
    <span><span class="pf-name">${esc(x.name)}</span><span class="pf-meta">${size(x.size)}${x.directory?'':` · ${esc(x.extension || x.name.split('.').pop())}`}<br>${date(x.modified)}${x.folder!=null?` · в ${esc(x.folder || 'корне')}`:''}</span>${x.tags?.length?`<span class="pf-tagline">${x.tags.map(esc).join(' · ')}</span>`:''}</span></button>`;
  }).join('') || '<p class="pf-empty">Файлов по этому запросу нет. Измените поиск или фильтр.</p>';
  if (current.deep) { $('file-browser-count').textContent = `Найдено: ${current.entries.length}${current.complete?'':' · поиск ограничен, уточните запрос'}`; $('file-browser-pages').innerHTML=''; return; }
  $('file-browser-count').textContent = `${current.entries.length} на странице${Number.isFinite(current.total)?` из ${current.total}`:''}${current.truncated?' · первые 1000 записей':''}`;
  $('file-browser-pages').innerHTML = `${current.offset?`<button class="ghost" data-file-browser-page="${Math.max(0,current.offset-200)}">Назад</button>`:''}${current.next_offset!=null?`<button class="ghost" data-file-browser-page="${current.next_offset}">Дальше</button>`:''}`;
}
async function loadFolder(root, path, offset=0) {
  const ticket = ++listTicket; error('');
  const changed = !current || current.root.id!==root || current.relative!==path;
  if (changed) { ++previewTicket; selected=null; previewData=null; stopMedia(); }
  $('file-browser-count').textContent = 'Открываю папку…';
  const data = await api(url('list',root,path,`&offset=${offset}&search=${encodeURIComponent(deep?'':query)}&kind=${encodeURIComponent(kind)}&sort=${sort}&direction=${direction}`));
  if (deep && query.trim().length>=2) { const found=await api(url('find',root,path,`&q=${encodeURIComponent(query.trim())}`)); data.entries=found.entries.filter(x=>!kind || x.kind===kind); Object.assign(data,{deep:true,complete:found.complete,next_offset:null}); }
  if (ticket!==listTicket || !$('project-browser-dialog')?.open) return;
  current={...data,offset};
  document.querySelector('[data-file-browser-upload]').hidden=!writable();
  document.querySelectorAll('[data-fm]').forEach(x=>{x.hidden=!writable() && !['journal'].includes(x.dataset.fm) || (!path && /folder/.test(x.dataset.fm));});
  $('file-browser-zip').href=url('zip',root,path);
  $('file-browser-root').innerHTML = rootList.map(x=>`<option value="${esc(x.id)}" ${x.id===root?'selected':''}>${esc(x.name)}</option>`).join('');
  const parts=path.split(/[\\/]/).filter(Boolean);
  $('file-browser-crumbs').innerHTML = `<button class="ghost" data-file-browser-path="">${esc(data.root.name || 'Корень')}</button>${parts.map((p,i)=>`<span aria-hidden="true">/</span><button class="ghost" data-file-browser-path="${esc(parts.slice(0,i+1).join('/'))}" ${i===parts.length-1?'aria-current="page"':''}>${esc(p)}</button>`).join('')}`;
  $('file-browser-folder').textContent=data.folder; $('file-browser-report').href=url('report',root,path);
  $('file-browser-history').innerHTML=history(data); renderFiles();
  if (changed) $('file-browser-preview').innerHTML='<div class="pf-canvas pf-empty"><div><strong>Выберите файл</strong>Предпросмотр появится здесь.</div></div>';
}
// W4: offline editors open a project file and save a new version beside it (static/editor.html)
const EDITOR_FOR = [[/\.(png|jpe?g|webp|gif|bmp)$/i, 'minipaint'], [/\.svg$/i, 'svgedit'], [/\.(wav|mp3|ogg|flac|m4a|aac)$/i, 'audiomass']];
function editorLink(root, item) { if (root !== 'projects') return ''; const tool = EDITOR_FOR.find(([re]) => re.test(item.name))?.[1]; return tool ? `<a href="/static/editor.html?tool=${tool}&root=${encodeURIComponent(root)}&path=${encodeURIComponent(item.relative)}" target="_blank" rel="noopener">Открыть в редакторе</a>` : ''; }
export async function openProjectBrowser(root='projects',path='',offset=0) {
  const d=dialog(); stopMedia(); shell(d); current=null; selected=null; ++previewTicket;
  try { if (!rootList.length) rootList=(await api(`${base}/roots`)).roots; await loadFolder(root,path,offset); } catch(e) { error(e); }
}
const table = rows => `<div class="pf-sheet"><table><tbody>${(rows || []).map(row=>`<tr>${row.map(value=>`<td>${esc(value)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
const blocks = rows => (rows || []).map(b=>b.type==='table'?table(b.rows):`<p>${esc(b.text)}</p>`).join('');
function safeMedia(value, fallback) { try { const u=new URL(value || fallback,location.origin); return u.origin===location.origin && u.pathname.startsWith(base+'/')?u.href:fallback; } catch { return fallback; } }
function detailBody(data,src,item) {
  const warnings=(data.warnings || []).map(w=>`<p class="note">${esc(w)}</p>`).join('');
  if(data.kind==='document') return `<div class="pf-canvas pf-doc" tabindex="0">${blocks(data.blocks) || '<p>Текстовое содержимое не найдено.</p>'}</div>${warnings}${data.truncated?'<p class="note">Показана часть документа.</p>':''}`;
  if(data.kind==='table') return `<label>Лист <select id="file-browser-sheet">${(data.sheets || []).map((s,i)=>`<option value="${i}">${esc(s.name)}</option>`).join('')}</select></label><div class="pf-canvas pf-doc" tabindex="0" id="file-browser-sheet-view">${table(data.sheets?.[0]?.rows)}</div>${warnings}${data.truncated?'<p class="note">Показана часть строк и столбцов.</p>':''}`;
  if(data.kind==='slides') return `<div class="pf-canvas pf-doc" tabindex="0">${(data.slides || []).map((s,i)=>`<section class="pf-slide"><h4>Слайд ${s.number || i+1}</h4>${blocks(s.blocks || (s.text || []).map(text=>({type:'paragraph',text})))}</section>`).join('')}</div>${warnings}`;
  if(data.kind==='image') return `<div class="pf-canvas"><img src="${esc(safeMedia(data.image_url,src))}" alt="${esc(item.name)}"></div>${warnings}`;
  if(data.kind==='model' && ['glb','gltf','obj','stl'].includes(data.format)) return `<div id="file-browser-model" class="pf-canvas pf-model" aria-label="3D-модель"></div><p class="note" id="file-browser-model-status">Загружаю 3D-просмотр…</p>${warnings}`;
  return `<div class="pf-canvas pf-empty"><div><strong>${data.kind==='model'?'3D-модель':'Предпросмотр недоступен'}</strong>${esc(data.message || 'Откройте файл в профильной программе. Можно скачать файл или скопировать путь на локальном узле.')}</div></div>${warnings}`;
}
async function preview(index) {
  const item=current?.entries[index]; if(!item || item.directory) return;
  const ticket=++previewTicket, root=current.root.id, container=$('file-browser-preview'), src=url('media',root,item.relative);
  stopMedia(); selected=item; previewData=null; renderFiles();
  $('file-browser-rows').querySelector(`[data-file-browser-preview="${index}"]`)?.focus({preventScroll:true});
  container.innerHTML=`<h3>${esc(item.name)}</h3><p class="pf-muted">${size(item.size)} · ${date(item.modified)}</p><div class="pf-actions"><a href="${esc(url('media',root,item.relative,'&download=true'))}">Скачать оригинал</a>${editorLink(root,item)}<button class="ghost" data-file-browser-copy>Скопировать путь</button></div>
  <div class="pf-actions" aria-label="Отправить в Telegram">${canDeliverPreview(item)?'<button class="ghost" data-fm="deliver-preview" data-mint-send>Отправить превью в Telegram</button>':''}<button class="ghost" data-fm="deliver-file" data-mint-send>${item.size>48*1048576?'Отправить ссылку на оригинал':(['image','video','audio'].includes(item.kind)?'Отправить оригинал':'Отправить файл')} в Telegram</button>${root==='projects' && (/\.html?$/i.test(item.name) || item.size>48*1048576)?`<button class="ghost" data-fm="report-links">${/\.html?$/i.test(item.name)?'Клиентская ссылка на отчёт':'Управление ссылками'}</button>`:''}</div>
  <p class="note">${canDeliverPreview(item)?'Превью — для просмотра в чате. Оригинал — без изменений. ':'Документы отправляются файлом. '}${item.size>48*1048576?'Оригинал больше 48 МБ: отправим ссылку для скачивания без входа. Её можно отозвать в «Отчётах и ссылках» проекта.':''}</p><div id="file-browser-delivery"></div>
  <details class="pf-file-actions" data-pf-detail="fileactions" ${preferences.fileactions?'open':''}><summary>Действия с файлом</summary><div class="pf-actions">${writable()?'<button class="ghost" data-fm="rename">Переименовать</button><button class="ghost" data-fm="move">Перенести</button><button class="ghost" data-fm="trash">В карантин</button>':''}</div></details><div id="file-browser-content"><p class="pf-empty">Открываю предпросмотр…</p></div>
  <details data-pf-detail="tags" ${preferences.tags?'open':''}><summary>Теги${item.tags?.length?` (${item.tags.length})`:''}</summary><form class="pf-tags" id="file-browser-tags"><label>Теги через запятую<input id="file-browser-tag-input" value="${esc((item.tags || []).join(', '))}" placeholder="Например: согласовано, обложка"></label><button type="submit">Сохранить теги</button><span id="file-browser-tag-status" class="pf-muted" role="status"></span></form></details>`;
  if(root==='projects' && item.kind==='video' && /^video\/[A-Za-z0-9][A-Za-z0-9-]+\//.test(norm(item.relative))){
    const parts=norm(item.relative).split('/'), link=document.createElement('a');
    link.href='/static/video-review.html?'+new URLSearchParams({project:parts[1],source:parts.slice(2).join('/')});
    link.textContent='Открыть монтажную';container.querySelector('.pf-actions').append(link);
  }
  let html;
  try {
    if(item.kind==='image' && !/\.(psd|psb|ai|eps)$/i.test(item.name)) html=`<div class="pf-canvas"><img src="${esc(src)}" alt="${esc(item.name)}"></div>`;
    else if(item.kind==='video') html=`<div class="pf-canvas"><video src="${esc(src)}" controls preload="metadata"></video></div><p class="note">Если браузер не поддерживает кодек, скачайте оригинал.</p>`;
    else if(item.kind==='audio') html=`<div class="pf-canvas"><audio src="${esc(src)}" controls preload="metadata"></audio></div>`;
    else if(item.kind==='pdf') html=`<div class="pf-canvas"><iframe src="${esc(src)}" title="${esc(item.name)}"></iframe></div>`;
    else if(item.kind==='text') {const data=await api(url('text',root,item.relative));html=`<div class="pf-canvas"><pre tabindex="0">${esc(data.text)}</pre></div>${data.truncated?'<p class="note">Показаны первые 256 КБ.</p>':''}`;}
    else { const data=await api(url('preview',root,item.relative));if(ticket!==previewTicket)return;previewData=data;html=detailBody(data,src,item); }
    if(ticket===previewTicket && $('file-browser-content')) {$('file-browser-content').innerHTML=html;if(previewData?.kind==='model')await renderModel(previewData,item,ticket);}
  } catch(e) {if(ticket===previewTicket){$('file-browser-content').innerHTML='<p class="pf-empty">Не удалось открыть предпросмотр. Оригинал можно скачать.</p>';error(e);}}
}
async function renderModel(data,item,ticket) {
  const host=$('file-browser-model');if(!host)return;
  if(item.size>64*1024*1024){$('file-browser-model-status').textContent='Модель больше 64 МБ. Для этого файла используйте профильную программу.';return;}
  let renderer, controls, observer, object, manager;
  const dispose=()=>{observer?.disconnect();controls?.dispose();if(object)object.traverse(x=>{x.geometry?.dispose();for(const m of (Array.isArray(x.material)?x.material:[x.material]).filter(Boolean)){for(const value of Object.values(m))if(value?.isTexture)value.dispose();m.dispose();}});renderer?.dispose();renderer?.forceContextLoss();};
  try{
    const vendor='/static/vendor/three-r186/';
    const [T,{OrbitControls}]=await Promise.all([import(vendor+'build/three.module.js'),import(vendor+'examples/jsm/controls/OrbitControls.js')]);
    if(ticket!==previewTicket)return;
    manager=new T.LoadingManager();manager.setURLModifier(value=>{const u=new URL(value,location.origin);if(u.protocol==='blob:' && u.origin===location.origin)return value;if(u.protocol==='data:' && /^(data:application\/octet-stream|data:image\/(png|jpeg|webp));base64,/i.test(value))return value;if(u.origin===location.origin && (u.pathname===base+'/model-data' || u.pathname===base+'/model-resource'))return u.href;throw new Error('Внешние ресурсы модели не загружаются');});
    const source=safeMedia(data.model_url,'');if(!source)throw new Error('Недоступный путь модели');
    const response=await fetch(source);if(!response.ok)throw new Error('Файл модели недоступен');const raw=await response.arrayBuffer();
    if(ticket!==previewTicket)return;
    if(data.format==='glb' || data.format==='gltf'){const {GLTFLoader}=await import(vendor+'examples/jsm/loaders/GLTFLoader.js');object=(await new GLTFLoader(manager).parseAsync(data.format==='gltf'?new TextDecoder().decode(raw):raw,location.origin+'/')).scene;}
    else if(data.format==='obj'){const {OBJLoader}=await import(vendor+'examples/jsm/loaders/OBJLoader.js');object=new OBJLoader(manager).parse(new TextDecoder().decode(raw));}
    else{const {STLLoader}=await import(vendor+'examples/jsm/loaders/STLLoader.js');const geometry=new STLLoader(manager).parse(raw);geometry.computeVertexNormals();object=new T.Mesh(geometry,new T.MeshStandardMaterial({color:0xb9ccd6,roughness:0.7,metalness:0.1}));}
    if(ticket!==previewTicket){dispose();return;}
    renderer=new T.WebGLRenderer({antialias:true,alpha:false});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setClearColor(0x151b20);host.append(renderer.domElement);
    const scene=new T.Scene(),camera=new T.PerspectiveCamera(40,1,0.01,10000);scene.add(object);scene.add(new T.HemisphereLight(0xffffff,0x536777,2));const light=new T.DirectionalLight(0xffffff,3);light.position.set(3,5,4);scene.add(light);
    const bounds=new T.Box3().setFromObject(object),center=bounds.getCenter(new T.Vector3()),extent=bounds.getSize(new T.Vector3()),radius=Math.max(extent.x,extent.y,extent.z);
    if(!Number.isFinite(radius) || radius<=0)throw new Error('В модели не найдена видимая геометрия');
    object.position.sub(center);camera.position.set(radius*1.4,radius*0.9,radius*1.6);camera.near=radius/1000;camera.far=radius*100;camera.updateProjectionMatrix();
    controls=new OrbitControls(camera,renderer.domElement);controls.target.set(0,0,0);controls.enableDamping=false;controls.minDistance=radius*0.02;controls.maxDistance=radius*20;controls.update();
    const draw=()=>renderer.render(scene,camera);controls.addEventListener('change',draw);observer=new ResizeObserver(()=>{const width=host.clientWidth,height=host.clientHeight;if(!width || !height)return;renderer.setSize(width,height,false);camera.aspect=width/height;camera.updateProjectionMatrix();draw();});observer.observe(host);disposeModel=dispose;
    $('file-browser-model-status').textContent='Перетаскивайте для вращения. Колесо — масштаб, правая кнопка — перемещение.';
  }catch(e){dispose();if(ticket===previewTicket && $('file-browser-model-status'))$('file-browser-model-status').textContent='3D-просмотр недоступен: '+e.message+'. Оригинал можно скачать.';}
}
const norm = v => String(v || '').replace(/\\/g,'/');
const parentOf = v => norm(v).split('/').slice(0,-1).join('/');
function pane(html) { stopMedia(); selected=null; ++previewTicket; renderFiles(); $('file-browser-preview').innerHTML=html; }
async function uploadFiles(files) {
  if (!writable() || !files?.length) return;
  const root=current.root.id, path=current.relative, count=$('file-browser-count'), done=[];
  for (const [i,f] of [...files].entries()) {
    await new Promise((resolve,reject)=>{const x=new XMLHttpRequest();
      x.open('PUT',url('upload',root,path,`&name=${encodeURIComponent(f.name)}`));
      x.upload.onprogress=e=>{if(e.lengthComputable)count.textContent=`Загрузка ${i+1}/${files.length}: ${f.name} — ${Math.floor(e.loaded*100/e.total)}%`;};
      x.onload=()=>{let d={};try{d=JSON.parse(x.responseText);}catch{} x.status<300?(done.push(d.name),resolve()):reject(new Error(`${f.name}: ${d.detail || x.statusText}`));};
      x.onerror=()=>reject(new Error(`${f.name}: соединение прервано`)); x.send(f);});
  }
  await loadFolder(root,path); error(''); $('file-browser-count').textContent+=` · загружено: ${done.length}`;
}
async function fileAction(name) {
  const root=current.root.id, item=selected, folder=norm(current.relative);
  if (name==='mkdir') { const n=prompt('Имя новой папки'); if(!n)return; await post('mkdir',{root,path:folder,name:n}); return loadFolder(root,folder); }
  if (name==='rename' || name==='rename-folder') { const target=name==='rename'?norm(item.relative):folder, old=target.split('/').pop(); const n=prompt('Новое имя',old); if(!n || n===old)return; const r=await post('rename',{root,path:target,name:n}); return name==='rename'?loadFolder(root,folder):loadFolder(root,r.path); }
  if (name==='move' || name==='move-folder') { const target=name==='move'?norm(item.relative):folder; const dest=prompt('Перенести в папку внутри «Проекты» (путь от корня, например video/Клиент/finals)',parentOf(target)); if(dest==null || norm(dest)===parentOf(target))return; await post('move',{root,path:target,dest:norm(dest).replace(/^\/+|\/+$/g,'')}); return loadFolder(root,name==='move'?folder:parentOf(target)); }
  if (name==='trash' || name==='trash-folder') { const target=name==='trash'?norm(item.relative):folder; if(!confirm(`Перенести «${target.split('/').pop()}» в карантин? Файл не удаляется, его можно вернуть из меню «Папка → Карантин».`))return; await post('trash',{root,path:target}); return loadFolder(root,name==='trash'?folder:parentOf(target)); }
  if (name==='report-links') return openReportLinks({sourcePath:item.path || `workspace/projects/${item.relative}`});
  if (name==='deliver-preview' || name==='deliver-file') {
    const deliveryMode = name==='deliver-preview' ? 'preview' : 'file', target=$('file-browser-delivery');
    const deliveryLabel = deliveryMode==='preview' ? 'превью' : item.size>48*1048576 ? 'ссылку на оригинал (скачивание без входа, доступ можно отозвать)' : 'оригинал файлом';
    if (!confirm(`Отправить ${deliveryLabel} «${item.name}» в Telegram, в оперативный чат Assistant?`)) return;
    const buttons=[...$('file-browser-preview').querySelectorAll('[data-fm^="deliver-"]')]; buttons.forEach(button=>button.disabled=true);
    target.innerHTML='<p role="status">Оформляю отправку…</p>';
    try { const job=await post('deliver',{root,path:norm(item.relative),mode:deliveryMode}); if(target.isConnected)target.innerHTML=deliveryReceiptHTML(job); }
    catch(err) { if(target.isConnected)target.textContent='Отправка не подтверждена: '+err.message; throw err; }
    finally { buttons.forEach(button=>button.disabled=false); }
    return;
  }
  if (name==='trash-list') { const d=await api(`${base}/trash`); return pane(`<h3>Карантин</h3><p class="pf-muted">Удалённое из панели лежит здесь: ${esc(d.folder)}. Оттуда ничего не стирается автоматически.</p><div class="pf-list">${d.items.map(x=>`<p><strong>${esc(x.name)}</strong> · ${date(x.at)}${x.remote?' · онлайн':''}<br><span class="pf-muted">${esc(x.original)}</span><br><button class="ghost" data-fm-restore="${esc(x.id)}">Вернуть на место</button></p>`).join('') || '<p>Карантин пуст.</p>'}</div>`); }
  if (name==='journal') { const d=await api(`${base}/journal`); return pane(`<h3>Журнал действий</h3><div class="pf-list">${d.items.map(x=>`<p><small>${date(x.at)}${x.remote?' · онлайн':''}</small> · ${esc(actionLabel[x.action] || x.action)}<br><span class="pf-muted">${esc(x.from?`${x.from} → ${x.to}`:x.path)}</span></p>`).join('') || '<p>Действий пока не было.</p>'}</div>`); }
}
export function initProjectBrowser() {
  if(initialized)return; initialized=true; let refreshing=false;
  setInterval(async()=>{const folder=current;if(refreshing || document.hidden || !folder || !$('project-browser-dialog')?.open)return;refreshing=true;
    try{const data=await api(url('events',folder.root.id,folder.relative));if(current===folder && $('project-browser-dialog')?.open)$('file-browser-history').innerHTML=history(data);}catch(e){error(e);}finally{refreshing=false;}
  },5000);
  document.addEventListener('click',async e=>{const b=e.target.closest('button');if(!b)return;
    try{
      if(b.hasAttribute('data-file-browser-close')){++listTicket;++previewTicket;stopMedia();$('project-browser-dialog')?.close();}
      else if(b.hasAttribute('data-file-browser-open'))await openProjectBrowser(b.dataset.fileBrowserRoot || 'projects',b.dataset.fileBrowserStart || '');
      else if(b.hasAttribute('data-file-browser-path'))await loadFolder(current.root.id,b.dataset.fileBrowserPath);
      else if(b.hasAttribute('data-file-browser-preview'))await preview(Number(b.dataset.fileBrowserPreview));
      else if(b.hasAttribute('data-file-browser-page'))await loadFolder(current.root.id,current.relative,Number(b.dataset.fileBrowserPage));
      else if(b.hasAttribute('data-file-browser-refresh'))await loadFolder(current.root.id,current.relative,current.offset);
      else if(b.hasAttribute('data-file-browser-mode')){mode=b.dataset.fileBrowserMode;preferences.mode=mode;remember();document.querySelectorAll('[data-file-browser-mode]').forEach(x=>x.setAttribute('aria-pressed',String(x.dataset.fileBrowserMode===mode)));renderFiles();}
      else if(b.id==='file-browser-direction'){direction=direction==='asc'?'desc':'asc';b.textContent=direction==='asc'?'↑ По возрастанию':'↓ По убыванию';await loadFolder(current.root.id,current.relative);}
      else if(b.hasAttribute('data-file-browser-upload'))$('file-browser-upload-input').click();
      else if(b.dataset.fm){b.closest('details.pf-menu')?.removeAttribute('open');await fileAction(b.dataset.fm);}
      else if(b.dataset.fmRestore){const r=await post('restore',{id:b.dataset.fmRestore});await loadFolder('projects',parentOf(r.path));}
      else if(b.hasAttribute('data-file-browser-copy')){await navigator.clipboard.writeText(selected?.path || '');b.textContent='Путь скопирован';}
    }catch(err){error(err);}
  });
  document.addEventListener('change',async e=>{try{
    if(e.target.id==='file-browser-root')await loadFolder(e.target.value,'');
    else if(e.target.id==='file-browser-deep'){deep=e.target.checked;await loadFolder(current.root.id,current.relative);}
    else if(e.target.id==='file-browser-upload-input'){const files=[...e.target.files];e.target.value='';await uploadFiles(files);}
    else if(e.target.id==='file-browser-kind'){kind=e.target.value;await loadFolder(current.root.id,current.relative);}
    else if(e.target.id==='file-browser-sort'){sort=e.target.value;await loadFolder(current.root.id,current.relative);}
    else if(e.target.id==='file-browser-sheet')$('file-browser-sheet-view').innerHTML=table(previewData?.sheets?.[Number(e.target.value)]?.rows);
  }catch(err){error(err);}});
  document.addEventListener('input',e=>{if(e.target.id==='file-browser-filter'){query=e.target.value;clearTimeout(searchTimer);searchTimer=setTimeout(()=>{if(current && $('project-browser-dialog')?.open)loadFolder(current.root.id,current.relative).catch(error);},250);}});
  document.addEventListener('submit',async e=>{if(e.target.id!=='file-browser-tags')return;e.preventDefault();const item=selected,root=current.root.id, ticket=previewTicket;const tags=$('file-browser-tag-input').value.split(',').map(t=>t.trim()).filter(Boolean);
    try{const data=await api(`${base}/tags`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({root,path:item.relative,tags})});item.tags=data.tags || tags;if(ticket===previewTicket){$('file-browser-tag-status').textContent='Теги сохранены';renderFiles();}}catch(err){error(err);}
  });
  document.addEventListener('dragover',e=>{const box=e.target.closest?.('#file-browser-rows');if(!box || !writable() || !e.dataTransfer?.types?.includes('Files'))return;e.preventDefault();box.classList.add('pf-drop');});
  document.addEventListener('dragleave',e=>{if(e.target.id==='file-browser-rows')e.target.classList.remove('pf-drop');});
  document.addEventListener('drop',e=>{const box=e.target.closest?.('#file-browser-rows');if(!box || !writable())return;e.preventDefault();box.classList.remove('pf-drop');uploadFiles([...e.dataTransfer.files]).catch(error);});
  document.addEventListener('keydown',e=>{if(e.key==='Escape' && $('project-browser-dialog')?.open){++listTicket;++previewTicket;stopMedia();}});
  document.addEventListener('toggle',e=>{if(e.target.dataset?.pfDetail){preferences[e.target.dataset.pfDetail]=e.target.open;remember();}},true);
}
