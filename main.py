"""
main.py — Kwentong Multo pipeline orchestrator.

Daily flow:
  1. Pick horror story seed from rotating Filipino category
  2. Generate original Tagalog horror script via OpenRouter
  3. Synthesize multi-voice TTS audio (Edge TTS — Filipino voices)
  4. Render 1920x1080 YouTube video with Pexels B-roll + subtitles
  5. Generate horror-style thumbnail
  6. Upload to YouTube

Run manually:
    python main.py
    python main.py --seed "Nakita ko ang aswang sa aming kapitbahay isang gabi"
    python main.py --no-upload
"""

import os
import json
import random
import re
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from config import (
    CHANNEL_NAME, UPLOAD_TAGS, UPLOAD_PRIVACY, UPLOAD_CATEGORY, SCENE_KEYWORDS
)
from trending import get_trending_drama_seed, is_title_used, save_used_title, append_video_log
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
        "gubat":      ["dark forest night", "foggy forest"],
        "ilog":       ["river night dark", "dark water"],
        "bahay":      ["dark house interior", "abandoned house"],
        "ospital":    ["hospital corridor dark", "hospital night"],
        "paaralan":   ["empty school corridor", "dark school"],
        "kwarto":     ["dark bedroom", "dim room"],
        "baryo":      ["rural village night", "tropical village dark"],
        "abroad":     ["city night street", "dark apartment"],
        "gabi":       ["dark night", "moonlit forest"],
        "bundok":     ["dark mountain", "foggy forest path"],
        "simbahan":   ["church dark interior", "old church night"],
        "default":    ["dark forest night", "foggy path", "abandoned building"],
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
    (["aswang", "manananggal", "capiz"], [
        "Nakita Ko ang Aswang — Totoo ang Mga Alamat ng Aming Baryo 😱 | Kwentong Multo",
        "Ang Lihim ng Aming Kapit-Bahay ay Aswang Pala 😱 | Horror Story Tagalog",
        "Kapre, Aswang, at ang Gabi na Magpakailanman Kong Aalalahanin | Kwentong Multo",
    ]),
    (["multo", "ghost", "white lady", "patay"], [
        "Ang Multo na Hindi Alam na Patay Na Siya 👻 | Kwentong Multo Tagalog",
        "White Lady sa Aming Bahay — Hindi Ito Alamat 😱 | True Horror Story",
        "Nakita Ko ang Aking Namatay na Lola sa Salamin 😱 | Kwentong Horror",
    ]),
    (["ofw", "abroad", "japan", "hong kong", "dubai", "saudi"], [
        "OFW Horror Story — May Sumusunod sa Akin Mula sa Pilipinas 😱 | Kwentong Multo",
        "Ang Aking Kwarto sa Abroad ay May Naninirahan na Hindi Ko Nakita | Horror",
        "Nag-abroad Ako at Natuklasan Ko ang Pinaka-Nakakatakot na Bagay 👻 | OFW Horror",
    ]),
    (["paaralan", "eskwelahan", "school", "kolehiyo", "unibersidad"], [
        "Ang Multo sa Aming Eskwelahan — May Kaklase Kaming Hindi Tao 😱 | Horror Tagalog",
        "Ang Kwarto 217 ng Aming Unibersidad ay Bawal Pumasok — Natuklasan Ko Kung Bakit | Horror",
        "Namatay ang Aming Kaklase Ngunit Patuloy Siyang Dumadalo sa Klase 👻 | Kwentong Multo",
    ]),
    (["ospital", "hospital", "nurse", "doktor"], [
        "Nagtatrabaho Bilang Nurse — Ang Pasyente sa Kwarto 404 ay Hindi Naka-Admit 😱 | Horror",
        "Ang Ospital na Ito ay May Lihim na Walang Gustong Ibahagi | Kwentong Multo",
        "Ang Morgue ng Aming Ospital ay May Kakaibang Gawi 👻 | True Hospital Horror Story",
    ]),
    (["probinsya", "baryo", "batangas", "ilocos", "visayas", "laguna"], [
        "Ang Baryo ng Aming Pamilya ay May Lihim na Tatlong Henerasyon Nang Inililihim 😱",
        "Ang Daan ng Patay sa Aming Probinsya — Natuklasan Ko Kung Bakit | Kwentong Multo",
        "Natulog Kami sa Lumang Bahay sa Probinsya — Hindi Kami Nag-iisa 👻 | Horror Tagalog",
    ]),
    (["engkanto", "kapre", "tikbalang", "duwende", "dwende"], [
        "Ang Kapre sa Puno ng Balete — Naniwala Ako na Alamat Lamang Ito 😱 | Kwentong Multo",
        "Naligaw Kami sa Gubat at ang Duwende ang Nagligtas Sa Amin | Filipino Horror",
        "Ang Engkanto ng Aming Ilog ay Naghingi ng Kapalit 👻 | Kwentong Multo Tagalog",
    ]),
    (["pamilya", "lola", "lolo", "ninuno", "curse"], [
        "Ang Sumpa ng Aming Pamilya — Ikinuwento ng Aking Lola Bago Siya Pumanaw 😱",
        "May Sumusunod sa Aming Lipi na Mula sa Kasalanan ng Aming Ninuno | Horror",
        "Ang Lumang Baul na Hindi Dapat Buksan — Ngunit Binuksan Namin 👻 | Kwentong Multo",
    ]),
    (["panaginip", "paranormal", "premonisyon"], [
        "Paulit-Ulit Kong Nangangarap ng Parehong Babae — Ngayon ay Natuklasan Ko Kung Sino Siya 😱",
        "Ang Aking Asawa ay Nagsasalita Habang Natutulog — Hindi Niya Ito Naalala 👻 | Horror",
        "May Mga Larawang Hindi Ko Kinuha sa Aking Telepono — Nasa Loob ng Aming Bahay 😱",
    ]),
    (["urban", "bgc", "makati", "quezon", "maynila", "manila", "lrt", "mrt"], [
        "Ang Elevator ng Aming Opisina ay Palaging Humihinto sa Ikapitong Palapag 😱 | Urban Legend",
        "Ang White Lady ng Balete Drive — Napatunayan Ko Ito Isang Gabi 👻 | Kwentong Multo",
        "Ang LRT Station na Aming Ginagamit Araw-Araw ay May Lihim | Horror Tagalog",
    ]),
]

