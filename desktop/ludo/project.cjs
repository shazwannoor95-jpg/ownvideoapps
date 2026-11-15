const fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const {normalizeWav,wavInfo,DEFAULT_VOICE,pieceKey}=require('./voiceover.cjs');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
function loadProject(folder){
 const root=fs.realpathSync(folder),file=path.join(root,'storyboard.json');
 const raw=fs.readFileSync(file),story=JSON.parse(raw);const ids=new Set();
 if(!Array.isArray(story.scenes)||!story.scenes.length)throw Error('Storyboard tiada babak.');
 const scenes=story.scenes.map(s=>{
  if(!/^s\d{2,4}$/.test(s.id)||ids.has(s.id)||typeof s.narration!=='string'||!s.narration.trim()||s.narration.length>5000)throw Error('ID/teks babak tidak sah.');
  ids.add(s.id);return {id:s.id,title:String(s.chapter||s.title||s.id),narration:s.narration};
 });
 return {root,title:String(story.title||'ownvideo'),scenes,revision:sha(raw)};
}
function audioDir(project){
 const dir=path.join(project.root,'audio');fs.mkdirSync(dir,{recursive:true});
 if(fs.realpathSync(dir)!==dir)throw Error('Folder audio symlink tidak dibenarkan.');return dir;
}
function atomic(file,data){const temp=file+'.partial.'+crypto.randomUUID();try{fs.writeFileSync(temp,data,{flag:'wx'});fs.renameSync(temp,file);}finally{fs.rmSync(temp,{force:true});}}
async function generate(project,driver,{ffmpeg='ffmpeg',onProgress=()=>{},signal}={}){
 if(loadProject(project.root).revision!==project.revision)throw Error('Storyboard berubah. Pilih dan semak semula projek.');
 const dir=audioDir(project),manifestFile=path.join(dir,'ludo-generation.json');
 if(fs.existsSync(manifestFile)&&fs.lstatSync(manifestFile).isSymbolicLink())throw Error('Manifest symlink tidak dibenarkan.');
 let manifest={provider:'Google AI Studio',voice:'Ludo',human_audio_review:'pending',clips:{}};
 if(fs.existsSync(manifestFile)){
  manifest=JSON.parse(fs.readFileSync(manifestFile));
  if(manifest.provider!=='Google AI Studio'||manifest.voice!=='Ludo'||!manifest.clips)throw Error('Manifest asal tidak dikenali; fail dikekalkan.');
 }
 // Check conflicts before sending any text; never overwrite supplied WAVs.
 for(const s of project.scenes){const file=path.join(dir,s.id+'.wav'),old=manifest.clips[s.id];
  if(fs.existsSync(file)){
   if(!fs.lstatSync(file).isFile()||!old||old.key!==pieceKey(s.narration,DEFAULT_VOICE)||sha(fs.readFileSync(file))!==old.audio_sha256)throw Error('WAV sedia ada tidak sepadan; fail dikekalkan: '+s.id);
   if(wavInfo(fs.readFileSync(file)).duration<.5)throw Error('WAV cache terlalu pendek.');
  }
 }
 for(const s of project.scenes){
  if(signal?.aborted)throw Error('CANCELLED');
  const file=path.join(dir,s.id+'.wav');
  if(fs.existsSync(file)){onProgress(s.id+' — guna semula WAV yang sepadan');continue;}
  onProgress(s.id+' — menjana Ludo');
  const raw=await driver.synthesize({text:s.narration,...DEFAULT_VOICE,signal});
  if(signal?.aborted)throw Error('CANCELLED');
  if(loadProject(project.root).revision!==project.revision)throw Error('Storyboard berubah semasa penjanaan; audio tidak disimpan.');
  const audio=normalizeWav(raw,ffmpeg),info=wavInfo(audio);
  if(info.duration<.5)throw Error('WAV terlalu pendek / mungkin belum lengkap.');
  const temp=file+'.partial.'+crypto.randomUUID();
  try{fs.writeFileSync(temp,audio,{flag:'wx'});fs.linkSync(temp,file);}finally{fs.rmSync(temp,{force:true});}
  manifest.clips[s.id]={key:pieceKey(s.narration,DEFAULT_VOICE),audio_sha256:sha(audio),narration_sha256:sha(Buffer.from(s.narration)),seconds:info.duration,generated_at:new Date().toISOString(),human_audio_review:'pending'};
  atomic(manifestFile,JSON.stringify(manifest,null,2)+'\n');onProgress(s.id+' — WAV disimpan; semakan sebutan diperlukan');
 }
 return {clips:Object.keys(manifest.clips).length,manifest:manifestFile,human_audio_review:'pending'};
}
module.exports={loadProject,generate,audioDir};
