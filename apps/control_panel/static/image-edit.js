// «Правка картинки» on the Quick edits tab: one button per edit (Relight, Expand, Remove BG, Angles, Mockup).
// Engines are listed best quality first; the default is the best available one (owner decision 08.10).
// The section is one persistent DOM node re-inserted after every tab render, so input and results survive refreshes.
const esc = (v) => String(v ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const fileUrl = (p) => `/api/models/file?path=${encodeURIComponent(p)}`;
const srcUrl = (p) => `/api/image-edit/source?path=${encodeURIComponent(p)}`;
const prefKey = 'pipeline.quick.imageEdit.v1';
let prefs = { op: 'relight', engines: {}, options: {} };
try { prefs = { ...prefs, ...JSON.parse(localStorage.getItem(prefKey) || '{}') }; } catch {}
const savePrefs = () => { try { localStorage.setItem(prefKey, JSON.stringify(prefs)); } catch {} };

let el = null;
let cat = null;
let source = null; // {path, name, preview}
let current = null; // run id being watched
let timer = null;

async function api(url, opts) {
  const r = await fetch(url, opts);
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || r.statusText);
  return data;
}

export function mountImageEdit(slot) {
  if (!slot) return;
  if (!el) {
    el = document.createElement('section');
    el.className = 'card quick-form image-edit';
    el.id = 'image-edit';
    el.setAttribute('aria-labelledby', 'image-edit-title');
    el.innerHTML = '<h2 id="image-edit-title">Правка картинки</h2><p class="note">Загрузка моделей…</p>';
    bind(el);
    load();
  }
  if (el.parentElement !== slot) slot.replaceChildren(el);
}

// Any failure (slow catalogue, network, bad payload) ends in a visible error with «Повторить», never an endless «Загрузка».
async function load() {
  try {
    cat = await api('/api/image-edit', { signal: AbortSignal.timeout(30000) });
    if (!cat.ops?.length) throw new Error('Каталог правок пуст');
    if (!cat.ops.find((o) => o.id === prefs.op)) prefs.op = cat.ops[0].id;
    const running = (cat.runs || []).find((r) => r.status === 'running');
    if (running) watch(running.id);
    render();
  } catch (err) {
    cat = null;
    const why = err.name === 'TimeoutError' ? 'Каталог моделей не ответил за 30 с' : err.message;
    el.innerHTML = `<h2 id="image-edit-title">Правка картинки</h2><p class="err">${esc(why)}</p><button type="button" id="ie-retry" class="ghost">Повторить</button>`;
  }
}

const op = () => cat.ops.find((o) => o.id === prefs.op);
function engineFor(o) {
  const chosen = prefs.engines[o.id];
  return chosen && o.engines.includes(chosen) && cat.engines[chosen]?.available ? chosen : o.default;
}