_GENERIC_TITLES = [
    "Nakaranas Ako ng Bagay na Hindi Ko Kayang Ipaliwanag 😱 | Kwentong Multo Tagalog",
    "Ang Pinakanakakatakot na Gabi ng Aking Buhay 👻 | True Horror Story Philippines",
    "Hindi Ako Naniniwala sa Multo Noon — Hanggang sa Mangyari Ito Sa Akin 😱 | Kwentong Horror",
    "Totoo Ba Ito? Ang Karanasang Hindi Ko Malilimutan 👻 | Kwentong Multo",
    "Ang Lihim ng Aming Lugar na Ilang Taon Ko Nang Iniingatan 😱 | Horror Story Tagalog",
    "Wala Akong Makausap — Dahil Sila ay Patay Na 👻 | Kwentong Multo Philippines",
]


def _make_title(story_seed: str) -> str:
    """Generate a unique viral Tagalog horror title via LLM, fall back to keyword pools."""
    from config import get_openrouter_keys
    api_keys = get_openrouter_keys()
    if api_keys:
        prompt = (
            f'Gumawa ng ISANG YouTube title para sa Tagalog horror video tungkol sa kwentong ito:\n"{story_seed}"\n\n'
            "Mga Patakaran:\n"
            "- 50-80 character ang kabuuan\n"
            "- Tagalog ang salita (Filipino)\n"
            "- Magsimula sa nakakatakot na hook — tulad ng: Nakita Ko, Natuklasan Ko, Hindi Ko Malilimutan\n"
            "- Kasama ang ISANG emoji (😱 👻 😨 😐 o 🔊)\n"
            "- Tapusin sa | Kwentong Multo o | Horror Tagalog\n"
            "- I-output LAMANG ang title, walang iba, walang quotes"
        )
        for key_idx, api_key in enumerate(api_keys):
            key_label = f"key{key_idx + 1}"
            for _attempt in range(3):
                try:
                    import requests as _req
                    resp = _req.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                        json={
                            "model": "google/gemini-2.5-flash",
                            "messages": [{"role": "user", "content": prompt}],
                            "max_tokens": 80,
                            "temperature": 1.0,
                        },
                        timeout=15,
                    )
                    if resp.status_code in (401, 402, 403):
                        print(f"[title] {key_label} auth/credit error — trying next key")
                        break
                    if resp.status_code == 429:
                        print(f"[title] {key_label} rate limited — trying next key")
                        break
                    if resp.status_code == 200:
                        title = resp.json()["choices"][0]["message"]["content"].strip().strip('"').strip("'")
                        if 45 <= len(title) <= 100 and not is_title_used(title):
                            print(f"[title] LLM {key_label} (attempt {_attempt+1}): {title}")
                            return title
                        elif is_title_used(title):
                            print(f"[title] Title already used, retrying...")
                except Exception as e:
                    print(f"[title] {key_label} failed, using pool: {e}")
                    break
    # fallback to keyword pools (pick unused variant)
    s = story_seed.lower()
    for keywords, pool in _TITLE_POOLS:
        if any(k in s for k in keywords):
            unused = [t for t in pool if not is_title_used(t)]
            if unused:
                return random.choice(unused)
            return random.choice(pool)  # all used — allow repeat from pool
    unused_generic = [t for t in _GENERIC_TITLES if not is_title_used(t)]
    return random.choice(unused_generic) if unused_generic else random.choice(_GENERIC_TITLES)


