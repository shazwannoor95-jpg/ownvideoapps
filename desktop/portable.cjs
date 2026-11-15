'use strict';
const fs=require('node:fs'),path=require('node:path'),{spawn}=require('node:child_process');

function inside(root,target){
 const realRoot=fs.realpathSync(root),real=fs.realpathSync(target);
 const rel=path.relative(realRoot,real);
 if(rel==='..'||rel.startsWith('..'+path.sep)||path.isAbsolute(rel))throw Error('Pilih projek dalam folder Data/videos aplikasi ini.');
 return real;
}
function layout(app){
 const base=app.isPackaged?path.dirname(process.execPath):path.resolve(__dirname,'..','.cache','portable');
 const data=path.join(base,'Data');
 fs.mkdirSync(path.join(data,'videos'),{recursive:true});
 // Fail clearly on a read-only USB/folder instead of using AppData silently.
 const probe=path.join(data,'.write-check');fs.writeFileSync(probe,'');fs.unlinkSync(probe);
 const runtime=path.join(process.resourcesPath||'', 'runtime');
 return {data,profile:path.join(data,'profile'),engine:app.isPackaged?path.join(process.resourcesPath,'engine'):path.resolve(__dirname,'..'),
  python:app.isPackaged?path.join(runtime,'python','python.exe'):(process.env.OWNVIDEO_PYTHON||'python3'),
  ffmpeg:app.isPackaged?path.join(runtime,'bin','ffmpeg.exe'):'ffmpeg',
  bin:app.isPackaged?path.join(runtime,'bin'):null};
}
function runEngine(config,args,{onLog=()=>{}}={}){
 const env={...process.env,OWNVIDEO_WORKSPACE:config.data,PYTHONUTF8:'1',PYTHONIOENCODING:'utf-8',PYTHONDONTWRITEBYTECODE:'1'};
 if(config.bin){const key=Object.keys(env).find(k=>k.toLowerCase()==='path')||'PATH';env[key]=config.bin+path.delimiter+(env[key]||'');}
 return new Promise((resolve,reject)=>{
  const child=spawn(config.python,['-u',path.join(config.engine,'tools','video.py'),...args],{cwd:config.data,env,windowsHide:true,shell:false});
  let output='',tail='';
  const log=chunk=>{const s=chunk.toString();output=(output+s).slice(-1048576);tail=(tail+s).slice(-5000);onLog(s);};
  child.stdout.on('data',log);child.stderr.on('data',log);
  child.on('error',()=>reject(Error('Python portable tidak dapat dijalankan. Pastikan ZIP diekstrak sepenuhnya.')));
  child.on('close',code=>{
   if(code!==0){reject(Error(tail||'Proses gagal.'));return;}
   const match=output.split(/\r?\n/).filter(x=>x.startsWith('PORTABLE_RESULT=')).pop();
   try{resolve(match?JSON.parse(match.slice('PORTABLE_RESULT='.length)):{message:'Selesai.'});}catch{reject(Error('Respons enjin tidak sah.'));}
  });
 });
}
function saveSceneEdits(project,payload){
 if(!Array.isArray(payload?.scenes)||payload.scenes.length!==project.scenes.length)throw Error('Senarai babak berubah; pilih projek semula.');
 const file=path.join(project.root,'storyboard.json');
 const story=JSON.parse(fs.readFileSync(file,'utf8'));
 const incoming=new Map(payload.scenes.map(s=>[s.id,s]));
 for(const s of story.scenes){
  const edit=incoming.get(s.id);
  if(!edit||typeof edit.title!=='string'||!edit.title.trim()||edit.title.length>300||typeof edit.narration!=='string'||!edit.narration.trim()||edit.narration.length>5000||!Array.isArray(edit.bullets)||!edit.bullets.length||edit.bullets.length>3||edit.bullets.some(t=>typeof t!=='string'||t.length>600))throw Error('Babak tidak sah: '+s.id);
  const wav=path.join(project.root,'audio',s.id+'.wav');
  if(edit.narration!==s.narration&&fs.existsSync(wav))throw Error('Narasi '+s.id+' sudah mempunyai WAV. Cipta versi baharu sebelum menukar narasi.');
  Object.assign(s,{title:edit.title.trim(),narration:edit.narration.trim(),bullets:edit.bullets});
 }
 const temp=file+'.partial';fs.writeFileSync(temp,JSON.stringify(story,null,2)+'\n');fs.renameSync(temp,file);
}
function saveCues(project,id,cues){
 if(!project.scenes.some(s=>s.id===id))throw Error('Babak tidak dikenali.');
 if(!Array.isArray(cues)||!cues.length)throw Error('Isi cap masa sebenar untuk sari kata.');
 let previous=0;
 for(const c of cues){
  if(!c||!Number.isFinite(c.start)||!Number.isFinite(c.end)||c.start<previous||c.end<=c.start||typeof c.text!=='string'||!c.text.trim())throw Error('Cues perlu berurutan dengan start/end dalam saat dan text.');
  previous=c.end;
 }
 const dir=path.join(project.root,'audio');fs.mkdirSync(dir,{recursive:true});inside(project.root,dir);
 const file=path.join(dir,id+'.cues.json');
 if(fs.existsSync(file)&&fs.lstatSync(file).isSymbolicLink())throw Error('Fail symlink tidak dibenarkan.');
 fs.writeFileSync(file,JSON.stringify(cues,null,2)+'\n');
}
module.exports={inside,layout,runEngine,saveSceneEdits,saveCues};
