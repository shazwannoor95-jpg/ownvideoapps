const {test}=require('node:test'),assert=require('node:assert/strict');
const {BrowserSession,loadPage}=require('../ludo/browser-session.cjs');
test('stalled Google page stops and rejects within the configured deadline',async()=>{
 let stopped=false;
 await assert.rejects(loadPage({loadURL:()=>new Promise(()=>{}),webContents:{stop:()=>{stopped=true;}}},'https://aistudio.google.com/',15),/terlalu lama/);
 assert.equal(stopped,true);
});
test('opening speech preserves Google login redirect instead of navigating away',async()=>{
 const browser=Object.create(BrowserSession.prototype);let navigated=false;
 browser.open=async()=>{};browser.window={webContents:{getURL:()=> 'https://accounts.google.com/v3/signin'},loadURL:()=>{navigated=true;}};
 browser.probe=async()=>({connection:'LOGIN_REQUIRED'});
 assert.equal((await browser.speech()).connection,'LOGIN_REQUIRED');assert.equal(navigated,false);
});