def _make_description(story_seed: str, title: str) -> str:
    hook = story_seed[:150] if len(story_seed) > 150 else story_seed
    hashtags = (
        "#KwentongMulto #HorrorTagalog #PinoyHorror #KwentongHorror "
        "#TotoonaKwento #AswangStory #MultoPhilippines #HorrorStoryPhilippines "
        "#ScaryStories #TruePinoyHorror #OFWHorror #PinoyCreepypasta "
        "#PhilippineHorror #TrueHorrorStory #KwentongSindak "
        "#nakakatakot #multo #aswang #engkanto #filipinohorror"
    )
    return (
        f"😱 {hook}\n"
        f"Mag-comment ng 😱 kung naniniwala ka, o 💀 kung sa tingin mo ay kathang-isip lamang.\n\n"
        f"Maligayang pagdating sa Kwentong Multo — ang channel ng mga totoong karanasan "
        f"ng mga Pilipino sa mga bagay na hindi maipaliwanag. Aswang, multo, engkanto, "
        f"at mga misteryong mula sa ating sariling kultura. "
        f"Pakinggan hanggang sa katapusan — maaaring mayroon ka ring katulad na karanasan.\n\n"
        f"👇 IBOTO MO:\n"
        f"😱 = Naniniwala ako sa kwento\n"
        f"💀 = Kathang-isip lamang ito\n"
        f"🤔 = Hindi ako sigurado\n\n"
        f"⏱️ MGA KABANATA\n"
        f"0:00 Ang Pinaka-Nakakatakot na Sandali\n"
        f"0:30 Ang Buong Kwento\n"
        f"2:00 Nagsimulang Maging Kakaiba\n"
        f"3:30 Ang Pinaka-Nakakatakot na Bahagi\n"
        f"5:00 Ang Nangyari Pagkatapos\n"
        f"6:30 Totoo Ba Ito?\n\n"
        f"🔔 Mag-subscribe at pindutin ang bel — bagong kwento ARAW-ARAW!\n"
        f"👍 I-like kung nanatili ka hanggang sa katapusan\n"
        f"📢 I-share sa iyong mga kaibigan na mahilig sa kwentong multo\n\n"
        f"{hashtags}"
    )


