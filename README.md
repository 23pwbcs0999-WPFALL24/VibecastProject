# VibeCast — Creative Commentary Studio

VibeCast turns unrelated words and phrases into a creative spoken mini-commentary. The user enters ingredients such as `Umbrella, Fall, Red, Gucci, Fun`, selects a vibe, and one animated character performs the result.

There is deliberately **one character and one speaker voice**. The selected vibe changes how that same character speaks; there are no host profiles, sidekicks or additional speakers.

## Architecture

```text
User keywords + vibe + language + intensity
                  |
                  v
        Streamlit interface (app.py)
                  |
                  v
        commentary_engine.py
             /          \
            /            \
       Groq API       ElevenLabs v4 API
       script text    ONE voice ID + vibe audio tags
            \            /
             \          /
              MP3 audio + visible script
                       |
                       v
        ONE animated VibeCast character
```

## Files

```text
VibeCast_Project/
├── app.py                                  # Streamlit UI and single-character performance stage
├── commentary_engine.py                   # Keyword parsing, Groq prompts, vibe tags, ElevenLabs TTS
├── requirements.txt                       # Lightweight Python dependencies
├── .env.example                            # Safe environment-variable template
├── .gitignore
├── README.md
├── ELEVENLABS_SETUP.md                     # One-character/one-voice setup and API troubleshooting
├── VOICE_UPDATE_NOTES.md
├── VibeCast_Commentary_Instructor.ipynb   # Detailed teacher-style notebook
├── VibeCast_Colab_Launcher.ipynb           # Short upload-and-run notebook
├── .streamlit/config.toml                  # Light theme defaults
├── assets/host.svg                         # The only character, with animated mouth
└── tests/test_engine.py                    # Offline tests with mocked HTTP requests
```

## Features

- Free-form keyword input: 2–18 unique words or short phrases.
- Five vibes: Energetic, Dramatic, Funny, Emotional and Professional.
- English, Urdu and Roman Urdu text-generation options.
- Quick, Standard and Extended commentary lengths.
- One recurring animated character and one ElevenLabs voice ID.
- Groq commentary generation with a labelled deterministic offline text fallback.
- ElevenLabs v4 MP3 narration with vibe-specific audio tags and performance intensity.
- Browser/device speech fallback if ElevenLabs audio is unavailable.
- One animated mouth, speaking state, waveform, MP3/text downloads and session history.
- Alabaster Gleam, Plum Wine and Olive Drab inspired light theme.

## Configure the one ElevenLabs voice

Set these environment variables in Colab Secrets or a private local `.env` file:

```env
GROQ_API_KEY=...
ELEVENLABS_API_KEY=...
ELEVENLABS_VOICE_ID=...
ELEVENLABS_TTS_MODEL=eleven_v4
ELEVENLABS_OUTPUT_FORMAT=mp3_44100_128
```

Choose **one voice that your account is entitled to use through API text-to-speech**, then copy its voice ID. VibeCast does not create voices, call Voice Design endpoints, offer multiple voice IDs or switch speakers. The one selected voice is used for every vibe.

### Important ElevenLabs account restriction

The account used during development returned `detected_unusual_activity` and reported that Free Tier API access had been disabled. This is an account-level provider restriction. Changing the app to one character/one voice does **not** bypass it. If this response continues, ElevenLabs TTS API requests will still fail until ElevenLabs resolves the restriction or the account uses an eligible paid subscription. Do not create extra accounts, rotate networks or keys to evade it.

## Run on Windows

1. Extract the ZIP and open PowerShell in `VibeCast_Project`.
2. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Copy `.env.example` to `.env` and set `GROQ_API_KEY`, `ELEVENLABS_API_KEY`, and one `ELEVENLABS_VOICE_ID`.
5. Run:

   ```powershell
   streamlit run app.py
   ```

Keep `.env` private. Do not commit it to GitHub or share it.

## Run in Google Colab

For the teacher-style walkthrough, open `VibeCast_Commentary_Instructor.ipynb` and run the sections in order. It covers dependencies, secrets, one character and one voice, keyword parsing, Groq prompts, audio tags, a real API test, five-vibe comparisons, offline tests and Streamlit deployment.

For a shorter setup, open `VibeCast_Colab_Launcher.ipynb`. Add the API keys and one voice ID to Colab Secrets, enable notebook access, upload the ZIP and run the cells. The launcher uses `serve_kernel_port_as_iframe()`.

When replacing an already-running version, stop the old Streamlit process or restart the Colab runtime before extracting and launching the new project. Otherwise port 8501 may continue displaying old code.

## How the one-character voice pipeline works

`synthesize_expressive_audio()` reads `ELEVENLABS_VOICE_ID` for every request. It decorates the generated commentary with Eleven v4 audio tags based only on the selected vibe and intensity, then calls:

```text
POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?output_format=mp3_44100_128
```

Authentication uses the `xi-api-key` header. The request sends `model_id=eleven_v4`, the vibe-tagged transcript, and per-vibe `stability` plus `similarity_boost` settings. Eleven v4 supports audio tags; it does not support the older `style` and `speed` voice settings.

- The character and voice identity never change.
- Vibe controls emotional tags such as `[excited]`, `[whispers]`, `[mischievously]`, `[laughs]` and `[sighs]`.
- Performance intensity (1–5) adjusts how strongly the performance is directed.
- The Groq prompt also tells the model to write for one commentator and not introduce another speaker.

If ElevenLabs is disabled or unavailable, the browser can use its Web Speech API. Device voices vary by browser and OS; this fallback does not create a downloadable MP3 and may not sound like the ElevenLabs voice.

## Tests

No API key or credits are required to run the offline tests:

```powershell
python -m unittest discover -s tests -v
```

The tests validate keyword parsing, one-character prompt rules, five distinct vibe tags, the one voice endpoint, v4 request payload, unusual-activity error handling and missing configuration.

## Official references

- ElevenLabs account and unusual-activity restrictions: https://elevenlabs.io/docs/overview/administration/account
- Eleven v4 audio tags: https://elevenlabs.io/docs/help-center/product/core-capabilities/text-to-speech/how-do-audio-tags-work-with-eleven-v3-and-v4
- Text-to-speech API: https://elevenlabs.io/docs/api-reference/text-to-speech/convert
- Groq API: https://console.groq.com/docs/api-reference
- Streamlit: https://docs.streamlit.io/
