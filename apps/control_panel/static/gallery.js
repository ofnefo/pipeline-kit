const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const types = {image:'Изображения',video:'Видео',audio:'Аудио',model:'3D и CAD',document:'Документы'};
const categories = {result:'Результаты',check:'Проверки интерфейсов',frames:'Кадры',source:'Исходники'};
const symbols = {image:'▧',video:'▶',audio:'♫',model:'◇',document:'▤'};
const fmt = n => new Intl.NumberFormat('ru').format(n || 0);
const bytes = n => n > 1048576 ? `${(n/1048576).toFixed(1)} МБ` : `${Math.ceil(n/1024)} КБ`;
const date = n => new Date(n*1000).toLocaleDateString('ru', {day:'numeric',month:'short',year:'numeric'});
const url = (r, download=false) => `/api/gallery/media/${r.id}${download?'?download=true':''}`;
async function api(path, options={}) {
  const r = await fetch('/api/gallery'+path, options);
  const d = await r.json().catch(()=>({}));
  if (!r.ok) throw Error(d.detail || 'Не удалось связаться с архивом');
  return d;
}
export const loadGallery = () => api('?view=comparisons');
let loaded;
export const renderGallery = data => { loaded=data; return `
  <div class="gallery">
    <div class="ga-intro"><div><span class="ga-eyebrow">МЕДИАТЕКА / ФИНАЛЬНЫЕ РЕЗУЛЬТАТЫ</span><h2>Сравнить. Выбрать. Сохранить.</h2></div>
      <button class="ghost" data-ga="scan">Обновить архив</button></div>
    <div class="ga-stats" aria-label="Состав архива"></div><div class="ga-modes" role="group" aria-label="Раздел архива"></div><div class="ga-context" hidden></div>
    <label class="ga-search"><span class="sr-only">Поиск</span><input type="search" name="q" placeholder="Название, модель, проект или прогон…" autocomplete="off"></label>
    <details class="ga-options"><summary>Фильтры и сортировка</summary><div class="ga-toolbar">
      <label>Проект / прогон<select name="group"><option value="">Все проекты и прогоны</option></select></label>
      <label>Модель / инструмент<select name="model"><option value="">Все найденные</option></select></label>
      <label>Приём<select name="technique"><option value="">Все приёмы</option></select></label>
      <label>Отбор<select name="chosen"><option value="">Любой выбор</option><option value="favorite">Избранное</option><option value="best">Лучшие</option></select></label>
      <label>Порядок<select name="sort"><option value="new">Сначала новые</option><option value="old">Сначала старые</option><option value="name">По названию</option><option value="size">По размеру</option></select></label>
    </div></details>
    <div class="ga-tabs" role="group" aria-label="Тип результата"></div>
    <div class="ga-list-head"><span class="ga-count" role="status" aria-live="polite"></span><button class="ghost" data-ga="export">Скачать список CSV</button></div>
    <div class="ga-error" role="alert" hidden></div><div class="ga-grid"></div>
    <div class="ga-pagination"><button class="ghost" data-ga="prev">← Назад</button><span></span><button class="ghost" data-ga="next">Дальше →</button></div>
    <details class="ga-coverage"><summary>Источники и полнота архива</summary><div></div></details>
    <div class="ga-tray" hidden><div><strong>Сравнение</strong><span class="ga-tray-count"></span></div><div class="ga-tray-names"></div><button data-ga="compare">Сравнить</button><button class="ghost" data-ga="clear">Очистить</button></div>
    <dialog class="ga-dialog" aria-labelledby="ga-dialog-title"><header><h2 id="ga-dialog-title"></h2><button class="ghost" data-ga="close" aria-label="Закрыть просмотр">✕</button></header><div class="ga-dialog-body"></div></dialog>
  </div>`; };

