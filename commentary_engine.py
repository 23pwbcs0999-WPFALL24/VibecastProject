"""Creative keyword-to-commentary engine for VibeCast.

Groq generates the spoken script. ElevenLabs v4 performs it as expressive
speech using user-owned Voice Design IDs. A deterministic fallback keeps the
text experience usable when Groq is unavailable.
"""
from __future__ import annotations

import os
import re
from typing import Iterable

import requests

GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
ELEVENLABS_TTS_MODEL = os.getenv("ELEVENLABS_TTS_MODEL", "eleven_v4")
ELEVENLABS_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
ELEVENLABS_OUTPUT_FORMAT = os.getenv("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128")
ELEVENLABS_VOICE_ENV_KEY = "ELEVENLABS_VOICE_ID"
CHARACTER_NAME = "VibeCast Host"

STYLES = ["Energetic", "Dramatic", "Funny", "Emotional", "Professional"]
STYLE_EMOJI = {
    "Energetic": "⚡",
    "Dramatic": "🎭",
    "Funny": "😄",
    "Emotional": "💜",
    "Professional": "🎙️",
}
LANGUAGES = ["English", "Urdu", "Roman Urdu"]

STYLE_DIRECTIONS = {
    "Energetic": "Fast-moving, lively and full of momentum. Use punchy openings, rhythmic bursts, exciting verbs and a celebratory finish.",
    "Dramatic": "Build suspense gradually. Use short pauses, vivid imagery and a powerful reveal. Make the moment cinematic without becoming confusing.",
    "Funny": "Playful, witty and light-hearted. Use clever, harmless humour, surprising comparisons and comic timing.",
    "Emotional": "Warm, heartfelt and expressive. Give the moment meaning with gentle phrasing, sincerity and natural spoken rhythm.",
    "Professional": "Polished, confident and composed. Use precise wording, smooth transitions and controlled emphasis while remaining engaging.",
}

TTS_DIRECTIONS = {
    "Energetic": "Perform with bright excitement, lively pitch movement, quick rhythmic momentum and a strong celebratory finish. Sound enthusiastic, not continuously loud.",
    "Dramatic": "Begin quietly and build suspense. Slow down before important details, use meaningful pauses and deliver the reveal with controlled intensity.",
    "Funny": "Sound amused and mischievous. Use playful emphasis, conversational timing and a small pause before the punchline. Let the funny line land naturally.",
    "Emotional": "Use a warm, gentle and heartfelt delivery. Slow the pace, soften the opening and emphasize meaningful words with sincerity rather than melodrama.",
    "Professional": "Speak like a polished presenter: clear articulation, balanced pace, measured emphasis and calm confidence. Avoid sounding flat.",
}

INTENSITY_DIRECTIONS = {
    1: "Keep the acting subtle and restrained, with gentle emotional colour.",
    2: "Use light but noticeable emotion and modest changes in emphasis.",
    3: "Use a balanced, clearly expressive performance with natural dynamic changes.",
    4: "Make the emotion strong and engaging, with pronounced changes in emphasis and delivery.",
    5: "Give a bold, theatrical performance with strong emotional contrast while keeping every word clear.",
}


def elevenlabs_voice_id() -> str:
    """Return the one and only ElevenLabs voice configured for VibeCast."""
    return os.getenv(ELEVENLABS_VOICE_ENV_KEY, "").strip()


def build_tts_prompt(
    text: str = "",
    style: str = "Energetic",
    language: str = "English",
    intensity: int = 4,
) -> str:
    """Build a human-readable director note for the single VibeCast character."""
    selected_style = style if style in STYLES else "Energetic"
    level = max(1, min(5, int(intensity)))
    language_note = {
        "English": "Use natural English pronunciation and rhythm.",
        "Urdu": "Use natural Urdu pronunciation and rhythm.",
        "Roman Urdu": "Read Roman Urdu naturally using Pakistani Urdu pronunciation; do not translate it into English.",
    }.get(language, "Use natural pronunciation for the supplied language.")
    return (
        f"CHARACTER: One consistent VibeCast commentator. Keep the same speaker identity. "
        f"VIBE ({selected_style}): {TTS_DIRECTIONS[selected_style]} "
        f"INTENSITY: {level}/5. {INTENSITY_DIRECTIONS[level]} "
        f"LANGUAGE: {language_note} Read only the supplied script."
    )


