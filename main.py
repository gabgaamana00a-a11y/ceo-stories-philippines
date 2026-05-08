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

# Keyword-matched punchy title pools — no raw seed text dumped in.
# Top AITA channels use short emotional hooks, not full sentences.
_TITLE_POOLS = [
    # (keywords, [title variants])
    (["wedding", "venue", "bride", "ceremony", "tacky"], [
        "She Called My Sister's Wedding TACKY and Now the Family is DONE With Her 😱",
        "I Said ONE Thing About the Wedding and Destroyed the Whole Family | AITA",
        "Was I Wrong to Call Her Wedding Choice Embarrassing? | Reddit Drama",
        "She Ruined the Wedding With ONE Sentence and I'm Still Not Over It | AITA",
    ]),
    (["cheating", "affair", "cheated"], [
        "I Found Out She Was Cheating and I'm Not Sorry 😤 | Reddit Drama AITA",
        "He Thought I'd Never Find Out… He Was Wrong | Reddit AITA Drama",
        "She Was Cheating the Whole Time and Nobody Saw This Coming 😱 | AITA",
    ]),
    (["divorce", "separated"], [
        "The Divorce No One Saw Coming — And I'm Still Not Over It | AITA Drama",
        "My Marriage Ended Over This and EVERYONE Has an Opinion 😤 | Reddit AITA",
    ]),
    (["fired", "quit", "boss", "workplace"], [
        "I Quit My Job in Front of EVERYONE and Never Looked Back 😤 | AITA",
        "My Boss Pushed Me Too Far… So I Did This | Reddit Drama AITA",
        "I Said What Nobody Else Would Say at Work and the Drama Was UNREAL | AITA",
    ]),
    (["mother-in-law", "mil"], [
        "My Mother-In-Law CROSSED the Line and I Finally Snapped | Reddit AITA",
        "She Went Too Far and I'm DONE Being Silent | Reddit Drama AITA",
    ]),
    (["mom", "mother", "stepmom"], [
        "My Own Mom BETRAYED Me and the Family is SPLIT | Reddit AITA Drama",
        "She's My Mom and She Still Did THIS — Am I Wrong for Cutting Her Off? | AITA",
    ]),
    (["sister"], [
        "My Sister Did the Unthinkable and the Whole Family Chose Sides | AITA",
        "She's My Sister and She STILL Did That 😱 | Reddit Drama AITA",
        "My Sister Crossed a Line I Can't Come Back From | Reddit AITA",
    ]),
    (["brother"], [
        "My Brother Crossed the Line and I Finally Said Enough | Reddit AITA",
        "He's My Brother and He STILL Did This — Who's Wrong Here? | AITA Drama",
    ]),
    (["boyfriend", "girlfriend", "ex", "dating"], [
        "My Ex Thought I'd Stay Silent… They Were WRONG 😤 | Reddit Drama AITA",
        "She Did This Behind My Back and NOBODY Saw It Coming 😱 | AITA",
        "I Found Out the Truth About My Partner and Everything Changed | AITA Drama",
    ]),
    (["husband"], [
        "My Husband's Secret Came Out and Changed EVERYTHING | Reddit AITA Drama",
        "He Thought I Didn't Know… But I Knew Everything 😤 | Reddit Drama",
    ]),
    (["wife"], [
        "She Hid This From Me for YEARS and I Finally Found Out 😱 | AITA Drama",
        "My Wife Did This Behind My Back and I'm Still Not Over It | Reddit AITA",
    ]),
    (["money", "cash", "stole", "loan", "debt"], [
        "She Took Everything and Thought I'd Stay Silent — She Was Wrong 😤 | AITA",
        "I Did the Math and Finally SNAPPED | Reddit Drama AITA",
    ]),
    (["party", "invite", "birthday", "christmas"], [
        "They Left Me Out and Then Had the Nerve to Be Upset | Reddit AITA",
        "I Wasn't Invited and I Made Sure They Knew It 😤 | AITA Drama",
    ]),
    (["secret", "lied", "hiding", "truth"], [
        "The Truth Finally Came Out and NOBODY Was Ready For It 😱 | Reddit AITA",
        "She Was Hiding This the Whole Time and I Am FLOORED | AITA Drama",
    ]),
    (["family"], [
        "This Family Drama Has EVERYONE Divided and I Need YOUR Verdict | AITA",
        "My Whole Family is Against Me — But Was I Really Wrong? | Reddit AITA",
    ]),
]

# Generic pool used when no keyword matches
_GENERIC_TITLES = [
    "Nobody Saw This Coming 😱 and I'm Still Processing It | Reddit AITA Drama",
    "I Said What I Said and I'm Not Sorry 😤 | Reddit Drama AITA",
    "The Truth Came Out and EVERYTHING Changed — Who's Wrong Here? | AITA",
    "They Thought I'd Stay Silent… They Were WRONG | Reddit Drama AITA",
    "This Drama Has EVERYONE Divided and I Need Your Verdict | AITA Drama",
    "I Did the Thing Nobody Expected and Now the Family is SPLIT | AITA",
    "She Crossed a Line I Can't Come Back From 😤 | Reddit AITA Drama",
]


