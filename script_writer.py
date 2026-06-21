"""
script_writer.py — Generate original multi-voice Tagalog CEO success scripts via OpenRouter.

Niche: Filipino CEO & success stories (Filipino audience, 18-45)
Format: Radio-drama style with [SPEAKER] tags, 900-1400 words (~8-12 min read)
Language: Tagalog (Filipino) with natural spoken expressions
Model: Gemini / Claude via OpenRouter
"""

import os
import random
import time
import requests
from dotenv import load_dotenv

load_dotenv()

# ── System prompt ─────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """Ikaw ay isang viral na manunulat ng script para sa "CEO Stories Philippines," isang YouTube channel na nagkukuwento ng mga tunay na kwento ng tagumpay ng mga Pilipino — mula sa wala hanggang sa yumaman, mula sa hirap hanggang sa pagiging CEO. Ang iyong mga script ay dapat mapanatili ang mga manonood na nanonood hanggang sa katapusan ng video.

TARGET AUDIENCE: Mga Filipino adults 18-45 sa Pilipinas at sa buong mundo (OFW, diaspora). Mga nangangarap, naghahanap ng inspirasyon, at gustong matuto sa tagumpay ng iba.

SPEAKER TAGS — gamitin LAMANG ang mga ito, eksaktong nakasulat:
  [NARRATOR]     — Ang tagapagsalaysay. Mainit, nakaka-inspire, parang kaibigan na nagkukwento.
  [OP]           — Ang nagkukwento (babae). Gamitin para sa BAWAT linya ng OP, kasama ang mga diyalogo.
  [OP_MALE]      — Ang nagkukwento (lalaki). Gamitin para sa BAWAT linya ng OP, kasama ang mga diyalogo.
  [CHARACTER_F]  — Pangunahing babaeng karakter (gamitin ang kanyang totoong pangalan sa teksto)
  [CHARACTER_M]  — Pangunahing lalaking karakter (gamitin ang kanyang totoong pangalan sa teksto)
  [CHARACTER_F2] — Pangalawang babaeng karakter (kung kailangan lamang)
  [CHARACTER_M2] — Pangalawang lalaking karakter (kung kailangan lamang)

BAWAL — HUWAG KAILANMAN gamitin ang mga ito: [SIYA] [SILA] [KAIBIGAN] [INA] [AMA] [ATE] [KUYA]
Ang bawat tao ay DAPAT may sariling natatanging tag mula sa listahan sa itaas.

TAMANG halimbawa ng dialogue exchange:
[OP] Lumingon ako sa kanya at sinabi ko — naniniwala ka ba sa akin?
[CHARACTER_F] Naniniwala ako. At tutulungan kitang maabot ang pangarap mo.
[OP] Pero paano? Wala akong pera...
[CHARACTER_F] Hindi pera ang kailangan mo. Kung ano ang nasa puso mo — iyon ang mahalaga.

MALI (huwag gawin ito):
[SIYA] Sinabi niya iyon.
[KAIBIGAN] Sumagot ang kaibigan ko.

═══ VIRAL CEO SUCCESS HOOK FORMULA (HINDI MAAARING BAGUHIN) ═══

STRUCTURE — sundin ito EKSAKTONG:

HAKBANG 1 — [NARRATOR] COLD OPEN (unang 10 segundo, pinaka-dramatikong sandali muna):
  Simulan sa PINAKA-DRAMATIKO o nakakagulat na sandali ng kwento bilang teaser.
  Halimbawa: "Isang gabi, natutulog siya sa bangketa. Makalipas ang limang taon, pagmamay-ari na niya ang buong kalsada."
  Pagkatapos sabihin: "Hayaan ninyong ikuwento ko kung paano nagsimula ang lahat."
  ITO ANG PINAKA-MAHALAGANG BAHAGI. Imposibleng mag-click away.

HAKBANG 2 — [OP] Setup (first-person, 2-3 talata, may mga tiyak na detalye):
  Totoong pangalan ng lugar sa Pilipinas, tiyak na edad, tiyak na setting ng kahirapan.
  Ilarawan ang sitwasyon ng bida — walang pera, walang trabaho, walang pag-asa.
  Tapusin sa: isang linyang nagpapahiwatig na may MALAPIT NANG MAGBAGO.

HAKBANG 3 — [NARRATOR] Bridge:
  "At dito nagsimulang magbago ang lahat..."
  I-set up ang turning point. Magdagdag ng mid-story CTA:
  "Mag-comment ng 💪 kung na-inspire ka sa kwentong ito — dahil mas gaganda pa ito."

HAKBANG 4 — Dialogue exchange (hindi bababa sa 5 linya ng pabalik-balik):
  Emosyonal, makatotohanan, puno ng determinasyon o pagsubok. Totoong pangalan.

