// Pemandu halaman Google AI Studio → Generate Speech.
// Semua interaksi melalui evaluate/insertText yang disuntik: dalam aplikasi ia webContents Electron, dalam ujian ia CDP ke Chrome.
// Kawalan dicari mengikut nama yang dilihat pengguna (Speech block text, Style, Speaker, Run, Download), bukan nombor elemen.
// STATUS: belum diuji pada halaman Google sebenar; nama kawalan datang daripada dokumen sesi terdahulu dan boleh berubah.
const {wavInfo,MIN_SECONDS}=require('./voiceover.cjs');

const norm=s=>String(s||'').replace(/\s+/g,' ').trim().toLowerCase();
const esc=s=>String(s).replace(/[.*+?^${}()|[\]\\]/g,'\\$&');
const TEXT_RE='speech block text|speech text|text to (speak|read)';

const HELPERS=String.raw`
const norm=s=>String(s||'').replace(/\s+/g,' ').trim().toLowerCase();
const shown=e=>!!(e.offsetWidth||e.offsetHeight||e.getClientRects().length);
const label=e=>{const p=[e.getAttribute('aria-label')];const by=e.getAttribute('aria-labelledby');if(by)by.split(/\s+/).forEach(i=>p.push(document.getElementById(i)?.textContent));if(e.labels)[...e.labels].forEach(l=>p.push(l.textContent));p.push(e.getAttribute('placeholder'),e.getAttribute('title'));const j=norm(p.filter(Boolean).join(' '));return j||norm(e.innerText||e.textContent);};
const find=(sel,re)=>[...document.querySelectorAll(sel)].filter(e=>shown(e)&&re.test(label(e)));
const off=e=>e.disabled||e.getAttribute('aria-disabled')==='true';
const FIELD='textarea,input[type=text],[contenteditable="true"],[role=textbox]';
const BUTTON='button,[role=button]';
const CONTROL='button,[role=button],[role=combobox],select';
const sleep=ms=>new Promise(r=>setTimeout(r,ms));
`;
const code=body=>`(async()=>{${HELPERS}${body}})()`;

const INSPECT=code(String.raw`
 return {text:find(FIELD,/${TEXT_RE}/).length,style:find(FIELD,/style/).length,run:find(BUTTON,/^run\b|^generate\b/).length,speaker:find(CONTROL,/speaker|voice|suara/).length,url:location.href};`);

const selectVoiceCode=voice=>code(String.raw`
 const start=new RegExp(${JSON.stringify('^'+esc(norm(voice))+'(?![\\p{L}\\p{N}])')},'u');
 const has=new RegExp(${JSON.stringify('(?<![\\p{L}\\p{N}])'+esc(norm(voice))+'(?![\\p{L}\\p{N}])')},'u');
 const controls=find(CONTROL,/speaker|voice|suara/);
 if(!controls.length)return {selected:false,reason:'tiada-kawalan',options:[]};
 const c=controls[0];
 if(has.test(label(c))||has.test(norm(c.value||''))||has.test(norm(c.textContent)))return {selected:true,already:true};
 if(c.tagName==='SELECT'){const o=[...c.options].find(x=>start.test(norm(x.textContent)));if(!o)return {selected:false,reason:'tiada-pilihan',options:[...c.options].map(x=>x.textContent.trim()).slice(0,12)};c.value=o.value;c.dispatchEvent(new Event('input',{bubbles:true}));c.dispatchEvent(new Event('change',{bubbles:true}));return {selected:has.test(norm(c.options[c.selectedIndex]?.textContent||''))};}
 c.click();await sleep(400);
 const options=[...document.querySelectorAll('[role=option],mat-option,[role=menuitem],[role=menuitemradio],li')].filter(shown);
 const hit=options.find(o=>start.test(norm(o.textContent)));
 if(!hit){document.body.click();return {selected:false,reason:'tiada-pilihan',options:options.map(o=>o.textContent.trim().replace(/\s+/g,' ').slice(0,40)).slice(0,12)};}
 hit.click();await sleep(300);
 const selected=find(CONTROL,/speaker|voice|suara/).some(e=>has.test(label(e))||has.test(norm(e.value||''))||has.test(norm(e.textContent)));
 return {selected,reason:selected?'':'label-suara-tidak-disahkan'};`);

