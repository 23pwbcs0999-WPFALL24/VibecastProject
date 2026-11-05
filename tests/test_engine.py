import os
import unittest
from pathlib import Path
from unittest.mock import patch

import commentary_engine as engine


class CommentaryEngineTests(unittest.TestCase):
    def test_parses_comma_newline_and_deduplicates(self):
        self.assertEqual(
            engine.parse_keywords("Umbrella, Fall\nRed; Gucci | Fun, umbrella"),
            ["Umbrella", "Fall", "Red", "Gucci", "Fun"],
        )

    def test_prompt_is_creative_and_requires_one_character(self):
        prompt = engine.build_system_prompt(style="Dramatic", language="English")
        self.assertIn("random words and phrases", prompt)
        self.assertIn("Dramatic", prompt)
        self.assertIn("exactly one recurring VibeCast character", prompt)
        self.assertIn("Do not introduce a co-host", prompt)
        self.assertNotIn("cricket", prompt.lower())
        self.assertNotIn("football", prompt.lower())
        self.assertNotIn("Milo", prompt)
        self.assertNotIn("Pip", prompt)
        self.assertNotIn("Nova", prompt)

    def test_five_styles_produce_different_fallbacks(self):
        words = ["Umbrella", "Fall", "Red", "Gucci", "Fun"]
        outputs = [engine.offline_commentary(words, style, "English") for style in engine.STYLES]
        self.assertEqual(len(set(outputs)), 5)
        for word in words:
            self.assertTrue(all(word.casefold() in output.casefold() for output in outputs))

    def test_quick_hit_fallback_keeps_all_keywords(self):
        words = ["Umbrella", "Fall", "Red", "Gucci", "Fun"]
        output = engine.offline_commentary(words, "Dramatic", "English", "Quick hit")
        for word in words:
            self.assertIn(word.casefold(), output.casefold())

    def test_missing_groq_key_uses_fallback(self):
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            script, status, used_fallback, label = engine.generate_commentary(
                "Umbrella, Fall, Red, Gucci, Fun", "Dramatic", "English"
            )
        self.assertTrue(script)
        self.assertTrue(used_fallback)
        self.assertIn("Offline", status)
        self.assertEqual(label, "Creative mix")

    def test_empty_or_single_keyword_is_rejected(self):
        script, status, used_fallback, _ = engine.generate_commentary("umbrella")
        self.assertIn("at least two", script)
        self.assertTrue(used_fallback)
        self.assertIn("Input needed", status)

    def test_too_many_keywords_is_rejected(self):
        raw = ",".join(f"word{i}" for i in range(19))
        script, status, used_fallback, _ = engine.generate_commentary(raw)
        self.assertIn("18 words or fewer", script)
        self.assertTrue(used_fallback)

    def test_urdu_and_roman_urdu_fallback_preserve_keywords(self):
        words = ["Umbrella", "Gucci", "Fun"]
        roman = engine.offline_commentary(words, "Energetic", "Roman Urdu")
        urdu = engine.offline_commentary(words, "Energetic", "Urdu")
        for word in words:
            self.assertIn(word, roman)
            self.assertIn(word, urdu)

    def test_single_character_voice_id_is_read_once(self):
        with patch.dict(os.environ, {"ELEVENLABS_VOICE_ID": "one-character-voice"}):
            self.assertEqual(engine.elevenlabs_voice_id(), "one-character-voice")

    def test_streamlit_interface_has_one_character_and_no_host_selector(self):
        app_source = (Path(__file__).resolve().parents[1] / "app.py").read_text(encoding="utf-8")
        self.assertNotIn("sidekick.svg", app_source)
        self.assertNotIn("Choose your host", app_source)
        self.assertNotIn("PERSONALITY_VOICE_PROFILES", app_source)
        self.assertIn("Your VibeCast Character", app_source)
        self.assertIn("if st.session_state.generated is None:", app_source)

    def test_five_vibes_produce_distinct_audio_tagged_transcripts(self):
        sample = "The red umbrella appears. Everyone turns around! What a moment!"
        tagged = {
            style: engine.decorate_elevenlabs_transcript(sample, style, 5)
            for style in engine.STYLES
        }
        self.assertEqual(len(set(tagged.values())), len(engine.STYLES))
        self.assertIn("[excited]", tagged["Energetic"])
        self.assertIn("[whispers]", tagged["Dramatic"])
        self.assertIn("[mischievously]", tagged["Funny"])
        self.assertIn("[softly]", tagged["Emotional"])
        self.assertIn("[confident]", tagged["Professional"])

    def test_tts_director_prompt_contains_one_character_and_selected_vibe(self):
        prompt = engine.build_tts_prompt(style="Dramatic", intensity=5)
        self.assertIn("One consistent VibeCast commentator", prompt)
        self.assertIn("dramatic", prompt.lower())
        self.assertIn("5/5", prompt)
        self.assertNotIn("sidekick", prompt.lower())

    def test_elevenlabs_request_uses_one_voice_v4_and_selected_vibe(self):
        audio = b"fake-mp3-audio"

        class FakeResponse:
            content = audio
            def raise_for_status(self):
                return None

        env = {
            "ELEVENLABS_API_KEY": "test-key",
            "ELEVENLABS_VOICE_ID": "one-character-voice-123",
        }
        with patch.dict(os.environ, env):
            with patch.object(engine.requests, "post", return_value=FakeResponse()) as post:
                result, status = engine.synthesize_expressive_audio(
                    "That is unexpected! What a moment!",
                    style="Funny",
                    intensity=5,
                )

        self.assertEqual(result, audio)
        self.assertIn("ElevenLabs v4", status)
        self.assertIn("VibeCast Host", status)
        self.assertIn("Funny", status)
        self.assertIn("one-character-voice-123", post.call_args.args[0])
        self.assertEqual(post.call_args.kwargs["headers"]["xi-api-key"], "test-key")
        body = post.call_args.kwargs["json"]
        self.assertEqual(body["model_id"], "eleven_v4")
        self.assertIn("[mischievously]", body["text"])
        self.assertIn("stability", body["voice_settings"])
        self.assertIn("similarity_boost", body["voice_settings"])
        self.assertNotIn("style", body["voice_settings"])
        self.assertNotIn("speed", body["voice_settings"])
        self.assertEqual(post.call_args.kwargs["params"]["output_format"], "mp3_44100_128")

    def test_all_vibes_use_same_character_voice_endpoint(self):
        class FakeResponse:
            content = b"fake-mp3-audio"
            def raise_for_status(self):
                return None

        env = {"ELEVENLABS_API_KEY": "test-key", "ELEVENLABS_VOICE_ID": "one-voice-only"}
        captured_urls = []
        with patch.dict(os.environ, env):
            with patch.object(
                engine.requests,
                "post",
                side_effect=lambda url, **kwargs: (captured_urls.append(url) or FakeResponse()),
            ):
                for vibe in engine.STYLES:
                    audio, status = engine.synthesize_expressive_audio(
                        "One character speaking in a different tone!", style=vibe
                    )
                    self.assertEqual(audio, b"fake-mp3-audio")
        self.assertEqual(len(captured_urls), 5)
        self.assertEqual(len(set(captured_urls)), 1)
        self.assertTrue(captured_urls[0].endswith("/one-voice-only"))

    def test_missing_elevenlabs_key_is_reported(self):
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": ""}):
            audio, status = engine.synthesize_expressive_audio("Hello", "Energetic")
        self.assertIsNone(audio)
        self.assertIn("ELEVENLABS_API_KEY", status)

    def test_missing_voice_id_is_reported(self):
        env = {"ELEVENLABS_API_KEY": "test-key", "ELEVENLABS_VOICE_ID": ""}
        with patch.dict(os.environ, env):
            audio, status = engine.synthesize_expressive_audio("Hello", "Energetic")
        self.assertIsNone(audio)
        self.assertIn("ELEVENLABS_VOICE_ID", status)

    def test_empty_audio_response_is_rejected(self):
        class FakeResponse:
            content = b""
            def raise_for_status(self):
                return None

        env = {"ELEVENLABS_API_KEY": "test-key", "ELEVENLABS_VOICE_ID": "one-voice"}
        with patch.dict(os.environ, env):
            with patch.object(engine.requests, "post", return_value=FakeResponse()):
                audio, status = engine.synthesize_expressive_audio("Hello", "Energetic")
        self.assertIsNone(audio)
        self.assertIn("empty audio", status)

    def test_text_over_limit_is_rejected_before_request(self):
        env = {"ELEVENLABS_API_KEY": "test-key", "ELEVENLABS_VOICE_ID": "one-voice"}
        with patch.dict(os.environ, env):
            with patch.object(engine.requests, "post") as post:
                audio, status = engine.synthesize_expressive_audio("x" * 10001)
        self.assertIsNone(audio)
        self.assertIn("10,000", status)
        post.assert_not_called()

    def test_performance_intensity_changes_v4_stability_setting(self):
        class FakeResponse:
            content = b"fake-mp3-audio"
            def raise_for_status(self):
                return None

        env = {
            "ELEVENLABS_API_KEY": "test-key",
            "ELEVENLABS_VOICE_ID": "one-voice-123",
        }
        captured = []

        def fake_post(*args, **kwargs):
            captured.append(kwargs["json"]["voice_settings"]["stability"])
            return FakeResponse()

        with patch.dict(os.environ, env):
            with patch.object(engine.requests, "post", side_effect=fake_post):
                engine.synthesize_expressive_audio(
                    "The rain was falling. What a moment!", "Dramatic", intensity=1
                )
                engine.synthesize_expressive_audio(
                    "The rain was falling. What a moment!", "Dramatic", intensity=5
                )
        self.assertEqual(len(captured), 2)
        self.assertLess(captured[1], captured[0])

    def test_unusual_activity_error_is_explained(self):
        class ErrorResponse:
            status_code = 401
            text = ""
            def json(self):
                return {"detail": {"status": "detected_unusual_activity", "message": "Free Tier access has been disabled."}}

        class FakeResponse:
            content = b""
            def raise_for_status(self):
                import requests
                err = requests.HTTPError("401 Client Error")
                err.response = ErrorResponse()
                raise err

        env = {"ELEVENLABS_API_KEY": "test-key", "ELEVENLABS_VOICE_ID": "one-voice"}
        with patch.dict(os.environ, env):
            with patch.object(engine.requests, "post", return_value=FakeResponse()):
                audio, status = engine.synthesize_expressive_audio("Hello there!", "Dramatic")
        self.assertIsNone(audio)
        self.assertIn("disabled Free Tier API access", status)
        self.assertIn("does not bypass", status)


if __name__ == "__main__":
    unittest.main(verbosity=2)
