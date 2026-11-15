const {test}=require('node:test'),assert=require('node:assert/strict'),fs=require('node:fs'),os=require('node:os'),path=require('node:path'),{spawnSync}=require('node:child_process');
const {DEFAULT_VOICE,VoiceSettings,cleanSettings,wavInfo,canonical,normalizeWav,pieceKey,synthesizeAll}=require('../ludo/voiceover.cjs');
const ffmpeg=process.env.VF_TEST_FFMPEG||'ffmpeg';const hasFfmpeg=spawnSync(ffmpeg,['-version']).status===0;
const tone=(seconds,rate=24000,channels=1,extra=false)=>{const n=Math.round(rate*seconds),pcm=Buffer.alloc(n*2*channels);for(let i=0;i<n*channels;i++)pcm.writeInt16LE(Math.round(Math.sin(i/9)*9000),i*2);
 const list=extra?Buffer.concat([Buffer.from('LIST'),Buffer.from([4,0,0,0]),Buffer.from('INFO')]):Buffer.alloc(0);const head=Buffer.alloc(24);head.write('fmt ',0,'ascii');head.writeUInt32LE(16,4);head.writeUInt16LE(1,8);head.writeUInt16LE(channels,10);head.writeUInt32LE(rate,12);head.writeUInt32LE(rate*2*channels,16);head.writeUInt16LE(2*channels,20);head.writeUInt16LE(16,22);
 const d=Buffer.concat([Buffer.from('data'),Buffer.from(new Uint8Array(new Uint32Array([pcm.length]).buffer)),pcm]);const body=Buffer.concat([Buffer.from('WAVE'),head,list,d]);return Buffer.concat([Buffer.from('RIFF'),Buffer.from(new Uint8Array(new Uint32Array([body.length]).buffer)),body]);};

test('tetapan lalai ialah Ludo + gaya narator BM; simpan, muat semula dan tolak input tidak sah',t=>{
 const dir=fs.mkdtempSync(path.join(os.tmpdir(),'vf-voice-'));t.after(()=>fs.rmSync(dir,{recursive:true,force:true}));const s=new VoiceSettings(dir);
 assert.deepEqual(s.get(),{...DEFAULT_VOICE});assert.equal(s.get().voice,'Ludo');assert.match(s.get().style,/Bahasa Melayu Malaysia baku/);
 s.set({voice:' Kore ',style:'Tenang.'});assert.deepEqual(new VoiceSettings(dir).get(),{voice:'Kore',style:'Tenang.'});
 for(const bad of [null,{voice:'',style:''},{voice:'x'.repeat(41),style:''},{voice:'a\nb',style:''},{voice:'Ludo',style:'x'.repeat(1001)}])assert.throws(()=>cleanSettings(bad));
 fs.writeFileSync(path.join(dir,'voice-settings.json'),'{rosak');assert.equal(s.get().voice,'Ludo');
});
test('wavInfo: sah, kosong, terpotong dan bukan WAV',()=>{
 const ok=tone(1);const info=wavInfo(ok);assert.equal(info.sampleRate,24000);assert.equal(info.channels,1);assert.ok(Math.abs(info.duration-1)<1e-6);
 assert.throws(()=>wavInfo(Buffer.alloc(10)),/kosong/);assert.throws(()=>wavInfo(Buffer.from('x'.repeat(100))),/bukan WAV/i);
 assert.throws(()=>wavInfo(ok.subarray(0,ok.length-100)),/terpotong/);
 const bad=Buffer.from(ok);bad.writeUInt32LE(bad.readUInt32LE(4)+50,4);assert.throws(()=>wavInfo(bad),/terpotong|tidak sepadan/);
 assert.ok(wavInfo(tone(0.04)).duration<0.5);
});
test('normalizeWav: PCM mono 24 kHz diberi pengepala kanonik 44 bait walaupun ada segmen tambahan',()=>{
 const messy=tone(1,24000,1,true);assert.ok(messy.indexOf('LIST')>0);const out=normalizeWav(messy);assert.equal(out.length,44+24000*2);assert.equal(out.toString('ascii',36,40),'data');assert.equal(out.readUInt32LE(40),48000);assert.deepEqual(out,canonical(out.subarray(44)));
 assert.throws(()=>normalizeWav(tone(1,48000,2)),/ffmpeg/);
});
test('normalizeWav: 48 kHz stereo ditukar ke mono 24 kHz melalui ffmpeg',{skip:hasFfmpeg?false:'ffmpeg tiada'},()=>{
 const out=normalizeWav(tone(1,48000,2),ffmpeg);const info=wavInfo(out);assert.equal(info.sampleRate,24000);assert.equal(info.channels,1);assert.equal(info.bits,16);assert.equal(info.dataStart,44);assert.ok(Math.abs(info.duration-1)<0.02,String(info.duration));
 assert.throws(()=>normalizeWav(tone(1,48000,2),'/tiada/ffmpeg'),/gagal/);
});
test('synthesizeAll: ikut urutan, guna semula cache tanpa memanggil pemandu dan melaporkan setiap babak',async()=>{
 const calls=[];const driver={synthesize:async a=>{calls.push(a);return tone(1+calls.length*0.1);}};const settings={voice:'Ludo',style:'S'};
 const scenes=[{narration:'satu'},{narration:'dua'},{narration:'tiga'}];const cached=canonical(Buffer.alloc(48000));
 const seen=[];const pieces=await synthesizeAll({driver,scenes,settings,reuse:key=>key===pieceKey('dua',settings)?cached:null,onPiece:p=>seen.push([p.index,p.fresh])});
 assert.deepEqual(calls.map(c=>c.text),['satu','tiga']);assert.deepEqual(calls.map(c=>[c.voice,c.style]),[['Ludo','S'],['Ludo','S']]);assert.deepEqual(seen,[[0,true],[1,false],[2,true]]);assert.equal(pieces.length,3);
 assert.notEqual(pieceKey('satu',settings),pieceKey('satu',{voice:'Kore',style:'S'}));
});
test('synthesizeAll: klip 0.04 s ditolak; ralat pemandu menghentikan babak seterusnya; batal berfungsi',async()=>{
 const settings={voice:'Ludo',style:''};
 await assert.rejects(synthesizeAll({driver:{synthesize:async()=>tone(0.04)},scenes:[{narration:'a'}],settings}),/terlalu pendek/);
 await assert.rejects(synthesizeAll({driver:{synthesize:async()=>Buffer.from('bukan wav')},scenes:[{narration:'a'}],settings}),/Audio babak 1 tidak sah/);
 let n=0;await assert.rejects(synthesizeAll({driver:{synthesize:async()=>{if(++n===2)throw Error('Quota habis');return tone(1);}},scenes:[{narration:'a'},{narration:'b'},{narration:'c'}],settings}),/Quota habis/);assert.equal(n,2);
 const ac=new AbortController();let m=0;await assert.rejects(synthesizeAll({driver:{synthesize:async()=>{m++;ac.abort();return tone(1);}},scenes:[{narration:'a'},{narration:'b'}],settings,signal:ac.signal}),/CANCELLED/);assert.equal(m,1);
});
