# Voice update notes — Single character

- The interface displays exactly one animated VibeCast character (`assets/host.svg`).
- The sidekick asset and all additional character/host selection controls have been removed.
- The app reads exactly one `ELEVENLABS_VOICE_ID`.
- The same voice ID is used for Energetic, Dramatic, Funny, Emotional and Professional performances.
- `commentary_engine.py` changes acting through vibe-specific Eleven v4 audio tags and intensity-sensitive Stability settings.
- Groq prompts explicitly forbid adding co-hosts, sidekicks or additional speakers.
- Browser speech fallback also animates the same single character.
- No Gemini or Qwen TTS dependency is included.
