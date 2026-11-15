const $=id=>document.getElementById(id);let busy=false,active=null,dirty=false;
function state(){for(const id of ['save','generate','render','reload'])$(id).disabled=busy||!active;for(const id of ['create','choose','open','embedded','check','folder'])$(id).disabled=busy;for(const b of document.querySelectorAll('#scripts button'))b.disabled=busy;}
async function action(fn){if(busy)return;busy=true;state();try{const r=await fn();if(r?.error)throw Error(r.error);return r;}catch(e){$('status').textContent=e.message;}finally{busy=false;state();}}
async function checked(promise){const r=await promise;if(r?.error)throw Error(r.error);return r;}
function input(parent,label,value,kind='textarea'){
 const l=document.createElement('label'),el=document.createElement(kind);l.textContent=label;el.value=value;el.oninput=()=>{dirty=true;};parent.append(l,el);return el;
}
function display(p){
 active=p;dirty=false;$('project').textContent=p.title;$('location').textContent=p.root;$('scripts').replaceChildren();
 for(const s of p.scenes){
  const a=document.createElement('article'),h=document.createElement('h3');h.textContent=s.id+(s.hasAudio?' · WAV tersedia':' · Belum ada WAV');a.append(h);a.dataset.id=s.id;
  input(a,'Tajuk babak',s.title,'input').className='scene-title';
  input(a,'Isi visual (satu isi setiap baris; maksimum tiga)',s.bullets.join('\n')).className='scene-bullets';
  input(a,'Skrip narasi Ludo',s.narration).className='scene-narration';
  const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='Audio & cap masa sari kata';details.append(summary);
  const listen=document.createElement('button');listen.textContent='Dengar WAV';listen.onclick=()=>action(async()=>{$('status').textContent=(await checked(window.ludo.audio(s.id))).message;});details.append(listen);
  const importAudio=document.createElement('button');importAudio.textContent='Import WAV '+s.id;importAudio.onclick=()=>action(async()=>{ensureSaved();const p=await checked(window.ludo.importWav(s.id));if(p){display(p);$('status').textContent='WAV diimport. Dengar rakaman dan sediakan cap masa sari kata.';}});details.append(importAudio);
  const hint=document.createElement('p');hint.className='hint';hint.textContent='Isi JSON menggunakan saat relatif kepada WAV babak, contohnya [{"start":0.2,"end":2.5,"text":"Ayat yang disebut."}]. Padankan dengan rakaman sebenar.';details.append(hint);
  const cues=document.createElement('textarea');cues.value=JSON.stringify(s.cues,null,2);cues.setAttribute('aria-label','Cap masa sari kata '+s.id);details.append(cues);
  const save=document.createElement('button');save.textContent='Simpan cap masa '+s.id;save.onclick=()=>action(async()=>{$('status').textContent=(await checked(window.ludo.cues(s.id,JSON.parse(cues.value)))).message;});details.append(save);
  a.append(details);$('scripts').append(a);
 }
 state();
}
function ensureSaved(){if(dirty)throw Error('Simpan suntingan storyboard dahulu.');}
$('create').onclick=()=>action(async()=>{ensureSaved();const p=await checked(window.ludo.create($('title').value));if(p){display(p);$('status').textContent='Draf projek siap. Semak tajuk, isi visual dan narasi setiap babak.';}});
$('choose').onclick=()=>action(async()=>{ensureSaved();const p=await checked(window.ludo.choose());if(p){display(p);$('status').textContent='Projek dibuka.';}});
$('save').onclick=()=>action(async()=>{const scenes=[...document.querySelectorAll('#scripts article')].map(a=>({id:a.dataset.id,title:a.querySelector('.scene-title').value,bullets:a.querySelector('.scene-bullets').value.split('\n').map(s=>s.trim()).filter(Boolean),narration:a.querySelector('.scene-narration').value}));display(await checked(window.ludo.save(scenes)));$('status').textContent='Storyboard disimpan.';});
function browserAction(id,fn){$(id).onclick=async()=>{$(id).disabled=true;try{$('status').textContent=(await checked(fn())).message;}catch(e){$('status').textContent=e.message;}finally{$(id).disabled=busy;}};}
browserAction('open',()=>window.ludo.external());
browserAction('embedded',()=>window.ludo.open());
$('check').onclick=()=>action(async()=>{$('status').textContent=(await checked(window.ludo.check())).message;});
$('generate').onclick=()=>action(async()=>{ensureSaved();$('status').textContent=(await checked(window.ludo.generate())).message;});
$('cancel').onclick=()=>checked(window.ludo.cancel()).then(r=>{$('status').textContent=r.message;}).catch(e=>{$('status').textContent=e.message;});
$('folder').onclick=()=>action(async()=>{$('status').textContent=(await checked(window.ludo.folder())).message;});
$('render').onclick=()=>action(async()=>{ensureSaved();$('status').textContent='Render sedang berjalan. Jangan tutup aplikasi.';$('status').textContent=(await checked(window.ludo.render())).message;});
$('reload').onclick=()=>action(async()=>{ensureSaved();display(await checked(window.ludo.refresh()));$('status').textContent='Babak dimuat semula.';});
window.ludo.onProgress(t=>{$('status').textContent=t.slice(-5000);});
