// «Модели»: Gradio-like tab for the local models on Local node. Forms are built from the sidecar fields
// returned by /api/models; runs go through the pipeline runners (gpu.lock, receipts) via /api/models/run.
import { tag, tagClass } from './tags.js';
import { mountImageEdit } from './image-edit.js';
import { enhancementBlock, enhancementOptions, videoOutputs } from './models-enhance.js?v=20261018';
import { VIDEO_TASKS, videoTasks, taskLabel, modeLabel } from './models-modes.js?v=experience-20261013';
import {familyKey, familyRank, modelName, variantName, modelPurpose, tasksFor, taskOptions, fieldMeta, optionLabel} from './models-catalog-ui.js?v=c3-20261019p';
import { HELP_RU } from './models-help-ru.js?v=ux10-20261011';
const esc = (v) => String(v ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
// Catalogue titles read "Name (engine spec): what it does"; the list shows the name and a short spec line, the full title stays in the tooltip.
function splitTitle(t) {
  let [name, ...rest] = String(t).split(': '); let spec = rest.join(': ');
  const m = name.match(/^(.*?)\s*\((.+)\)$/);
  if (m) { name = m[1]; spec = spec ? `${m[2]} · ${spec}` : m[2]; }
  return { name, spec: spec.replace(/\s*->\s*/g, ' → ') };
}
const dot = (state) => `<i class="dot ${state}"></i>`;
const pill = (text, state = '') => `<span class="pill ${state}">${esc(text)}</span>`;
const mb = (b) => b > 1048576 ? `${(b / 1048576).toFixed(1)} МБ` : `${Math.round((b || 0) / 1024)} КБ`;
const FMT = { hour: '2-digit', minute: '2-digit', day: '2-digit', month: '2-digit' };
const toDate = (t) => { if (!t) return null; const n = Number(t); const d = Number.isFinite(n) ? new Date((n > 1e11 ? n : n * 1000)) : new Date(String(t).replace(' ', 'T')); return Number.isNaN(d.getTime()) ? null : d; };
const when = (t) => { const d = toDate(t); return d ? d.toLocaleString('ru-RU', FMT) : (t ? String(t) : ''); };
const request = async (url, body) => {
  const r = await fetch(url, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  const data = await r.json().catch(() => ({}));
  if (!r.ok) { const e = new Error(data.detail || r.statusText); e.queue = r.headers.get('X-Gpu-Queue') === 'offer'; throw e; }
  return data;
};
const fileUrl = (p) => `/api/models/file?path=${encodeURIComponent(p)}`;
const MEDIA = { img: /\.(png|jpe?g|webp|gif)$/i, video: /\.(mp4|webm|mov|mkv)$/i, audio: /\.(wav|mp3|flac|ogg|m4a)$/i };

let reload = () => {};
// Same line icons as Главная (home.js LAUNCH); one SVG set instead of text glyphs/emoji.
const svg = (d) => `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="${d}"/></svg>`;
const ICON = { video: 'M4 6h12v12H4zM16 10l4-2v8l-4-2', image: 'M4 4h16v16H4zM4 16l5-5 4 4 3-3 4 4M15 8h.01', voice: 'M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3zM5 11a7 7 0 0 0 14 0M12 18v3',
  music: 'M9 18V5l11-2v13M9 18a3 3 0 1 1-6 0 3 3 0 0 1 6 0zM20 16a3 3 0 1 1-6 0 3 3 0 0 1 6 0z', '3d': 'm12 3 8 4.5v9L12 21l-8-4.5v-9zM12 12l8-4.5M12 12v9M12 12 4 7.5', text: 'M4 5h16v11H8l-4 4zM8 9h8M8 12h5',
  library: 'M5 4h4v16H5zM10 4h4v16h-4zM15 5l3.5-.8 3 15.6-3.5.8z', star: 'm12 4 2.5 5 5.5.8-4 3.9.9 5.5-4.9-2.6-4.9 2.6.9-5.5-4-3.9 5.5-.8z', folder: 'M3 6h6l2 2h10v11H3z' };
// Panel/agent checks keep ordinary titles; these prefixes mark them so they do not crowd Operator's own results.
const SERVICE_RUN = /^(smoke(:| control-\d)|UX[- ]?(check|\d+ тест)|W\d+ проверка)|\(проба панели\)/i;
let last = { cat: null, runs: [] };
const enhancementSources = new Map();
const state = { group: 'video', videoTask: 'all', kind: null, params: {}, inputs: {}, uploads: {}, title: '', chat: [], chatBusy: false, chatModel: 't-lite', chatDraft: '',
  lib: { q: '', source: '', items: [], counts: {}, total: 0, open: false, busy: false, err: '' }, improve: { busy: false, res: null, err: '' },
  feed: 'group', loc: 'all', toProj: null, projects: null, runMsg: {}, target: store('models-target') };
function store(k, v) { try { if (v === undefined) return localStorage.getItem(k) || ''; localStorage.setItem(k, v); } catch { return ''; } return v; }

export async function loadModels() {
  if (!state.projects) state.projects = await request('/api/models/projects').catch(() => null);  // for the form's «Проект» picker
  const [cat, rr] = await Promise.all([fetch('/api/models').then((r) => r.json()), fetch('/api/models/runs?limit=30').then((r) => r.json())]);
  return { cat, runs: Array.isArray(rr) ? rr : rr.runs || [], queue: rr.queue || [] };
}

// Home tiles open Модели on a given section (#models/<group>); renderModels then picks that section's main model.
// 3.0: «Быстрая правка» (image-edit.js, moved from «Конвертеры») sits on top of «Картинки»; its open state is remembered.
const IE_OPEN = 'models-image-edit-open';
const ieOpen = () => { try { return localStorage.getItem(IE_OPEN) === '1'; } catch (_) { return false; } };
document.addEventListener('toggle', (e) => { if (e.target?.id === 'models-image-edit') { try { localStorage.setItem(IE_OPEN, e.target.open ? '1' : '0'); } catch (_) {} } }, true);
const imageEditBlock = () => { queueMicrotask(() => mountImageEdit(document.querySelector('#models-image-edit .image-edit-slot')));
  return '<details class="models-image-edit" id="models-image-edit"' + (ieOpen() ? ' open' : '') + '><summary><b>Быстрая правка картинки</b><span>свет, расширить кадр, убрать фон, ракурс, мокап</span></summary><div class="image-edit-slot"></div></details>'; };
// #models/kind/<id> (Студия «Повторить в Моделях») opens that exact model; renderModels finds its section.
let pendingKind = null;
export function setModelsGroup(g, kind) {
  if (g === 'kind') { pendingKind = kind || null; return; }
  if (!g || g === state.group) return;
  state.group = g; state.feed = g === 'text' ? 'all' : 'group'; state.videoTask = 'all'; state.uiTask = 'all'; state.loc = 'all'; state.previewRun = null;
}

function item(cat, kind) {
  for (const g of cat.groups || []) for (const it of g.items) if (it.id === kind) return it;
  return null;
}

function defaults(it) {
  const p = {};
  for (const f of it.fields) if (f.kind !== 'upload' && f.default !== undefined && f.default !== null && f.default !== 'PROMPT') p[f.name] = f.default;
  return p;
}

// keep=true when switching the mode of the same base: values of fields with the same name carry over.
const drafts = new Map();
let selectionEpoch = 0;
const uploadRequests = new Map();
function select(kind, keep = false) {
  const it = item(last.cat, kind);
  if (!it) return;
  selectionEpoch++;
  const prev = { params: state.params, inputs: state.inputs, uploads: state.uploads };
  if (state.kind) drafts.set(state.kind, {...prev, title:state.title,task:state.task,skeleton:state.skeleton});
  const saved = drafts.get(kind);
  const sameFamily = item(last.cat,state.kind) && familyKey(item(last.cat,state.kind))===familyKey(it);
  keep = keep && sameFamily;
  state.cloudEst = null; state.ownerRequest = ''; state.enhanceGate = null;
  state.controlNotice='';
  state.kind = kind; state.params = defaults(it); state.inputs = {}; state.uploads = {};
  if (keep) {
    for (const f of it.fields) {
      if (prev.params[f.name] !== undefined) state.params[f.name] = prev.params[f.name];
      if (prev.inputs[f.name]) { state.inputs[f.name] = prev.inputs[f.name]; if (prev.uploads[f.name]) state.uploads[f.name] = prev.uploads[f.name]; }
    }
  } else { state.title = ''; state.task = ''; state.skeleton = ''; }
  if (saved) Object.assign(state, saved);
  state.improve = { busy: false, res: null, err: '' }; state.lib.items = []; state.lib.total = 0;
  if (state.lib.open) setTimeout(libSearch, 0);
}

// Task preset: frame/duration values + English prompt skeleton placed in front of the subject text.
function applyPreset(it, p) {
  const values = { ...p.values };
  if (p.prompt && it.visual_presets) {
    const map={kino:'cinema',ad:'product',mockup:'product',realism:'documentary',musicvideo:'clip',cartoon:'animation',archviz:'architecture',game:'animation',animatic:'animation',food:'product',reels:'clip'};
    const selected=it.visual_presets.find(v=>v.id===(map[p.id]||'none'));
    for(const f of it.fields.filter(f=>f.visual)) values[f.name]=selected?.values[f.name]||'none';
    state.task=p.id;
  } else if(p.prompt && it.fields.some(f=>f.name==='prompt')) {
    // Only legacy models without visual controls use explicit text insertion.
    values.prompt=[state.params.prompt||'',p.prompt].filter(Boolean).join(', ');
  }
  Object.assign(state.params, values);
  syncControls(it);
  const f = document.getElementById('models-form'); if (!f) return;
  for (const [k, v] of Object.entries(values)) { const el = f.querySelector(`[data-param="${k}"]`); if (el) el.type === 'checkbox' ? (el.checked = !!v) : (el.value = v); }
  refreshDurations(it); cloudReset();
  markAspect();
  if (p.prompt) f.querySelectorAll('[data-m-list="task_presets"]').forEach((x) => x.classList.toggle('on', x.textContent === p.name));
  const msg = f.querySelector('.form-msg'); if (msg) { msg.classList.remove('err'); msg.textContent = `Пресет «${p.name}»${p.note ? ': ' + p.note : ''}`; }
  refreshChips(); refreshVisual(it); invalidatePreview();
}

function chipsFor(it) {
  const doc = last.cat?.chips || {};
  if (!it.fields.some((f) => f.name === 'prompt')) return [];
  return (doc.chips || []).filter((c) => (c.models_ok || []).includes(it.base));
}

function chipBlock(it) {
  const chips = chipsFor(it); if (!chips.length) return '';
  const prompt = String(state.params.prompt || '');
  const on = new Set(chips.filter((c) => prompt.includes(c.fragment_en)).map((c) => c.id));
  const blocked = (c) => chips.find((o) => on.has(o.id) && o.id !== c.id && ((o.conflicts || []).includes(c.id) || (c.conflicts || []).includes(o.id)));
  const groups = last.cat.chips.groups || {};
  const rows = Object.entries(groups).map(([g, title]) => {
    const list = chips.filter((c) => c.group === g); if (!list.length) return '';
    return `<div class="chip-row"><span>${esc(title)}</span>${list.map((c) => {
      const by = !on.has(c.id) && blocked(c);
      return `<button type="button" class="preset chip${on.has(c.id) ? ' on' : ''}" data-m-chip="${esc(c.id)}" aria-pressed="${on.has(c.id)}"${by ? ` disabled title="Конфликт: ${esc(by.label_ru)}"` : ` title="${esc(c.fragment_en)}"`}>${esc(c.label_ru)}</button>`;
    }).join('')}</div>`;
  }).join('');
  return `<details class="note prompt-chips" id="m-chips"><summary>Дополнительные фразы в описании${on.size ? ` <span class="count">${on.size}</span>` : ''}</summary>${rows}</details>`;
}

function refreshChips() {
  const it = item(last.cat, state.kind); const box = document.getElementById('m-chips'); if (!it || !box) return;
  const open = box.open; const tmp = document.createElement('div'); tmp.innerHTML = chipBlock(it);
  const fresh = tmp.firstElementChild; if (!fresh) return; fresh.open = open; box.replaceWith(fresh);
}

function toggleChip(id) {
  const it = item(last.cat, state.kind); const c = chipsFor(it || { fields: [] }).find((x) => x.id === id); if (!c) return;
  let p = String(state.params.prompt || '');
  if (p.includes(c.fragment_en)) p = p.replace(c.fragment_en, '').replace(/,\s*,/g, ',').replace(/^\s*,\s*|\s*,\s*$/g, '').trim();
  else p = [p.trim(), c.fragment_en].filter(Boolean).join(', ');
  state.params.prompt = p;
  const el = document.querySelector('#models-form [data-param="prompt"]'); if (el) el.value = p;
  refreshChips(); invalidatePreview(); cloudReset();
}

// Prompt library (catalog/prompt-library.json) and «Улучшить промпт» via local Assistant (/api/prompts*).
const PFIELD = { acestep: 'tags', qwen3tts: 'instruct' };
const promptField = (it) => { const n = PFIELD[it?.base] || 'prompt'; return it?.fields.some((f) => f.name === n) ? n : null; };
const SRC = { own: 'свои', 'prompts.chat': 'prompts.chat · CC0', civitai: 'Civitai' };

function setPrompt(it, text) {
  const n = promptField(it); if (!n) return;
  state.params[n] = text; state.skeleton = ''; state.task = '';
  const el = document.querySelector(`#models-form [data-param="${n}"]`); if (el) el.value = text;
  document.querySelectorAll('#models-form [data-m-list="task_presets"]').forEach((x) => x.classList.remove('on'));
  refreshChips(); invalidatePreview(); cloudReset();
}

function libBlock(it) {
  if (!promptField(it)) return '';
  const L = state.lib;
  const rows = L.items.map((r, i) => `<li><div><b>${esc(r.title)}</b> ${pill(SRC[r.source] || r.source)}${r.url && r.source !== 'own' ? ` <a href="${esc(r.url)}" target="_blank" rel="noopener">источник</a>` : ''}
      <p>${esc(r.prompt.length > 260 ? r.prompt.slice(0, 260) + '…' : r.prompt)}</p></div>
      <button type="button" class="preset" data-m-lib="${i}">В форму</button></li>`).join('');
  const src = ['', ...Object.keys(SRC)].map((k) => `<option value="${k}"${L.source === k ? ' selected' : ''}>${k ? esc(SRC[k]) : 'все источники'}</option>`).join('');
  const info = L.err ? `<p class="err">${esc(L.err)}</p>` : L.busy ? '<p class="muted">Ищу…</p>'
    : `<p class="muted">Найдено: ${L.total}${L.total > L.items.length ? `, показаны первые ${L.items.length}` : ''}. Подходят к «${esc(it.base_title || it.title)}».</p>`;
  return `<details class="note prompt-lib" id="m-lib"${L.open ? ' open' : ''}><summary>Библиотека промптов</summary>
    <div class="lib-search"><input type="search" id="m-lib-q" placeholder="поиск: кофе, неон, cinematic…" value="${esc(L.q)}"><select id="m-lib-src" aria-label="Источник">${src}</select></div>
    ${info}<ul class="lib-list">${rows}</ul></details>`;
}

function improveBlock(it) {
  if (!promptField(it)) return '';
  const I = state.improve;
  const res = I.res ? `<div class="improve-res"><p><b>Предложение:</b> ${esc(I.res.prompt)}</p>
      ${I.res.why?.length ? `<ul>${I.res.why.map((w) => `<li>${esc(w)}</li>`).join('')}</ul>` : ''}
      <div class="presets"><button type="button" class="preset" data-m-improve-accept>Принять</button><button type="button" class="preset" data-m-improve-drop>Оставить как было</button></div></div>` : '';
  return `<div class="improve" id="m-improve"><div class="presets"><button type="button" class="preset" data-m-improve${I.busy ? ' disabled' : ''}>${I.busy ? 'Улучшаю… (до минуты)' : 'Улучшить промпт'}</button>
    <span class="muted">локальная модель Assistant, без облака</span></div>${I.err ? `<p class="err">${esc(I.err)}</p>` : ''}${res}</div>`;
}

function refreshBlock(id, html) {
  const box = document.getElementById(id); if (!box) return;
  const tmp = document.createElement('div'); tmp.innerHTML = html; const fresh = tmp.firstElementChild; if (fresh) box.replaceWith(fresh);
}

let libSeq = 0;
async function libSearch() {
  const it = item(last.cat, state.kind); if (!it) return;
  const L = state.lib; L.busy = true; L.err = ''; const seq = ++libSeq;
  try {
    const q = new URLSearchParams({ q: L.q, base: it.base || '', source: L.source, limit: 20 });
    const r = await request('/api/prompts?' + q);
    if (seq !== libSeq) return;
    Object.assign(L, { items: r.items, counts: r.counts, total: r.total });
  } catch (err) { L.err = err.message; }
  L.busy = false;
  if (seq === libSeq) {
    const keep = document.activeElement?.id === 'm-lib-q';
    refreshBlock('m-lib', libBlock(it));
    if (keep) { const q = document.getElementById('m-lib-q'); q.focus(); q.setSelectionRange(q.value.length, q.value.length); }
  }
}

async function improvePrompt() {
  const it = item(last.cat, state.kind); const n = promptField(it); if (!n) return;
  const I = state.improve; I.busy = true; I.err = ''; I.res = null; refreshBlock('m-improve', improveBlock(it));
  try { I.res = await request('/api/prompts/improve', { prompt: String(state.params[n] || ''), base: it.base || '', task: state.task || '' }); }
  catch (err) { I.err = err.message; }
  I.busy = false; if (state.kind === it.id) refreshBlock('m-improve', improveBlock(it));
}


function timeChoices(f) {
  const d=f.duration, rule=d.when;
  return rule && String(state.params[rule.field])===rule.equals ? rule.values : d.values;
}
function secondsText(v,f) {
  const selected=Number(state.params[f.duration.fps_field]), fps=selected>0&&Number.isFinite(selected)?selected:f.duration.fps;
  return (Number(v)/fps).toLocaleString('ru-RU',{maximumFractionDigits:1})+' с';
}
function syncControls(it) {
  for(const f of it.fields) {
    if(f.automatic) { delete state.params[f.name]; continue; }
    if(f.fixed!==undefined) state.params[f.name]=f.fixed;
    if(f.duration) {
      const values=timeChoices(f), old=state.params[f.name]??f.default;
      if(!values.some(v=>String(v)===String(old))) {
        const nearest=values.reduce((a,b)=>Math.abs(Number(b)-Number(old))<Math.abs(Number(a)-Number(old))?b:a);
        state.params[f.name]=nearest;
        state.controlNotice='Длительность приведена к доступному значению: '+secondsText(nearest,f)+'.';
      }
    }
  }
  for(const f of it.fields) if(f.linked_to) state.params[f.name]=state.params[f.linked_to];
}
function durationField(f) {
  const values=timeChoices(f), value=state.params[f.name]??f.default, idx=Math.max(0,values.findIndex(v=>String(v)===String(value))), text=secondsText(values[idx],f);
  return '<label class="field wide model-duration" data-duration-wrap="'+esc(f.name)+'"><span class="duration-heading"><span>'+esc(f.duration.label)+'</span><output>'+esc(text)+'</output></span><input type="hidden" data-param="'+esc(f.name)+'" value="'+esc(values[idx])+'"><input type="range" data-duration="'+esc(f.name)+'" min="0" max="'+(values.length-1)+'" step="1" value="'+idx+'" aria-label="'+esc(f.duration.label)+'" aria-valuetext="'+esc(text)+'"'+(values.length===1?' disabled':'')+'><span class="duration-scale"><span>'+esc(secondsText(values[0],f))+'</span><span>До '+esc(secondsText(values.at(-1),f))+'</span></span><small>'+esc(f.duration.note)+'</small></label>';
}
function refreshDurations(it) {
  syncControls(it);
  for(const f of it.fields.filter(x=>x.duration)) {
    const wrap=document.querySelector('[data-duration-wrap="'+f.name+'"]');if(wrap)wrap.outerHTML=durationField(f);
  }
  const note=document.querySelector('[data-control-notice]');if(note)note.textContent=state.controlNotice||'';
}

function field(original) {
  if(original.duration) return durationField(original);
  if(original.automatic) return `<div class="field wide"><span class="field-name">Длительность</span><small>${esc(original.automatic)}</small></div>`;
  const it = item(last.cat,state.kind); const meta = fieldMeta(original,it);
  const f = {...original,label:(original.name==='generate_audio' && it.id.startsWith('h3_') ? original.label : meta.label),help:meta.help || original.help};
  const v = state.params[f.name] ?? '';
  const ru = f.help && Object.hasOwn(HELP_RU, f.help) && HELP_RU[f.help];
  const help = f.help ? `<small${ru && ru !== f.help ? ` title="${esc(f.help)}"` : ''}>${esc(ru || f.help)}</small>` : '';
  const req = f.required ? ' <b class="req">*</b>' : '';
  const name = `<span class="field-name">${esc(f.label)}${req}</span>`;
  if (f.kind === 'upload') {
    const have = state.uploads[f.name] || (state.inputs[f.name] ? { name: state.inputs[f.name] } : null);
    return `<label class="field upload">${name}
      <span class="dropzone"><input type="file" aria-label="${esc(f.label)}" data-input="${esc(f.name)}" accept="${esc(f.accept || '')}">
        <span><b>Перетащите файл</b> или нажмите, чтобы выбрать</span>
        <span class="file-state">${have ? dot('ok') + esc(have.name) + (have.size ? ' · ' + mb(have.size) : '') : ''}</span></span>
      <span class="server-path"><input aria-label="Путь к файлу на сервере: ${esc(f.label)}" type="text" data-input-path="${esc(f.name)}" placeholder="…или путь на локальном узле (workspace/projects\\…)" value="${state.uploads[f.name] ? '' : esc(state.inputs[f.name] || '')}">${help}</span></label>`;
  }
  // UX-12: the prompt field opens the library itself (button after the textarea so a click on the label text still focuses it)
  const pick = f.name === promptField(item(last.cat, state.kind)) ? '<button type="button" class="preset pick" data-m-lib-open>' + svg(ICON.library) + 'Из библиотеки</button>' : '';
  if (f.kind === 'textarea') return `<label class="field wide">${name}${help}<textarea data-param="${esc(f.name)}" rows="${f.name === 'lyrics' ? 8 : 4}">${esc(v)}</textarea>${pick}</label>`;
  if (f.kind === 'select') return `<label class="field">${name}${help}<select data-param="${esc(f.name)}">${(f.choices || []).map((c) => `<option value="${esc(c)}"${String(v) === String(c) ? ' selected' : ''}>${esc(optionLabel(f, c))}</option>`).join('')}</select></label>`;
  if (f.kind === 'bool') return `<label class="field check"><input type="checkbox" data-param="${esc(f.name)}"${v ? ' checked' : ''}> ${esc(f.label)}${help}</label>`;
  if (f.kind === 'number') return `<label class="field">${name}${help}<input type="number" step="${f.step ?? (f.integer ? 1 : 'any')}"${f.min!==undefined ? ` min="${f.min}"` : ''}${f.max!==undefined ? ` max="${f.max}"` : ''} data-param="${esc(f.name)}" value="${esc(v)}"></label>`;
  return `<label class="field">${name}${help}<input type="text" data-param="${esc(f.name)}" value="${esc(v)}"></label>`;
}

// UX-10: aspect presets keep the default frame area and the model's size step ("multiple of N" in the hint, else 32).
const ASPECTS = [['16:9', 16, 9], ['9:16', 9, 16], ['1:1', 1, 1], ['4:3', 4, 3], ['3:4', 3, 4], ['21:9', 21, 9]];
function aspectSizes(it) {
  const w = it.fields.find((f) => f.name === 'width' && f.kind === 'number'); const h = it.fields.find((f) => f.name === 'height' && f.kind === 'number');
  const area = (+w?.default || 0) * (+h?.default || 0); if (!area) return [];
  const step = +(`${w.help || ''} ${h.help || ''}`.match(/multiples? of (\d+)/)?.[1] || 32);
  const snap = (x) => Math.max(step, Math.round(x / step) * step);
  return ASPECTS.map(([name, a, b]) => { const x = Math.sqrt(area * a / b); return { name, w: snap(x), h: snap(area / x) }; });
}
function aspectRow(it) {
  const list = aspectSizes(it); if (!list.length) return '';
  const on = (s) => String(state.params.width) === String(s.w) && String(state.params.height) === String(s.h);
  return `<div class="presets aspects" role="group" aria-label="Пропорции"><span>Кадр:</span>${list.map((s) => `<button type="button" class="preset${on(s) ? ' on' : ''}" data-m-aspect="${s.w}x${s.h}" title="${s.w}×${s.h}">${s.name} <small>${s.w}×${s.h}</small></button>`).join('')}</div>`;
}
function markAspect() {
  document.querySelectorAll('#models-form [data-m-aspect]').forEach((b) => b.classList.toggle('on', b.dataset.mAspect === `${state.params.width}x${state.params.height}`));
}

function presetRow(label, list, key, active) {
  if (!list?.length) return '';
  return `<div class="presets"><span>${label}</span>${list.map((p, i) => `<button type="button" class="preset${active && p.id === active ? ' on' : ''}" data-m-preset="${i}" data-m-list="${key}"${p.note ? ` title="${esc(p.note)}"` : ''}>${esc(p.name)}</button>`).join('')}</div>`;
}

const mainItem = (g) => [...g.items].sort((x, y) => (x.mode_rank ?? 0) - (y.mode_rank ?? 0))[0];

function siblings(cat, it) {
  if (!it.base) return [it];
  return cat.groups.flatMap((g) => g.items).filter((x) => x.base === it.base).sort((x, y) => (x.mode_rank ?? 0) - (y.mode_rank ?? 0));
}

function formCols(it) {
  syncControls(it);
  const selectedVoice=(it.voices||[]).find(v=>state.params.voice_preset===v.name+' · '+v.id);
  const visible=it.fields.filter(f=>(!f.visible_when||Object.entries(f.visible_when).every(([k,v])=>state.params[k]===v))&&!f.linked_to&&f.fixed===undefined&&!(selectedVoice&&['ref_audio','ref_text','voice_rights'].includes(f.name)));
  const main=visible.filter(f=>f.duration||f.automatic||f.main||fieldMeta(f,it).main), advanced=visible.filter(f=>!f.duration&&!f.automatic&&!f.main&&!fieldMeta(f,it).main);
  return '<div class="model-inputs'+(main.filter(f=>f.kind==='upload').length===2?' paired-inputs':'')+'">'+main.filter(f=>!f.visual).map(field).join('')+(selectedVoice?'<div class="voice-preview"><strong>'+esc(selectedVoice.name)+'</strong><audio controls preload="none" src="/api/models/voice/'+encodeURIComponent(selectedVoice.id)+'"></audio><p>'+esc(selectedVoice.description||'')+'</p><small>Образец голоса. '+(selectedVoice.quality_status==='owner_preferred'?'Этот вариант выбран вами.':'Качество новой озвучки нужно оценить прослушиванием.')+'</small></div>':'')+(it.audio_info?'<p class="model-audio-info"><strong>Звук</strong> '+esc(it.audio_info)+'</p>':'')+'<p class="model-control-notice" data-control-notice>'+esc(state.controlNotice||'')+'</p></div>'+
    (advanced.length ? '<details class="model-advanced" data-model-disclosure="advanced"'+(state.formOpen?.advanced?' open':'')+'><summary>Технические настройки <span>Размер и параметры модели</span></summary>'+aspectRow(it)+'<div class="form-grid">'+advanced.filter(f=>!f.visual).map(field).join('')+'</div></details>' : '');
}


function visualBlock(it) {
  const fields=it.fields.filter(f=>f.visual); if(!fields.length) return '';
  const chosen=(it.visual_presets||[]).find(p=>fields.every(f=>(state.params[f.name]||'none')===(p.values[f.name]||'none')));
  const guide=chosen?.use ? '<div class="visual-guide"><p>'+esc(chosen.use)+'</p><dl><dt>Исходник</dt><dd>'+esc(chosen.input)+'</dd><dt>Проверить в результате</dt><dd>'+esc(chosen.check)+'</dd></dl><p class="visual-limit">'+esc(chosen.limit)+'</p></div>' : (chosen?.id==='none'?'':'<p class="visual-limit">Свой набор приёмов. Для одного короткого кадра лучше выбрать одно движение камеры и одно основное действие.</p>');
  const tags=fields.filter(f=>state.params[f.name] && state.params[f.name]!=='none').map(f=>
    '<button type="button" class="preset on" data-visual-remove="'+esc(f.name)+'" aria-label="Убрать: '+esc(f.option_labels[state.params[f.name]])+'">'+esc(f.option_labels[state.params[f.name]])+' ×</button>').join('');
  return '<section class="model-visual" id="m-visual"><label class="field"><span class="field-name">Приём для кадра</span><select data-visual-preset><option value="">Свой набор…</option>'+it.visual_presets.map(p=>'<option value="'+p.id+'"'+(chosen?.id===p.id?' selected':'')+'>'+esc(p.name)+'</option>').join('')+'</select></label>'+guide+
    '<div class="visual-tags" aria-label="Выбранные приёмы">'+(tags||'<small>Стиль не добавлен — используется ваше описание.</small>')+'</div>'+
    '<details data-visual-details><summary>Настроить приём · оптика, ракурс, свет</summary><div class="visual-grid">'+fields.map(f=>'<label class="field"><span class="field-name">'+esc(f.label)+'</span><select data-param="'+f.name+'">'+f.choices.map(c=>'<option value="'+c+'"'+((state.params[f.name]||'none')===c?' selected':'')+'>'+esc(f.option_labels[c])+'</option>').join('')+'</select></label>').join('')+'</div></details>'+
    '<small>Приёмы добавляются к описанию отдельно. Они не меняют сюжет, длительность и звук. Это указания модели, а не оптическая симуляция или готовый эффект монтажа. 35 мм у объектива — фокусное расстояние; у плёнки — формат.</small></section>';
}
function refreshVisual(it) {
  const box=document.getElementById('m-visual'); if(!box)return;
  const open=box.querySelector('details')?.open;
  box.outerHTML=visualBlock(it); document.querySelector('#m-visual details').open=!!open;
  invalidatePreview(); cloudReset();
}
function invalidatePreview() {
  const box=document.querySelector('[data-model-preview]');
  if(box){box.replaceChildren();box.textContent='Настройки изменились. Нажмите «Проверить, что отправится» ещё раз.';}
  if(state.enhanceGate){state.queueBody=null;document.querySelector('#models-form [data-m-queue]')?.remove();}  // a queue offer is for the previewed settings only
  syncGate();
}
// A form opened from «Улучшить видео» runs only after a successful preview of exactly these settings.
const requestSnapshot=()=>JSON.stringify({kind:state.kind,params:state.params,inputs:state.inputs});
const PREVIEW_FIRST='Сначала нажмите «Проверить, что отправится».';
// A reply belongs to the form that sent it: select() and «Улучшить видео» start a new one.
const formOwner=()=>({epoch:selectionEpoch,gate:state.enhanceGate});
const ownsForm=(o)=>o.epoch===selectionEpoch&&o.gate===state.enhanceGate;
// Refresh the results column only: a reply for an older form must not re-render the current one.
async function refreshHistory(){
  const d=await loadModels().catch(()=>null),box=document.querySelector('.model-results');
  if(!d||!box)return;last.runs=d.runs;last.queue=d.queue;box.innerHTML=feed(last);
}
// Keep the preview text and summary above the sticky actions (and the phone navigation under them).
function revealPreview(box){
  const actions=box.closest('form')?.querySelector('.actions');if(!actions)return;
  const coverOf=()=>(parseFloat(getComputedStyle(actions).bottom)||0)+actions.offsetHeight+12;
  const cover=coverOf();box.style.scrollMarginBottom=cover+'px';
  box.scrollIntoView({block:box.offsetHeight+cover+16<=window.innerHeight?'end':'start',behavior:'smooth'});
  // The actions grow later (queue/run message, error, «Встать в очередь»): re-measure and lift the preview again
  // if that growth covered it. Only for this form's box; a replaced form disconnects the observer.
  box._keepClear?.disconnect();
  const owner=formOwner();let lastH=actions.offsetHeight;
  const ro=new ResizeObserver(()=>{
    if(!box.isConnected||!actions.isConnected||!ownsForm(owner)){ro.disconnect();return;}
    const h=actions.offsetHeight,grew=h-lastH;lastH=h;
    box.style.scrollMarginBottom=coverOf()+'px';
    if(grew<=0||box.hidden)return;
    const top=actions.getBoundingClientRect().top,limit=top-12,bottom=box.getBoundingClientRect().bottom;
    // Was clear of the panel's previous top (any gap, even under 12 px): lift it back to the 12 px margin.
    if(bottom>limit&&bottom<=top+grew+0.5&&bottom>0)window.scrollBy(0,Math.ceil(bottom-limit));
  });
  ro.observe(actions);box._keepClear=ro;
}
function previewGate(){const g=state.enhanceGate;return !!g&&g.kind===state.kind&&g.ok!==requestSnapshot();}
function syncGate(){
  const btn=document.querySelector('#models-form [type=submit]'),hint=document.querySelector('#models-form [data-preview-hint]');
  if(!btn||!state.enhanceGate)return;
  const need=previewGate();if(hint)hint.hidden=!need;
  btn.disabled=need||btn.hasAttribute('data-blocked');
}
function requiredError(it) {
  if (it.contract_error) return it.contract_error;
  for(const f of it.fields) {
    if(f.visible_when && !Object.entries(f.visible_when).every(([k,v])=>state.params[k]===v))continue;
    if(!f.required)continue;
    const v=f.kind==='upload'?state.inputs[f.name]:state.params[f.name];
    if(v===undefined || v===null || String(v).trim()==='' || v==='PROMPT') {
      document.querySelector('#models-form [data-param="'+f.name+'"]')?.focus();
      return (f.kind==='upload'?'Добавьте файл «':'Заполните «')+fieldMeta(f,it).label+'»';
    }
  }
  return '';
}

function form(it, cat) {
  const processing = ['video_rife','video_esrgan','seedvr2_upscale_video'].includes(it.id);
  const modeRow = ''; 
  const proj = it.project_presets || [];
  const projBlock = proj.length ? `<details class="note"><summary>Пресеты проектов <span class="count">${proj.length}</span></summary>
      <div class="presets">${proj.map((p, i) => `<button type="button" class="preset" data-m-preset="${i}" data-m-list="project_presets" title="${esc(p.note || '')}">${esc(p.name)}</button>`).join('')}</div>
      <p>Только для своего проекта: ${[...new Set(proj.map((p) => `${p.project} → карточка ${p.card}`))].map(esc).join('; ')}.</p></details>` : '';
  const smoke = it.last_smoke ? `${esc(it.last_smoke.date)} · ${esc(it.last_smoke.status)}${it.last_smoke.wall_seconds ? ' · ' + Math.round(it.last_smoke.wall_seconds) + ' с' : ''}` : 'нет записи';
  const blockers = [];
  if (it.api_present === false) blockers.push('Файл workflow не найден.');
  if (it.models_present === false) blockers.push('Отсутствуют веса: ' + (it.missing_models || it.models || []).join(', '));
  if (cat.lock?.state === 'held' && !it.cloud) blockers.push(`GPU занят: ${cat.lock.owner || ''} ${cat.lock.purpose ? '· ' + cat.lock.purpose : ''}`);
  return `<form class="card models-form${state.serverPaths ? ' show-server-paths' : ''}" id="models-form" data-disclosure-skip data-kind="${esc(it.id)}">
    <div class="model-form-heading"><span class="model-eyebrow">${processing ? 'Обработка видео' : 'Параметры генерации'}</span><h3>${esc(modelName(it))}</h3><span class="model-location">${it.cloud ? 'Облако · платно' : 'Локально'}</span></div>
    <p class="model-purpose">${esc(modelPurpose(it))}${it.cloud && it.group==='video' && videoTasks(it).includes('t2v') && videoTasks(it).includes('i2v') ? '<br>Для видео по тексту оставьте изображения пустыми. Для оживления загрузите первый кадр.' : ''}</p>
    ${it.contract_note ? `<p class="model-audio-info">${esc(it.contract_note)}</p>` : ''}
    ${it.contract_error ? `<p class="err" role="alert">${esc(it.contract_error)}</p>` : ''}
    ${modeRow}

    ${formCols(it)}
    ${visualBlock(it)}
    ${it.fields.some(f=>f.kind==='upload') ? `<button class="model-path-toggle" type="button" data-model-paths aria-pressed="${!!state.serverPaths}">${state.serverPaths ? 'Скрыть пути к файлам' : 'Выбрать файл по пути на сервере'}</button>` : ''}

    ${it.cloud ? cloudCost() + ownerField() : ''}
    <details class="model-save" data-model-disclosure="save"${state.formOpen?.save ? ' open' : ''}><summary>Сохранение · ${esc(state.target?.split('/').pop() || 'без проекта')}</summary>${it.cloud ? '' : targetField()}<label class="field wide">Название генерации<input type="text" id="m-title" value="${esc(state.title)}" placeholder="например: реклама кофе, дубль 2"></label></details>
    ${blockers.length ? `<p class="err">${blockers.map(esc).join('<br>')}</p>` : ''}
    ${it.needs_comfy && !cat.comfy_up ? '<p class="note">ComfyUI запустится вместе с задачей, если GPU свободен.</p>' : ''}
    <div class="model-request-preview"><button type="button" class="secondary" data-preview-request${it.contract_error ? ' disabled' : ''}>Проверить, что отправится</button><div data-model-preview hidden></div></div>
    <div class="actions"><button type="submit"${blockers.length || it.contract_error ? ' disabled data-blocked' : previewGate() ? ' disabled' : ''}>${it.cloud ? cloudButton() : processing ? 'Обработать видео' : 'Создать'}</button>${state.enhanceGate?.kind === it.id ? `<small data-preview-hint${previewGate() ? '' : ' hidden'}>Сначала проверьте, что отправится.</small>` : ''}<span class="form-msg"></span></div>
    <details class="model-assist" data-model-disclosure="assist"${state.formOpen?.assist ? ' open' : ''}><summary>Помощь с описанием и готовые настройки</summary>
    ${presetRow('Сценарии:',it.task_presets,'task_presets',state.task)}${presetRow('Настройки:',it.presets,'presets')}${projBlock}
    ${improveBlock(it)}${chipBlock(it)}${libBlock(it)}</details>
    <details class="note"><summary>О модели и проверках</summary><p>${esc(it.title)}</p>${it.note ? `<p>${esc(it.note)}</p>` : ''}
      <p>${esc(it.about)}</p>
      ${it.license ? `<p><b>Лицензия:</b> ${esc(it.license)}</p>` : ''}${it.vram ? `<p><b>VRAM:</b> ${esc(it.vram)}</p>` : ''}
      <p><b>Проверка запуска:</b> ${smoke}</p>
      ${it.last_smoke?.note ? `<p>${esc(it.last_smoke.note)}</p>` : ''}
      ${it.last_smoke?.receipt ? `<p><b>Квитанция:</b> <code>${esc(it.last_smoke.receipt)}</code></p>` : ''}
      <p>Успешный запуск не означает, что качество результата уже принято.</p>
      ${(it.models || []).length ? `<p><b>Веса:</b> ${it.models.map(esc).join(', ')}</p>` : ''}
      ${it.api ? `<p><b>Workflow:</b> <code>${esc(it.api)}</code></p>` : ''}
    </details></form>`;
}

function output(o) {
  const url = fileUrl(o.path);
  let media = '';
  if (MEDIA.img.test(o.name)) media = `<img src="${url}" loading="lazy" alt="">`;
  else if (MEDIA.video.test(o.name)) media = `<video src="${url}" controls preload="metadata"></video>`;
  else if (MEDIA.audio.test(o.name)) media = `<audio src="${url}" controls preload="none"></audio>`;
  else if (/\.glb$/i.test(o.name)) media = o.size > GLB_MAX ? `<p class="note">3D-файл ${mb(o.size)} — больше ${mb(GLB_MAX)}, просмотр в панели выключен; скачайте его.</p>`
    : `<div class="m3d"><button type="button" class="ghost" data-m3d="${url}">Показать 3D</button></div>`;
  return `<div class="output">${media}<a href="${url}" download="${esc(o.name.split(/[\\/]/).pop())}">${esc(o.name)}</a> <small>${mb(o.size)}</small></div>`;
}

const GROUP_TYPE = { video: 'video', image: 'design', '3d': 'design', music: 'music', voice: 'music' };

// One inline GLB viewer at a time (same vendored three.js as the project file browser); opening another disposes it.
let view3dDispose = null;
const GLB_MAX = 150 * 1024 * 1024;  // bigger GLBs stall the tab; download them instead
async function view3d(btn) {
  const host = btn.parentElement; view3dDispose?.(); view3dDispose = null;
  btn.disabled = true; btn.textContent = 'Загружаю 3D…';
  let renderer, controls, observer, object, gone = false;  // gone: a newer viewer (or Hide) disposed this one mid-load
  const dispose = () => { gone = true; if (view3dDispose === dispose) view3dDispose = null; observer?.disconnect(); controls?.dispose(); object?.traverse((x) => { x.geometry?.dispose(); for (const m of [x.material].flat().filter(Boolean)) { for (const v of Object.values(m)) if (v?.isTexture) v.dispose(); m.dispose(); } }); renderer?.dispose(); renderer?.forceContextLoss(); renderer?.domElement.remove(); btn.disabled = false; btn.textContent = 'Показать 3D'; delete btn.dataset.m3dOpen; };
  view3dDispose = dispose;
  try {
    const vendor = '/static/vendor/three-r186/';
    const [T, { OrbitControls }, { GLTFLoader }] = await Promise.all([import(vendor + 'build/three.module.js'), import(vendor + 'examples/jsm/controls/OrbitControls.js'), import(vendor + 'examples/jsm/loaders/GLTFLoader.js')]);
    const res = await fetch(btn.dataset.m3d); if (!res.ok) throw new Error('файл недоступен');
    if (Number(res.headers.get('content-length')) > GLB_MAX) { res.body?.cancel(); throw new Error('файл слишком большой для просмотра в панели'); }
    object = (await new GLTFLoader().parseAsync(await res.arrayBuffer(), location.origin + '/')).scene;
    if (gone) { dispose(); return; }
    renderer = new T.WebGLRenderer({ antialias: true }); renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); renderer.setClearColor(0x151b20); host.prepend(renderer.domElement);
    const scene = new T.Scene(), camera = new T.PerspectiveCamera(40, 1, 0.01, 10000); scene.add(object, new T.HemisphereLight(0xffffff, 0x536777, 2));
    const light = new T.DirectionalLight(0xffffff, 3); light.position.set(3, 5, 4); scene.add(light);
    const box = new T.Box3().setFromObject(object), r = Math.max(...box.getSize(new T.Vector3()).toArray());
    if (!Number.isFinite(r) || r <= 0) throw new Error('в модели нет видимой геометрии');
    object.position.sub(box.getCenter(new T.Vector3())); camera.position.set(r * 1.4, r * 0.9, r * 1.6); camera.near = r / 1000; camera.far = r * 100;
    controls = new OrbitControls(camera, renderer.domElement); controls.update();
    const draw = () => renderer.render(scene, camera); controls.addEventListener('change', draw);
    observer = new ResizeObserver(() => { const w = host.clientWidth; if (!w) return; renderer.setSize(w, Math.round(w * 0.75), false); camera.aspect = 4 / 3; camera.updateProjectionMatrix(); draw(); }); observer.observe(host);
    btn.disabled = false; btn.textContent = 'Скрыть 3D'; btn.dataset.m3dOpen = '1';
  } catch (e) { dispose(); btn.textContent = `3D-просмотр недоступен: ${e.message}`; }
}
const TYPE_RU = { video: 'Видео', music: 'Музыка', design: 'Дизайн', web: 'Веб', soft: 'Софт', games: 'Игры', office: 'Офис' };
const HIDE = ['prompt', 'lyrics', 'text', 'tags', 'ref_text', 'instruct'];
const runById = (id) => (last.runs || []).find((r) => r.id === id);

// UX-02: pick the project before Run; the run remembers it and the card offers a one-click save there.
// UX-05: paid cloud item — price first (server-side estimate), then «Запустить за $X» sends that price as confirm_usd.
const cloudKey = () => JSON.stringify([state.params, state.inputs]);
const cloudEst = () => (state.cloudEst && state.cloudEst.key === cloudKey() ? state.cloudEst : null);
const cloudButton = () => { const e = cloudEst(); return e ? `Запустить за $${e.usd}` : 'Оценить стоимость'; };
function cloudCost() {
  const e = cloudEst();
  const line = e ? `Цена: $${e.usd} (≈${e.rub} ₽) · ${e.basis}. Лимит проекта ${e.project}: осталось $${e.project_left_usd}.${e.fits ? '' : ' Не хватает лимита.'}` : 'Платный запуск. Сначала панель посчитает цену по тарифу пайплайна (без списаний).';
  return `<p class="note" id="m-cloud-est">${esc(line)}<br><small>Остановка в панели не отменяет задачу на стороне Replicate: резерв лимита сохранится, результат можно забрать командой cloud-fetch.</small></p>`;
}
function ownerField() {
  return `<label class="field wide">Ваша просьба на облачный запуск (дословно, попадёт в квитанцию)<input type="text" id="m-owner" value="${esc(state.ownerRequest || '')}" placeholder="например: сделай короткий тест в облаке для проекта X"></label>`;
}
function cloudReset() {
  if (!state.cloudEst || cloudEst()) return;
  state.cloudEst = null;
  const btn = document.querySelector('#models-form [type=submit]'); const est = document.getElementById('m-cloud-est');
  if (btn) { btn.textContent = cloudButton(); btn.disabled = false; }
  if (est) est.outerHTML = cloudCost();
  const msg = document.querySelector('#models-form .form-msg'); if (msg) msg.textContent = '';
}

function targetField() {
  const P = state.projects; if (!P) return '';
  const all = (P.types || []).flatMap((t) => (P.projects?.[t] || []).map((n) => `${t}/${n}`));
  if (state.target && !all.includes(state.target)) state.target = '';
  const groups = (P.types || []).filter((t) => P.projects?.[t]?.length).map((t) => `<optgroup label="${esc(TYPE_RU[t] || t)}">${P.projects[t].map((n) => `<option value="${esc(t + '/' + n)}"${state.target === t + '/' + n ? ' selected' : ''}>${esc(n)}</option>`).join('')}</optgroup>`).join('');
  return `<label class="field wide">Проект<select id="m-target"><option value="">— без проекта (решу потом)</option>${groups}</select>
    <small class="note">После запуска результат сохраняется в папку проекта generations\\ одной кнопкой на карточке.</small></label>`;
}

function toProjBlock(r) {
  const P = state.toProj; const types = state.projects?.types || Object.keys(TYPE_RU);
  const list = state.projects?.projects?.[P.type] || [];
  const exists = list.includes(P.name.trim());
  return `<div class="to-project" data-disclosure-skip>
    <div class="form-grid">
      <label class="field">Тип<select data-tp="type">${types.map((t) => `<option value="${t}"${t === P.type ? ' selected' : ''}>${esc(TYPE_RU[t] || t)}</option>`).join('')}</select></label>
      <label class="field">Проект<input type="text" data-tp="name" list="tp-list" value="${esc(P.name)}" placeholder="существующий или новый"><datalist id="tp-list">${list.map((n) => `<option value="${esc(n)}">`).join('')}</datalist></label>
    </div>
    <label class="field check" data-mint-send><input type="checkbox" data-tp="deliver"${P.deliver ? ' checked' : ''}> Отправить результат в Assistant («Оперативный чат»)</label>
    <p class="muted" data-tp-hint>${P.name.trim() ? (exists ? `Добавлю в существующий проект workspace/projects\\${esc(P.type)}\\${esc(P.name.trim())}` : `Создам новый проект workspace/projects\\${esc(P.type)}\\${esc(P.name.trim())} + карточку NameNode`) : 'Выберите проект из списка или впишите новое название.'}</p>
    <div class="actions"><button type="button" data-tp-save${P.busy ? ' disabled' : ''}>${P.busy ? 'Сохраняю…' : 'Сохранить в проект'}</button><button type="button" class="ghost" data-tp-cancel>Отмена</button></div>
    ${P.err ? `<p class="err">${esc(P.err)}</p>` : ''}</div>`;
}

function runCard(r) {
  const st = { running: 'warn', done: 'ok', error: 'bad', stopped: '' }[r.status] || '';
  const ru = { running: `идёт ${Math.round((r.elapsed || 0) / 60)} мин`, done: 'готово', error: 'ошибка', stopped: 'остановлен' }[r.status] || r.status;
  const it = item(last.cat, r.kind);
  const model = it ? modelName(it) + ' · ' + variantName(it) : r.kind;
  const inputs = Object.entries(r.inputs || {}).map(([k, v]) => `${k}: ${String(v).split(/[\\/]/).pop()}`).join(' · ');
  const params = Object.entries(r.params || {}).filter(([k]) => !HIDE.includes(k)).map(([k, v]) => `${k}=${v}`).join(' ');
  const text = ['prompt', 'tags', 'instruct', 'text', 'lyrics'].map((k) => r.params?.[k]).find(Boolean);
  const outs = r.outputs || [];
  const dur = r.finished && r.started ? Math.round(r.finished - r.started) : 0;
  const idle = r.status !== 'running';
  const hasSeed = r.params && 'seed' in r.params;
  const msg = state.runMsg[r.id];
  const acts = idle ? `<div class="run-actions">
      <button type="button" class="ghost small" data-run-again="${esc(r.id)}" title="Тот же запуск, те же параметры${hasSeed ? ' и seed' : ''}">↻ Повторить</button>
      ${hasSeed ? `<button type="button" class="ghost small" data-run-again="${esc(r.id)}" data-new-seed title="Те же параметры, случайный seed">↻ Другой вариант</button>` : ''}
      <button type="button" class="ghost small" data-run-edit="${esc(r.id)}" title="Загрузить параметры в форму и поправить">Изменить и повторить</button>
      ${outs.length && r.target && !r.project ? `<button type="button" class="small" data-run-target="${esc(r.id)}" title="Сохранить в ${esc(r.target.type + '/' + r.target.name)}\\generations">→ В «${esc(r.target.name)}»</button>` : ''}
      ${outs.length ? `<button type="button" class="ghost small" data-run-proj="${esc(r.id)}">→ В ${r.target && !r.project ? 'другой ' : ''}проект</button>` : ''}</div>`
    : `<div class="run-actions"><button class="ghost small" data-m-stop="${esc(r.id)}">Остановить</button></div>`;
  return `<div class="card run-card${r.favorite ? ' fav' : ''}" data-run="${esc(r.id)}">
    ${outs.length ? `<div class="outputs${outs.length > 1 ? ' multi' : ''}">${outs.slice(0, 4).map(output).join('')}</div>` : ''}
    ${outs.length > 4 ? `<p class="note">+ ещё ${outs.length - 4} файл(ов) в папке запуска</p>` : ''}
    <h3><span>${dot(st)}${esc(r.title || model)}</span><span class="run-head">${pill(ru, st)}<button type="button" class="star${r.favorite ? ' on' : ''}" data-run-fav="${esc(r.id)}" aria-pressed="${!!r.favorite}" title="${r.favorite ? 'Убрать из избранного' : 'В избранное'}">${r.favorite ? '★' : '☆'}</button></span></h3>
    <p class="note">${esc(model)} · ${when(r.started)}${dur ? ` · ${dur < 120 ? dur + ' с' : Math.round(dur / 60) + ' мин'}` : ''}</p>
    ${text ? `<p class="run-prompt">«${esc(String(text).slice(0, 220))}${String(text).length > 220 ? '…' : ''}»</p>` : ''}
    ${r.project ? `<p class="note">${pill('в проекте', 'ok')} <code>${esc(r.project.dest || r.project.path)}</code>${r.project.delivered ? ' · отправлено в Assistant' : ''}</p>` : ''}
    ${acts}
    ${(r.kind.startsWith("h3_")||r.kind.startsWith("ltx25_"))?'<p class="run-audio-label">'+(r.params?.generate_audio?(r.params.audio_content==='speech'?'Звук · реплика · '+esc(r.params.speech_language||'язык не указан'):r.params.audio_content==='scene'?'Звуки сцены · без речи':r.params.audio_content==='reference'?'Звук по образцу':'Со звуком модели'):'Без звука')+'</p>':''}
    ${enhancementBlock(r, last.cat, esc, enhancementSources.get(r.id))}
    ${r.saved_voice ? `<p class="note">Голос сохранён: ${esc(r.saved_voice.name || r.saved_voice.id || r.saved_voice)}</p>` : ''}
    ${r.voice_save_error ? `<p class="err">Не удалось сохранить голос: ${esc(r.voice_save_error)}</p>` : ''}
    ${msg ? `<p class="${msg.err ? 'err' : 'note'}">${esc(msg.text)}</p>` : ''}
    ${state.toProj?.runId === r.id ? toProjBlock(r) : ''}
    <details class="note"><summary>Параметры и файлы</summary>
      ${params ? `<p class="mono">${esc(params)}</p>` : ''}${inputs ? `<p>${esc(inputs)}</p>` : ''}
      ${outs.length > 4 ? `<div class="outputs">${outs.slice(4).map(output).join('')}</div>` : ''}
      <p><code>${esc(r.out_dir)}</code></p></details>
    ${(r.log_tail || []).length ? `<details class="note"><summary>Лог ${r.status === 'running' ? '(живой)' : ''}</summary><pre>${esc(r.log_tail.join('\n'))}</pre></details>` : ''}</div>`;
}

// P2.1: the shared GPU waiting list (agents and panel); only panel places can be removed here
function queueBlock(queue) {
  if (!queue.length) return '';
  const row = (t) => `<li><b>${t.position}.</b> ${esc(t.title || t.purpose || '')} <span class="note">${esc(t.mine ? 'панель' : t.owner)}${t.state === 'started' ? ' · запускается' : ` · ждёт ${Math.round((t.age_s || 0) / 60)} мин`}${t.note ? ' · ' + esc(t.note) : ''}</span>
    ${t.mine && t.state !== 'started' ? `<button type="button" class="ghost" data-q-leave="${esc(t.id)}">Убрать из очереди</button>` : ''}</li>`;
  return `<details class="note" open><summary>Очередь GPU: ${queue.length}</summary><ol class="gpu-queue">${queue.map(row).join('')}</ol>
    <p class="note">Задачи панели запускаются сами по очереди, когда GPU свободен.</p></details>`;
}

function feed(data) {
  const runs = data.runs || [];
  const fav = runs.filter((r) => r.favorite).length;
  const cur = item(data.cat, state.kind);
  const base = cur && familyKey(cur);
  const mine = (r) => { const x = item(data.cat, r.kind); return (x ? familyKey(x) : r.kind) === base; };
  // UX-11: results of the project chosen in «Сохранять в» — sent there or saved into it
  const tgt = state.target || ''; const tname = tgt.split('/').pop();
  const ofProj = (r) => !!tgt && ((r.target && `${r.target.type}/${r.target.name}` === tgt) || String(r.project?.path || '').replaceAll('\\', '/').endsWith('/' + tgt));
  const inGroup=r=>item(data.cat,r.kind)?.group===state.group;
  const rows = state.feed === 'group' ? runs.filter(inGroup) : state.feed === 'fav' ? runs.filter((r) => r.favorite) : state.feed === 'model' ? runs.filter(mine) : state.feed === 'proj' && tgt ? runs.filter(ofProj) : runs;
  const btn = (k, label, n) => `<button type="button" class="preset${state.feed === k ? ' on' : ''}" aria-pressed="${state.feed === k}" data-feed="${k}">${label} <span class="count">${n}</span></button>`;
  const head = runs.length ? `<div class="presets" role="group" aria-label="Фильтр запусков">${state.group!=='text'?btn('group', 'Этот раздел',runs.filter(inGroup).length):''}${btn('all', 'Все', runs.length)}${btn('fav', svg(ICON.star) + 'Избранное', fav)}${cur ? btn('model', 'Эта модель', runs.filter(mine).length) : ''}${tgt ? btn('proj', svg(ICON.folder) + esc(tname), runs.filter(ofProj).length) : ''}</div>` : '';
  const empty = '<div class="model-empty">'+svg(ICON[state.group]||ICON.video)+'<h3>'+ (runs.length?'Нет результатов с таким фильтром':'Здесь появится результат')+'</h3><p>'+(runs.length?'Выберите другой фильтр истории.':'Выберите задачу, добавьте исходники и нажмите «Создать».')+'</p></div>';
  const own=rows.filter(r=>!SERVICE_RUN.test(r.title||'')), service=rows.filter(r=>SERVICE_RUN.test(r.title||''));
  const selected=rows.find(r=>r.id===state.previewRun)||own[0]||rows[0];
  const histItem=r=>'<button type="button" data-preview-run="'+esc(r.id)+'" aria-pressed="'+(r===selected)+'"><b>'+esc(r.title || modelName(item(last.cat,r.kind)||{title:r.kind,id:r.kind}))+'</b><span>'+esc(({done:'Готово',running:'В работе',error:'Ошибка',stopped:'Остановлено'})[r.status]||r.status)+' · '+esc(when(r.started))+'</span></button>';
  const history=(own.length?'<div class="model-history" aria-label="История генераций">'+own.map(histItem).join('')+'</div>':'')+
    (service.length?'<details class="model-history-service"'+(service.includes(selected)?' open':'')+'><summary>Служебные проверки · '+service.length+'</summary><div class="model-history" aria-label="Служебные проверки">'+service.map(histItem).join('')+'</div></details>':'');
  return `<div class="model-results-heading"><h2>Результаты</h2><span>${runs.length} в истории</span></div>${queueBlock(data.queue || [])}${head}<div class="model-preview">${selected ? runCard(selected) : empty}</div>${history}
    <details class="note"><summary>Папка запусков</summary><code>${esc(data.cat?.runs_root || '')}</code></details>`;
}

async function runAgain(r, newSeed) {
  const params = { ...r.params };
  if (newSeed) params.seed = Math.floor(Math.random() * 2 ** 31);
  state.runMsg[r.id] = { text: 'Запускаю…' }; reload();
  try {
    const res = await request('/api/models/run', { kind: r.kind, params, inputs: r.inputs || {}, title: r.title || '' });
    state.runMsg[r.id] = { text: `Запущен повтор ${res.run.id}${newSeed ? ` (seed ${params.seed})` : ''}` };
  } catch (err) {
    if (err.queue) {  // GPU busy: the repeat waits in the shared list instead
      try { const q = await request('/api/models/run', { kind: r.kind, params, inputs: r.inputs || {}, title: r.title || '', queue: true }); state.runMsg[r.id] = { text: `GPU занят — повтор в очереди, место ${q.ticket.position}` }; }
      catch (e2) { state.runMsg[r.id] = { text: e2.message, err: true }; }
    } else state.runMsg[r.id] = { text: err.message, err: true };
  }
  reload();
}

function editRun(r) {
  const it = item(last.cat, r.kind); if (!it) { state.runMsg[r.id] = { text: 'Модель этого запуска больше не в каталоге', err: true }; reload(); return; }
  state.group = it.group || state.group; state.videoTask='all';state.uiTask='all';state.loc='all'; select(r.kind);state.params=defaults(it);state.inputs={};state.uploads={};state.task='';state.skeleton='';
  for (const f of it.fields) {
    if (f.kind === 'upload') { if (r.inputs?.[f.name]) state.inputs[f.name] = r.inputs[f.name]; }
    else if (r.params?.[f.name] !== undefined) state.params[f.name] = r.params[f.name];
  }
  state.title = r.title || '';
  reload();
  setTimeout(() => document.getElementById('models-form')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 80);
}

async function openToProj(r) {
  const it = item(last.cat, r.kind);
  state.toProj = { runId: r.id, type: r.target?.type || GROUP_TYPE[it?.group || r.group] || 'video', name: r.target?.name || '', deliver: false, busy: false, err: '' };
  if (!state.projects) { try { state.projects = await request('/api/models/projects'); } catch (err) { state.toProj.err = err.message; } }
  reload();
  setTimeout(() => document.querySelector('.to-project [data-tp="name"]')?.focus(), 60);
}

async function saveToProj() {
  const P = state.toProj; if (!P || P.busy) return;
  if (!P.name.trim()) { P.err = 'Укажите проект'; reload(); return; }
  P.busy = true; P.err = ''; reload();
  try {
    const res = await request(`/api/models/runs/${encodeURIComponent(P.runId)}/to-project`, { type: P.type, project: P.name.trim(), deliver: P.deliver });
    const d = res.delivery ? (res.delivery.ok ? ' · поставлено в очередь Assistant' : ' · Assistant: ошибка постановки') : '';
    state.runMsg[P.runId] = { text: `${res.created ? 'Создан проект и сохранено' : 'Сохранено'}: ${res.files.length} файл(ов) + run.json → ${res.dest}${d}${res.warnings?.length ? ' · ' + res.warnings.join('; ') : ''}` };
    state.toProj = null; state.projects = null;
  } catch (err) { P.busy = false; P.err = err.message; }
  reload();
}

function chatCard(cat) {
  const c = cat.chat || {};
  const selected = (c.models || []).find((m) => m.id === state.chatModel);
  const up = selected?.ready && selected?.present;
  const msgs = state.chat.map((m) => `<div class="msg ${m.role}"><b>${m.role === 'user' ? 'Ты' : esc(m.model || 'Модель')}</b><div>${esc(m.content)}</div></div>`).join('');
  return `<div class="card chat-card" data-disclosure-skip><h3><span>${dot(up ? 'ok' : 'warn')}Чат с локальной LLM</span><a class="head-link" href="#studio" title="Чаты с историей, сохранённые в папке проекта">Открыть в Студии →</a></h3>
    <label class="field">Модель на локальном узле<select id="chat-model"${state.chatBusy ? ' disabled' : ''}>${(c.models || []).map((m) => `<option value="${esc(m.id)}"${m.id === state.chatModel ? ' selected' : ''}${m.ready && m.present ? '' : ' disabled'}>${esc(m.name)}${m.ready ? '' : ' — запуск не подтверждён'}</option>`).join('')}</select></label>
    <p class="note">${esc(selected?.note || '')} Модель загружается на запрос и освобождает GPU после ответа. Первый ответ требует времени на загрузку. Без облака.</p>
    ${(c.models || []).filter((m) => !m.ready).map((m) => `<p class="note">${esc(m.name)}: ${esc(m.note)}</p>`).join('')}
    <div class="chat-log" id="chat-log">${msgs || '<p class="note">Сообщений пока нет.</p>'}</div>
    <form id="chat-form" class="chat-form" data-disclosure-skip><textarea id="chat-input" aria-label="Сообщение модели" rows="2" placeholder="Напиши запрос…"${up ? '' : ' disabled'}>${esc(state.chatDraft)}</textarea>
    <div class="actions"><button type="submit"${up && !state.chatBusy ? '' : ' disabled'}>${state.chatBusy ? 'Думает…' : 'Отправить'}</button><button type="button" class="ghost" data-chat-clear>Очистить</button><span class="form-msg"></span></div></form></div>`;
}

export function renderModels(data) {
  last=data; const cat=data.cat||{groups:[]};
  if(pendingKind){const k=pendingKind;pendingKind=null;const pg=cat.groups.find(x=>(x.items||[]).some(it=>it.id===k));if(pg){state.group=pg.key;state.feed='group';state.videoTask='all';state.uiTask='all';state.loc='all';state.previewRun=null;select(k);}}
  if(state.group!=='text' && (!state.kind || !item(cat,state.kind))){const g=cat.groups.find(x=>x.key===state.group)||cat.groups[0];if(g?.items?.length){state.group=g.key;select(mainItem(g).id);}}
  const groups=[...cat.groups,{key:'text',title:'Текст',items:cat.chat?.models||[]}];
  const tabs=groups.map(g=>'<button type="button" class="model-category" aria-pressed="'+(g.key===state.group)+'" data-m-group="'+g.key+'"><span class="category-icon">'+svg(ICON[g.key]||ICON['3d'])+'</span><span>'+esc(g.title)+'<small>'+g.items.length+' вариантов</small></span></button>').join('');
  const full=cat.groups.find(g=>g.key===state.group)||{items:[]};
  const active=state.group==='video'?state.videoTask:(state.uiTask||'all');
  // Local/cloud filter only where a group has both (video, image): cloud runs are paid.
  const byTask=full.items.filter(it=>active==='all'||tasksFor(it).includes(active));
  const mixed=full.items.some(it=>it.cloud)&&full.items.some(it=>!it.cloud), loc=mixed?state.loc:'all';
  const filtered=byTask.filter(it=>loc==='all'||(loc==='cloud')===!!it.cloud);
  const locBtn=(k,label)=>'<button type="button" class="preset'+(loc===k?' on':'')+'" aria-pressed="'+(loc===k)+'" data-m-loc="'+k+'">'+label+' <span class="count">'+byTask.filter(it=>k==='all'||(k==='cloud')===!!it.cloud).length+'</span></button>';
  const locGroup=mixed?'<div class="presets model-loc" role="group" aria-label="Где запускать">'+locBtn('all','Все')+locBtn('local','Локальные')+locBtn('cloud','Облако · платно')+'</div>':'';
  if(state.group!=='text' && !filtered.some(it=>it.id===state.kind)){if(filtered.length)select((state.group==='video'&&active==='v2v'?filtered.find(it=>it.id==='wan22_vace_a14b_v2v'):null)?.id||mainItem({items:filtered}).id,true);else state.kind=null;}
  const cur=item(cat,state.kind);
  for(const f of cur?.cloud?cur.fields:[]){if(f.kind==='select'&&f.choices?.length&&!f.choices.map(String).includes(String(state.params[f.name]??''))){state.params[f.name]=f.default??f.choices[0];state.cloudEst=null;}}
  const families=[];for(const it of filtered){const k=familyKey(it);let f=families.find(x=>x.key===k);if(!f){f={key:k,items:[]};families.push(f);}f.items.push(it);}for(const f of families)f.items.sort((a,b)=>familyRank(a)-familyRank(b));
  const selectedFamily=cur?families.find(f=>f.key===familyKey(cur)):null;
  const option=(value,label,on)=>'<option value="'+esc(value)+'"'+(on?' selected':'')+'>'+esc(label)+'</option>';
  const taskSelect='<label>Что сделать<select data-model-task>'+taskOptions(state.group).filter(([key])=>key==='all'||full.items.some(it=>tasksFor(it).includes(key))).map(([key,label])=>option(key,label,active===key)).join('')+'</select></label>';
  const modelsSelect='<label>Модель<select data-model-select>'+families.map(f=>option(f.items.some(it=>it.id===cur?.id)?cur.id:f.items[0].id,modelName(f.items[0])+(f.items[0].cloud?' · облако, $':' · локально'),f===selectedFamily)).join('')+'</select></label>';
  const variants=selectedFamily?.items||[];
  const variantSelect=variants.length>1?'<label>Режим<select data-model-variant>'+variants.map(it=>option(it.id,variantName(it),it.id===cur.id)).join('')+'</select></label>':'';
  const status=cat.lock?.state==='held'?'GPU занят':cat.lock?.state==='stale'?'Состояние GPU требует проверки':'Нет активной резервации GPU';
  return '<div class="models-workspace"><div class="models-topline"><div class="model-categories" role="group" aria-label="Тип модели">'+tabs+'</div><span class="model-resource" role="status">'+esc(status)+'</span></div>'+
    (state.group==='image'?imageEditBlock():'')+(state.group==='text'?chatCard(cat):'<div class="models-selectors">'+taskSelect+modelsSelect+variantSelect+'</div>'+locGroup+'<div class="model-workbench"><div class="model-inspector">'+(cur?form(cur,cat):'<p>Для этой задачи пока нет подключённых моделей.</p>')+'</div><section class="model-results" aria-label="Результаты генераций">'+feed(data)+'</section></div>')+
    (state.group==='text'?feed(data):'')+cloudBudget(cat.cloud_budget)+'<details class="model-diagnostics"><summary>Подключение и диагностика моделей</summary><p>'+esc(cat.comfy_up?'ComfyUI работает':'ComfyUI запускается вместе с локальной задачей')+'</p>'+engineChecked(cat.engine_checked||[])+'</details></div>';
}

function cloudBudget(b) {
  if (!b) return '';
  if (b.error) return `<p class="err" role="status">${esc(b.error)}</p>`;
  if (!b.configured) return '';
  const money = (n) => Number.isFinite(n) ? `$${n.toFixed(2)}` : 'не сверено';
  const states = { reserved: 'Резерв', submitting: 'Отправляется', submitted: 'В очереди', processing: 'Генерируется', succeeded: 'Готово', failed: 'Ошибка', canceled: 'Отменено', 'submit-unknown': 'Проверить отправку', reconciled: 'Расход учтён' };
  // every finished job without an invoice gets a form, not only the 12 rows shown in the table
  const books = (b.jobs || []).filter((j) => j.actual_usd === null && ['succeeded', 'failed', 'canceled'].includes(j.generation_state || j.state)).map((j) => `<li><details><summary>${esc(j.label || j.id)} · смета ${money(j.estimate_usd)}</summary><form data-m-reconcile="${esc(j.id)}" class="cloud-book">
        <label>Списано, $ <input name="actual_usd" type="number" min="0" step="0.000001" required></label>
        <label>Основание <input name="evidence" minlength="8" required placeholder="строка счёта или ссылка на prediction"></label>
        <button type="submit" class="secondary">Учесть</button> <span class="form-msg" role="status"></span></form></details></li>`);
  const rows = (b.jobs || []).slice(0, 12).map((j) => {
    const state = j.generation_state || j.state;
    const cost = j.actual_usd === null ? ' · расход не сверен' : state === 'failed' && j.actual_usd === 0 ? ' · без списания по правилам сервиса' : '';
    return `<tr><td>${esc(j.label || j.id)}</td><td>${esc(j.project)}</td><td>${esc((states[state] || state) + cost)}</td><td>${money(j.estimate_usd)}</td><td>${money(j.actual_usd)}</td></tr>`;
  }).join('');
  // P2.2: per-project limits; a new or raised limit needs the owner's own words, kept in the ledger
  const limits = (b.projects || []).map((p) => `<li><b>${esc(p.id)}</b>: лимит ${money(p.limit_usd)}, учтено ${money(p.actual_usd)}, в резерве ${money(p.reserved_usd)}</li>`).join('');
  const names = state.projects?.projects?.video || [];
  const limitForm = `<details class="note"><summary>Одобрить лимит проекта</summary><form id="m-cloud-limit" class="cloud-book">
    <label>Проект <select name="project" required>${names.length ? names.map((n) => `<option>${esc(n)}</option>`).join('') : '<option value="">Нет видеопроектов</option>'}</select></label>
    <label>Лимит, $ <input name="limit_usd" type="number" min="0.01" step="0.01" required></label>
    <label>Слова владельца <textarea name="owner_request" rows="2" minlength="12" required placeholder="Как Оператор разрешил расход: цитата"></textarea></label>
    <button type="submit" class="secondary">Одобрить лимит</button> <span class="form-msg" role="status"></span></form></details>`;
  let open = false;
  try { open = localStorage.getItem('models-replicate-budget-open') === 'true'; } catch (_) {}
  const observed = b.provider_observation;
  return `${b.warning ? '<p class="err" role="status">Replicate: мало доступного бюджета — проверьте расходы.</p>' : ''}<details class="card" id="models-replicate-budget"${open ? ' open' : ''}><summary>Replicate · ${observed ? `по последней сверке ${money(observed.balance_usd)}` : `расчётно доступно ${money(b.available_usd)}`} · в резерве ${money(b.reserved_usd)}</summary>
    ${b.warning ? '<p class="err" role="status">Остаток бюджета низкий или исчерпан. Проверьте расходы перед следующим запуском.</p>' : ''}
    ${observed ? `<p class="note">Баланс на сервисе: ${money(observed.balance_usd)}; расход за месяц: ${money(observed.usage_usd)}. Сверка ${esc(new Date(observed.as_of).toLocaleString('ru-RU'))}. Это сохранённые данные, не обновление в реальном времени.</p>` : ''}
    <p class="note">Начальный баланс ${money(b.opening_usd)} — по подтверждению владельца. Расходы, учтённые по отдельным запускам: ${money(b.actual_usd)}. Для новых запусков расчётно доступно ${money(b.available_usd)} с учётом резервов. Расходы вне пайплайна автоматически не учитываются.</p>
    ${rows ? `<div class="table-wrap"><table><thead><tr><th>Ролик</th><th>Проект</th><th>Состояние</th><th>Смета</th><th>Учтено</th></tr></thead><tbody>${rows}</tbody></table></div>` : '<p class="note">Запусков в этом учёте пока нет.</p>'}
    ${books.length ? `<p class="note">Учесть расход по счёту Replicate · ${books.length}</p><ul class="note">${books.join('')}</ul>` : ''}
    ${limits ? `<ul class="note">${limits}</ul>` : '<p class="note">Лимитов по проектам пока нет: облачный запуск недоступен, пока владелец не одобрит лимит.</p>'}
    ${limitForm}
    <p class="note">При неясном ответе API резерв сохраняется. Повторная генерация автоматически не запускается.</p>
  </details>`;
}

// W6: engine passed a test workflow (receipt), but the panel has no launch form for it yet.
function engineChecked(rows) {
  if (!rows.length) return '';
  const li = rows.map((m) => `<li><b>${esc(m.name)}</b> ${tag('type', m.group, { video: 'Видео', image: 'Картинки', '3d': '3D', audio: 'Аудио' }[m.group] || m.group)} <span class="note">${esc(m.purpose || '')}</span>
    <details class="note"><summary>Что проверено</summary><p>${esc(m.smoke)}</p>
    ${m.receipt ? `<p>Квитанция: <code>${esc(m.receipt)}</code></p>` : ''}${m.workflow ? `<p>Workflow: <code>${esc(m.workflow)}</code></p>` : ''}
    <p>Лицензия: ${esc(m.licence || '—')}</p></details></li>`).join('');
  return `<h2>Проверены движком, запуска из панели нет · ${rows.length}</h2>
    <p class="note">Движок прошёл тестовый прогон по квитанции. Это не готовая кнопка: форма запуска появится отдельно.</p>
    <ul class="engine-checked">${li}</ul>`;
}

async function upload(file, name, label) {
  const epoch = selectionEpoch, token = Symbol(name);
  uploadRequests.set(name, token);
  const current = () => epoch === selectionEpoch && uploadRequests.get(name) === token;
  const fd = new FormData(); fd.append('file', file);
  let r;
  try { r = await fetch('/api/models/upload', { method: 'POST', body: fd }); }
  catch (error) { if (!current()) return false; throw error; }
  const data = await r.json().catch(() => ({}));
  // A late upload must not replace a newer file or the input of another model/mode.
  if (!current()) return false;
  if (!r.ok) throw new Error(data.detail || r.statusText);
  state.inputs[name] = data.path; invalidatePreview(); state.uploads[name] = { name: data.name, size: data.size }; cloudReset();
  if (label) label.innerHTML = `${dot('ok')}${esc(data.name)} · ${mb(data.size)}`;
  return true;
}

export function initModels(refresh) {
  document.addEventListener('toggle', (e) => {
    if (e.target.id === 'models-replicate-budget') {
      try { localStorage.setItem('models-replicate-budget-open', String(e.target.open)); } catch (_) {}
    }
  }, true);
  reload = refresh;
  document.addEventListener('input', (e) => {
    const el = e.target;
    if(el.closest('#models-form')) { invalidatePreview(); queueMicrotask(syncGate); }  // re-check after the handlers below update state
    if (el.dataset?.duration !== undefined) {
      const it=item(last.cat,state.kind), f=it.fields.find(f=>f.name===el.dataset.duration), value=timeChoices(f)[Number(el.value)];
      state.params[f.name]=value; syncControls(it); cloudReset();
      const wrap=el.closest('[data-duration-wrap]'), text=secondsText(value,f);wrap.querySelector('output').textContent=text;wrap.querySelector('[data-param]').value=value;el.setAttribute('aria-valuetext',text);
    }
    else if (el.dataset?.param !== undefined) { state.params[el.dataset.param] = el.type === 'checkbox' ? el.checked : el.value; cloudReset(); const current=item(last.cat,state.kind); if(current?.fields.some(f=>(f.duration?.when?.field===el.dataset.param||f.duration?.fps_field===el.dataset.param))) refreshDurations(current); if (el.dataset.param === 'prompt') refreshChips(); if (el.dataset.param === 'width' || el.dataset.param === 'height') markAspect(); }
    else if (el.dataset?.inputPath !== undefined) {
      uploadRequests.delete(el.dataset.inputPath);
      state.inputs[el.dataset.inputPath] = el.value.trim(); delete state.uploads[el.dataset.inputPath];
      const field=el.closest('label'), label=field?.querySelector('.file-state'), file=field?.querySelector('input[type="file"]');
      if(label)label.textContent='';
      if(file)file.value=''; // Selecting the same local file again must trigger change after cancellation.
      cloudReset();
    }
    else if (el.id === 'm-title') state.title = el.value;
    else if (el.id === 'm-owner') state.ownerRequest = el.value;
    else if (el.id === 'chat-input') state.chatDraft = el.value;
    else if (el.dataset?.tp === 'name' && state.toProj) { state.toProj.name = el.value; const h = document.querySelector('[data-tp-hint]'); if (h) { const t = state.toProj.type; const n = el.value.trim(); h.textContent = !n ? 'Выберите проект из списка или впишите новое название.' : (state.projects?.projects?.[t] || []).includes(n) ? `Добавлю в существующий проект workspace/projects\\${t}\\${n}` : `Создам новый проект workspace/projects\\${t}\\${n} + карточку NameNode`; } }
    else if (el.id === 'm-lib-q') { state.lib.q = el.value; clearTimeout(el._t); el._t = setTimeout(libSearch, 300); }
  });
  document.addEventListener('change', async (e) => {
    if(e.target.matches('[data-enhance-source]')) {const r=runById(e.target.dataset.sourceRun);const out=r&&videoOutputs(r)[Number(e.target.value)];if(out)enhancementSources.set(r.id,out.path);return;}
    if(e.target.dataset.param?.startsWith('visual_')) {refreshVisual(item(last.cat,state.kind));return;}
    if(e.target.matches('[data-param="generate_audio"], [data-param="audio_content"]')) {reload();return;}
    if(e.target.matches('[data-param="voice_preset"]')) {uploadRequests.delete('ref_audio');delete state.inputs.ref_audio;delete state.uploads.ref_audio;reload();return;}
    if (e.target.matches('[data-visual-preset]')) {
      const it=item(last.cat,state.kind),p=it.visual_presets.find(p=>p.id===e.target.value); if(!p)return;
      for(const f of it.fields.filter(f=>f.visual))state.params[f.name]=p.values[f.name]||'none';
      refreshVisual(it);return;
    }
    if (e.target.matches('[data-model-task]')) { if(state.group==='video')state.videoTask=e.target.value;else state.uiTask=e.target.value;reload();return; }
    if (e.target.matches('[data-model-select], [data-model-variant]')) { select(e.target.value,e.target.hasAttribute('data-model-variant'));reload();return; }
    if (e.target.id === 'chat-model') { state.chatModel = e.target.value; reload(); return; }
    if (e.target.id === 'm-target') { state.target = store('models-target', e.target.value); if (!state.target && state.feed === 'proj') state.feed = 'all'; reload(); return; }  // the feed's project filter follows it
    if (e.target.id === 'm-lib-src') { state.lib.source = e.target.value; libSearch(); return; }
    if (e.target.dataset?.tp === 'type' && state.toProj) { state.toProj.type = e.target.value; reload(); return; }
    if (e.target.dataset?.tp === 'deliver' && state.toProj) { state.toProj.deliver = e.target.checked; return; }
    const el = e.target;
    if (el.dataset?.input === undefined || !el.files?.length) return;
    const label = el.closest('label')?.querySelector('.file-state');
    if (label) label.textContent = `загружаю ${el.files[0].name}…`;
    try { if (await upload(el.files[0], el.dataset.input, label)) { const p = el.closest('label')?.querySelector('[data-input-path]'); if (p) p.value = ''; } }
    catch (err) { if (label) label.innerHTML = `<span class="err">${esc(err.message)}</span>`; }
  });
  document.addEventListener('click', async (e) => {
    const removeVisual=e.target.closest('[data-visual-remove]');
    if(removeVisual){state.params[removeVisual.dataset.visualRemove]='none';refreshVisual(item(last.cat,state.kind));return;}
    const previewButton=e.target.closest('[data-preview-request]');
    if(previewButton){
      const box=document.querySelector('[data-model-preview]'),it=item(last.cat,state.kind);
      box.hidden=false;const problem=requiredError(it);if(problem){box.textContent=problem;return;}
      const snapshot=requestSnapshot(),gate=state.enhanceGate;
      previewButton.disabled=true;box.textContent='Проверяю параметры…';
      try{
        const r=await request('/api/models/preview',JSON.parse(snapshot));
        if(!box.isConnected||state.enhanceGate!==gate)return;  // a reply for a form that was replaced must not unlock or fill the new one
        if(snapshot!==requestSnapshot()){invalidatePreview();return;}
        if(gate?.kind===state.kind){gate.ok=snapshot;syncGate();}
        const formMsg=document.querySelector('#models-form .form-msg');
        if(formMsg?.textContent===PREVIEW_FIRST){formMsg.textContent='';formMsg.classList.remove('err');}  // only the stale gate error; other errors stay
        const warnings = r.instructions?.template_warnings || [];
        box.innerHTML='<p><strong>'+esc(r.engine)+'</strong> · '+esc(r.note)+'</p>'+(warnings.length ? '<div class="note" role="status" data-model-warnings><strong>Что учесть перед запуском</strong><ul>'+warnings.map(w=>'<li>'+esc(w)+'</li>').join('')+'</ul></div>' : '')+Object.entries(r.texts).map(([name,text])=>'<p><strong>'+esc(it.fields.find(f=>f.name===name)?.label||name)+'</strong></p><pre>'+esc(text||'(пусто)')+'</pre>').join('')+'<details><summary>Параметры и входные файлы</summary><pre>'+esc(JSON.stringify({params:r.params,inputs:r.inputs},null,2))+'</pre></details>';
        requestAnimationFrame(()=>revealPreview(box));
      }catch(err){box.textContent=err.message;}finally{previewButton.disabled=false;}return;
    }

    const b = e.target.closest('button'); if (!b) return;
    if (b.hasAttribute('data-model-paths')) { state.serverPaths=!state.serverPaths;document.getElementById('models-form')?.classList.toggle('show-server-paths',state.serverPaths);b.setAttribute('aria-pressed',String(state.serverPaths));b.textContent=state.serverPaths?'Скрыть пути к файлам':'Выбрать файл по пути на сервере';}
    else if (b.dataset.previewRun) {state.previewRun=b.dataset.previewRun;reload();}
    else if (b.dataset.enhance) {
      const r=runById(b.dataset.sourceRun);
      if(!r)return;
      const choice=enhancementOptions(last.cat).find(c=>c.id===b.dataset.enhance);
      const source=b.closest('.run-enhance')?.querySelector('[data-enhance-source]');
      const out=videoOutputs(r)[Number(source?.value ?? 0)];
      if(!choice || !out){state.runMsg[r.id]={text:'Не удалось открыть обработку. Обновите каталог и выберите исходный ролик ещё раз.',err:true};reload();return;}
      state.group='video';state.videoTask='all';state.uiTask='all';state.loc='all';select(b.dataset.enhance);
      const {model:it,input}=choice;
      state.inputs={ [input.name]:out.path };state.uploads={ [input.name]:{name:out.name || out.path.split(/[\\/]/).pop(),size:out.size} };state.title=(r.title||'Видео')+' · '+modelName(it);
      state.enhanceGate={kind:b.dataset.enhance,ok:null};
      await reload();
      requestAnimationFrame(()=>{const form=document.getElementById('models-form');if(!form)return;form.tabIndex=-1;form.focus({preventScroll:true});form.scrollIntoView({block:'start',behavior:'smooth'});});
    }
    else if (b.dataset.mLoc) { state.loc = b.dataset.mLoc; reload(); }
    else if (b.dataset.mVideoTask) { state.videoTask = b.dataset.mVideoTask; reload(); }
    else if (b.dataset.mGroup) { if(b.dataset.mGroup==='text'&&state.feed==='group')state.feed='all';else if(b.dataset.mGroup!=='text')state.feed='group'; state.previewRun=null; state.videoTask = 'all'; state.uiTask = 'all'; state.loc = 'all'; state.group = b.dataset.mGroup; const g = last.cat.groups.find((x) => x.key === state.group); if (g?.items?.length) select(mainItem(g).id); reload(); }
    else if (b.dataset.mKind) { select(b.dataset.mKind, b.dataset.mMode !== undefined); reload(); }
    else if (b.dataset.m3d) { if (b.dataset.m3dOpen) { delete b.dataset.m3dOpen; view3dDispose?.(); view3dDispose = null; } else view3d(b); }
    else if (b.dataset.mAspect) {
      const [w, h] = b.dataset.mAspect.split('x').map(Number); Object.assign(state.params, { width: w, height: h });
      for (const [k, v] of [['width', w], ['height', h]]) { const el = document.querySelector(`#models-form [data-param="${k}"]`); if (el) el.value = v; }
      markAspect(); invalidatePreview(); cloudReset();
    }
    else if (b.dataset.mPreset !== undefined) {
      const it = item(last.cat, state.kind); const p = it?.[b.dataset.mList || 'presets']?.[+b.dataset.mPreset];
      if (p) applyPreset(it, p);
    } else if (b.dataset.mChip) toggleChip(b.dataset.mChip);
    else if (b.dataset.mLib !== undefined) {
      const r = state.lib.items[+b.dataset.mLib];
      if (r) { setPrompt(item(last.cat, state.kind), r.prompt); const m = document.querySelector('#models-form .form-msg'); if (m) { m.classList.remove('err'); m.textContent = `Промпт из библиотеки: ${r.title}`; } }
      document.querySelector('#models-form [data-m-lib-open]')?.closest('.field')?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    } else if (b.dataset.mLibOpen !== undefined) {
      const lib = document.getElementById('m-lib'); if (!lib) return;
      const assist=lib.closest('.model-assist'); if(assist)assist.open=true;
      lib.open = true; lib.scrollIntoView({ block: 'start', behavior: 'smooth' });  // the toggle listener loads the list
      document.getElementById('m-lib-q')?.focus({ preventScroll: true });
    } else if (b.dataset.mImprove !== undefined) improvePrompt();
    else if (b.dataset.mImproveAccept !== undefined) { const it = item(last.cat, state.kind); if (state.improve.res) setPrompt(it, state.improve.res.prompt); state.improve.res = null; refreshBlock('m-improve', improveBlock(it)); }
    else if (b.dataset.mImproveDrop !== undefined) { state.improve.res = null; refreshBlock('m-improve', improveBlock(item(last.cat, state.kind))); }
    else if (b.dataset.mStop) {
      b.disabled = true;
      try { await request(`/api/models/runs/${encodeURIComponent(b.dataset.mStop)}/stop`, {}); reload(); } catch (err) { b.textContent = err.message.slice(0, 50); }
    } else if (b.dataset.chatClear !== undefined) { state.chat = []; reload(); }
    else if (b.dataset.feed) { state.feed = b.dataset.feed; reload(); }
    else if (b.dataset.qLeave) {
      b.disabled = true;
      try { await request(`/api/gpu/queue/${encodeURIComponent(b.dataset.qLeave)}/leave`, {}); reload(); } catch (err) { b.textContent = err.message.slice(0, 60); }
    } else if (b.dataset.mQueue !== undefined && state.queueBody) {
      const msg = document.querySelector('#models-form .form-msg'), qb = state.queueBody, g = state.enhanceGate, owner = formOwner();
      if (previewGate() || (g && g.ok !== JSON.stringify({ kind: qb.kind, params: qb.params, inputs: qb.inputs }))) { state.queueBody = null; b.remove(); if (msg) { msg.textContent = PREVIEW_FIRST; msg.classList.add('err'); } return; }
      b.disabled = true;
      try {
        const q = await request('/api/models/run', { ...qb, queue: true });
        if (!ownsForm(owner)) { refreshHistory(); return; }  // the form was replaced while waiting: show the ticket in history only
        if (state.queueBody === qb) state.queueBody = null; b.remove(); if (msg) { msg.classList.remove('err'); msg.textContent = `В очереди GPU: место ${q.ticket.position}. Запустится сам, когда GPU освободится.`; }
        setTimeout(() => ownsForm(owner) ? reload() : refreshHistory(), 600);
      } catch (err) { if (!ownsForm(owner)) return; if (msg) { msg.textContent = err.message; msg.classList.add('err'); } b.disabled = false; }
    }
    else if (b.dataset.runFav) {
      const r = runById(b.dataset.runFav); if (!r) return; b.disabled = true;
      try { const res = await request(`/api/models/runs/${encodeURIComponent(r.id)}/mark`, { favorite: !r.favorite }); r.favorite = res.favorite; } catch (err) { state.runMsg[r.id] = { text: err.message, err: true }; }
      reload();
    } else if (b.dataset.runAgain) { const r = runById(b.dataset.runAgain); if (r) runAgain(r, b.dataset.newSeed !== undefined); }
    else if (b.dataset.runEdit) { const r = runById(b.dataset.runEdit); if (r) editRun(r); }
    else if (b.dataset.runProj) { const r = runById(b.dataset.runProj); if (r) openToProj(r); }
    else if (b.dataset.runTarget) { const r = runById(b.dataset.runTarget); if (r?.target) { b.disabled = true; state.toProj = { runId: r.id, type: r.target.type, name: r.target.name, deliver: false, busy: false, err: '' }; saveToProj(); } }  // an error opens the usual «В проект» block
    else if (b.dataset.tpSave !== undefined) saveToProj();
    else if (b.dataset.tpCancel !== undefined) { state.toProj = null; reload(); }
  });
  const zone = (e) => e.dataTransfer?.types?.includes('Files') && e.target.closest?.('#models-form .field.upload');  // text drops keep working in the path input
  document.addEventListener('dragover', (e) => { const z = zone(e); if (!z) return; e.preventDefault(); z.classList.add('drag'); });
  document.addEventListener('dragleave', (e) => { const z = zone(e); if (z && !z.contains(e.relatedTarget)) z.classList.remove('drag'); });
  document.addEventListener('drop', (e) => {
    const z = zone(e); if (!z) return; e.preventDefault(); z.classList.remove('drag');
    const input = z.querySelector('[data-input]'); if (!input || !e.dataTransfer?.files?.length) return;
    input.files = e.dataTransfer.files; input.dispatchEvent(new Event('change', { bubbles: true }));
  });
  document.addEventListener('toggle', (e) => { if(e.target.dataset?.modelDisclosure){state.formOpen ||= {};state.formOpen[e.target.dataset.modelDisclosure]=e.target.open;} if (e.target.id === 'm-lib') { state.lib.open = e.target.open; if (e.target.open && !state.lib.items.length && !state.lib.busy) libSearch(); } }, true);
  // Keep the focused field clear of the sticky «Создать» bar (WCAG 2.4.11 focus not obscured).
  document.addEventListener('focusin', (e) => {
    const el = e.target, bar = el.closest?.('#models-form')?.querySelector('[type=submit]');
    if (!bar || el === bar || el.id === 'models-form') return;
    const r = el.getBoundingClientRect(), b = bar.getBoundingClientRect();
    if (r.height > window.innerHeight / 2) return;
    if (r.bottom > b.top - 8) window.scrollBy(0, Math.min(r.bottom - b.top + 16, r.top - 72));
  });
  document.addEventListener('submit', async (e) => {
    const f = e.target;
    if (f.id === 'm-cloud-limit' || f.dataset?.mReconcile) {
      e.preventDefault();
      const btn = f.querySelector('[type=submit]'); const msg = f.querySelector('.form-msg'); const v = Object.fromEntries(new FormData(f));
      btn.disabled = true; msg.classList.remove('err'); msg.textContent = 'Сохраняю…';
      try {
        if (f.dataset.mReconcile) await request('/api/models/cloud-budget/reconcile', { job: f.dataset.mReconcile, actual_usd: String(v.actual_usd), evidence: v.evidence });
        else await request('/api/models/cloud-budget/project', { project: v.project, limit_usd: String(v.limit_usd), owner_request: v.owner_request });
        msg.textContent = 'Сохранено'; setTimeout(reload, 300);
      } catch (err) { msg.textContent = err.message; msg.classList.add('err'); btn.disabled = false; }
    } else if (f.id === 'models-form') {
      e.preventDefault();
      const btn = f.querySelector('[type=submit]'); const msg = f.querySelector('.form-msg');
      const problem=requiredError(item(last.cat,state.kind));
      if(problem){msg.textContent=problem;msg.classList.add('err');return;}
      if(previewGate()){msg.textContent=PREVIEW_FIRST;msg.classList.add('err');return;}
      const cloud = item(last.cat, state.kind)?.cloud;
      if (cloud && !cloudEst()) {
        btn.disabled = true; msg.classList.remove('err'); msg.textContent = 'Считаю цену…';
        try {
          const key = cloudKey(); const r = await request('/api/models/estimate', { kind: state.kind, params: state.params, inputs: state.inputs });
          state.cloudEst = { ...r, key }; msg.textContent = r.fits ? 'Проверьте цену и подтвердите запуск.' : 'Не хватает лимита проекта.';
          document.getElementById('m-cloud-est').outerHTML = cloudCost(); btn.textContent = cloudButton(); btn.disabled = !r.fits;
        } catch (err) { msg.textContent = err.message; msg.classList.add('err'); btn.disabled = false; }
        return;
      }
      f.querySelector('[data-m-queue]')?.remove();
      const owner = formOwner(); let queued = null;
      btn.disabled = true; msg.classList.remove('err'); msg.textContent = item(last.cat, state.kind)?.needs_comfy && !last.cat.comfy_up ? 'Запускаю ComfyUI и задачу…' : 'Запускаю…';
      try {
        const [type, ...rest] = state.target ? state.target.split('/') : [];
        const body = { kind: state.kind, params: state.params, inputs: state.inputs, title: state.title, target: type ? { type, name: rest.join('/') } : null };
        if (cloud) { body.target = null; body.confirm_usd = cloudEst().usd; body.owner_request = state.ownerRequest || ''; }
        queued = state.queueBody = JSON.parse(JSON.stringify(body));  // a snapshot: later edits must not change what the queue offer sends
        const r = await request('/api/models/run', body);
        // The preview gate lives as long as the form (select() or a new «Улучшить видео» replaces it); a late reply must not touch a newer form.
        if (!ownsForm(owner)) { if (state.queueBody === queued) state.queueBody = null; refreshHistory(); return; }
        msg.textContent = `Запущено: ${r.run.id}`; state.previewRun=r.run.id;state.feed='group'; state.title = ''; state.cloudEst = null; state.ownerRequest = ''; if (state.queueBody === queued) state.queueBody = null;
        setTimeout(() => ownsForm(owner) ? reload() : refreshHistory(), 600);
      } catch (err) {
        if (!ownsForm(owner)) { if (state.queueBody === queued) state.queueBody = null; return; }
        msg.textContent = err.message; msg.classList.add('err'); btn.disabled = false;
        if (err.queue) msg.insertAdjacentHTML('afterend', '<button type="button" class="secondary" data-m-queue>Встать в очередь</button>');
      }
    } else if (f.id === 'chat-form') {
      e.preventDefault();
      const ta = f.querySelector('#chat-input'); const text = ta.value.trim(); if (!text || state.chatBusy) return;
      state.chat.push({ role: 'user', content: text }); state.chatBusy = true; state.chatDraft = ''; ta.value = '';
      reload();
      try {
        const r = await request('/api/models/chat', { messages: state.chat.slice(-12), model: state.chatModel });
        state.chat.push({ role: 'assistant', model: r.model, content: (r.content || '') + (r.truncated ? '\n[Достигнут лимит ответа]' : '') });
      } catch (err) { state.chat.push({ role: 'assistant', content: 'Ошибка: ' + err.message }); }
      state.chatBusy = false; reload();
      setTimeout(() => { const log = document.getElementById('chat-log'); if (log) log.scrollTop = log.scrollHeight; }, 50);
    }
  });
}
