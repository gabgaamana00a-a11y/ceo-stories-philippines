"""Central config for Drama Desk — AITA/Reddit drama YouTube channel."""

CHANNEL_NAME = "Drama Desk"
CHANNEL_NICHE = "aita_drama"

# ── YouTube upload ────────────────────────────────────────────────────────────
UPLOAD_PRIVACY  = "public"   # public | unlisted | private
UPLOAD_CATEGORY = "22"       # 22 = People & Blogs (best for AITA narrator format)
UPLOAD_TAGS = [
    # Exact-match high-volume searches
    "aita", "am i the asshole", "am i wrong", "reddit aita", "aita reddit",
    "reddit stories", "reddit drama", "reddit story time", "best reddit stories",
    # Long-tail relationship terms
    "relationship advice", "relationship drama", "family drama",
    "mother in law drama", "cheating story", "toxic relationship story",
    # Format/channel terms
    "storytime", "true story", "drama channel", "drama desk",
    "reddit reading", "reddit narration", "aita stories 2025",
    # Discovery terms
    "entitled people", "viral reddit", "shocking story",
    "reddit update", "unbelievable story", "real story",
]

# ── Video format — 16:9 landscape for YouTube long-form ──────────────────────
VIDEO_WIDTH  = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS    = 30

# Target script length for a 5-10 minute video
SCRIPT_MIN_WORDS = 700
SCRIPT_MAX_WORDS = 1200

# ── TTS voices (Kokoro-82M — open-weight, emotional, runs on CPU/GPU) ────────
# Grade A/A- voices chosen for maximum expressiveness.
# Local: GPU-accelerated via PyTorch. GitHub Actions: CPU via ONNX.
VOICES = {
    "NARRATOR":     "af_heart",    # Grade A — warmest, most emotional female narrator
    "OP":           "af_bella",    # Grade A- — passionate, great for personal monologues
    "OP_MALE":      "am_michael",  # Grade B — authoritative male storyteller
    "CHARACTER_F":  "af_nicole",   # Grade B- — distinctive, opinionated
    "CHARACTER_M":  "am_fenrir",   # Grade B — dramatic deep male
    "CHARACTER_F2": "af_aoede",    # Grade B — warm secondary female
    "CHARACTER_M2": "am_puck",     # Grade B — lighter younger male
    # Aliases used by LLM-generated scripts
    "HER":          "af_nicole",
    "HIM":          "am_fenrir",
    "HER_FRIEND":   "af_aoede",
    "HIS_FRIEND":   "am_puck",
}

# Human-readable display names shown as on-screen speaker labels
SPEAKER_LABELS = {
    "NARRATOR":     "NARRATOR",
    "OP":           "OP",
    "OP_MALE":      "OP",
    "CHARACTER_F":  "HER",
    "CHARACTER_M":  "HIM",
    "CHARACTER_F2": "HER FRIEND",
    "CHARACTER_M2": "HIS FRIEND",
}

# ── Pexels B-roll scene mapping ───────────────────────────────────────────────
# Maps detected scene keywords in script → Pexels search queries
SCENE_KEYWORDS = {
    "restaurant":   ["restaurant dining", "cafe people"],
    "kitchen":      ["kitchen cooking", "home kitchen"],
    "bedroom":      ["bedroom interior", "home room"],
    "office":       ["office workplace", "business meeting"],
    "wedding":      ["wedding ceremony", "bride"],
    "phone":        ["smartphone texting", "phone call"],
    "family":       ["family dinner", "family gathering"],
    "outdoor":      ["city street people", "park outdoor"],
    "argument":     ["couple conflict", "people arguing"],
    "couple":       ["couple relationship", "man woman"],
    "money":        ["money finance", "cash bills"],
    "default":      ["cinematic people", "dramatic indoor", "living room"],
}

# ── Reddit drama subreddits (for trending story seeds) ───────────────────────
DRAMA_SUBREDDITS = [
    "AmItheAsshole",
    "AITAH",
    "relationship_advice",
    "entitledparents",
    "tifu",
    "TrueOffMyChest",
    "offmychest",
    "weddingshaming",
    "JUSTNOMIL",
]

# ── Schedule ──────────────────────────────────────────────────────────────────
SCHEDULE_HOUR   = 14   # 2 PM UTC = 9 AM EST / 10 AM EDT
SCHEDULE_MINUTE = 0
