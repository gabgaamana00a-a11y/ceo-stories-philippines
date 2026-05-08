"""
main.py — Drama Desk pipeline orchestrator.

Daily flow:
  1. Fetch trending story seed from Reddit (or curated fallback)
  2. Generate original multi-voice drama script via OpenRouter
  3. Synthesize multi-voice TTS audio (Edge TTS)
  4. Render 1920x1080 YouTube video with Pexels B-roll + subtitles
  5. Generate thumbnail
  6. Upload to YouTube

Run manually:
    python main.py
    python main.py --seed "My boss publicly humiliated me and I quit on the spot"
    python main.py --no-upload
"""

import os
import asyncio
import json
import random
import re
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from config import (
    CHANNEL_NAME, UPLOAD_TAGS, UPLOAD_PRIVACY, UPLOAD_CATEGORY, SCENE_KEYWORDS
)
from trending import get_trending_drama_seed
from script_writer import generate_drama_script
from tts_engine import generate_drama_audio
from video_renderer import render_drama_video
from thumbnail import generate_thumbnail


# ── Scene tag extraction ──────────────────────────────────────────────────────

def _extract_scene_tags(script: str) -> list[str]:
    """Map script keywords to Pexels search terms for scene-matched B-roll."""
    lower = script.lower()
    tags = []
    scene_map = {
        "restaurant": ["restaurant dining", "cafe table"],
        "kitchen":    ["kitchen home", "cooking"],
        "bedroom":    ["bedroom interior"],
        "office":     ["office workplace", "business people"],
        "wedding":    ["wedding ceremony", "bride groom"],
        "phone":      ["smartphone texting", "phone call"],
        "family":     ["family dinner", "family gathering"],
        "park":       ["park outdoor", "city street people"],
        "outdoor":    ["city street people", "outdoor lifestyle"],
        "argument":   ["couple conflict", "people dramatic"],
        "couple":     ["couple relationship"],
        "money":      ["money finance"],
        "hospital":   ["hospital interior", "medical"],
        "car":        ["car interior", "driving"],
    }
    for keyword, pexels_kws in scene_map.items():
        if keyword in lower:
            tags.extend(pexels_kws)
    if not tags:
        tags = list(SCENE_KEYWORDS["default"])
    return list(dict.fromkeys(tags))[:6]   # deduplicated, max 6


# ── Title & description ───────────────────────────────────────────────────────

_TITLE_PATTERNS = [
    'She Did WHAT?! | {seed}',
    'Am I Wrong? | {seed}',
    'This Changed Everything | {seed}',
    'Nobody Saw This Coming | {seed}',
    'Reddit Drama: {seed}',
    'AITA: {seed}',
    'I Can\'t Believe This Happened | {seed}',
    'The Truth Finally Came Out | {seed}',
]


def _make_title(story_seed: str) -> str:
    seed = story_seed.strip().rstrip("?").strip()
    # Cap seed at 65 chars for title length
    if len(seed) > 65:
        seed = seed[:62] + "..."
    pattern = random.choice(_TITLE_PATTERNS)
    title = pattern.format(seed=seed)
    return title[:100]   # YouTube title limit


def _make_description(story_seed: str, title: str) -> str:
    tags = " ".join([
        "#AITA", "#RedditDrama", "#DramaDesk", "#RelationshipAdvice",
        "#FamilyDrama", "#Reddit", "#StoryTime", "#AmITheAsshole",
        "#Relationships", "#TrueStory", "#EntitledPeople",
    ])
    return (
        f"{title}\n\n"
        f"Today on Drama Desk we're diving into a story that has everyone divided.\n\n"
        f'"{story_seed}"\n\n'
        f"What do YOU think? Let us know in the comments!\n\n"
        f"Subscribe for daily drama: @DramaDeskChannel\n\n"
        f"{tags}"
    )


# ── Music finder ──────────────────────────────────────────────────────────────

def _find_music() -> str | None:
    music_dir = os.path.join(os.path.dirname(__file__), "music")
    if not os.path.isdir(music_dir):
        return None
    for f in os.listdir(music_dir):
        if f.lower().endswith((".mp3", ".wav", ".ogg", ".m4a", ".flac")):
            return os.path.join(music_dir, f)
    return None


# ── YouTube uploader ──────────────────────────────────────────────────────────

