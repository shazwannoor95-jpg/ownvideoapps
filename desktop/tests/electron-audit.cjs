const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {BrowserSession}=require('../ludo/browser-session.cjs');const {wavInfo}=require('../ludo/voiceover.cjs');const {page}=require('./fixture.cjs');
async function run({app,BrowserWindow,session,shell,live}){
 const out=path.resolve(process.env.OWNVIDEO_AUDIT_DIR||path.join(__dirname,'../../.cache/ludo-audit'));fs.mkdirSync(out,{recursive:true});
 let browser;const results=[];
 try{
  const ses=session.fromPartition('persist:ownvideo-ludo');
  const failedHosts=new Set();if(live)ses.webRequest.onErrorOccurred(details=>{try{failedHosts.add(new URL(details.url).hostname);}catch{}});
  if(live&&process.env.HTTPS_PROXY)await ses.setProxy({proxyRules:process.env.HTTPS_PROXY});
  if(!live){
   const ui=new BrowserWindow({show:false,webPreferences:{preload:path.join(__dirname,'../preload.cjs'),contextIsolation:true,nodeIntegration:false,sandbox:true}});
   await ui.loadFile(path.join(__dirname,'../index.html'));
   assert.equal(await ui.webContents.executeJavaScript('typeof window.ludo.choose'),'function');
   assert.equal(await ui.webContents.executeJavaScript('document.getElementById("generate").disabled'),true);
   assert.equal(await ui.webContents.executeJavaScript('typeof require'),'undefined');
   results.push('dashboard preload, disabled generation before project, Node isolation');
   ui.destroy();
  }
  let mode='ok';
  if(!live)ses.protocol.handle('https',request=>new Response(page(mode),{headers:{'content-type':'text/html; charset=utf-8'}}));
  browser=new BrowserSession({BrowserWindow,session,shell});await browser.speech();
  if(live){
   const wc=browser.window.webContents;
   // Inspect only the current UI; never enter credentials or trigger generation.
   await new Promise(r=>setTimeout(r,3000));
   const url=new URL(wc.getURL()),onLogin=url.hostname==='accounts.google.com';
   const ready=!onLogin&&url.hostname==='aistudio.google.com'?(await browser.speechDriver().ready()).ready:false;
   const report={kind:'live Google page audit',url:url.origin+url.pathname,status:onLogin?'LOGIN_REQUIRED':ready?'SPEECH_EDITOR_DETECTED':'PAGE_NOT_READY',ludo_selected:false,wav_generated:false,human_login_required:onLogin,shared_codex_viewer_attached:false,failed_background_hosts:[...failedHosts]};
   fs.writeFileSync(path.join(out,'google-live.png'),(await wc.capturePage()).toPNG());
   fs.writeFileSync(path.join(out,'google-live.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
  }else{
   const ready=await browser.prepareSpeech();assert.equal(ready.ready,true);results.push('speech editor readiness');
   assert.equal(await browser.window.webContents.executeJavaScript('typeof require'),'undefined');results.push('remote page Node isolation');
   const wav=await browser.synthesize({text:'satu dua tiga empat lima',voice:'Ludo',style:'Baca dengan tenang.'});assert.ok(wavInfo(wav).duration>=.5);results.push('Ludo selection, style, text, Run and complete WAV extraction');
   assert.equal(await browser.window.webContents.executeJavaScript('window.__voice'),'Ludo');
   for(const [next,pattern] of [['noludo',/Suara.*tidak ditemui/],['quota',/Quota exceeded/],['noeditor',/belum sedia/]]){
    mode=next;await browser.window.loadURL('https://aistudio.google.com/generate-speech');
    await assert.rejects(browser.synthesize({text:'Ini ujian',voice:'Ludo',style:''}),pattern);results.push('reject '+next);
   }
   const report={kind:'Electron fixture audit, no Google contacted',passed:results,ludo_live_generation:'NOT_RUN'};
   fs.writeFileSync(path.join(out,'fixture-audit.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify(report));
  }
  browser.dispose();app.exit(0);
 }catch(e){console.error('AUDIT_FAILED:',e.stack);browser?.dispose();app.exit(1);}
}
module.exports={run};