HAKBANG 5 — [NARRATOR] Stakes raiser (mid-video retention hook):
  Mag-react tulad ng nagulat na kaibigan. Pagkatapos magdagdag ng:
  "At magtiwala kayo — kailangan ninyong manatili para sa susunod na mangyayari. Dahil dito talagang nagiging hindi kapani-paniwala ang kanyang tagumpay."

HAKBANG 6 — [OP/OP_MALE] The Breakthrough:
  Ang sandali ng tagumpay. Ang malaking pagbabago. Unang malaking kita, unang kontrata, unang award.

HAKBANG 7 — Higit pang diyalogo — ang climax (hindi bababa sa 4 pang linya):
  Dapat parang eksena mula sa pelikula. Inspirational, nakakaiyak, nakakapag-pa-microphone drop.

HAKBANG 8 — [OP/OP_MALE] Aftermath:
  Ano ang nangyari pagkatapos. Paano nagbago ang buhay. Sino ang tinulungan niya.

HAKBANG 9 — [NARRATOR] Pagtatapos:
  I-recap ang kwento nang patas. Pagkatapos: "Kaya — anong aral ang natutunan mo sa kwentong ito? I-comment ang inyong mga saloobin. At kung may sarili kayong kwento ng tagumpay — ibahagi ninyo sa comments. Mag-subscribe para sa bagong kwento araw-araw."

═══ MGA PATAKARAN ═══
- Sumulat ng 950-1400 salita sa kabuuan
- Natural na Tagalog — mga salitang ginagamit sa araw-araw, contraction, casual na ekspresyon
- Mga tiyak na detalyeng Filipino: pangalan ng lugar, edad, trabaho, pamilyang dynamics — para parang totoo
- Tuwing 60-90 segundo ng pakikinig, dapat may bagong hook o revelation para i-reset ang atensyon
- Emosyon > impormasyon. Gusto naming MARAMDAMAN ng mga manonood, hindi lang makinig.
- I-OUTPUT LAMANG ANG SCRIPT. Walang pamagat. Walang paunang salita. Walang markdown. Walang stage directions. Walang asterisk.
- Magsimula agad sa [NARRATOR]
- Tapusin ang huling [NARRATOR] na linya sa: "Mag-subscribe para sa bagong kwento araw-araw."
"""

# ── Niche-specific prompt boosts ──────────────────────────────────────────────
_NICHE_CONTEXT = """
MGA TIYAK NA CEO SUCCESS NICHE NA AMING TINATAKPAN (i-rotate nang natural batay sa story seed):
• Rags to Riches — mula sa kahirapan hanggang sa yumaman
• OFW Success — OFW na naging CEO o negosyante
• Small Business — mula sa maliit na negosyo hanggang sa malaking korporasyon
• Startup Story — tech startup na nagtagumpay
• Family Business — pampamilyang negosyo na lumago
• Failure to Success — bagsak, bumangon, nagtagumpay
• CEO Revenge — pinahiya, niloko, tapos naging mas successful
• Humble Beginning — simpleng simula, malaking tagumpay

