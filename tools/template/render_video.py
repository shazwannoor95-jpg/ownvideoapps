"""Deterministic, scene-based UiTM corporate motion graphics, 1280x720/30fps.

Actual timing comes from storyboard.duration, supplied after narration alignment.
Preview timing is estimated and is never silently used for production rendering.
"""
from __future__ import annotations
import argparse, hashlib, json, math, subprocess
from pathlib import Path
from functools import lru_cache
from concurrent.futures import ProcessPoolExecutor
from PIL import Image, ImageDraw, ImageFont

ROOT=Path(__file__).resolve().parent
W,H,FPS=1280,720,30
BLUE='#042E6F'; PURPLE='#92278F'; GOLD='#FEBE10'; WHITE='#FFFFFF'
INK=BLUE; LIGHT='#F3F6FC'; LINE='#DCE4F0'; MUTED='#526885'; PALE='#E8D7EC'
FONT=ROOT/'local_resources/Outfit[wght].ttf'
AUDIT=None

def story(): return json.loads((ROOT/'storyboard.json').read_text(encoding='utf-8-sig'))
def clamp(x):return max(0,min(1,x))
def ease(x):return 1-(1-clamp(x))**3
def phase(t,start=.0,span=.65):return ease((t-start)/span)
def cue(t,d,f):return phase(t,min(d-1.0,max(.8,d*f)))
def duration(s):return float(s.get('duration',max(12,len(s['narration'].split())/2.25+1)))

@lru_cache(maxsize=180)
def font(size,weight=500):
    f=ImageFont.truetype(str(FONT),int(size))
    try:f.set_variation_by_axes([float(weight)])
    except (OSError,AttributeError):pass
    return f

def width(text,size,weight=500):return font(size,weight).getlength(text)
def wrap(text,size,maxw,weight=500):
    lines=[]
    for para in str(text).split('\n'):
        line=''
        for word in para.split():
            candidate=(line+' '+word).strip()
            if line and width(candidate,size,weight)>maxw:
                lines.append(line);line=word
            else:line=candidate
        lines.append(line)
    return lines

def fit(text,size,maxw,maxh,weight=500,minsize=22,gap=1.18):
    for v in range(size,minsize-1,-1):
        if len(wrap(text,v,maxw,weight))*v*gap<=maxh:return v
    raise ValueError(f'Text does not fit: {text!r} in {maxw}x{maxh}')

@lru_cache(maxsize=1000)
def text_image(text,size,maxw,color,weight,align):
    lines=wrap(text,size,maxw,weight); lh=math.ceil(size*1.18)
    layer=Image.new('RGBA',(int(maxw),max(1,lh*len(lines)+8)))
    draw=ImageDraw.Draw(layer)
    for i,line in enumerate(lines):
        x=(maxw-width(line,size,weight))/2 if align=='center' else 0
        draw.text((x,lh*i),line,font=font(size,weight),fill=color,anchor='lt')
    return layer

def paste(im,layer,xy,alpha=1):
    if alpha<=0:return
    if alpha<.999:
        layer=layer.copy();layer.putalpha(layer.getchannel('A').point(lambda a:int(a*alpha)))
    im.alpha_composite(layer,(round(xy[0]),round(xy[1])))

def txt(im,text,x,y,size=30,maxw=1100,color=INK,weight=500,align='left',alpha=1,maxh=None):
    if maxh is not None:size=fit(text,size,maxw,maxh,weight)
    layer=text_image(str(text),size,int(maxw),color,weight,align)
    paste(im,layer,(x,y),alpha)
    if AUDIT is not None and alpha>.9:
        AUDIT.append({'text':str(text),'bounds':[x,y,x+layer.width,y+layer.height],
                      'font':size,'within_canvas':x>=0 and y>=0 and x+layer.width<=W and y+layer.height<=H})
    return layer.height