# ── Music finder ──────────────────────────────────────────────────────────────

def _find_music() -> str | None:
    import requests as _requests
    music_dir = os.path.join(os.path.dirname(__file__), "music")
    os.makedirs(music_dir, exist_ok=True)

    # Return random track from cached pool (variety between videos)
    cached = [
        os.path.join(music_dir, f)
        for f in os.listdir(music_dir)
        if f.lower().endswith((".mp3", ".wav", ".ogg", ".m4a", ".flac"))
    ]
    if len(cached) >= 3:
        return random.choice(cached)

    # ── Build a pool of 5 dramatic piano tracks via Jamendo ──────────────────
    # All Jamendo tracks are CC-licensed (free for YouTube use).
    # We search specifically for piano + emotional/cinematic mood tags.
    POOL_TARGET = 5
    jamendo_id = os.getenv("JAMENDO_CLIENT_ID", "")
    if jamendo_id:
        piano_searches = [
            {"fuzzytags": "piano dramatic"},
            {"fuzzytags": "piano cinematic"},
            {"fuzzytags": "piano melancholic"},
            {"fuzzytags": "piano sad emotional"},
            {"tags": "piano"},
        ]
        for search_params in piano_searches:
            if len(cached) >= POOL_TARGET:
                break
            try:
                resp = _requests.get(
                    "https://api.jamendo.com/v3.0/tracks/",
                    params={
                        "client_id": jamendo_id,
                        "format": "json",
                        "limit": 20,
                        "orderby": "popularity_total",
                        "audioformat": "mp32",
                        "audiodlformat": "mp32",
                        **search_params,
                    },
                    timeout=15,
                )
                if resp.status_code != 200:
                    continue
                tracks = resp.json().get("results", [])
                tracks = [t for t in tracks if t.get("audiodownload_allowed") and t.get("audiodownload")]
                # Shuffle top 10 so each run picks something different
                pool = tracks[:10]
                random.shuffle(pool)
                for track in pool:
                    if len(cached) >= POOL_TARGET:
                        break
                    track_path = os.path.join(music_dir, f"jamendo_{track['id']}.mp3")
                    if os.path.exists(track_path):
                        cached.append(track_path)
                        continue
                    r = _requests.get(track["audiodownload"], timeout=60, stream=True)
                    if r.status_code == 200:
                        with open(track_path, "wb") as f_out:
                            for chunk in r.iter_content(chunk_size=65536):
                                f_out.write(chunk)
                        if os.path.getsize(track_path) > 50_000:
                            print(f"[music] Downloaded: '{track.get('name')}' by {track.get('artist_name')} (CC license)")
                            cached.append(track_path)
                        else:
                            os.remove(track_path)
            except Exception as e:
                print(f"[music] Jamendo search failed: {e}")
                continue
    else:
        print("[music] No JAMENDO_CLIENT_ID — get a free key at devportal.jamendo.com")

    if cached:
        return random.choice(cached)

    print("[music] No music found — drop a dramatic piano MP3 into the music/ folder")
    return None


# ── Telegram notifier ───────────────────────────────────────────────────────────

def _notify_telegram(message: str) -> None:
    """Send a Telegram notification. Silently skips if env vars are missing."""
    token   = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    import urllib.request
    url  = f"https://api.telegram.org/bot{token}/sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": message, "parse_mode": "HTML"}).encode()
    req  = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=10)
        print("[telegram] Notification sent")
    except Exception as e:
        print(f"[telegram] Notification failed: {e}")


