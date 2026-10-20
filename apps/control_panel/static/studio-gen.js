// Phase 1.2: generation form inside the Studio project page. Same catalogue and run API as the «Модели» tab
// (/api/models*), which stays; here the project is the Studio project, examples come from the prompt packs and
// parameters stay folded until asked for.
import { html, useState, useEffect, useRef } from './vendor/htm-3.1.1/standalone.module.js';
import { HELP_RU } from './models-help-ru.js?v=ux10-20261011';

const api = async (path, body) => {
  const r = await fetch(path, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  const d = await r.json().catch(() => ({}));
  if (!r.ok) { const e = new Error(typeof d.detail === 'string' ? d.detail : r.statusText); e.queue = r.headers.get('X-Gpu-Queue') === 'offer'; throw e; }
  return d;
};
const store = { get: (k, d) => { try { return localStorage.getItem(k) || d; } catch { return d; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch {} } };
const fileUrl = (p) => '/api/models/file?path=' + encodeURIComponent(p);
const mb = (n) => n < 1048576 ? Math.max(1, Math.round(n / 1024)) + ' КБ' : (n / 1048576).toFixed(1) + ' МБ';
const STATUS = { running: 'идёт', done: 'готово', error: 'ошибка', stopped: 'остановлен', failed: 'ошибка' };
const rank = (x, y) => (x.mode_rank ?? 0) - (y.mode_rank ?? 0);
const all = (cat) => cat.groups.flatMap((g) => g.items);
const findItem = (cat, kind) => all(cat).find((x) => x.id === kind);
// one row per model: the base's first mode stands for it
const bases = (g) => { const seen = new Map(); for (const it of [...g.items].sort(rank)) if (!seen.has(it.base || it.id)) seen.set(it.base || it.id, it); return [...seen.values()]; };
const modes = (cat, it) => it.base ? all(cat).filter((x) => x.base === it.base).sort(rank) : [it];
const MAIN = (f) => f.kind === 'upload' || f.kind === 'textarea';
const PFIELD = { acestep: 'tags', qwen3tts: 'instruct', wan22_svi_long: 'prompt_1' };
// catalogue titles without base_title are whole specs; the list shows the name, the tooltip the rest
const short = (s) => s.length > 42 ? s.split(/: | \(/)[0].slice(0, 60) : s;

export function defaults(it) {
  const p = {};
  for (const f of it.fields) if (f.kind !== 'upload' && f.default !== undefined && f.default !== null && f.default !== 'PROMPT') p[f.name] = f.default;
  return p;
}

// Why a model cannot start now; an empty list means the button is live.
export function blockers(cat, it) {
  const out = [];
  if (it.api_present === false) out.push('Нет файла workflow.');
  if (it.models_present === false) out.push('Нет весов: ' + (it.missing_models || []).join(', '));
  if (cat.lock?.state === 'held' && !it.cloud) out.push(`GPU занят: ${cat.lock.owner || ''}${cat.lock.purpose ? ' · ' + cat.lock.purpose : ''}`);
  return out;
}

// UX-10 aspect presets: keep the default frame area and the model's size step.
const ASPECTS = [['16:9', 16, 9], ['9:16', 9, 16], ['1:1', 1, 1], ['4:3', 4, 3], ['3:4', 3, 4]];
function aspects(it) {
  const w = it.fields.find((f) => f.name === 'width' && f.kind === 'number'), h = it.fields.find((f) => f.name === 'height' && f.kind === 'number');
  const area = (+w?.default || 0) * (+h?.default || 0); if (!area) return [];
  const step = +(`${w.help || ''} ${h.help || ''}`.match(/multiples? of (\d+)/)?.[1] || 32), snap = (x) => Math.max(step, Math.round(x / step) * step);
  return ASPECTS.map(([name, a, b]) => { const x = Math.sqrt(area * a / b); return { name, w: snap(x), h: snap(area / x) }; });
}

function Field({ f, value, set, have, onFile, onPath }) {
  const ru = f.help && Object.hasOwn(HELP_RU, f.help) && HELP_RU[f.help];
  const help = f.help && html`<small title=${ru && ru !== f.help ? f.help : ''}>${ru || f.help}</small>`;
  const name = html`<span class="field-name">${f.label}${f.required && html` <b class="req">*</b>`}</span>`;
  if (f.kind === 'upload') return html`<label class="field upload">${name}
    <span class="dropzone"><input type="file" accept=${f.accept || ''} onChange=${(e) => e.target.files[0] && onFile(e.target.files[0])} />
      <span><b>Перетащите файл</b> или нажмите, чтобы выбрать</span>
      ${have && html`<span class="file-state">${have.name}${have.size ? ' · ' + mb(have.size) : ''}</span>`}</span>
    <input type="text" placeholder="…или путь на локальном узле (workspace/projects\\…)" value=${have?.size ? '' : (have?.name || '')} onInput=${(e) => onPath(e.target.value.trim())} />${help}</label>`;
  const v = value ?? '';
  if (f.kind === 'textarea') return html`<label class="field wide">${name}${help}<textarea rows=${f.name === 'lyrics' ? 8 : 4} value=${v} onInput=${(e) => set(e.target.value)}></textarea></label>`;
  if (f.kind === 'select') return html`<label class="field">${name}${help}<select value=${String(v)} onChange=${(e) => set(e.target.value)}>${(f.choices || []).map((c) => html`<option value=${c}>${c}</option>`)}</select></label>`;
  if (f.kind === 'bool') return html`<label class="field check"><input type="checkbox" checked=${!!v} onChange=${(e) => set(e.target.checked)} /> ${f.label}${help}</label>`;
  return html`<label class="field">${name}${help}<input type=${f.kind === 'number' ? 'number' : 'text'} step="any" value=${v} onInput=${(e) => set(e.target.value)} /></label>`;
}

function RunRow({ r }) {
  const outs = r.outputs || [];
  return html`<div class="studio-run"><b>${r.title || r.kind || r.id}</b> <span class=${'pill ' + (r.status === 'done' ? 'ok' : r.status === 'running' ? 'warn' : 'bad')}>${STATUS[r.status] || r.status}</span>
    ${r.error && html`<small class="err">${String(r.error).slice(0, 300)}</small>`}
    ${outs.slice(0, 4).map((o) => html`<a href=${fileUrl(o.path)} target="_blank" rel="noopener">${o.name}</a>`)}</div>`;
}

// project: Studio key ('inbox' or '<type>/<name>'); onDone(): a launched run ended, the gallery reloads.
let repeated = 0;  // the last «Повторить» click applied: the form remounts on tab/project switches and must not apply it again
export function GenForm({ project, repeat, onDone }) {
  const [cat, setCat] = useState(null);
  const [group, setGroup] = useState(store.get('studio-gen-group', 'video'));
  const [kind, setKind] = useState(store.get('studio-gen-kind', ''));
  const [params, setParams] = useState({});
  const [inputs, setInputs] = useState({});  // field -> path on Local node (uploaded or typed)
  const [files, setFiles] = useState({});  // field -> {name, size} of an upload
  const [title, setTitle] = useState('');
  const [skeleton, setSkeleton] = useState('');  // prompt prefix of the chosen task preset
  const [pack, setPack] = useState(null);
  const [est, setEst] = useState(null);  // cloud estimate for exactly these params
  const [owner, setOwner] = useState('');
  const [msg, setMsg] = useState(null);
  const [head, setHead] = useState(null);  // «Повторить» result, shown at the top where the gallery scrolls to
  const [busy, setBusy] = useState(false);
  // runs started from this form, newest first; saved {id,status} stubs survive a tab switch until their details arrive
  const [mine, setMine] = useState(() => { try { const s = JSON.parse(store.get('studio-gen-runs', '[]')); return Array.isArray(s) ? s : []; } catch { return []; } });
  const live = useRef(true);
  useEffect(() => () => { live.current = false; }, []);
  const cur = useRef('');  // model shown now: a late examples answer for another model is dropped
  const gen = useRef(0);  // bumped by a model switch: a late upload for the old model is dropped
  const lastBody = useRef(null);  // the refused run body, for «Встать в очередь»
  const up = useRef({});  // field -> latest upload/path edit; an older upload never overwrites a newer choice

  const load = () => api('/api/models').then((c) => { if (live.current) setCat(c); }).catch((e) => setMsg({ err: true, text: e.message }));
  useEffect(() => {
    load();
    const on = () => load(); document.addEventListener('studio:refresh', on);  // the panel's «Обновить»: GPU lock, ComfyUI state
    if (mine.length) api('/api/models/runs?limit=60').then((d) => {  // came back to the tab: fill the stubs, keep runs started meanwhile
      const rows = Array.isArray(d) ? d : d.runs || [];
      if (!live.current) return;
      setMine((m) => m.flatMap((r) => {
        if (r.kind) return [r];  // already a full row (started or polled after mount)
        const n = rows.find((x) => x.id === r.id);
        return n ? [n] : [];
      }));
      // `mine` here is the mount-time list of saved stubs: one that was running and has ended means new files in the gallery
      if (mine.some((s) => s.status === 'running' && rows.find((x) => x.id === s.id && x.status !== 'running'))) onDone?.();
    }).catch(() => {});
    return () => document.removeEventListener('studio:refresh', on);
  }, []);
  useEffect(() => { store.set('studio-gen-runs', JSON.stringify(mine.map((r) => ({ id: r.id, status: r.status })))); }, [mine]);
  const it = cat && (findItem(cat, kind) || bases(cat.groups.find((g) => g.key === group) || cat.groups[0])[0]);
  cur.current = it?.id || '';
  const fieldNames = it ? it.fields.map((f) => f.name).join(',') : '';
  // a model switch resets values (a mode switch keeps those with the same name); examples follow the model
  const pick = (next, keep = false) => {
    setKind(next.id); store.set('studio-gen-kind', next.id); setGroup(next.group); store.set('studio-gen-group', next.group);
    const p = defaults(next), inp = {}, fl = {};
    if (keep) for (const f of next.fields) { if (params[f.name] !== undefined) p[f.name] = params[f.name]; if (inputs[f.name]) { inp[f.name] = inputs[f.name]; if (files[f.name]) fl[f.name] = files[f.name]; } }
    else { setSkeleton(''); setTitle(''); gen.current++; up.current = {}; }
    setParams(p); setInputs(inp); setFiles(fl); setEst(null); setMsg(null); setHead(null);
  };
  useEffect(() => { if (it && it.id !== kind) pick(it); else if (it && !Object.keys(params).length) setParams(defaults(it)); }, [cat]);
  // Phase 1.3 «Повторить» in the gallery: that run's model, parameters, input files and title (applied once per click)
  useEffect(() => {
    if (!cat || !repeat || repeated === repeat.n) return; repeated = repeat.n;
    const next = findItem(cat, repeat.kind);
    if (!next) { setHead({ err: true, text: `Запуск ${repeat.id} сделан не моделью из этой формы (${repeat.kind}) — повторите его там, где запускали.` }); return; }
    pick(next);
    const names = new Set(next.fields.map((f) => f.name)), p = defaults(next), inp = {};
    for (const [k, v] of Object.entries(repeat.params || {})) if (names.has(k)) p[k] = v;
    for (const [k, v] of Object.entries(repeat.inputs || {})) if (names.has(k) && v) inp[k] = String(v);
    setParams(p); setInputs(inp); setTitle(repeat.title || '');
    setHead({ text: `Параметры запуска ${repeat.id} подставлены — проверьте и запустите.` });
  }, [cat, repeat?.n]);
  useEffect(() => {
    if (!it) return; setPack(null); const id = it.id;
    api(`/api/studio/packs?base=${encodeURIComponent(it.base || it.id)}&fields=${encodeURIComponent(fieldNames)}`).then((d) => { if (live.current && cur.current === id) setPack(d); }).catch(() => {});
  }, [it?.id]);
  // poll the runs started here until they end
  const running = mine.some((r) => r.status === 'running');
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => api('/api/models/runs?limit=30').then((d) => {
      const rows = Array.isArray(d) ? d : d.runs || [];
      setMine((m) => m.map((r) => { const n = rows.find((x) => x.id === r.id); if (n && r.status === 'running' && n.status !== 'running') { onDone?.(); load(); } return n || r; }));
    }).catch(() => {}), 4000);
    return () => clearInterval(t);
  }, [running]);

  if (!cat) return html`<p class="note">${msg?.text || 'Загрузка моделей…'}</p>`;
  const g = cat.groups.find((x) => x.key === it.group) || cat.groups[0];
  const block = blockers(cat, it);
  const set = (name) => (v) => { setParams((p) => ({ ...p, [name]: v })); setEst(null); };
  const pf = it.fields.some((f) => f.name === (PFIELD[it.base] || 'prompt')) ? PFIELD[it.base] || 'prompt' : null;
  const [type, ...rest] = project === 'inbox' ? [] : project.split('/');
  const projPresets = it.project_presets || [];  // as in «Модели»: names carry the project ("Мопи · основной")
  const apply = (v) => {
    const [src, i] = v.split(':'); if (!src) return;
    if (src === 'pack') { const ex = pack.examples[+i]; setParams((p) => ({ ...p, ...ex.values })); setSkeleton(''); setMsg({ text: `Пример «${ex.title}» из пакета ${pack.pack.id}${ex.context ? ' — ' + ex.context : ''}. Замените детали на свои.` }); }
    else if (src === 'task') {  // task preset: frame values + an English skeleton in front of the subject text
      const t = it.task_presets[+i], values = { ...t.values };
      if (t.prompt && pf) { let tail = String(params[pf] || ''); if (skeleton && tail.startsWith(skeleton)) tail = tail.slice(skeleton.length).replace(/^,\s*/, ''); values[pf] = [t.prompt, tail].filter(Boolean).join(', '); setSkeleton(t.prompt); }
      setParams((p) => ({ ...p, ...values })); setMsg({ text: `Задача «${t.name}»${t.note ? ': ' + t.note : ''}` });
    } else { const p = (src === 'proj' ? projPresets : it.presets)[+i]; setParams((x) => ({ ...x, ...p.values })); setMsg({ text: `Пресет «${p.name}»${p.note ? ': ' + p.note : ''}` }); }
    setEst(null);
  };
  const upload = async (name, file) => {
    setMsg({ text: `Загружаю ${file.name}…` });
    const g0 = gen.current, tok = up.current[name] = (up.current[name] || 0) + 1;
    try {
      const fd = new FormData(); fd.append('file', file);
      const r = await fetch('/api/models/upload', { method: 'POST', body: fd }), d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d.detail || r.statusText);
      if (!live.current || g0 !== gen.current || up.current[name] !== tok) return;  // the model or this field changed meanwhile
      setInputs((x) => ({ ...x, [name]: d.path })); setFiles((x) => ({ ...x, [name]: { name: d.name, size: d.size } })); setMsg(null);
    } catch (e) { setMsg({ err: true, text: e.message }); }
  };
  const quoted = it.cloud && est && est.key === JSON.stringify(params);
  const submit = async (e) => {
    e.preventDefault(); if (busy || block.length) return;
    setBusy(true); setMsg(null);
    try {
      if (it.cloud && !quoted) {  // UX-05: price first, then «Запустить за $X» sends exactly that price
        const r = await api('/api/models/estimate', { kind: it.id, params });
        setEst({ ...r, key: JSON.stringify(params) }); setMsg({ text: r.fits ? 'Проверьте цену и подтвердите запуск.' : 'Не хватает лимита проекта.', err: !r.fits });
        return;
      }
      const body = { kind: it.id, params, inputs, title, target: type ? { type, name: rest.join('/') } : null };
      if (it.cloud) Object.assign(body, { target: null, confirm_usd: est.usd, owner_request: owner });
      lastBody.current = body;
      setMsg({ text: it.needs_comfy && !cat.comfy_up ? 'Запускаю ComfyUI и задачу…' : 'Запускаю…' });
      const r = await api('/api/models/run', body);
      setMine((m) => [r.run, ...m].slice(0, 6)); setEst(null); setOwner(''); setTitle('');
      setMsg({ text: `Запущено: ${r.run.id}` });
    } catch (x) { setMsg({ err: true, text: x.message, queue: x.queue ? lastBody.current : null }); } finally { setBusy(false); }
  };
  const enqueue = async (body) => {  // P2.1: the shared GPU waiting list; the panel starts the run when its turn comes
    setBusy(true);
    try { const r = await api('/api/models/run', { ...body, queue: true }); setMsg({ text: `В очереди GPU: место ${r.ticket.position}. Запустится сам, когда GPU освободится; очередь видна в «Модели → Запуски».` }); }
    catch (x) { setMsg({ err: true, text: x.message }); } finally { setBusy(false); }
  };

  const main = it.fields.filter(MAIN), side = it.fields.filter((f) => !MAIN(f)), sizes = aspects(it);
  const ms = modes(cat, it);
  const n = (pack?.examples.length || 0) + (it.task_presets || []).length + (it.presets || []).length + projPresets.length;
  const field = (f) => html`<${Field} key=${it.id + f.name} f=${f} value=${params[f.name]} set=${set(f.name)} have=${files[f.name] || (inputs[f.name] ? { name: inputs[f.name] } : null)}
    onFile=${(file) => upload(f.name, file)} onPath=${(p) => { up.current[f.name] = (up.current[f.name] || 0) + 1; setInputs((x) => ({ ...x, [f.name]: p })); setFiles((x) => { const y = { ...x }; delete y[f.name]; return y; }); }} />`;
  return html`<form class="studio-gen" onSubmit=${submit}>
    ${head && html`<p class=${head.err ? 'err' : 'note'}>${head.text}</p>`}
    <div class="presets" role="tablist" aria-label="Что генерируем">${cat.groups.map((x) => html`<button type="button" role="tab" aria-selected=${x.key === g.key}
      class=${'preset' + (x.key === g.key ? ' on' : '')} onClick=${() => x.key !== g.key && pick(bases(x)[0])}>${x.title}</button>`)}</div>
    <div class="studio-gen-row">
      <label class="field">Модель<select value=${(bases(g).find((b) => (b.base || b.id) === (it.base || it.id)) || it).id} onChange=${(e) => pick(findItem(cat, e.target.value))}>
        ${bases(g).map((b) => html`<option value=${b.id} title=${b.title}>${short(b.base_title || b.title)}${b.cloud ? ' · облако, $' : ''}${blockers(cat, b).length ? ' — недоступна' : ''}</option>`)}</select></label>
      ${n > 0 && html`<label class="field">Шаблон<select value="" onChange=${(e) => { apply(e.target.value); e.target.value = ''; }}>
        <option value="">— выбрать (${n}) —</option>
        ${pack?.examples.length > 0 && html`<optgroup label=${'Примеры · ' + pack.pack.id}>${pack.examples.map((x, i) => html`<option value=${'pack:' + i} title=${x.context}>${x.title}</option>`)}</optgroup>`}
        ${(it.task_presets || []).length > 0 && html`<optgroup label="Задачи">${it.task_presets.map((x, i) => html`<option value=${'task:' + i}>${x.name}</option>`)}</optgroup>`}
        ${(it.presets || []).length > 0 && html`<optgroup label="Пресеты модели">${it.presets.map((x, i) => html`<option value=${'preset:' + i}>${x.name}</option>`)}</optgroup>`}
        ${projPresets.length > 0 && html`<optgroup label="Пресеты проекта">${projPresets.map((x, i) => html`<option value=${'proj:' + i}>${x.name}</option>`)}</optgroup>`}
      </select></label>`}
    </div>
    ${ms.length > 1 && html`<div class="presets" role="group" aria-label="Режим"><span>Режим:</span>${ms.map((m) => html`<button type="button" class=${'preset' + (m.id === it.id ? ' on' : '')}
      aria-pressed=${m.id === it.id} title=${m.title} onClick=${() => m.id !== it.id && pick(m, true)}>${m.mode || m.id}</button>`)}</div>`}
    ${it.note && html`<p class="note">${it.note}</p>`}
    ${main.map(field)}
    ${(side.length > 0 || sizes.length > 0) && html`<details class="studio-params"><summary>Параметры <span class="count">${side.length}</span></summary>
      ${sizes.length > 0 && html`<div class="presets aspects" role="group" aria-label="Пропорции"><span>Кадр:</span>${sizes.map((s) => html`<button type="button" title=${s.w + '×' + s.h}
        class=${'preset' + (String(params.width) === String(s.w) && String(params.height) === String(s.h) ? ' on' : '')}
        onClick=${() => { setParams((p) => ({ ...p, width: s.w, height: s.h })); setEst(null); }}>${s.name} <small>${s.w}×${s.h}</small></button>`)}</div>`}
      <div class="form-grid">${side.map(field)}
        <label class="field wide">Название запуска<input type="text" value=${title} placeholder="например: реклама кофе, дубль 2" onInput=${(e) => setTitle(e.target.value)} /></label></div>
      ${pack?.pack?.pattern && html`<p class="note"><b>Схема промпта:</b> ${pack.pack.pattern}</p>`}
    </details>`}
    ${it.cloud ? html`<p class="note">${quoted ? `Цена: $${est.usd} (≈${est.rub} ₽) · ${est.basis}. Лимит ${est.project}: осталось $${est.project_left_usd}.`
        : 'Платный облачный запуск: сначала панель посчитает цену (без списаний).'} Результат ляжет в бюджетный проект облака, не в «${project}». Остановка в панели не отменяет задачу на стороне Replicate.</p>
      <label class="field wide">Ваша просьба на облачный запуск (дословно, в квитанцию)<input type="text" value=${owner} onInput=${(e) => setOwner(e.target.value)} placeholder="например: сделай короткий тест в облаке" /></label>`
      : html`<p class="note">${type ? html`Запуск привяжется к проекту <b>${rest.join('/')}</b> и появится в его галерее; файлы — в папке запусков, копию в папку проекта кладёт «→ В проект» во вкладке «Модели».`
        : html`Без проекта: файлы в <b>${cat.runs_root || 'папке запусков'}</b>, запуск виден здесь, во Входящих.`}${it.needs_comfy && !cat.comfy_up ? ' · ComfyUI запустится вместе с задачей, если GPU свободен.' : ''}</p>`}
    ${block.length > 0 && html`<p class="err">${block.join(' ')}</p>`}
    <div class="actions"><button type="submit" disabled=${busy || block.length > 0 || (it.cloud && quoted && (!est.fits || !owner.trim()))}>
      ${busy ? 'Подождите…' : it.cloud ? (quoted ? `Запустить за $${est.usd}` : 'Оценить стоимость') : 'Запустить'}</button>
      ${msg && html`<span class=${msg.err ? 'err' : 'note'}>${msg.text}</span>`}
      ${msg?.queue && html`<button type="button" class="secondary" disabled=${busy} onClick=${() => enqueue(msg.queue)}>Встать в очередь</button>`}</div>
    ${mine.length > 0 && html`<div class="studio-runs">${mine.map((r) => html`<${RunRow} key=${r.id} r=${r} />`)}</div>`}
  </form>`;
}
