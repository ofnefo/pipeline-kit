// Montage M0: the editor inside Studio. An all-intra proxy plus requestVideoFrameCallback give the exact presented
// frame; the timeline shows thumbnails, audio peaks, requests and comments. A comment becomes a board task with its still.
// The v1 page (video-review.html) keeps working and shares the same project journal (50-edit\video-review.json).
// M1b: the sequence (50-edit\sequence.json) — V1 video, V2 over it (generated versions), A1 sound — and an exact export.
import { html, useState, useEffect, useRef, useMemo } from './vendor/htm-3.1.1/standalone.module.js';

const call = async (path, body) => {
  const r = await fetch(path, body ? { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {});
  const d = await r.json().catch(() => null);
  if (!r.ok) throw Object.assign(new Error(typeof d?.detail === 'string' ? d.detail : r.statusText), { status: r.status });
  if (!d) throw new Error('Сервер ответил не JSON');
  return d;
};
const store = { get: (k, d) => { try { return localStorage.getItem(k) || d; } catch { return d; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch {} } };
const when = (ts) => new Date(ts * 1000).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
const mb = (n) => n < 1048576 ? Math.max(1, Math.round(n / 1024)) + ' КБ' : (n / 1048576).toFixed(n < 10485760 ? 1 : 0) + ' МБ';
const nonce = () => crypto.randomUUID?.() || Date.now().toString(36) + Math.random().toString(36).slice(2, 12);
const LANE_H = 48;
const MODES = [['flf', 'Первый и последний кадр'], ['v2v', 'Видео → видео'], ['inpaint', 'Замена области']];
const TASK = { queued: 'в очереди', running: 'агент работает', blocked: 'остановлено', review: 'готово, проверьте', done: 'принято' };
// Local first+last-frame models (video_review.GEN_MODELS); a busy GPU puts the run into the shared queue.
const GEN = [['ltx25_flf', 'LTX-2.5'], ['wan22_i2v14b_flf', 'Wan 2.2']];
const GSTATE = { starting: 'запускается', queued: 'в очереди GPU', running: 'генерируется', conforming: 'подгоняю к участку', done: 'готово', error: 'ошибка' };
const ACTIVE = ['starting', 'queued', 'running', 'conforming'];
const STEPS = ['Выделите кусок', 'Опишите', 'Сгенерируйте', 'Выберите версию', 'Соберите'];

// Board hand-off shared by the editor and the sequence: the project card (cached per slug) and the session prompt.
const cards = new Map();
const projectCardId = async (slug) => {
  if (cards.has(slug)) return cards.get(slug);
  const tail = '/projects/video/' + slug.toLowerCase(); let id = '';
  try { const { cards: list } = await call('/api/board/projects'); id = (list.find((c) => String(c.canonical || '').replace(/\\/g, '/').toLowerCase().replace(/\/+$/, '').endsWith(tail)) || {}).id || ''; }
  catch {}
  cards.set(slug, id); return id;
};
const handoffPrompt = async (task) => { try { await navigator.clipboard.writeText((await call(`/api/board/${task.id}/handoff`)).prompt); return true; } catch { return false; } };
const handedOff = (task, copied) => `Задача ${task.id} на Доске.${copied ? ' Запрос для сессии скопирован — вставьте его агенту.' : ' Запрос для сессии — на Доске, кнопка «Передать».'}`;

// Frame clock: the presented media time → frame index and back. Variable frame rate uses the probed frame times;
// a seek lands a quarter frame (or mid-gap) after the frame start, so rounding never shows the neighbour.
function clockOf(tl) {
  const a = tl.assets.state === 'ready' ? tl.assets : null, fps = tl.fps_value, times = a?.times || null;
  const frames = a ? a.frames : tl.frames;
  const at = (t) => {
    if (times) { let lo = 0, hi = times.length - 1; while (lo < hi) { const m = (lo + hi + 1) >> 1; if (times[m] <= t + 1e-3) lo = m; else hi = m - 1; } return lo; }
    return Math.min(frames - 1, Math.max(0, Math.floor(t * fps + 0.01)));
  };
  const time = (n) => times ? (n + 1 < times.length ? (times[n] + times[n + 1]) / 2 : times[n] + 0.25 / fps) : (n + 0.25) / fps;
  const p = (x) => String(x).padStart(2, '0');
  const tc = (n) => {
    if (times) { const t = times[n] || 0; return `${p(Math.floor(t / 60))}:${p(Math.floor(t) % 60)}.${String(Math.floor((t % 1) * 1000)).padStart(3, '0')}`; }
    const r = Math.round(fps) || 1, s = Math.floor(n / r); return `${p(Math.floor(s / 3600))}:${p(Math.floor(s / 60) % 60)}:${p(s % 60)}:${p(n % r)}`;
  };
  return { frames, fps, exact: !!a, at, time, tc, clamp: (n) => Math.max(0, Math.min(frames - 1, Math.round(n))) };
}

export function Montage({ ov }) {
  const slug = ov.montage;
  const known = (rel) => ov.videos.some((v) => v.relative === rel);
  const [source, setSource] = useState(() => { const s = slug && store.get('video-review-source:' + slug, ''); return s && known(s) ? s : ''; });
  const [seq, setSeq] = useState(() => !!slug && store.get('montage-seq:' + slug, '') === '1');
  const [add, setAdd] = useState(null);  // a video to put on V1 when the sequence opens
  if (!slug) return html`<p class="note">Монтаж открывается для видеопроектов. Выберите видеопроект в списке слева.</p>`;
  if (!ov.videos.length) return html`<p class="note">В проекте пока нет видео (mp4, mov, webm, mkv).</p>`;
  const v1 = (rel) => '/static/video-review.html?' + new URLSearchParams({ project: slug, source: rel });
  const pick = (rel) => { store.set('video-review-source:' + slug, rel); setSource(rel); };
  const openSeq = (rel) => { setAdd(rel || null); setSeq(true); store.set('montage-seq:' + slug, '1'); };
  if (source) return html`<${Editor} key=${slug + '|' + source} ov=${ov} slug=${slug} source=${source} v1=${v1(source)} back=${seq ? '← Монтаж' : '← Все видео'}
    onClose=${() => { setSource(''); store.set('video-review-source:' + slug, ''); }} />`;
  if (seq) return html`<${Sequence} key=${slug} ov=${ov} slug=${slug} add=${add} onOpen=${(rel) => { setAdd(null); pick(rel); }}
    onClose=${() => { setSeq(false); setAdd(null); store.set('montage-seq:' + slug, ''); }} />`;
  return html`<div class="studio-videos"><div class="studio-video sq-entry">
    <div><b>Монтаж</b><small class="note">Таймлайн V1 / V2 / A1: склейка видео проекта, сгенерированные версии поверх, звук, экспорт в MP4 с квитанцией.</small></div>
    <span class="mt-open"><button type="button" onClick=${() => openSeq()}>Открыть монтаж</button></span></div>
    ${ov.videos.map((v) => html`<div class="studio-video">
    <div><b>${v.name}</b><small class="note">${v.relative.split('/').slice(0, -1).join(' / ') || 'корень проекта'} · ${when(v.modified)} · ${mb(v.size)}</small></div>
    <span class="mt-open"><button type="button" onClick=${() => pick(v.relative)}>Править кусок</button><button type="button" class="ghost" onClick=${() => openSeq(v.relative)}>+ в монтаж</button>
      <a class="note" href=${v1(v.relative)}>прежняя монтажная</a></span></div>`)}</div>
    ${ov.videos.length >= 40 && html`<p class="note">Показаны 40 новых видео; остальные — во вкладке «Файлы».</p>`}`;
}

function Editor({ ov, slug, source, v1, back = '← Все видео', onClose }) {
  const base = '/api/video-review/' + encodeURIComponent(slug);
  const file = (rel) => '/api/project-browser/media?' + new URLSearchParams({ root: 'projects', path: 'video/' + slug + '/' + rel });
  const [tl, setTl] = useState(null);
  const [journal, setJournal] = useState({ requests: [], comments: [] });
  const [tasks, setTasks] = useState(null);  // null = the board did not answer: hand-off stays hidden
  const [frame, setFrame] = useState(0);
  const [sel, setSel] = useState(null);  // {a, b}: inclusive in/out frames
  const [inMark, setIn] = useState(null);
  const [text, setText] = useState('');
  const [note, setNote] = useState(() => store.get('video-review-draft:' + slug, ''));
  const [mode, setMode] = useState('flf');
  const [executor, setExecutor] = useState(store.get('video-review-executor', 'codex'));
  const [cmp, setCmp] = useState(null);  // {r, v, view: 'side'|'wipe', pos}
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [muted, setMuted] = useState(false);
  const [build, setBuild] = useState(0);  // bumped by «Повторить»: restarts the build and its polling
  const [gen, setGenState] = useState(() => ({ model: store.get('montage-gen-model', 'ltx25_flf'), quality: store.get('montage-gen-quality', 'draft') }));
  const setGen = (g) => { setGenState(g); store.set('montage-gen-model', g.model); store.set('montage-gen-quality', g.quality); };
  const vid = useRef(null), head = useRef(null), tcBox = useRef(null), cur = useRef(0), want = useRef(null), resume = useRef(0);
  const pos = () => want.current ?? cur.current;  // a seek still in flight counts: rapid steps never read a stale frame
  const pend = useRef({ comment: null, request: null });  // the same body resent keeps its nonce: no duplicate rows
  const say = (t, bad = false) => setMsg({ t, bad });

  const loadJournal = () => call(base).then((d) => setJournal({ requests: d.requests || [], comments: d.comments || [] }));
  const loadTasks = () => call('/api/board').then((d) => setTasks(d.tasks || [])).catch(() => setTasks((t) => t && null));
  const refresh = () => Promise.all([loadJournal(), loadTasks()]);
  useEffect(() => { refresh().catch((e) => say(e.message, true)); }, []);

  // Proxy, sprite and peaks: start the build on open, poll while it runs. Until then the original plays (approximate frames).
  useEffect(() => {
    let live = true, timer = 0;
    const q = '?' + new URLSearchParams({ path: source });
    const poll = async (start) => {
      try {
        const d = await call(base + '/timeline' + q, start ? {} : undefined);
        if (!live) return;
        setTl(d);
        if (['queued', 'building'].includes(d.assets.state)) timer = setTimeout(() => poll(false), 2000);
      } catch (e) { if (live) say(e.message, true); }
    };
    poll(true);
    return () => { live = false; clearTimeout(timer); };
  }, [source, build]);
  const retry = () => setBuild((n) => n + 1);

  const clk = useMemo(() => tl && clockOf(tl), [tl?.assets.state, tl?.assets.key]);
  const a = tl?.assets.state === 'ready' ? tl.assets : null;
  const src = a ? `${base}/timeline/${a.key}/proxy.mp4` : file(source);

  // Presented frame: the playhead and timecode update straight in the DOM while playing; state follows when paused.
  useEffect(() => {
    const v = vid.current; if (!v || !clk) return;
    let live = true, id = 0;
    const paint = (t) => {
      const n = clk.at(t); cur.current = n; if (!v.seeking) want.current = null;
      if (head.current) { head.current.style.left = (100 * (n + 0.5) / clk.frames) + '%'; head.current.parentElement?.setAttribute('aria-valuenow', n); }
      if (tcBox.current) tcBox.current.textContent = `${clk.tc(n)} · кадр ${n}`;
      if (v.paused) setFrame(n);
    };
    const onPause = () => { setPlaying(false); setFrame(cur.current); };
    const onPlay = () => setPlaying(true);
    v.addEventListener('pause', onPause); v.addEventListener('play', onPlay);
    let off;
    if (v.requestVideoFrameCallback) {
      const tick = (_, md) => { if (!live) return; paint(md.mediaTime); id = v.requestVideoFrameCallback(tick); };
      id = v.requestVideoFrameCallback(tick);
      off = () => v.cancelVideoFrameCallback?.(id);
    } else {
      const on = () => paint(v.currentTime);
      v.addEventListener('timeupdate', on); v.addEventListener('seeked', on);
      off = () => { v.removeEventListener('timeupdate', on); v.removeEventListener('seeked', on); };
    }
    paint(v.currentTime);
    return () => { live = false; off(); v.removeEventListener('pause', onPause); v.removeEventListener('play', onPlay); };
  }, [clk, src]);

  const seek = (n) => { const v = vid.current; if (!v || !clk) return; v.pause(); want.current = clk.clamp(n); v.currentTime = clk.time(want.current); };
  const toggle = () => { const v = vid.current; if (!v) return; v.paused ? v.play().catch((e) => say('Нажмите ещё раз: ' + e.message, true)) : v.pause(); };
  const markIn = () => { const n = pos(); setIn(n); setSel(sel && sel.b >= n ? { a: n, b: sel.b } : { a: n, b: n }); };
  const markOut = () => { const n = pos(), s = inMark != null && inMark <= n ? inMark : sel && sel.a <= n ? sel.a : n; setSel({ a: s, b: n }); };
  const clearSel = () => { setSel(null); setIn(null); };

  useEffect(() => {
    const on = (e) => {
      if (!clk || e.ctrlKey || e.metaKey || e.altKey || e.target.closest?.('input:not([type=range]),textarea,select,.mt-compare')) return;
      if (['Space', 'Enter'].includes(e.code) && e.target.closest?.('button,summary,a')) return;
      if (e.code.startsWith('Arrow') && e.target.closest?.('input[type=range]')) return;
      const sec = Math.round(clk.fps) || 1, step = e.shiftKey ? 10 : 1;
      const act = { Space: toggle, KeyK: toggle, KeyJ: () => seek(pos() - sec), KeyL: () => seek(pos() + sec),
        ArrowLeft: () => seek(pos() - step), ArrowRight: () => seek(pos() + step), KeyI: markIn, KeyO: markOut }[e.code];
      if (act) { e.preventDefault(); act(); }
    };
    document.addEventListener('keydown', on);
    return () => document.removeEventListener('keydown', on);
  });

  const once = async (fn) => { if (busy) return; setBusy(true); try { await fn(); } catch (e) { say(e.message, true); } finally { setBusy(false); } };
  const comments = journal.comments.filter((c) => c.source === source);
  const requests = journal.requests.filter((r) => r.source === source);
  const target = sel ? (sel.a === sel.b ? `к кадру ${sel.a}` : `к кадрам ${sel.a}–${sel.b}`) : `к кадру ${frame}`;

  const addComment = (e) => { e.preventDefault(); const t = text.trim(); if (!t || !tl) return; once(async () => {
    const body = { source, frame: sel ? sel.a : pos(), end: sel && sel.b > sel.a ? sel.b + 1 : null, text: t, source_identity: tl.identity };
    const key = JSON.stringify(body); if (pend.current.comment?.key !== key) pend.current.comment = { key, nonce: nonce() };
    await call(base + '/comments', { ...body, nonce: pend.current.comment.nonce });
    pend.current.comment = null; setText(''); await loadJournal(); say('Комментарий сохранён в проекте.');
  }); };
  const resolve = (c) => once(async () => { await call(`${base}/comments/${c.id}/resolve`, { resolved: !c.resolved }); await loadJournal(); });
  // «Сгенерировать» saves the request and starts a local take in one go; «Только записать» keeps the old path (agent / own file).
  const genStart = async (r, prompt) => {
    const g = await call(`${base}/requests/${r.id}/generate`, { model: gen.model, quality: gen.quality, prompt });
    await loadJournal();
    say(g.state === 'queued' ? `GPU занят — генерация в общей очереди${g.position ? ', место ' + g.position : ''}. Страница обновится сама.`
      : 'Генерация идёт на локальном узле. Готовый вариант появится на дорожке «Генерации».');
  };
  const addRequest = (e) => { e.preventDefault(); const t = note.trim(); if (!t || !sel || !tl) return;
    const andGen = e.submitter?.value === 'gen' && mode === 'flf'; if (andGen && t.length < 3) return say('Промпт для генерации — хотя бы 3 символа.');
    once(async () => {
      const body = { source, start: sel.a, end: sel.b + 1, note: t, mode, source_identity: tl.identity };
      const key = JSON.stringify(body); if (pend.current.request?.key !== key) pend.current.request = { key, nonce: nonce() };
      const r = await call(base + '/requests', { ...body, nonce: pend.current.request.nonce });
      pend.current.request = null; setNote(''); store.set('video-review-draft:' + slug, ''); clearSel(); await refresh();
      if (andGen) await genStart(r, t);
      else say('Запрос сохранён. Сгенерировать вариант можно в карточке запроса, или передать агенту.');
    }); };
  const regen = (r) => (e) => { e.preventDefault(); const p = String(new FormData(e.target).get('prompt') || '').trim(); if (p.length < 3) return say('Промпт для генерации — хотя бы 3 символа.'); once(() => genStart(r, p)); };

  // Active generations: ask the server to advance them every 5 s (it reads the run list and the GPU queue).
  const live = requests.some((r) => (r.generations || []).some((g) => ACTIVE.includes(g.state)));
  useEffect(() => {
    if (!live) return;
    let on = true;
    const t = setInterval(() => call(base + '/generations/sync', {}).then((d) => on && setJournal({ requests: d.requests || [], comments: d.comments || [] })).catch(() => {}), 5000);
    return () => { on = false; clearInterval(t); };
  }, [live]);

  // Board hand-off, as on the v1 page: the task description carries a marker, so no extra server state is needed.
  const marker = (r, kind) => kind === 'comment' ? `video-review-comment:${r.id}` : `video-review:${r.id}:${kind}` + (kind === 'assemble' ? `:${r.selected_variant}` : '');
  const taskFor = (r, kind) => tasks?.find((t) => t.status !== 'cancelled' && String(t.description || '').includes(marker(r, kind)));
  const post = async (r, kind, title, description, acceptance) => {
    if (taskFor(r, kind)) throw new Error('Задача уже на Доске');
    const task = await call('/api/board', { title, description: [...description, `Метка: ${marker(r, kind)}`].join('\n'), acceptance,
      project_id: await projectCardId(slug), executor, priority: 'P2' });
    setTasks((t) => [...(t || []).filter((x) => x.id !== task.id), task]);
    say(handedOff(task, await handoffPrompt(task)) + ' Генерация сама не запускается.');
  };
  const winPath = (rel) => String(ov.path).replace(/[\\/]+$/, '') + '\\' + rel.replace(/\//g, '\\');
  const range = (c) => c.end_exclusive ? `кадры ${c.frame}–${c.end_exclusive - 1}` : `кадр ${c.frame}`;
  const commentTask = (c) => once(() => post(c, 'comment', `Правка по комментарию · ${slug} · ${range(c)}`, [
    `Монтажная проекта ${slug}: комментарий оператора (${range(c)}, ${c.source}).`, `Комментарий: ${c.text}`,
    c.thumb ? `Кадр: ${winPath(c.thumb)}` : 'Кадр: стоп-кадр не сохранился, откройте монтажную.',
    'Исходник не перезаписывать: результат — новый файл в проекте. Платные модели — только после сметы и согласия оператора.'],
    'Правка сделана в новом файле; исходник не изменён; путь к результату указан в задаче.'));
  const requestTask = (r, kind) => once(async () => {
    const cmd = `python scripts/video_pipeline.py repair-review --project ${slug} --request-id ${r.id}` + (kind === 'assemble' ? ' --assemble' : '');
    const frames = `кадры ${r.start}–${r.end_exclusive - 1}`;
    await post(r, kind, `${kind === 'assemble' ? 'Собрать версию' : 'Подготовить варианты'} · ${slug} · ${frames}`, [
      `Монтажная проекта ${slug}: ${kind === 'assemble' ? 'Оператор выбрал вариант, нужна отдельная сборка' : 'замечание к участку'} (${frames}, ${r.source}).`,
      `Замечание: ${r.note}`, `Способ: ${r.mode}.`,
      'Read docs/MODULES.md and skills/video-editing/SKILL.md in Pipeline Kit. Prepare a new local version using the included CPU tools or an explicitly configured external adapter. No repair-generation worker is bundled.',
      kind === 'assemble' ? 'В результате укажите путь к receipt.json и к MP4 для просмотра в браузере, если он сделан. Исходный мастер не перезаписывать.'
        : 'Варианты (MP4 H.264, только выделенный участок, те же FPS и размер) добавьте в монтажную. Платные модели — только после сметы и согласия оператора.'],
      kind === 'assemble' ? 'Квитанция repair-apply со статусом technical_pass; мастер не изменён; стыки проверены глазами.' : 'К замечанию добавлен хотя бы один вариант; квитанция генерации лежит в проекте.');
  });
  const accept = (t) => confirm('Отметить сборку принятой? Файлы не меняются.') && once(async () => {
    await call(`/api/board/${t.id}`, { version: t.version, action: 'approve', data: {} }); await refresh(); say('Сборка принята.');
  });
  const stage = (r) => {
    const prep = taskFor(r, 'variants'), build = taskFor(r, 'assemble');
    if (r.state === 'selected') return build ? { text: build.status === 'review' ? 'Сборка готова — проверьте' : 'Сборка: ' + (TASK[build.status] || build.status), task: build, build: true }
      : { text: 'Вариант выбран · ждёт сборки', action: 'assemble' };
    const g = (r.generations || []).at(-1);
    if (g && ACTIVE.includes(g.state)) return { text: 'Генерация: ' + GSTATE[g.state] + (g.state === 'queued' && g.position ? ', место ' + g.position : ''), task: prep };
    if (r.state === 'review') return { text: 'Можно сравнить', task: prep };
    return prep ? { text: 'Варианты: ' + (TASK[prep.status] || prep.status), task: prep }
      : { text: g?.state === 'error' ? 'Генерация не удалась' : 'Ждёт генерации', action: 'variants' };
  };
  const addVariant = (r) => (e) => { e.preventDefault(); const f = Object.fromEntries(new FormData(e.target)); once(async () => {
    await call(`${base}/requests/${r.id}/variants`, f); await refresh(); say('Вариант добавлен. Посмотрите оба ролика перед выбором.');
  }); };
  const choose = () => cmp && confirm(`Выбрать «${cmp.v.label}» для замены участка? Исходник сохранится.`) && once(async () => {
    await call(`${base}/requests/${cmp.r.id}/select`, { variant_id: cmp.v.id }); await refresh(); setCmp(null);
    say('Выбор сохранён. Следующий шаг — сборка отдельной версии и проверка стыков.');
  });
  // A take goes on V2 of the sequence exactly over its span (the source joins V1 when it is not there yet).
  const toSeq = (r, v) => v && once(async () => {
    const d = await call(base + '/sequence');
    await call(base + '/sequence/place', { version: d.version, request_id: r.id, variant_id: v.id });
    say(`«${v.label}» лежит в монтаже на V2 над кадрами ${r.start}–${r.end_exclusive - 1}. Монтаж — кнопка «${back}» или «Открыть монтаж» в списке.`);
  });
  const jump = (n, end) => { seek(n); if (end != null) { setSel({ a: n, b: end }); setIn(n); } };

  if (!tl || !clk) return html`<div class="mt-bar"><button type="button" class="ghost" onClick=${onClose}>${back}</button><b class="mt-name">${source.split('/').pop()}</b></div>
    <p class=${msg?.bad ? 'err' : 'note'}>${msg?.t || 'Открываю видео…'}</p>`;
  const st = tl.assets.state;
  // One visible path: select → describe → generate → choose → assemble. The step follows the newest request.
  const last = requests[requests.length - 1];
  const step = sel ? 1 : !last ? 0 : last.state === 'selected' ? 4 : last.variants.length ? 3 : 2;
  const hint = [
    'Отметьте начало и конец куска на таймлайне: клавиши I и O или кнопки I / O под видео.',
    'Напишите под таймлайном, что изменить, и нажмите «Сгенерировать».',
    live ? 'Генерация идёт на локальном узле — можно продолжать работу, вариант появится на дорожке «Генерации».' : 'Запустите генерацию в карточке запроса или передайте участок агенту.',
    'Сравните варианты с исходником (кнопки на дорожке «Генерации») и выберите лучший.',
    'Положите выбранный вариант в монтаж («В монтаж») или передайте на сборку — исходник не перезаписывается.'][step];
  const pick = () => html`<span class="mt-pick">
    <select aria-label="Модель" value=${gen.model} onChange=${(e) => setGen({ ...gen, model: e.target.value })}>${GEN.map(([k, t]) => html`<option value=${k}>${t}</option>`)}</select>
    <select aria-label="Качество" value=${gen.quality} onChange=${(e) => setGen({ ...gen, quality: e.target.value })}><option value="draft">Черновик</option><option value="final">Финал</option></select></span>`;
  const openCmp = (r, v) => setCmp({ r, v, view: cmp?.view || 'side', pos: 50 });
  return html`<div class="mt">
    <div class="mt-bar"><button type="button" class="ghost" onClick=${onClose}>${back}</button>
      <b class="mt-name" title=${source}>${source.split('/').pop()}</b>
      <small class="note">${tl.width}×${tl.height} · ${tl.fps_value.toFixed(3).replace(/\.?0+$/, '')} к/с${tl.vfr ? ' · переменная частота' : ''} · ${clk.frames} кадров</small></div>
    <ol class="mt-steps">${STEPS.map((s, i) => html`<li class=${i < step ? 'done' : i === step ? 'now' : ''}><b>${i + 1}</b><span>${s}</span></li>`)}</ol>
    <p class="note mt-hint">${hint}</p>
    ${st !== 'ready' && html`<p class=${st === 'error' ? 'err' : 'note'}>${st === 'error' ? html`Прокси не собрался: ${tl.assets.error || 'ошибка'} <button type="button" class="ghost small" onClick=${retry}>Повторить</button>`
      : 'Готовлю прокси, миниатюры и звук — пока кадры примерные. Процессор, низкий приоритет; GPU не занимается.'}</p>`}
    <div class="mt-grid">
      <div class="mt-stage">
        <div class=${'mt-player' + (tl.height > tl.width ? ' portrait' : '')}>
          <video ref=${vid} src=${src} playsinline preload="auto" muted=${muted} onClick=${toggle}
            onLoadedMetadata=${(e) => { if (resume.current) { e.target.currentTime = resume.current; resume.current = 0; } }}
            onEmptied=${() => { resume.current = vid.current?.currentTime || 0; }}
            onError=${() => say('Браузер не может воспроизвести этот файл. Дождитесь прокси или подготовьте MP4 H.264; исходник сохраняется.', true)}></video>
        </div>
        <div class="mt-controls">
          <button type="button" class="ghost" aria-label="Кадр назад" title="Кадр назад (←)" onClick=${() => seek(pos() - 1)}>◀︎</button>
          <button type="button" aria-label=${playing ? 'Пауза' : 'Воспроизвести'} title="Пробел / K" onClick=${toggle}>${playing ? '❚❚' : '▶'}</button>
          <button type="button" class="ghost" aria-label="Кадр вперёд" title="Кадр вперёд (→)" onClick=${() => seek(pos() + 1)}>▶︎</button>
          <span class="mt-tc" ref=${tcBox}></span>
          <button type="button" class="ghost" title="Начало куска (I)" onClick=${markIn}>I</button>
          <button type="button" class="ghost" title="Конец куска (O)" onClick=${markOut}>O</button>
          ${sel && html`<span class="mt-sel">${sel.a}–${sel.b}<button type="button" class="ghost small" aria-label="Снять выделение" onClick=${clearSel}>×</button></span>`}
          <button type="button" class="ghost" aria-label=${muted ? 'Включить звук' : 'Выключить звук'} onClick=${() => setMuted(!muted)}>${muted ? '🔇' : '🔊'}</button>
        </div>
        <${Lanes} tl=${tl} clk=${clk} a=${a} base=${base} frame=${frame} sel=${sel} requests=${requests} comments=${comments} head=${head} onSeek=${seek} onPick=${openCmp} />
        ${!clk.exact && html`<p class="note">Точные номера кадров появятся, когда прокси будет готов.</p>`}
        ${sel && html`<form class="mt-gen" onSubmit=${addRequest}>
          <div class="mt-bar"><b>Кусок ${sel.a}–${sel.b}</b><small class="note">${sel.b + 1 - sel.a} кадр. · ${((sel.b + 1 - sel.a) / clk.fps).toFixed(1)} с</small></div>
          <textarea rows="2" aria-label="Что изменить" placeholder="Что изменить на куске — это же уйдёт в промпт" value=${note} maxlength="4000" onInput=${(e) => { setNote(e.target.value); store.set('video-review-draft:' + slug, e.target.value); }}></textarea>
          <div class="mt-acts">
            ${mode === 'flf' && pick()}
            ${mode === 'flf' && html`<button type="submit" value="gen" disabled=${busy || note.trim().length < 3 || !clk.exact} title=${note.trim().length < 3 ? 'Промпт — хотя бы 3 символа' : ''}>Сгенерировать</button>`}
            <button type="submit" value="save" class=${mode === 'flf' ? 'ghost' : ''} disabled=${busy || !note.trim() || !clk.exact}>Только записать</button>
            <select aria-label="Способ правки" class="mt-mode" value=${mode} onChange=${(e) => setMode(e.target.value)}>${MODES.map(([k, t]) => html`<option value=${k}>${t}</option>`)}</select>
          </div>
          <p class="note">${mode === 'flf' ? 'Локально на локальном узле по первому и последнему кадру куска; GPU занят — встанет в общую очередь. Бесплатно.'
            : 'Этот способ делает агент: запишите запрос и передайте его в карточке.'}</p>
        </form>`}
        ${cmp && html`<${Compare} key=${cmp.r.id + '|' + cmp.v.id} cmp=${cmp} setCmp=${setCmp} clk=${clk} file=${file} busy=${busy} onChoose=${choose} onPlace=${() => toSeq(cmp.r, cmp.v)} say=${say} />`}
      </div>
      <div class="mt-side">
        ${msg && html`<p class=${msg.bad ? 'err' : 'note'} role="status">${msg.t}</p>`}
        <h4>Правки <span class="count">${requests.length}</span></h4>
        ${requests.length ? html`<div class="mt-list">${requests.slice().reverse().map((r) => { const s = stage(r), t = s.task, gens = r.generations || [], g = gens.at(-1);
          const canGen = r.mode === 'flf' && r.state !== 'selected' && !(g && ACTIVE.includes(g.state));
          return html`<article class="mt-item" key=${r.id}>
          <div><b>${s.text}</b><small class="note">Кадры ${r.start}–${r.end_exclusive - 1} · ${{ flf: 'первый/последний кадр', v2v: 'видео → видео', inpaint: 'замена области' }[r.mode] || r.mode}</small><p>${r.note}</p>
            ${g?.state === 'error' && html`<small class="err">${g.label}: ${g.error}</small>`}
            ${t && html`<small class="note">Задача <a href="/#board">${t.id}</a> · ${t.executor}${t.status === 'blocked' && t.blocker ? ' · ' + t.blocker : ''}</small>`}
            ${s.build && t.evidence && html`<p class="note">Результат: ${t.evidence}</p>`}
            <div class="mt-acts"><button type="button" class="ghost small" onClick=${() => jump(r.start, r.end_exclusive - 1)}>К куску</button>
              ${s.action === 'assemble' && tasks && html`<button type="button" class="small" disabled=${busy} onClick=${() => requestTask(r, 'assemble')}>Передать на сборку</button>`}
              ${s.build && t.status === 'review' && html`<button type="button" class="small" disabled=${busy} onClick=${() => accept(t)}>Принять сборку</button>`}
              ${r.variants.map((v) => html`<button type="button" class=${'ghost small' + (cmp?.v.id === v.id ? ' active' : '')} onClick=${() => openCmp(r, v)}>${r.selected_variant === v.id ? '✓ ' : ''}${v.label}</button>`)}
              ${r.selected_variant && html`<button type="button" class="small" disabled=${busy} onClick=${() => toSeq(r, r.variants.find((v) => v.id === r.selected_variant))}>В монтаж</button>`}</div>
            ${canGen && html`<details open=${!r.variants.length && !gens.length}><summary class="note">${gens.length ? 'Ещё вариант' : 'Сгенерировать вариант'}</summary><form class="mt-form" onSubmit=${regen(r)}>
              <textarea name="prompt" rows="2" aria-label="Промпт" maxlength="4000" required minlength="3" defaultValue=${r.note}></textarea>
              <div class="mt-acts">${pick()}<button type="submit" class="small" disabled=${busy}>Сгенерировать</button></div></form></details>`}
            ${r.state !== 'selected' && html`<details><summary class="note">Ещё</summary>
              ${s.action === 'variants' && tasks && html`<div class="mt-acts"><button type="button" class="ghost small" disabled=${busy} onClick=${() => requestTask(r, 'variants')}>Передать агенту</button></div>`}
              <form class="mt-form" onSubmit=${addVariant(r)}>
              <input name="path" aria-label="Путь в проекте" placeholder="60-motion/variant.mp4" required />
              <input name="label" aria-label="Название" value=${'Вариант ' + (r.variants.length + 1)} maxlength="100" />
              <button type="submit" class="ghost" disabled=${busy}>Добавить свой файл</button>
              <p class="note">Файл — только этот кусок, те же FPS и размер.</p></form></details>`}
          </div></article>`; })}</div>`
          : html`<p class="note">Правок пока нет. Отметьте кусок на таймлайне — форма появится под ним.</p>`}
        <h4>Комментарии <span class="count">${comments.filter((c) => !c.resolved).length}</span></h4>
        <form class="mt-form" onSubmit=${addComment}>
          <textarea rows="2" aria-label="Комментарий" placeholder=${'Комментарий ' + target} value=${text} maxlength="2000" onInput=${(e) => setText(e.target.value)}></textarea>
          ${text.trim() && html`<button type="submit" disabled=${busy || !clk.exact} title=${clk.exact ? '' : 'Дождитесь прокси: нужен точный кадр'}>Комментарий ${target}</button>`}
        </form>
        ${comments.length ? html`<div class="mt-list">${comments.slice().reverse().map((c) => { const t = taskFor(c, 'comment'); return html`<article class=${'mt-item' + (c.resolved ? ' done' : '')} key=${c.id}>
          ${c.thumb && html`<img src=${file(c.thumb)} alt=${'Кадр ' + c.frame} loading="lazy" onClick=${() => jump(c.frame, c.end_exclusive ? c.end_exclusive - 1 : null)} />`}
          <div><small class="note">${range(c)} · ${when(c.created_at)}</small><p>${c.text}</p>
            ${t && html`<small class="note">Задача <a href="/#board">${t.id}</a> · ${TASK[t.status] || t.status}</small>`}
            <div class="mt-acts"><button type="button" class="ghost small" onClick=${() => jump(c.frame, c.end_exclusive ? c.end_exclusive - 1 : null)}>К кадру</button>
              <button type="button" class="ghost small" disabled=${busy} onClick=${() => resolve(c)}>${c.resolved ? 'Вернуть' : 'Решено'}</button>
              ${!t && tasks && !c.resolved && html`<button type="button" class="small" disabled=${busy} onClick=${() => commentTask(c)}>→ задача</button>`}</div></div></article>`; })}</div>`
          : html`<p class="note">Комментариев пока нет.</p>`}
        ${tasks === null && html`<p class="note">Доска не отвечает — передача агенту скрыта, обновите страницу.</p>`}
        <details class="mt-more"><summary>Ещё</summary>
          <label class="mt-exec">Исполнитель задач <select value=${executor} onChange=${(e) => { setExecutor(e.target.value); store.set('video-review-executor', e.target.value); }}>
            <option value="codex">Codex</option><option value="claude">Claude</option></select></label>
          <p class="note">Клавиши: пробел/K — пуск, J/L — секунда, ←/→ — кадр (Shift — 10), I/O — начало/конец куска.</p>
          <a class="note" href=${v1}>Прежняя монтажная</a>
        </details>
      </div>
    </div></div>`;
}

// Timeline: thumbnail strip, audio peaks, requests/comments/selection and one playhead. Drag anywhere to scrub.
function Lanes({ tl, clk, a, base, frame, sel, requests, comments, head, onSeek, onPick }) {
  const box = useRef(null), wave = useRef(null), drag = useRef(false);
  const [w, setW] = useState(0);
  useEffect(() => {
    const el = box.current; if (!el) return;
    const ro = new ResizeObserver(() => setW(el.clientWidth)); ro.observe(el); setW(el.clientWidth);
    return () => ro.disconnect();
  }, []);
  useEffect(() => {
    const c = wave.current; if (!c || !w) return;
    const dpr = window.devicePixelRatio || 1, h = 32; c.width = Math.round(w * dpr); c.height = h * dpr;
    const g = c.getContext('2d'); g.clearRect(0, 0, c.width, c.height);
    const peaks = a?.peaks; if (!peaks?.length) return;
    g.fillStyle = getComputedStyle(c).color;
    const dur = tl.duration || peaks.length * a.peak_seconds, cols = c.width;
    for (let x = 0; x < cols; x++) {
      const i0 = Math.floor((x / cols) * dur / a.peak_seconds), i1 = Math.max(i0 + 1, Math.floor(((x + 1) / cols) * dur / a.peak_seconds));
      let m = 0; for (let i = i0; i < i1 && i < peaks.length; i++) m = Math.max(m, peaks[i]);
      const y = (m / 100) * (c.height / 2); if (y) g.fillRect(x, c.height / 2 - y, 1, Math.max(1, 2 * y));
    }
  }, [w, a?.key]);
  const pct = (n) => (100 * Math.max(0, Math.min(clk.frames, n)) / clk.frames) + '%';
  const at = (e) => { const r = box.current.getBoundingClientRect(); onSeek(Math.floor((e.clientX - r.left) / r.width * clk.frames)); };
  let tiles = [];
  if (a && w) {
    const sw = a.thumb_w * LANE_H / a.thumb_h, k = Math.max(1, Math.ceil(w / sw)), tw = w / k;
    tiles = Array.from({ length: k }, (_, j) => {
      const idx = Math.min(a.thumbs - 1, Math.floor(((j + 0.5) / k) * clk.frames / a.step));
      return html`<i style=${`width:${tw}px;background-image:url(${base}/timeline/${a.key}/sprite.jpg);background-size:${a.thumbs * sw}px ${LANE_H}px;background-position:${-idx * sw + (tw - sw) / 2}px 0`}></i>`;
    });
  }
  const made = requests.filter((r) => r.variants.length || (r.generations || []).length);
  return html`<div class="mt-tl"><div class="mt-lanes" ref=${box} role="slider" tabindex="0" aria-label="Таймлайн" aria-valuemin="0" aria-valuemax=${clk.frames - 1} aria-valuenow=${frame}
      onPointerDown=${(e) => { drag.current = true; e.currentTarget.setPointerCapture?.(e.pointerId); at(e); }}
      onPointerMove=${(e) => drag.current && at(e)} onPointerUp=${() => { drag.current = false; }} onPointerCancel=${() => { drag.current = false; }}>
    <div class="mt-thumbs">${tiles}</div>
    <canvas class="mt-wave" ref=${wave} style=${`width:${w}px`}></canvas>
    <div class="mt-marks">
      ${requests.map((r) => html`<span class="seg" style=${`left:${pct(r.start)};width:${pct(r.end_exclusive - r.start)}`} title=${`Кадры ${r.start}–${r.end_exclusive - 1}: ${r.note}`}></span>`)}
      ${comments.map((c) => html`<span class=${'cm' + (c.resolved ? ' done' : '')} style=${`left:${pct(c.frame)};width:${c.end_exclusive ? pct(c.end_exclusive - c.frame) : '3px'}`} title=${`${c.frame}: ${c.text}`}></span>`)}
      ${sel && html`<span class="sel" style=${`left:${pct(sel.a)};width:${pct(sel.b + 1 - sel.a)}`}></span>`}
    </div>
    <b class="mt-head" ref=${head} style=${`left:${100 * (frame + 0.5) / clk.frames}%`}></b>
  </div>
  <div class="mt-gens" aria-label="Генерации">${made.length ? made.map((r) => { const g = (r.generations || []).at(-1), run = g && ACTIVE.includes(g.state);
    return html`<span key=${r.id} class=${'gen' + (run ? ' run' : g?.state === 'error' && !r.variants.length ? ' bad' : '')} style=${`left:${pct(r.start)};width:${pct(r.end_exclusive - r.start)}`}
      title=${`Кадры ${r.start}–${r.end_exclusive - 1}: ${r.note}` + (g ? ` · ${g.label}: ${GSTATE[g.state]}${g.error ? ' — ' + g.error : ''}` : '')}>
      ${r.variants.map((v) => html`<button type="button" class=${r.selected_variant === v.id ? 'on' : ''} onClick=${() => onPick(r, v)}>${r.selected_variant === v.id ? '✓ ' : ''}${v.label}</button>`)}
      ${run ? html`<i>${GSTATE[g.state]}</i>` : !r.variants.length && g?.state === 'error' ? html`<i>ошибка</i>` : ''}</span>`; })
    : html`<small class="note">Генерации появятся здесь, под своим куском</small>`}</div></div>`;
}

// Variant review: side by side or a wipe over the same frame range. The original plays muted, the variant with sound.
function Compare({ cmp, setCmp, clk, file, busy, onChoose, onPlace, say }) {
  const before = useRef(null), after = useRef(null), run = useRef(0);
  const { r, v, view, pos } = cmp, fps = r.media.fps_value, last = r.end_exclusive - 1;
  // The original follows the source frame clock (variable frame rate too); the variant is a constant-rate clip of the range.
  const src = clk || { at: (t) => Math.floor(t * fps + 0.01), time: (n) => (n + 0.25) / fps };
  const park = (n) => { if (before.current) before.current.currentTime = src.time(n); if (after.current) after.current.currentTime = (n - r.start + 0.25) / fps; };
  const stop = () => { run.current++; before.current?.pause(); after.current?.pause(); };  // also retires any frame watcher
  const end = () => { stop(); park(last); };
  useEffect(() => stop, []);  // keyed per request and variant: nothing outlives its range
  const play = async () => {
    const x = before.current, y = after.current; if (!x || !y) return;
    stop(); const mine = run.current; park(r.start); x.muted = true; y.muted = false;
    try { await Promise.all([x.play(), y.play()]); } catch (e) { if (run.current === mine) { stop(); say('Нажмите воспроизведение ещё раз: ' + e.message, true); } return; }
    // timeupdate fires ~4 times a second: watch every presented frame and pause as soon as the last one of the range is shown.
    if (run.current !== mine || !x.requestVideoFrameCallback) return;
    const tick = (_, m) => { if (run.current !== mine || x.paused) return; if (src.at(m.mediaTime) >= last) end(); else x.requestVideoFrameCallback(tick); };
    x.requestVideoFrameCallback(tick);
  };
  const onTime = (e) => { if (!e.target.paused && src.at(e.target.currentTime) >= last) end(); };  // fallback without rVFC
  const broken = (what) => () => say(`Не удалось открыть ${what} в браузере. Проверьте файл во вкладке «Файлы».`, true);
  return html`<section class="mt-compare-box">
    <div class="mt-bar"><b>${v.label}</b><small class="note">кадры ${r.start}–${r.end_exclusive - 1} · ${r.note}</small></div>
    <div class=${'mt-compare ' + view} style=${`--wipe:${pos}%`}>
      <figure><video ref=${before} src=${file(r.source)} muted playsinline preload="auto" onLoadedMetadata=${() => park(r.start)} onTimeUpdate=${onTime} onError=${broken('исходник')}></video><figcaption>Было</figcaption></figure>
      <figure class="after"><video ref=${after} src=${file(v.path)} playsinline preload="auto" onLoadedMetadata=${() => park(r.start)} onError=${broken('вариант ' + v.path)}></video><figcaption>Вариант</figcaption></figure>
      ${view === 'wipe' && html`<input type="range" class="mt-wipe" min="0" max="100" value=${pos} aria-label="Шторка" onInput=${(e) => setCmp({ ...cmp, pos: Number(e.target.value) })} />`}
    </div>
    <div class="mt-acts">
      <button type="button" class=${'ghost small' + (view === 'side' ? ' active' : '')} onClick=${() => setCmp({ ...cmp, view: 'side' })}>Рядом</button>
      <button type="button" class=${'ghost small' + (view === 'wipe' ? ' active' : '')} onClick=${() => setCmp({ ...cmp, view: 'wipe' })}>Шторка</button>
      <button type="button" class="small" onClick=${play}>Играть оба</button><button type="button" class="ghost small" onClick=${stop}>Пауза</button>
      ${r.state !== 'selected' && html`<button type="button" class="small" disabled=${busy} onClick=${onChoose}>Выбрать этот вариант</button>`}
      <button type="button" class="ghost small" disabled=${busy} title="На V2 монтажа над этим куском" onClick=${onPlace}>В монтаж</button>
      <button type="button" class="ghost small" onClick=${() => { stop(); setCmp(null); }}>Закрыть</button>
    </div></section>`;
}

// Montage M1b: the sequence. V1 is the base picture with its sound, V2 lies over it (generated versions, no sound), A1 adds
// sound. Clips are cut, moved and trimmed by hand; every edit is saved to 50-edit\sequence.json with its version, export is
// an exact ffmpeg render with a receipt. Preview plays the clip under the playhead (V2 over V1) on a frame clock of its own.
const fpsOf = (s) => { if (!s) return null; const [a, b = '1'] = String(s).split('/'); const v = Number(a) / Number(b); return v > 0 && Number.isFinite(v) ? v : null; };
const sid = () => nonce().replace(/-/g, '').slice(0, 12);
const len = (c) => c.end - c.start;
const fin = (c) => c.at + len(c);
const under = (f, row) => row.find((c) => c.at <= f && f < fin(c));
const LANES = ['T1', 'V2', 'V1', 'A1'];
const LANE_NAME = { T1: 'T1 титры', V2: 'V2 поверх', V1: 'V1 видео', A1: 'A1 звук' };
const PICTURE = (t) => t === 'V1' || t === 'V2';  // these two switch by dragging up and down; T1 and A1 stay put
const PLACE = { bottom: 'внизу', center: 'по центру', top: 'вверху' }, SIZE = { small: 'мелкий', medium: 'средний', large: 'крупный' };
const LH = 44;
const TICKS = [1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1800, 3600];
const EXP = { queued: 'в очереди', running: 'рендерится', done: 'готово', error: 'ошибка' };
const SAVE = { saved: 'сохранено', dirty: 'не сохранено', saving: 'сохраняю…' };
const framesOf = (m, fv) => m?.frames ?? (m?.seconds ? Math.max(1, Math.round(m.seconds * fv)) : null);
const p2 = (x) => String(x).padStart(2, '0');
const tcOf = (f, fv) => {
  const s = Math.floor(f / fv), ff = Math.min(Math.ceil(fv) - 1, Math.floor(f - s * fv));
  return `${s >= 3600 ? Math.floor(s / 3600) + ':' : ''}${p2(Math.floor(s / 60) % 60)}:${p2(s % 60)}:${p2(ff)}`;
};
const secOf = (s) => s >= 3600 ? `${Math.floor(s / 3600)}:${p2(Math.floor(s / 60) % 60)}:${p2(s % 60)}` : `${Math.floor(s / 60)}:${p2(s % 60)}`;

function Sequence({ ov, slug, add, onClose, onOpen }) {
  const base = '/api/video-review/' + encodeURIComponent(slug);
  const file = (rel) => '/api/project-browser/media?' + new URLSearchParams({ root: 'projects', path: 'video/' + slug + '/' + rel });
  const winPath = (rel) => String(ov.path).replace(/[\\/]+$/, '') + '\\' + rel.replace(/\//g, '\\');
  const [doc, setDoc] = useState(null);
  const [tracks, setTracksState] = useState(null);
  const [media, setMediaState] = useState({});
  const [fps, setFpsState] = useState(null);
  const [save, setSave] = useState('saved');
  const [sel, setSel] = useState(null);  // clip id
  const [now, setNow] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [pxf, setPxf] = useState(null);  // pixels per frame; null = fit the whole sequence
  const [w, setW] = useState(0);
  const [lib, setLib] = useState(null);
  const [msg, setMsg] = useState(null);
  const [busy, setBusy] = useState(false);
  const [ask, setAsk] = useState('');
  const [executor, setExecutor] = useState(store.get('video-review-executor', 'codex'));
  const [ttl, setTtl] = useState({ text: '', seconds: 3, place: 'bottom', size: 'medium' });
  const [out, setOut] = useState(null);  // the last hand-over to FilmCraft / openDAW
  // Refs mirror the state that timers, window listeners and the play loop read.
  const tk = useRef(null), md = useRef({}), fr = useRef(null), pf = useRef(0), pxr = useRef(1), fvr = useRef(25), endR = useRef(0);
  const ver = useRef(0), sf = useRef(null), good = useRef(null), hist = useRef([]), edits = useRef(0), done = useRef(0), inflight = useRef(false);
  const timer = useRef(0), epoch = useRef(0), dragging = useRef(false), placing = useRef(false), gone = useRef(0);
  const pic = useRef(null), over = useRef(null), snd = useRef(null), mus = useRef(null), head = useRef(null), tcBox = useRef(null);
  const scroller = useRef(null), wide = useRef(null), lanesBox = useRef(null);
  const setTracks = (t) => { t = { V1: [], V2: [], A1: [], T1: [], ...t }; tk.current = t; setTracksState(t); };  // older files have no T1
  const setMedia = (f) => { md.current = typeof f === 'function' ? f(md.current) : f; setMediaState(md.current); };
  const setFps = (v) => { fr.current = v; setFpsState(v); };
  const say = (t, bad = false) => setMsg({ t, bad });

  // Saving: edits are counted; a debounced flush sends the newest tracks with the version they were edited from.
  const adopt = (d) => {
    ver.current = d.version; sf.current = d.fps; good.current = d.tracks; setDoc(d);
    setMedia((m) => ({ ...m, ...d.media }));
    if (d.fps) setFps(d.fps);
    else if (!LANES.some((t) => tk.current?.[t]?.length)) {  // an empty sequence forgets its format
      setFps(null); setMedia((m) => Object.fromEntries(Object.entries(m).map(([k, v]) => [k, { ...v, frames: null }])));
    }
  };
  const load = async () => {
    const d = await call(base + '/sequence');
    epoch.current++; clearTimeout(timer.current); hist.current = []; edits.current = done.current = 0;
    setTracks(d.tracks); setFps(d.fps); adopt(d); setSave('saved');
    return d;
  };
  // After leaving the page: one last save (and one retry for a save still in flight), then nothing.
  const later = (ms) => { clearTimeout(timer.current); if (gone.current && gone.current++ > 1) return; timer.current = setTimeout(flush, ms); };
  const flush = async () => {
    clearTimeout(timer.current);
    if (inflight.current || dragging.current || done.current === edits.current) return;
    inflight.current = true; setSave('saving');
    const n = edits.current, ep = epoch.current;
    let wait = 300;
    try {
      const d = await call(base + '/sequence', { version: ver.current, tracks: tk.current });
      if (ep === epoch.current) { done.current = n; adopt(d); }
    } catch (e) {
      if (ep !== epoch.current) return;
      if (e.status === 409) { say(e.message, true); await load().catch((x) => say(x.message, true)); }
      else if (!e.status || e.status >= 500) { say('Монтаж не сохранился (' + e.message + '). Повторю через 3 с.', true); wait = 3000; }
      else if (fr.current !== sf.current) { say('Не сохранено: ' + e.message, true); await load().catch((x) => say(x.message, true)); }  // back to the saved format
      else { say('Не сохранено: ' + e.message, true); setTracks(good.current); done.current = edits.current; }
    } finally {
      inflight.current = false;
      if (ep === epoch.current) { if (done.current !== edits.current) { setSave('dirty'); later(wait); } else setSave('saved'); }
    }
  };
  const commit = (next, snap = tk.current) => {
    if (placing.current) return say('Подождите: вариант ложится на V2.', true);  // its answer replaces the tracks
    // A new format (A1 already rescaled) reaches the server only with a video: the one that set it stays until the save,
    // the very first format too. Music alone is kept in the saved format, or in 24 fps when nothing is saved yet.
    if (fr.current && fr.current !== (sf.current || '24') && !next.V1.length && !next.V2.length && (next.A1.length || next.T1.length))
      return say('Дождитесь сохранения монтажа и повторите.', true);
    if (snap) hist.current = [...hist.current.slice(-99), snap];
    edits.current++;
    setTracks(next); setSave('dirty'); later(800);
    return true;
  };
  const undo = () => { if (placing.current) return; const s = hist.current.pop(); if (!s) return; edits.current++; setTracks(s); setSave('dirty'); later(300); };
  useEffect(() => () => { gone.current = 1; clearTimeout(timer.current); if (done.current !== edits.current) flush(); }, []);
  useEffect(() => {
    if (save === 'saved') return;
    const on = (e) => { e.preventDefault(); e.returnValue = ''; };
    addEventListener('beforeunload', on); return () => removeEventListener('beforeunload', on);
  }, [save]);

  const once = async (fn) => {
    if (busy) return; setBusy(true);
    try { await fn(); } catch (e) { say(e.message, true); if (e.status === 409) load().catch(() => {}); } finally { setBusy(false); }
  };
  const loadLib = () => call(base + '/sequence/library').then(setLib).catch((e) => setLib({ files: [], takes: [], error: e.message }));
  useEffect(() => { load().then(() => add && addClip(add, 'V1')).catch((e) => say(e.message, true)); loadLib(); }, []);

  // Editing. A new clip lands at the playhead when there is room, else at the end of its track.
  const addClip = (path, lane) => once(() => lay(path, lane));
  const lay = async (path, lane) => {
    const m = await call(base + '/sequence/clip?' + new URLSearchParams({ path }));
    if (lane === 'A1' ? !m.audio : !m.video) throw new Error(`${m.name}: ${lane === 'A1' ? 'в файле нет звука' : 'в файле нет видео'}`);
    // The first video sets the format; music laid before it keeps its time in the new frames.
    const first = PICTURE(lane) && !tk.current.V1.length && !tk.current.V2.length && m.fps;
    if (first && fr.current && first !== fr.current && (inflight.current || done.current !== edits.current))
      throw new Error('Дождитесь сохранения монтажа и повторите.');  // the server fixes the format by the saved tracks
    // Titles and sound laid before any picture keep the saved format (24 fps when none): the server fixes it the same way.
    const fs = first || fr.current || (PICTURE(lane) ? m.sequence_fps : sf.current || '24'), n = fs === m.sequence_fps ? m.frames : Math.max(1, Math.round(m.seconds * (fpsOf(fs) || 25)));
    let T = tk.current;
    const turn = fr.current && fs !== fr.current;
    if (turn) {
      hist.current = [];  // older steps are in the old frames; undo stops at this video
      const k = fpsOf(fs) / fpsOf(fr.current), r = (x) => Math.round(x * k);
      const frames = (v) => (v.seconds ? Math.max(1, Math.round(v.seconds * fpsOf(fs))) : v.frames);
      setMedia((x) => Object.fromEntries(Object.entries(x).map(([p, v]) => [p, { ...v, frames: frames(v) }])));
      const move = (c) => { const at = r(c.at), start = r(c.start), lim = frames(md.current[c.path] || {}) || Infinity;
        return { ...c, at, start, end: Math.max(start + 1, Math.min(start + Math.max(1, r(fin(c)) - at), lim)) }; };
      T = { ...T, A1: T.A1.map(move), T1: T.T1.map(move) };  // sound and titles keep their times
    }
    if (fs !== fr.current) setFps(fs);
    setMedia((x) => ({ ...x, [path]: { ...m, frames: n } }));
    const row = T[lane], f = pf.current, free = !row.some((c) => c.at < f + n && f < fin(c));
    const c = { id: sid(), path, start: 0, end: n, at: free ? f : row.reduce((e, x) => Math.max(e, fin(x)), 0), mute: false, label: '' };
    // A format change is not undone: without this video the server would keep the old format under the rescaled A1.
    if (!commit({ ...T, [lane]: [...row, c].sort((a, b) => a.at - b.at) }, turn ? null : T)) return;
    setSel(c.id); say(`${m.name} → ${lane}${free ? '' : ', в конец дорожки'}.`);
  };
  const place = (t) => {
    if (save !== 'saved') return say('Дождитесь сохранения монтажа и повторите.', true);
    once(async () => {
      const snap = tk.current; placing.current = true;
      const d = await call(base + '/sequence/place', { version: ver.current, request_id: t.request, variant_id: t.variant })
        .finally(() => { placing.current = false; });
      // a placement that changed the frame rate (music-only before) cannot be undone in the old frames
      hist.current = !fr.current || d.fps === fr.current ? [...hist.current.slice(-99), snap] : [];
      setTracks(d.tracks); adopt(d);
      const c = d.tracks.V2.find((x) => !snap.V2.some((y) => y.id === x.id));
      if (c) { setSel(c.id); endR.current = Math.max(endR.current, fin(c)); seekTo(c.at); }
      say(`«${t.label}» лежит на V2${c ? ` над кадрами ${c.at}–${fin(c) - 1}` : ''}.`);
    });
  };
  const found = (id) => { for (const t of LANES) { const c = tk.current?.[t].find((x) => x.id === id); if (c) return [t, c]; } return []; };
  const split = () => {
    const f = pf.current, T = tk.current; if (!T) return;
    let [lane, c] = sel ? found(sel) : [];
    if (!c || !(c.at < f && f < fin(c))) { lane = LANES.find((t) => { const x = under(f, T[t]); return x && x.at < f; }); c = lane && under(f, T[lane]); }
    if (!c) return say('Поставьте курсор внутрь клипа, потом S.', true);
    const k = c.start + f - c.at;
    commit({ ...T, [lane]: T[lane].flatMap((x) => x.id === c.id ? [{ ...x, end: k }, { ...x, id: sid(), start: k, at: f }] : [x]) });
    say('Клип разрезан по курсору.');
  };
  const remove = () => { const [lane, c] = found(sel); if (!c) return; commit({ ...tk.current, [lane]: tk.current[lane].filter((x) => x.id !== c.id) }); setSel(null); };
  const mute = () => { const [lane, c] = found(sel); if (!c) return; commit({ ...tk.current, [lane]: tk.current[lane].map((x) => x.id === c.id ? { ...x, mute: !x.mute } : x) }); };

  // Drag: move (V1 ↔ V2 by height), trim the left or the right edge. Edges snap to 0, the playhead and other clips.
  const grab = (e, lane, c, mode) => {
    if (e.button > 0 || placing.current) return;
    e.stopPropagation(); e.preventDefault(); setSel(c.id);
    const snap = tk.current, x0 = e.clientX, y0 = e.clientY, px = pxr.current, top = lanesBox.current.getBoundingClientRect().top;
    const total = framesOf(md.current[c.path], fvr.current) ?? c.end;
    const edges = [0, pf.current]; for (const t of LANES) for (const x of snap[t]) if (x.id !== c.id) edges.push(x.at, fin(x));
    const near = (v) => { let best = null, d = 8 / px; for (const g of edges) if (Math.abs(g - v) <= d) { d = Math.abs(g - v); best = g; } return best; };
    let moved = false, last = null;
    dragging.current = true;
    const on = (ev) => {
      const dx = ev.clientX - x0;
      if (!moved && Math.abs(dx) < 3 && Math.abs(ev.clientY - y0) < 3) return;
      moved = true;
      const df = Math.round(dx / px), y = { ...c };
      let to = lane;
      if (mode === 'move') {
        const at = Math.max(0, c.at + df), a = near(at), b = near(at + len(c));
        y.at = a != null && (b == null || Math.abs(a - at) <= Math.abs(b - at - len(c))) ? a : b != null ? Math.max(0, b - len(c)) : at;
        if (PICTURE(lane)) to = Math.floor((ev.clientY - top) / LH) <= 1 ? 'V2' : 'V1';
      } else if (mode === 'l') {
        const g = near(c.at + df), dd = Math.max(-c.start, -c.at, Math.min(len(c) - 1, (g ?? c.at + df) - c.at));
        y.start = c.start + dd; y.at = c.at + dd;
      } else {
        const g = near(fin(c) + df);
        y.end = Math.max(c.start + 1, Math.min(total, c.start + (g ?? fin(c) + df) - c.at));
      }
      const next = { ...snap, [lane]: snap[lane].filter((o) => o.id !== c.id) };
      if (next[to].some((o) => o.at < fin(y) && y.at < fin(o))) return;  // no overlap: keep the last good layout
      next[to] = [...next[to], y].sort((a, b) => a.at - b.at);
      last = next; setTracks(next);
    };
    const off = () => { dragging.current = false; removeEventListener('pointermove', on); removeEventListener('pointerup', up); removeEventListener('pointercancel', cancel); };
    const up = () => { off(); if (last) commit(last, snap); else { if (moved) setTracks(snap); if (done.current !== edits.current) later(300); } };
    const cancel = () => { off(); setTracks(snap); if (done.current !== edits.current) later(300); };
    addEventListener('pointermove', on); addEventListener('pointerup', up); addEventListener('pointercancel', cancel);
  };

  // Playhead: the mouse scrubs on the ruler and empty lanes; a finger only taps (dragging scrolls the timeline).
  const at = (ev) => Math.floor((ev.clientX - wide.current.getBoundingClientRect().left) / pxr.current);
  const scrub = (e) => {
    if (e.button > 0 || e.target.closest('.sq-clip')) return;
    if (e.target.closest('.sq-lane')) setSel(null);
    if (e.pointerType === 'mouse') {
      seekTo(at(e));
      const on = (ev) => seekTo(at(ev)), off = () => { removeEventListener('pointermove', on); removeEventListener('pointerup', off); };
      addEventListener('pointermove', on); addEventListener('pointerup', off);
      return;
    }
    const x0 = e.clientX, off = (ev) => { removeEventListener('pointerup', off); removeEventListener('pointercancel', off);
      if (ev.type === 'pointerup' && Math.abs(ev.clientX - x0) < 6) seekTo(at(ev)); };
    addEventListener('pointerup', off); addEventListener('pointercancel', off);
  };
  const seekTo = (f) => { f = Math.max(0, Math.min(endR.current, Math.round(f))); pf.current = f; setPlaying(false); setNow(f); paint(f); };

  // Preview: one picture element (V2 over V1, hidden in gaps) with the T1 title over it; the V1 and A1 sound follow the playhead.
  const follow = (el, c, f, play) => {
    if (!el) return false;
    if (!c) { if (!el.paused) el.pause(); return false; }
    const src = file(c.path), t = (c.start + f - c.at + 0.25) / fvr.current;
    if (el.dataset.src !== src) { el.dataset.src = src; el.src = src; }
    if (play) { if (Math.abs(el.currentTime - t) > 0.25) el.currentTime = t; if (el.paused) el.play().catch(() => {}); }
    else { if (!el.paused) el.pause(); if (Math.abs(el.currentTime - t) > 0.5 / fvr.current) el.currentTime = t; }
    return true;
  };
  const sync = (f, play) => {
    const T = tk.current; if (!T) return;
    const low = under(f, T.V1), shown = follow(pic.current, under(f, T.V2) || low, f, play);
    if (pic.current) pic.current.style.visibility = shown ? 'visible' : 'hidden';
    const tl = follow(over.current, under(f, T.T1), f, play);
    if (over.current) over.current.style.visibility = tl ? 'visible' : 'hidden';
    follow(snd.current, low && !low.mute && md.current[low.path]?.audio ? low : null, f, play);
    const a = under(f, T.A1); follow(mus.current, a && !a.mute ? a : null, f, play);
  };
  const paint = (f) => {
    const x = f * pxr.current, s = scroller.current;
    if (head.current) head.current.style.left = x + 'px';
    if (tcBox.current) tcBox.current.textContent = `${tcOf(f, fvr.current)} · кадр ${f}`;
    if (s && (x < s.scrollLeft || x > s.scrollLeft + s.clientWidth - 16)) s.scrollLeft = Math.max(0, x - 48);
  };
  useEffect(() => {
    if (!playing) return;
    let id = 0; const t0 = performance.now(), f0 = pf.current;
    const tick = (ts) => {
      const f = Math.floor(f0 + (ts - t0) / 1000 * fvr.current);
      if (f >= endR.current) { pf.current = endR.current; setPlaying(false); return; }
      if (f !== pf.current) { pf.current = f; paint(f); sync(f, true); }
      id = requestAnimationFrame(tick);
    };
    id = requestAnimationFrame(tick);
    return () => { cancelAnimationFrame(id); for (const el of [pic.current, over.current, snd.current, mus.current]) el?.pause(); setNow(pf.current); };
  }, [playing]);
  const toggle = () => {
    if (playing) return setPlaying(false);
    if (!endR.current) return;
    if (pf.current >= endR.current) pf.current = 0;
    sync(pf.current, true); setPlaying(true);  // play() inside the click keeps the browser's autoplay permission
  };

  const T = tracks || { V1: [], V2: [], A1: [], T1: [] };
  const fv = fpsOf(fps) || 25; fvr.current = fv;
  const vEnd = Math.max(0, ...T.V1.map(fin), ...T.V2.map(fin)), span = Math.max(vEnd, ...T.A1.map(fin), ...T.T1.map(fin));
  const end = vEnd || span; endR.current = end;
  const fit = Math.max(0.02, (w - 24) / Math.max(span, fv * 20)), pxv = pxf ?? fit; pxr.current = pxv;
  useEffect(() => { if (!playing) { paint(now); sync(now, false); } }, [now, tracks, pxv, playing, media]);
  useEffect(() => {
    const el = scroller.current; if (!el) return;
    const ro = new ResizeObserver(() => setW(el.clientWidth)); ro.observe(el); setW(el.clientWidth);
    return () => ro.disconnect();
  }, [!!tracks]);
  const zoom = (k) => setPxf(Math.min(40, Math.max(0.02, pxv * k)));

  // Export: only a saved version; poll while it runs (only the export list is taken from the answer).
  const exps = doc?.exports || [];
  const running = exps.some((e) => e.state === 'queued' || e.state === 'running');
  const exportNow = () => once(async () => {
    if (save !== 'saved') throw new Error('Дождитесь сохранения монтажа.');
    const changed = Object.values(md.current).filter((m) => m.changed && !m.missing).map((m) => m.name);
    if (changed.length) {
      if (!confirm(`После сохранения монтажа заменили: ${changed.join(', ')}.\nПересохранить монтаж с новыми файлами и экспортировать?`)) return;
      adopt(await call(base + '/sequence', { version: ver.current, tracks: tk.current }));
    }
    const e = await call(base + '/sequence/export', { version: ver.current });
    setDoc((d) => ({ ...d, exports: [...(d.exports || []), e] }));
    say('Экспорт идёт на локальном узле (процессор, GPU не занимается). MP4 и квитанция появятся внизу.');
  });
  useEffect(() => {
    if (!running) return;
    let on = true;
    const t = setInterval(() => call(base + '/sequence').then((d) => on && setDoc((x) => ({ ...x, exports: d.exports || [] }))).catch(() => {}), 2000);
    return () => { on = false; clearInterval(t); };
  }, [running]);

  // Titles are made by EffectCraft in the sequence format and land on T1 at the playhead.
  const title = (e) => { e.preventDefault(); once(async () => {
    if (save !== 'saved') throw new Error('Дождитесь сохранения монтажа.');
    say('EffectCraft делает титр на локальном узле…');
    const r = await call(base + '/sequence/title', { version: ver.current, ...ttl, seconds: Number(ttl.seconds) });
    await lay(r.path, 'T1'); setTtl((x) => ({ ...x, text: '' })); loadLib();
  }); };
  // Hand-over to the craft programs on Local node: a FilmCraft project of this version, the V1 and A1 sound as WAV for openDAW.
  const craft = (kind) => once(async () => {
    if (save !== 'saved') throw new Error('Дождитесь сохранения монтажа.');
    setOut(null); say(kind === 'filmcraft' ? 'Собираю проект FilmCraft…' : 'Свожу звук V1 и A1 в WAV…');
    setOut({ kind, ...(await call(base + '/sequence/' + kind, { version: ver.current })) }); setMsg(null);
  });

  // Complex edits go to an agent through the Board: the sequence file, its version and the API are in the task.
  const handoff = (e) => { e.preventDefault(); const t = ask.trim(); if (!t) return; once(async () => {
    if (save !== 'saved') throw new Error('Дождитесь сохранения монтажа.');
    const v = ver.current, api = location.origin + base;
    const task = await call('/api/board', { title: `Монтаж · ${slug} · ${t.slice(0, 60)}`, description: [
      `Монтаж проекта ${slug}: ${winPath('50-edit/sequence.json')} (версия ${v}).`, `Задача: ${t}`,
      'Дорожки: V1 — основное видео со своим звуком, V2 — видео поверх V1 без звука, T1 — титры с прозрачностью поверх всего, A1 — дополнительный звук. Клип: {id, path (от папки проекта), start, end (кадры файла при FPS монтажа, end не входит), at (кадр монтажа), mute, label}; клипы одной дорожки не пересекаются.',
      `Local API: GET ${api}/sequence; POST {version, tracks}; a 409 requires rereading the current version. Export: POST ${api}/sequence/export {version}, requires FFmpeg.`,
      'CPU editing tools: modules/video/scripts/editorial.py and montage.py. Read each subcommand help. Keep all media paths inside the project.',
      'FilmCraft, EffectCraft, OpenMontage and GPU workers are not bundled. Select and configure any external editor explicitly.',
      'Исходники не перезаписывать: новые файлы — в папки проекта. Платные модели — только после сметы и согласия оператора.',
      `Метка: video-sequence:${slug}:v${v}`].join('\n'),
      acceptance: 'Монтаж сохранён новой версией через API (или в задаче сказано, почему нет); исходники не изменены; сделанное описано в задаче.',
      project_id: await projectCardId(slug), executor, priority: 'P2' });
    setAsk(''); say(handedOff(task, await handoffPrompt(task)));
  }); };

  useEffect(() => {
    const on = (e) => {
      if (e.altKey || e.target.closest?.('input,textarea,select')) return;
      if ((e.ctrlKey || e.metaKey) && e.code === 'KeyZ') { e.preventDefault(); undo(); return; }
      if (e.ctrlKey || e.metaKey) return;
      if (['Space', 'Enter'].includes(e.code) && e.target.closest?.('button,summary,a')) return;
      const step = e.shiftKey ? 10 : 1;
      const act = { Space: toggle, KeyK: toggle, KeyS: split, Delete: remove, Backspace: remove, Home: () => seekTo(0), End: () => seekTo(endR.current),
        ArrowLeft: () => seekTo(pf.current - step), ArrowRight: () => seekTo(pf.current + step) }[e.code];
      if (act) { e.preventDefault(); act(); }
    };
    document.addEventListener('keydown', on);
    return () => document.removeEventListener('keydown', on);
  });

  if (!tracks) return html`<div class="mt-bar"><button type="button" class="ghost" onClick=${onClose}>← Все видео</button><b class="mt-name">Монтаж</b></div>
    <p class=${msg?.bad ? 'err' : 'note'}>${msg?.t || 'Открываю монтаж…'}</p>`;
  const hasVideo = T.V1.length + T.V2.length > 0;
  const step = !hasVideo ? 0 : !T.V2.length ? 1 : exps.some((e) => e.state === 'done' && e.version === doc?.version) ? 4 : 3;
  const hint = {
    0: 'Добавьте видео из «Файлы проекта» кнопкой «+ V1» — клипы встанут друг за другом.',
    1: 'Двигайте и обрезайте клипы мышью (за края), S — разрезать по курсору. Переделать кусок: выберите клип → «Сгенерировать кусок».',
    3: 'Новая версия лежит на V2 поверх оригинала. Проверьте стыки и нажмите «Экспорт MP4».',
    4: 'Экспорт готов — MP4 и квитанция внизу. Сложную правку можно отдать агенту.' }[step];
  const [sl, sc] = sel ? found(sel) : [];
  const sm = sc && media[sc.path];
  const files = lib?.files || [], takes = lib?.takes || [];
  const ar = doc?.width && doc?.height ? [doc.width, doc.height] : [16, 9];
  const wideW = Math.max(w - 2, (span + 5 * fv) * pxv);
  const tickS = TICKS.find((s) => s * fv * pxv >= 64) || 3600;
  const ticks = [];
  for (let s = 0; s * fv * pxv < wideW && ticks.length < 500; s += tickS) ticks.push(html`<i style=${`left:${s * fv * pxv}px`}>${secOf(s)}</i>`);
  const saved = save === 'saved';
  return html`<div class="mt sq">
    <div class="mt-bar"><button type="button" class="ghost" onClick=${onClose}>← Все видео</button><b class="mt-name">Монтаж</b>
      <small class="note">${doc?.width ? `${doc.width}×${doc.height} · ` : ''}${fps ? fv.toFixed(3).replace(/\.?0+$/, '') + ' к/с · ' : ''}${tcOf(end, fv)}</small>
      <span class=${'sq-save ' + save}>${SAVE[save]}</span><span class="sq-grow"></span>
      <button type="button" class="ghost small" disabled=${!hist.current.length} title="Ctrl+Z" onClick=${undo}>Отменить</button>
      <button type="button" class="small" disabled=${busy || running || !saved || !hasVideo} title=${saved ? '' : 'Дождитесь сохранения'} onClick=${exportNow}>${running ? 'Экспорт идёт…' : 'Экспорт MP4'}</button></div>
    <ol class="mt-steps">${['Добавьте видео', 'Режьте и двигайте', 'Переделайте кусок', 'Экспорт'].map((s, i) => html`<li class=${i < step ? 'done' : i === step ? 'now' : ''}><b>${i + 1}</b><span>${s}</span></li>`)}</ol>
    <p class="note mt-hint">${hint}</p>
    ${msg && html`<p class=${msg.bad ? 'err' : 'note'} role="status">${msg.t}</p>`}
    <div class="sq-top">
      <aside class="sq-lib">
        <div class="mt-bar"><b>Файлы проекта</b><span class="sq-grow"></span><button type="button" class="ghost small" title="Обновить список" onClick=${loadLib}>↻</button></div>
        ${!lib ? html`<p class="note">Читаю папку проекта…</p>` : lib.error ? html`<p class="err">${lib.error}</p>`
          : !files.length ? html`<p class="note">Видео и звука в проекте нет.</p>`
          : html`<div class="sq-list">${files.map((f) => html`<div class="sq-row" key=${f.path}>
            <span class=${'sq-kind ' + f.kind}>${f.kind === 'audio' ? 'звук' : 'видео'}</span>
            <div class="sq-name"><b title=${f.path}>${f.name}</b><small class="note">${f.path.split('/').slice(0, -1).join(' / ') || 'корень'} · ${mb(f.size)}</small></div>
            <span class="sq-add">${f.kind === 'video' && f.path.startsWith('50-edit/titles/') ? html`<button type="button" class="ghost small" disabled=${busy} onClick=${() => addClip(f.path, 'T1')}>+ T1</button>`
              : f.kind === 'video' ? html`<button type="button" class="ghost small" disabled=${busy} onClick=${() => addClip(f.path, 'V1')}>+ V1</button><button type="button" class="ghost small" disabled=${busy} onClick=${() => addClip(f.path, 'V2')}>+ V2</button>`
              : html`<button type="button" class="ghost small" disabled=${busy} onClick=${() => addClip(f.path, 'A1')}>+ A1</button>`}</span></div>`)}</div>`}
        <h4>Версии из правок <span class="count">${takes.length}</span></h4>
        ${takes.length ? html`<div class="sq-list">${takes.map((t) => html`<div class="sq-row" key=${t.variant}>
            <span class="sq-kind take">версия</span>
            <div class="sq-name"><b title=${t.path}>${t.selected ? '✓ ' : ''}${t.label}</b><small class="note" title=${t.note}>${t.source.split('/').pop()} · кадры ${t.start}–${t.end_exclusive - 1}</small></div>
            <span class="sq-add"><button type="button" class="small" disabled=${busy || !saved} title="Положить на V2 точно над этим куском" onClick=${() => place(t)}>На V2</button>
              <button type="button" class="ghost small" onClick=${() => onOpen(t.source)}>Правка</button></span></div>`)}</div>`
          : html`<p class="note">Версии появятся после генерации: выберите клип → «Сгенерировать кусок».</p>`}
      </aside>
      <div class="sq-stage">
        <div class="sq-screen" style=${`aspect-ratio:${ar[0]} / ${ar[1]};max-width:min(100%, calc(52vh * ${ar[0]} / ${ar[1]}))`} onClick=${toggle}>
          <video ref=${pic} muted playsinline preload="auto"></video>
          <video ref=${over} class="sq-over" muted playsinline preload="auto"></video>
          ${!end && html`<p class="note">Пусто. Добавьте видео из списка — оно ляжет на V1.</p>`}
        </div>
        <audio ref=${snd} preload="auto"></audio><audio ref=${mus} preload="auto"></audio>
        <div class="mt-controls">
          <button type="button" class="ghost" aria-label="Кадр назад" title="Кадр назад (←)" onClick=${() => seekTo(pf.current - 1)}>◀︎</button>
          <button type="button" aria-label=${playing ? 'Пауза' : 'Воспроизвести'} title="Пробел / K" disabled=${!end} onClick=${toggle}>${playing ? '❚❚' : '▶'}</button>
          <button type="button" class="ghost" aria-label="Кадр вперёд" title="Кадр вперёд (→)" onClick=${() => seekTo(pf.current + 1)}>▶︎</button>
          <span class="mt-tc" ref=${tcBox}></span>
        </div>
        ${span > vEnd && vEnd > 0 && html`<p class="note">Звук на A1 длиннее видео — хвост звука не попадёт в экспорт.</p>`}
      </div>
    </div>
    <div class="sq-tlbar">
      <button type="button" class="ghost small" aria-label="Мельче" onClick=${() => zoom(1 / 1.5)}>−</button>
      <button type="button" class="ghost small" aria-label="Крупнее" onClick=${() => zoom(1.5)}>+</button>
      <button type="button" class="ghost small" disabled=${pxf == null} onClick=${() => setPxf(null)}>Вписать</button>
      <small class="note">Пробел — пуск · S — разрезать · Delete — убрать · Ctrl+Z — отменить · ←/→ — кадр (Shift — 10)</small>
    </div>
    <div class="sq-tl">
      <div class="sq-names"><span class="sq-rh"></span>${LANES.map((t) => html`<span key=${t}>${LANE_NAME[t]}</span>`)}</div>
      <div class="sq-scroll" ref=${scroller}>
        <div class="sq-wide" ref=${wide} style=${`width:${wideW}px`} onPointerDown=${scrub}>
          <div class="sq-ruler">${ticks}</div>
          <div class="sq-lanes" ref=${lanesBox}>${LANES.map((t) => html`<div class=${'sq-lane ' + t} key=${t}>${T[t].map((c) => { const m = media[c.path];
            return html`<div key=${c.id} class=${`sq-clip ${t}${c.id === sel ? ' on' : ''}${m?.missing || m?.changed ? ' bad' : ''}${c.mute ? ' mute' : ''}`}
              style=${`left:${c.at * pxv}px;width:${Math.max(2, len(c) * pxv)}px`}
              title=${`${m?.name || c.path} · кадры файла ${c.start}–${c.end - 1} · ${len(c)} кадр.${m?.missing ? ' · файла нет' : ''}`}
              onPointerDown=${(e) => grab(e, t, c, 'move')}>
              <i class="sq-h l" onPointerDown=${(e) => grab(e, t, c, 'l')}></i><span>${c.label || m?.name || c.path.split('/').pop()}</span><i class="sq-h r" onPointerDown=${(e) => grab(e, t, c, 'r')}></i></div>`; })}</div>`)}</div>
          <b class="sq-head" ref=${head} style=${`left:${now * pxv}px`}></b>
        </div>
      </div>
    </div>
    ${sc && html`<div class="sq-insp">
      <div class="sq-name"><b title=${sc.path}>${sm?.name || sc.path}</b><small class="note">${sl} · кадры файла ${sc.start}–${sc.end - 1} · ${len(sc)} кадр. (${(len(sc) / fv).toFixed(1)} с) · с ${tcOf(sc.at, fv)}</small>
        ${sm?.missing && html`<small class="err">Файла нет в проекте — экспорт не соберётся.</small>`}
        ${sm?.changed && !sm?.missing && html`<small class="err">Файл заменили после сохранения — проверьте клип; экспорт пересохранит монтаж.</small>`}</div>
      <span class="mt-acts">
        <button type="button" class="ghost small" onClick=${split}>Разрезать (S)</button>
        ${(sl === 'V1' || sl === 'A1') && html`<button type="button" class="ghost small" onClick=${mute}>${sc.mute ? 'Включить звук' : 'Без звука'}</button>`}
        ${PICTURE(sl) && !sm?.missing && !sc.path.startsWith('50-edit/') && html`<button type="button" class="small" title="Открыть файл, выделить кусок и сгенерировать новую версию" onClick=${() => onOpen(sc.path)}>Сгенерировать кусок</button>`}
        <button type="button" class="ghost small danger-text" onClick=${remove}>Убрать</button></span></div>`}
    <div class="sq-bottom">
      <form class="mt-form" onSubmit=${handoff}>
        <h4>Отдать агенту</h4>
        <textarea rows="2" aria-label="Задача агенту" maxlength="4000" placeholder="Сложная правка: например, «собери ролик 30 с из лучших кусков под музыку»" value=${ask} onInput=${(e) => setAsk(e.target.value)}></textarea>
        <div class="mt-acts"><button type="submit" class="small" disabled=${busy || !ask.trim() || !saved}>Отдать агенту</button>
          <select aria-label="Исполнитель" value=${executor} onChange=${(e) => { setExecutor(e.target.value); store.set('video-review-executor', e.target.value); }}>
            <option value="codex">Codex</option><option value="claude">Claude</option></select></div>
        <p class="note">Задача ляжет на Доску с путём к монтажу, его версией и маршрутом через OpenMontage; сама ничего не запускает.</p>
      </form>
      <form class="mt-form" onSubmit=${title}>
        <h4>Титр на T1</h4>
        <textarea rows="2" aria-label="Текст титра" maxlength="200" placeholder="До трёх строк" value=${ttl.text} onInput=${(e) => setTtl({ ...ttl, text: e.target.value })}></textarea>
        <div class="mt-acts">
          <label class="note">с <input type="number" class="sq-num" min="0.5" max="30" step="0.5" value=${ttl.seconds} onInput=${(e) => setTtl({ ...ttl, seconds: e.target.value })} /></label>
          <select aria-label="Где" value=${ttl.place} onChange=${(e) => setTtl({ ...ttl, place: e.target.value })}>${Object.entries(PLACE).map(([k, v]) => html`<option value=${k}>${v}</option>`)}</select>
          <select aria-label="Размер" value=${ttl.size} onChange=${(e) => setTtl({ ...ttl, size: e.target.value })}>${Object.entries(SIZE).map(([k, v]) => html`<option value=${k}>${v}</option>`)}</select>
          <button type="submit" class="small" disabled=${busy || !ttl.text.trim() || !saved || !hasVideo}>Сделать титр</button></div>
        <p class="note">EffectCraft на локальном узле, в формате монтажа; ляжет на T1 у курсора. Проект .ecproj — рядом в 50-edit\\titles.</p>
      </form>
      <div>
        <h4>Открыть в программах</h4>
        <div class="mt-acts">
          <button type="button" class="ghost small" disabled=${busy || !saved || !hasVideo} title="Проект .fcproj этой версии со всеми дорожками" onClick=${() => craft('filmcraft')}>Открыть в FilmCraft</button>
          <button type="button" class="ghost small" disabled=${busy || !saved || !(T.V1.length || T.A1.length)} title="Звук V1 и A1 отдельными WAV" onClick=${() => craft('stems')}>Звук в openDAW</button></div>
        ${out?.kind === 'filmcraft' && html`<p class="note">Проект FilmCraft (${out.clips} клип.): <code class="sq-path">${out.native}</code> — откройте его в FilmCraft на локальном узле.</p>
          ${out.warnings.map((w) => html`<p class="err">${w}</p>`)}`}
        ${out?.kind === 'stems' && html`<div class="sq-list">${out.stems.map((x) => html`<div class="sq-row" key=${x.track}>
            <span class="sq-kind audio">${x.track}</span>
            <div class="sq-name"><b title=${x.native}>${x.path.split('/').pop()}</b><small class="note">${x.seconds.toFixed(1)} с · с начала монтажа</small></div>
            <span class="sq-add"><a href=${file(x.path) + '&download=true'} title=${x.native}>WAV</a></span></div>`)}</div>
          <p class="note">${out.daw.responding ? html`openDAW работает: <a href=${out.daw.url} target="_blank" rel="noopener">открыть</a> и перетащить WAV на дорожки (оба с нуля).`
            : html`openDAW не отвечает. Запуск на локальном узле: <code class="sq-path">${out.daw.start}</code>`} С ноутбука — через туннель <code class="sq-path">${out.daw.tunnel}</code>.</p>`}
      </div>
      <div class="sq-exp">
        <h4>Экспорт</h4>
        ${exps.length ? html`<div class="sq-list">${exps.slice(-3).reverse().map((e) => html`<div class="sq-row" key=${e.id}>
          <span class=${'sq-kind ' + e.state}>${EXP[e.state] || e.state}</span>
          <div class="sq-name"><b>Версия ${e.version} · ${when(e.created_at)}</b>
            <small class="note">${e.render_seconds ? `рендер ${Math.round(e.render_seconds)} с` : ''}${e.frames ? ` · ${e.frames} кадр.` : ''}</small>
            ${e.error && html`<small class="err">${e.error}</small>`}</div>
          ${e.state === 'done' && html`<span class="sq-add"><a href=${file(e.path)} target="_blank" rel="noopener" title=${winPath(e.path)}>MP4</a>
            <a href=${file(e.receipt) + '&download=true'} title=${winPath(e.receipt)}>квитанция</a></span>`}</div>`)}</div>`
          : html`<p class="note">Экспортов пока нет. MP4 ляжет в 50-edit\\exports, квитанция — рядом.</p>`}
      </div>
    </div></div>`;
}
