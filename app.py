from __future__ import annotations

import base64
import html
import json
import os
import re
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

import commentary_engine as engine

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
load_dotenv(BASE_DIR / ".env")

st.set_page_config(
    page_title="VibeCast · Creative Commentary Studio",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Approximate digital palette based on the requested Pantone colours.
ALABASTER = "#F0DEBD"
PLUM = "#674550"
OLIVE = "#756D47"
PAPER = "#FBF8F2"
INK = "#302B2A"


def _secret(name: str) -> str:
    value = os.getenv(name, "").strip()
    if value:
        return value
    try:
        value = str(st.secrets.get(name, "") or "").strip()
    except Exception:
        value = ""
    if value:
        os.environ[name] = value
    return value


def _inject_css() -> None:
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap');
        :root {{ --paper:{PAPER}; --alabaster:{ALABASTER}; --plum:{PLUM}; --olive:{OLIVE}; --ink:{INK}; }}
        html, body, [data-testid="stAppViewContainer"] {{ background: var(--paper); color:var(--ink); }}
        [data-testid="stHeader"] {{ background:transparent; }}
        [data-testid="stToolbar"] {{ right:1rem; }}
        .block-container {{ padding-top:1.7rem; padding-bottom:3rem; max-width:1240px; }}
        body, p, label, input, textarea, button {{ font-family:'DM Sans',sans-serif; }}
        h1,h2,h3 {{ font-family:'Fraunces',serif !important; color:var(--plum) !important; letter-spacing:-.035em; }}
        [data-testid="stMarkdownContainer"] p {{ color:var(--ink); }}
        [data-testid="stTextArea"] textarea {{ background:#fffdf9; border:1px solid #e4d5bd; border-radius:17px; min-height:138px; color:var(--ink); }}
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div {{ background:#fffdf9; border-color:#e4d5bd; border-radius:13px; }}
        [data-testid="stRadio"] > div {{ gap:.4rem; }}
        [data-testid="stRadio"] label {{ background:#fffdf9; border:1px solid #e8ddcc; border-radius:13px; padding:.45rem .72rem; }}
        [data-testid="stRadio"] label:has(input:checked) {{ background:#f2e7d7; border-color:var(--plum); }}
        [data-testid="stSlider"] [data-baseweb="slider"] {{ padding-top:.6rem; }}
        .brandline {{ display:flex;align-items:center;gap:.65rem; color:var(--plum);font-weight:800;letter-spacing:.08em;text-transform:uppercase;font-size:.78rem; }}
        .brandmark {{ width:39px;height:39px;display:flex;align-items:center;justify-content:center;border-radius:13px;background:var(--plum);color:#fff;font-size:1.25rem;box-shadow:0 6px 16px #6745502a; }}
        .hero {{ background:linear-gradient(115deg,#f5e7d2 0%,#f8efe3 54%,#e9e8d9 100%);border:1px solid #e9dcc8;border-radius:27px;padding:1.55rem 1.7rem;position:relative;overflow:hidden; }}
        .hero:after {{ content:'✦';position:absolute;right:5%;top:4%;font-size:5rem;color:#756d4725;transform:rotate(15deg); }}
        .eyebrow {{ color:var(--olive);font-size:.72rem;font-weight:800;text-transform:uppercase;letter-spacing:.15em; }}
        .hero-title {{ font-family:'Fraunces',serif;font-size:clamp(2rem,4vw,3.55rem);line-height:1.02;color:var(--plum);margin:.5rem 0 .65rem;max-width:760px; }}
        .hero-copy {{ color:#665a51;font-size:1rem;max-width:670px;line-height:1.65; }}
        .panel {{ background:#fffdf9;border:1px solid #e9dfd1;border-radius:22px;padding:1.15rem 1.25rem;box-shadow:0 10px 30px #49352c08; }}
        .panel-title {{ color:var(--plum);font-weight:800;font-size:1rem;margin-bottom:.2rem; }}
        .panel-sub {{ color:#887e72;font-size:.83rem;line-height:1.45; }}
        .word-example {{ display:inline-block;background:#f0e3cf;color:var(--plum);border:1px solid #e7d6bd;border-radius:999px;padding:.32rem .72rem;font-size:.77rem;font-weight:700;margin:.18rem .18rem 0 0; }}
        .stButton button, .stFormSubmitButton button {{ background:var(--plum);color:white;border:0;border-radius:14px;padding:.68rem 1.2rem;font-weight:800;box-shadow:0 7px 16px #67455025;transition:transform .15s,box-shadow .15s; }}
        .stButton button:hover, .stFormSubmitButton button:hover {{ background:#513541;color:white;transform:translateY(-1px);box-shadow:0 9px 19px #67455032; }}
        .stDownloadButton button {{ border-radius:12px;border:1px solid #d8c7b5;background:#fffdf9;color:var(--plum);font-weight:700; }}
        .result-heading {{ display:flex;align-items:center;justify-content:space-between;gap:1rem;margin:.3rem 0 .7rem; }}
        .result-pill {{ display:inline-flex;align-items:center;gap:.4rem;padding:.35rem .7rem;border-radius:999px;background:#e8ebdd;color:#566044;font-weight:700;font-size:.73rem; }}
        .commentary-box {{ background:#f3e8d8;border:1px solid #e7d7c2;border-radius:18px;padding:1.2rem 1.3rem;color:#43353b;font-family:'Fraunces',serif;font-size:1.17rem;line-height:1.65; }}
        .mini-label {{ color:var(--olive);font-size:.68rem;font-weight:800;letter-spacing:.12em;text-transform:uppercase; }}
        .history-item {{ background:#fffdf9;border:1px solid #ece2d5;border-radius:14px;padding:.75rem .9rem;margin:.45rem 0; }}
        div[data-testid="stAlert"] {{ border-radius:14px; }}
        #MainMenu, footer {{ visibility:hidden; }}
        @media (max-width:700px) {{ .block-container{{padding-left:1rem;padding-right:1rem;}} .hero{{padding:1.2rem;}} .hero-title{{font-size:2.25rem;}} }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _read_svg(filename: str) -> str:
    path = ASSETS_DIR / filename
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return "<div class='avatar-fallback'>✦</div>"


def _performance_html(script: str, style: str, language: str, audio_bytes: bytes | None) -> str:
    """Render one animated VibeCast character with vibe-aware playback."""
    host_svg = _read_svg("host.svg")
    safe_script = html.escape(script).replace("\n", "<br>")
    js_script = json.dumps(script, ensure_ascii=False).replace("</", "<\\/")
    audio_markup = ""
    if audio_bytes:
        audio_b64 = base64.b64encode(audio_bytes).decode("ascii")
        audio_markup = f'<audio id="vibeAudio" preload="metadata" src="data:audio/mpeg;base64,{audio_b64}"></audio>'
    lang_code = "ur-PK" if language in ("Urdu", "Roman Urdu") else "en-US"
    performance_label = html.escape(f"One VibeCast Host · {style}")
    vibe_class = re.sub(r"[^a-z0-9-]", "", style.lower())
    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#fbf8f2;font-family:Arial,sans-serif;color:#302b2a}}
.stage{{position:relative;overflow:hidden;border:1px solid #e8dccb;border-radius:23px;background:radial-gradient(circle at 17% 18%,#fff7e9 0,#f3e6d3 40%,#e9e8db 100%);height:410px;min-height:0;padding:17px 18px 14px;display:flex;flex-direction:column}}
.stage:before,.stage:after{{content:'✦';position:absolute;color:#b29a6d55;font-size:30px;animation:twinkle 3s ease-in-out infinite}}.stage:before{{top:18px;right:24px}}.stage:after{{left:34px;bottom:65px;font-size:22px;animation-delay:1.2s}}
.topline{{display:flex;justify-content:space-between;align-items:center;gap:10px;position:relative;z-index:2}}
.tag{{font-size:10px;font-weight:800;letter-spacing:1.5px;color:#756d47;text-transform:uppercase}}.live{{display:flex;gap:6px;align-items:center;font-size:10px;color:#756d47;font-weight:800;letter-spacing:1px;text-transform:uppercase}}.dot{{width:7px;height:7px;background:#9aa071;border-radius:50%;box-shadow:0 0 0 4px #9aa07120}}
.bubble{{position:relative;z-index:2;margin:13px auto 0;max-width:720px;background:#fffdf9;border:1px solid #eadfce;border-radius:17px 17px 17px 5px;padding:12px 15px;color:#4a3b40;font-family:Georgia,serif;font-size:15px;line-height:1.5;box-shadow:0 8px 20px #6745500c;min-height:58px;height:115px;flex:0 0 115px;overflow-y:auto;}}
.cast{{flex:1;min-height:0;display:flex;justify-content:center;align-items:flex-end;position:relative;z-index:1;margin-top:0}}
.host{{height:225px;width:225px;transform-origin:50% 90%;animation:idleBob 3.4s ease-in-out infinite;filter:drop-shadow(0 8px 9px #67455018)}}.host svg{{width:100%;height:100%;display:block;object-fit:contain}}
#host-mouth{{transform-box:fill-box;transform-origin:center}}
.stage.vibe-energetic:not(.speaking) .host{{animation:energeticIdle .8s ease-in-out infinite}}
.stage.vibe-dramatic:not(.speaking) .host{{animation:dramaticIdle 4.2s ease-in-out infinite}}
.stage.vibe-funny:not(.speaking) .host{{animation:funnyIdle 1.7s ease-in-out infinite}}
.stage.vibe-emotional:not(.speaking) .host{{animation:emotionalIdle 3.8s ease-in-out infinite}}
.stage.vibe-professional:not(.speaking) .host{{animation:professionalIdle 3.2s ease-in-out infinite}}
.stage.speaking .host{{animation:speakingBob .32s ease-in-out infinite alternate}}.stage.speaking #host-mouth{{animation:mouthTalk .19s ease-in-out infinite alternate}}
.stage.speaking.vibe-energetic .host{{animation:energeticSpeak .27s ease-in-out infinite alternate}}
.stage.speaking.vibe-dramatic .host{{animation:dramaticSpeak .62s ease-in-out infinite alternate}}
.stage.speaking.vibe-funny .host{{animation:funnySpeak .38s ease-in-out infinite alternate}}
.stage.speaking.vibe-emotional .host{{animation:emotionalSpeak .72s ease-in-out infinite alternate}}
.stage.speaking.vibe-professional .host{{animation:professionalSpeak .46s ease-in-out infinite alternate}}
.controls{{position:relative;z-index:3;display:flex;align-items:center;gap:12px;background:#fffdf9d9;border:1px solid #e8dece;border-radius:15px;padding:9px 11px;margin-top:-1px}}
.play{{border:0;border-radius:50%;height:39px;width:39px;background:#674550;color:#fff;font-size:15px;cursor:pointer;display:grid;place-items:center;flex:0 0 auto;box-shadow:0 4px 9px #67455030}}
.track{{flex:1;min-width:0}}.tracktop{{display:flex;justify-content:space-between;gap:8px;font-size:10px;color:#756d47;font-weight:700;margin-bottom:6px}}.bars{{height:24px;display:flex;align-items:center;gap:3px;overflow:hidden}}.bar{{width:4px;min-width:3px;border-radius:5px;background:#c2b395;height:var(--h);transform-origin:center}}.stage.speaking .bar{{animation:wave .45s ease-in-out infinite alternate;animation-delay:var(--d)}}
.voicehint{{font-size:10px;color:#8a7f72;white-space:nowrap}}.hidden{{display:none}}
@keyframes idleBob{{0%,100%{{transform:translateY(0) rotate(-1deg)}}50%{{transform:translateY(-5px) rotate(1deg)}}}}
@keyframes speakingBob{{from{{transform:translateY(0) rotate(-1deg)}}to{{transform:translateY(-4px) rotate(1deg)}}}}
@keyframes energeticIdle{{0%,100%{{transform:translateY(0) rotate(-1deg)}}50%{{transform:translateY(-10px) rotate(1deg)}}}}
@keyframes dramaticIdle{{0%,100%{{transform:translateY(0) scale(1)}}50%{{transform:translateY(-4px) scale(1.015)}}}}
@keyframes funnyIdle{{0%,100%{{transform:translateY(0) rotate(-2deg)}}50%{{transform:translateY(-6px) rotate(2deg)}}}}
@keyframes emotionalIdle{{0%,100%{{transform:translateY(0) scale(1)}}50%{{transform:translateY(-3px) scale(1.01)}}}}
@keyframes professionalIdle{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-2px)}}}}
@keyframes energeticSpeak{{from{{transform:translateY(0) rotate(-2deg) scale(1)}}to{{transform:translateY(-7px) rotate(2deg) scale(1.025)}}}}
@keyframes dramaticSpeak{{from{{transform:translateY(0) scale(1)}}to{{transform:translateY(-3px) scale(1.01)}}}}
@keyframes funnySpeak{{from{{transform:translateY(0) rotate(-3deg)}}to{{transform:translateY(-5px) rotate(3deg)}}}}
@keyframes emotionalSpeak{{from{{transform:translateY(0) scale(1)}}to{{transform:translateY(-2px) scale(1.012)}}}}
@keyframes professionalSpeak{{from{{transform:translateY(0)}}to{{transform:translateY(-3px)}}}}
@keyframes mouthTalk{{from{{transform:scaleY(.35)}}to{{transform:scaleY(1.8)}}}}
@keyframes wave{{from{{transform:scaleY(.45)}}to{{transform:scaleY(1.4)}}}}
@keyframes twinkle{{0%,100%{{opacity:.35;transform:scale(.8) rotate(0)}}50%{{opacity:1;transform:scale(1.15) rotate(20deg)}}}}
</style></head><body>
<div class="stage vibe-{vibe_class}" id="stage">
 <div class="topline"><div class="tag">VibeCast · One host · Live performance</div><div class="live"><span class="dot"></span><span id="stateText">Ready when you are</span></div></div>
 <div class="bubble" id="bubble">{safe_script}</div>
 <div class="cast"><div class="host">{host_svg}</div></div>
 <div class="controls">
  <button class="play" id="playBtn" aria-label="Play voice">▶</button>
  <div class="track"><div class="tracktop"><span id="trackLabel">{performance_label}</span><span id="timeLabel">Tap to hear</span></div><div class="bars" id="bars"></div></div>
  <div class="voicehint">{('ElevenLabs v4 audio' if audio_bytes else 'Device speech fallback')}</div>
 </div>
 {audio_markup}
</div>
<script>
const scriptText = {js_script};
const languageCode = {json.dumps(lang_code)};
const stage=document.getElementById('stage'), btn=document.getElementById('playBtn'), stateText=document.getElementById('stateText'), timeLabel=document.getElementById('timeLabel');
const audio=document.getElementById('vibeAudio'); let speaking=false; let utterance=null;
const bars=document.getElementById('bars'); for(let i=0;i<52;i++){{const b=document.createElement('i');b.className='bar';b.style.setProperty('--h',(5+Math.abs(Math.sin(i*1.7))*17)+'px');b.style.setProperty('--d',(i%9)*.055+'s');bars.appendChild(b)}}
function setSpeaking(on){{speaking=on;stage.classList.toggle('speaking',on);btn.textContent=on?'Ⅱ':'▶';stateText.textContent=on?'Speaking now':'Ready when you are';timeLabel.textContent=on?'Live performance':'Tap to hear';}}
function stopSpeech(){{if('speechSynthesis' in window)window.speechSynthesis.cancel();setSpeaking(false)}}
if(audio){{audio.addEventListener('play',()=>setSpeaking(true));audio.addEventListener('pause',()=>setSpeaking(false));audio.addEventListener('ended',()=>setSpeaking(false));audio.addEventListener('timeupdate',()=>{{if(audio.duration)timeLabel.textContent=Math.floor(audio.currentTime)+'s / '+Math.floor(audio.duration)+'s'}})}}
btn.addEventListener('click',async()=>{{
 if(audio){{if(audio.paused){{try{{await audio.play()}}catch(e){{stateText.textContent='Playback blocked'}}}}else audio.pause();return;}}
 if(!('speechSynthesis' in window)){{stateText.textContent='Voice unavailable in this browser';return;}}
 if(speaking){{stopSpeech();return;}}
 utterance=new SpeechSynthesisUtterance(scriptText);utterance.lang=languageCode;
 const styleRate={{Energetic:1.12,Dramatic:0.88,Funny:1.05,Emotional:0.91,Professional:0.98}};
 const stylePitch={{Energetic:1.12,Dramatic:0.88,Funny:1.10,Emotional:0.92,Professional:1.00}};
 utterance.rate=styleRate[{json.dumps(style)}]||1;
 utterance.pitch=stylePitch[{json.dumps(style)}]||1;
 utterance.onstart=()=>setSpeaking(true);utterance.onend=()=>setSpeaking(false);utterance.onerror=()=>setSpeaking(false);
 let voices=window.speechSynthesis.getVoices();
 if(!voices.length){{await new Promise(resolve=>{{let done=false;const finish=()=>{{if(!done){{done=true;resolve()}}}};window.speechSynthesis.addEventListener('voiceschanged',finish,{{once:true}});setTimeout(finish,900);}});voices=window.speechSynthesis.getVoices();}}
 const languageVoices=voices.filter(v=>v.lang.toLowerCase().startsWith(languageCode.slice(0,2).toLowerCase()));
 const preferred=languageVoices.find(v=>/google us english|microsoft aria|microsoft guy|english/i.test(v.name));
 if(preferred){{utterance.voice=preferred;stateText.textContent='Device voice · '+preferred.name;}}else if(languageVoices.length){{utterance.voice=languageVoices[0];stateText.textContent='Using device voice';}}else if(voices.length){{stateText.textContent='Using browser default voice';}}
 window.speechSynthesis.speak(utterance);
}});
</script></body></html>"""


def _generate(
    words: str,
    style: str,
    language: str,
    length: str,
    intensity: int,
    make_ai_voice: bool,
) -> None:
    with st.spinner("Connecting your ideas into a moment..."):
        script, status, used_fallback, label = engine.generate_commentary(
            words=words,
            style=style,
            language=language,
            commentator_name=engine.CHARACTER_NAME,
            length=length,
            intensity=intensity,
        )
        tokens = engine.parse_keywords(words)
        audio_bytes = None
        voice_status = ""
        if len(tokens) >= 2 and make_ai_voice and _secret("ELEVENLABS_API_KEY"):
            with st.spinner("Your VibeCast character is warming up the microphone..."):
                audio_bytes, voice_status = engine.synthesize_expressive_audio(
                    text=script,
                    style=style,
                    language=language,
                    intensity=intensity,
                )
        elif len(tokens) >= 2 and not make_ai_voice:
            voice_status = "ElevenLabs narration is switched off. Play uses the same single animated character with browser/device speech."
        elif len(tokens) >= 2:
            voice_status = "ELEVENLABS_API_KEY is missing. Add it in Colab Secrets or .env to enable ElevenLabs narration."

    st.session_state.generated = {
        "script": script,
        "status": status,
        "used_fallback": used_fallback,
        "label": label,
        "words": words,
        "style": style,
        "language": language,
        "length": length,
        "intensity": intensity,
        "make_ai_voice": make_ai_voice,
        "audio": audio_bytes,
        "voice_status": voice_status,
        "created_at": datetime.now().strftime("%b %d · %I:%M %p"),
    }
    if len(tokens) >= 2:
        history = st.session_state.get("history", [])
        history.insert(0, st.session_state.generated.copy())
        st.session_state.history = history[:6]


_inject_css()
_secret("GROQ_API_KEY")
_secret("ELEVENLABS_API_KEY")
_secret("ELEVENLABS_VOICE_ID")

if "generated" not in st.session_state:
    st.session_state.generated = None
if "history" not in st.session_state:
    st.session_state.history = []

# Brand and hero
st.markdown(
    f"""<div class="brandline"><div class="brandmark">✦</div> VibeCast <span style="color:#a69a86;font-weight:500;letter-spacing:0">/ Creative Commentary Studio</span></div>""",
    unsafe_allow_html=True,
)
st.write("")
st.markdown(
    """
    <div class="hero">
      <div class="eyebrow">A little imagination goes a long way</div>
      <div class="hero-title">Give us a few words.<br>We'll give them a voice.</div>
      <div class="hero-copy">Throw in random ideas, unexpected objects, colours, names or feelings. One animated character will turn them into a moment worth hearing.</div>
    </div>
    """,
    unsafe_allow_html=True,
)
st.write("")

left, right = st.columns([1.08, 0.92], gap="large")
with left:
    st.markdown('<div class="panel-title">✦ Start with your imagination</div><div class="panel-sub">No sport, category or event required. Just add ingredients.</div>', unsafe_allow_html=True)
    with st.form("create_commentary", clear_on_submit=False):
        words = st.text_area(
            "Your words and ideas",
            placeholder="Umbrella, Fall, Red, Gucci, Fun...",
            height=142,
            help="Separate ideas with commas or put each one on a new line. Add 2–18 words or short phrases.",
        )
        st.markdown('<div class="mini-label">Pick the vibe</div>', unsafe_allow_html=True)
        style = st.radio(
            "Commentary tone",
            engine.STYLES,
            index=1,
            horizontal=True,
            format_func=lambda x: f"{engine.STYLE_EMOJI[x]} {x}",
            label_visibility="collapsed",
        )
        a, b = st.columns(2)
        with a:
            language = st.selectbox("Language", engine.LANGUAGES, index=0)
            length = st.selectbox("Commentary length", ["Quick hit", "Standard", "Extended"], index=1)
        with b:
            intensity = st.slider("Emotion intensity", min_value=1, max_value=5, value=4)
            st.caption("One character · one voice · only the selected vibe changes the delivery.")
        make_ai_voice = st.checkbox("Generate expressive ElevenLabs v4 narration", value=True)
        submitted = st.form_submit_button("✦ Create my commentary", use_container_width=True)
    if submitted:
        if len(engine.parse_keywords(words)) < 2:
            st.warning("Add at least two words or short phrases to get the story started.")
        elif len(engine.parse_keywords(words)) > 18:
            st.warning("Please use 18 words or fewer so the story stays focused.")
        else:
            _generate(words, style, language, length, intensity, make_ai_voice)
            st.rerun()

    st.markdown(
        """<div style="margin-top:1.1rem"><span class="mini-label">Need a spark?</span><br>
        <span class="word-example">Umbrella</span><span class="word-example">Fall</span><span class="word-example">Red</span><span class="word-example">Gucci</span><span class="word-example">Fun</span>
        </div>""",
        unsafe_allow_html=True,
    )

with right:
    if st.session_state.generated is None:
        st.markdown('<div class="panel-title">Meet your commentator</div><div class="panel-sub">One character. One voice. Choose a vibe to change the character’s delivery.</div>', unsafe_allow_html=True)
        host_svg = _read_svg("host.svg")
        preview_vibe = re.sub(r"[^a-z0-9-]", "", style.lower())
        st.markdown(
            f"""
            <div class="vibe-preview vibe-{preview_vibe}" style="background:linear-gradient(135deg,#f1e5d4,#e9eadb);border:1px solid #e5d9c7;border-radius:22px;padding:16px 12px 12px;overflow:hidden;">
              <div style="display:flex;align-items:center;justify-content:center;height:285px;">
                <div class="preview-host" style="width:100%;max-width:265px;">{host_svg}</div>
              </div>
              <div style="display:flex;gap:8px;justify-content:center;padding:0 0 6px;">
                <span style="background:#674550;color:white;padding:6px 14px;border-radius:30px;font-size:11px;font-weight:700">Your VibeCast Character</span>
              </div>
            </div>
            <style>
            .preview-host{{animation:previewIdle 3s ease-in-out infinite}}
            .vibe-preview.vibe-energetic .preview-host{{animation:previewBounce .8s ease-in-out infinite}}
            .vibe-preview.vibe-dramatic .preview-host{{animation:previewSlow 4s ease-in-out infinite}}
            .vibe-preview.vibe-funny .preview-host{{animation:previewTilt 1.5s ease-in-out infinite}}
            .vibe-preview.vibe-emotional .preview-host{{animation:previewGentle 3.6s ease-in-out infinite}}
            .vibe-preview.vibe-professional .preview-host{{animation:previewPoised 3s ease-in-out infinite}}
            .preview-host svg{{width:100%;height:100%;display:block}}
            @keyframes previewIdle{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-5px)}}}}
            @keyframes previewBounce{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-10px)}}}}
            @keyframes previewSlow{{0%,100%{{transform:translateY(0) scale(1)}}50%{{transform:translateY(-3px) scale(1.02)}}}}
            @keyframes previewTilt{{0%,100%{{transform:rotate(-2deg)}}50%{{transform:rotate(2deg) translateY(-5px)}}}}
            @keyframes previewGentle{{0%,100%{{transform:translateY(0) scale(1)}}50%{{transform:translateY(-2px) scale(1.01)}}}}
            @keyframes previewPoised{{0%,100%{{transform:translateY(0)}}50%{{transform:translateY(-2px)}}}}
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.markdown('<div class="panel-sub" style="margin-top:.7rem">The same character stays in place. Its movement reflects the selected vibe; when audio plays, its mouth animates in sync with playback.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="panel-title">Your character is performing below</div><div class="panel-sub">The one VibeCast character appears in the live performance stage. Its expression and movement follow the selected vibe.</div>', unsafe_allow_html=True)

# Results
result = st.session_state.generated
if result:
    st.write("")
    st.markdown('<div class="result-heading"><div><div class="mini-label">Your moment is ready</div><h2 style="margin:.1rem 0 0">Lights, mic, imagination.</h2></div><span class="result-pill">✦ Creative mix</span></div>', unsafe_allow_html=True)
    if result["used_fallback"]:
        st.info(result["status"])
    else:
        st.success(result["status"])

    stage_html = _performance_html(result["script"], result["style"], result["language"], result["audio"])
    components.html(stage_html, height=410, scrolling=False)

    c1, c2 = st.columns([1.15, 0.85], gap="large")
    with c1:
        st.markdown('<div class="mini-label">The written performance</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="commentary-box">{html.escape(result["script"]).replace(chr(10), "<br>")}</div>', unsafe_allow_html=True)
        st.caption(f"Character: VibeCast Host · Tone: {result['style']} · One voice · Language: {result['language']} · Created: {result['created_at']}")
    with c2:
        st.markdown('<div class="mini-label">Take it with you</div>', unsafe_allow_html=True)
        st.download_button(
            "↓ Download commentary (.txt)",
            data=result["script"].encode("utf-8"),
            file_name="vibecast_commentary.txt",
            mime="text/plain",
            use_container_width=True,
        )
        if result["audio"]:
            st.download_button(
                "↓ Download voice (.mp3)",
                data=result["audio"],
                file_name="vibecast_voice.mp3",
                mime="audio/mpeg",
                use_container_width=True,
            )
            st.caption(result["voice_status"])
        else:
            st.warning(result["voice_status"] or "ElevenLabs audio was not generated. Play will use the same on-screen character with browser/device narration.")
        if st.button("↻ Make another version", use_container_width=True):
            _generate(
                result["words"], result["style"], result["language"],
                result["length"], result["intensity"], result.get("make_ai_voice", True),
            )
            st.rerun()

if st.session_state.history:
    with st.expander("Your recent creations", expanded=False):
        for item in st.session_state.history:
            st.markdown(
                f"""<div class="history-item"><div style="display:flex;justify-content:space-between;gap:8px"><b style="color:{PLUM}">{html.escape(item['style'])} · {html.escape(item['created_at'])}</b><span style="color:{OLIVE};font-size:12px">{html.escape(', '.join(engine.parse_keywords(item['words'])[:5]))}</span></div><div style="font-family:Georgia,serif;color:#5a4b4d;margin-top:5px">{html.escape(item['script'][:220])}{'…' if len(item['script'])>220 else ''}</div></div>""",
                unsafe_allow_html=True,
            )

with st.expander("How VibeCast works", expanded=False):
    st.markdown(
        """1. **Your words** become the creative ingredients.
2. **Groq** connects them into a short commentary using the selected vibe.
3. **ElevenLabs v4** turns the script into expressive MP3 narration using one voice ID and vibe-specific emotion tags. The same character and speaker remain consistent.
4. If a key or service is unavailable, the app still creates a local fallback script and can use your browser's built-in speech voice.

The animated mouth and waveform react to audio playback. Browser speech uses the voices installed in the browser/device, so voice quality and Urdu support vary by device."""
    )

st.markdown(
    f"<div style='text-align:center;color:#9a8f81;font-size:11px;margin-top:2.4rem'>VibeCast · Made for unexpected ideas · <span style='color:{PLUM}'>Alabaster Gleam × Plum Wine × Olive Drab</span></div>",
    unsafe_allow_html=True,
)
