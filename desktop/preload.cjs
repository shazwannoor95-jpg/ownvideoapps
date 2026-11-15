const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('ludo',{
 refresh:()=>ipcRenderer.invoke('ludo:refresh'),
 create:title=>ipcRenderer.invoke('ludo:create',{title}),save:scenes=>ipcRenderer.invoke('ludo:save',{scenes}),cues:(id,cues)=>ipcRenderer.invoke('ludo:cues',{id,cues}),audio:id=>ipcRenderer.invoke('ludo:audio',{id}),folder:()=>ipcRenderer.invoke('ludo:folder'),render:()=>ipcRenderer.invoke('ludo:render'),
 choose:()=>ipcRenderer.invoke('ludo:choose'),open:()=>ipcRenderer.invoke('ludo:open'),check:()=>ipcRenderer.invoke('ludo:check'),generate:()=>ipcRenderer.invoke('ludo:generate'),cancel:()=>ipcRenderer.invoke('ludo:cancel'),
 onProgress:fn=>ipcRenderer.on('ludo:progress',(_e,value)=>fn(value))
});
