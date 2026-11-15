"""Original, restrained background score for the UiTM explainer.

Usage: python create_audio.py --duration 150 --output audio/music.wav
Optional --scene-cues cues.json accepts a list (or {"scenes": [...]}) with
time/start/start_time in seconds, and type/sfx of paper, tick, or chime.
No samples, downloaded content, voices, or third-party music are used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, sosfilt


SR = 48000


def hz(midi: float) -> float:
    return 440.0 * 2.0 ** ((midi - 69.0) / 12.0)


def envelope(n: int, attack: float, release: float) -> np.ndarray:
    e = np.ones(n, np.float32)
    a = min(int(SR * attack), n // 2)
    r = min(int(SR * release), n // 2)
    if a:
        e[:a] = np.sin(np.linspace(0, np.pi / 2, a)) ** 2
    if r:
        e[-r:] = np.cos(np.linspace(0, np.pi / 2, r)) ** 2
    return e


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--duration", type=float, default=150.0)
    ap.add_argument("--output", type=Path, default=Path(__file__).resolve().parent / "audio/music.wav")
    ap.add_argument("--scene-cues", type=Path)
    ap.add_argument("--variant", help="Stable project identifier for a distinct arrangement")
    args = ap.parse_args()
    if not 0.1 <= args.duration <= 3600:
        ap.error("--duration must be 0.1 to 3600 seconds")
    n = int(round(SR * args.duration))
    mix = np.zeros((n, 2), np.float32)

    def add(sound: np.ndarray, start: float, gain: float = 1.0, pan: float = 0.0) -> None:
        idx = int(round(start * SR))
        if idx >= n:
            return
        if idx < 0:
            sound = sound[-idx:]
            idx = 0
        count = min(len(sound), n - idx)
        if count <= 0:
            return
        angle = (np.clip(pan, -1, 1) + 1) * np.pi / 4
        mix[idx : idx + count, 0] += sound[:count] * (gain * np.cos(angle))
        mix[idx : idx + count, 1] += sound[:count] * (gain * np.sin(angle))

    def pad(note: int, length: float, phase: float) -> np.ndarray:
        t = np.arange(int(length * SR), dtype=np.float32) / SR
        f = hz(note)
        # Rounded, detuned fundamental with breathing upper partials.
        x = (0.56 * np.sin(2 * np.pi * f * t + phase)
             + 0.24 * np.sin(2 * np.pi * f * 1.0018 * t + phase + 0.35)
             + 0.14 * np.sin(2 * np.pi * f * 2 * t + 0.17)
             + 0.06 * np.sin(2 * np.pi * f * 3 * t + 0.6))
        breath = 0.93 + 0.07 * np.sin(2 * np.pi * 0.11 * t + phase)
        return (x * breath * envelope(len(t), 0.7, 0.85)).astype(np.float32)

    def pluck(note: int, length: float = 1.35) -> np.ndarray:
        t = np.arange(int(length * SR), dtype=np.float32) / SR
        f = hz(note)
        # Mallet-like sine body and short, soft wood harmonics.
        x = (np.sin(2 * np.pi * f * t) * np.exp(-3.6 * t)
             + 0.25 * np.sin(2 * np.pi * 2 * f * t + 0.1) * np.exp(-6.2 * t)
             + 0.07 * np.sin(2 * np.pi * 3 * f * t) * np.exp(-9.0 * t))
        return (x * envelope(len(t), 0.007, 0.1)).astype(np.float32)

    def bass(note: int, length: float = 1.8) -> np.ndarray:
        t = np.arange(int(length * SR), dtype=np.float32) / SR
        f = hz(note)
        x = (np.sin(2 * np.pi * f * t) + 0.12 * np.sin(2 * np.pi * 2 * f * t))
        return (x * np.exp(-1.5 * t) * envelope(len(t), 0.04, 0.25)).astype(np.float32)

    variant = args.variant
    seed = int.from_bytes(hashlib.sha256(variant.encode("utf-8")).digest()[:8], "big") if variant else 8108
    rng = np.random.default_rng(seed)
    tempo = round(float(rng.uniform(68, 82)), 2) if variant else 76.0
    transpose = int(rng.integers(-4, 5)) if variant else 0
    beat = 60.0 / tempo
    bar = 4 * beat
    # Cmaj9 - Am7 - Fmaj9 - Gsus/add9. Voicing keeps the middle register clear.
    chords = [([48, 55, 59, 62], 36), ([48, 55, 57, 60], 33),
              ([48, 53, 57, 64], 29), ([50, 55, 60, 62], 31)]
    patterns = [[0, 2, 1, 3], [0, 1, 3, 2], [2, 0, 3, 1], [0, 3, 2, 1]]
    if variant:
        # Keep the first note anchored and vary the remaining arpeggio and its timing.
        patterns = [[0, *rng.permutation([1, 2, 3]).tolist()] for _ in patterns]
        pluck_positions = np.array([0.5, 1.35, 2.2, 3.05]) + rng.uniform(-0.18, 0.18, size=4)
    else:
        pluck_positions = [0.5, 1.35, 2.2, 3.05]
    bars = int(np.ceil(args.duration / bar))
    for b in range(bars):
        start = b * bar
        chord, root = chords[b % 4]
        cycle = b // 4
        # Gentle variation in arrangement, register and dynamics over longer videos.
        flow = 0.88 + 0.12 * np.sin(2 * np.pi * b / 24 - 0.3)
        for j, note in enumerate(chord):
            p = [-0.48, 0.42, -0.22, 0.26][j]
            add(pad(note + transpose, bar + 0.32, j * 0.7 + b * 0.17), start,
                gain=0.020 * flow, pan=p)
        for position in (0, 2):
            add(bass(root + transpose), start + position * beat, gain=0.040 * flow, pan=0)
        pattern = patterns[cycle % len(patterns)]
        for k, j in enumerate(pattern):
            if cycle % 4 == 3 and k == 3:  # Occasional rest lets narration breathe.
                continue
            note = chord[j] + 12 + transpose
            if cycle % 3 == 2 and k == 2:
                note += 12
            when = start + pluck_positions[k] * beat
            amount = (0.028 if k % 2 else 0.036) * flow
            tone = pluck(note)
            pan = (-0.3 if k % 2 else 0.3)
            add(tone, when, amount, pan)
            add(tone, when + 0.22, amount * 0.15, -pan)
            add(tone, when + 0.43, amount * 0.055, pan)
        # Very soft muted pulse, adding movement without a hard drum attack.
        for k in (1, 3):
            t = np.arange(int(0.10 * SR), dtype=np.float32) / SR
            pulse = np.sin(2 * np.pi * 185 * t) * np.exp(-70 * t)
            pulse *= envelope(len(t), 0.004, 0.03)
            add(pulse.astype(np.float32), start + k * beat, 0.014, -0.1)

    cue_count = 0
    if args.scene_cues:
        cues = json.loads(args.scene_cues.read_text(encoding="utf-8-sig"))
        if isinstance(cues, dict):
            cues = cues.get("scenes", cues.get("cues", []))
        for cue in cues:
            when = float(cue.get("time", cue.get("start", cue.get("start_time", 0))))
            kind = cue.get("type", cue.get("sfx", "paper"))
            if kind == "paper":
                count = int(0.28 * SR)
                noise = rng.normal(size=count).astype(np.float32)
                filtered = sosfilt(butter(2, [600, 3400], btype="bandpass", fs=SR, output="sos"), noise)
                filtered /= max(float(np.max(np.abs(filtered))), 1e-8)
                add((filtered * envelope(count, 0.06, 0.16)).astype(np.float32), when, 0.018, -0.12)
            elif kind == "tick":
                add(pluck(84, 0.12), when, 0.023, 0.15)
            elif kind == "chime":
                add(pluck(76, 1.5), when, 0.026, -0.18)
                add(pluck(79, 1.5), when + 0.09, 0.020, 0.18)
            else:
                continue
            cue_count += 1

    # Light room wash of the score, with unequal delays to retain stereo width.
    for channel, delay in ((0, 0.067), (1, 0.083)):
        offset = int(SR * delay)
        if n > offset:
            mix[offset:, channel] += mix[:-offset, channel].copy() * 0.075
    # No DC, no harsh edges, controlled excursion well below full scale.
    mix -= np.mean(mix, axis=0)
    mix *= envelope(n, min(2.0, args.duration / 4), min(4.0, args.duration / 3))[:, None]
    peak_before = float(np.max(np.abs(mix)))
    rms_before = float(np.sqrt(np.mean(np.square(mix, dtype=np.float64))))
    mix *= min(0.29 / max(peak_before, 1e-12), 0.030 / max(rms_before, 1e-12))
    peak = float(np.max(np.abs(mix)))
    rms = float(np.sqrt(np.mean(np.square(mix, dtype=np.float64))))
    if not np.isfinite(mix).all() or peak >= 0.45:
        raise RuntimeError("Audio validation failed: non-finite samples or peak exceeded target")
    pcm = np.round(np.clip(mix, -1, 1) * 32767).astype(np.int16)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    wavfile.write(args.output, SR, pcm)
    report = {"file": str(args.output.resolve()), "duration_seconds": n / SR,
              "sample_rate": SR, "channels": 2, "sample_format": "signed PCM 16-bit",
              "tempo_bpm": tempo, "music_variant": variant, "transpose_semitones": transpose,
              "peak_linear": peak,
              "peak_dbfs": round(20 * np.log10(max(peak, 1e-12)), 2),
              "rms_dbfs": round(20 * np.log10(max(rms, 1e-12)), 2),
              "finite_samples": True, "clipped_samples": 0,
              "scene_accents": cue_count, "original_procedural_composition": True}
    args.output.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
