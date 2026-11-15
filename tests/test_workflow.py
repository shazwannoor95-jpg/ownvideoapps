import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import math
import struct
import wave
from unittest.mock import patch
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import video

class VersionTests(unittest.TestCase):
    def test_title_versions_are_independent_and_remote_aware(self):
        self.assertEqual(video.slugify('Pelantikan Pegawai — UiTM!'),'pelantikan-pegawai-uitm')
        refs='abc\trefs/heads/video/tajuk/v003\ndef\trefs/tags/tajuk-v007\nabc\trefs/heads/video/lain/v999\n'
        self.assertEqual(video.next_version('tajuk',refs),'v008')
        self.assertEqual(video.next_version('baharu',refs),'v001')
        with self.assertRaises(ValueError):video.slugify('!!!')

    def test_source_words_are_kept_and_cards_bounded(self):
        text='# Peranan\n'+('Tugas pengurusan rekod jabatan. '*70)
        story=video.create_story('Video',text)
        spoken=' '.join(s['narration'] for s in story['scenes'])
        self.assertEqual(' '.join(spoken.split()),' '.join(text.split('\n',1)[1].split()))
        self.assertTrue(all(len(s['bullets'])<=3 for s in story['scenes']))

class LifecycleTests(unittest.TestCase):
    def test_local_render_and_independent_versions_without_git(self):
        with tempfile.TemporaryDirectory(prefix='portable-test-') as tmp:
            root=Path(tmp)
            source=root/'bahan.md'
            source.write_text('# Ujian\nIni ujian suara Melayu. Rekod disimpan dengan teratur.',encoding='utf8')
            old=video.REPO;video.REPO=root
            try:
                with patch.object(video,'git',side_effect=AssertionError('Git must never run')):
                    p=video.new('Ujian Video',source)
                    self.assertEqual(p.name,'v001')
                    info=json.loads((p/'project.json').read_text())
                    self.assertEqual(info['voiceover']['voice'],'Ludo')
                    self.assertEqual(info['storage'],'local')
                    self.assertNotIn('branch',info)
                    with wave.open(str(p/'audio/s01.wav'),'wb') as audio:
                        audio.setnchannels(1);audio.setsampwidth(2);audio.setframerate(24000)
                        audio.writeframes(b''.join(struct.pack('<h',round(2000*math.sin(2*math.pi*220*n/24000))) for n in range(72000)))
                    (p/'audio/s01.cues.json').write_text(json.dumps([{'start':0,'end':3,'text':'Ini ujian suara Melayu. Rekod disimpan dengan teratur.'}]))
                    video.render(p,1)
                    info=json.loads((p/'project.json').read_text())
                    self.assertEqual(info['status'],'RENDERED')
                    self.assertTrue((p/info['final_video']).is_file())
                    report=json.loads((p/'qa/final-technical-report.json').read_text(encoding='utf8'))
                    self.assertTrue(report['technical_checks_passed'])
                    self.assertEqual(video.new('Ujian Video',source).name,'v002')
                    self.assertEqual(video.new('Tajuk Lain',source).name,'v001')
                with self.assertRaisesRegex(ValueError,'dilumpuhkan'):video.publish(p)
            finally:video.REPO=old

    def test_original_repository_is_rejected_without_reading(self):
        with patch.object(Path,'read_text',side_effect=AssertionError('Must not read source')):
            with self.assertRaisesRegex(ValueError,'dilindungi'):
                video.new('Forbidden','/workspace/ownvideo/README.md')
        with self.assertRaisesRegex(ValueError,'dilumpuhkan'):video.git('status')

class VoicePolicyTests(unittest.TestCase):
    def test_missing_ludo_audio_blocks_render_before_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)
            (p/'storyboard.json').write_text(json.dumps({'scenes':[{'id':'s01'}]}))
            with patch.object(video,'project',return_value=(p,{})),patch.object(video,'run') as run:
                with self.assertRaisesRegex(ValueError,'WAV Ludo'):
                    video.render(p,1)
                (p/'audio').mkdir();(p/'audio/s01.wav').touch()
                with self.assertRaisesRegex(ValueError,'s01.cues.json'):
                    video.render(p,1)
                run.assert_not_called()

    def test_resynthesis_cannot_fall_back_to_offline_voice(self):
        with patch.object(video,'project',return_value=(Path('/unused'),{})),patch.object(video,'run') as run:
            with self.assertRaisesRegex(ValueError,'Google AI Studio'):
                video.render('/unused',1,resynthesize=True)
            run.assert_not_called()

if __name__=='__main__':unittest.main()