def decorate_elevenlabs_transcript(
    text: str,
    style: str,
    intensity: int = 4,
) -> str:
    """Add Eleven v4 audio tags so one character performs each vibe differently."""
    transcript = (text or "").strip()
    if not transcript:
        return ""
    selected_style = style if style in STYLES else "Energetic"
    level = max(1, min(5, int(intensity)))
    sentences = [p.strip() for p in re.split(r"(?<=[.!?؟۔])\s+", transcript) if p.strip()]
    if not sentences:
        return transcript

    opening_by_style = {
        "Energetic": "[excited]",
        "Dramatic": "[whispers]",
        "Funny": "[mischievously]",
        "Emotional": "[softly]",
        "Professional": "[confident]",
    }
    middle_by_style = {
        "Energetic": "[excited]",
        "Dramatic": "[curious]",
        "Funny": "[playfully]",
        "Emotional": "[tenderly]",
        "Professional": "[confident]",
    }
    ending_by_style = {
        "Energetic": "[shouts]" if level >= 4 else "[excited]",
        "Dramatic": "[whispers]" if level <= 3 else "[excited]",
        "Funny": "[laughs]" if level >= 4 else "[mischievously]",
        "Emotional": "[sighs]" if level >= 4 else "[softly]",
        "Professional": "[confident]",
    }

    sentences[0] = f"{opening_by_style[selected_style]} {sentences[0]}"
    if len(sentences) >= 3 and level >= 2:
        middle_index = len(sentences) // 2
        sentences[middle_index] = f"{middle_by_style[selected_style]} {sentences[middle_index]}"
    if len(sentences) >= 2:
        if selected_style == "Dramatic":
            sentences[-1] = f"... {ending_by_style[selected_style]} {sentences[-1]}"
        else:
            sentences[-1] = f"{ending_by_style[selected_style]} {sentences[-1]}"
    return " ".join(sentences)


# This is intentionally a small, transparent offline fallback rather than a
# pretend LLM. It keeps user-supplied words in the result and varies by tone.
def parse_keywords(raw_words: str | Iterable[str]) -> list[str]:
    """Split comma/newline/semicolon/pipe-separated words into clean tokens."""
    if isinstance(raw_words, str):
        pieces = re.split(r"[,;|\n]+", raw_words)
    else:
        pieces = [str(item) for item in raw_words]
    words: list[str] = []
    seen: set[str] = set()
    for piece in pieces:
        cleaned = re.sub(r"\s+", " ", str(piece)).strip(" \t\r\n•-*—")
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key not in seen:
            words.append(cleaned)
            seen.add(key)
    return words


def _length_spec(length: str) -> tuple[int, int, str]:
    choices = {
        "Quick hit": (1, 2, "1–2 lively sentences, roughly 15–30 words"),
        "Standard": (2, 4, "2–4 short spoken sentences, roughly 35–60 words"),
        "Extended": (4, 6, "4–6 short spoken sentences, roughly 65–100 words"),
    }
    return choices.get(length, choices["Standard"])


def build_system_prompt(
    style: str = "Energetic",
    language: str = "English",
    commentator_name: str = CHARACTER_NAME,
    length: str = "Standard",
    intensity: int = 4,
) -> str:
    """Create the creative, non-sports prompt used by Groq."""
    selected_style = style if style in STYLES else "Energetic"
    selected_language = language if language in LANGUAGES else "English"
    _, _, length_text = _length_spec(length)
    return f"""You are {commentator_name}, the single on-screen commentator for VibeCast.

YOUR TASK:
Turn the user's random words and phrases into one connected, entertaining spoken commentary moment. The words can describe objects, brands, emotions, places, people, colours, actions or completely unrelated ideas. Find a playful, surprising connection between them and make the result feel like a live performance, not a dictionary list.

SELECTED TONE: {selected_style}
TONE DIRECTION: {STYLE_DIRECTIONS[selected_style]}
LANGUAGE: {selected_language}. Write naturally and fluently in this language. Keep proper nouns and brand names as supplied.
PERFORMANCE INTENSITY: {max(1, min(5, int(intensity)))}/5
LENGTH: {length_text}.

CHARACTER RULE:
- There is exactly one recurring VibeCast character and one commentator voice.
- Do not introduce a co-host, sidekick, second speaker, dialogue exchange or additional character.
- The same commentator should sound like the same person in every generation; only the selected tone changes the acting style.

CREATIVE RULES:
- Use every supplied keyword or phrase naturally; do not simply list them.
- Build one coherent mini-scene or surprising moment that links the ingredients.
- You may invent harmless fictional connective details because this is creative entertainment, not factual reporting.
- Do not claim the story is real. Do not add hateful, sexual, dangerous or defamatory content.
- Make the chosen tone unmistakable through pacing, word choice and punctuation.
- Sound natural when read aloud. Use short sentences, varied rhythm and purposeful pauses.
- Do not imitate or impersonate a real commentator, celebrity or copyrighted character.
- Do not mention prompts, AI, keywords, instructions or the generation process.

OUTPUT: Return only the commentary. No title, markdown, explanations, quotation marks around the whole response, stage directions or dialogue labels."""