def _make_title(story_seed: str) -> str:
    s = story_seed.lower()
    for keywords, pool in _TITLE_POOLS:
        if any(k in s for k in keywords):
            return random.choice(pool)
    return random.choice(_GENERIC_TITLES)


def _make_description(story_seed: str, title: str) -> str:
    tags = " ".join([
        "#AITA", "#RedditDrama", "#DramaDesk", "#RelationshipAdvice",
        "#FamilyDrama", "#Reddit", "#StoryTime", "#AmITheAsshole",
        "#Relationships", "#TrueStory", "#EntitledPeople", "#RedditStories",
        "#AITAReddit", "#DramaChannel", "#DailyDrama", "#RedditReading",
    ])
    return (
        f"{title}\n\n"
        f"Today on Drama Desk, we're diving into a story that has EVERYONE divided:\n"
        f'"{story_seed}"\n\n'
        f"Drop a ❤️ if you're on OP's side. Drop a 💀 if you think they went too far.\n"
        f"Comment your verdict — I read every single one.\n\n"
        f"⏱️ CHAPTERS\n"
        f"0:00 The Most Shocking Part First\n"
        f"0:30 The Full Story Begins\n"
        f"2:00 Things Start Going Wrong\n"
        f"3:30 The Big Confrontation\n"
        f"5:00 The Aftermath\n"
        f"6:00 Who's Really in the Wrong?\n\n"
        f"🔔 NEW drama story every single day — Subscribe so you never miss one!\n"
        f"👇 @DramaDeskChannel\n\n"
        f"{tags}"
    )


# ── Music finder ──────────────────────────────────────────────────────────────

def _find_music() -> str | None:
    import requests as _requests
    music_dir = os.path.join(os.path.dirname(__file__), "music")
    os.makedirs(music_dir, exist_ok=True)
    # Return cached track if present
    for f in os.listdir(music_dir):
        if f.lower().endswith((".mp3", ".wav", ".ogg", ".m4a", ".flac")):
            return os.path.join(music_dir, f)
    # ── 1. Try Jamendo (best free music API — cinematic/dramatic tracks) ────────
    jamendo_id = os.getenv("JAMENDO_CLIENT_ID", "")
    if jamendo_id:
        for tags in ["cinematic dramatic", "tension thriller", "emotional piano", "suspense ambient", "dramatic orchestral"]:
            try:
                resp = _requests.get(
                    "https://api.jamendo.com/v3.0/tracks/",
                    params={
                        "client_id": jamendo_id,
                        "format": "json",
                        "limit": 20,
                        "tags": tags,
                        "audioformat": "mp32",
                        "audiodlformat": "mp32",
                    },
                    timeout=15,
                )
                if resp.status_code != 200:
                    continue
                tracks = resp.json().get("results", [])
                tracks = [t for t in tracks if t.get("audiodownload_allowed") and t.get("audiodownload")]
                if not tracks:
                    continue
                track = random.choice(tracks[:10])
                track_path = os.path.join(music_dir, f"jamendo_{track['id']}.mp3")
                r = _requests.get(track["audiodownload"], timeout=60, stream=True)
                if r.status_code == 200:
                    with open(track_path, "wb") as f_out:
                        for chunk in r.iter_content(chunk_size=65536):
                            f_out.write(chunk)
                    if os.path.getsize(track_path) > 50_000:
                        print(f"[music] Jamendo: '{track.get('name', tags)}' by {track.get('artist_name', '?')}")
                        return track_path
                    os.remove(track_path)   # too small, bad download
            except Exception as e:
                print(f"[music] Jamendo failed for '{tags}': {e}")
                continue
    else:
        print("[music] No JAMENDO_CLIENT_ID — get a free key at devportal.jamendo.com")

    # ── 2. Fallback: Pixabay Audio ────────────────────────────────────────────
    api_key = os.getenv("PIXABAY_API_KEY", "")
    if not api_key:
        print("[music] No music found — drop an MP3 into the music/ folder")
        return None
    queries = ["dramatic cinematic", "tension thriller", "emotional piano strings", "suspense background"]
    for q in queries:
        try:
            resp = _requests.get(
                "https://pixabay.com/api/",
                params={"key": api_key, "q": q, "media_type": "music", "per_page": 10},
                timeout=15,
            )
            if resp.status_code != 200:
                continue
            hits = resp.json().get("hits", [])
            random.shuffle(hits)
            for hit in hits:
                url = hit.get("previewURL", "")
                if not url:
                    continue
                track_path = os.path.join(music_dir, f"drama_bg_{q.split()[0]}.mp3")
                r = _requests.get(url, timeout=30)
                if r.status_code == 200 and len(r.content) > 10_000:
                    with open(track_path, "wb") as f_out:
                        f_out.write(r.content)
                    print(f"[music] Downloaded: {os.path.basename(track_path)}")
                    return track_path
        except Exception as e:
            print(f"[music] Auto-download failed for '{q}': {e}")
    print("[music] No background music found — add an MP3 to music/ folder")
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
    generate_thumbnail(
        title, thumb_path, video_path, style="drama",
        story_seed=story_seed,
        pexels_key=os.getenv("PEXELS_API_KEY"),
    )

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
