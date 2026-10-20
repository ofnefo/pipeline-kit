// Server-side destinations only. Browsing never creates folders or queues downloads.
const esc = v => String(v ?? '').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const drafts = new Map();
let initialized = false;
const read = async url => {
  const r = await fetch(url); const data = await r.json();
  if (!r.ok) throw new Error(data.detail || 'Не удалось загрузить папки.');
  return data;
};

export function destinationFields(url = false) {
  return `<div class="dl-destination"><label>Папка назначения
    <span class="dl-folder-control"><input name="dest" placeholder="Выберите папку на сервере" ${url ? '' : 'required'}>
    <button type="button" class="ghost" data-dl-pick>Выбрать папку</button></span></label>
    ${url ? `<label>Имя файла <input name="filename" placeholder="Например, textures.zip"></label>
    <details><summary>Полный путь вручную</summary><label>Файл назначения
    <input name="target" required placeholder="workspace/downloads/textures.zip"></label>
    <p class="note">Заполняется из папки и имени файла. Здесь можно указать другой разрешённый путь.</p></details>` : ''}</div>`;
}

export function restoreDownloadDrafts() {
  requestAnimationFrame(() => {
    for (const f of document.querySelectorAll('.dl-form')) {
      const saved = drafts.get(f.id);
      if (!saved) continue;
      for (const el of f.elements) {
        if (!el.name || !(el.name in saved)) continue;
        if (el.type === 'checkbox') el.checked = saved[el.name];
        else el.value = saved[el.name];
      }
    }
  });
}

export function clearDownloadDraft(form) { drafts.delete(form.id); }
function remember(form) {
  const data = {};
  for (const el of form.elements) if (el.name) data[el.name] = el.type === 'checkbox' ? el.checked : el.value;
  // Keep URLs only in memory: they can contain temporary credentials.
  drafts.set(form.id, data);
}
function updateTarget(form) {
  if (form.id !== 'dl-url') return;
  const folder = form.elements.dest.value.trim().replace(/[\\/]+$/, '');
  const name = form.elements.filename.value.trim();
  form.elements.filename.setCustomValidity(/[\\/]/.test(name) ? 'Укажите имя файла без папок.' : '');
  form.elements.target.value = folder && name ? `${folder}/${name}` : '';
}

export function initDownloadPicker() {
  if (initialized) return;
  initialized = true;
  const css = document.createElement('link'); css.rel = 'stylesheet'; css.href = '/static/download-picker.css'; document.head.append(css);
  for (const event of ['input', 'change']) document.addEventListener(event, e => {
    const f = e.target.closest('.dl-form'); if (!f) return;
    if (['dest', 'filename'].includes(e.target.name)) updateTarget(f);
    // Suggest the last URL segment only if the owner has not chosen a filename.
    if (event === 'change' && e.target.name === 'url' && !f.elements.filename.value) {
      try { f.elements.filename.value = decodeURIComponent(new URL(e.target.value).pathname.split('/').pop()); updateTarget(f); } catch {}
    }
    remember(f);
  });
  document.addEventListener('click', e => {
    const button = e.target.closest('[data-dl-pick]');
    if (button) openPicker(button.closest('form'), button);
  });
  // A manually entered full path may be missing inside a closed disclosure.
  document.addEventListener('invalid', e => {
    if (e.target.name === 'target') {
      const details = e.target.closest('details'); if (details) details.open = true;
    }
  }, true);
}