def _english_fallback(words: list[str], style: str) -> str:
    w = words[:]
    # The minimum is checked by the app; for direct engine use, repeat a neutral
    # connector when only one ingredient is supplied.
    if len(w) == 1:
        w.append("a surprise")
    first = w[0]
    second = w[1]
    middle = w[2:-1]
    last = w[-1]
    middle_text = ", ".join(middle)
    if style == "Energetic":
        bits = [f"Ladies and gentlemen, here comes {first} — and it is bringing {second} along for the ride!"]
        if middle_text:
            bits.append(f"{middle_text} just joined the action, and the whole scene has gone up a level!")
        bits.append(f"And the final twist? {last}! What a moment, what a combination, what a finish!")
    elif style == "Dramatic":
        bits = [f"At first, it was just {first}. Then came {second}… and suddenly, everything changed."]
        if middle_text:
            bits.append(f"{middle_text} appeared one by one, each adding another layer to the mystery.")
        bits.append(f"But the final reveal was {last}. Pause for a moment… what a scene!")
    elif style == "Funny":
        bits = [f"Someone invited {first} to the party, but nobody warned it about {second}!"]
        if middle_text:
            bits.append(f"Then {middle_text} showed up like they owned the place. Honestly, there is no committee prepared for this lineup.")
        bits.append(f"And {last} gets the last word. Absolutely chaotic — and somehow, completely brilliant!")
    elif style == "Emotional":
        bits = [f"Sometimes a memorable moment begins with something as simple as {first}, then finds its spark in {second}."]
        if middle_text:
            bits.append(f"With {middle_text} becoming part of the story, the little details start to mean so much more.")
        bits.append(f"And there it is: {last}. A small collection of ideas, turned into a moment worth remembering.")
    else:
        bits = [f"The scene opens with {first}, followed by the unexpected arrival of {second}."]
        if middle_text:
            bits.append(f"The addition of {middle_text} creates a distinctive and engaging sequence.")
        bits.append(f"The moment closes with {last}, bringing the full picture together with a memorable finish.")
    return " ".join(bits)


