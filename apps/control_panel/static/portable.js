// Capability explanations use the existing Control components and navigation.
import { renderSettings, mountSettings } from './home.js?v=c3-20261019u';
export function configurePortableViews(views) {
  const optional = {
    gallery: 'Generation result archives require a generation worker adapter.',
    inventory: 'This workspace has no machine inventory. Projects and files remain available locally.',
    mint: 'A messaging assistant is not bundled. Use the local task board.',
    models: 'Generation workers and model weights are optional upstream installations. Local chat can be configured in workspace/config.json and used in Studio. No paid model routes are enabled.',
    server: 'Remote hosts, domain accounts, storage scans and backups are not configured.',
    gpu: 'GPU execution and reservations require an explicit worker adapter.',
    downloads: 'Install optional tools from their upstream projects. This distribution does not download or launch models.',
    agents: 'Choose an agent in the task board to record ownership. Agent processes are launched separately by their operator.',
  };
  for (const [key,message] of Object.entries(optional)) {
    views[key] = { ...views[key], sub:'Optional component', load:async()=>null,
      render:()=>`<div class="card"><h2>${views[key].title}</h2><p>${message}</p><p><a href="#projects">Projects</a> · <a href="#board">Tasks</a> · <a href="#studio">Studio</a></p></div>`, mount:undefined };
  }
  views.health={...views.health,sub:'Local workspace',load:()=>fetch('/api/capabilities').then(r=>r.json()),
    render:d=>`<div class="card"><h2>Pipeline Kit ${d.version}</h2><p>Local control panel is running. Remote monitoring and alerts are disabled.</p><p>Available: ${d.local.join(', ')}.</p></div>`};
  views.settings={...views.settings,sub:'Appearance and optional local model',load:async()=>({}),
    render:()=>renderSettings('<div class="card"><h2>Optional local model</h2><p>Copy config/workspace.example.json to your workspace as config.json. Enable local_chat and enter the model identifier served on the configured loopback endpoint. Restart Control after editing configuration. See docs/CONFIGURATION.md. Credentials are not collected by this panel.</p></div>'),
    mount:mountSettings};
  const renderProjects=views.projects.render;
  views.projects.render=d=>'<div class="view-actions"><button type="button" id="kit-new-project">New project folder</button></div>'+renderProjects(d);
}

document.addEventListener('click', async event=>{
  if(event.target.id!=='kit-new-project')return;
  const data=await fetch('/api/models/projects').then(r=>r.json());
  let dialog=document.getElementById('kit-project-dialog');
  if(!dialog){dialog=document.createElement('dialog');dialog.id='kit-project-dialog';document.body.append(dialog);}
  dialog.innerHTML=`<form id="kit-project-form"><h2>New project folder</h2><label>Pipeline<select name="type">${data.types.map(t=>`<option>${t}</option>`).join('')}</select></label><label>Name<input name="name" required maxlength="80"></label><p role="status"></p><button>Create</button> <button type="button" id="kit-project-close" class="ghost">Cancel</button></form>`;
  dialog.querySelector('#kit-project-close').onclick=()=>dialog.close();
  dialog.querySelector('form').onsubmit=async event=>{
    event.preventDefault();const body=Object.fromEntries(new FormData(event.target));
    const response=await fetch('/api/projects/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
    const result=await response.json();
    if(!response.ok){dialog.querySelector('[role=status]').textContent=result.detail;return;}
    dialog.close();location.hash='#studio/'+result.studio_key;
  };
  dialog.showModal();
});