function render() {
  if (!cat) return;
  const o = op();
  const engine = engineFor(o);
  const opt = o.option;
  const optValue = opt && opt.choices.includes(prefs.options[o.id]) ? prefs.options[o.id] : opt?.choices[0];
  const focusId = document.activeElement && el.contains(document.activeElement) ? document.activeElement.id : '';
  el.innerHTML = `<h2 id="image-edit-title">Правка картинки</h2>
    <div class="ie-ops" role="group" aria-label="Что сделать">${cat.ops.map((x) => `<button type="button" id="ie-op-${x.id}" class="ie-op${x.id === o.id ? ' active' : ''}" aria-pressed="${x.id === o.id}" data-ie-op="${x.id}"><b>${esc(x.title)}</b><small>${esc(x.about)}</small></button>`).join('')}</div>
    <div class="ie-grid">
      <div class="ie-source">
        <label for="ie-file">Картинка <small>PNG, JPG, WEBP</small></label><input id="ie-file" type="file" accept=".png,.jpg,.jpeg,.webp">
        <label for="ie-path">Или путь на локальном узле</label><input id="ie-path" type="text" placeholder="workspace/projects\\…\\image.png" value="${esc(source && !source.uploaded ? source.path : '')}">
        ${source?.preview ? `<img class="ie-preview" src="${esc(source.preview)}" alt="Исходник">` : ''}
        ${source ? `<p class="note">${esc(source.name)}</p>` : ''}
      </div>
      <div class="ie-settings">
        ${opt ? `<label class="field" for="ie-option">${esc(opt.label)}<select id="ie-option">${opt.choices.map((c) => `<option${c === optValue ? ' selected' : ''}>${esc(c)}</option>`).join('')}</select></label>` : ''}
        <label class="field" for="ie-detail">Уточнение <small>необязательно</small><input id="ie-detail" type="text" placeholder="${esc(o.detail_hint)}" value="${esc(prefs.detail || '')}"></label>
        <label class="field" for="ie-engine">Модель<select id="ie-engine">${o.engines.map((k, i) => { const e = cat.engines[k]; return `<option value="${k}"${k === engine ? ' selected' : ''}${e.available ? '' : ' disabled'}>${esc(e.title)}${i === 0 ? ' — лучшее качество' : ''}${e.available ? '' : ` (недоступно: ${esc(e.reason)})`}</option>`; }).join('')}</select></label>
        <p class="note">${esc(cat.engines[engine].note)}</p>
        <div class="actions"><button type="button" id="ie-run"${current ? ' disabled' : ''}>Сделать</button><span class="form-msg" role="status" aria-live="polite"></span></div>
      </div>
    </div>
    <div class="ie-result" id="ie-result"></div>
    <details class="quick-details" data-quick-detail="image-edit-runs"><summary>Последние правки · ${(cat.runs || []).length}</summary><div class="ie-runs">${(cat.runs || []).map(runCard).join('') || '<p class="note">Пока нет.</p>'}</div></details>`;
  showResult();
  if (focusId) document.getElementById(focusId)?.focus();
}

function receipt(r) {
  const q = r.quick_edit || {};
  const rc = r.receipt || {};
  const rows = [['Модель', q.engine_title], ['Провайдер', rc.provider || q.provider], ['Функция', rc.feature], ['Кредиты Adobe', rc.credits], ['Модель Codex', rc.codex_model], ['Поток Codex', rc.thread_id],
    ['Время', rc.seconds != null ? `${rc.seconds} с` : r.elapsed != null ? `${r.elapsed} с` : ''], ['Исходник', (r.inputs || {}).input_image], ['SHA-256 исходника', rc.source_sha256],
    ...(r.outputs || []).map((o) => ['Результат', `${o.path}${o.sha256 ? ` · ${o.sha256}` : ''}`]), ['Промпт', rc.revised_prompt || rc.prompt], ['Ошибка', rc.error || rc.failure]].filter(([, v]) => v);
  return `<details class="ie-receipt"><summary>Квитанция</summary><dl>${rows.map(([k, v]) => `<dt>${esc(k)}</dt><dd>${esc(typeof v === 'object' ? JSON.stringify(v) : v)}</dd>`).join('')}</dl></details>`;
}

function outputs(r, lazy = false) {
  return (r.outputs || []).map((o) => `<figure><a href="${fileUrl(o.path)}" target="_blank" rel="noopener"><img src="${fileUrl(o.path)}" alt="Результат"${lazy ? ' loading="lazy"' : ''}></a><figcaption><a href="${fileUrl(o.path)}" download="${esc(o.name)}">Скачать ${esc(o.name)}</a></figcaption></figure>`).join('');
}

function runCard(r) {
  const state = r.status === 'done' ? 'ok' : r.status === 'running' ? 'warn' : 'bad';
  return `<div class="ie-run"><p><i class="dot ${state}"></i><b>${esc(r.title)}</b> <small class="note">${esc(r.quick_edit?.engine_title || '')}</small></p>${outputs(r, true)}${r.status !== 'done' && r.status !== 'running' ? `<p class="err">${esc((r.log_tail || []).slice(-2).join(' ') || 'Без результата')}</p>` : ''}${receipt(r)}</div>`;
}

