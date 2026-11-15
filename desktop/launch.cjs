const {spawn}=require('node:child_process');
if(process.platform==='linux'&&!process.env.DISPLAY&&!process.env.WAYLAND_DISPLAY){
 console.error('Paparan desktop Linux tiada. Jalankan aplikasi pada PC/desktop yang boleh dilihat. Pemasangan ini tidak mewujudkan viewer Codex; jangan gunakan pelayar tanpa paparan untuk login pengguna.');process.exit(1);
}
const child=spawn(require('electron'),['.',...process.argv.slice(2)],{cwd:__dirname,stdio:'inherit'});
child.on('error',()=>{console.error('Electron gagal bermula; jalankan setup-ludo dahulu.');process.exitCode=1;});
child.on('exit',(code)=>{process.exitCode=code??1;});
