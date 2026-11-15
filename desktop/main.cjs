const {app,BrowserWindow,session,shell,ipcMain,dialog}=require('electron');
const path=require('node:path'),fs=require('node:fs'),{pathToFileURL}=require('node:url');
const {BrowserSession}=require('./ludo/browser-session.cjs');const {loadProject,generate}=require('./ludo/project.cjs');
const {inside,layout,runEngine,saveSceneEdits,saveCues}=require('./portable.cjs');
const config=layout(app);
const profile=process.env.OWNVIDEO_LUDO_PROFILE||config.profile;
fs.mkdirSync(profile,{recursive:true});
app.setPath('userData',path.resolve(profile));
let control,browser,selected,job;const dashboard=pathToFileURL(path.join(__dirname,'index.html')).href;
function bind(name,fn){ipcMain.handle('ludo:'+name,async (e,payload)=>{
 if(e.sender!==control?.webContents||e.senderFrame?.url!==dashboard)throw Error('Pemanggil tidak dibenarkan.');
 try{return await fn(payload);}catch(error){return {error:error.message};}
});}
function current(){if(!selected)throw Error('Pilih projek dahulu.');inside(path.join(config.data,'videos'),selected.root);return loadProject(selected.root);}
function details(p){return {...p,scenes:p.scenes.map(s=>{const file=path.join(p.root,'audio',s.id+'.cues.json'),story=JSON.parse(fs.readFileSync(path.join(p.root,'storyboard.json'),'utf8')).scenes.find(x=>x.id===s.id);return {...s,bullets:story.bullets||[],hasAudio:fs.existsSync(path.join(p.root,'audio',s.id+'.wav')),cues:fs.existsSync(file)?JSON.parse(fs.readFileSync(file,'utf8')):[]};})};}
const progress=t=>{if(control&&!control.isDestroyed())control.webContents.send('ludo:progress',t);};
app.whenReady().then(async()=>{
 if(process.argv.includes('--fixture-audit')||process.argv.includes('--live-audit')){await require('./tests/electron-audit.cjs').run({app,BrowserWindow,session,shell,live:process.argv.includes('--live-audit')});return;}
 if(!app.requestSingleInstanceLock()){app.quit();return;}
 browser=new BrowserSession({BrowserWindow,session,shell});
 const proxy=process.env.HTTPS_PROXY;
 if(proxy)await session.fromPartition('persist:ownvideo-ludo').setProxy({proxyRules:proxy});
 control=new BrowserWindow({width:1200,height:900,title:'OwnVideo Apps — Portable',webPreferences:{preload:path.join(__dirname,'preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true}});
 control.webContents.setWindowOpenHandler(()=>({action:'deny'}));control.webContents.on('will-navigate',e=>e.preventDefault());
 control.on('close',e=>{if(job){e.preventDefault();progress('Tunggu proses selesai sebelum menutup aplikasi. Untuk Ludo, tekan Hentikan dahulu.');}});
 bind('choose',async()=>{if(job)throw Error('Proses sedang berjalan.');const r=await dialog.showOpenDialog(control,{title:'Pilih storyboard.json dalam Data/videos',defaultPath:path.join(config.data,'videos'),filters:[{name:'Storyboard JSON',extensions:['json']}],properties:['openFile']});if(r.canceled)return null;if(path.basename(r.filePaths[0])!=='storyboard.json')throw Error('Pilih fail storyboard.json.');const root=inside(path.join(config.data,'videos'),path.dirname(r.filePaths[0]));selected=loadProject(root);return details(selected);});
 bind('create',async payload=>{
  if(job)throw Error('Proses sedang berjalan.');
  if(typeof payload?.title!=='string'||!payload.title.trim()||payload.title.length>200)throw Error('Isi tajuk video (maksimum 200 aksara).');
  const r=await dialog.showOpenDialog(control,{title:'Import bahan video',filters:[{name:'Dokumen',extensions:['txt','md','pdf','docx','pptx']}],properties:['openFile']});if(r.canceled)return null;
  job=new AbortController();try{const result=await runEngine(config,['new',payload.title,'--source',r.filePaths[0]],{onLog:progress});inside(path.join(config.data,'videos'),result.project);selected=loadProject(result.project);return details(selected);}finally{job=null;}
 });
 bind('save',payload=>{if(job)throw Error('Proses sedang berjalan.');const p=current();saveSceneEdits(p,payload);selected=loadProject(p.root);return details(selected);});
 bind('refresh',()=>{if(job)throw Error('Proses sedang berjalan.');selected=current();return details(selected);});
 bind('cues',payload=>{if(job)throw Error('Proses sedang berjalan.');saveCues(current(),payload?.id,payload?.cues);return {message:'Cap masa sari kata disimpan.'};});
 bind('audio',async payload=>{const p=current();if(!p.scenes.some(s=>s.id===payload?.id))throw Error('Babak tidak dikenali.');const file=path.join(p.root,'audio',payload.id+'.wav');inside(p.root,file);const error=await shell.openPath(file);if(error)throw Error(error);return {message:'WAV dibuka dalam pemain audio.'};});
 bind('folder',async()=>{const error=await shell.openPath(selected?current().root:config.data);if(error)throw Error(error);return {message:'Folder setempat dibuka.'};});
 bind('render',async()=>{if(job)throw Error('Proses sedang berjalan.');const p=current();job=new AbortController();try{await runEngine(config,['render',p.root,'--workers','2'],{onLog:progress});return {message:'MP4 dan SRT siap dalam folder outputs. Semak kandungan dan sebutan sebelum berkongsi.'};}finally{job=null;}});
 bind('open',async()=>{if(job)throw Error('Tunggu penjanaan selesai.');await browser.speech();return {message:'Tetingkap dibuka. Login sendiri; pembukaan sahaja tidak mengesahkan login.'};});
 bind('check',async()=>{if(job)throw Error('Penjanaan sedang berjalan.');const r=await browser.prepareSpeech();return {ready:r.ready,message:r.ready?'Editor pertuturan dikesan. Pilihan Ludo akan disemak semasa penjanaan.':r.message};});
 bind('cancel',()=>{job?.abort();return {message:'Permintaan berhenti diterima.'};});
 bind('generate',async()=>{
  if(job||!selected)throw Error('Pilih projek dahulu; satu penjanaan pada satu masa.');
  const ready=await browser.prepareSpeech();if(!ready.ready)throw Error(ready.message);
  const project=current();if(project.revision!==selected.revision)throw Error('Storyboard berubah; pilih dan semak semula.');
  const approval=await dialog.showMessageBox(control,{type:'question',buttons:['Batal','Luluskan dan jana Ludo'],defaultId:0,cancelId:0,title:'Hantar narasi ke Google AI Studio?',message:`${project.scenes.length} babak, ${project.scenes.reduce((n,s)=>n+s.narration.length,0)} aksara narasi akan dihantar.`,detail:'Hanya teks narasi dan gaya suara. Login, kuota dan pilihan Ludo diperlukan. Semak teks yang dipaparkan sebelum meluluskan.'});
  if(approval.response!==1)return {message:'Dibatalkan; tiada narasi dihantar.'};
  job=new AbortController();try{const r=await generate(project,browser,{ffmpeg:config.ffmpeg,signal:job.signal,onProgress:progress});return {message:`${r.clips} WAV disimpan dalam audio/. Semak sebutan dan sediakan cues sebenar sebelum render.`};}finally{job=null;}
 });
 control.on('closed',()=>{job?.abort();browser.dispose();app.quit();});
 await control.loadURL(dashboard);
 if(process.argv.includes('--portable-smoke')){
  const checks=await control.webContents.executeJavaScript('({create:typeof window.ludo.create,render:typeof window.ludo.render,isolated:typeof require==="undefined",generationDisabled:document.getElementById("generate").disabled})');
  if(checks.create!=='function'||checks.render!=='function'||!checks.isolated||!checks.generationDisabled)throw Error('Dashboard smoke check failed.');
  fs.writeFileSync(path.join(config.data,'portable-smoke.json'),JSON.stringify({passed:true,packaged:app.isPackaged,checks},null,2));
  browser.dispose();app.exit(0);
 }
}).catch(()=>{console.error('Aplikasi gagal bermula. Semak paparan desktop dan dependency sistem.');app.exit(1);});
app.on('window-all-closed',()=>{if(!process.argv.includes('--fixture-audit')&&!process.argv.includes('--live-audit'))app.quit();});