def offline_commentary(
    words: str | Iterable[str],
    style: str = "Energetic",
    language: str = "English",
    length: str = "Standard",
) -> str:
    """Produce deterministic creative commentary without external API calls."""
    tokens = parse_keywords(words)
    if not tokens:
        return "Add a few words and let the story begin!"
    selected_style = style if style in STYLES else "Energetic"
    english = _english_fallback(tokens, selected_style)
    if language == "Roman Urdu":
        # Keep the supplied keywords unchanged while giving a natural Roman
        # Urdu fallback. Groq handles fluent translation when configured.
        prefix = {
            "Energetic": "Ladies and gentlemen, kya zabardast scene ban raha hai!",
            "Dramatic": "Sab kuch bilkul normal lag raha tha... phir achanak kahani badal gayi.",
            "Funny": "Yeh scene dekh kar lagta hai kisi ne imagination ka remote kho diya hai!",
            "Emotional": "Kabhi kabhi choti choti cheezen mil kar aik yaadgar lamha bana deti hain.",
            "Professional": "Is manzar ka aghaz aik dilchasp combination se hota hai.",
        }[selected_style]
        joined = ", ".join(tokens[:-1])
        return f"{prefix} {joined} aur {tokens[-1]} — kya khoobsurat, unexpected combination hai!"
    if language == "Urdu":
        prefix = {
            "Energetic": "خواتین و حضرات، کیا زبردست منظر بن رہا ہے!",
            "Dramatic": "سب کچھ معمول کے مطابق تھا... پھر اچانک کہانی بدل گئی۔",
            "Funny": "یہ منظر دیکھ کر لگتا ہے تخیل نے آج چھٹی نہیں کی!",
            "Emotional": "کبھی کبھی چھوٹی چھوٹی چیزیں مل کر ایک یادگار لمحہ بنا دیتی ہیں۔",
            "Professional": "اس منظر کا آغاز ایک دلچسپ امتزاج سے ہوتا ہے۔",
        }[selected_style]
        return f"{prefix} {'، '.join(tokens)} — کیا خوبصورت اور غیر متوقع امتزاج ہے!"
    # Avoid chopping in the middle of a sentence. The text-generation API
    # follows the selected length more precisely.
    sentences = re.split(r"(?<=[.!?])\s+", english)
    if length == "Quick hit" and len(sentences) > 2:
        # Merge the payoff into sentence two so even the shorter mode retains
        # every user-supplied ingredient.
        return sentences[0] + " " + " ".join(sentences[1:])
    return english


def _safe_api_message(exc: Exception) -> str:
    message = str(exc).lower()
    if "401" in message or "authentication" in message or "invalid api key" in message:
        return "Groq authentication failed; check GROQ_API_KEY."
    if "429" in message or "rate limit" in message or "quota" in message:
        return "Groq rate limit or quota reached; using offline commentary."
    if "404" in message or "model" in message and "not found" in message:
        return f"Groq model '{GROQ_MODEL}' was not found; check GROQ_MODEL."
    return "Groq could not be reached; using offline commentary."


def generate_commentary(
    words: str | Iterable[str],
    style: str = "Energetic",
    language: str = "English",
    commentator_name: str = CHARACTER_NAME,
    length: str = "Standard",
    intensity: int = 4,
) -> tuple[str, str, bool, str]:
    """Return (commentary, status, used_fallback, label)."""
    tokens = parse_keywords(words)
    if len(tokens) < 2:
        return "Please enter at least two words or short phrases to connect.", "Input needed · add at least two ideas", True, "Waiting for ideas"
    if len(tokens) > 18:
        return "Please use 18 words or fewer so the commentary can connect them clearly.", "Input too long · use 18 words or fewer", True, "Too many ideas"
    if style not in STYLES:
        style = "Energetic"
    if language not in LANGUAGES:
        language = "English"

    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        script = offline_commentary(tokens, style, language, length)
        return script, "Offline creative mode · GROQ_API_KEY not configured", True, "Creative mix"

    prompt = build_system_prompt(style, language, commentator_name, length, intensity)
    user_message = "Create the commentary from these user-supplied ingredients:\n" + "\n".join(f"- {item}" for item in tokens)
    try:
        from groq import Groq

        client = Groq(api_key=api_key, timeout=60.0, max_retries=1)
        completion = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message},
            ],
            reasoning_effort="low" if "gpt-oss" in GROQ_MODEL else None,
            include_reasoning=False if "gpt-oss" in GROQ_MODEL else None,
            max_completion_tokens=1200,
            temperature=0.8,
            top_p=0.95,
            stream=False,
        )
        content = completion.choices[0].message.content
        if not content or not content.strip():
            raise RuntimeError("Groq returned an empty response")
        return content.strip(), f"Live AI inference · {GROQ_MODEL}", False, "Creative mix"
    except Exception as exc:  # API failure should not break the rest of the app.
        script = offline_commentary(tokens, style, language, length)
        return script, _safe_api_message(exc), True, "Creative mix"