def enter_text(im,text,x,y,t,start=.0,**kw):
    a=phase(t,start);return txt(im,text,x,y+(1-a)*18,alpha=a,**kw)

def rounded(im,rect,fill=WHITE,outline=None,r=18,width=2):
    ImageDraw.Draw(im).rounded_rectangle(tuple(round(v) for v in rect),radius=r,fill=fill,outline=outline,width=width)

def panel(w,h,fill=WHITE):
    im=Image.new('RGBA',(w,h));rounded(im,(0,0,w-1,h-1),fill=fill,outline=LINE)
    return im

@lru_cache(maxsize=20)
def icon(sid,size):return Image.open(ROOT/f'assets/icons/{sid}.png').convert('RGBA').resize((size,size),Image.Resampling.LANCZOS)
@lru_cache(maxsize=4)
def logo(w=182):
    im=Image.open(ROOT/'assets/brand/LogoUiTM.png').convert('RGBA')
    return im.resize((w,round(w*im.height/im.width)),Image.Resampling.LANCZOS)

def icon_in(im,sid,x,y,size,t,start=.3):
    a=phase(t,start)
    paste(im,icon(sid,size),(x,y+(1-a)*25),a)

def check(im,x,y,amount=1,color=PURPLE):
    draw=ImageDraw.Draw(im);pts=[(x,y+9),(x+7,y+16),(x+21,y)]
    if amount<.5:draw.line([pts[0],(x+7*amount*2,y+9+7*amount*2)],fill=color,width=4)
    else:draw.line(pts[:2]+[(x+7+14*(amount-.5)*2,y+16-16*(amount-.5)*2)],fill=color,width=4)

def arrow(im,start,end,a=1,color=PURPLE):
    if a<=0:return
    sx,sy=start;ex,ey=end;tx=sx+(ex-sx)*a;ty=sy+(ey-sy)*a
    d=ImageDraw.Draw(im);d.line((sx,sy,tx,ty),fill=color,width=4)
    if a>.95:
        angle=math.atan2(ey-sy,ex-sx)
        d.polygon([(ex,ey),(ex-12*math.cos(angle-.5),ey-12*math.sin(angle-.5)),(ex-12*math.cos(angle+.5),ey-12*math.sin(angle+.5))],fill=color)

def footnote(s):
    return 'Sumber: teks dibekalkan pengguna • BARU / UiTM | Narasi sintetik BM'

def base(s,i,n,t,d,dark=False):
    im=Image.new('RGBA',(W,H),BLUE if dark else LIGHT);draw=ImageDraw.Draw(im)
    # Original diagonal brand ribbon remains subordinate to foreground information.
    if dark:
        draw.polygon([(980,0),(1280,0),(1280,720),(1150,720)],fill='#123E7B')
        draw.polygon([(1175,0),(1280,0),(1280,720),(1260,720)],fill=PURPLE)
    else:
        draw.polygon([(1130,0),(1280,0),(1280,720),(1210,720)],fill='#EBE0F0')
    rounded(im,(1038,22,1230,108),WHITE,outline=None,r=10)
    paste(im,logo(),(1043,26))
    txt(im,s.get('eyebrow',''),58,39,size=17,maxw=920,color=GOLD if dark else PURPLE,weight=650)
    if True:
        enter_text(im,s['title'],58,88,t,size=42,maxw=930,maxh=108,color=WHITE if dark else BLUE,weight=650)
    draw.line((58,663,1222,663),fill='#59749B' if dark else '#C9D7E8',width=1)
    end=58+1164*clamp(t/d)
    draw.line((58,663,end,663),fill=GOLD if dark else PURPLE,width=3)
    txt(im,footnote(s),58,681,size=15,maxw=1030,color='#CDDAEF' if dark else MUTED)
    txt(im,f'{i+1:02d} / {n:02d}',1156,681,size=15,maxw=65,color=WHITE if dark else BLUE,align='center')
    return im

