"""Prepare actual voice timings, then assemble and verify the UiTM explainer.

No external service or original skill installation is required for rendering.
Run --prepare after all audio/sXX.wav files exist, render all scenes, then
run --assemble. Source WAVs and narration text are never modified here.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import sys
import wave

ROOT = Path(__file__).resolve().parent
STORY = ROOT / "storyboard.json"
AUDIO = ROOT / "audio"
QA = ROOT / "qa"
RENDERED = ROOT / "rendered"
OUTPUT = ROOT / "outputs"
PROJECT = json.loads((ROOT / "project.json").read_text(encoding="utf-8"))
OUTPUT_NAME = PROJECT["slug"] + "-" + PROJECT["version"] + ".mp4"
FPS, SR = 30, 48000
VOICE_OFFSET, GUARD = 0.25, 0.75
voiceover = PROJECT.get("voiceover", {})
VOICE = f"{voiceover.get('provider', 'Google AI Studio')} / {voiceover.get('voice', 'Ludo')}"
_VISUAL_FILE_CACHE = {}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def text_hash(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def visual_signature(scene: dict, index: int, count: int) -> str:
    """Stable render input hash. index is zero-based; audio-only metadata is ignored.

    Renderer saves this string under visual_signature in sXX.render.json along
    with output_sha256 and duration_frames. produce.py itself is not hashed.
    """
    ignored = {"narration", "narration_sha256", "audio_duration", "narration_offset",
               "duration_frames", "audio_file", "audio_sha256"}
    visual_scene = {key: value for key, value in scene.items() if key not in ignored}
    paths = [ROOT / "render_video.py"]
    for folder in (ROOT / "assets", ROOT / "local_resources"):
        paths += sorted(p for p in folder.rglob("*") if p.is_file()
                        and p.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg", ".ttf", ".otf", ".py"}
                        and "__pycache__" not in p.parts)
    files = {}
    for path in paths:
        stat = path.stat()
        cache_key = (str(path), stat.st_size, stat.st_mtime_ns)
        if cache_key not in _VISUAL_FILE_CACHE:
            _VISUAL_FILE_CACHE[cache_key] = digest(path)
        files[path.relative_to(ROOT).as_posix()] = _VISUAL_FILE_CACHE[cache_key]
    value = {"scene": visual_scene, "index": index, "count": count,
             "format": [1280, 720, FPS], "files": files}
    return text_hash(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def run(args):
    result = subprocess.run([str(a) for a in args], capture_output=True, text=True,
                            encoding="utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(f"Command failed: {' '.join(map(str, args[:7]))}\n{result.stderr[-6000:]}")
    return result


def ffmpeg(*args):
    return run(["ffmpeg", "-hide_banner", "-nostdin", "-y", *args])


def probe(path):
    return json.loads(run(["ffprobe", "-v", "error", "-show_format", "-show_streams",
                           "-of", "json", path]).stdout)


def wav_info(path):
    path = Path(path)
    with wave.open(str(path), "rb") as wav:
        frames, rate = wav.getnframes(), wav.getframerate()
        if wav.getcomptype() != "NONE" or frames <= 0 or rate <= 0:
            raise ValueError(f"Expected nonempty PCM WAV: {path}")
        return {"duration_seconds": frames / rate, "frames": frames, "sample_rate": rate,
                "channels": wav.getnchannels(), "sample_width": wav.getsampwidth(),
                "bytes": path.stat().st_size, "sha256": digest(path)}


def loudness_json(stderr):
    matches = re.findall(r'\{\s*"input_i".*?\}', stderr, re.S)
    if not matches:
        raise ValueError("FFmpeg returned no loudness measurements")
    info = json.loads(matches[-1])
    for key in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset"):
        if not math.isfinite(float(info[key])):
            raise ValueError(f"Invalid/silent audio loudness: {key}")
    return info


def norm_filter(info, target, peak):
    return (f"loudnorm=I={target}:TP={peak}:LRA=11:"
            f"measured_I={info['input_i']}:measured_TP={info['input_tp']}:"
            f"measured_LRA={info['input_lra']}:measured_thresh={info['input_thresh']}:"
            f"offset={info['target_offset']}:linear=true:print_format=json")


def validate_story(data):
    scenes = data["scenes"]
    ids = [scene["id"] for scene in scenes]
    if not scenes or ids != [f"s{i:02d}" for i in range(1, len(scenes) + 1)]:
        raise ValueError("Scene IDs must be consecutive from s01")
    source_ids = {source["id"] for source in data.get("sources", [])}
    for scene in scenes:
        narration = scene.get("narration", "")
        if not narration.strip() or not scene.get("source_refs"):
            raise ValueError(f"Missing narration/source references: {scene['id']}")
        if scene.get("narration_sha256") not in (None, text_hash(narration)):
            raise ValueError(f"Frozen narration hash mismatch: {scene['id']}")
        for ref in scene["source_refs"]:
            if ref["source"] not in source_ids:
                raise ValueError(f"Unknown source: {ref['source']}")
    if data.get("fps", FPS) != FPS:
        raise ValueError("Expected a 30 fps storyboard")
    return scenes


def prepare():
    data = read_json(STORY)
    scenes = validate_story(data)
    # Validate every original before changing prepared files or the storyboard.
    infos = {s["id"]: wav_info(AUDIO / f"{s['id']}.wav") for s in scenes}
    if len({info["sha256"] for info in infos.values()}) != len(scenes):
        raise ValueError("Duplicate voice clips; check the split/generation")
    if any(not 0.5 <= info["duration_seconds"] <= 180 for info in infos.values()):
        raise ValueError("Unexpected narration length; inspect clips before preparation")
    total_frames = sum(math.ceil((i["duration_seconds"] + GUARD) * FPS) for i in infos.values())
    if total_frames / FPS > 1800:
        raise ValueError("Video exceeds 30 minutes")
    normalized = AUDIO / "prepared"
    normalized.mkdir(parents=True, exist_ok=True)
    QA.mkdir(parents=True, exist_ok=True)
    cursor, timeline, manifest_scenes = 0, [], []
    source_map = {s["id"]: s for s in data["sources"]}
    if "user_pdf" in source_map and (ROOT / "source/video-unit-konsultasi.pdf").exists():
        source_map["user_pdf"]["packaged_path"] = "source/video-unit-konsultasi.pdf"
    for order, scene in enumerate(scenes, 1):
        sid = scene["id"]
        info = infos[sid]
        frames = math.ceil((info["duration_seconds"] + GUARD) * FPS)
        duration, samples = frames / FPS, frames * (SR // FPS)
        src, dst = AUDIO / f"{sid}.wav", normalized / f"{sid}.wav"
        measured = loudness_json(ffmpeg("-i", src, "-af",
            "loudnorm=I=-18:TP=-3:LRA=11:print_format=json", "-f", "null", "-").stderr)
        filt = (norm_filter(measured, -18, -3) + f",aresample={SR},"
                f"adelay={round(VOICE_OFFSET * SR)}S:all=1,apad=whole_len={samples},"
                f"atrim=end_sample={samples}")
        ffmpeg("-i", src, "-af", filt, "-ar", SR, "-ac", 1, "-c:a", "pcm_s16le", dst)
        prepared = wav_info(dst)
        if prepared["frames"] != samples or prepared["sample_rate"] != SR:
            raise ValueError(f"Prepared WAV is not sample-exact: {sid}")
        scene.update(duration=duration, duration_frames=frames,
                     audio_duration=info["duration_seconds"], narration_offset=VOICE_OFFSET)
        narration_hash = text_hash(scene["narration"])
        scene.setdefault("narration_sha256", narration_hash)
        start, end = cursor / FPS, (cursor + frames) / FPS
        timeline.append({"id": sid, "start_seconds": start, "end_seconds": end,
                         "start_frame": cursor, "duration_frames": frames, "duration_seconds": duration,
                         "narration_offset_seconds": VOICE_OFFSET,
                         "narration_text": scene["narration"], "narration_sha256": narration_hash,
                         "original_audio": info, "prepared_audio": prepared, "loudness_before": measured})
        sources = [dict(source_map[ref["source"]], **ref, reference=ref["source"], claim=scene["narration"])
                   for ref in scene["source_refs"]]
        text = [scene[k] for k in ("eyebrow", "title", "subtitle", "note") if scene.get(k)]
        text += scene.get("bullets", [])
        manifest_scenes.append({"id": sid, "order": order, "chapter_id": "pegawai_pengelas",
            "start_seconds": start, "end_seconds": end,
            "visual": {"description": scene["title"], "layout": scene.get("layout"),
                       "motion": "Layered vector, text and process-diagram animation with eased transitions."},
            "on_screen_text": text, "narration": {"text": scene["narration"],
                "voice_id": VOICE, "audio_file": f"audio/{sid}.wav", "offset_seconds": VOICE_OFFSET},
            "transition_in": {"type": "cut"}, "requires_source": True,
            "sources": sources, "claim_ids": scene.get("claim_ids", [])})
        cursor += frames
        print(f"Prepared {sid}: {info['duration_seconds']:.3f}s voice / {duration:.3f}s scene", flush=True)
    master = AUDIO / "narration-master.wav"
    with wave.open(str(master), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(SR)
        for scene in scenes:
            with wave.open(str(normalized / f"{scene['id']}.wav"), "rb") as clip:
                while chunk := clip.readframes(SR * 10):
                    out.writeframesraw(chunk)
    master_info = wav_info(master)
    if master_info["frames"] != cursor * (SR // FPS):
        raise ValueError("Master narration sample count mismatch")
    for sid, info in infos.items():
        if digest(AUDIO / f"{sid}.wav") != info["sha256"]:
            raise ValueError(f"Narration changed while preparing: {sid}; prepare again")
    backup = ROOT / "storyboard.before-voice-timing.json"
    if not backup.exists():
        shutil.copy2(STORY, backup)
    data.update(fps=FPS, duration_seconds=cursor / FPS, narration_provider=VOICE,
                narration_status="recorded_and_timed_from_final_scene_wavs")
    write_json(STORY, data)
    write_json(ROOT / "timeline.json", {"fps": FPS, "duration_frames": cursor,
        "duration_seconds": cursor / FPS, "master_audio": master_info, "scenes": timeline})
    manifest = {"schema_version": 1, "title": data["title"], "output_file": OUTPUT_NAME,
        "duration_seconds": cursor / FPS, "fps": FPS, "default_voice": VOICE,
        "chapters": [{"id": "pegawai_pengelas", "order": 1, "title": data["title"],
                      "scene_ids": [s["id"] for s in scenes]}], "scenes": manifest_scenes,
        "brand_reference": "assets/brand/brand-notes.md", "palette": "assets/brand/palette.json"}
    write_json(ROOT / "video-manifest.json", manifest)
    validator = ROOT / "validate_video_manifest.py"
    verdict = run([sys.executable, validator, ROOT / "video-manifest.json"])
    write_json(QA / "manifest-review.json", {"status": "passed", "scene_count": len(scenes),
        "manifest_sha256": digest(ROOT / "video-manifest.json"), "output": verdict.stdout.strip()})
    print(f"Prepared {len(scenes)} scenes: {cursor / FPS:.3f}s. Render updated storyboard before assembly.")


def concat_line(path):
    return "file '" + Path(path).resolve().as_posix().replace("'", "'\\''") + "'\n"


def assemble(output_dir=OUTPUT):
    output_dir = Path(output_dir).expanduser().resolve()
    data, timeline = read_json(STORY), read_json(ROOT / "timeline.json")
    scenes = validate_story(data)
    duration, total_frames = timeline["duration_seconds"], timeline["duration_frames"]
    if len(scenes) != len(timeline["scenes"]):
        raise ValueError("Scene count changed; prepare and render again")
    segments, proofs = [], {}
    for index, (scene, timing) in enumerate(zip(scenes, timeline["scenes"], strict=True)):
        sid = scene["id"]
        if sid != timing["id"] or text_hash(scene["narration"]) != timing["narration_sha256"]:
            raise ValueError(f"Script changed since preparation: {sid}")
        if digest(AUDIO / f"{sid}.wav") != timing["original_audio"]["sha256"]:
            raise ValueError(f"Voice changed since preparation: {sid}")
        if round(scene["duration"] * FPS) != timing["duration_frames"]:
            raise ValueError(f"Duration changed: {sid}")
        path = RENDERED / f"{sid}.mp4"
        proof = read_json(RENDERED / f"{sid}.render.json")
        if proof["visual_signature"] != visual_signature(scene, index, len(scenes)):
            raise ValueError(f"Stale render inputs: {sid}; rerender this scene")
        if proof["output_sha256"] != digest(path) or proof["duration_frames"] != timing["duration_frames"]:
            raise ValueError(f"Rendered file/duration differs from render proof: {sid}")
        streams = [s for s in probe(path)["streams"] if s["codec_type"] == "video"]
        if len(streams) != 1:
            raise ValueError(f"Expected one video stream: {sid}")
        stream = streams[0]
        if any([stream["codec_name"] != "h264", stream["width"] != 1280,
                stream["height"] != 720, stream["pix_fmt"] != "yuv420p",
                stream["r_frame_rate"] != "30/1", int(stream.get("nb_frames", -1)) != timing["duration_frames"]]):
            raise ValueError(f"Rendered specification/frame mismatch: {sid}")
        segments.append(path)
        proofs[sid] = proof
    master = AUDIO / "narration-master.wav"
    if digest(master) != timeline["master_audio"]["sha256"]:
        raise ValueError("Master narration changed; prepare again")
    QA.mkdir(parents=True, exist_ok=True)
    concat = ROOT / "video-concat.txt"
    concat.write_text("".join(concat_line(path) for path in segments), encoding="utf-8")
    silent = RENDERED / "silent-full.mp4"
    ffmpeg("-f", "concat", "-safe", "0", "-i", concat, "-map", "0:v:0", "-an",
           "-c:v", "copy", "-movflags", "+faststart", silent)
    print(f"Joined {len(scenes)} scenes: {duration:.3f}s", flush=True)
    music = AUDIO / "music-final.wav"
    music_variant = f"{PROJECT['slug']}/{PROJECT['version']}"
    run([sys.executable, ROOT / "create_audio.py", "--duration", duration,
         "--output", music, "--variant", music_variant])
    mixed = AUDIO / "mix-before-mastering.wav"
    graph = ("[0:a]pan=stereo|c0=c0|c1=c0[voice];[1:a]volume=0.40[music];"
             f"[voice][music]amix=inputs=2:duration=first:dropout_transition=0:normalize=0,atrim=duration={duration}[mix]")
    ffmpeg("-i", master, "-i", music, "-filter_complex", graph, "-map", "[mix]",
           "-ar", SR, "-c:a", "pcm_s24le", mixed)
    before = loudness_json(ffmpeg("-i", mixed, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
                                  "-f", "null", "-").stderr)
    output_dir.mkdir(parents=True, exist_ok=True)
    final = output_dir / OUTPUT_NAME
    temp = output_dir / (final.stem + ".partial.mp4")
    encoded = ffmpeg("-i", silent, "-i", mixed, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
        "-af", norm_filter(before, -16, -1.5), "-ar", SR, "-ac", 2, "-c:a", "aac", "-b:a", "192k",
        "-t", duration, "-metadata", f"title={data['title']}", "-metadata", f"comment={VOICE}",
        "-movflags", "+faststart", temp)
    (QA / "final-encode.log").write_text(encoded.stderr, encoding="utf-8")
    metadata = probe(temp)
    video = next(s for s in metadata["streams"] if s["codec_type"] == "video")
    sound = next(s for s in metadata["streams"] if s["codec_type"] == "audio")
    decoded = ffmpeg("-v", "error", "-i", temp, "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-")
    measured = loudness_json(ffmpeg("-i", temp, "-vn", "-af", "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json",
                                    "-f", "null", "-").stderr)
    checks = {"h264": video["codec_name"] == "h264", "aac": sound["codec_name"] == "aac",
        "1280x720": (video["width"], video["height"]) == (1280, 720), "30fps": video["r_frame_rate"] == "30/1",
        "yuv420p": video["pix_fmt"] == "yuv420p", "frame_count": int(video["nb_frames"]) == total_frames,
        "duration": abs(float(metadata["format"]["duration"]) - duration) < 0.06,
        "stereo_48khz": sound["channels"] == 2 and int(sound["sample_rate"]) == SR,
        "complete_decode": not decoded.stderr.strip(),
        "loudness_within_1_lu": abs(float(measured["input_i"]) + 16) <= 1,
        "true_peak_below_minus_1_db": float(measured["input_tp"]) <= -1}
    report = {"checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "file": str(final), "bytes": temp.stat().st_size, "sha256": digest(temp),
        "duration_seconds": duration, "duration_frames": total_frames, "scene_count": len(scenes),
        "checks": checks, "technical_checks_passed": all(checks.values()),
        "ffprobe": metadata, "final_audio_measurements": measured, "mix_measurements_before_mastering": before,
        "decode_log": decoded.stderr, "voice_provider": VOICE,
        "voice_clip_hashes": {s["id"]: s["original_audio"]["sha256"] for s in timeline["scenes"]},
        "render_provenance": proofs,
        "review_limit": "Automated technical verification does not establish factual accuracy or perfect pronunciation. Refer to the separate content, visual and audio transcript reviews."}
    audio_review = QA / "audio-review.json"
    if audio_review.is_file():
        report["audio_content_review"] = read_json(audio_review)
    write_json(QA / "final-technical-report.json", report)
    if not all(checks.values()):
        raise ValueError(f"Final verification failed: {[k for k, value in checks.items() if not value]}; partial MP4 retained")
    temp.replace(final)
    write_json(output_dir / "video-manifest.json", read_json(ROOT / "video-manifest.json"))
    print(f"SUCCESS: {final}\n{duration:.3f}s; {len(scenes)} scenes; all {len(checks)} technical checks passed.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare", action="store_true")
    group.add_argument("--assemble", action="store_true")
    ap.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = ap.parse_args()
    for command in ("ffmpeg", "ffprobe"):
        if shutil.which(command) is None:
            ap.error(f"{command} must be available on PATH")
    prepare() if args.prepare else assemble(args.output_dir)


if __name__ == "__main__":
    main()
