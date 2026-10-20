// «Быстрые правки» (search across editors, converters and tools + file converters) and «Инструменты» (catalogue).
import { tagClass } from './tags.js';
const esc = (v) => String(v ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const dot = (state) => `<i class="dot ${state}"></i>`;
const pill = (text, state = '') => `<span class="pill ${state}">${esc(text)}</span>`;
const mb = (b) => b > 1048576 ? `${(b / 1048576).toFixed(1)} МБ` : `${Math.round((b || 0) / 1024)} КБ`;
const FMT = { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' };
const toDate = (t) => { if (!t) return null; const n = Number(t); const d = Number.isFinite(n) ? new Date((n > 1e11 ? n : n * 1000)) : new Date(String(t).replace(' ', 'T')); return Number.isNaN(d.getTime()) ? null : d; };
const when = (t) => { const d = toDate(t); return d ? d.toLocaleString('ru-RU', FMT) : (t ? String(t) : ''); };
const fileUrl = (p) => `/api/convert/file?path=${encodeURIComponent(p)}`;
const MEDIA = { img: /\.(png|jpe?g|webp|gif)$/i, video: /\.(mp4|webm|mov)$/i, audio: /\.(wav|mp3|flac|ogg|m4a)$/i };

export const editors = [
  { title: 'Screenshot Studio', url: 'https://www.screenshot-studio.com/', about: 'Скриншоты и презентационные кадры для портфолио и соцсетей', tags: 'скриншот картинка превью' },
  { title: 'Photopea', url: 'https://www.photopea.com/', about: 'Браузерный «Фотошоп»: PSD, слои, быстрая ретушь без установки', tags: 'фото psd слои ретушь картинка' },
  { title: 'miniPaint', url: '/static/editor.html?tool=minipaint', local: true, about: 'Простой растровый редактор: обрезка, слои, текст, фильтры; работает без интернета', tags: 'картинка рисовать обрезать слои фото png jpg' },
  { title: 'Squoosh', url: 'https://squoosh.app/', about: 'Сжатие и конвертация картинок для сайта и Telegram', tags: 'сжать webp картинка' },
  { title: 'OpenReel', url: 'https://openreel.video/', about: 'Монтаж коротких роликов и субтитры прямо в браузере', tags: 'видео монтаж субтитры reels' },
  { title: 'Fluid', url: 'https://fluid.krackeddevs.com/', about: 'Анимированные фоны WebGL; экспорт картинки или самостоятельного HTML', tags: 'фон шейдер анимация дизайн веб видео' },
  { title: 'AudioMass', url: '/static/editor.html?tool=audiomass', local: true, about: 'Обрезать звук, настроить громкость и затухание в браузере', tags: 'звук музыка аудио голос wav mp3' },
  { title: 'SVG-Edit', url: '/static/editor.html?tool=svgedit', local: true, about: 'Быстрые правки вектора: формы, текст и контуры SVG', tags: 'svg вектор логотип иконка дизайн' },
  { title: 'Piskel', url: 'https://www.piskelapp.com/', about: 'Пиксельная графика, игровые спрайты и покадровая анимация', tags: 'игры спрайт пиксель gif' },
  { title: 'CyberChef', url: '/tools/cyberchef/CyberChef_v11.5.0.html', local: true, about: 'Преобразование текста, кодировок и данных в браузере', tags: 'текст данные json base64 кодировка osint' },
];

let reload = () => {};
let q = '';
let kind = '';
let lastQuick = null;
let lastTools = null;
let toolQuery = '';
let convGroup = '';
let editorGroup = '';
const formCache = new Map();
const prefKey = 'pipeline.quick.workspace.v1';
let prefs = { layout: 'left', hidden: false, details: {} };
try { prefs = { ...prefs, ...JSON.parse(localStorage.getItem(prefKey) || '{}') }; } catch {}
if (!['left', 'top'].includes(prefs.layout)) prefs.layout = 'left';
const savePrefs = () => { try { localStorage.setItem(prefKey, JSON.stringify(prefs)); } catch {} };
// UX-32: «1 конвертер · 2 конвертера · 5 конвертеров»
const plural = (n, one, few, many) => { const t = n % 100, u = n % 10; return `${n} ${t > 10 && t < 20 ? many : u === 1 ? one : u >= 2 && u <= 4 ? few : many}`; };
const editorCategory = (e) => ({ OpenReel: 'Видео', Fluid: 'Видео', AudioMass: 'Звук', CyberChef: 'Данные', 'SVG-Edit': 'Графика', Piskel: 'Графика' }[e.title] || 'Картинки');
function keepForm() { const f = document.getElementById('convert-form'); if (f) formCache.set(f.dataset.kind, f); }
function restoreForm() {
  const slot = document.querySelector('#quick-workspace-root .quick-form-slot');
  const cached = formCache.get(kind);
  if (slot && cached) slot.replaceChildren(cached);
}
function updateQuick(focusSelector) {
  const root = document.getElementById('quick-workspace-root');
  if (!root || !lastQuick) return;
  keepForm();
  root.outerHTML = renderQuickEdits(lastQuick);
  restoreForm();
  if (focusSelector) document.querySelector(focusSelector)?.focus();
}

const match = (text) => !q || text.toLowerCase().includes(q.toLowerCase());

function option(o) {
  const v = o.default ?? '';
  const help = o.help ? `<small>${esc(o.help)}</small>` : '';
  if (o.kind === 'select') return `<label class="field">${esc(o.label)}${help}<select name="${esc(o.name)}">${(o.choices || []).map((c) => `<option value="${esc(c)}"${String(v) === String(c) ? ' selected' : ''}>${esc(c)}</option>`).join('')}</select></label>`;
  if (o.kind === 'bool') return `<label class="field check"><input type="checkbox" name="${esc(o.name)}"${v ? ' checked' : ''}> ${esc(o.label)}${help}</label>`;
  if (o.kind === 'number') return `<label class="field">${esc(o.label)}${help}<input type="number" step="any" name="${esc(o.name)}" value="${esc(v)}"${o.min != null ? ` min="${o.min}"` : ''}${o.max != null ? ` max="${o.max}"` : ''}></label>`;
  return `<label class="field">${esc(o.label)}${help}<input type="text" name="${esc(o.name)}" value="${esc(v)}"></label>`;
}

function convertForm(cv) {
  return `<form class="card quick-form" id="convert-form" data-disclosure-skip data-kind="${esc(cv.id)}"><h3>${esc(cv.title)}<small>${esc(cv.tool)}</small></h3>
    <p class="note">${esc(cv.about)}</p>
    <div class="form-grid">
      <div class="field upload wide"><label for="quick-source-file">Файл <small>${esc((cv.src || []).join(' '))}</small></label><input id="quick-source-file" type="file" name="file" accept="${esc((cv.src || []).join(','))}">
        <label for="quick-source-path">Или путь к файлу на локальном узле</label><input id="quick-source-path" type="text" name="src" placeholder="workspace/projects\\…"></div>
      ${(cv.options || []).map(option).join('')}
    </div>
    <div class="actions"><button type="submit"${cv.available ? '' : ' disabled'}>Конвертировать</button><span class="form-msg" role="status" aria-live="polite"></span></div>
    ${cv.available ? '' : '<p class="err">Нужная программа не установлена на локальном узле.</p>'}
    <div class="outputs" id="convert-outputs"></div></form>`;
}

function outputHtml(o) {
  const url = fileUrl(o.path);
  let media = '';
  if (MEDIA.img.test(o.name)) media = `<img src="${url}" loading="lazy" alt="">`;
  else if (MEDIA.video.test(o.name)) media = `<video src="${url}" controls preload="metadata"></video>`;
  else if (MEDIA.audio.test(o.name)) media = `<audio src="${url}" controls preload="none"></audio>`;
  return `<div class="output">${media}<a href="${url}" download="${esc(o.name)}">${esc(o.name)}</a> <small>${mb(o.size)}</small></div>`;
}

export function renderQuickEdits(data) {
  keepForm();
  lastQuick = data;
  const cat = data.convert || { converters: [], groups: [] };
  const tools = data.tools?.tools || [];
  const references = (data.tools?.references?.items || []).filter((r) => match(`${r.name} ${r.category} ${r.about} ${r.tags}`));
  const convs = cat.converters || [];
  if (!kind || !convs.find((c) => c.id === kind)) kind = convs[0]?.id || '';
  const hits = {
    editors: editors.filter((e) => (!editorGroup || editorCategory(e) === editorGroup) && match(`${e.title} ${e.about} ${e.tags}`)).sort((a, b) => Number(!!b.local) - Number(!!a.local)),  // local editors first
    convs: convs.filter((c) => (!convGroup || c.group === convGroup) && match(`${c.title} ${c.about} ${c.group} ${(c.src || []).join(' ')} ${c.tool}`)),
    tools: q ? tools.filter((t) => match(`${t.name} ${t.about} ${t.how} ${t.category_title}`)) : [],
  };
  const groups = [...new Set(hits.convs.map((c) => c.group))];
  const convList = groups.map((g) => `<div class="conv-group"><small>${esc(g)}</small>${hits.convs.filter((c) => c.group === g).map((c) =>
    `<button type="button" class="model-item${c.id === kind ? ' active' : ''}${c.available ? '' : ' off'}" aria-pressed="${c.id === kind}" data-conv="${esc(c.id)}"><b>${esc(c.title)}</b>${c.available ? '' : '<small>Не установлен</small>'}</button>`).join('')}</div>`).join('');
  const cv = convs.find((c) => c.id === kind);
  const runs = (data.runs || []).slice(0, 12).map((r) => `<div class="card run-card"><h3><span>${dot(r.ok ? 'ok' : 'bad')}${esc(r.title)}</span>${pill(`${r.seconds ?? '?'} с`)}</h3>
    <p class="note">${when(r.ts)} · ${esc(String(r.src).split(/[\\/]/).pop())}</p>${(r.outputs || []).length ? `<div class="outputs">${r.outputs.map(outputHtml).join('')}</div>` : `<p class="err">${esc(r.error || r.log || 'без результата')}</p>`}</div>`).join('');
  const toolHits = hits.tools.map((t) => `<div class="card tool-hit"><h3>${esc(t.name)}<small>${esc(t.category_title)}</small></h3><p class="note">${esc(t.about)}</p><p class="note"><b>Как:</b> ${esc(t.how)}${t.tab ? ` · <a href="#${esc(t.tab)}">вкладка</a>` : ''}</p></div>`).join('');
  const missing = Object.entries(cat.not_available || {}).map(([k, v]) => `<li><b>${esc(k)}</b> — ${esc(v)}</li>`).join('');
  const cats = [...new Set(convs.map((c) => c.group))];
  const editorCats = [...new Set(editors.map(editorCategory))];
  const detail = (key) => prefs.details?.[key] ? ' open' : '';
  queueMicrotask(restoreForm);
  return `<div id="quick-workspace-root">
    <div class="quick-search"><label for="quick-q">Найти инструмент</label><input type="search" id="quick-q" placeholder="PDF, сжать, монтаж, SVG…" value="${esc(q)}" autocomplete="off"><span class="note" role="status">${plural(hits.convs.length, 'конвертер', 'конвертера', 'конвертеров')} · ${plural(hits.editors.length, 'редактор', 'редактора', 'редакторов')}</span></div>
    <p class="note quick-moved">Правка картинок нейросетью (свет, расширение кадра, фон, ракурс, мокап) — в разделе <a href="#models/image">Модели › Картинки</a>.</p>
    <section class="quick-converters" data-disclosure-skip aria-labelledby="quick-converters-title">
      <div class="quick-heading"><h2 id="quick-converters-title">Конвертеры</h2><div class="quick-layout-controls"><label for="quick-layout">Выбор инструмента</label><select id="quick-layout"><option value="left"${prefs.layout === 'left' ? ' selected' : ''}>Слева</option><option value="top"${prefs.layout === 'top' ? ' selected' : ''}>Сверху</option></select><button type="button" class="ghost" id="quick-toggle-chooser" aria-controls="quick-chooser" aria-expanded="${!prefs.hidden}">${prefs.hidden ? 'Показать список' : 'Скрыть список'}</button></div></div>
      <div class="quick-workbench layout-${prefs.layout}${prefs.hidden ? ' chooser-hidden' : ''}">
        <aside id="quick-chooser" class="quick-chooser" aria-label="Выбор конвертера"${prefs.hidden ? ' hidden' : ''}>
          <label class="quick-category" for="quick-conv-group">Категория<select id="quick-conv-group"><option value="">Все категории (${convs.length})</option>${cats.map((g) => `<option value="${esc(g)}"${convGroup === g ? ' selected' : ''}>${esc(g)}</option>`).join('')}</select></label>
          <div class="quick-converter-list" tabindex="0" aria-label="Конвертеры по категориям">${convList || '<p class="note">Нет совпадений. Измените запрос или категорию.</p>'}</div>
        </aside>
        <div class="quick-form-slot">${cv && !formCache.has(kind) ? convertForm(cv) : ''}</div>
      </div>
      <details class="quick-details" data-quick-detail="converter-help"${detail('converter-help')}><summary>Папка результатов и другие возможности</summary><p class="note receipt-path">${esc(cat.out_root)}</p>${missing ? `<ul>${missing}</ul>` : ''}</details>
    </section>
    <section class="quick-editors" aria-labelledby="quick-editors-title"><div class="quick-heading"><h2 id="quick-editors-title">Редакторы</h2><label class="quick-category" for="quick-editor-group">Категория<select id="quick-editor-group"><option value="">Все</option>${editorCats.map((g) => `<option value="${esc(g)}"${editorGroup === g ? ' selected' : ''}>${esc(g)}</option>`).join('')}</select></label></div>
      <div class="quick-editor-grid">${hits.editors.map((e) => `<a class="card quick-edit-card" href="${e.url}" target="_blank" rel="noopener"><small class="note">${esc(editorCategory(e))}</small><h3>${esc(e.title)} <span aria-hidden="true">↗</span></h3><p class="note">${esc(e.about)}</p><span class="quick-external-note">${e.local ? 'Локально, без интернета · новая вкладка' : 'Онлайн · новая вкладка'}</span></a>`).join('') || '<p class="note">Редакторы не найдены.</p>'}</div>
    </section>
    ${toolHits ? `<details class="quick-details" data-quick-detail="tool-hits"${detail('tool-hits')}><summary>Другие инструменты по запросу · ${hits.tools.length}</summary><div class="grid">${toolHits}</div></details>` : ''}
    <details class="quick-details" data-quick-detail="references"${detail('references')}><summary>Референсы, приёмы и библиотеки · ${references.length}</summary><p class="note">Камера, свет, анимация, шрифты и SVG. Доступ к подпискам указан отдельно.</p>
      <div class="grid">${references.map((r) => `<div class="card reference-card"><h3>${r.url ? `<a href="${esc(r.url)}" target="_blank" rel="noopener">${esc(r.name)} ↗</a>` : esc(r.name)}</h3><small>${esc(r.category)}</small><p>${esc(r.about)}</p><p class="note">${esc(r.access)}</p>${r.path ? `<small class="receipt-path">${esc(r.path)}</small>` : ''}</div>`).join('') || '<p class="note">Нет совпадений.</p>'}</div></details>
    ${runs ? `<details class="quick-details" data-quick-detail="runs"${detail('runs')}><summary>Последние конвертации · ${Math.min(data.runs.length, 12)}</summary><div class="grid runs">${runs}</div></details>` : ''}</div>`;
}

// Catalog display grouping (Operator 08.10): Example game is a game project, OSINT sits with security. Sources stay where they are.
const SKILL_MERGE = {};
const SKILL_TITLES = { security: 'Security / OSINT' };
function mergeSkillGroups(groups) {
  const out = new Map();
  for (const g of groups) {
    const m = SKILL_MERGE[g.key];
    const key = m?.into || g.key;
    if (!out.has(key)) out.set(key, { key, title: SKILL_TITLES[key] || g.title, uses: [], items: [] });
    const t = out.get(key);
    if (!m) t.title = SKILL_TITLES[key] || g.title;
    for (const u of [g.focus && `Фокус: ${g.focus}`, g.use]) if (u && !t.uses.includes(u)) t.uses.push(u);
    // A merged project keeps its own roles but never outranks the host group's entry skill.
    const items = g.items || g.names.map((name) => ({ name, role: '' }));
    for (const it of items) if (!t.items.some((x) => x.name === it.name)) t.items.push({ name: it.name, role: m && it.role === 'primary' ? 'aux' : it.role, origin: m?.origin || '' });
  }
  const rank = { primary: 0, aux: 1 };
  for (const g of out.values()) g.items.sort((a, b) => (rank[a.role] ?? 2) - (rank[b.role] ?? 2) || a.name.localeCompare(b.name));
  return [...out.values()];
}

const skillName = (n) => esc(n.name) + (n.origin ? ` <span class="${tagClass('role', 'reference')}" title="Навык проекта ${esc(n.origin)}">${esc(n.origin)}</span>` : '');
function skillList(items) {
  const by = (role) => items.filter((n) => (n.role || 'reference') === role);
  const [main, aux, ref] = [by('primary'), by('aux'), by('reference')];
  if (!main.length && !aux.length) return `<p>${ref.map(skillName).join(' · ')}</p>`;
  return (main.length ? `<p class="skill-role-line"><span class="${tagClass('role', 'primary')}">Вход</span> <b>${main.map(skillName).join(' · ')}</b></p>` : '')
    + (aux.length ? `<p class="skill-role-line"><span class="${tagClass('role', 'aux')}">Вспомогательные</span> ${aux.map(skillName).join(' · ')}</p>` : '')
    + (ref.length ? `<p class="note">Справочные: ${ref.map(skillName).join(' · ')}</p>` : '');
}

// «Инструменты» = skills only (Operator, 2026-10-11): the tool/model catalogue lives in «Модели»; radar/gaps/next moved to the board (2026-10-12).
export function renderTools(data) {
  lastTools = data;
  const review = data.review || {};
  const sq = toolQuery.trim().toLowerCase();
  const skillGroups = mergeSkillGroups(review.groups || []).map((g) => (!sq || g.title.toLowerCase().includes(sq) ? g : { ...g, items: g.items.filter((n) => `${n.name} ${n.origin}`.toLowerCase().includes(sq)) })).filter((g) => g.items.length);
  const found = skillGroups.reduce((a, g) => a + g.items.length, 0);
  const skillRows = skillGroups.map((g) => `<details class="card"${sq ? ' open' : ''}><summary><b>${esc(g.title)}</b> · ${g.items.length} навыков</summary>${g.uses.map((u) => `<p class="note">${esc(u)}</p>`).join('')}${skillList(g.items)}</details>`).join('');
  return `<div id="tools-workspace-root"><h2 class="tools-sr-heading">Навыки по пайплайнам</h2>
    <div class="tools-filters"><label for="tools-q">Поиск навыка<input type="search" id="tools-q" value="${esc(toolQuery)}" placeholder="Название, пайплайн или проект…"></label><span class="note" role="status">${sq ? `Найдено: ${found} из ${review.unique_names ?? 0}` : `${review.unique_names ?? 0} названий`}</span></div>
    <p class="note">Основной навык — вход пайплайна, с него начинать; вспомогательные — по его маршруту.</p>
    <details class="note"><summary>Подробнее</summary><p>${review.source ? `Из ${esc(review.source)} на ${esc(review.checked_at)}: ${review.count} папок навыков.` : `Сверка ${esc(review.checked_at || '—')}: ${review.count ?? 0} записей источников.`} Выполнение всех навыков не проверялось.</p></details>
    <div class="grid">${skillRows || '<p class="note">Навыки не найдены. Измените запрос.</p>'}</div>
    <p class="note tools-board-note">Планы по инструментам и навыкам (радар, что добавить, что доделать) ведутся задачами на <a href="/#board">доске</a>.</p></div>`;
}

export function initQuick(refresh) {
  reload = refresh;
  let timer = null;
  const updateTools = (focus) => { const root = document.getElementById('tools-workspace-root'); if (root && lastTools) { root.outerHTML = renderTools(lastTools); document.querySelector(focus)?.focus(); } };
  document.addEventListener('input', (e) => {
    if (e.target.id === 'tools-q') { toolQuery = e.target.value; clearTimeout(timer); timer = setTimeout(() => { const pos = e.target.selectionStart; updateTools('#tools-q'); document.getElementById('tools-q')?.setSelectionRange(pos, pos); }, 200); return; }
    if (e.target.id !== 'quick-q') return;
    q = e.target.value;
    clearTimeout(timer);
    timer = setTimeout(() => { const pos = e.target.selectionStart; updateQuick('#quick-q'); const el = document.getElementById('quick-q'); if (el) el.setSelectionRange(pos, pos); }, 200);
  });
  document.addEventListener('change', (e) => {
    if (e.target.id === 'quick-layout') { prefs.layout = e.target.value; savePrefs(); updateQuick('#quick-layout'); }
    else if (e.target.id === 'quick-conv-group') { convGroup = e.target.value; updateQuick('#quick-conv-group'); }
    else if (e.target.id === 'quick-editor-group') { editorGroup = e.target.value; updateQuick('#quick-editor-group'); }
  });
  document.addEventListener('toggle', (e) => {
    const key = e.target.dataset?.quickDetail;
    if (key) { prefs.details = { ...prefs.details, [key]: e.target.open }; savePrefs(); }
  }, true);
  document.addEventListener('click', (e) => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.dataset.conv) { kind = b.dataset.conv; updateQuick(`[data-conv="${CSS.escape(kind)}"]`); }
    else if (b.id === 'quick-toggle-chooser') { prefs.hidden = !prefs.hidden; savePrefs(); updateQuick('#quick-toggle-chooser'); }
  });
  document.addEventListener('submit', async (e) => {
    const f = e.target; if (f.id !== 'convert-form') return;
    e.preventDefault();
    const btn = f.querySelector('[type=submit]'); const msg = f.querySelector('.form-msg'); const out = f.querySelector('#convert-outputs');
    if (btn.disabled) return;
    const fd = new FormData(); const opts = {};
    for (const el of f.querySelectorAll('.form-grid [name]')) {
      if (el.name === 'file') { if (el.files?.length) fd.append('file', el.files[0]); }
      else if (el.name === 'src') { if (el.value.trim()) fd.append('src', el.value.trim()); }
      else opts[el.name] = el.type === 'checkbox' ? el.checked : el.type === 'number' ? Number(el.value) : el.value;
    }
    fd.append('kind', f.dataset.kind); fd.append('options', JSON.stringify(opts));
    btn.disabled = true; msg.classList.remove('err'); msg.textContent = 'Конвертирую…'; out.innerHTML = '';
    try {
      const r = await fetch('/api/convert', { method: 'POST', body: fd });
      const data = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(data.detail || r.statusText);
      msg.textContent = `Готово за ${data.seconds} с`;
      out.innerHTML = (data.outputs || []).map(outputHtml).join('') || `<p class="note">${esc(data.log || 'без файлов')}</p>`;
    } catch (err) { msg.textContent = err.message; msg.classList.add('err'); }
    finally { btn.disabled = false; }
  });
}