def bullet_cards(im,s,t,d,*,x=440,y=225,w=780,h=82,spacing=14,color=BLUE):
    bullets=s['bullets']; count=len(bullets)
    if count>4:h=68;spacing=10
    for j,label in enumerate(bullets):
        a=cue(t,d,.08+j*.15);yy=y+j*(h+spacing)
        card=panel(w,h);dd=ImageDraw.Draw(card)
        dd.rounded_rectangle((18,19,50,51),radius=9,fill=PALE)
        txt(card,f'{j+1:02d}',19,26,size=17,maxw=30,align='center',color=PURPLE,weight=650)
        fs=fit(label,29,w-91,h-20,600,minsize=22)
        lines=wrap(label,fs,w-91,600);height=len(lines)*fs*1.18
        txt(card,label,68,(h-height)/2,size=fs,maxw=w-91,color=color,weight=550)
        paste(im,card,(x+(1-a)*26,yy),a)

def intro(im,s,t,d):
    enter_text(im,'Pelantikan\nPegawai Pengelas',60,154,t,.15,size=53,maxw=780,color=WHITE,weight=650)
    enter_text(im,'dan Pemberian Kuasa\nPegawai Pengelas Semula',60,298,t,.5,size=40,maxw=790,color=WHITE,weight=500)
    a=phase(t,.4);ImageDraw.Draw(im).rectangle((60,129,60+180*a,135),fill=GOLD)
    icon_in(im,'SV0341',870,185,310,t,.6)
    for j,(num,desc) in enumerate([('2B','Pelantikan'),('2C','Pengelasan semula')]):
        a=cue(t,d,.23+j*.2); x=60+j*390
        card=panel(360,92);txt(card,num,20,20,size=40,maxw=90,weight=700,color=PURPLE)
        txt(card,desc,118,30,size=25,maxw=230,weight=600)
        paste(im,card,(x,513+(1-a)*20),a)

def comparison(im,s,t,d):
    if s['id']=='s02':
        items=[('PEGAWAI PENGELAS','Mengelaskan perkara rasmi','Rahsia Besar\nRahsia\nSulit\nTerhad'),
               ('PEGAWAI PENGELAS SEMULA','Mengelaskan semula','Terhenti menjadi\nrahsia rasmi')]
        for j,(eyebrow,headline,body) in enumerate(items):
            a=cue(t,d,.06+j*.25);x=58+j*594;card=panel(570,355)
            rounded(card,(0,0,569,66),BLUE if j==0 else PURPLE,r=18)
            txt(card,eyebrow,24,24,size=21,maxw=522,color=WHITE,weight=650)
            txt(card,headline,24,94,size=29,maxw=522,weight=600)
            if j==0:
                for k,level in enumerate(body.split('\n')):
                    aa=cue(t,d,.13+k*.065)
                    rounded(card,(24,147+k*44,546,184+k*44),fill='#EDF2F9',r=8)
                    txt(card,level,42,157+k*44,size=23,maxw=490,alpha=aa,color=BLUE,weight=600)
            else:
                paste(card,icon('SV0341',130),(220,146))
                txt(card,body,30,276,size=27,maxw=510,color=PURPLE,weight=600,align='center')
            paste(im,card,(x,217+(1-a)*20),a)
        txt(im,s.get('footnote','Pengelasan semula meliputi suratan dalam Jadual kepada Akta 88 atau perkara rasmi yang telah dikelaskan.'),66,592,size=22,maxw=1148,color=MUTED,align='center',alpha=cue(t,d,.7))
    else:
        txt(im,s['bullets'][0],60,208,size=25,maxw=1160,weight=550)
        entries=[('5','Menteri','Warta Kerajaan\nPersekutuan'),('9','Menteri Besar / Ketua Menteri /\nPremier Sarawak','Warta Kerajaan\nNegeri')]
        for j,(sec,authority,outcome) in enumerate(entries):
            a=cue(t,d,.12+j*.26);x=58+594*j;card=panel(570,343)
            txt(card,'SEKSYEN',26,24,size=19,maxw=190,color=PURPLE,weight=650)
            txt(card,sec,24,57,size=83,maxw=150,color=PURPLE,weight=700)
            txt(card,authority,174,40,size=28,maxw=370,maxh=130,weight=600)
            arrow(card,(45,186),(523,186),a=cue(t,d,.28+j*.2),color=GOLD)
            txt(card,outcome,26,226,size=32,maxw=518,align='center',weight=600)
            paste(im,card,(x,268+(1-a)*20),a)