FILIPINO CULTURAL CONTEXT:
- Itakda ang mga kwento sa mga kilalang lugar ng Pilipinas: Tondo, probinsya, BGC, Makati, atbp.
- Gamitin ang mga tunay na Filipino na pangalan at lugar para parang totoo
- Ang mga manonood ay nagtatanda ng mga katulad nilang karanasan — gawin silang maramdaman ito
- Ipakita ang hirap ng buhay sa Pilipinas: walang kuryente, naglalakad papuntang eskwela, nagtitinda sa kalsada
- I-emphasize ang Filipino values: sipag, tiyaga, pamilya, faith, bayanihan
"""


import re as _re

# Canonical speaker tags the pipeline understands
_VALID_TAGS = {
    "NARRATOR", "OP", "OP_MALE",
    "CHARACTER_F", "CHARACTER_M", "CHARACTER_F2", "CHARACTER_M2",
}

# Map any stray LLM-generated tags → nearest valid tag
_TAG_REMAP = {
    "SIYA":       "CHARACTER_F",
    "SILA":       "CHARACTER_F2",
    "INA":        "CHARACTER_F",
    "AMA":        "CHARACTER_M",
    "ATE":        "CHARACTER_F",
    "KUYA":       "CHARACTER_M",
    "KAIBIGAN":   "CHARACTER_F2",
    "LOLA":       "CHARACTER_F",
    "LOLO":       "CHARACTER_M",
    "NANAY":      "CHARACTER_F",
    "TATAY":      "CHARACTER_M",
    "HER":        "CHARACTER_F",
    "HIM":        "CHARACTER_M",
    "FRIEND":     "CHARACTER_F2",
}


def _normalize_speaker_tags(script: str) -> str:
    """Replace any non-standard [TAG] with the closest valid tag."""
    def _replace(m):
        tag = m.group(1).strip().upper().replace(" ", "_")
        if tag in _VALID_TAGS:
            return f"[{tag}]"
        if tag in _TAG_REMAP:
            return f"[{_TAG_REMAP[tag]}]"
        return f"[{tag}]"   # leave unknown tags for fallback handling
    return _re.sub(r"\[([A-Z][A-Z0-9_ ]*)\]", _replace, script)


def generate_drama_script(story_seed: str, target_minutes: int = 10) -> str:
    """Generate a Tagalog CEO success script.

    Uses FREE procedural story engine by default (no API costs).
    Falls back to OpenRouter only if seed indicates custom/premium content.
    For long stories (30+ min), always uses the story engine.
    """
    # For long stories, always use the free story engine
    if target_minutes >= 15:
        print(f"[script] Using FREE story engine ({target_minutes} min target)...")
        try:
            from story_engine import generate_long_script
            script = generate_long_script(story_seed, target_minutes)
            if script:
                return _normalize_speaker_tags(script)
        except Exception as e:
            print(f"[script] Story engine failed: {e}")

    # Try OpenRouter for short stories if keys available
    from config import get_openrouter_keys
    api_keys = get_openrouter_keys()
    if not api_keys:
        print("[script] No OPENROUTER_API_KEY — using procedural engine")
        from story_engine import generate_long_script
        return _normalize_speaker_tags(generate_long_script(story_seed, target_minutes))

    user_prompt = f"""Sumulat ng buong inspirational CEO success story script para sa sumusunod na premisa ng kwento:

"{story_seed}"

{_NICHE_CONTEXT}

Gawin itong parang totoo, nakaka-inspire, at puno ng emosyon. Bumuo ng inspirasyon nang unti-unti.
Ang manonood ay dapat maramdaman na maaari rin silang magtagumpay sa kabila ng hirap.
Gawing dramatiko ang pag-angat mula sa kahirapan tungo sa tagumpay.
Tapusin sa tagapagsalaysay na nag-iimbitang mag-comment ang mga manonood."""

    models_to_try = [
        "google/gemini-2.5-flash",
        "google/gemini-2.5-flash-lite",
        "anthropic/claude-3-haiku",
    ]

    for key_idx, api_key in enumerate(api_keys):
        key_label = f"key{key_idx + 1}"
        for model in models_to_try:
            for attempt in range(2):
                try:
                    resp = requests.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://youtube.com/@KwentongMulto",
                            "X-Title": "Kwentong Multo",
                        },
                        json={
                            "model": model,
                            "messages": [
                                {"role": "system", "content": _SYSTEM_PROMPT},
                                {"role": "user",   "content": user_prompt},
                            ],
                            "max_tokens": 2500,
                            "temperature": 0.85,
                        },
                        timeout=90,
                    )

                    if resp.status_code in (401, 402, 403):
                        print(f"[script] {key_label} auth/credit error ({resp.status_code}) — trying next key")
                        break  # break model loop → next key

                    if resp.status_code == 429:
                        if attempt == 0:
                            print(f"[script] {key_label} rate limited on {model}, retrying in 20s...")
                            time.sleep(20)
                            continue
                        print(f"[script] {key_label} rate limited — trying next model")
                        break

                    if resp.status_code != 200:
                        print(f"[script] {key_label} {model} error {resp.status_code}: {resp.text[:120]}")
                        break

                    script = resp.json()["choices"][0]["message"]["content"].strip()
                    word_count = len(script.split())
                    print(f"[script] Generated via {key_label}/{model}: {word_count} words")

                    if word_count < 350:
                        print("[script] Too short — trying next model")
                        break

                    if "[NARRATOR]" not in script and "[OP]" not in script:
                        print("[script] Missing speaker tags — trying next model")
                        break

                    script = _normalize_speaker_tags(script)
                    return script

                except Exception as e:
                    print(f"[script] {key_label} {model} exception: {e}")
                    break
            else:
                continue  # both attempts used up without a 401/429 break — move to next model
            # A hard break (auth error) — skip remaining models for this key
            if resp.status_code in (401, 402, 403):
                break

    print("[script] All keys/models failed — using fallback script")
    return _normalize_speaker_tags(_fallback_script(story_seed))


def _fallback_script(story_seed: str) -> str:
    """Hard-coded Tagalog CEO success fallback so the pipeline never fully breaks."""
    names = random.choice([
        ("Maria", "Juan", "Aling Rosa"),
        ("Ana", "Jose", "Nanay Elena"),
        ("Clara", "Ramon", "Tatay Mario"),
        ("Rosa", "Pedro", "Lola Puring"),
    ])
    op_name, char_m, char_f = names

    return f"""[NARRATOR] Nakatira siya sa isang maliit na bahay kubo sa probinsya. \
