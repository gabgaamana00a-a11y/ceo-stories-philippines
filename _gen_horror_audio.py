"""
_gen_horror_audio.py — Generate a rich horror ambient track via numpy synthesis.

Layers:
  1. Sub-bass beating drone  (30 + 31 Hz, creates 1 Hz eerie wobble)
  2. Tritone mid drone       (55 Hz + tritone 77.8 Hz) with slow tremolo
  3. Heartbeat pulse         (68 BPM double-thud, slightly slow = unsettling)
  4. High shimmer            (880 Hz, very faint, "held breath" tension)
  5. Filtered noise breath   (moving-average ~300 Hz, breathing envelope)

Post-processing via ffmpeg: double echo + low-pass.
Output: music/horror_ambient_loop.mp3  (4 minutes, 128kbps)
"""

import os, sys, subprocess, wave, shutil
import numpy as np

try:
    import imageio_ffmpeg
    FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG = shutil.which("ffmpeg") or "ffmpeg"

SR       = 44100
DURATION = 240          # 4 minutes
WAV_PATH = os.path.join("music", "_horror_raw.wav")
OUT_PATH = os.path.join("music", "horror_ambient_loop.mp3")

print("[audio] Synthesizing horror ambient...")

t = np.linspace(0, DURATION, SR * DURATION, endpoint=False, dtype=np.float32)

# ── Layer 1: Sub-bass beating drone ──────────────────────────────────────────
# Two close frequencies → 1 Hz beat frequency = slow eerie pulse in the chest
bass  = 0.38 * np.sin(2 * np.pi * 30.0 * t, dtype=np.float32)
bass += 0.28 * np.sin(2 * np.pi * 31.0 * t, dtype=np.float32)

# ── Layer 2: Tritone mid drone ────────────────────────────────────────────────
# Tritone = f * 2^(6/12) — the "devil's interval", psychologically unsettling
f0         = 55.0
f_tritone  = f0 * (2 ** (6 / 12))   # ~77.78 Hz
# Very slow 8-second swell tremolo
tremolo    = (0.55 + 0.45 * np.sin(2 * np.pi * 0.125 * t)).astype(np.float32)
mid        = tremolo * (
    0.22 * np.sin(2 * np.pi * f0        * t, dtype=np.float32) +
    0.15 * np.sin(2 * np.pi * f_tritone * t, dtype=np.float32)
)

# ── Layer 3: Heartbeat pulse ──────────────────────────────────────────────────
# 68 BPM (slightly below resting) = subtle dread without panic
period  = 60.0 / 68.0
beat_t  = (t % period).astype(np.float32)

thud1   = np.where(beat_t < 0.060,
                   np.sin(np.pi * beat_t / 0.060) ** 2, 0.0).astype(np.float32)
t2s, t2d = 0.210, 0.055
thud2   = np.where(
    (beat_t >= t2s) & (beat_t < t2s + t2d),
    0.65 * (np.sin(np.pi * (beat_t - t2s) / t2d) ** 2),
    0.0,
).astype(np.float32)

heartbeat = 0.42 * (thud1 + thud2) * np.sin(2 * np.pi * 75 * t, dtype=np.float32)

# ── Layer 4: High shimmer ─────────────────────────────────────────────────────
# Very slow 14-second swell at 880 Hz — tinnitus-like, builds unease
shimmer_lfo = (0.5 + 0.5 * np.sin(2 * np.pi * 0.072 * t)).astype(np.float32)
shimmer     = (0.018 * shimmer_lfo * np.sin(2 * np.pi * 880 * t, dtype=np.float32))

# ── Layer 5: Noise breath ─────────────────────────────────────────────────────
rng_np   = np.random.default_rng(1337)
noise    = rng_np.standard_normal(len(t)).astype(np.float32)
# Vectorized FIR low-pass (~300 Hz) via moving-average convolution
win_size = int(SR / 300)                         # ~147 samples
kernel   = np.ones(win_size, dtype=np.float32) / win_size
filtered = np.convolve(noise, kernel, mode="same")
# Breathing envelope: 0.20 Hz (inhale/exhale cycle ~5 seconds)
breath_env = np.maximum(0, np.sin(2 * np.pi * 0.20 * t - np.pi / 4)).astype(np.float32)
breath     = 0.04 * breath_env * filtered

# ── Mix ───────────────────────────────────────────────────────────────────────
mix = bass + mid + heartbeat + shimmer + breath

# ── Fade in 4s / fade out 6s ─────────────────────────────────────────────────
fade_in  = np.minimum(t / 4.0,                  1.0).astype(np.float32)
fade_out = np.minimum((DURATION - t) / 6.0,     1.0).astype(np.float32)
mix     *= fade_in * fade_out

# ── Normalize to 94% peak ────────────────────────────────────────────────────
peak = np.max(np.abs(mix))
if peak > 1e-6:
    mix *= 0.94 / peak

# ── Write 16-bit mono WAV ────────────────────────────────────────────────────
pcm = (mix * 32767).astype(np.int16)
with wave.open(WAV_PATH, "w") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(SR)
    wf.writeframes(pcm.tobytes())
print(f"[audio] WAV written: {WAV_PATH}")

# ── Convert to MP3 via ffmpeg with reverb ────────────────────────────────────
# Double echo: short (80ms) + long (155ms) tail = cave-like, ominous
cmd = [
    FFMPEG, "-y", "-i", WAV_PATH,
    "-af", (
        "aecho=0.92:0.80:80:0.65,"
        "aecho=0.85:0.65:155:0.45,"
        "lowpass=f=5500,"
        "volume=1.55"
    ),
    "-b:a", "128k",
    OUT_PATH,
]
result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode != 0:
    print("[audio] ffmpeg error:\n", result.stderr[-800:])
    sys.exit(1)

os.remove(WAV_PATH)
size_mb = os.path.getsize(OUT_PATH) / 1_048_576
print(f"[audio] Done: {OUT_PATH}  ({size_mb:.1f} MB, {DURATION}s)")