def authority(im,s,t,d):
    sec='2B' if s['id']=='s03' else '2C'
    a=phase(t,.3);card=panel(300,360)
    txt(card,'SEKSYEN',25,35,size=24,maxw=250,align='center',weight=600,color=PURPLE)
    txt(card,sec,25,101,size=115,maxw=250,align='center',weight=750,color=BLUE)
    txt(card,'Akta Rahsia Rasmi\n1972 [Akta 88]',25,260,size=27,maxw=250,align='center',weight=550)
    paste(im,card,(60-(1-a)*22,235),a)
    if s['id']=='s03':
        labels=['Pelantikan yang sah','Menteri Pendidikan Tinggi','Konteks Universiti Teknologi MARA']
        bullet_cards(im,{'bullets':labels},t,d,x=422,y=250,w=798,h=94,spacing=20)
    else:
        labels=['Menteri • Menteri Besar • Ketua Menteri','Premier Sarawak • Ketua Jabatan','Kuasa langsung: Tidak perlu pelantikan baharu']
        bullet_cards(im,{'bullets':labels},t,d,x=422,y=250,w=798,h=94,spacing=20)

def roles(im,s,t,d):
    if s['id']=='s12':
        labels=[('UiTM SHAH ALAM','Naib Canselor'),('UiTM CAWANGAN','Rektor')]
        for j,(location,role) in enumerate(labels):
            a=cue(t,d,.10+j*.25);x=58+j*594;card=panel(570,280)
            rounded(card,(0,0,569,12),PURPLE if j else BLUE,r=6)
            txt(card,location,24,42,size=24,maxw=522,color=PURPLE,weight=650)
            person(card,70,120,1.0)
            txt(card,role,170,139,size=38,maxw=370,weight=650)
            paste(im,card,(x,252+(1-a)*20),a)
        txt(im,'Berdasarkan peranan Ketua Agensi',60,578,size=30,maxw=1160,align='center',weight=550,alpha=cue(t,d,.64))
    else:
        for j,label in enumerate(s['bullets']):
            a=cue(t,d,.08+j*.16);x=58+(j%2)*594;y=226+(j//2)*196;card=panel(570,170)
            person(card,30,43,.75)
            txt(card,label,132,49,size=31,maxw=410,maxh=100,weight=600)
            paste(im,card,(x,y+(1-a)*22),a)
        txt(im,'Cadangan Ketua Jabatan → Pelantikan yang sah',58,625,size=22,maxw=1164,align='center',color=MUTED,alpha=cue(t,d,.73))

def person(im,x,y,scale=1):
    d=ImageDraw.Draw(im);r=25*scale
    d.ellipse((x+32*scale-r,y,x+32*scale+r,y+2*r),fill=PALE,outline=BLUE,width=3)
    d.rounded_rectangle((x,y+57*scale,x+64*scale,y+119*scale),radius=int(20*scale),fill='#CBD9F0',outline=BLUE,width=3)
    d.line((x+32*scale,y+63*scale,x+32*scale,y+99*scale),fill=PURPLE,width=5)

def flow(im,s,t,d):
    for j,label in enumerate(s['bullets']):
        a=cue(t,d,.08+j*.18);x=58+j*297;card=panel(273,318)
        rounded(card,(20,22,74,76),PURPLE,r=14)
        txt(card,str(j+1),22,35,size=30,maxw=50,align='center',color=WHITE,weight=650)
        if j<3:arrow(im,(x+276,398),(x+293,398),cue(t,d,.20+j*.18),color=PURPLE)
        sid=['SV0104','SV0108','SV1101','SV0102'][j]
        paste(card,icon(sid,104),(150,22))
        fs=fit(label,29,225,185,600,minsize=23)
        txt(card,label,24,125,size=fs,maxw=225,weight=600)
        paste(im,card,(x,252+(1-a)*20),a)
    txt(im,'Lengkapkan setiap peringkat mengikut kuasa yang berkenaan.',58,608,size=25,maxw=1164,align='center',color=MUTED,alpha=cue(t,d,.78))

def timeline(im,s,t,d):
    icon_in(im,'SV0105',55,258,285,t,.3)
    bullet_cards(im,s,t,d,x=382,y=220,w=840,h=84,spacing=16)

def deadline(im,s,t,d):
    is_first=s['id']=='s07'; form='KPKK 9' if is_first else 'KPKK 9A'
    card=panel(545,380)
    txt(card,form,28,30,size=54,maxw=489,weight=700,color=PURPLE)
    txt(card,'Borang Maklumat\nPegawai Pengelas'+('' if is_first else ' Semula'),28,107,size=29,maxw=489,weight=550)
    txt(card,'+ Salinan sijil perakuan' if is_first else '+ Salinan Warta Kerajaan\nbagi pegawai yang diwakilkan',28,223,size=29,maxw=489,maxh=100,weight=600)
    txt(card,'Kemukakan kepada CGSO',28,329,size=25,maxw=489,weight=600,color=PURPLE)
    a=phase(t,.4);paste(im,card,(58,230+(1-a)*20),a)
    aa=cue(t,d,.33);draw=ImageDraw.Draw(im)
    draw.arc((785,220,1115,550),-90,-90+360*aa,fill=GOLD,width=14)
    txt(im,'30',780,287,size=112,maxw=340,align='center',weight=700,color=BLUE,alpha=aa)
    txt(im,'HARI BEKERJA',758,419,size=31,maxw=384,align='center',weight=650,color=PURPLE,alpha=aa)
    if is_first:txt(im,'Dari tarikh sijil diterima',690,577,size=29,maxw=520,align='center',weight=600,alpha=cue(t,d,.70))
    else:
        txt(im,'Tempoh pengemukaan maklumat',669,577,size=26,maxw=556,align='center',weight=550,alpha=cue(t,d,.70))
        txt(im,s.get('footnote',''),60,630,size=19,maxw=1160,align='center',color=MUTED,alpha=cue(t,d,.78))

def checklist(im,s,t,d):
    icon_in(im,'SV0341',57,264,290,t,.3)
    bullet_cards(im,s,t,d,x=397,y=255,w=823,h=94,spacing=22)

def folder(im,s,t,d):
    icon_in(im,'SV0102',54,257,314,t,.3)
    a=cue(t,d,.54);rounded(im,(100,521,323,582),fill=PURPLE,r=8)
    txt(im,'SULIT',111,536,size=31,maxw=200,color=WHITE,align='center',weight=700,alpha=a)
    bullet_cards(im,s,t,d,x=416,y=219,w=804,h=83,spacing=17)

def cancel(im,s,t,d):
    icon_in(im,'SV0108',62,252,290,t,.25)
    bullet_cards(im,s,t,d,x=410,y=222,w=810,h=86,spacing=16)
    if s['id']=='s17':txt(im,'Kemas kini maklumat dan urusan kuasa yang berkaitan.',59,613,size=24,maxw=1162,align='center',color=MUTED,alpha=cue(t,d,.77))

def delegation(im,s,t,d):
    a=phase(t,.3);card=panel(310,336)
    person(card,115,36,1.1)
    txt(card,'Pewakilan\nkuasa yang sah',20,210,size=32,maxw=270,align='center',weight=600)
    paste(im,card,(60,253+(1-a)*22),a)
    bullet_cards(im,s,t,d,x=425,y=250,w=795,h=98,spacing=21)

def summary(im,s,t,d):
    for j,label in enumerate(s['bullets']):
        a=cue(t,d,.08+j*.17);x=58+(j%2)*594;y=229+(j//2)*177;card=panel(570,150)
        rounded(card,(20,26,66,72),PURPLE,r=10)
        txt(card,f'{j+1:02d}',23,39,size=24,maxw=40,align='center',color=WHITE,weight=650)
        txt(card,label,88,36,size=30,maxw=454,maxh=104,weight=600)
        paste(im,card,(x,y+(1-a)*20),a)
    txt(im,'Borang lengkap • Kuasa sah • Maklumat dikemas kini',60,610,size=28,maxw=1160,align='center',color=WHITE,alpha=cue(t,d,.78))

LAYOUTS={'intro':intro,'compare':comparison,'authority':authority,'roles':roles,'flow':flow,'timeline':timeline,
         'deadline':deadline,'checklist':checklist,'folder':folder,'cancel':cancel,'delegation':delegation,'summary':summary}

def render_frame(scene,index,count,t):
    d=duration(scene)
    im=base(scene,index,count,t,d,False)
    # Left column identifies each role; right column animates the source text.
    rid=scene.get('role',0)
    badge=panel(240,340)
    txt(badge,f'{rid:02d}' if rid else 'UiTM',22,35,size=68,maxw=196,color=PURPLE,weight=700,align='center')
    iconid=['SV0341','SV0341','SV0102','SV0104','SV0104','SV0105','SV0105'][rid]
    paste(badge,icon(iconid,122),(59,138))
    txt(badge,'TUGAS & PROSEDUR',15,288,size=17,maxw=210,align='center',weight=650)
    paste(im,badge,(58,235))
    items=scene['bullets'];n=len(items);h=min(126,int(370/max(n,1))-12)
    for j,label in enumerate(items):
        a=phase(t,.45+j*.5);card=panel(895,h)
        fs=fit(label,30,819,h-24,550,minsize=18)
        height=len(wrap(label,fs,819,550))*fs*1.18
        txt(card,label,26,(h-height)/2,size=fs,maxw=819,color=BLUE,weight=550)
        paste(im,card,(326+(1-a)*25,222+j*(h+14)),a)
    if any('belum' in x.lower() for x in items):
        txt(im,'CATATAN SUMBER: ALIRAN KHUSUS BELUM DISAHKAN',326,625,size=18,maxw=895,color=PURPLE,weight=650)
    return im.convert('RGB')

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def render_scene(args):
    scene,index,count=args
    if 'duration' not in scene:raise ValueError(f"Actual narration duration missing: {scene['id']}")
    n=round(scene['duration']*FPS);out=ROOT/'rendered'/f"{scene['id']}.mp4";out.parent.mkdir(exist_ok=True)
    from produce import visual_signature
    signature=visual_signature(scene,index,count)
    proof_path=out.with_suffix('.render.json')
    if out.is_file() and proof_path.is_file():
        cached=json.loads(proof_path.read_text(encoding='utf-8-sig'))
        if (cached.get('visual_signature')==signature and cached.get('duration_frames')==n
                and cached.get('output_sha256')==sha(out)):
            print(f"Reused {scene['id']}: {n} verified frames",flush=True)
            return cached
    cmd=['ffmpeg','-y','-v','error','-f','rawvideo','-vcodec','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r',str(FPS),'-i','-',
         '-an','-c:v','libx264','-threads','2','-preset','fast','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',str(out)]
    process=subprocess.Popen(cmd,stdin=subprocess.PIPE)
    try:
        for k in range(n):process.stdin.write(render_frame(scene,index,count,k/FPS).tobytes())
    finally:process.stdin.close()
    if process.wait()!=0:raise RuntimeError(f"Render failed: {scene['id']}")
    proof={'scene_id':scene['id'],'visual_signature':signature,'output_sha256':sha(out),'duration_frames':n}
    out.with_suffix('.render.json').write_text(json.dumps(proof,indent=2),encoding='utf-8')
    print(f"Rendered {scene['id']}: {n} frames",flush=True)
    return proof

def previews():
    global AUDIT
    data=story();scenes=data['scenes'];dest=ROOT/'qa/styleframes';dest.mkdir(parents=True,exist_ok=True);rows=[]
    for i,s in enumerate(scenes):
        d=duration(s);AUDIT=[]
        for f in (0,.04,.10,.25,.45,.65,.82,.95,.999):render_frame(s,i,len(scenes),d*f)
        rows.append({'id':s['id'],'sample_times':[round(d*f,3) for f in (0,.04,.10,.25,.45,.65,.82,.95,.999)],
                     'text_within_canvas':all(r['within_canvas'] for r in AUDIT),'text_samples':len(AUDIT)})
        AUDIT=None
        render_frame(s,i,len(scenes),d*.86).save(dest/f"{s['id']}.png")
    sheet=Image.new('RGB',(1280,math.ceil(len(scenes)/3)*266),LIGHT)
    dr=ImageDraw.Draw(sheet)
    for i,s in enumerate(scenes):
        pic=Image.open(dest/f"{s['id']}.png").resize((420,236),Image.Resampling.LANCZOS);x=(i%3)*426;y=(i//3)*266
        sheet.paste(pic,(x,y));dr.text((x+5,y+240),s['id'],font=font(18,600),fill=BLUE)
    sheet.save(ROOT/'qa/contact-sheet.png')
    (ROOT/'qa/visual-qa.json').write_text(json.dumps({'stage':'rendered_preview','samples_per_scene':9,'scenes':rows,
                  'all_text_within_canvas':all(r['text_within_canvas'] for r in rows),
                  'timing_basis':'actual_narration' if all('duration' in s for s in scenes) else 'estimated_preview',
                  'note':'Text-bounds checks are supplemented by visual inspection.'},indent=2),encoding='utf-8')
    print(f'{len(scenes)} scene previews and contact sheet complete.',flush=True)

def proof():
    data=story();scene=dict(data['scenes'][14]);scene['duration']=10.;out=ROOT/'qa/motion-proof.mp4'
    process=subprocess.Popen(['ffmpeg','-y','-v','error','-f','rawvideo','-pix_fmt','rgb24','-s',f'{W}x{H}','-r','30','-i','-',
            '-an','-c:v','libx264','-threads','2','-preset','fast','-crf','20','-pix_fmt','yuv420p',str(out)],stdin=subprocess.PIPE)
    for k in range(300):process.stdin.write(render_frame(scene,14,len(data['scenes']),k/30).tobytes())
    process.stdin.close()
    if process.wait()!=0:raise RuntimeError('Proof rendering failed')
    subprocess.run(['ffmpeg','-v','error','-i',str(out),'-f','null','-'],check=True)
    print('10-second motion proof complete and fully decoded.',flush=True)

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--frames',action='store_true');ap.add_argument('--proof',action='store_true')
    ap.add_argument('--all',action='store_true');ap.add_argument('--scene');ap.add_argument('--workers',type=int,default=3);args=ap.parse_args()
    if args.frames:previews()
    if args.proof:proof()
    if args.all or args.scene:
        scenes=story()['scenes'];jobs=[(s,i,len(scenes)) for i,s in enumerate(scenes) if args.all or s['id']==args.scene]
        if args.workers==1:
            for j in jobs:render_scene(j)
        else:
            with ProcessPoolExecutor(max_workers=args.workers) as pool:list(pool.map(render_scene,jobs))

if __name__=='__main__':main()
