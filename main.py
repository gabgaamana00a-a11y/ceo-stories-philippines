"""
main.py — CEO Stories Philippines pipeline orchestrator.

Daily flow:
  1. Pick CEO success story seed from rotating Filipino category
  2. Generate original Tagalog CEO story script via OpenRouter
  3. Synthesize multi-voice TTS audio (Edge TTS — Filipino voices)
  4. Download real B-roll videos from Pexels/Pixabay (success-themed)
  5. Render 1920x1080 YouTube video with subtitles over real video
  6. Generate success-style thumbnail
  7. Upload to YouTube

Run manually:
    python main.py
    python main.py --seed "Isang CEO na nagsimula sa pagtitinda ng fish balls"
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
        "negosyo":    ["office building modern", "business meeting"],
        "opisina":    ["corporate office", "modern workplace"],
        "probinsya":  ["rural philippines village", "simple life farming"],
        "lungsod":    ["manila city skyline", "makati business"],
        "bahay":      ["modern house interior", "filipino home"],
        "tindahan":   ["small store business", "market philippines"],
        "pamilya":    ["filipino family", "family gathering"],
        "paaralan":   ["students studying", "school philippines"],
        "abroad":     ["airport travel", "modern city abroad"],
        "factory":    ["factory worker philippines", "manufacturing"],
        "trabaho":    ["people working office", "corporate work"],
        "construction": ["construction worker", "building construction"],
        "pera":       ["money business", "financial success"],
        "default":    ["successful businessman", "modern office", "city skyline philippines"],
    }
    for keyword, pexels_kws in scene_map.items():
        if keyword in lower:
            tags.extend(pexels_kws)
    if not tags:
        tags = list(SCENE_KEYWORDS["default"])
    return list(dict.fromkeys(tags))[:6]   # deduplicated, max 6


# ── Title & description ───────────────────────────────────────────────────────

# Keyword-matched punchy title pools — no raw seed text dumped in.
# Top channels use short emotional hooks, not full sentences.
_TITLE_POOLS = [
    (["ceo", "corporation", "korporasyon", "presidente", "executive"], [
        "Mula sa Wala, Naging CEO — Ang Kanyang Kwento ay Hindi Kapani-paniwala 💼 | CEO Stories",
        "Siya ay Dati Mahirap — Ngayon CEO na ng Isang Multi-Million Company 🏆 | Tagalog Inspirasyon",
        "Ang CEO na Dating Nakatira sa Bangketa — Hindi Mo Ito Akalain 💪 | Kwento ng Tagumpay",
    ]),
    (["negosyo", "business", "entrepreneur", "startup", "tindahan"], [
        "P1,000 Lang ang Puhunan — Ngayon ay Millionaire Na Siya 💰 | CEO Stories Philippines",
        "Mula sa Maliit na Tindahan — Nagtayo ng Business Empire 🏢 | Inspirational Story Tagalog",
        "Ang Sikreto ng Tagumpay ng Negosyanteng Nagsimula sa Wala 🔥 | Kwento ng CEO",
    ]),
    (["ofw", "abroad", "dubai", "japan", "hongkong", "saudi", "canada", "taiwan"], [
        "OFW na Naging CEO — Mula sa Pagiging Katulong Hanggang sa Pagmamay-ari ng Kumpanya ✈️ | CEO Stories",
        "Nag-OFW Siya ng 10 Taon — Umuwi at Nagtayo ng Business Empire 🇵🇭 | Inspirasyon ng Pinoy",
        "Ang OFW na Hindi Sumuko — Ngayon ay CEO na ng Kanyang Sariling Kumpanya 💼 | Tagalog Success",
    ]),
    (["mahirap", "hirap", "walang pera", "bangketa", "tondo", "estero"], [
        "Galing sa Basurahan — Ngayon ay Multi-Millionaire Na Siya 😱 | CEO Story Tagalog",
        "Walang Makain Kundi Kanin at Asin — Ngayon ay CEO Na 🔥 | Kwento ng Tagumpay",
        "Mula sa Kahirapan Tungo sa Tagumpay — Hindi Ka Maniniwala sa Kanyang Kwento 💪 | CEO Stories",
    ]),
    (["pamilya", "nanay", "tatay", "ina", "ama", "anak", "lola", "lolo"], [
        "Iniwan ng Asawa Dahil sa Kahirapan — Ngayon ay CEO Na at Masaya 💪 | CEO Stories Philippines",
        "Ang Anak na Nagsakripisyo para sa Pamilya — Ngayon ay CEO Na 🏆 | Tagalog Inspirasyon",
        "Pamilya Sila na Nagsimula sa Wala — Ngayon ay May Business Empire 👨‍👩‍👧‍👦 | CEO Stories",
    ]),
    (["probinsya", "baryo", "batangas", "ilocos", "visayas", "laguna", "bukid"], [
        "Taga-Probinsya Lang Siya — Ngayon ay CEO Ng Isang Malaking Korporasyon 🏢 | CEO Stories",
        "Mula sa Baryo Tungo sa Boardroom — Ang Kwento ng Isang Batang Probinsyano 🌾 | Tagalog Success",
        "Ang Batang Taga-Probinsya na Nagpatunay na Walang неможливо 💪 | CEO Stories Philippines",
    ]),
    (["bagsak", "fail", "scam", "naloko", "nawalan", "bangkarote", "sumuko"], [
        "Tatlong Beses na Bumagsak — Pero Hindi Sumuko — Ngayon ay CEO Na 🔥 | CEO Stories",
        "Nawalan ng Lahat — Nagsimula Ulit — Ngayon ay Multi-Millionaire Na 💰 | Tagalog Inspirasyon",
        "Ang Kwento ng Pagkabigo na Naging Tagumpay — Hindi Ka Maniniwala 📖 | CEO Stories Philippines",
    ]),
    (["tech", "startup", "app", "software", "programmer", "code", "digital"], [
        "College Dropout na Nag-Code sa Internet Cafe — Ngayon ay CEO ng Tech Company 💻 | CEO Stories",
        "Mula sa Garahe Hanggang sa Unicorn — Ang Kwento ng Isang Tech CEO 🚀 | Tagalog Success",
        "Ang Programmer na Naging CEO — At Binili ang Dating Kumpanya Niya 💼 | CEO Stories Philippines",
    ]),
    (["revenge", "higanti", "iniwan", "niloko", "pinahiya", "tinanggal", "itinakwil"], [
        "Pinahiya ng Dating Boss — Ngayon ay CEO at Ang Boss ay Nag-Aapply sa Kanya 😱 | CEO Stories",
        "Niloko ng Business Partner — Nagtayo ng Mas Malaking Empire 💪 | Revenge CEO Story Tagalog",
        "Itinakwil ng Mayamang Pamilya — Naging Mas Mayaman Pa Kaysa sa Kanilang Lahat 🔥 | CEO Stories",
        "Tinanggal sa Trabaho — Nagtayo ng Karibal na Kumpanya — Binili ang Dating Kumpanya 🏢 | CEO Revenge",
        "Iniwan ng Fiance Dahil Mahirap — Naging Bilyonaryo — Bumili ng Diamond Ring 💍 | CEO Stories",
    ]),
    (["babae", "nanay", "ina", "babaeng ceo", "woman", "female"], [
        "Ang Babaeng CEO na Nagsimula sa Pagtitinda sa Palengke — Ngayon ay May Empire 👩‍💼 | CEO Stories",
        "Isang Ina na Nagsakripisyo para sa Anak — Ngayon ay CEO ng Malaking Kumpanya 💪 | Tagalog Inspirasyon",
        "Babaeng CEO na Hindi Nagsusungit — At Ang Kanyang Kwento ay Nakakaiyak 😢 | CEO Stories Philippines",
    ]),
]

_GENERIC_TITLES = [
    "Mula sa Wala Hanggang sa Yaman — Ang Kwento ng Tagumpay na Dapat Mong Malaman 💰 | CEO Stories",
    "Hindi Ka Maniniwala Kung Saan Siya Nagsimula — Ngayon CEO Na Siya 🔥 | Tagalog Success Story",
    "Ang Pinaka-Inspirational na Kwento ng CEO na Makikita Mo Ngayong Araw 💪 | CEO Stories Philippines",
    "Mula sa Hirap Tungo sa Tagumpay — Ang Kanyang Diskarte ay Hindi Kapani-paniwala 🏆 | CEO Stories",
    "Siya ay Wala — Ngayon ay Isa Nang CEO — Heto Ang Kanyang Sikreto 🤫 | Tagalog Inspirasyon",
    "Ang Batang Walang Pangarap — Ngayon ay CEO — Kung Paano Niya Binago ang Kanyang Buhay 📈 | CEO Stories",
]


def _make_title(story_seed: str) -> str:
    """Generate a unique viral Tagalog horror title via LLM, fall back to keyword pools."""
    from config import get_openrouter_keys
    api_keys = get_openrouter_keys()
    if api_keys:
        prompt = (
            f'Gumawa ng ISANG YouTube title para sa Tagalog CEO success story video tungkol sa kwentong ito:\n"{story_seed}"\n\n'
            "Mga Patakaran:\n"
            "- 50-80 character ang kabuuan\n"
            "- Tagalog ang salita (Filipino)\n"
            "- Magsimula sa nakaka-inspire na hook — tulad ng: Mula sa Wala, Galing sa Hirap, Isang CEO na\n"
            "- Kasama ang ISANG emoji (💼 💰 🔥 🏆 💪 o 📈)\n"
            "- Tapusin sa | CEO Stories o | Tagalog Success o | CEO Stories Philippines\n"
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
        "#CEOStories #TagalogSuccessStory #PinoyCEO #InspirasyonPinoy "
        "#RagsToRiches #SuccessStoryPhilippines #OFWSuccess #PinoyEntrepreneur "
        "#NegosyoStory #CEOPhilippines #MotivationTagalog #BusinessStory "
        "#MulaSaWala #TagumpayNgPinoy #CEO #SuccessMindset "
        "#SipagAtTiyaga #PinoyPride #EntrepreneurPhilippines #YamanStory"
    )
    return (
        f"💼 {hook}\n"
        f"Mag-comment ng 💪 kung na-inspire ka, o 🔥 kung gusto mo ng ganitong klaseng kwento!\n\n"
        f"Maligayang pagdating sa CEO Stories Philippines — ang channel ng mga totoong kwento "
        f"ng tagumpay ng mga Pilipino. Mula sa kahirapan, OFW, maliit na negosyo — "
        f"hanggang sa pagiging CEO at pagtatayo ng business empire. "
        f"Patunayan na ang Pilipino ay kayang magtagumpay sa kabila ng lahat.\n\n"
        f"👇 IBOTO MO:\n"
        f"💪 = Na-inspire ako sa kwentong ito\n"
        f"🔥 = Gusto ko ng ganitong kwento araw-araw\n"
        f"🙏 = May katulad akong kwento\n\n"
        f"⏱️ MGA KABANATA\n"
        f"0:00 Ang Pinaka-Dramatikong Sandali\n"
        f"0:30 Ang Simula ng Kwento\n"
        f"2:00 Ang Pagsubok\n"
        f"3:30 Ang Pagbabago\n"
        f"5:00 Ang Tagumpay\n"
        f"6:30 Aral ng Kwento\n\n"
        f"🔔 Mag-subscribe at pindutin ang bel — bagong kwento ng inspirasyon ARAW-ARAW!\n"
        f"👍 I-like kung nainspire ka hanggang sa katapusan\n"
        f"📢 I-share sa iyong mga kaibigan na nangangailangan ng inspirasyon\n\n"
        f"{hashtags}"
    )


# ── Music finder ──────────────────────────────────────────────────────────────

def _find_music() -> str | None:
    """Find a CC-licensed background music track for CEO success stories.

    Uses the free Jamendo API to search for uplifting, inspirational,
    corporate cinematic tracks — all CC-licensed (free for YouTube).
    Returns path to a random cached track, or None.
    """
    import requests as _requests
    music_dir = os.path.join(os.path.dirname(__file__), "music")
    os.makedirs(music_dir, exist_ok=True)

    # Return random track from cached pool (variety between videos)
    cached = [
        os.path.join(music_dir, f)
        for f in os.listdir(music_dir)
        if f.lower().endswith((".mp3", ".wav", ".ogg", ".m4a", ".flac"))
        and not f.startswith("horror_")  # skip old horror music
    ]
    if len(cached) >= 5:
        return random.choice(cached)

    # ── Build a pool of 10 inspiring/success tracks via Jamendo ──────────────
    # All Jamendo tracks are CC-licensed (free for YouTube use).
    POOL_TARGET = 10
    jamendo_id = os.getenv("JAMENDO_CLIENT_ID", "")
    if jamendo_id:
        success_searches = [
            {"fuzzytags": "uplifting inspirational cinematic"},
            {"fuzzytags": "corporate inspirational motivational"},
            {"fuzzytags": "hopeful inspiring emotional"},
            {"tags": "cinematic"},
            {"fuzzytags": "success motivational uplifting"},
            {"fuzzytags": "inspiring corporate uplifting"},
            {"tags": "inspirational"},
        ]
        for search_params in success_searches:
            if len(cached) >= POOL_TARGET:
                break
            try:
                resp = _requests.get(
                    "https://api.jamendo.com/v3.0/tracks/",
                    params={
                        "client_id": jamendo_id,
                        "format": "json",
                        "limit": 30,
                        "orderby": "popularity_total",
                        "audioformat": "mp32",
                        "audiodlformat": "mp32",
                        "durationmin": 60,
                        **search_params,
                    },
                    timeout=15,
                )
                if resp.status_code != 200:
                    continue
                tracks = resp.json().get("results", [])
                tracks = [t for t in tracks
                          if t.get("audiodownload_allowed") and t.get("audiodownload")]
                # Shuffle top 15 so each run picks different tracks
                pool = tracks[:15]
                random.shuffle(pool)
                for track in pool:
                    if len(cached) >= POOL_TARGET:
                        break
                    track_id = track["id"]
                    # Skip if already cached
                    existing = [c for c in cached if f"jamendo_{track_id}" in c]
                    if existing:
                        continue
                    track_path = os.path.join(music_dir, f"jamendo_{track_id}.mp3")
                    try:
                        r = _requests.get(
                            track["audiodownload"], timeout=(8, 30), stream=True
                        )
                        if r.status_code == 200:
                            with open(track_path, "wb") as f_out:
                                for chunk in r.iter_content(chunk_size=65536):
                                    if chunk:
                                        f_out.write(chunk)
                            if os.path.getsize(track_path) > 50_000:
                                print(f"[music] Downloaded: '{track.get('name')}' "
                                      f"by {track.get('artist_name')} (CC license) "
                                      f"~{int(track.get('duration', 0))}s")
                                cached.append(track_path)
                            else:
                                os.remove(track_path)
                    except Exception as dl_err:
                        print(f"[music] Download failed for {track.get('name')}: {dl_err}")
                        if os.path.exists(track_path):
                            os.remove(track_path)
                        continue
            except Exception as e:
                print(f"[music] Jamendo search failed: {e}")
                continue
    else:
        print("[music] No JAMENDO_CLIENT_ID — get a free key at devportal.jamendo.com")

    if cached:
        chosen = random.choice(cached)
        print(f"[music] Using: {os.path.basename(chosen)}")
        return chosen

    print("[music] No music found — place MP3 files in the music/ folder")
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
    story_minutes: int = 10,
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
        print("\n[1/6] Fetching CEO success story seed...")
        story_seed = get_trending_drama_seed()
    print(f"  Seed: {story_seed[:85]}...")

    # ── 2. Script ─────────────────────────────────────────────────────────────
    print("\n[2/6] Generating CEO success script...")
    script = generate_drama_script(story_seed, target_minutes=story_minutes)
    script_path = os.path.join(output_dir, "script.txt")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script)

    # ── 3. TTS audio ──────────────────────────────────────────────────────────
    print("\n[3/6] Generating multi-voice TTS audio...")
    tts_dir = os.path.join(output_dir, "tts")
    tts = generate_drama_audio(script, tts_dir)
    dur = tts["total_duration"]
    print(f"  Duration: {dur:.1f}s ({dur/60:.1f} min) | {len(tts['segments'])} segments")

    # ── 4. Video render (real B-roll + subtitles) ─────────────────────────────
    print("\n[4/6] Rendering video with real B-roll + subtitles...")
    scene_tags = _extract_scene_tags(script)
    video_path = os.path.join(output_dir, "drama_video.mp4")
    render_drama_video(
        audio_path=tts["audio_path"],
        captions=tts["captions"],
        segments=tts["segments"],
        output_path=video_path,
        scene_tags=scene_tags,
        music_path=_find_music(),
    )

    # ── 5. Thumbnail ──────────────────────────────────────────────────────────
    print("\n[5/6] Generating success-style thumbnail...")
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
    parser = argparse.ArgumentParser(description="CEO Stories Philippines — success story video generator")
    parser.add_argument("--seed",      type=str,  default=None, help="Custom CEO story seed")
    parser.add_argument("--no-upload", action="store_true",     help="Skip YouTube upload")
    parser.add_argument("--output",    type=str,  default=None, help="Output directory")
    parser.add_argument("--long",      action="store_true",     help="Generate 30-min free story (no API costs)")
    parser.add_argument("--minutes",   type=int,  default=None, help="Custom story length in minutes")
    args = parser.parse_args()

    try:
        result = create_drama_video(
            story_seed=args.seed,
            output_dir=args.output,
            upload=not args.no_upload,
            story_minutes=args.minutes or (30 if args.long else 10),
        )
        repo = os.getenv("GITHUB_REPOSITORY", "local")
        yt_url = result.get("youtube_url")
        if yt_url:
            _notify_telegram(
                f"\u2705 <b>CEO Stories Philippines — Na-upload na!</b>\n\n"
                f"\U0001f4bc {result['title']}\n"
                f"\U0001f517 {yt_url}\n\n"
                f"\U0001f4e6 Repo: {repo}"
            )
        elif not args.no_upload:
            _notify_telegram(
                f"\u26a0\ufe0f <b>CEO Stories Philippines — Na-render pero hindi na-upload sa YouTube.</b>\n"
                f"Tingnan ang Actions logs para sa detalye.\n\n"
                f"\U0001f4e6 Repo: {repo}"
            )
    except Exception as exc:
        repo = os.getenv("GITHUB_REPOSITORY", "local")
        _notify_telegram(
            f"\u274c <b>CEO Stories Philippines — Pipeline failed:</b>\n\n"
            f"<code>{exc}</code>\n\n"
            f"\U0001f4e6 Repo: {repo}"
        )
        raise
