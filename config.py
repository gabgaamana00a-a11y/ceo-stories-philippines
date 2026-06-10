"""Central config for Kwentong Multo — Filipino horror & supernatural YouTube channel."""

CHANNEL_NAME = "Kwentong Multo"
CHANNEL_NICHE = "tagalog_horror"

# ── YouTube upload ────────────────────────────────────────────────────────────
UPLOAD_PRIVACY  = "public"   # public | unlisted | private
UPLOAD_CATEGORY = "22"       # 22 = People & Blogs
UPLOAD_TAGS = [
    # High-volume Tagalog horror searches
    "kwentong multo", "multo", "horror story tagalog", "kwentong horror",
    "tagalog horror stories", "kwentong aswang", "aswang story",
    "kwentong totoo", "true horror story", "pinoy horror",
    # Folklore creatures
    "aswang", "manananggal", "kapre", "tikbalang", "duwende",
    "engkanto", "white lady", "multo sa paaralan", "multo sa ospital",
    # Format/discovery terms
    "horror stories", "kwentong sindak", "nakakatakot na kwento",
    "pinoy scary stories", "philippine folklore", "urban legend",
    "ofw horror story", "probinsya horror",
    # Engagement terms
    "nakakatakot", "true story", "pinoy horror channel",
]

# ── Video format — 16:9 landscape for YouTube long-form ──────────────────────
VIDEO_WIDTH  = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS    = 30

# Target script length for a 8-12 minute video
SCRIPT_MIN_WORDS = 900
SCRIPT_MAX_WORDS = 1400

# ── TTS voices (Microsoft Edge TTS — free, Filipino language support) ─────────
# Uses edge-tts package. Only 2 Filipino neural voices available.
VOICES = {
    "NARRATOR":     "fil-PH-AngeloNeural",      # deep male narrator — ominous horror voice
    "OP":           "fil-PH-BlessicaNeural",   # female first-person storyteller
    "OP_MALE":      "fil-PH-AngeloNeural",      # male first-person storyteller
    "CHARACTER_F":  "fil-PH-BlessicaNeural",    # female character
    "CHARACTER_M":  "fil-PH-AngeloNeural",      # male character
    "CHARACTER_F2": "fil-PH-BlessicaNeural",    # secondary female
    "CHARACTER_M2": "fil-PH-AngeloNeural",      # secondary male
    # Aliases
    "SIYA_B":       "fil-PH-BlessicaNeural",
    "SIYA_L":       "fil-PH-AngeloNeural",
    "KAIBIGAN":     "fil-PH-AngeloNeural",
    "INA":          "fil-PH-BlessicaNeural",
    "AMA":          "fil-PH-AngeloNeural",
}

# Human-readable display names shown as on-screen speaker labels
SPEAKER_LABELS = {
    "NARRATOR":     "TAGAPAGSALAYSAY",
    "OP":           "KWENTISTA",
    "OP_MALE":      "KWENTISTA",
    "CHARACTER_F":  "SIYA",
    "CHARACTER_M":  "SIYA",
    "CHARACTER_F2": "KAIBIGAN",
    "CHARACTER_M2": "KAIBIGAN",
    "SIYA_B":       "SIYA",
    "SIYA_L":       "SIYA",
    "KAIBIGAN":     "KAIBIGAN",
    "INA":          "INA",
    "AMA":          "AMA",
}

# ── Pexels B-roll scene mapping (horror-themed) ───────────────────────────────
SCENE_KEYWORDS = {
    "gabi":         ["dark night forest", "scary night"],
    "bundok":       ["dark mountain forest", "foggy forest"],
    "probinsya":    ["rural philippines", "tropical forest night"],
    "bahay":        ["dark house interior", "abandoned house"],
    "ospital":      ["hospital corridor dark", "hospital night"],
    "paaralan":     ["empty school corridor", "dark school"],
    "gubat":        ["dark jungle forest", "foggy forest path"],
    "ilog":         ["river night", "dark water"],
    "baryo":        ["rural village night", "tropical village dark"],
    "abroad":       ["city night street", "dark apartment"],
    "kwarto":       ["dark bedroom", "dim room interior"],
    "kitchen":      ["dark kitchen", "dim kitchen interior"],
    "default":      ["dark forest night", "foggy path", "abandoned building"],
}

# ── Horror story categories for sustainable 365-day rotation ──────────────────
HORROR_CATEGORIES = [
    "aswang_folklore",      # aswang, manananggal, berberoka, sigbin
    "engkanto_spirits",     # engkanto, diwata, kapre, tikbalang, duwende
    "multo_ghost",          # white lady, school ghosts, house haunting
    "ofw_horror",           # overseas Filipino worker supernatural encounters
    "paaralan_horror",      # school/university ghost stories
    "ospital_horror",       # hospital ghost stories
    "probinsya_horror",     # province rural supernatural stories
    "urban_legend",         # Metro Manila / Cebu city urban legends
    "pamilya_horror",       # family supernatural/curse stories
    "panaginip_paranormal", # dreams, premonitions, paranormal
]

# ── Schedule (Philippine Standard Time UTC+8 = prime time 8-9 PM PST) ────────
SCHEDULE_HOUR   = 8    # 08:00 UTC = 4:00 PM PHT (Philippine Time, UTC+8)
SCHEDULE_MINUTE = 0
