#!/usr/bin/env python3
"""Build Windows x64 ZIP on Windows or Linux; no Git, installer or host runtime."""
import argparse
import gzip
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
ASSETS={
 'electron-v45.3.1-win32-x64.zip':('https://github.com/electron/electron/releases/download/v45.3.1/electron-v45.3.1-win32-x64.zip','d92d1aa4700e3a7e7f174731f5086ebd9c21f9773e642b260160fe0a6ebe12d2'),
 'python.3.12.10.nupkg':('https://api.nuget.org/v3-flatcontainer/python/3.12.10/python.3.12.10.nupkg','0eb85c2dfccccf1b17352de4c397f69194035b7d37149eacc16f1147d93de3b8'),
 'ffmpeg-win32-x64.gz':('https://github.com/eugeneware/ffmpeg-static/releases/download/b6.1.1/ffmpeg-win32-x64.gz','8883a3dffbd0a16cf4ef95206ea05283f78908dbfb118f73c83f4951dcc06d77'),
 'ffprobe-win32-x64.gz':('https://github.com/eugeneware/ffmpeg-static/releases/download/b6.1.1/ffprobe-win32-x64.gz','f309e6223ad89d2fe54bccd420a7709b66fd27540674e92309578ed491a43c8d'),
 'ffmpeg-LICENSE':('https://raw.githubusercontent.com/eugeneware/ffmpeg-static/b6.1.1/LICENSE','3972dc9744f6499f0f9b2dbf76696f2ae7ad8af9b23dde66d6af86c9dfb36986'),
}
def digest(p):
 h=hashlib.sha256()
 with open(p,'rb') as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()

def fetch(cache,name,url,expected):
 target=cache/name
 if not target.exists():
  temp=target.with_name(name+'.partial')
  with urllib.request.urlopen(url,timeout=120) as r,open(temp,'wb') as f:shutil.copyfileobj(r,f)
  temp.replace(target)
 if digest(target)!=expected:raise ValueError('SHA256 mismatch: '+name)
 print('Verified:',name,flush=True)
 return target

def unpack(archive,dest,prefix=''):
 with zipfile.ZipFile(archive) as z:
  for item in z.infolist():
   if not item.filename.startswith(prefix):continue
   name=item.filename[len(prefix):]
   if not name:continue
   p=(dest/name).resolve()
   if not p.is_relative_to(dest.resolve()):raise ValueError('Unsafe archive path')
   if item.is_dir():p.mkdir(parents=True,exist_ok=True)
   else:
    p.parent.mkdir(parents=True,exist_ok=True)
    with z.open(item) as src,open(p,'wb') as out:shutil.copyfileobj(src,out)

def build(cache,out):
 cache.mkdir(parents=True,exist_ok=True);out.mkdir(parents=True,exist_ok=True)
 for name,(url,sha) in ASSETS.items():fetch(cache,name,url,sha)
 wheels=cache/'wheels';wheels.mkdir(exist_ok=True)
 subprocess.run([sys.executable,'-m','pip','download','--disable-pip-version-check','--no-cache-dir','--only-binary=:all:','--platform','win_amd64','--python-version','312','--implementation','cp','--abi','cp312','--dest',str(wheels),'-r',str(ROOT/'requirements-portable.txt')],check=True)
 # Validate all wheels against PyPI metadata before unpacking/copying any code.
 for wheel in sorted(wheels.glob('*.whl')):
  name,version=wheel.name.split('-')[:2]
  with urllib.request.urlopen(f'https://pypi.org/pypi/{name}/{version}/json',timeout=30) as r:metadata=json.load(r)
  record=next(x for x in metadata['urls'] if x['filename']==wheel.name)
  if digest(wheel)!=record['digests']['sha256']:raise ValueError('Wheel SHA256 mismatch: '+wheel.name)
 stage=out/'OwnVideoApps-Portable'
 if stage.exists():shutil.rmtree(stage)
 stage.mkdir()
 unpack(cache/'electron-v45.3.1-win32-x64.zip',stage)
 (stage/'electron.exe').rename(stage/'OwnVideoApps.exe')
 (stage/'resources/default_app.asar').unlink(missing_ok=True)
 app=stage/'resources/app';app.mkdir(parents=True,exist_ok=True)
 for name in ['main.cjs','preload.cjs','portable.cjs','index.html','ui.js','style.css']:
  shutil.copy2(ROOT/'desktop'/name,app/name)
 shutil.copytree(ROOT/'desktop/ludo',app/'ludo')
 (app/'package.json').write_text(json.dumps({'name':'ownvideoapps','version':'0.2.1','main':'main.cjs','private':True}),encoding='utf8')
 engine=stage/'resources/engine/tools';engine.mkdir(parents=True)
 for name in ['video.py','portable_source.py']:shutil.copy2(ROOT/'tools'/name,engine/name)
 shutil.copytree(ROOT/'tools/template',engine/'template',ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
 runtime=stage/'resources/runtime';python=runtime/'python';python.mkdir(parents=True)
 unpack(cache/'python.3.12.10.nupkg',python,'tools/')
 packages=python/'Lib/site-packages';packages.mkdir(parents=True,exist_ok=True)
 for wheel in sorted(wheels.glob('*.whl')):unpack(wheel,packages)
 binaries=runtime/'bin';binaries.mkdir()
 for name in ['ffmpeg','ffprobe']:
  with gzip.open(cache/(name+'-win32-x64.gz'),'rb') as src,open(binaries/(name+'.exe'),'wb') as dest:shutil.copyfileobj(src,dest)
 shutil.copy2(cache/'ffmpeg-LICENSE',stage/'FFMPEG-LICENSE.txt')
 shutil.copy2(ROOT/'docs/PORTABLE.md',stage/'MULA-DI-SINI.md')
 shutil.copy2(ROOT/'docs/THIRD-PARTY.md',stage/'THIRD-PARTY.md')
 shutil.copy2(ROOT/'tools/smoke_windows.ps1',stage/'Semak-Portable.ps1')
 data=stage/'Data';data.mkdir();(data/'videos').mkdir()
 manifest={str(p.relative_to(stage)).replace('\\','/'):digest(p) for p in sorted(stage.rglob('*')) if p.is_file()}
 (stage/'SHA256SUMS.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
 for p in [stage/'OwnVideoApps.exe',python/'python.exe',binaries/'ffmpeg.exe',binaries/'ffprobe.exe']:
  with open(p,'rb') as f:
   if f.read(2)!=b'MZ':raise ValueError('Not a Windows executable: '+str(p))
 zip_path=out/'OwnVideoApps-Windows-x64.zip'
 with zipfile.ZipFile(zip_path,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(stage.rglob('*')):
   if p.is_file():z.write(p,p.relative_to(out))
 (out/(zip_path.name+'.sha256')).write_text(digest(zip_path)+'  '+zip_path.name+'\n',encoding='utf8')
 print('BUILT:',zip_path,'bytes:',zip_path.stat().st_size,flush=True)
 return stage

if __name__=='__main__':
 ap=argparse.ArgumentParser(description=__doc__)
 ap.add_argument('--cache',type=Path,default=ROOT/'.cache/portable-build')
 ap.add_argument('--output',type=Path,default=ROOT/'dist')
 args=ap.parse_args();build(args.cache.resolve(),args.output.resolve())
