// Voice-over Google AI Studio: tetapan, semakan WAV dan orkestrasi per babak.
// Modul ini tidak menyentuh rangkaian atau browser; pemandu (driver) disuntik supaya boleh diuji.
const fs=require('node:fs'),os=require('node:os'),path=require('node:path'),crypto=require('node:crypto'),{spawnSync}=require('node:child_process');

const DEFAULT_VOICE=Object.freeze({
 voice:'Ludo',
 style:'Baca dalam Bahasa Melayu Malaysia baku. Gunakan nada narator latihan korporat yang jelas, tenang dan yakin. Ikut skrip dengan tepat. Beri jeda natural dan sebut akronim, nama serta kod mengikut bentuk sebutan yang ditulis.'
});
const MAX_WAV=50*1024*1024;
const MIN_SECONDS=0.5; // Pemain AI Studio pernah mendedahkan klip 0.04 s sebelum WAV penuh dimuatkan.

function cleanSettings(input){
 if(!input||typeof input!=='object')throw Error('Tetapan suara tidak sah.');
 const voice=typeof input.voice==='string'?input.voice.trim():'';const style=typeof input.style==='string'?input.style.trim():'';
 if(!voice||voice.length>40||/[\r\n<>]/.test(voice))throw Error('Nama suara diperlukan (maksimum 40 aksara).');
 if(style.length>1000)throw Error('Arahan gaya maksimum 1000 aksara.');
 return {voice,style};
}
class VoiceSettings{
 constructor(root){this.file=path.join(root,'voice-settings.json');}
 get(){try{return cleanSettings(JSON.parse(fs.readFileSync(this.file,'utf8')));}catch{return {...DEFAULT_VOICE};}}
 set(input){const value=cleanSettings(input);fs.mkdirSync(path.dirname(this.file),{recursive:true});const temp=this.file+'.'+crypto.randomUUID()+'.tmp';fs.writeFileSync(temp,JSON.stringify(value,null,2),{flag:'wx'});fs.renameSync(temp,this.file);return value;}
}

// Baca pengepala WAV dan tolak fail kosong, terpotong atau tidak konsisten.
function wavInfo(buf){
 if(!Buffer.isBuffer(buf)||buf.length<44)throw Error('WAV kosong atau terlalu kecil.');
 if(buf.length>MAX_WAV)throw Error('WAV melebihi had 50 MiB.');
 if(buf.toString('ascii',0,4)!=='RIFF'||buf.toString('ascii',8,12)!=='WAVE')throw Error('Fail bukan WAV.');
 if(buf.readUInt32LE(4)+8!==buf.length)throw Error('WAV terpotong atau saiz pengepala tidak sepadan.');
 let pos=12,fmt=null,data=null;
 while(pos+8<=buf.length){
  const id=buf.toString('ascii',pos,pos+4),size=buf.readUInt32LE(pos+4),start=pos+8;
  if(start+size>buf.length)throw Error('Segmen WAV terpotong.');
  if(id==='fmt '){if(size<16)throw Error('Segmen fmt WAV rosak.');fmt={format:buf.readUInt16LE(start),channels:buf.readUInt16LE(start+2),sampleRate:buf.readUInt32LE(start+4),bits:buf.readUInt16LE(start+14)};}
  else if(id==='data')data={start,size};
  pos=start+size+(size%2);
 }
 if(!fmt||!data)throw Error('WAV tiada segmen fmt atau data.');
 const frame=fmt.channels*fmt.bits/8;if(!(frame>0)||!(fmt.sampleRate>0))throw Error('Format WAV tidak sah.');
 return {...fmt,dataStart:data.start,dataBytes:data.size,duration:data.size/(fmt.sampleRate*frame)};
}
// Pengepala 44 bait kanonik (padVoice dalam video-workflow bergantung padanya).
function canonical(pcm,rate=24000){const out=Buffer.alloc(44+pcm.length);out.write('RIFF',0,'ascii');out.writeUInt32LE(36+pcm.length,4);out.write('WAVEfmt ',8,'ascii');out.writeUInt32LE(16,16);out.writeUInt16LE(1,20);out.writeUInt16LE(1,22);out.writeUInt32LE(rate,24);out.writeUInt32LE(rate*2,28);out.writeUInt16LE(2,32);out.writeUInt16LE(16,34);out.write('data',36,'ascii');out.writeUInt32LE(pcm.length,40);pcm.copy(out,44);return out;}
// Pulangkan PCM 16-bit mono 24 kHz kanonik; tukar melalui ffmpeg jika format asal berbeza.
function normalizeWav(buf,ffmpeg){
 const info=wavInfo(buf);
 if(info.format===1&&info.channels===1&&info.sampleRate===24000&&info.bits===16)return canonical(buf.subarray(info.dataStart,info.dataStart+info.dataBytes));
 if(!ffmpeg)throw Error('Format WAV ('+info.sampleRate+' Hz, '+info.channels+' saluran) memerlukan ffmpeg untuk ditukar.');
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'vf-wav-'));
 try{
  const input=path.join(dir,'in.wav'),output=path.join(dir,'out.wav');fs.writeFileSync(input,buf);
  const r=spawnSync(ffmpeg,['-v','error','-y','-i',input,'-vn','-ar','24000','-ac','1','-c:a','pcm_s16le','-f','wav',output],{windowsHide:true,timeout:60000,encoding:'utf8'});
  if(r.status!==0||!fs.existsSync(output))throw Error('Penukaran WAV gagal: '+String(r.stderr||r.error||'').slice(0,300));
  const out=fs.readFileSync(output),o=wavInfo(out);return canonical(out.subarray(o.dataStart,o.dataStart+o.dataBytes));
 }finally{fs.rmSync(dir,{recursive:true,force:true});}
}
const pieceKey=(text,settings)=>crypto.createHash('sha256').update(JSON.stringify({provider:'google-ai-studio',text,voice:settings.voice,style:settings.style})).digest('hex');

// Jana WAV untuk setiap babak mengikut urutan. Berhenti pada ralat pertama; babak yang siap dipulangkan melalui onPiece.
async function synthesizeAll({driver,scenes,settings,signal,ffmpeg,reuse,onPiece}){
 const pieces=[];
 for(let i=0;i<scenes.length;i++){
  if(signal?.aborted)throw Error('CANCELLED');
  const text=scenes[i].narration,key=pieceKey(text,settings);
  let audio=reuse?.(key)||null,fresh=false;
  if(!audio){const raw=await driver.synthesize({text,voice:settings.voice,style:settings.style,signal});if(signal?.aborted)throw Error('CANCELLED');try{audio=normalizeWav(raw,ffmpeg);}catch(error){throw Error('Audio babak '+(i+1)+' tidak sah: '+error.message);}fresh=true;}
  const info=wavInfo(audio);if(info.duration<MIN_SECONDS)throw Error('Audio babak '+(i+1)+' terlalu pendek ('+info.duration.toFixed(2)+' s); klip tidak lengkap. Cuba semula.');
  const piece={index:i,key,audio,duration:info.duration,sha256:crypto.createHash('sha256').update(audio).digest('hex'),fresh};pieces.push(piece);await onPiece?.(piece);
 }
 return pieces;
}
module.exports={DEFAULT_VOICE,VoiceSettings,cleanSettings,wavInfo,canonical,normalizeWav,pieceKey,synthesizeAll,MIN_SECONDS,MAX_WAV};
