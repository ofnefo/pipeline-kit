// Studio (Phase 1): chats stored in the project folder, Inbox for unsorted work. Preact+htm, vendored, Studio only.
import { html, render, useState, useEffect, useRef } from './vendor/htm-3.1.1/standalone.module.js';
import { Montage } from './studio-montage.js?v=c3-20261019';

const api = async (path, body) => {
  const r = await fetch(path, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof d.detail === 'string' ? d.detail : r.statusText);
  return d;
};
// Phase 1: a POST answered with server-sent events; errors before the stream starts throw like api().
const sse = async (path, body, onEvent) => {
  const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  if (!r.ok) { const d = await r.json().catch(() => ({})); throw new Error(typeof d.detail === 'string' ? d.detail : r.statusText); }
  const reader = r.body.getReader(), dec = new TextDecoder();
  let buf = '';
  for (;;) {
    const { value, done } = await reader.read();
    if (done) return;
    buf += dec.decode(value, { stream: true });
    for (let i; (i = buf.indexOf('\n\n')) >= 0; buf = buf.slice(i + 2)) {
      const block = buf.slice(0, i), kind = /^event: (.*)$/m.exec(block), data = /^data: (.*)$/m.exec(block);
      if (kind && data) onEvent(kind[1], JSON.parse(data[1]));
    }
  }
};
const TIER = { local: 'локально', subscription: 'подписка', paid: 'платно' };
const TIER_GROUP = [['local', 'Локально'], ['subscription', 'Подписка'], ['paid', 'Платно']];
const usd = (n) => '$' + (n < 0.01 ? n.toFixed(4) : n.toFixed(2));
const q = (key) => 'project=' + encodeURIComponent(key);
const store = { get: (k, d) => { try { return localStorage.getItem(k) || d; } catch { return d; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch {} } };
const when = (ts) => new Date(ts * 1000).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
const label = (meta, key) => key === 'inbox' ? 'Входящие' : key.replace('/', ' · ');
const fileUrl = (p) => '/api/models/file?path=' + encodeURIComponent(p);
const IMG = /\.(png|jpe?g|webp|gif)$/i, VID = /\.(mp4|webm|mov)$/i, AUD = /\.(wav|flac|mp3|ogg|m4a)$/i;
const STATUS = { running: 'идёт', done: 'готово', error: 'ошибка', stopped: 'остановлен' };
// UX-42: one project page. #studio/<type>/<name> opens that project (the «Проекты» rows link here).
const fromHash = () => { const m = /^#(?:studio|montage)\/(.+)$/.exec(location.hash); try { return m ? decodeURIComponent(m[1]) : ''; } catch { return ''; } };
// 3.0: generation lives only in «Модели»; montage is its own section (#montage). Studio keeps chats, results and files.
const TABS = [['chats', 'Чаты'], ['gen', 'Результаты'], ['files', 'Файлы']];
const TYPE_RU = { video: 'Видео', music: 'Музыка', design: 'Дизайн', web: 'Веб', soft: 'Софт', games: 'Игры', office: 'Офис' };

// A7: smoke/benchmark projects are hidden from the list (only the selected one stays, in a last group); names shared by two types get the type
const TEST_PROJECT = /smoke|benchmark|(^|-)cpu(-|$)|(^|-)test(-|$)/i;
function ProjectSelect({ meta, value, onChange, skip, id, title, disabled, placeholder }) {
  const seen = {};
  meta.types.forEach((t) => (meta.projects[t] || []).forEach((n) => { seen[n] = (seen[n] || 0) + 1; }));
  const opt = (t, n) => html`<option value=${`${t}/${n}`}>${seen[n] > 1 ? `${n} (${TYPE_RU[t] || t})` : n}</option>`;
  const rows = (t, test) => (meta.projects[t] || []).filter((n) => `${t}/${n}` !== skip && TEST_PROJECT.test(n) === test);
  const tests = meta.types.flatMap((t) => rows(t, true).filter((n) => `${t}/${n}` === value).map((n) => [t, n]));
  return html`<select id=${id} title=${title} disabled=${disabled} value=${value} onChange=${(e) => onChange(e.target.value)}>
    ${placeholder && html`<option value="">${placeholder}</option>`}
    ${skip !== 'inbox' && html`<option value="inbox">Входящие</option>`}
    ${meta.types.map((t) => rows(t, false).length > 0 && html`<optgroup label=${TYPE_RU[t] || t}>
      ${rows(t, false).map((n) => opt(t, n))}</optgroup>`)}
    ${tests.length > 0 && html`<optgroup label="Тесты и смоук">${tests.map(([t, n]) => opt(t, n))}</optgroup>`}
  </select>`;
}

function Output({ o }) {
  const url = fileUrl(o.path), n = o.name || '';
  return html`<div class="output">${IMG.test(n) ? html`<img src=${url} loading="lazy" alt="" />` : VID.test(n) ? html`<video src=${url} controls preload="metadata"></video>`
    : AUD.test(n) ? html`<audio src=${url} controls preload="none"></audio>` : null}<a href=${url} download=${n.split(/[\\/]/).pop()}>${n}</a></div>`;
}

// Phase 1.3: a run as text for the chat draft: what was asked and where its files are
const PROMPT_KEYS = ['prompt', 'tags', 'instruct', 'prompt_1', 'text'];
const runText = (r) => {
  const k = PROMPT_KEYS.find((x) => typeof r.params[x] === 'string' && r.params[x].trim());
  return [`Генерация «${r.title || r.kind}» (${r.kind}, запуск ${r.id})`, k && `${k}: ${r.params[k].trim()}`, ...r.outputs.map((o) => `Файл: ${o.path}`)].filter(Boolean).join('\n');
};
const slash = (s) => String(s || '').replace(/\\/g, '/');
const inside = (path, root) => { const a = slash(path), b = slash(root).replace(/\/$/, '') + '/'; return a.toLowerCase().startsWith(b.toLowerCase()) ? a.slice(b.length) : ''; };

// Phase 1.3: «В проект» copies the run into <project>\generations (the same action as in «Модели», no Assistant delivery);
// «В монтажную» opens a video from that copy, saving it first if needed; «Повторить» opens that model in «Модели»; «В чат» puts the run into the chat draft.
function RunActions({ r, ov, meta, project, onRepeat, onChat, onSaved, say }) {
  const [to, setTo] = useState('');
  const [busy, setBusy] = useState(false);
  if (r.status === 'running') return null;
  const here = r.saved && inside(r.saved, ov.path) ? r.saved : '';  // a copy in this project's folder (not in another one)
  const save = (key) => { const [type, ...rest] = key.split('/'); return api(`/api/models/runs/${encodeURIComponent(r.id)}/to-project`, { type, project: rest.join('/'), deliver: false }); };
  const act = async (fn) => { if (busy) return; setBusy(true); say(null); try { await fn(); } catch (e) { say({ err: true, text: e.message }); } finally { setBusy(false); } };
  const keep = (key) => act(async () => { const d = await save(key); say({ text: `Сохранено в ${d.dest}${d.warnings?.length ? ' · ' + d.warnings.join('; ') : ''}` }); onSaved(); });
  const montage = (o) => act(async () => {
    let source = o.copy || '';  // the server maps it from <copy>\run.json: clashing names were renamed on save
    if (!source && here) throw new Error('Копия этого файла не найдена в run.json папки проекта — откройте её во вкладке «Файлы»');
    if (!source) { const d = await save(project); source = inside((d.files.find((f) => slash(f.source).toLowerCase() === slash(o.path).toLowerCase()) || {}).path, ov.path); onSaved(); }
    if (!source) throw new Error('Файл не найден в папке проекта');
    location.href = '/static/video-review.html?' + new URLSearchParams({ project: ov.montage, source });
  });
  const vids = ov.montage && r.status === 'done' ? r.outputs.filter((o) => VID.test(o.name || '')) : [];
  return html`<div class="run-actions">
    <button type="button" class="ghost small" disabled=${busy} title="Открыть эту модель в разделе «Модели»" onClick=${() => onRepeat(r)}>Повторить в Моделях</button>
    <button type="button" class="ghost small" disabled=${busy} title="Добавить промпт и пути файлов в черновик чата" onClick=${() => onChat(r)}>В чат</button>
    ${here ? html`<small class="note" title=${here}>✓ в папке проекта</small>`
      : r.status !== 'done' ? null
      : project !== 'inbox' ? html`<button type="button" class="ghost small" disabled=${busy} title="Скопировать файлы и run.json в generations проекта" onClick=${() => keep(project)}>В проект</button>`
      : html`<details class="run-to"><summary>В проект…</summary><${ProjectSelect} meta=${meta} value=${to} skip="inbox" onChange=${setTo} title="Куда сохранить" placeholder="— проект —" />
          <button type="button" class="ghost small" disabled=${!to || busy} onClick=${() => keep(to)}>Сохранить</button></details>`}
    ${vids.map((o) => html`<button type="button" class="ghost small" disabled=${busy} title=${here ? 'Открыть копию в монтажной' : 'Сохранить в проект и открыть в монтажной'}
      onClick=${() => montage(o)}>В монтажную${vids.length > 1 ? ': ' + o.name : ''}</button>`)}
  </div>`;
}

function Gallery({ ov, ...act }) {
  const [note, say] = useState(null);
  if (!ov.runs.length) return html`<p class="note">Результатов в этом проекте пока нет. Генерации запускаются в разделе <a href="#models">«Модели»</a> — при запуске выберите этот проект.</p>`;
  return html`${note && html`<p class=${note.err ? 'err' : 'note'}>${note.text}</p>`}<div class="grid runs">${ov.runs.map((r) => html`<div class="card run-card" key=${r.id}>
    <b>${r.title || r.kind}</b><small class="note">${when(r.started)} · ${STATUS[r.status] || r.status}${r.favorite ? ' · ★' : ''}</small>
    <div class=${'outputs' + (r.outputs.length > 1 ? ' multi' : '')}>${r.outputs.map((o) => html`<${Output} o=${o} />`)}</div>
    ${r.count > 4 && html`<small class="note">и ещё ${r.count - 4} — в разделе «Модели»</small>`}
    <${RunActions} r=${r} ov=${ov} say=${say} ...${act} /></div>`)}</div>`;
}

function Files({ ov, project }) {
  return html`<p>Папка проекта: <code>${ov.path}</code></p>
    <p><button type="button" data-file-browser-open data-file-browser-start=${project === 'inbox' ? '_inbox' : project}>Открыть файлы проекта</button></p>
    <p class="note">Плеер, отчёты, теги и история изменений — в том же окне, что и в «Проектах».</p>`;
}

// Phase 1: read-only GPU/queue bar. Polls every 10 s while the page is visible; no buttons — actions stay on the GPU tab.
const gb = (n) => (n / 1024).toFixed(1);
const ago = (s) => s == null ? '' : s < 60 ? `${Math.round(s)} с` : s < 3600 ? `${Math.round(s / 60)} мин` : `${(s / 3600).toFixed(1)} ч`;
function GpuBar() {
  const [d, setD] = useState(null), [fail, setFail] = useState('');
  useEffect(() => {
    let live = true, ctl = null;  // one request at a time, aborted after 15 s or on unmount
    const load = async () => {
      if (ctl || document.visibilityState !== 'visible') return;
      const mine = ctl = new AbortController(), t = setTimeout(() => mine.abort(), 15000);
      try {
        const r = await fetch('/api/studio/gpu', { signal: mine.signal }), x = await r.json().catch(() => null);
        if (!r.ok) throw new Error(typeof x?.detail === 'string' ? x.detail : r.statusText);
        if (!x) throw new Error('ответ не JSON');
        if (live) { setD(x); setFail(''); }
      } catch (e) { if (live) setFail(e.name === 'AbortError' ? 'нет ответа 15 с' : e.message); }
      finally { clearTimeout(t); ctl = null; }
    };
    load();
    const t = setInterval(load, 10000);
    document.addEventListener('visibilitychange', load);
    return () => { live = false; clearInterval(t); document.removeEventListener('visibilitychange', load); ctl?.abort(); };
  }, []);
  if (!d) return html`<div class="studio-gpu note">${fail ? 'GPU: нет данных — ' + fail : 'GPU: загрузка…'}</div>`;
  const { lock = {}, gpu, comfy = {}, runs = [], queue = [] } = d;
  const st = lock.unreadable ? 'warn' : lock.state === 'held' ? 'bad' : lock.state === 'stale' ? 'warn' : 'ok';
  const who = lock.unreadable ? 'Замок GPU есть, но не читается' : lock.state === 'free' ? 'GPU свободна'
    : lock.state === 'stale' ? `Замок GPU брошен: ${lock.owner || '?'}` : `GPU занята: ${lock.owner || '?'}`;
  const busy = comfy.state !== 'running' ? 'ComfyUI остановлен' : comfy.running == null ? 'ComfyUI работает, очередь неизвестна'
    : `ComfyUI: ${comfy.running} идёт · в очереди ${comfy.pending ?? 0}`;
  return html`<details class="studio-gpu">
    <summary><span><i class=${'dot ' + st}></i>${who}</span>
      <span>${gpu ? `VRAM ${gb(gpu.vram_used_mb)}/${Math.round(gpu.vram_total_mb / 1024)} ГБ · ${gpu.util_pct}%` : 'VRAM: nvidia-smi не ответил'}</span>
      <span>${busy}</span>${runs.length ? html`<span>Запуски панели: ${runs.length}</span>` : ''}${queue.length ? html`<span>Очередь GPU: ${queue.length}</span>` : ''}
      ${fail && html`<span class="err" title=${fail}>устарело</span>`}</summary>
    <div class="studio-gpu-more">
      ${lock.state !== 'free' && html`<p>${lock.purpose || 'Без описания'}${lock.age_s != null ? ` · держит ${ago(lock.age_s)}` : ''}${lock.agent && lock.agent !== lock.owner ? ` · ${lock.agent}` : ''}</p>`}
      ${runs.length ? html`<ul class="plain">${runs.map((r) => html`<li>${r.title}${r.project ? ` · ${r.project}` : ''}${r.cloud ? ' · облако' : ''}${r.elapsed != null ? ` · ${ago(r.elapsed)}` : ''}</li>`)}</ul>`
        : html`<p>Панель сейчас ничего не запускает.</p>`}
      ${queue.length > 0 && html`<p>Очередь GPU (агенты и панель):</p><ol class="plain">${queue.map((t) => html`<li>${t.title || t.purpose || 'без описания'} · ${t.mine ? 'панель' : t.owner}${t.state === 'started' ? ' · запускается' : ''}</li>`)}</ol>`}
      <p class="note">Одна тяжёлая GPU-задача за раз. Остановить или запустить ComfyUI — во вкладке <a href="#gpu">GPU</a>. Обновлено ${new Date(d.read_at * 1000).toLocaleTimeString('ru-RU')}.</p>
    </div></details>`;
}

function Studio({ mode }) {
  const [meta, setMeta] = useState(null);
  // Montage keeps its own last project and prefers a video project (only those have a montage).
  const pkey = mode === 'montage' ? 'montage-project' : 'studio-project';
  const [project, setProject] = useState(fromHash() || store.get(pkey, 'inbox'));
  const fromLink = useRef(!!fromHash());
  const [tab, setTab] = useState(() => { if (mode === 'montage') return 'montage'; const t = store.get('studio-tab', 'chats'); return TABS.some(([k]) => k === t) ? t : 'chats'; });
  const [ov, setOv] = useState(null);
  const [chats, setChats] = useState([]);
  const [chat, setChat] = useState(null);
  const [model, setModel] = useState(store.get('studio-model', 't-lite'));
  const [draft, setDraft] = useState('');
  const [pending, setPending] = useState('');
  const [answer, setAnswer] = useState('');  // streamed text of the pending answer
  const [quote, setQuote] = useState(null);  // paid route: the estimate the owner sees before sending
  const [err, setErr] = useState('');
  const [moveTo, setMoveTo] = useState('');
  const [title, setTitle] = useState(null);
  const log = useRef(null);
  const cur = useRef(project); cur.current = project;  // drop answers that arrive after a project switch
  const [op, setOp] = useState(false);  // rename/move in flight
  const inflight = useRef(false);  // synchronous twin of op: a double click or Enter+blur fires before the re-render
  const busy = !!pending || op;
  const gen = useRef(0);  // each open/mutation bumps it; an older chat GET never overwrites newer state

  const fail = (e, key = cur.current) => { if (key === cur.current) setErr(e.message); };  // errors from a previous project stay hidden
  useEffect(() => { api('/api/studio/meta').then((m) => {
    const ok = m.models.filter((x) => x.available);
    if (ok.length && !ok.some((x) => x.id === model)) setModel(ok[0].id);  // stored model gone → first ready one
    setMeta(m);
  }).catch(fail); }, []);
  const loadChats = (key = project) => api('/api/studio/chats?' + q(key)).then((d) => { if (key === cur.current) setChats(d.chats); return key === cur.current ? d.chats : []; });
  const ovGen = useRef(0);  // only the newest overview request may paint (A→B→A switches overlap)
  const loadOv = (key = project) => { const g = ++ovGen.current; return api('/api/studio/overview?' + q(key)).then((d) => { if (g === ovGen.current && key === cur.current) setOv(d); }).catch((e) => { if (g === ovGen.current) fail(e, key); }); };
  // A7: #studio/<name> without a type (old links) waits for meta and resolves to the only matching type
  const hashNote = useRef('');
  const needsType = (p) => p !== 'inbox' && !p.includes('/');
  useEffect(() => {
    if (!meta || !needsType(project)) return;
    const hits = meta.types.flatMap((t) => (meta.projects[t] || []).filter((n) => n.toLowerCase() === project.toLowerCase()).map((n) => `${t}/${n}`));
    if (hits.length !== 1) hashNote.current = hits.length ? `«${project}» есть в нескольких типах: ${hits.map((h) => label(meta, h)).join(', ')} — выберите проект в списке` : `Проект «${project}» не найден — открыты Входящие`;
    setProject(hits.length === 1 ? hits[0] : 'inbox');
  }, [meta, project]);
  useEffect(() => {
    if (mode !== 'montage' || !meta || fromLink.current || project.startsWith('video/')) return;
    const v = (meta.projects.video || []).find((n) => !TEST_PROJECT.test(n));
    if (v) setProject('video/' + v);
  }, [meta]);
  useEffect(() => {
    if (needsType(project)) return;
    history.replaceState(null, '', (mode === 'montage' ? '#montage/' : '#studio/') + project.split('/').map(encodeURIComponent).join('/'));
    setOv(null); loadOv(project);
    const note = hashNote.current; hashNote.current = '';
    store.set(pkey, project); setChat(null); setErr(note);
    loadChats(project).then((rows) => rows[0] && !note && open(rows[0].id, project)).catch((e) => { if (project === cur.current) setChats([]); fail(e, project); });
  }, [project]);
  useEffect(() => { if (log.current) log.current.scrollTop = log.current.scrollHeight; }, [chat, pending, answer]);

  const open = (id, key = project) => { const g = ++gen.current; return api(`/api/studio/chats/${id}?` + q(key)).then((d) => { if (key === cur.current && g === gen.current) { setChat(d); setTitle(null); setErr(''); } }).catch((e) => { if (g === gen.current) fail(e, key); }); };
  const create = async () => { gen.current++; try { const d = await api('/api/studio/chats', { project }); setChat(d); await loadChats(); } catch (e) { fail(e); } };
  const sel = meta?.models.find((m) => m.id === model);
  const paid = sel?.tier === 'paid';
  const quoted = paid && quote && quote.model === model && quote.text === draft.trim();
  // Phase 1: the answer streams in; a paid route first shows its price and sends only with that confirmed price.
  const send = async (e) => {
    e?.preventDefault(); const text = draft.trim(); if (!text || busy || !chat || !sel?.available) return;
    if (paid && !quoted) return once(async () => setQuote({ ...await api(`/api/studio/chats/${chat.id}/estimate`, { project, content: text, model }), text }));
    const key = project, id = chat.id, before = chat.messages.length;
    let done = null, error = null;
    setPending(text); setAnswer(''); setDraft(''); setErr(''); gen.current++;
    try {
      await sse(`/api/studio/chats/${id}/stream`, { project, content: text, model, ...(paid ? { confirm_usd: quote.usd } : {}) }, (k, d) => {
        if (k === 'delta') setAnswer((a) => a + d.text); else if (k === 'done') done = d; else if (k === 'error') error = d;
      });
      if (error) throw Object.assign(new Error(error.message), { saved: error.saved });
      if (!done) throw new Error('Поток ответа оборвался');
      if (key === cur.current) setChat(done);
      if (done.messages.length === before) setDraft(text);  // stopped before any text: nothing saved, the draft returns
      await loadChats(key);
    } catch (x) {
      if (x.saved) open(id, key); else setDraft(text);  // a failed answer keeps either the received text or the draft
      fail(x, key);
    }
    setPending(''); setAnswer(''); setQuote(null);
  };
  const stopAnswer = () => chat && api(`/api/studio/chats/${chat.id}/stop`, {}).catch(fail);
  const once = async (fn) => {
    if (inflight.current || pending) return; inflight.current = true; setOp(true); gen.current++;
    try { await fn(); } catch (e) { fail(e); } finally { inflight.current = false; setOp(false); }
  };
  const rename = () => {
    const t = (title || '').trim(); setTitle(null); if (!t || t === chat.title) return;
    return once(async () => { setChat(await api(`/api/studio/chats/${chat.id}/rename`, { project, title: t })); await loadChats(); });
  };
  const move = () => moveTo && once(async () => { await api(`/api/studio/chats/${chat.id}/move`, { project, to: moveTo }); setMoveTo(''); setProject(moveTo); });
  // The panel's «Обновить» button reloads data in place instead of remounting, so the draft and a pending answer survive.
  const reload = useRef(null);
  reload.current = () => {
    api('/api/studio/meta').then(setMeta).catch(fail);
    loadChats(project).catch((e) => fail(e, project));
    loadOv(project);
    if (chat && !busy) open(chat.id, project);
  };
  useEffect(() => { const on = () => reload.current(); document.addEventListener('studio:refresh', on); return () => document.removeEventListener('studio:refresh', on); }, []);

  if (!meta) return html`<div class="loading">${err || 'Загрузка…'}</div>`;
  const groups = TIER_GROUP.map(([t, name]) => [name, meta.models.filter((m) => m.tier === t)]).filter(([, rows]) => rows.length);
  const price = (m) => m.tier === 'paid' && m.price ? ` · $${m.price.in_per_mtok}/$${m.price.out_per_mtok} за 1М ток.` : '';
  const count = { gen: ov?.runs.length, montage: ov?.montage ? ov.videos.length : 0 };
  const goTab = (k) => { setTab(k); store.set('studio-tab', k); };
  const pick = (k) => (e) => { e.preventDefault(); goTab(k); };
  const gallery = {
    meta, project, onSaved: () => { if (project === cur.current) loadOv(project); },  // a save that ends after a project switch must not cancel the new page's load
    onRepeat: (r) => { location.hash = 'models/kind/' + encodeURIComponent(r.kind); },
    onChat: (r) => { setDraft((d) => (d.trim() ? d.trimEnd() + '\n\n' : '') + runText(r)); goTab('chats');
      if (!chat && !busy) (chats[0] ? open(chats[0].id) : create()); },
  };
  return html`${mode !== 'montage' && html`<div class="subtabs studio-tabs" role="tablist" aria-label="Разделы проекта">${TABS.map(([k, t]) => html`<a href="#" role="tab"
    aria-selected=${tab === k} class=${tab === k ? 'active' : ''} onClick=${pick(k)}>${t}${count[k] ? html` <span class="count">${count[k]}</span>` : ''}</a>`)}</div>
  <${GpuBar} />`}
  <div class="studio">
    <aside class="studio-side card">
      <label class="field">Проект<${ProjectSelect} id="studio-project" meta=${meta} value=${project} disabled=${busy} onChange=${setProject} /></label>
      ${tab === 'chats' && html`<button type="button" disabled=${busy} onClick=${create}>Новый чат</button>
      <div class="studio-chats">${chats.length ? chats.map((c) => html`<button type="button" class=${'studio-chat' + (chat?.id === c.id ? ' active' : '')} disabled=${busy} onClick=${() => open(c.id)}>
        <b>${c.title}</b><small>${when(c.updated)} · ${c.count} сообщ.</small></button>`)
        : html`<p class="note">В проекте «${label(meta, project)}» чатов пока нет.</p>`}</div>
      <details class="studio-where"><summary>Где хранятся чаты</summary><p class="note">В папке проекта: studio\\chats. Неразобранное — ${meta.inbox.path}.</p></details>`}
      ${tab === 'montage' && html`<p class="note">Видео проекта: результаты генераций и загруженные ролики. Готовый монтаж сохраняется в папку проекта.</p>`}
    </aside>
    <section class="studio-main card">
      ${tab !== 'chats' ? (!ov ? html`<p class="note">${err ? '' : 'Загрузка…'}</p>` : tab === 'gen' ? html`<div class="studio-gen-head"><span>Результаты генераций этого проекта. Новая генерация — в разделе «Модели».</span><a class="button-link" href="#models">Открыть Модели</a></div><${Gallery} ov=${ov} ...${gallery} />`
        : tab === 'files' ? html`<${Files} ov=${ov} project=${project} />` : html`<${Montage} ov=${ov} />`)
      : !chat ? html`<p class="note">Выберите чат слева или создайте новый.</p>` : html`
      <div class="studio-head">
        ${title === null ? html`<h3 title="Переименовать" onClick=${() => !busy && setTitle(chat.title)}>${chat.title}</h3>`
          : html`<input class="studio-title" value=${title} maxlength="120" autofocus onInput=${(e) => setTitle(e.target.value)}
              onBlur=${rename} onKeyDown=${(e) => { if (e.key === 'Enter') rename(); if (e.key === 'Escape') setTitle(null); }} />`}
        <details class="studio-move"><summary>Перенести в проект</summary>
          <${ProjectSelect} meta=${meta} value=${moveTo} skip=${project} onChange=${setMoveTo} title="Куда перенести" placeholder="— куда —" />
          <button type="button" class="ghost" disabled=${!moveTo || busy} onClick=${move}>Перенести</button></details>
      </div>
      <div class="chat-log studio-log" ref=${log}>
        ${chat.messages.map((m) => html`<div class=${'msg ' + m.role}><b>${m.role === 'user' ? 'Ты' : (m.model || 'Модель')}${m.cost_usd ? ' · ' + usd(m.cost_usd) : ''}</b><div>${m.content}${m.truncated ? '\n[Достигнут лимит ответа]' : ''}${m.stopped ? '\n[Остановлено]' : ''}</div></div>`)}
        ${pending && html`<div class="msg user"><b>Ты</b><div>${pending}</div></div><div class="msg assistant"><b>${sel?.name || model}</b>${answer ? html`<div>${answer}</div>`
          : html`<div class="note">${sel?.engine === 'worker' ? 'Думает… первый ответ дольше: модель загружается на GPU.' : 'Думает…'}</div>`}</div>`}
        ${!chat.messages.length && !pending && html`<p class="note">Сообщений пока нет.</p>`}
      </div>
      <form class="chat-form" onSubmit=${send}>
        <textarea rows="3" aria-label="Сообщение" placeholder="Напиши запрос… (Ctrl+Enter — отправить)" value=${draft} disabled=${busy}
          onInput=${(e) => setDraft(e.target.value)} onKeyDown=${(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) send(e); }}></textarea>
        <div class="actions">
          <select aria-label="Модель" value=${model} disabled=${busy} onChange=${(e) => { setModel(e.target.value); store.set('studio-model', e.target.value); }}>
            ${groups.map(([name, rows]) => html`<optgroup label=${name}>${rows.map((m) => html`<option value=${m.id} disabled=${!m.available}
              title=${m.note || ''}>${m.name} · ${TIER[m.tier]}${m.available ? price(m) : ' — ' + m.reason}</option>`)}</optgroup>`)}</select>
          ${pending ? html`<button type="button" class="ghost" onClick=${stopAnswer}>Стоп</button>`
            : html`<button type="submit" disabled=${busy || !draft.trim() || !sel?.available}>${busy ? 'Думает…' : !sel?.available ? 'Модель недоступна'
              : paid ? (quoted ? `Отправить за ≈${usd(quote.usd)}` : 'Узнать цену') : 'Отправить'}</button>`}
        </div>
        ${quoted && html`<p class="note">Платная модель: ≈${quote.tokens_in} ток. на входе и до ${quote.max_tokens} на выходе — не больше ${usd(quote.usd)}. Отправка только после подтверждения.</p>`}
      </form>`}
      ${err && html`<p class="err">${err}</p>`}
    </section>
  </div>`;
}

// Returns a disposer: app.js calls it before replacing the view, so listeners and the component do not pile up on revisits.
export function mountStudio(el, opts = {}) { render(html`<${Studio} mode=${opts.mode} />`, el); return () => render(null, el); }