def _upload_youtube(video_path: str, title: str, description: str) -> str | None:
    try:
        import google.auth.transport.requests
        import google.oauth2.credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        token_file = os.path.join(os.path.dirname(__file__), "token.json")
        creds_file = os.path.join(os.path.dirname(__file__), "credentials.json")

        if not os.path.exists(token_file):
            print("[youtube] token.json not found — skipping upload")
            return None
        if not os.path.exists(creds_file):
            print("[youtube] credentials.json not found — skipping upload")
            return None

        with open(token_file) as f:
            token_data = json.load(f)
        with open(creds_file) as f:
            cred_data = json.load(f)

        installed = cred_data.get("installed", cred_data.get("web", {}))
        creds = google.oauth2.credentials.Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=installed.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=installed.get("client_id"),
            client_secret=installed.get("client_secret"),
            scopes=["https://www.googleapis.com/auth/youtube.upload"],
        )

        if creds.expired and creds.refresh_token:
            creds.refresh(google.auth.transport.requests.Request())
            with open(token_file, "w") as f:
                json.dump({
                    "token":          creds.token,
                    "refresh_token":  creds.refresh_token,
                    "token_uri":      creds.token_uri,
                    "client_id":      creds.client_id,
                    "client_secret":  creds.client_secret,
                }, f)

        youtube = build("youtube", "v3", credentials=creds)
        body = {
            "snippet": {
                "title":           title[:100],
                "description":     description[:5000],
                "tags":            UPLOAD_TAGS,
                "categoryId":      UPLOAD_CATEGORY,
                "defaultLanguage": "en",
            },
            "status": {
                "privacyStatus":           UPLOAD_PRIVACY,
                "selfDeclaredMadeForKids": False,
            },
        }
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/mp4")
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

        response = None
        while response is None:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"[youtube] Upload: {pct}%")

        video_id = response.get("id", "")
        url = f"https://www.youtube.com/watch?v={video_id}"
        print(f"[youtube] Live: {url}")
        return url

    except Exception as e:
        print(f"[youtube] Upload failed: {e}")
        return None


# ── Main pipeline ─────────────────────────────────────────────────────────────

async def create_drama_video(
    story_seed: str | None = None,
    output_dir: str | None = None,
    upload: bool = True,
) -> dict:
    """Run the full drama video pipeline. Returns result dict."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if output_dir is None:
        output_dir = os.path.join("output", f"drama_{timestamp}")
    os.makedirs(output_dir, exist_ok=True)

    banner = "=" * 60
    print(f"\n{banner}\n{CHANNEL_NAME} — {timestamp}\n{banner}")

    # ── 1. Story seed ─────────────────────────────────────────────────────────
    if not story_seed:
        print("\n[1/6] Fetching trending story seed...")
        story_seed = get_trending_drama_seed()
    print(f"  Seed: {story_seed[:85]}...")

    # ── 2. Script ─────────────────────────────────────────────────────────────
    print("\n[2/6] Generating drama script...")
    script = generate_drama_script(story_seed)
    script_path = os.path.join(output_dir, "script.txt")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)

    # ── 3. TTS audio ──────────────────────────────────────────────────────────
    print("\n[3/6] Generating multi-voice TTS audio...")
    tts_dir = os.path.join(output_dir, "tts")
    tts = await generate_drama_audio(script, tts_dir)
    dur = tts["total_duration"]
    print(f"  Duration: {dur:.1f}s ({dur/60:.1f} min) | {len(tts['segments'])} segments")

    # ── 4. Video render ───────────────────────────────────────────────────────
    print("\n[4/6] Rendering video...")
    scene_tags = _extract_scene_tags(script)
    music_path = _find_music()
    video_path = os.path.join(output_dir, "drama_video.mp4")
    render_drama_video(
        audio_path=tts["audio_path"],
        captions=tts["captions"],
        segments=tts["segments"],
        output_path=video_path,
        scene_tags=scene_tags,
        music_path=music_path,
    )

    # ── 5. Thumbnail ──────────────────────────────────────────────────────────
    print("\n[5/6] Generating thumbnail...")
    title = _make_title(story_seed)
    thumb_path = os.path.join(output_dir, "thumbnail.png")
    generate_thumbnail(title, thumb_path, video_path, style="drama")

    # ── 6. Upload ─────────────────────────────────────────────────────────────
    url = None
    if upload:
        print("\n[6/6] Uploading to YouTube...")
        description = _make_description(story_seed, title)
        url = _upload_youtube(video_path, title, description)
    else:
        print("\n[6/6] Upload skipped (--no-upload flag)")

    result = {
        "story_seed":      story_seed,
        "title":           title,
        "output_dir":      output_dir,
        "video_path":      video_path,
        "thumbnail_path":  thumb_path,
        "duration_seconds": dur,
        "youtube_url":     url,
        "timestamp":       timestamp,
    }

    result_path = os.path.join(output_dir, "result.json")
    with open(result_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"\n{banner}")
    print(f"DONE  →  {video_path}")
    if url:
        print(f"YouTube →  {url}")
    print(f"{banner}\n")

    return result


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Drama Desk — daily video generator")
    parser.add_argument("--seed",      type=str,  default=None, help="Custom story seed")
    parser.add_argument("--no-upload", action="store_true",     help="Skip YouTube upload")
    parser.add_argument("--output",    type=str,  default=None, help="Output directory")
    args = parser.parse_args()

    asyncio.run(create_drama_video(
        story_seed=args.seed,
        output_dir=args.output,
        upload=not args.no_upload,
    ))