const focusCode=kind=>code(String.raw`
 const els=find(FIELD,${kind==='text'?`/${TEXT_RE}/`:'/style/'});
 if(els.length!==1)return {ok:false,count:els.length};
 const e=els[0];e.scrollIntoView({block:'center'});e.focus();
 if(typeof e.select==='function')e.select();else{const r=document.createRange();r.selectNodeContents(e);const s=getSelection();s.removeAllRanges();s.addRange(r);}
 return {ok:document.activeElement===e||e.contains(document.activeElement),count:1};`);

const readCode=kind=>code(String.raw`
 const e=find(FIELD,${kind==='text'?`/${TEXT_RE}/`:'/style/'})[0];
 return e?String(e.value!==undefined?e.value:e.innerText):null;`);

const CLICK_RUN=code(String.raw`
 const b=find(BUTTON,/^run\b|^generate\b/);
 if(b.length!==1)return {clicked:false,reason:b.length?'lebih-satu-butang':'tiada-butang'};
 if(off(b[0]))return {clicked:false,reason:'butang-dinyahdayakan'};
 b[0].click();return {clicked:true};`);

const CLICK_DOWNLOAD=code(String.raw`
 const b=find(BUTTON+',a[download]',/download/).filter(e=>!off(e));
 if(!b.length)return {clicked:false};
 b[0].click();return {clicked:true};`);

const STATUS=code(String.raw`
 const a=document.querySelector('audio');const s=a?(a.currentSrc||a.src||''):'';
 const errs=[...document.querySelectorAll('[role=alert],[role=status],.error,mat-error,snack-bar-container,.mat-mdc-snack-bar-container,[class*=snack]')].filter(shown).map(e=>(e.innerText||'').replace(/\s+/g,' ').trim()).filter(t=>/quota|rate.?limit|exceeded|too many requests|resource.?exhausted|try again later|something went wrong|permission denied|unavailable|failed/i.test(t));
 return {running:find(BUTTON,/^stop\b/).length>0,download:find(BUTTON+',a[download]',/download/).some(e=>!off(e)),hasAudio:!!a,src:s.length+':'+s.slice(-48),error:errs[0]?errs[0].slice(0,200):''};`);

// Seek ke 0 dan main supaya pemain memuatkan WAV penuh (klip pertama pernah dilaporkan 0.04 s sahaja), kemudian baca src.
const FETCH_AUDIO=code(String.raw`
 const a=document.querySelector('audio');if(!a)return {ok:false,reason:'tiada-pemain-audio'};
 a.pause();a.currentTime=0;try{await a.play();}catch(e){}
 for(let i=0;i<50&&!(a.duration>0.5);i++)await sleep(200);
 await sleep(300);
 const src=a.currentSrc||a.src;if(!src)return {ok:false,reason:'pemain-tiada-src'};
 const out=b64=>b64.length>70000000?{ok:false,reason:'terlalu-besar'}:{ok:true,base64:b64,pageDuration:a.duration};
 if(src.startsWith('data:')){const i=src.indexOf('base64,');if(i<0)return {ok:false,reason:'data-url-bukan-base64'};return out(src.slice(i+7));}
 const r=await fetch(src);if(!r.ok)return {ok:false,reason:'fetch-'+r.status};
 const bytes=new Uint8Array(await r.arrayBuffer());let bin='';for(let i=0;i<bytes.length;i+=0x8000)bin+=String.fromCharCode.apply(null,bytes.subarray(i,i+0x8000));
 return out(btoa(bin));`);