async function openPicker(form, opener) {
  if (document.querySelector('#dl-folder-dialog')) return;
  const dialog = document.createElement('dialog'); dialog.id = 'dl-folder-dialog';
  dialog.className = 'dl-folder-dialog'; dialog.setAttribute('aria-labelledby', 'dl-folder-title');
  dialog.innerHTML = `<h2 id="dl-folder-title">Куда сохранить файл</h2>
    <label>Раздел <select data-root disabled><option>Загрузка разделов…</option></select></label>
    <div class="dl-folder-location"><button type="button" class="ghost" data-up disabled>↑ На уровень выше</button><span class="note" data-path></span></div>
    <p class="note" data-hint></p><div class="dl-folder-list" aria-label="Подпапки"></div>
    <div class="actions" data-pages></div>
    <label>Новая подпапка <input data-new placeholder="Необязательно, например CC0/textures" disabled></label>
    <p class="note">Новая папка появится при сохранении загруженного файла.</p>
    <p class="form-msg" role="status" aria-live="polite"></p>
    <div class="actions"><button type="button" data-choose disabled>Выбрать эту папку</button><button type="button" class="ghost" data-close>Отмена</button></div>`;
  document.body.append(dialog); dialog.showModal();
  dialog.addEventListener('close', () => { dialog.remove(); opener.focus(); });
  dialog.querySelector('[data-close]').onclick = () => dialog.close();
  const rootSelect = dialog.querySelector('[data-root]'), list = dialog.querySelector('.dl-folder-list');
  const msg = dialog.querySelector('.form-msg'), choose = dialog.querySelector('[data-choose]');
  const sub = dialog.querySelector('[data-new]'), up = dialog.querySelector('[data-up]');
  let current, roots = [], sequence = 0, busy = false;
  async function load(path, offset = 0) {
    const ticket = ++sequence; busy = true; choose.disabled = true; up.disabled = true; sub.disabled = true;
    list.replaceChildren(); dialog.querySelector('[data-pages]').replaceChildren(); msg.textContent = 'Загрузка папок…';
    try {
      const data = await read(`/api/downloads/folders?path=${encodeURIComponent(path)}&offset=${offset}`);
      if (ticket !== sequence || !dialog.isConnected) return;
      current = data; busy = false; sub.value = ''; sub.disabled = !data.selectable;
      choose.disabled = !data.selectable || data.pending_worker_reload; up.disabled = !data.parent;
      dialog.querySelector('[data-path]').textContent = data.path;
      dialog.querySelector('[data-hint]').textContent = data.pending_worker_reload ? 'Библиотека станет доступна после обновления загрузчика. Текущие передачи продолжаются; пока можно выбрать «Общие загрузки».' : data.selectable ? (data.exists ? 'Выберите эту папку или откройте подпапку.' : 'Папка будет создана при сохранении файла.') : 'Выберите проект, затем его папку downloads.';
      list.innerHTML = data.folders.map(x => `<button type="button" class="ghost" data-folder="${esc(x.path)}">▸ ${esc(x.name)}</button>`).join('') || '<p class="note">Подпапок нет.</p>';
      dialog.querySelector('[data-pages]').innerHTML = `${data.offset ? '<button type="button" class="ghost" data-page="prev">← Назад</button>' : ''}${data.next_offset != null ? '<button type="button" class="ghost" data-page="next">Ещё папки →</button>' : ''}`;
      msg.textContent = '';
    } catch (err) {
      if (ticket !== sequence || !dialog.isConnected) return;
      busy = false; current = null; msg.textContent = err.message;
      list.innerHTML = '<button type="button" class="ghost" data-retry>Повторить</button>';
      list.querySelector('[data-retry]').onclick = () => load(path, offset);
    }
  }
  rootSelect.onchange = () => load(rootSelect.value);
  up.onclick = () => { if (!busy && current?.parent) load(current.parent); };
  dialog.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b || busy) return;
    if (b.dataset.folder) load(b.dataset.folder);
    if (b.dataset.page && current) load(current.path, b.dataset.page === 'prev' ? Math.max(0, current.offset - 100) : current.next_offset);
  });
  choose.onclick = async () => {
    if (busy || !current?.selectable) return;
    const suffix = sub.value.trim();
    if (suffix && (/^[\\/]/.test(suffix) || suffix.split(/[\\/]/).some(x => !x || x === '.' || x === '..') || /[:<>"|?*]/.test(suffix))) {
      msg.textContent = 'Укажите относительное имя подпапки без «..» и специальных символов.'; sub.focus(); return;
    }
    busy = true; choose.disabled = true; rootSelect.disabled = true;
    try {
      const data = await read(`/api/downloads/folders?path=${encodeURIComponent(current.path + (suffix ? '/' + suffix : ''))}`);
      if (!dialog.isConnected) return;
      if (!data.selectable) throw new Error('Выберите папку downloads внутри проекта.');
      if (data.pending_worker_reload) throw new Error('Загрузчик ещё обновляется. Выберите «Общие загрузки» или подождите.');
      form.elements.dest.value = data.path; updateTarget(form); remember(form); dialog.close();
    } catch (err) { msg.textContent = err.message; busy = false; choose.disabled = false; rootSelect.disabled = false; }
  };
  try {
    roots = (await read('/api/downloads/destinations')).roots;
    if (!dialog.isConnected) return;
    rootSelect.innerHTML = roots.map(r => `<option value="${esc(r.path)}">${esc(r.label)}${r.pending_worker_reload ? ' · после текущих загрузок' : ''}</option>`).join(''); rootSelect.disabled = false;
    const normalize = v => v.replaceAll('\\', '/').toLowerCase().replace(/\/$/, '');
    const saved = form.elements.dest.value.trim();
    const match = roots.find(r => normalize(saved) === normalize(r.path) || normalize(saved).startsWith(normalize(r.path) + '/'));
    rootSelect.value = (match || roots.find(r => /hub[\\/]Downloads$/i.test(r.path)) || roots[0]).path;
    await load(match ? saved : rootSelect.value);
  } catch (err) { msg.textContent = `${err.message} Закройте окно и попробуйте снова; ручной ввод пути доступен в форме.`; }
}
