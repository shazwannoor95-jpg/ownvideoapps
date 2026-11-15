const page=(mode='ok')=>mode==='noeditor'?'<body><h1>Sila login</h1></body>':`<!doctype html><meta charset=utf-8><body>
<button id=spk aria-label="Speaker">Puck</button><ul id=list role=listbox hidden></ul>
<textarea aria-label="Speech block text"></textarea><textarea aria-label="Style instructions"></textarea>
<button id=run aria-label="Run">Run</button><button id=stop aria-label="Stop" hidden>Stop</button><button id=dl aria-label="Download" disabled>Download</button>
<audio id=a controls></audio><div id=err role=alert hidden></div>
<script>
const VOICES=${JSON.stringify(mode==='noludo'?['Puck','Kore']:['Puck','Ludo','Kore'])};
const wav=s=>{const n=Math.round(24000*s),b=new ArrayBuffer(44+n*2),v=new DataView(b),w=(o,t)=>[...t].forEach((c,i)=>v.setUint8(o+i,c.charCodeAt(0)));w(0,'RIFF');v.setUint32(4,36+n*2,true);w(8,'WAVEfmt ');v.setUint32(16,16,true);v.setUint16(20,1,true);v.setUint16(22,1,true);v.setUint32(24,24000,true);v.setUint32(28,48000,true);v.setUint16(32,2,true);v.setUint16(34,16,true);w(36,'data');v.setUint32(40,n*2,true);for(let i=0;i<n;i++)v.setInt16(44+i*2,Math.round(Math.sin(i/20)*8000),true);let s2='';const u=new Uint8Array(b);for(let i=0;i<u.length;i+=4096)s2+=String.fromCharCode.apply(null,u.subarray(i,i+4096));return 'data:audio/wav;base64,'+btoa(s2);};
spk.onclick=()=>{list.hidden=false;list.innerHTML='';VOICES.forEach(n=>{const li=document.createElement('li');li.setAttribute('role','option');li.textContent=n;li.onclick=()=>{spk.textContent=n;list.hidden=true;};list.appendChild(li);});};
let full=null,swapped=false;
run.onclick=()=>{
 if('${mode}'==='quota'){err.hidden=false;err.textContent='Quota exceeded for this model. Try again later.';return;}
 const words=document.querySelector('[aria-label="Speech block text"]').value.trim().split(/\\s+/).length;full=wav(Math.max(1,words*0.4));swapped=false;
 dl.disabled=true;stop.hidden=false;run.disabled=true;
 setTimeout(()=>{stop.hidden=true;run.disabled=false;dl.disabled=false;a.src=wav(0.04);window.__voice=spk.textContent;},250);
};
a.addEventListener('play',()=>{if(!swapped&&full){swapped=true;a.src=full;a.play().catch(()=>{});}});
</script></body>`;

module.exports={page};
