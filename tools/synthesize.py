"""Offline Malay speech, with caption boundaries measured from actual PCM samples."""
import ctypes as c
import json
import re
import wave
from pathlib import Path
import espeakng_loader


def generate(project):
    root=Path(project);story=json.loads((root/'storyboard.json').read_text())
    lib=espeakng_loader.load_library()
    lib.espeak_Initialize.argtypes=[c.c_int,c.c_int,c.c_char_p,c.c_int]
    lib.espeak_Initialize.restype=c.c_int
    rate=lib.espeak_Initialize(2,0,espeakng_loader.get_data_path().encode(),0)
    if rate<=0:raise RuntimeError('eSpeak initialization failed')
    lib.espeak_SetVoiceByName.argtypes=[c.c_char_p]
    if lib.espeak_SetVoiceByName(b'ms')!=0:raise RuntimeError('Malay voice unavailable')
    lib.espeak_SetParameter(1,165,0)
    lib.espeak_Synth.argtypes=[c.c_char_p,c.c_size_t,c.c_uint,c.c_int,c.c_uint,c.c_uint,c.c_void_p,c.c_void_p]
    blocks=[]
    @c.CFUNCTYPE(c.c_int,c.POINTER(c.c_short),c.c_int,c.c_void_p)
    def callback(data,n,events):
        if data and n:blocks.append(c.string_at(data,n*2))
        return 0
    lib.espeak_SetSynthCallback(callback)
    replacements=story.get('pronunciation',{})
    (root/'audio').mkdir(exist_ok=True)
    for scene in story['scenes']:
        chunks=[];chunk=''
        for word in scene['narration'].split():
            if len(chunk)+len(word)>145:chunks.append(chunk);chunk=''
            chunk=(chunk+' '+word).strip()
        if chunk:chunks.append(chunk)
        pcm=bytearray();cues=[]
        for chunk in chunks:
            spoken=chunk
            for a,b in replacements.items():spoken=spoken.replace(a,b)
            spoken=spoken.replace('→',', kemudian ').replace('•',', ').replace(' / ',' atau ')
            blocks.clear();data=spoken.encode()
            status=lib.espeak_Synth(data,len(data)+1,0,1,0,1,None,None)
            lib.espeak_Synchronize()
            if status!=0:raise RuntimeError('Speech synthesis failed: '+scene['id'])
            start=len(pcm)/(2*rate);pcm.extend(b''.join(blocks))
            cues.append({'start':start,'end':len(pcm)/(2*rate),'text':chunk})
        with wave.open(str(root/'audio'/f"{scene['id']}.wav"),'wb') as out:
            out.setnchannels(1);out.setsampwidth(2);out.setframerate(rate);out.writeframes(pcm)
        (root/'audio'/f"{scene['id']}.cues.json").write_text(json.dumps(cues,ensure_ascii=False,indent=2))
        print('Voice:',scene['id'],round(len(pcm)/(2*rate),2),'s',flush=True)