function showResult() {
  const box = el.querySelector('#ie-result'); const msg = el.querySelector('.form-msg');
  const r = (cat.runs || []).find((x) => x.id === (current || prefs.last));
  if (!box || !r) return;
  if (r.status === 'running') {
    msg.textContent = `Идёт: ${r.quick_edit?.engine_title || ''} · ${r.elapsed ?? 0} с`;
    box.innerHTML = (r.log_tail || []).length ? `<p class="note">${esc(r.log_tail.slice(-1)[0])}</p>` : '';
    return;
  }
  msg.classList.toggle('err', r.status !== 'done');
  msg.textContent = r.status === 'done' ? 'Готово' : 'Не получилось';
  const before = r.inputs?.input_image ? `<figure><img src="${srcUrl(r.inputs.input_image)}" alt="До"><figcaption>До</figcaption></figure>` : '';
  box.innerHTML = `<div class="ie-compare${r.quick_edit?.op === 'remove_bg' ? ' ie-alpha' : ''}">${before}${outputs(r)}</div>${r.status !== 'done' ? `<p class="err">${esc((r.log_tail || []).slice(-3).join(' ') || 'Без результата')}</p>` : ''}${receipt(r)}`;
}

function watch(id) {
  current = id;
  clearTimeout(timer);
  const tick = async () => {
    try {
      const data = await api('/api/image-edit/runs');
      cat.runs = data.runs;
      const r = data.runs.find((x) => x.id === id);
      if (!r || r.status !== 'running') { current = null; prefs.last = id; savePrefs(); render(); return; }
      showResult();
    } catch {}
    timer = setTimeout(tick, 4000);
  };
  timer = setTimeout(tick, 2500);
}

async function run() {
  const msg = el.querySelector('.form-msg');
  const btn = el.querySelector('#ie-run');
  const o = op();
  msg.classList.remove('err');
  try {
    const path = el.querySelector('#ie-path').value.trim();
    if (path && (!source || source.path !== path)) source = { path, name: path.split(/[\\/]/).pop(), preview: srcUrl(path) };
    if (!source) throw new Error('Выберите картинку');
    btn.disabled = true; msg.textContent = 'Запускаю…';
    const body = { op: o.id, engine: el.querySelector('#ie-engine').value, input: source.path, option: el.querySelector('#ie-option')?.value || '', detail: el.querySelector('#ie-detail').value };
    const res = await api('/api/image-edit/run', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    cat.runs = [{ ...res.run, outputs: [], elapsed: 0 }, ...(cat.runs || [])];
    watch(res.run.id);
    render();
  } catch (err) { msg.textContent = err.message; msg.classList.add('err'); btn.disabled = false; }
}

async function upload(file) {
  const msg = el.querySelector('.form-msg');
  msg.classList.remove('err'); msg.textContent = 'Загружаю…';
  try {
    const fd = new FormData(); fd.append('file', file);
    const up = await api('/api/models/upload', { method: 'POST', body: fd });
    if (source?.uploaded && source.preview) URL.revokeObjectURL(source.preview);
    source = { path: up.path, name: file.name, preview: URL.createObjectURL(file), uploaded: true };
    render();
  } catch (err) { msg.textContent = err.message; msg.classList.add('err'); }
}

function bind(root) {
  root.addEventListener('click', (e) => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.dataset.ieOp) { prefs.op = b.dataset.ieOp; savePrefs(); render(); }
    else if (b.id === 'ie-run') run();
    else if (b.id === 'ie-retry') { el.innerHTML = '<h2 id="image-edit-title">Правка картинки</h2><p class="note">Загрузка моделей…</p>'; load(); }
  });
  root.addEventListener('change', (e) => {
    const o = op();
    if (e.target.id === 'ie-file' && e.target.files?.length) upload(e.target.files[0]);
    else if (e.target.id === 'ie-engine') { prefs.engines[o.id] = e.target.value; savePrefs(); render(); }
    else if (e.target.id === 'ie-option') { prefs.options[o.id] = e.target.value; savePrefs(); }
    else if (e.target.id === 'ie-path' && e.target.value.trim()) { const p = e.target.value.trim(); source = { path: p, name: p.split(/[\\/]/).pop(), preview: srcUrl(p) }; render(); }
  });
  root.addEventListener('input', (e) => { if (e.target.id === 'ie-detail') { prefs.detail = e.target.value; savePrefs(); } });
}
