const $=id=>document.getElementById(id), params=new URLSearchParams(location.search), project=params.get('project')||'';
const base='/api/video-review/'+encodeURIComponent(project);
let media=null, rows=[], current=null, variant=null, busy=false, loadedSource='', pending=null;
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const file=p=>'/api/project-browser/media?'+new URLSearchParams({root:'projects',path:'video/'+project+'/'+p});
function status(text,bad=false){$('status').textContent=text;$('status').className=bad?'error':'success';}
async function api(path='',body){const r=await fetch(base+path,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});const d=await r.json();if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'Не удалось сохранить. Проверьте поля');return d;}
function frame(){return media?Math.min(media.frames-1,Math.max(0,Math.floor($('player').currentTime*media.fps_value+.0001))):0;}
function move(n){if(!media)return;$('player').pause();$('player').currentTime=Math.max(0,Math.min(media.frames-1,n))/media.fps_value;}
async function open(){try{media=null;loadedSource='';const source=$('source').value;media=await api('/media?'+new URLSearchParams({path:source}));loadedSource=source;$('player').src=file(source);$('seek').max=media.frames-1;$('start').value=0;$('start').max=$('end').max=media.frames-1;$('end').value=media.frames-1;$('player').closest('.vr-workspace').classList.toggle('portrait',media.height>media.width);marks();$('format').textContent=`${media.width}×${media.height} · ${media.fps} кадр/с`;
localStorage.setItem('video-review-source:'+project,source);$('source-name').textContent=source.split('/').pop();$('source-settings').open=false;status(media.frame_count_exact?'Выделите участок и опишите правку.':'Выделите участок. Точные кадры будут проверены при подготовке.');}catch(e){$('player').closest('.vr-workspace').classList.remove('portrait');marks();$('source-settings').open=true;status(e.message,true);}}
// UX-37: hand-off goes through the board (Доска). The task description carries a marker, so the request-task
// link needs no extra server state; the board keeps executors, claims, evidence and the owner's approval.
// The assembly marker names the chosen variant: after a re-selection the old build no longer counts.
let tasks=[], boardOk=true, projectCard=null;
const marker=(r,kind)=>`video-review:${r.id}:${kind}`+(kind==='assemble'?`:${r.selected_variant}`:'');
const taskFor=(r,kind)=>tasks.find(t=>t.status!=='cancelled'&&String(t.description||'').includes(marker(r,kind)));
const taskText={queued:'в очереди',running:'агент работает',blocked:'остановлено',review:'готово, проверьте',done:'принято'};
async function board(url,body){const r=await fetch(url,body?{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(typeof d.detail==='string'?d.detail:'Доска не ответила');return d;}
// On a failed read keep the last list and hide hand-off: an empty list would offer a duplicate task.
async function loadTasks(){try{tasks=(await board('/api/board')).tasks||[];boardOk=true;}catch{boardOk=false;}}
async function card(){
  if(projectCard!==null)return projectCard;
  const tail='/projects/video/'+project.toLowerCase();
  try{const {cards}=await board('/api/board/projects');projectCard=(cards.find(c=>String(c.canonical||'').replace(/\\/g,'/').toLowerCase().replace(/\/+$/,'').endsWith(tail))||{}).id||'';}
  catch{projectCard='';}
  return projectCard;
}
function stage(r){
  const prep=taskFor(r,'variants'), build=taskFor(r,'assemble');
  if(r.state==='selected'){
    if(!build)return {text:'Вариант выбран · ждёт сборки',action:'assemble'};
    return {text:build.status==='review'?'Сборка готова — проверьте':'Сборка: '+(taskText[build.status]||build.status),task:build,build:true};
  }
  if(r.state==='review')return {text:'Можно сравнить',task:prep};
  if(!prep)return {text:'Ждёт передачи агенту',action:'variants'};
  return {text:'Варианты: '+(taskText[prep.status]||prep.status),task:prep};
}
function previewPath(evidence){
  const base='/projects/video/'+project.toLowerCase()+'/';
  for(let tok of evidence.replace(/\\/g,'/').split(/[\s;,]+/)){
    tok=tok.replace(/[.)]+$/,'');const i=tok.toLowerCase().indexOf(base);const rel=i>=0?tok.slice(i+base.length):tok;
    if(/^\d\d-[\w.-]+(\/[\w.@-]+)+\.mp4$/i.test(rel)&&!rel.split('/').includes('..'))return rel;
  }
  return '';
}
function assembly(t){
  if(!t.evidence)return '';
  // A browser can't play the FFV1 candidate-master.mkv; show an MP4 from the evidence when the agent made one.
  const mp4=previewPath(t.evidence);
  return `<p class="note">Результат: ${esc(t.evidence)}</p>${mp4?`<video controls playsinline preload="metadata" src="${file(mp4)}"></video>`:''}`;
}
function requestCard(r){
  const s=stage(r), t=s.task;
  const taskLine=t?`<p class="note">Задача <a href="/#board">${esc(t.id)}</a> · ${esc(t.executor)}${t.status==='blocked'&&t.blocker?' · '+esc(t.blocker):''}</p>`:'';
  const preview=s.build&&['review','done'].includes(t.status)?assembly(t):'';
  const handoff=s.action&&!boardOk?'<p class="note">Доска не отвечает — обновите страницу перед передачей.</p>':s.action?`<button class="small" data-handoff="${r.id}" data-kind="${s.action}">${s.action==='assemble'?'Передать на сборку':'Передать агенту'}</button>`:'';
  const accept=s.build&&t.status==='review'?`<button class="small" data-accept="${t.id}">Принять сборку</button>`:'';
  const variants=r.variants.map(v=>`<button class="ghost small" data-compare="${r.id}" data-variant="${v.id}">${r.selected_variant===v.id?'✓ ':''}${esc(v.label)}</button>`).join('');
  const add=r.state!=='selected'?`<details><summary>Добавить готовый вариант</summary><form data-add="${r.id}"><label>Путь в проекте<input name="path" placeholder="60-motion/variant.mp4" required></label><label>Название<input name="label" value="Вариант ${r.variants.length+1}" maxlength="100"></label><button class="ghost" type="submit">Добавить для сравнения</button><p class="note">Файл должен содержать только выделенный участок, с теми же FPS и размером.</p></form></details>`:'';
  return `<article class="vr-request"><strong>${esc(s.text)}</strong><div class="note">Кадры ${r.start}–${r.end_exclusive-1} · ${esc(r.source.split('/').pop())}</div><p>${esc(r.note)}</p>${taskLine}${preview}${handoff}${accept}<button class="ghost small" data-jump="${r.id}">К участку</button>${variants}${add}</article>`;
}
function render(){marks();$('count').textContent=rows.length;$('requests').innerHTML=rows.length?rows.slice().reverse().map(requestCard).join(''):'<p class="note">Пока нет замечаний. Отметьте участок на видео слева.</p>';}
async function handoff(r,kind){
  const known=taskFor(r,kind);if(known)throw Error('Задача '+known.id+' уже на Доске');
  const cmd=`python scripts/video_pipeline.py repair-review --project ${project} --request-id ${r.id}`+(kind==='assemble'?' --assemble':'');
  const frames=`кадры ${r.start}–${r.end_exclusive-1}`;
  const description=[
    `Монтажная проекта ${project}: ${kind==='assemble'?'Оператор выбрал вариант, нужна отдельная сборка':'замечание к участку'} (${frames}, ${r.source}).`,
    `Замечание: ${r.note}`, `Способ: ${r.mode}.`,
      'Read docs/MODULES.md and skills/video-editing/SKILL.md in Pipeline Kit. Prepare a new local version using the included CPU tools or an explicitly configured external adapter. No repair-generation worker is bundled.',
    kind==='assemble'?'В результате укажите путь к receipt.json и к MP4 для просмотра в браузере, если он сделан. Исходный мастер не перезаписывать.'
      :'Варианты (MP4 H.264, только выделенный участок, те же FPS и размер) добавьте в монтажную. Платные модели — только после сметы и согласия оператора.',
    `Метка: ${marker(r,kind)}`].join('\n');
  const task=await board('/api/board',{title:`${kind==='assemble'?'Собрать версию':'Подготовить варианты'} · ${project} · ${frames}`,description,
    acceptance:kind==='assemble'?'Квитанция repair-apply со статусом technical_pass; мастер не изменён; стыки проверены глазами.':'К замечанию добавлен хотя бы один вариант; квитанция генерации лежит в проекте.',
    project_id:await card(),executor:$('executor').value,priority:'P2'});
  tasks=[...tasks.filter(x=>x.id!==task.id),task];render();
  let copied=false;
  try{await navigator.clipboard.writeText((await board(`/api/board/${task.id}/handoff`)).prompt);copied=true;}catch{}
  return {task,copied};
}
async function refresh(){rows=(await api()).requests;await loadTasks();render();}
// UX-41: back goes to the same project folder in the file browser, not to the project list.
const back=()=>{const dir=$('source').value.split('/').slice(0,-1);$('back').href='/#files/'+['video',project,...dir].filter(Boolean).map(encodeURIComponent).join('/');};
$('project-name').textContent=project;$('source').value=params.get('source')||localStorage.getItem('video-review-source:'+project)||'';
back();$('source').addEventListener('change',back);$('open').onclick=open;$('prev').onclick=()=>move(frame()-1);$('next').onclick=()=>move(frame()+1);
$('seek').oninput=e=>move(Number(e.target.value));$('mark-start').onclick=()=>{if(media)$('start').value=frame();marks();};$('mark-end').onclick=()=>{if(media)$('end').value=frame();marks();};
$('player').ontimeupdate=$('player').onseeked=()=>{if(!media)return;$('seek').value=frame();$('position').textContent=`${tc(frame())} · кадр ${frame()}`;};
// UX-38/39: one scrubber (no native controls) with marked ranges, SMPTE-like timecode and editor keys.
const tc=n=>{const r=Math.round(media.fps_value)||1,s=Math.floor(n/r),p=x=>String(x).padStart(2,'0');return `${p(Math.floor(s/3600))}:${p(Math.floor(s/60)%60)}:${p(s%60)}:${p(n%r)}`;};
function marks(){
  const box=$('marks');if(!media){box.innerHTML='';return;}
  const pct=n=>(100*Math.max(0,Math.min(media.frames,n))/media.frames).toFixed(3)+'%';
  const span=(a,b,cls,title)=>`<span class="${cls}" style="left:${pct(a)};width:${pct(b-a)}" title="${esc(title)}"></span>`;
  box.innerHTML=rows.filter(r=>r.source===loadedSource).map(r=>span(r.start,r.end_exclusive,'',`Кадры ${r.start}–${r.end_exclusive-1}: ${r.note}`)).join('')
    +span(Number($('start').value),Number($('end').value)+1,'sel','Выделенный участок');
}
$('marks').onclick=e=>{if(!media)return;const b=$('marks').getBoundingClientRect();move(Math.floor((e.clientX-b.left)/b.width*media.frames));};
$('start').oninput=$('end').oninput=marks;
const toggle=()=>{const p=$('player');if(!media)return;p.paused?p.play().catch(e=>status('Нажмите ещё раз: '+e.message,true)):p.pause();};
$('play').onclick=toggle;$('player').onclick=()=>{if(!$('player').controls)toggle();};
$('player').onplay=$('player').onpause=()=>{const on=!$('player').paused;$('play').textContent=on?'❚❚':'▶';$('play').setAttribute('aria-label',on?'Пауза':'Воспроизвести');};
$('mute').onclick=()=>{const p=$('player');p.muted=!p.muted;$('mute').textContent=p.muted?'🔇':'🔊';$('mute').setAttribute('aria-label',p.muted?'Включить звук':'Выключить звук');};
$('full').onclick=()=>{const p=$('player');p.requestFullscreen?p.requestFullscreen().catch(()=>{}):p.webkitEnterFullscreen?.();};
document.addEventListener('fullscreenchange',()=>{$('player').controls=document.fullscreenElement===$('player');});
// Physical keys (e.code), so the Russian layout works too; fields keep their own typing.
document.addEventListener('keydown',e=>{
  if(!media||e.ctrlKey||e.metaKey||e.altKey||e.target.closest?.('input:not([type=range]),textarea,select,#comparison'))return;
  if(['Space','Enter'].includes(e.code)&&e.target.closest?.('button,summary,a'))return;
  if(e.code.startsWith('Arrow')&&e.target===$('seek'))return;
  const sec=Math.round(media.fps_value), step=e.shiftKey?10:1;
  const act={Space:toggle,KeyK:toggle,KeyJ:()=>move(frame()-sec),KeyL:()=>move(frame()+sec),ArrowLeft:()=>move(frame()-step),ArrowRight:()=>move(frame()+step),
    KeyI:()=>$('mark-start').click(),KeyO:()=>$('mark-end').click()}[e.code];
  if(act){e.preventDefault();act();}
});
const draftKey='video-review-draft:'+project;
try{$('note').value=localStorage.getItem(draftKey)||'';}catch{}
$('note').oninput=()=>localStorage.setItem(draftKey,$('note').value);
$('request-form').onsubmit=async e=>{e.preventDefault();if(busy)return;if(!media||loadedSource!==$('source').value){status('Сначала откройте выбранное видео.',true);return;}if(Number($('end').value)<Number($('start').value)){status('Последний кадр раньше начального.',true);return;}busy=true;$('save').disabled=true;try{const body={source:loadedSource,start:Number($('start').value),end:Number($('end').value)+1,note:$('note').value,mode:$('mode').value,source_identity:media.identity};const key=JSON.stringify(body);if(!pending||pending.key!==key)pending={key,nonce:crypto.randomUUID()};await api('/requests',{...body,nonce:pending.nonce});await refresh();pending=null;$('note').value='';localStorage.removeItem(draftKey);status('Запрос сохранён в проекте. Генерация ещё не запущена.');}catch(e){status(e.message,true);}finally{busy=false;$('save').disabled=false;}};
$('requests').addEventListener('click',async e=>{const b=e.target.closest('[data-handoff],[data-accept]');if(!b||busy)return;busy=true;b.disabled=true;
  try{
    if(b.dataset.handoff){const r=rows.find(x=>x.id===b.dataset.handoff);const {task,copied}=await handoff(r,b.dataset.kind);await refresh();
      status(`Задача ${task.id} на Доске.${copied?' Запрос для сессии скопирован — вставьте его агенту.':' Запрос для сессии — на Доске, кнопка «Передать».'} Генерация сама не запускается.`);}
    else{const t=tasks.find(x=>x.id===b.dataset.accept);if(!confirm('Отметить сборку принятой? Файлы не меняются.'))return;await board(`/api/board/${t.id}`,{version:t.version,action:'approve',data:{}});await refresh();status('Сборка принята.');}
  }catch(err){status(err.message,true);}finally{busy=false;b.disabled=false;}});
$('executor').value=localStorage.getItem('video-review-executor')||'codex';$('executor').onchange=()=>localStorage.setItem('video-review-executor',$('executor').value);
$('requests').onclick=async e=>{const jump=e.target.closest('[data-jump]'), compare=e.target.closest('[data-compare]');if(jump){const r=rows.find(x=>x.id===jump.dataset.jump);$('source').value=r.source;await open();move(r.start);$('start').value=r.start;$('end').value=r.end_exclusive-1;marks();}
if(compare){current=rows.find(x=>x.id===compare.dataset.compare);variant=current.variants.find(v=>v.id===compare.dataset.variant);$('before').src=file(current.source);$('after').src=file(variant.path);$('variant-name').textContent=variant.label;$('compare-note').textContent=current.note;$('comparison').hidden=false;$('comparison').scrollIntoView({behavior:'smooth'});$('before').onloadedmetadata=()=>{$('before').currentTime=current.start/current.media.fps_value;};}};
$('requests').onsubmit=async e=>{const f=e.target.closest('[data-add]');if(!f)return;e.preventDefault();try{await api(`/requests/${f.dataset.add}/variants`,Object.fromEntries(new FormData(f)));await refresh();status('Вариант добавлен. Посмотрите оба ролика перед выбором.');}catch(e){status(e.message,true);}};
$('play-both').onclick=async()=>{if(!current)return;const a=$('before'),b=$('after');a.currentTime=current.start/current.media.fps_value;b.currentTime=0;a.muted=true;b.muted=false;try{await Promise.all([a.play(),b.play()]);}catch(e){a.pause();b.pause();status('Нажмите воспроизведение на ролике: '+e.message,true);}};
$('before').ontimeupdate=()=>{if(current&&$('before').currentTime>=current.end_exclusive/current.media.fps_value){$('before').pause();$('after').pause();}};
$('select-variant').onclick=async()=>{if(!current||!variant)return;if(!confirm(`Выбрать «${variant.label}» для замены отмеченного участка? Исходник сохранится.`))return;try{await api(`/requests/${current.id}/select`,{variant_id:variant.id});await refresh();status('Выбор сохранён. Следующий шаг — сборка отдельной версии и проверка стыков.');}catch(e){status(e.message,true);}};
for(const id of ['player','before','after'])$(id).onerror=()=>status('Браузер не может воспроизвести этот файл. Подготовьте MP4 H.264 для просмотра; исходник сохраняется.',true);
try{await refresh();if($('source').value)await open();else{$('source-settings').open=true;status('Выберите видео проекта. Можно открыть эту страницу из предпросмотра файла.');}}catch(e){status(e.message,true);}
