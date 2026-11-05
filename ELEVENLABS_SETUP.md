# VibeCast — One Character / One Voice Setup

VibeCast contains one animated commentator and uses one ElevenLabs voice ID for every generation. The only user-selected performance controls are the five vibes and intensity. There are no separate host profiles or sidekick voices.

## Colab Secrets or local `.env`

```env
GROQ_API_KEY=...
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...
ELEVENLABS_TTS_MODEL=eleven_v4
ELEVENLABS_OUTPUT_FORMAT=mp3_44100_128
```

Copy one voice ID that your account is permitted to use through API text-to-speech. VibeCast does not create, clone or save voices through Voice Design APIs.

## How emotion works

The same character and voice are used for every generation. `commentary_engine.py` adds Eleven v4 audio tags according to the selected vibe:

- Energetic: excited delivery and a strong finish.
- Dramatic: quieter opening, suspense and a reveal.
- Funny: mischievous delivery and comic timing.
- Emotional: softer, tender and heartfelt delivery.
- Professional: confident, controlled presentation.

Intensity 1–5 changes how strongly the selected performance is directed. Eleven v4 requests use Stability and Similarity; the old `style` and `speed` settings are not used.

## Account restriction

During development this account returned `detected_unusual_activity` and said Free Tier access had been disabled. One character and one voice ID do not bypass provider-side access restrictions. Contact ElevenLabs support or use an eligible paid subscription if this restriction persists. Do not create extra accounts or rotate IPs/keys to evade it.

## Troubleshooting

- `401 missing_permissions`: edit the API key and enable the permissions required for the TTS endpoint.
- `401 detected_unusual_activity`: the provider has disabled Free Tier API access for the account; changing code or voice ID will not fix it.
- `403`: check voice availability, model access and account restrictions.
- `404`: verify `ELEVENLABS_VOICE_ID`.
- `422`: verify the selected model, text length and request payload.
- `429`: check concurrency and remaining credits.
