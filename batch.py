"""
batch.py — Batch runner for CEO Stories Philippines.

Generates multiple CEO success story videos in sequence (no upload by default).
Usage:
    python batch.py              # generates 3 videos, no upload
    python batch.py --count 5    # generates 5 videos
    python batch.py --upload     # generates + uploads to YouTube
"""

import argparse
import sys
import time
from main import create_drama_video


def run_batch(count: int = 3, upload: bool = False, delay: int = 15) -> None:
    print(f"\n{'='*60}")
    print(f"  CEO STORIES PHILIPPINES — Batch Generator")
    print(f"  Videos: {count} | Upload: {upload} | Delay: {delay}s")
    print(f"{'='*60}\n")

    results = []
    failed  = []

    for i in range(1, count + 1):
        print(f"\n[Batch {i}/{count}] Starting video generation...")
        try:
            result = create_drama_video(upload=upload)
            results.append(result)
            print(f"[Batch {i}/{count}] Done → {result.get('video_path', '?')}")
            if i < count:
                print(f"[Batch] Waiting {delay}s before next video...")
                time.sleep(delay)
        except Exception as e:
            print(f"[Batch {i}/{count}] FAILED: {e}")
            failed.append({"index": i, "error": str(e)})

    # Summary
    print(f"\n{'='*60}")
    print(f"  BATCH COMPLETE")
    print(f"  Success: {len(results)}/{count}")
    if failed:
        print(f"  Failed:  {len(failed)}/{count}")
        for f in failed:
            print(f"    [{f['index']}] {f['error']}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Kwentong Multo batch video generator")
    parser.add_argument("--count",  type=int, default=3,    help="Number of videos to generate")
    parser.add_argument("--upload", action="store_true",    help="Upload to YouTube after rendering")
    parser.add_argument("--delay",  type=int, default=15,   help="Seconds to wait between videos")
    args = parser.parse_args()
    run_batch(count=args.count, upload=args.upload, delay=args.delay)
