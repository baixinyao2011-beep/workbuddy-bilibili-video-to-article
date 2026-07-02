#!/usr/bin/env python3
"""
Transcribe audio using faster-whisper with timestamps.
Usage: python transcribe.py AUDIO_PATH OUTPUT_PATH [--model medium|large-v3]
"""
import argparse, sys, time
from faster_whisper import WhisperModel

def main():
    parser = argparse.ArgumentParser(description="Transcribe audio with faster-whisper")
    parser.add_argument("audio", help="Path to 16kHz mono WAV file")
    parser.add_argument("output", help="Path to output transcript file")
    parser.add_argument("--model", default="large-v3", choices=["medium", "large-v3", "large-v2", "small", "base", "tiny"])
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--language", default="zh")
    parser.add_argument("--beam-size", type=int, default=5)
    parser.add_argument("--no-vad", action="store_true", default=True, help="Disable VAD (default: True for completeness)")
    parser.add_argument("--vad", action="store_true", help="Enable VAD filtering")
    args = parser.parse_args()

    print(f"[1/3] Loading model '{args.model}'...", flush=True)
    t0 = time.time()
    model = WhisperModel(
        args.model, device=args.device, compute_type="int8",
        num_workers=4, cpu_threads=8,
    )
    print(f"      Model loaded in {time.time() - t0:.1f}s", flush=True)

    print(f"[2/3] Transcribing: {args.audio}", flush=True)
    vad_filter = not args.no_vad if hasattr(args, 'vad') else not args.no_vad
    if args.vad:
        vad_filter = True
    else:
        vad_filter = not args.no_vad
    
    t1 = time.time()
    segments, info = model.transcribe(
        args.audio, language=args.language, beam_size=args.beam_size,
        vad_filter=vad_filter,
        condition_on_previous_text=True,
        no_speech_threshold=0.3,
    )
    print(f"      Language: {info.language} ({info.language_probability:.2f})", flush=True)
    print(f"      Duration: {info.duration:.1f}s", flush=True)

    print(f"[3/3] Writing to {args.output}...", flush=True)
    count = 0
    with open(args.output, "w", encoding="utf-8") as f:
        for seg in segments:
            count += 1
            text = seg.text.strip()
            if not text:
                continue
            mins, secs = int(seg.start // 60), int(seg.start % 60)
            f.write(f"[{mins:02d}:{secs:02d}] {text}\n")
            if count % 50 == 0:
                print(f"      ... {count} segments", flush=True)

    elapsed = time.time() - t1
    print(f"\nDone: {count} segments in {elapsed:.1f}s ({info.duration/elapsed:.1f}x realtime)", flush=True)

if __name__ == "__main__":
    main()