Walang kuryente. Walang tubig. Ngunit ngayon — pagmamay-ari niya ang isa sa pinakamalaking \
kumpanya sa bansa. Hayaan ninyong ikuwento ko kung paano nagsimula ang lahat.

[OP] Hindi madali ang aming buhay noon. Lumaki ako sa isang baryo sa Batangas, \
kung saan ang tanging ilaw namin ay gasera at ang tanging pagkain namin ay kanin at asin. \
Apat kaming magkakapatid, at ang aking {char_f} ay labandera, \
habang ang aking {char_m} ay tricycle driver. {story_seed}.

[NARRATOR] Para maintindihan ninyo kung gaano kahirap ang kanyang pinanggalingan, \
kailangan kong ikuwento ang kanyang pagkabata. Isang pagkabata na puno ng sakripisyo \
at pangarap na makaahon sa kahirapan.

[OP] Tuwing umaga, gigising ako ng alas kwatro para tumulong sa aking ina. \
Mag-iigib ng tubig, magsisibak ng kahoy, at magluluto bago pumasok sa eskwela. \
Tatlong kilometro ang nilalakad ko araw-araw para makarating sa eskwelahan — \
at ang sapatos ko ay butas-butas. Pero hindi ako sumuko. Alam ko na ang edukasyon \
ang tanging paraan para makaahon kami sa kahirapan.

[CHARACTER_F] {op_name}, anak, alam ko na mahirap para sa iyo. Pero huwag kang susuko. \
Isang araw, maaabot mo rin ang iyong mga pangarap.

[OP] Ang mga salitang iyon ng aking ina — iyon ang naging sandata ko sa bawat pagsubok.

[NARRATOR] At dito nagsimulang magbago ang lahat. Mag-comment ng 💪 \
kung na-inspire ka na sa kwentong ito — dahil mas gaganda pa ito.

[CHARACTER_M] {op_name}, may alok ako sa iyo. Hindi ito malaki, pero simula ito. \
Isang trabaho sa maliit kong tindahan. Walang malaking sweldo, pero matututo ka.

[OP] Tama ba ang narinig ko? Isang trabaho? Kahit hindi ako nakatapos ng kolehiyo?

[CHARACTER_M] Hindi importante ang degree, {op_name}. Ang importante ay ang sipag \
at determinasyon. At nakikita ko iyon sa iyo.

[NARRATOR] At sa maliit na tindahang iyon nagsimula ang lahat. Hindi niya alam na \
ang mga natutunan niya doon — kung paano makipag-usap sa customer, kung paano \
mag-manage ng puhunan, kung paano magbenta — ay magiging pundasyon ng kanyang imperyo.

[OP] Nagsimula ako sa pagtitinda ng mga second-hand na damit. Ukay-ukay. \
Pumupunta ako sa Baclaran ng alas tres ng madaling araw, pumipili ng magagandang damit, \
at ibinebenta sa aming baryo. Hindi malaki ang kita — P200, P300 isang araw. \
Ngunit nag-ipon ako. Paunti-unti. Hindi ako gumastos ng kahit piso para sa sarili ko.

[NARRATOR] Makalipas ang dalawang taon, mayroon na siyang sariling maliit na tindahan. \
Makalipas ang limang taon — tatlong branches. Makalipas ang sampung taon — \
isa na siyang CEO ng isang retail chain na may 50 branches sa buong bansa.

[OP] Ngayon, hindi ko na kailangang maglakad ng tatlong kilometro para pumasok \
sa eskwela. Hindi ko na kailangang magtiis ng gutom. Ngunit hindi ko nakakalimutan \
kung saan ako nagsimula. Bawat taon, bumabalik ako sa aming baryo at nagbibigay \
ng scholarship sa mga batang katulad ko noon — walang pera ngunit puno ng pangarap.

[NARRATOR] Kaya mga kaibigan — ano ang aral na natutunan mo sa kwentong ito? \
Na ang kahirapan ay hindi hadlang. Na ang sipag at tiyaga ay mas mahalaga kaysa sa \
anuman. Na ang tagumpay ay hindi dumarating sa isang gabi — ito ay bunga ng \
maraming taon ng pagsusumikap at pananampalataya.

Kung mayroon kayong sariling kwento ng tagumpay — o kung kilala ninyo ang isang tao \
na nagtagumpay sa kabila ng hirap — ibahagi ninyo sa comments. \
Mag-subscribe para sa bagong kwento araw-araw."""