export function mountGallery(view, initial) {
  initial ||= loaded;
  const root = view.querySelector('.gallery');
  if (!root) return;
  if(window.innerWidth<760)root.querySelector('.ga-options').open=false;
  let viewMode = initial.view || 'comparisons', bundle = '';
  let data = initial, offset = 0, kind = '', alive = true, serial = 0, timer, poll;
  const picked = new Map(), current = new Map();
  const params = () => {
    const p = new URLSearchParams({kind,view:viewMode,bundle,offset:String(offset),limit:'48'});
    root.querySelectorAll('input[name],select[name]').forEach(x=>p.set(x.name,x.value));
    return p;
  };
  const error = message => { const el=root.querySelector('.ga-error'); el.hidden=!message; el.textContent=message; };
  function options(name, values, label) {
    const select=root.querySelector(`[name="${name}"]`), value=select.value;
    select.innerHTML=`<option value="">${label}</option>` + Object.entries(values).sort((a,b)=>a[0].localeCompare(b[0],'ru')).map(([k,n])=>`<option value="${esc(k)}">${esc(k)} (${fmt(n)})</option>`).join('');
    select.value=value;
  }
  function draw(d) {
    data=d; current.clear(); d.items.forEach(r=>current.set(r.id,r)); (d.groups||[]).forEach(g=>g.previews.forEach(r=>current.set(r.id,r)));
    root.querySelector('.ga-grid').classList.toggle('ga-group-grid',viewMode!=='results');
    const count = d.facets.kind;
    root.querySelector('.ga-stats').innerHTML = `<div><strong>${fmt(d.all)}</strong><span>финальных результатов</span></div><div><strong>${fmt(count.video)}</strong><span>видео</span></div><div><strong>${fmt(count.image)}</strong><span>изображений</span></div><div><strong>${fmt(count.audio)}</strong><span>аудио</span></div><div><strong>${fmt(d.best)}</strong><span>выбрано лучших</span></div>`;
    options('technique',d.facets.technique||{},'Все приёмы');
    root.querySelector('.ga-modes').innerHTML=[['comparisons','Готовые сравнения'],['models','По моделям'],['results','Все результаты']].map(([v,t])=>`<button class="ghost" data-view="${v}" aria-pressed="${viewMode===v}">${t}</button>`).join('');
    const ctx=root.querySelector('.ga-context');ctx.hidden=!d.bundle;ctx.innerHTML=d.bundle?`<button class="ghost" data-ga="back">← К сравнениям</button><div><strong>${esc(d.bundle.title)}</strong><p>${esc(d.bundle.description)}</p></div>`:'';
    options('group',d.facets.group,'Все проекты и прогоны'); options('model',d.facets.model,'Все найденные');
    root.querySelector('.ga-tabs').innerHTML = [['','Все'],...Object.entries(types)].map(([k,v])=>`<button class="ghost" data-kind="${k}" aria-pressed="${kind===k}">${v}${k?` <span>${fmt(count[k])}</span>`:''}</button>`).join('');
    root.querySelector('.ga-count').textContent = d.scanning ? `Обновляем архив… Сейчас ${fmt(d.all)} файлов` : `${fmt(d.total)} ${viewMode==='comparisons'?'сравнений':viewMode==='models'?'моделей / инструментов':'результатов'} · ${d.updated?'обновлён '+date(d.updated):'архив ещё не собран'}`;
    root.querySelector('[data-ga="scan"]').disabled=d.scanning;
    root.querySelector('.ga-grid').innerHTML = (viewMode==='results'?d.items.length:d.groups?.length) ? (viewMode==='results'?d.items.map(card):d.groups.map(groupCard)).join('') : `<div class="ga-empty"><span>▧</span><h3>${d.scanning?'Собираем результаты':'Ничего не найдено'}</h3><p>${d.scanning?'Можно оставить страницу открытой — результаты появятся здесь.':'Измените фильтры или обновите архив.'}</p><button class="ghost" data-ga="reset">Сбросить фильтры</button></div>`;
    root.querySelector('.ga-pagination span').textContent=d.total?`${fmt(offset+1)}–${fmt(Math.min(offset+48,d.total))} из ${fmt(d.total)}`:'';
    root.querySelector('[data-ga="prev"]').disabled=offset===0;
    root.querySelector('[data-ga="next"]').disabled=offset+48>=d.total;
    root.querySelector('.ga-coverage div').innerHTML=`<p>Показаны завершённые генерации и итоговые варианты обработки. Библиотеки, исходники, извлечённые кадры, скриншоты проверок и неудачные прогоны исключены. Модели и параметры взяты из квитанций; при их отсутствии — из имени и папки. Совпадающие файлы объединены, оригиналы остаются на месте. Сравнения по папкам объединяют варианты серии; одинаковый промпт для них не подтверждён.</p><p>Проверено ${fmt(d.curation?.scanned)} файлов · оставлено ${fmt(d.all)} · готовых сравнений ${fmt(d.sets_count)}.</p><ul>${d.sources.map(s=>`<li>${esc(s.name)}: ${s.available?fmt(s.count)+' файлов':'источник недоступен'}${s.errors?`, пропущено папок/файлов: ${s.errors}`:''}</li>`).join('')}</ul><p>Не сканируются библиотеки программ, веса моделей, секреты, рабочие копии кода и ссылки на другие диски. Старые материалы вне этих источников не входят в этот список.</p>`;
    if(d.error) error(d.error);
    clearTimeout(poll);
    if(d.scanning) poll=setTimeout(()=>load(),2500);
    tray();
  }
  function card(r) {
    const mark=r.selection||{};
    return `<article class="ga-card" data-id="${r.id}">
      <button class="ga-preview" data-open="${r.id}" aria-label="Открыть ${esc(r.name)}">
        <span class="ga-placeholder ga-${r.kind}">${symbols[r.kind]}</span>
        ${['image','video'].includes(r.kind)?`<img src="/api/gallery/thumb/${r.id}" loading="lazy" alt="" onerror="this.hidden=true">`:''}
        <span class="ga-kind">${types[r.kind]}</span>${mark.best?'<span class="ga-best">Лучший</span>':''}
      </button>
      <div class="ga-card-body"><span class="ga-project">${esc(r.group)}</span><button class="ga-name" data-open="${r.id}">${esc(r.label||r.name)}</button>
      <div class="ga-meta"><span>${esc(r.model||categories[r.category])} · ${esc(r.technique||'')}</span><span>${date(r.modified)} · ${bytes(r.size)}</span></div>
      <div class="ga-actions"><button class="ghost" data-pick="${r.id}" aria-pressed="${picked.has(r.id)}">${picked.has(r.id)?'✓ Выбран':'＋ Сравнить'}</button><button class="ghost ga-star" data-favorite="${r.id}" aria-pressed="${!!mark.favorite}" aria-label="${mark.favorite?'Убрать из избранного':'В избранное'}">${mark.favorite?'★':'☆'}</button></div></div></article>`;
  }

  function groupCard(g) {
    return `<article class="ga-card ga-group"><div class="ga-group-previews">${g.previews.slice(0,4).map(r=>`<button class="ga-preview" data-open="${r.id}" aria-label="Открыть ${esc(r.label||r.name)}"><span class="ga-placeholder ga-${r.kind}">${symbols[r.kind]}</span>${['image','video'].includes(r.kind)?`<img src="/api/gallery/thumb/${r.id}" loading="lazy" alt="" onerror="this.hidden=true">`:''}<span class="ga-kind">${esc(r.phase||types[r.kind])}</span></button>`).join('')}</div>
      <div class="ga-card-body"><span class="ga-project">${fmt(g.count)} ${viewMode==='models'?'результатов':'вариантов'}</span><h3>${esc(g.title)}</h3><p class="ga-group-description">${esc(g.description)}</p><div class="ga-actions">${viewMode==='models'?`<button class="ghost" data-model="${esc(g.id)}">Открыть результаты →</button>`:`<button data-setcompare="${g.id}">${g.count>4?'Сравнить первые 4':'Сравнить'}</button><button class="ghost" data-bundle="${g.id}">Все варианты →</button>`}</div></div></article>`;
  }
  function metadata(r) {
    return `<div class="ga-result-meta"><strong>${esc(r.model)}</strong><span>${esc(r.technique||'Генерация')}${r.phase?' · '+esc(r.phase):''}</span>${r.seconds!=null?`<span>${Number(r.seconds).toFixed(1)} с генерации</span>`:''}${r.vram_mib?`<span>VRAM ${(r.vram_mib/1024).toFixed(1)} ГБ</span>`:''}</div>`;
  }
  async function load() {
    const request=++serial;
    try { const d=await api('?'+params()); if(alive&&request===serial) {error(''); draw(d);} }
    catch(e) {if(alive&&request===serial) error(e.message);}
  }
  function tray() {
    const el=root.querySelector('.ga-tray'); el.hidden=!picked.size;
    root.querySelector('.ga-tray-count').textContent=`${picked.size} из 4`;
    root.querySelector('.ga-tray-names').textContent=[...picked.values()].map(x=>x.name).join(' · ');
    root.querySelector('[data-ga="compare"]').disabled=picked.size<2;
  }
  function media(r) {
    if(r.kind==='image')return `<img class="ga-full-image" src="${url(r)}" alt="${esc(r.name)}">`;
    if(r.kind==='video')return `<video controls playsinline preload="metadata" poster="/api/gallery/thumb/${r.id}" src="${url(r)}"></video>`;
    if(r.kind==='audio')return `<div class="ga-audio-art">♫</div><audio controls preload="metadata" src="${url(r)}"></audio>`;
    return `<div class="ga-file-art">${symbols[r.kind]}<p>${r.kind==='model'?'3D / CAD — откройте оригинал в профильном инструменте':'Документ — скачайте для просмотра'}</p></div>`;
  }
  function open(rows) {
    const dialog=root.querySelector('dialog');
    root.querySelector('#ga-dialog-title').textContent=rows.length>1?'Сравнение вариантов':'Просмотр результата';
    root.querySelector('.ga-dialog-body').innerHTML=`${rows.length>1?'<div class="ga-play-controls"><button data-ga="play">▶ Запустить вместе</button><button class="ghost" data-ga="pause">Пауза</button><button class="ghost" data-ga="rewind">В начало</button><span>Видео запускаются без звука. Включите звук у нужного варианта.</span></div>':''}<div class="ga-compare-grid" data-count="${rows.length}">${rows.map((r,i)=>`<section class="ga-candidate" data-id="${r.id}"><div class="ga-candidate-label"><b>${rows.length>1?String.fromCharCode(65+i):types[r.kind]}</b><span>${esc(r.group)}</span></div><div class="ga-media">${media(r)}</div><h3>${esc(r.label||r.name)}</h3>${metadata(r)}<div class="ga-candidate-actions"><button class="ghost" data-best="${r.id}" aria-pressed="${!!r.selection?.best}">${r.selection?.best?'✓ Лучший':'Отметить лучшим'}</button><a href="${url(r,true)}" download>Скачать оригинал ↗</a></div><label>Заметка<textarea data-note="${r.id}" rows="2" maxlength="2000" placeholder="Что нравится, что исправить…">${esc(r.selection?.note||'')}</textarea></label><button class="ghost" data-save="${r.id}">Сохранить заметку</button><span class="ga-save-status" role="status"></span><details><summary>Подробности</summary><p>${r.provenance==='receipt'?'Подтверждено квитанцией':'По имени и папке'} · ${bytes(r.size)} · ${date(r.modified)}</p><p>${esc(r.source)} / ${esc(r.relative)}</p>${r.params?`<dl class="ga-params">${Object.entries(r.params).map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join('')}</dl>`:''}${r.receipt?`<p>Квитанция: ${esc(r.receipt)}</p>`:''}${r.aliases?.length?`<p>Совпадающих копий: ${r.aliases.length}</p>`:''}<p>${esc(r.name)}</p></details></section>`).join('')}</div>`;
    if(!dialog.open)dialog.showModal();
  }
  async function save(id,patch) {
    const selection=await api('/selection/'+id,{method:'PATCH',headers:{'Content-Type':'application/json'},body:JSON.stringify(patch)});
    for(const map of [current,picked])if(map.has(id))map.get(id).selection=selection;
    return selection;
  }
  const click = async e => {
    const b=e.target.closest('button,a'); if(!b)return;
    const id=b.dataset.open||b.dataset.pick||b.dataset.favorite||b.dataset.best||b.dataset.save;
    const r=current.get(id)||picked.get(id);
    try {
      if(b.dataset.view){viewMode=b.dataset.view;bundle='';offset=0;await load();}
      if(b.dataset.model){root.querySelector('[name="model"]').value=b.dataset.model;viewMode='results';bundle='';offset=0;await load();}
      if(b.dataset.bundle){bundle=b.dataset.bundle;viewMode='results';offset=0;await load();}
      if(b.dataset.setcompare){const group=data.groups.find(g=>g.id===b.dataset.setcompare);if(group)open(group.previews);}
      if(b.dataset.kind!==undefined){kind=b.dataset.kind;offset=0;await load();}
      if(b.dataset.open){open([r]);}
      if(b.dataset.pick){
        if(picked.has(id))picked.delete(id);else if(picked.size<4)picked.set(id,r);else {error('Для сравнения можно выбрать до четырёх вариантов. Снимите один из выбранных.');return;}
        b.setAttribute('aria-pressed',String(picked.has(id)));b.textContent=picked.has(id)?'✓ Выбран':'＋ Сравнить';tray();
      }
      if(b.dataset.favorite){b.disabled=true;const s=await save(id,{favorite:!r.selection?.favorite});b.textContent=s.favorite?'★':'☆';b.setAttribute('aria-pressed',String(s.favorite));b.setAttribute('aria-label',s.favorite?'Убрать из избранного':'В избранное');}
      if(b.dataset.best){b.disabled=true;const s=await save(id,{best:!r.selection?.best});b.textContent=s.best?'✓ Лучший':'Отметить лучшим';b.setAttribute('aria-pressed',String(s.best));}
      if(b.dataset.save){b.disabled=true;await save(id,{note:root.querySelector(`[data-note="${id}"]`).value});b.parentElement.querySelector('.ga-save-status').textContent='Сохранено';}
      switch(b.dataset.ga){
        case 'back':bundle='';viewMode='comparisons';offset=0;await load();break;
        case 'scan': b.disabled=true;await api('/refresh',{method:'POST'});poll=setTimeout(load,300);break;
        case 'prev':offset=Math.max(0,offset-48);await load();break;
        case 'next':offset+=48;await load();root.querySelector('.ga-toolbar').scrollIntoView({behavior:'smooth',block:'start'});break;
        case 'reset':root.querySelectorAll('input[name],select[name]').forEach(x=>x.value=x.name==='sort'?'new':'');kind='';bundle='';offset=0;await load();break;
        case 'clear':picked.clear();draw(data);break;
        case 'compare':open([...picked.values()]);break;
        case 'close':root.querySelector('dialog').close();break;
        case 'play':{
          const players=[...root.querySelectorAll('dialog video,dialog audio')];
          const results=await Promise.allSettled(players.map(m=>{m.currentTime=0;m.muted=true;return m.play();}));
          if(results.some(x=>x.status==='rejected'))root.querySelector('.ga-play-controls span').textContent='Один из форматов не воспроизводится браузером. Скачайте оригинал.';
          break;
        }
        case 'pause':root.querySelectorAll('dialog video,dialog audio').forEach(m=>m.pause());break;
        case 'rewind':root.querySelectorAll('dialog video,dialog audio').forEach(m=>{m.pause();m.currentTime=0;});break;
        case 'export':{
          const a=document.createElement('a');a.href='/api/gallery/export?'+params();a.download='результаты.csv';a.click();break;
        }
      }
    } catch(ex) {
      if(root.querySelector('dialog').open){const status=b.parentElement.querySelector('.ga-save-status');if(status)status.textContent=ex.message;else error(ex.message);}
      else error(ex.message);
    } finally {if(b.isConnected)b.disabled=false;}
  };
  root.addEventListener('click',click);
  const change = e => {if(e.target.matches('select')){offset=0;load();}};
  const input = e => {if(e.target.name==='q'){clearTimeout(timer);timer=setTimeout(()=>{offset=0;load();},280);}};
  root.addEventListener('change',change);root.addEventListener('input',input);
  const close = () => {root.querySelector('.ga-dialog-body').innerHTML='';load();};
  root.querySelector('dialog').addEventListener('close',close);
  draw(data);
  return () => {alive=false;clearTimeout(timer);clearTimeout(poll);root.querySelectorAll('video,audio').forEach(m=>m.pause());root.querySelector('dialog').removeEventListener('close',close);root.querySelector('dialog').close();root.removeEventListener('click',click);root.removeEventListener('change',change);root.removeEventListener('input',input);};
}