class SpeechDriver{
 constructor({evaluate,insertText,sleep=ms=>new Promise(r=>setTimeout(r,ms)),downloads=null,pollMs=750,timeoutMs=180000,startMs=20000}){Object.assign(this,{evaluate,insertText,sleep,downloads,pollMs,timeoutMs,startMs});}
 inspect(){return this.evaluate(INSPECT);}
 async ready(){const i=await this.inspect();return {ready:i.text===1&&i.run===1,...i};}
 async setField(kind,value){
  const f=await this.evaluate(focusCode(kind));
  if(!f.ok){if(kind==='style'&&f.count===0)return false;throw Error(f.count===1?'Medan '+kind+' gagal difokuskan.':'Medan '+(kind==='text'?'Speech block text':'Style')+' '+(f.count?'lebih daripada satu dikesan':'tidak dikesan')+'; buka satu blok pertuturan sahaja.');}
  await this.insertText(value);
  const back=await this.evaluate(readCode(kind));
  if(norm(back)!==norm(value))throw Error('Teks tidak masuk dengan betul ke medan '+(kind==='text'?'Speech block text':'Style')+'. Tiada Run ditekan.');
  return true;
 }
 async synthesize({text,voice,style,signal}){
  const abort=()=>{if(signal?.aborted)throw Error('CANCELLED');};
  if(typeof text!=='string'||!text.trim()||text.length>5000)throw Error('Teks narasi mesti 1–5000 aksara.');
  abort();
  const ins=await this.inspect();
  if(ins.text!==1||ins.run!==1)throw Error('Halaman Generate Speech belum sedia: ruang "Speech block text" atau butang Run tidak dikesan. Buka halaman itu (satu blok teks) dan cuba lagi.');
  const sel=await this.evaluate(selectVoiceCode(voice));
  if(!sel.selected)throw Error('Suara "'+voice+'" tidak ditemui dalam AI Studio'+(sel.options?.length?' (tersedia: '+sel.options.join(', ')+')':'')+'. Tiada suara lain digunakan secara senyap; tukar suara dalam tetapan atau import WAV sendiri.');
  abort();
  if(style)await this.setField('style',style);
  await this.setField('text',text);
  abort();
  const before=await this.evaluate(STATUS);
  const clicked=await this.evaluate(CLICK_RUN);
  if(!clicked.clicked)throw Error('Butang Run tidak boleh ditekan ('+(clicked.reason||'sebab tidak diketahui')+').');
  const t0=Date.now();let sawRunning=false;
  for(;;){
   abort();await this.sleep(this.pollMs);abort();
   const s=await this.evaluate(STATUS);
   if(s.error)throw Error('AI Studio melaporkan: '+s.error+'. Percubaan dihentikan; semak kuota atau cuba lagi kemudian.');
   if(s.running)sawRunning=true;
   const changed=s.src!==before.src;
   if(!s.running&&s.download&&(sawRunning||changed))break;
   if(!sawRunning&&!changed&&Date.now()-t0>this.startMs)throw Error('Run tidak kelihatan bermula. Semak halaman AI Studio.');
   if(Date.now()-t0>this.timeoutMs)throw Error('Masa tamat menunggu audio siap.');
  }
  abort();
  const got=await this.evaluate(FETCH_AUDIO,true);
  let why=got.reason||'';
  if(got.ok){
   try{
    const buf=Buffer.from(got.base64,'base64'),info=wavInfo(buf);
    if(Number.isFinite(got.pageDuration)&&Math.abs(info.duration-got.pageDuration)>1)throw Error('tempoh WAV '+info.duration.toFixed(2)+' s tidak sepadan pemain '+got.pageDuration.toFixed(2)+' s');
    if(info.duration<MIN_SECONDS)throw Error('klip hanya '+info.duration.toFixed(2)+' s (belum lengkap)');
    return buf;
   }catch(error){why=error.message;}
  }
  if(this.downloads){
   const count=this.downloads.count();const c=await this.evaluate(CLICK_DOWNLOAD);
   if(c.clicked){const buf=await this.downloads.takeNew(count,20000);if(buf){wavInfo(buf);return buf;}why+=' · muat turun tidak diterima';}
  }
  throw Error('Audio tidak dapat diambil secara automatik ('+why+'). Tekan Download dalam tetingkap AI Studio lalu import WAV, atau cuba semula.');
 }
}
module.exports={SpeechDriver,TEXT_RE};
