#!/usr/bin/env python3
"""
Extract keyframes from a video at specified timestamps or regular intervals.
Usage:
  python extract_frames.py VIDEO_PATH OUTPUT_DIR --timestamps "00:10,01:30,02:45"
  python extract_frames.py VIDEO_PATH OUTPUT_DIR --interval 60
"""
import argparse, os, subprocess, sys

def main():
    parser = argparse.ArgumentParser(description="Extract keyframes from video")
    parser.add_argument("video", help="Path to video file")
    parser.add_argument("output_dir", help="Directory to save frames")
    parser.add_argument("--timestamps", help="Comma-separated timestamps in MM:SS format")
    parser.add_argument("--interval", type=int, default=0, help="Extract every N seconds")
    parser.add_argument("--quality", type=int, default=2, help="JPEG quality (2=best, 31=worst)")
    parser.add_argument("--size", default="", help="Optional resize e.g. 1280x720")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    if args.timestamps:
        timestamps = [t.strip() for t in args.timestamps.split(",")]
    elif args.interval:
        # Generate timestamps at regular intervals
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", args.video],
            capture_output=True, text=True
        )
        duration = float(result.stdout.strip())
        import math
        count = int(duration // args.interval)
        timestamps = []
        for i in range(count):
            ts = i * args.interval + min(args.interval // 2, 10)
            mins, secs = int(ts // 60), int(ts % 60)
            timestamps.append(f"{mins:02d}:{secs:02d}")
    else:
        print("Error: --timestamps or --interval required", file=sys.stderr)
        sys.exit(1)

    size_args = ["-s", args.size] if args.size else []
    
    for ts in timestamps:
        label = ts.replace(":", "_")
        out = os.path.join(args.output_dir, f"{label}.jpg")
        cmd = ["ffmpeg", "-y", "-ss", ts, "-i", args.video, "-vframes", "1", "-q:v", str(args.quality)]
        cmd += size_args + [out]
        subprocess.run(cmd, capture_output=True)
        print(f"  {ts} → {out}")

    print(f"\nDone: {len(timestamps)} frames in {args.output_dir}")

if __name__ == "__main__":
    main()