def synthesize_expressive_audio(
    text: str,
    style: str = "Energetic",
    language: str = "English",
    intensity: int = 4,
) -> tuple[bytes | None, str]:
    """Generate expressive MP3 narration for the one VibeCast character."""
    transcript = (text or "").strip()
    if not transcript:
        return None, "No commentary text is available to narrate."
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    if not api_key:
        return None, "ElevenLabs voice is not configured: add ELEVENLABS_API_KEY to Colab Secrets or .env."

    selected_voice_id = os.getenv(ELEVENLABS_VOICE_ENV_KEY, "").strip()
    if not selected_voice_id:
        return None, (
            "No ElevenLabs voice is configured. Add one voice ID as "
            "ELEVENLABS_VOICE_ID in Colab Secrets or your local .env file."
        )
    if len(transcript) > 10000:
        return None, "Eleven v4 accepts up to 10,000 characters per request. Shorten the commentary and try again."

    selected_style = style if style in STYLES else "Energetic"
    tagged_text = decorate_elevenlabs_transcript(transcript, selected_style, intensity)
    level = max(1, min(5, int(intensity)))
    # Modest stability changes complement the tags; the tags remain the main
    # emotional control. Similarity helps keep the one shared speaker consistent.
    stability_by_style = {
        "Energetic": 0.34,
        "Dramatic": 0.40,
        "Funny": 0.30,
        "Emotional": 0.52,
        "Professional": 0.60,
    }
    # Higher performance intensity lowers stability slightly to allow a wider
    # expressive range; low intensity keeps the same host more controlled.
    # Eleven v4 exposes Stability and Similarity. Its Style and Speed sliders
    # are not supported, so acting is directed by inline tags plus stability.
    adjusted_stability = round(
        max(0.22, min(0.78, stability_by_style[selected_style] - (level - 3) * 0.045)),
        2,
    )
    body = {
        "text": tagged_text,
        "model_id": ELEVENLABS_TTS_MODEL,
        "voice_settings": {
            "stability": adjusted_stability,
            "similarity_boost": 0.78,
        },
    }
    url = ELEVENLABS_TTS_URL.format(voice_id=selected_voice_id)

    try:
        response = requests.post(
            url,
            params={"output_format": ELEVENLABS_OUTPUT_FORMAT},
            headers={"xi-api-key": api_key, "Content-Type": "application/json"},
            json=body,
            timeout=120,
        )
        response.raise_for_status()
        audio_bytes = response.content
        if not audio_bytes:
            return None, "ElevenLabs returned an empty audio response. Check the selected voice and model access."
        return audio_bytes, (
            f"ElevenLabs v4 · VibeCast Host · {selected_style} · "
            f"intensity {level}/5 · MP3"
        )
    except requests.HTTPError as exc:
        status_code = exc.response.status_code if exc.response is not None else "unknown"
        provider_detail = ""
        if exc.response is not None:
            try:
                error_payload = exc.response.json()
                provider_detail = str(error_payload.get("detail", error_payload.get("message", "")))
            except (ValueError, AttributeError):
                provider_detail = str(getattr(exc.response, "text", ""))
        detail_text = provider_detail.lower()
        if status_code == 401 and ("detected_unusual_activity" in detail_text or "free tier access has been disabled" in detail_text):
            message = (
                "ElevenLabs has disabled Free Tier API access on this account due to unusual-activity detection. "
                "Using one voice ID does not bypass this account restriction. Contact ElevenLabs support or use an eligible paid subscription."
            )
        elif status_code == 401 and ("missing_permissions" in detail_text or "missing permission" in detail_text):
            message = "ElevenLabs API key is missing a required permission. Edit the key permissions in the ElevenLabs dashboard."
        elif status_code == 401:
            message = "ElevenLabs authentication failed; check whether ELEVENLABS_API_KEY is valid and active."
        elif status_code == 403:
            message = "ElevenLabs denied this request. Check voice ownership/availability, model access and plan restrictions."
        elif status_code == 404:
            message = "ElevenLabs voice ID was not found. Check the configured custom voice ID."
        elif status_code == 422:
            message = "ElevenLabs rejected the request. Check the voice ID, model, audio tags and text length."
        elif status_code == 429:
            message = "ElevenLabs concurrency limit or monthly credit allowance reached. Check your Usage page."
        else:
            message = f"ElevenLabs TTS request failed (HTTP {status_code})."
        if provider_detail:
            message += f" Provider detail: {provider_detail[:320]}"
        return None, message
    except requests.RequestException as exc:
        return None, f"ElevenLabs network request failed ({type(exc).__name__}). Check your connection and try again."
    except (ValueError, KeyError, TypeError) as exc:
        return None, f"ElevenLabs returned an unexpected response ({type(exc).__name__})."