# ── YouTube uploader ──────────────────────────────────────────────────────────

def _upload_youtube(video_path: str, title: str, description: str, thumb_path: str = None) -> str | None:
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
                "title":                title[:100],
                "description":          description[:5000],
                "tags":                 UPLOAD_TAGS,
                "categoryId":           UPLOAD_CATEGORY,
                "defaultLanguage":      "fil",
                "defaultAudioLanguage": "fil",
            },
            "status": {
                "privacyStatus":           UPLOAD_PRIVACY,
                "selfDeclaredMadeForKids": False,
                "madeForKids":             False,
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

        # Set thumbnail on the uploaded video
        if thumb_path and os.path.exists(thumb_path) and video_id:
            try:
                youtube.thumbnails().set(
                    videoId=video_id,
                    media_body=MediaFileUpload(thumb_path, mimetype="image/png"),
                ).execute()
                print("[youtube] Thumbnail set")
            except Exception as e:
                print(f"[youtube] Thumbnail upload failed: {e}")

        return url

    except Exception as e:
        print(f"[youtube] Upload failed: {e}")
        return None


# ── Main pipeline ─────────────────────────────────────────────────────────────

def create_drama_video(
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
    tts = generate_drama_audio(script, tts_dir)
    dur = tts["total_duration"]
    print(f"  Duration: {dur:.1f}s ({dur/60:.1f} min) | {len(tts['segments'])} segments")

    # ── 4. Video render ───────────────────────────────────────────────────────
    print("\n[4/6] Rendering video...")
    scene_tags = _extract_scene_tags(script)
    video_path = os.path.join(output_dir, "drama_video.mp4")
    render_drama_video(
        audio_path=tts["audio_path"],
        captions=tts["captions"],
        segments=tts["segments"],
        output_path=video_path,
        scene_tags=scene_tags,
        music_path=None,
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
        url = _upload_youtube(video_path, title, description, thumb_path=thumb_path)
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

    # ── Log title + video record ───────────────────────────────────────────────
    save_used_title(title)
    append_video_log({
        "date":             timestamp,
        "seed":             story_seed,
        "title":            title,
        "youtube_url":      url,
        "duration_seconds": dur,
    })

    print(f"\n{banner}")
    print(f"DONE  →  {video_path}")
    if url:
        print(f"YouTube →  {url}")
    print(f"{banner}\n")

    return result


# ── CLI entry point ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Kwentong Multo — daily horror video generator")
    parser.add_argument("--seed",      type=str,  default=None, help="Custom story seed")
    parser.add_argument("--no-upload", action="store_true",     help="Skip YouTube upload")
    parser.add_argument("--output",    type=str,  default=None, help="Output directory")
    args = parser.parse_args()

    try:
        result = create_drama_video(
            story_seed=args.seed,
            output_dir=args.output,
            upload=not args.no_upload,
        )
        repo = os.getenv("GITHUB_REPOSITORY", "local")
        yt_url = result.get("youtube_url")
        if yt_url:
            _notify_telegram(
                f"\u2705 <b>Kwentong Multo — Na-upload na!</b>\n\n"
                f"\U0001f47b {result['title']}\n"
                f"\U0001f517 {yt_url}\n\n"
                f"\U0001f4e6 Repo: {repo}"
            )
        elif not args.no_upload:
            _notify_telegram(
                f"\u26a0\ufe0f <b>Kwentong Multo — Na-render pero hindi na-upload sa YouTube.</b>\n"
                f"Tingnan ang Actions logs para sa detalye.\n\n"
                f"\U0001f4e6 Repo: {repo}"
            )
    except Exception as exc:
        repo = os.getenv("GITHUB_REPOSITORY", "local")
        _notify_telegram(
            f"\u274c <b>Kwentong Multo — Pipeline failed:</b>\n\n"
            f"<code>{exc}</code>\n\n"
            f"\U0001f4e6 Repo: {repo}"
        )
        raise
