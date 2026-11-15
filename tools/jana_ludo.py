"""Generate a new Ludo recording with the Gemini API and save it as a WAV."""

import argparse
import io
import os
from pathlib import Path
import wave


def collect_wav(responses):
    audio = bytearray()
    audio_format = None
    for response in responses:
        for part in response.parts or ():
            inline = part.inline_data
            if not inline or not inline.data:
                continue
            mime, *params = (inline.mime_type or '').lower().split(';')
            options = dict(param.strip().split('=', 1) for param in params if '=' in param)
            current = (mime.strip(), int(options.get('rate', '24000')))
            if audio_format is not None and current != audio_format:
                raise ValueError('Format audio berubah semasa penjanaan.')
            audio_format = current
            audio.extend(inline.data)

    if not audio or audio_format is None:
        raise ValueError('Gemini tidak memulangkan audio.')
    mime, sample_rate = audio_format
    if mime in ('audio/wav', 'audio/x-wav'):
        wav = bytes(audio)
    elif mime == 'audio/l16' and len(audio) % 2 == 0:
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as output:
            output.setparams((1, 2, sample_rate, 0, 'NONE', 'not compressed'))
            output.writeframes(audio)
        wav = buffer.getvalue()
    else:
        raise ValueError(f'Format audio tidak disokong: {mime}')

    with wave.open(io.BytesIO(wav), 'rb') as result:
        frame_bytes = result.getnchannels() * result.getsampwidth()
        frames = result.getnframes()
        if not frames or len(result.readframes(frames)) != frames * frame_bytes:
            raise ValueError('WAV kosong atau tidak lengkap.')
        return wav, frames / result.getframerate()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('script', type=Path, help='Fail teks narasi UTF-8')
    parser.add_argument('output', type=Path, help='Laluan fail WAV baharu')
    args = parser.parse_args()
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        parser.error('Tetapkan GEMINI_API_KEY dalam persekitaran setempat.')
    if args.output.suffix.lower() != '.wav' or args.output.exists():
        parser.error('Pilih laluan .wav yang belum wujud.')
    if not args.output.parent.is_dir():
        parser.error('Folder keluaran mesti wujud.')
    transcript = args.script.read_text(encoding='utf-8-sig').strip()
    if not transcript:
        parser.error('Skrip narasi kosong.')

    from google import genai
    from google.genai import types

    with genai.Client(api_key=api_key) as client:
        responses = client.models.generate_content_stream(
            model='gemini-3.8-flash-tts',
            contents=f'## Transcript:\n{transcript}',
            config=types.GenerateContentConfig(
                temperature=1,
                response_modalities=['audio'],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name='Ludo'),
                    ),
                ),
            ),
        )
        wav, duration = collect_wav(responses)

    with args.output.open('xb') as output:
        output.write(wav)
    print(f'{args.output} ({duration:.2f} saat)')


if __name__ == '__main__':
    main()
