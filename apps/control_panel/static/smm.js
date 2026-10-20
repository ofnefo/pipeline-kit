// Local editorial planning. Dates and approval never imply remote publication; «Каналы» (social.js) owns sending.
import { mountChannels } from './social.js?v=w3s-20261019';
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let data, brand = '', mode = 'board', search = '', includeArchive = false, refresh;
try { ({brand = '', mode = 'board'} = JSON.parse(localStorage.getItem('smm.view') || '{}')); } catch {}
const request = async (url, method, body) => {
  const r = await fetch(url, method ? {method, headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)} : {});
  const d = await r.json();
  if (!r.ok) throw Error(typeof d.detail === 'string' ? d.detail : 'Проверьте заполнение полей.');
  return d;
};
export const loadSmm = () => request('/api/smm');
const opts = (items, selected) => items.map(([v,t]) => `<option value="${esc(v)}" ${v === selected ? 'selected' : ''}>${esc(t)}</option>`).join('');
const when = value => value ? new Date(value).toLocaleString('ru-RU',{timeZone:'Europe/Moscow',day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'}) : 'Без даты';
const brandName = id => data.brands.find(b => b.id === id)?.name || id;
const card = p => `<button class="smm-post ghost" data-smm-edit="${esc(p.id)}"><span class="smm-meta">${esc(brandName(p.brand))} <span>${esc(data.networks[p.network])}</span></span><strong>${esc(p.title)}</strong><span class="smm-meta">${esc(p.campaign || 'Без кампании')}${p.scheduled ? ` · ${esc(when(p.scheduled))}` : ''}</span></button>`;

function body() {
  if (mode === 'channels') { setTimeout(() => { const el = document.querySelector('#smm-channels'); if (el) mountChannels(el, data, brand); }); return '<div id="smm-channels"><p class="note">Загружаю подключения…</p></div>'; }
  const posts = data.posts.filter(p => (!brand || p.brand === brand) && (includeArchive || p.status !== 'archived') && `${p.title} ${p.text} ${p.campaign}`.toLowerCase().includes(search.toLowerCase()));
  if (mode === 'strategy') return `<div class="grid">${data.brands.filter(b=>!brand || b.id===brand).map(b=>`<article class="card" data-disclosure-skip><h2>${esc(b.name)}</h2><p>${esc(b.offer)}</p><p class="note">${esc(b.audience)}</p><h3>Цель</h3><p>${esc(b.goal)}</p><p><b>Действие:</b> ${esc(b.cta)}</p><details><summary>Рубрики и ритм</summary><ul>${b.pillars.map(p=>`<li>${esc(p)}</li>`).join('')}</ul><p>${esc(b.cadence)}</p></details><details><summary>SEO и ограничения</summary><p>${esc(b.seo)}</p></details></article>`).join('')}</div><p class="note">Рабочая гипотеза на первый месяц. Частотность, охваты и конверсия ещё не измерены.</p>`;
  if (mode === 'accounts') return `<section class="card" data-disclosure-skip><h2>Аккаунты брендов</h2><p class="note">Имя сохраняется в каталоге. Это не подключение и не разрешение на публикацию. Пароли и токены сюда не вводите.</p><form id="smm-account" class="smm-toolbar"><label>Бренд<select name="brand">${opts(data.brands.map(b=>[b.id,b.name]),brand || data.brands[0].id)}</select></label><label>Площадка<select name="network">${opts(Object.entries(data.networks),'instagram')}</select></label><label class="smm-grow">Ссылка или @имя<input name="handle" maxlength="250" required autocomplete="off"></label><button>Сохранить имя</button></form><p id="smm-account-result" role="status"></p>${data.accounts.filter(a=>!brand || a.brand===brand).map(a=>`<p>${esc(brandName(a.brand))} · ${esc(data.networks[a.network])} · ${esc(a.handle)} <small class="note">не подключён</small></p>`).join('') || '<p class="note">Аккаунты пока не указаны.</p>'}</section><div class="grid">${data.providers.map(p=>`<article class="card" data-disclosure-skip><h3>${esc(p.name)}</h3><span class="pill warn">${esc(p.state)}</span><p>${esc(p.detail)}</p><a href="${esc(p.url)}" target="_blank" rel="noopener noreferrer">Документация</a></article>`).join('')}</div>`;
  if (mode === 'calendar') {
    const grouped = new Map();
    [...posts].sort((a,b)=>(a.scheduled ? Date.parse(a.scheduled) : Infinity)-(b.scheduled ? Date.parse(b.scheduled) : Infinity)).forEach(p=>{
      const key = p.scheduled ? new Date(p.scheduled).toLocaleDateString('ru-RU',{timeZone:'Europe/Moscow'}) : 'Без даты';
      if (!grouped.has(key)) grouped.set(key,[]); grouped.get(key).push(p);
    });
    return `<p class="note">Календарь плана · московское время. Автопубликация не подключена.</p><div class="smm-calendar">${[...grouped].map(([day,rows])=>`<section><h3>${esc(day)} <small>${rows.length}</small></h3>${rows.map(card).join('')}</section>`).join('') || '<p>Пока нет материалов по этому фильтру.</p>'}</div>`;
  }
  // UX-31: only columns with materials take board width; empty ones collapse into one line
  const cols=Object.entries(data.states).filter(([s])=>s!=='archived'||includeArchive).map(([s,label])=>({label,rows:posts.filter(p=>p.status===s)}));
  const full=cols.filter(c=>c.rows.length), empty=cols.filter(c=>!c.rows.length);
  const emptyLine=empty.length ? `<p class="smm-empty-cols">Пусто: ${empty.map(c=>esc(c.label)).join(' · ')}</p>` : '';
  return `${emptyLine}<div class="smm-board" style="--smm-cols:${Math.min(full.length,4)||1}">${full.map(c=>`<section class="smm-column"><h2>${esc(c.label)} <small>${c.rows.length}</small></h2>${c.rows.map(card).join('')}</section>`).join('') || '<p class="note">Пока нет материалов по этому фильтру.</p>'}</div>`;
}

export function renderSmm(d) {
  data = d;
  if (brand && !data.brands.some(b=>b.id===brand)) brand='';
  // OAuth callback lands on #smm/channels: open the mode once, then drop the suffix so other modes stay reachable
  if (location.hash === '#smm/channels') { mode='channels'; history.replaceState(null,'','#smm'); }
  if (!['board','calendar','strategy','accounts','channels'].includes(mode)) mode='board';
  return `<div class="smm-workspace"><div class="smm-toolbar"><label>Бренд<select id="smm-brand">${opts([['','Все бренды'],...d.brands.map(b=>[b.id,b.name])],brand)}</select></label><label class="smm-grow">Поиск<input id="smm-search" type="search" value="${esc(search)}" placeholder="Тема или кампания"></label><button id="smm-new">+ Материал</button><a class="smm-export" href="/api/smm/export?brand=${encodeURIComponent(brand)}" download>Экспорт плана</a></div><div class="smm-toolbar smm-tabs" role="group" aria-label="Вид SMM"><div>${[['board','Канбан'],['calendar','Календарь'],['strategy','Стратегия'],['accounts','Аккаунты'],['channels','Каналы']].map(([id,title])=>`<button class="ghost ${mode===id?'selected':''}" data-smm-mode="${id}" aria-pressed="${mode===id}">${title}</button>`).join('')}</div><label class="smm-check"><input id="smm-archive" type="checkbox" ${includeArchive?'checked':''}> Архив</label></div>${mode==='channels' ? '' : `<div class="smm-notice" role="note"><b>Сами посты в сеть не уходят.</b> Здесь материалы готовят, согласуют и выгружают локально. Подключение аккаунтов и публикация в эту сборку не входят.</div>`}<div id="smm-content">${body()}</div></div>`;
}

function repaint() {
  const v = document.querySelector('#view');
  if (v?.dataset.tab !== 'smm') return;
  v.innerHTML=renderSmm(data);
  try {localStorage.setItem('smm.view',JSON.stringify({brand,mode}));} catch {}
}

function editor(id) {
  const p=data.posts.find(p=>p.id===id) || {brand:brand || data.brands[0].id,status:'idea',network:'instagram'};
  const dlg=document.querySelector('#smm-editor');
  dlg.dataset.id=id || '';
  dlg.dataset.revision=p.revision || '';
  const localDate = p.scheduled ? new Date(new Date(p.scheduled).getTime()+3*3600000).toISOString().slice(0,16) : '';
  dlg.innerHTML=`<form id="smm-form"><header><h2>${id?'Материал':'Новый материал'}</h2><button type="button" class="ghost" data-smm-close aria-label="Закрыть редактор">Закрыть</button></header><div class="smm-form-grid"><label>Бренд<select name="brand">${opts(data.brands.map(b=>[b.id,b.name]),p.brand)}</select></label><label>Статус<select name="status">${opts(Object.entries(data.states),p.status)}</select></label></div><label>Название<input name="title" required maxlength="180" value="${esc(p.title)}"></label><fieldset><legend>${id?'Площадка':'Варианты для площадок'}</legend><div class="smm-targets">${Object.entries(data.networks).map(([v,t])=>`<label class="smm-check"><input type="${id?'radio':'checkbox'}" name="network" value="${v}" ${p.network===v?'checked':''}> ${t}</label>`).join('')}</div></fieldset><label>Текст<textarea name="text" rows="6" maxlength="16000" placeholder="Черновик поста…">${esc(p.text)}</textarea></label><label>Призыв к действию<input name="cta" maxlength="500" value="${esc(p.cta)}"></label><div class="smm-form-grid"><label>Дата плана (Москва)<input name="scheduled" type="datetime-local" value="${localDate}"></label><label>Кампания<input name="campaign" maxlength="120" value="${esc(p.campaign)}"></label></div><label>Материал: путь или ссылка<input name="asset" maxlength="2000" value="${esc(p.asset)}" placeholder="Мастер-файл из проекта"></label><details><summary>Задание продакшену и заметки</summary><textarea name="notes" rows="4" maxlength="4000">${esc(p.notes)}</textarea></details><details><summary>Превью текста</summary><div id="smm-preview" class="smm-preview">${esc(p.text || 'Добавьте текст выше.')}</div><p class="note">Текстовый предпросмотр. Медиа смотрите в разделе «Файлы»; формат площадки проверяется перед публикацией.</p></details><p id="smm-form-error" class="err" role="alert"></p><footer><span class="note">Сохранение не публикует пост.</span><button type="submit">${id?'Сохранить':'Создать варианты'}</button></footer></form>`;
  dlg.showModal(); dlg.querySelector('[name=title]').focus();
  dlg.dataset.dirty='false';
}

export function initSmm(onRefresh) {
  refresh=onRefresh;
  const dlg=document.createElement('dialog');dlg.id='smm-editor';dlg.setAttribute('aria-label','Редактор материала');document.body.append(dlg);
  const close=()=>{if(dlg.dataset.dirty==='true' && !confirm('Закрыть без сохранения изменений?'))return;dlg.close();};
  dlg.addEventListener('cancel',e=>{e.preventDefault();close();});
  document.addEventListener('click',e=>{
    if(e.target.closest('[data-smm-close]'))return close();
    if(e.target.closest('#smm-new'))return editor('');
    const edit=e.target.closest('[data-smm-edit]');if(edit)return editor(edit.dataset.smmEdit);
    const tab=e.target.closest('[data-smm-mode]');if(tab){mode=tab.dataset.smmMode;repaint();}
  });
  document.addEventListener('change',e=>{
    if(e.target.id==='smm-brand'){brand=e.target.value;repaint();}
    if(e.target.id==='smm-archive'){includeArchive=e.target.checked;repaint();}
  });
  document.addEventListener('input',e=>{
    if(e.target.id==='smm-search' && mode!=='channels'){search=e.target.value;document.querySelector('#smm-content').innerHTML=body();}
    if(e.target.closest('#smm-form')){dlg.dataset.dirty='true';if(e.target.name==='text')dlg.querySelector('#smm-preview').textContent=e.target.value;}
  });
  document.addEventListener('submit',async e=>{
    if(e.target.id==='smm-account'){
      e.preventDefault();const output=document.querySelector('#smm-account-result');const b=e.target.querySelector('button');b.disabled=true;
      try{await request('/api/smm/accounts','PUT',Object.fromEntries(new FormData(e.target)));data=await loadSmm();repaint();document.querySelector('#smm-account-result').textContent='Имя сохранено. Подключение ещё предстоит.';}catch(err){output.textContent=err.message;b.disabled=false;}return;
    }
    if(e.target.id!=='smm-form')return;
    e.preventDefault();const fd=new FormData(e.target);const targets=fd.getAll('network');const err=dlg.querySelector('#smm-form-error');
    if(!targets.length){err.textContent='Выберите хотя бы одну площадку.';return;}
    const payload=Object.fromEntries(fd);payload.scheduled=payload.scheduled?`${payload.scheduled}:00+03:00`:'';
    const button=e.target.querySelector('[type=submit]');button.disabled=true;err.textContent='';
    try{
      if(dlg.dataset.id)await request(`/api/smm/posts/${dlg.dataset.id}`,'PUT',{...payload,revision:Number(dlg.dataset.revision)});
      else await request('/api/smm/posts','POST',{posts:targets.map(network=>({...payload,network}))});
      dlg.dataset.dirty='false';dlg.close();refresh();
    }catch(error){err.textContent=error.message;}finally{button.disabled=false;}
  });
}
