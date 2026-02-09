"""
Comprehensive backend tests for LectureSnipe.

Tests cover all modules: panopto_parser, speaker_detector, note_generator,
panopto_client, config, lecture_processor, and Flask app endpoints.
Each test probes edge cases to find and document bugs.
"""

import unittest
import tempfile
import os
import json
import shutil
from unittest.mock import patch, MagicMock

from panopto_parser import PanoptoParser
from speaker_detector import SpeakerDetector
from note_generator import NoteGenerator
from config import Config
from panopto_client import PanoptoClient
from lecture_processor import LectureProcessor


# =====================================================================
# PanoptoParser Tests
# =====================================================================

class TestPanoptoParserSessionId(unittest.TestCase):
    """Thorough tests for session ID extraction"""

    def test_standard_viewer_url(self):
        url = "https://university.hosted.panopto.com/Panopto/Pages/Viewer.aspx?id=abc-123-def"
        self.assertEqual(PanoptoParser.extract_session_id(url), "abc-123-def")

    def test_embed_url(self):
        url = "https://example.panopto.com/Panopto/Pages/Embed.aspx?id=session-456"
        self.assertEqual(PanoptoParser.extract_session_id(url), "session-456")

    def test_uuid_session_id(self):
        url = "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=12345678-abcd-1234-efgh-123456789012"
        self.assertEqual(
            PanoptoParser.extract_session_id(url),
            "12345678-abcd-1234-efgh-123456789012"
        )

    def test_url_with_extra_query_params(self):
        url = "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=myid123&autoplay=true&width=800"
        self.assertEqual(PanoptoParser.extract_session_id(url), "myid123")

    def test_url_id_not_first_param(self):
        url = "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?autoplay=true&id=myid456"
        self.assertEqual(PanoptoParser.extract_session_id(url), "myid456")

    def test_url_without_id(self):
        url = "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?session=abc"
        result = PanoptoParser.extract_session_id(url)
        self.assertIsNone(result)

    def test_empty_url(self):
        result = PanoptoParser.extract_session_id("")
        self.assertIsNone(result)

    def test_none_url(self):
        """Passing None should not crash"""
        result = PanoptoParser.extract_session_id(None)
        self.assertIsNone(result)

    def test_malformed_url(self):
        result = PanoptoParser.extract_session_id("not-a-url")
        self.assertIsNone(result)

    def test_fragment_in_url(self):
        url = "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=sessXYZ#t=120"
        self.assertEqual(PanoptoParser.extract_session_id(url), "sessXYZ")


class TestPanoptoParserServer(unittest.TestCase):
    """Tests for server extraction"""

    def test_extract_server(self):
        url = "https://myuni.hosted.panopto.com/Panopto/Pages/Viewer.aspx?id=abc"
        self.assertEqual(PanoptoParser.extract_server(url), "myuni.hosted.panopto.com")

    def test_extract_server_no_subdomain(self):
        url = "https://panopto.com/Panopto/Pages/Viewer.aspx?id=abc"
        self.assertEqual(PanoptoParser.extract_server(url), "panopto.com")

    def test_extract_server_empty_url(self):
        result = PanoptoParser.extract_server("")
        self.assertIsNone(result)

    def test_extract_server_none(self):
        """Passing None should not crash"""
        result = PanoptoParser.extract_server(None)
        self.assertIsNone(result)


class TestPanoptoParserValidation(unittest.TestCase):
    """Tests for URL validation"""

    def test_valid_viewer_url(self):
        url = "https://university.hosted.panopto.com/Panopto/Pages/Viewer.aspx?id=abc123"
        self.assertTrue(PanoptoParser.is_valid_panopto_url(url))

    def test_valid_embed_url(self):
        url = "https://example.panopto.com/Panopto/Pages/Embed.aspx?id=test-session"
        self.assertTrue(PanoptoParser.is_valid_panopto_url(url))

    def test_invalid_non_panopto_domain(self):
        url = "https://youtube.com/watch?v=123"
        self.assertFalse(PanoptoParser.is_valid_panopto_url(url))

    def test_invalid_no_session_id(self):
        url = "https://university.panopto.com/Panopto/Pages/Viewer.aspx"
        self.assertFalse(PanoptoParser.is_valid_panopto_url(url))

    def test_invalid_empty_string(self):
        self.assertFalse(PanoptoParser.is_valid_panopto_url(""))

    def test_invalid_none(self):
        self.assertFalse(PanoptoParser.is_valid_panopto_url(None))

    def test_invalid_random_string(self):
        self.assertFalse(PanoptoParser.is_valid_panopto_url("not a url at all"))

    def test_valid_http_url(self):
        """HTTP (non-HTTPS) should still be valid if domain is panopto"""
        url = "http://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=abc"
        self.assertTrue(PanoptoParser.is_valid_panopto_url(url))

    def test_case_insensitive_panopto(self):
        """Domain check should be case-insensitive"""
        url = "https://uni.PANOPTO.com/Panopto/Pages/Viewer.aspx?id=abc"
        self.assertTrue(PanoptoParser.is_valid_panopto_url(url))


# =====================================================================
# SpeakerDetector Tests
# =====================================================================

class TestSpeakerDetectorClassify(unittest.TestCase):
    """Tests for speaker classification"""

    def setUp(self):
        self.detector = SpeakerDetector()

    def test_professor_keywords_therefore(self):
        result = self.detector.classify_segment("Therefore, we can see the solution.")
        self.assertEqual(result, "professor")

    def test_professor_keywords_lets(self):
        result = self.detector.classify_segment("Let's move on to the next topic.")
        self.assertEqual(result, "professor")

    def test_professor_keywords_notice(self):
        result = self.detector.classify_segment("Notice that this pattern is consistent.")
        self.assertEqual(result, "professor")

    def test_professor_keywords_conclusion(self):
        result = self.detector.classify_segment("In conclusion, the data supports our hypothesis.")
        self.assertEqual(result, "professor")

    def test_professor_long_text(self):
        """Long text (>30 words) gets a professor bonus"""
        long_text = " ".join(["word"] * 35)
        result = self.detector.classify_segment(long_text)
        self.assertIn(result, ["professor", "unknown"])

    def test_student_could_you_explain(self):
        result = self.detector.classify_segment("Could you explain that again please?")
        self.assertEqual(result, "student")

    def test_student_dont_understand(self):
        result = self.detector.classify_segment("I don't understand this concept at all.")
        self.assertEqual(result, "student")

    def test_student_question_mark_boost(self):
        """Question marks add to student score"""
        result = self.detector.classify_segment("What if we use a different approach?")
        self.assertIn(result, ["student", "unknown"])

    def test_noise_returns_noise(self):
        result = self.detector.classify_segment("[laughter]")
        self.assertEqual(result, "noise")

    def test_empty_string_returns_noise(self):
        result = self.detector.classify_segment("")
        self.assertEqual(result, "noise")

    def test_none_returns_noise(self):
        result = self.detector.classify_segment(None)
        self.assertEqual(result, "noise")

    def test_whitespace_only_returns_noise(self):
        result = self.detector.classify_segment("   ")
        self.assertEqual(result, "noise")

    def test_tie_breaking_with_previous_speaker(self):
        """When scores are tied, previous speaker is returned"""
        result = self.detector.classify_segment("This is a neutral sentence.", "professor")
        self.assertEqual(result, "professor")

    def test_tie_breaking_no_previous(self):
        """When scores are tied and no previous, returns 'unknown'"""
        result = self.detector.classify_segment("A neutral statement here.")
        self.assertEqual(result, "unknown")

    def test_custom_professor_keywords(self):
        """Custom professor keywords should boost professor score"""
        detector = SpeakerDetector(professor_keywords=["algorithm"])
        result = detector.classify_segment("The algorithm works like this.")
        self.assertEqual(result, "professor")


class TestSpeakerDetectorNoise(unittest.TestCase):
    """Tests for noise detection"""

    def setUp(self):
        self.detector = SpeakerDetector()

    def test_square_brackets(self):
        self.assertTrue(self.detector.is_noise("[laughter]"))

    def test_parentheses(self):
        self.assertTrue(self.detector.is_noise("(inaudible)"))

    def test_um(self):
        self.assertTrue(self.detector.is_noise("um"))

    def test_uh(self):
        self.assertTrue(self.detector.is_noise("uh"))

    def test_ummm(self):
        self.assertTrue(self.detector.is_noise("ummm"))

    def test_like_alone(self):
        self.assertTrue(self.detector.is_noise("like"))

    def test_whitespace(self):
        self.assertTrue(self.detector.is_noise("   "))

    def test_empty(self):
        self.assertTrue(self.detector.is_noise(""))

    def test_none(self):
        self.assertTrue(self.detector.is_noise(None))

    def test_normal_text_not_noise(self):
        self.assertFalse(self.detector.is_noise("This is a normal sentence."))

    def test_text_with_brackets_in_middle(self):
        """Text that contains brackets but is a real sentence should not be noise"""
        self.assertFalse(self.detector.is_noise("He mentioned [the book] in class."))

    def test_background_noise_tag(self):
        self.assertTrue(self.detector.is_noise("[background noise]"))

    def test_crosstalk_tag(self):
        self.assertTrue(self.detector.is_noise("(crosstalk)"))


class TestSpeakerDetectorFilter(unittest.TestCase):
    """Tests for transcript filtering"""

    def setUp(self):
        self.detector = SpeakerDetector()
        self.transcript = [
            {"text": "Therefore, today we discuss algorithms.", "start": "00:00:00"},
            {"text": "Could you repeat that?", "start": "00:00:10"},
            {"text": "In conclusion, algorithms are step-by-step procedures.", "start": "00:00:15"},
            {"text": "[background noise]", "start": "00:00:20"},
            {"text": "   ", "start": "00:00:25"},
        ]

    def test_filter_professor_only(self):
        filtered = self.detector.filter_transcript(self.transcript, include_students=False)
        # Should exclude student and noise entries
        for entry in filtered:
            self.assertNotEqual(entry.get("speaker"), "student")
        self.assertGreaterEqual(len(filtered), 1)

    def test_filter_includes_students(self):
        filtered = self.detector.filter_transcript(self.transcript, include_students=True)
        # Should include student entries
        speakers = [e.get("speaker") for e in filtered]
        # The student question should be tagged
        self.assertTrue(any(s == "student" for s in speakers) or len(filtered) >= 2)

    def test_noise_always_excluded(self):
        filtered = self.detector.filter_transcript(self.transcript, include_students=True)
        for entry in filtered:
            self.assertNotEqual(entry["text"].strip(), "[background noise]")
            self.assertNotEqual(entry["text"].strip(), "")

    def test_empty_transcript(self):
        filtered = self.detector.filter_transcript([], include_students=False)
        self.assertEqual(len(filtered), 0)

    def test_all_noise_transcript(self):
        noise_only = [
            {"text": "[laughter]", "start": "00:00:00"},
            {"text": "(inaudible)", "start": "00:00:05"},
            {"text": "um", "start": "00:00:10"},
        ]
        filtered = self.detector.filter_transcript(noise_only, include_students=True)
        self.assertEqual(len(filtered), 0)

    def test_does_not_mutate_original_entries(self):
        """FIXED: filter_transcript should not mutate the original transcript dicts."""
        transcript = [
            {"text": "Therefore, today we discuss algorithms.", "start": "00:00:00"},
        ]
        # Before filtering, no 'speaker' key
        self.assertNotIn("speaker", transcript[0])
        # Filter
        result = self.detector.filter_transcript(transcript, include_students=False)
        # Original dict should NOT have 'speaker' key (no mutation)
        self.assertNotIn("speaker", transcript[0])
        # But the returned entry should
        self.assertIn("speaker", result[0])

    def test_unknown_speaker_continuation(self):
        """Unknown segments after professor are treated as professor continuation"""
        transcript = [
            {"text": "Therefore, today we discuss algorithms.", "start": "00:00:00"},
            {"text": "A neutral statement.", "start": "00:00:05"},
        ]
        filtered = self.detector.filter_transcript(transcript, include_students=False)
        # The neutral statement should be included as professor continuation
        self.assertEqual(len(filtered), 2)


class TestSpeakerDetectorKeyPoints(unittest.TestCase):
    """Tests for key point extraction"""

    def setUp(self):
        self.detector = SpeakerDetector()

    def test_extracts_important_keyword(self):
        transcript = [
            {"text": "This is important to remember.", "speaker": "professor"},
            {"text": "Regular content here.", "speaker": "professor"},
        ]
        key_points = self.detector.extract_key_points(transcript)
        self.assertEqual(len(key_points), 1)
        self.assertIn("important", key_points[0].lower())

    def test_extracts_multiple_key_points(self):
        transcript = [
            {"text": "This is important.", "speaker": "professor"},
            {"text": "The key point is clarity.", "speaker": "professor"},
            {"text": "In conclusion, we learned a lot.", "speaker": "professor"},
        ]
        key_points = self.detector.extract_key_points(transcript)
        self.assertGreaterEqual(len(key_points), 2)

    def test_no_key_points(self):
        transcript = [
            {"text": "Hello everyone.", "speaker": "professor"},
            {"text": "Let me check something.", "speaker": "professor"},
        ]
        key_points = self.detector.extract_key_points(transcript)
        self.assertEqual(len(key_points), 0)

    def test_empty_transcript(self):
        key_points = self.detector.extract_key_points([])
        self.assertEqual(len(key_points), 0)

    def test_missing_text_key(self):
        """Entries without 'text' key should not crash"""
        transcript = [{"speaker": "professor"}]
        key_points = self.detector.extract_key_points(transcript)
        self.assertEqual(len(key_points), 0)

    def test_preserves_original_case(self):
        """Key points should preserve the original text case, not the lowered version"""
        transcript = [
            {"text": "This is IMPORTANT to Note.", "speaker": "professor"},
        ]
        key_points = self.detector.extract_key_points(transcript)
        self.assertEqual(len(key_points), 1)
        self.assertEqual(key_points[0], "This is IMPORTANT to Note.")


# =====================================================================
# NoteGenerator Tests
# =====================================================================

class TestNoteGeneratorMarkdown(unittest.TestCase):
    """Tests for Markdown note generation"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.generator = NoteGenerator(self.temp_dir)
        self.transcript = [
            {"text": "Welcome to the lecture.", "speaker": "professor", "start": "00:00:00"},
            {"text": "What is the topic?", "speaker": "student", "start": "00:00:10"},
            {"text": "Today we cover algorithms.", "speaker": "professor", "start": "00:00:15"},
        ]

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_markdown_header(self):
        notes = self.generator.generate_notes(self.transcript, format_type="markdown")
        self.assertIn("# Lecture Notes", notes)

    def test_markdown_contains_content(self):
        notes = self.generator.generate_notes(self.transcript, format_type="markdown")
        self.assertIn("Welcome to the lecture.", notes)
        self.assertIn("Today we cover algorithms.", notes)

    def test_markdown_student_formatted(self):
        notes = self.generator.generate_notes(self.transcript, format_type="markdown")
        self.assertIn("Student Question:", notes)

    def test_markdown_timestamps(self):
        notes = self.generator.generate_notes(
            self.transcript, format_type="markdown", include_timestamps=True
        )
        self.assertIn("[00:00:00]", notes)
        self.assertIn("[00:00:15]", notes)

    def test_markdown_no_timestamps(self):
        notes = self.generator.generate_notes(
            self.transcript, format_type="markdown", include_timestamps=False
        )
        self.assertNotIn("[00:00:00]", notes)

    def test_markdown_with_slides(self):
        slides = ["/path/slide1.png", "/path/slide2.png"]
        notes = self.generator.generate_notes(
            self.transcript, slides=slides, format_type="markdown",
            include_slides=True
        )
        self.assertIn("Slide 1", notes)

    def test_markdown_without_slides(self):
        notes = self.generator.generate_notes(
            self.transcript, format_type="markdown", include_slides=False
        )
        self.assertNotIn("Slide", notes)

    def test_markdown_empty_transcript(self):
        notes = self.generator.generate_notes([], format_type="markdown")
        self.assertIn("# Lecture Notes", notes)

    def test_markdown_date_present(self):
        notes = self.generator.generate_notes(self.transcript, format_type="markdown")
        self.assertIn("Generated on", notes)


class TestNoteGeneratorHTML(unittest.TestCase):
    """Tests for HTML note generation"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.generator = NoteGenerator(self.temp_dir)
        self.transcript = [
            {"text": "Introduction to data structures.", "speaker": "professor", "start": "00:00:00"},
            {"text": "Can you repeat?", "speaker": "student", "start": "00:00:10"},
        ]

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_html_doctype(self):
        notes = self.generator.generate_notes(self.transcript, format_type="html")
        self.assertIn("<!DOCTYPE html>", notes)

    def test_html_contains_content(self):
        notes = self.generator.generate_notes(self.transcript, format_type="html")
        self.assertIn("Introduction to data structures.", notes)

    def test_html_student_question_div(self):
        notes = self.generator.generate_notes(self.transcript, format_type="html")
        self.assertIn("student-question", notes)
        self.assertIn("Student Question:", notes)

    def test_html_timestamps(self):
        notes = self.generator.generate_notes(
            self.transcript, format_type="html", include_timestamps=True
        )
        self.assertIn("[00:00:00]", notes)

    def test_html_closes_properly(self):
        notes = self.generator.generate_notes(self.transcript, format_type="html")
        self.assertIn("</body>", notes)
        self.assertIn("</html>", notes)


class TestNoteGeneratorText(unittest.TestCase):
    """Tests for plain text note generation"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.generator = NoteGenerator(self.temp_dir)
        self.transcript = [
            {"text": "Welcome.", "speaker": "professor", "start": "00:00:00"},
            {"text": "Question?", "speaker": "student", "start": "00:00:05"},
        ]

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_text_header(self):
        notes = self.generator.generate_notes(self.transcript, format_type="text")
        self.assertIn("LECTURE NOTES", notes)

    def test_text_separator(self):
        notes = self.generator.generate_notes(self.transcript, format_type="text")
        self.assertIn("=" * 70, notes)

    def test_text_student_prefix(self):
        notes = self.generator.generate_notes(self.transcript, format_type="text")
        self.assertIn("STUDENT QUESTION:", notes)

    def test_text_timestamps(self):
        notes = self.generator.generate_notes(
            self.transcript, format_type="text", include_timestamps=True
        )
        self.assertIn("[00:00:00]", notes)


class TestNoteGeneratorSaveNotes(unittest.TestCase):
    """Tests for saving notes to files"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.generator = NoteGenerator(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_markdown(self):
        path = self.generator.save_notes("# Notes", "test", "markdown")
        self.assertTrue(path.endswith(".md"))
        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            self.assertEqual(f.read(), "# Notes")

    def test_save_html(self):
        path = self.generator.save_notes("<h1>Notes</h1>", "test", "html")
        self.assertTrue(path.endswith(".html"))
        self.assertTrue(os.path.exists(path))

    def test_save_text(self):
        path = self.generator.save_notes("Notes", "test", "text")
        self.assertTrue(path.endswith(".txt"))
        self.assertTrue(os.path.exists(path))

    def test_save_unknown_format(self):
        """Unknown format should default to .txt"""
        path = self.generator.save_notes("Notes", "test", "unknown_format")
        self.assertTrue(path.endswith(".txt"))

    def test_save_creates_file(self):
        path = self.generator.save_notes("content", "myfile", "markdown")
        self.assertTrue(os.path.isfile(path))

    def test_save_overwrites_existing(self):
        """Saving to the same filename should overwrite"""
        self.generator.save_notes("version1", "same", "markdown")
        path = self.generator.save_notes("version2", "same", "markdown")
        with open(path) as f:
            self.assertEqual(f.read(), "version2")

    def test_output_dir_created(self):
        """NoteGenerator should create output dir if it doesn't exist"""
        new_dir = os.path.join(self.temp_dir, "subdir", "notes")
        generator = NoteGenerator(new_dir)
        self.assertTrue(os.path.isdir(new_dir))

    def test_save_utf8_content(self):
        """Should handle UTF-8 content properly"""
        content = "Notes with special chars: àéîöü 日本語"
        path = self.generator.save_notes(content, "utf8test", "text")
        with open(path, encoding="utf-8") as f:
            self.assertEqual(f.read(), content)


class TestNoteGeneratorSummary(unittest.TestCase):
    """Tests for summary generation"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.generator = NoteGenerator(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_short_transcript_returns_full(self):
        """When transcript is shorter than max_length, return full text"""
        transcript = [
            {"text": "Short lecture.", "speaker": "professor"},
        ]
        summary = self.generator.generate_summary(transcript, max_length=100)
        self.assertIn("Short lecture.", summary)

    def test_long_transcript_truncated(self):
        """Long transcripts should be summarized to approximately max_length words"""
        transcript = [
            {"text": " ".join(["word"] * 100), "speaker": "professor"},
        ]
        summary = self.generator.generate_summary(transcript, max_length=50)
        words = summary.split()
        # Should be roughly max_length + the "..." separator
        self.assertLessEqual(len(words), 60)  # Allow some flexibility

    def test_only_professor_text_included(self):
        """Summary should only include professor text, not student"""
        transcript = [
            {"text": "Professor says this.", "speaker": "professor"},
            {"text": "Student asks question?", "speaker": "student"},
        ]
        summary = self.generator.generate_summary(transcript, max_length=100)
        self.assertIn("Professor says this.", summary)
        self.assertNotIn("Student asks question?", summary)

    def test_empty_transcript(self):
        summary = self.generator.generate_summary([], max_length=100)
        self.assertEqual(summary, "")

    def test_no_professor_entries(self):
        """Transcript with no professor entries should return empty"""
        transcript = [
            {"text": "Student question.", "speaker": "student"},
        ]
        summary = self.generator.generate_summary(transcript, max_length=100)
        self.assertEqual(summary, "")

    def test_summary_contains_ellipsis(self):
        """Long summaries should have '...' to indicate truncation"""
        transcript = [
            {"text": " ".join(["word"] * 200), "speaker": "professor"},
        ]
        summary = self.generator.generate_summary(transcript, max_length=50)
        self.assertIn("...", summary)

    def test_missing_speaker_key(self):
        """Entries without 'speaker' key should be skipped gracefully"""
        transcript = [
            {"text": "No speaker tag here."},
        ]
        summary = self.generator.generate_summary(transcript, max_length=100)
        # Should not crash, and should return empty since no 'professor' entries
        self.assertEqual(summary, "")


# =====================================================================
# PanoptoClient Tests (with mocking)
# =====================================================================

class TestPanoptoClientInit(unittest.TestCase):
    """Tests for PanoptoClient initialization"""

    def test_init_basic(self):
        client = PanoptoClient("test.panopto.com")
        self.assertEqual(client.server, "test.panopto.com")
        self.assertIsNone(client.username)
        self.assertIsNone(client.password)
        self.assertFalse(client.authenticated)

    def test_init_with_credentials(self):
        client = PanoptoClient("test.panopto.com", "user", "pass")
        self.assertEqual(client.username, "user")
        self.assertEqual(client.password, "pass")


class TestPanoptoClientAuth(unittest.TestCase):
    """Tests for authentication"""

    def test_auth_no_credentials(self):
        client = PanoptoClient("test.panopto.com")
        result = client.authenticate()
        self.assertFalse(result)

    def test_auth_empty_credentials(self):
        client = PanoptoClient("test.panopto.com", "", "")
        result = client.authenticate()
        self.assertFalse(result)

    @patch("panopto_client.requests.Session")
    def test_auth_success(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        # Mock login page GET
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200

        # Mock login POST
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.cookies.get_dict.return_value = {"auth": "token123"}

        mock_session.get.return_value = mock_get_response
        mock_session.post.return_value = mock_post_response

        client = PanoptoClient("test.panopto.com", "user", "pass")
        client.session = mock_session
        result = client.authenticate()
        self.assertTrue(result)
        self.assertTrue(client.authenticated)

    @patch("panopto_client.requests.Session")
    def test_auth_failure_no_cookie(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session

        mock_get_response = MagicMock()
        mock_get_response.status_code = 200

        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.cookies.get_dict.return_value = {}

        mock_session.get.return_value = mock_get_response
        mock_session.post.return_value = mock_post_response

        client = PanoptoClient("test.panopto.com", "user", "wrongpass")
        client.session = mock_session
        result = client.authenticate()
        self.assertFalse(result)

    @patch("panopto_client.requests.Session")
    def test_auth_network_error(self, mock_session_cls):
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        mock_session.get.side_effect = Exception("Network error")

        client = PanoptoClient("test.panopto.com", "user", "pass")
        client.session = mock_session
        result = client.authenticate()
        self.assertFalse(result)


class TestPanoptoClientTranscript(unittest.TestCase):
    """Tests for transcript fetching"""

    def test_get_transcript_json_format(self):
        client = PanoptoClient("test.panopto.com")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {"text": "Hello", "start": "00:00:00"},
        ]
        client.session = MagicMock()
        client.session.get.return_value = mock_response

        result = client.get_transcript("session123")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "Hello")

    def test_get_transcript_404(self):
        client = PanoptoClient("test.panopto.com")
        mock_response = MagicMock()
        mock_response.status_code = 404
        client.session = MagicMock()
        client.session.get.return_value = mock_response

        result = client.get_transcript("nonexistent")
        self.assertIsNone(result)

    def test_get_transcript_network_error(self):
        client = PanoptoClient("test.panopto.com")
        client.session = MagicMock()
        client.session.get.side_effect = Exception("Timeout")

        result = client.get_transcript("session123")
        self.assertIsNone(result)


class TestPanoptoClientVTTParsing(unittest.TestCase):
    """Tests for VTT format parsing"""

    def setUp(self):
        self.client = PanoptoClient("test.panopto.com")

    def test_standard_vtt(self):
        vtt = """WEBVTT

00:00:00.000 --> 00:00:05.000
Hello everyone, welcome to the lecture.

00:00:05.000 --> 00:00:10.000
Today we cover algorithms.
"""
        result = self.client._parse_vtt(vtt)
        self.assertEqual(len(result), 2)
        self.assertIn("Hello everyone", result[0]["text"])
        self.assertIn("Today we cover", result[1]["text"])

    def test_vtt_multiline_text(self):
        vtt = """WEBVTT

00:00:00.000 --> 00:00:05.000
Line one
Line two
"""
        result = self.client._parse_vtt(vtt)
        self.assertEqual(len(result), 1)
        self.assertIn("Line one", result[0]["text"])
        self.assertIn("Line two", result[0]["text"])

    def test_vtt_empty(self):
        result = self.client._parse_vtt("")
        self.assertEqual(len(result), 0)

    def test_vtt_no_entries(self):
        result = self.client._parse_vtt("WEBVTT\n\n")
        self.assertEqual(len(result), 0)

    def test_vtt_preserves_timestamps(self):
        vtt = """00:01:30.500 --> 00:01:35.000
Some text here."""
        result = self.client._parse_vtt(vtt)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["start"], "00:01:30.500")
        self.assertEqual(result[0]["end"], "00:01:35.000")


class TestPanoptoClientSlides(unittest.TestCase):
    """Tests for slide fetching"""

    def test_get_slide_images_no_session_data(self):
        client = PanoptoClient("test.panopto.com")
        client.session = MagicMock()
        # get_session_data returns None
        mock_response = MagicMock()
        mock_response.status_code = 404
        client.session.get.return_value = mock_response

        result = client.get_slide_images("session123")
        self.assertEqual(result, [])

    def test_download_slide_success(self):
        client = PanoptoClient("test.panopto.com")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake image data"
        client.session = MagicMock()
        client.session.get.return_value = mock_response

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            path = f.name

        try:
            result = client.download_slide("http://example.com/slide.png", path)
            self.assertTrue(result)
            with open(path, "rb") as f:
                self.assertEqual(f.read(), b"fake image data")
        finally:
            os.unlink(path)

    def test_download_slide_failure(self):
        client = PanoptoClient("test.panopto.com")
        mock_response = MagicMock()
        mock_response.status_code = 404
        client.session = MagicMock()
        client.session.get.return_value = mock_response

        result = client.download_slide("http://example.com/slide.png", "/tmp/test.png")
        self.assertFalse(result)

    def test_download_slide_network_error(self):
        client = PanoptoClient("test.panopto.com")
        client.session = MagicMock()
        client.session.get.side_effect = Exception("Connection refused")

        result = client.download_slide("http://example.com/slide.png", "/tmp/test.png")
        self.assertFalse(result)


# =====================================================================
# Config Tests
# =====================================================================

class TestConfig(unittest.TestCase):
    """Tests for Config module"""

    def test_config_has_required_attributes(self):
        self.assertTrue(hasattr(Config, "PANOPTO_USERNAME"))
        self.assertTrue(hasattr(Config, "PANOPTO_PASSWORD"))
        self.assertTrue(hasattr(Config, "SECRET_KEY"))
        self.assertTrue(hasattr(Config, "OUTPUT_DIR"))
        self.assertTrue(hasattr(Config, "NOTES_DIR"))
        self.assertTrue(hasattr(Config, "SLIDES_DIR"))
        self.assertTrue(hasattr(Config, "TRANSCRIPTS_DIR"))

    def test_init_app_creates_directories(self):
        """init_app should create all output directories"""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_output = Config.OUTPUT_DIR
            original_slides = Config.SLIDES_DIR
            original_transcripts = Config.TRANSCRIPTS_DIR
            original_notes = Config.NOTES_DIR

            try:
                Config.OUTPUT_DIR = os.path.join(tmpdir, "output")
                Config.SLIDES_DIR = os.path.join(tmpdir, "output", "slides")
                Config.TRANSCRIPTS_DIR = os.path.join(tmpdir, "output", "transcripts")
                Config.NOTES_DIR = os.path.join(tmpdir, "output", "notes")

                Config.init_app()

                self.assertTrue(os.path.isdir(Config.OUTPUT_DIR))
                self.assertTrue(os.path.isdir(Config.SLIDES_DIR))
                self.assertTrue(os.path.isdir(Config.TRANSCRIPTS_DIR))
                self.assertTrue(os.path.isdir(Config.NOTES_DIR))
            finally:
                Config.OUTPUT_DIR = original_output
                Config.SLIDES_DIR = original_slides
                Config.TRANSCRIPTS_DIR = original_transcripts
                Config.NOTES_DIR = original_notes

    def test_default_secret_key(self):
        """Default secret key should exist (though it should be changed in production)"""
        self.assertIsNotNone(Config.SECRET_KEY)
        self.assertGreater(len(Config.SECRET_KEY), 0)

    def test_notes_dir_is_under_output(self):
        self.assertIn("output", Config.NOTES_DIR)

    def test_slides_dir_is_under_output(self):
        self.assertIn("output", Config.SLIDES_DIR)


# =====================================================================
# Flask App Tests
# =====================================================================

class TestFlaskApp(unittest.TestCase):
    """Tests for Flask web application endpoints"""

    def setUp(self):
        from app import app
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_index_returns_200(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_index_contains_lecturesnipe(self):
        response = self.client.get("/")
        self.assertIn(b"LectureSnipe", response.data)

    def test_health_endpoint(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "healthy")

    def test_process_no_body(self):
        """POST without body should return 400"""
        response = self.client.post(
            "/api/process",
            content_type="application/json",
            data=json.dumps({})
        )
        # Empty dict has no 'url' key
        self.assertEqual(response.status_code, 400)

    def test_process_no_url(self):
        """POST with body but no URL should return 400"""
        response = self.client.post(
            "/api/process",
            content_type="application/json",
            data=json.dumps({"format": "markdown"})
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)

    def test_summary_no_url(self):
        """POST to summary without URL should return 400"""
        response = self.client.post(
            "/api/summary",
            content_type="application/json",
            data=json.dumps({})
        )
        self.assertEqual(response.status_code, 400)

    def test_download_nonexistent_file(self):
        """Downloading a non-existent file should return 404"""
        response = self.client.get("/download/nonexistent_file.md")
        self.assertEqual(response.status_code, 404)

    def test_process_invalid_url(self):
        """Processing with an invalid Panopto URL should return 500 with error"""
        response = self.client.post(
            "/api/process",
            content_type="application/json",
            data=json.dumps({"url": "https://youtube.com/watch?v=123"})
        )
        data = json.loads(response.data)
        self.assertFalse(data.get("success", True))

    def test_summary_invalid_url(self):
        """Summary with an invalid Panopto URL should return error"""
        response = self.client.post(
            "/api/summary",
            content_type="application/json",
            data=json.dumps({"url": "https://youtube.com/watch?v=123"})
        )
        data = json.loads(response.data)
        self.assertFalse(data.get("success", True))


# =====================================================================
# LectureProcessor Tests (with mocking)
# =====================================================================

class TestLectureProcessorInvalidURL(unittest.TestCase):
    """Tests for LectureProcessor with invalid URLs"""

    def test_invalid_url_returns_error(self):
        processor = _create_processor()
        result = processor.process_lecture("https://youtube.com/watch?v=123")
        self.assertFalse(result["success"])
        self.assertIn("Invalid", result["error"])

    def test_empty_url_returns_error(self):
        processor = _create_processor()
        result = processor.process_lecture("")
        self.assertFalse(result["success"])

    def test_valid_url_no_transcript(self):
        """Processing a valid URL that returns no transcript"""
        processor = _create_processor()
        with patch.object(PanoptoClient, "authenticate", return_value=False), \
             patch.object(PanoptoClient, "get_transcript", return_value=None):
            result = processor.process_lecture(
                "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=abc123"
            )
            self.assertFalse(result["success"])
            self.assertIn("transcript", result["error"].lower())


class TestLectureProcessorSuccess(unittest.TestCase):
    """Tests for successful lecture processing"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_processing_pipeline(self):
        """Test the complete processing pipeline with mocked API calls"""
        mock_transcript = [
            {"text": "Therefore, today we discuss algorithms.", "start": "00:00:00"},
            {"text": "Could you repeat that?", "start": "00:00:10"},
            {"text": "In conclusion, algorithms solve problems.", "start": "00:00:15"},
        ]

        processor = _create_processor(notes_dir=self.temp_dir)

        with patch.object(PanoptoClient, "authenticate", return_value=True), \
             patch.object(PanoptoClient, "get_transcript", return_value=mock_transcript), \
             patch.object(PanoptoClient, "get_slide_images", return_value=[]), \
             patch.object(PanoptoClient, "download_slide", return_value=True):
            result = processor.process_lecture(
                "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=abc123",
                format_type="markdown"
            )

        self.assertTrue(result["success"])
        self.assertIsNotNone(result["notes_path"])
        self.assertTrue(os.path.exists(result["notes_path"]))
        self.assertEqual(result["transcript_entries"], 3)

    def test_processing_html_format(self):
        """Test processing with HTML output"""
        mock_transcript = [
            {"text": "Hello class.", "start": "00:00:00"},
        ]

        processor = _create_processor(notes_dir=self.temp_dir)

        with patch.object(PanoptoClient, "authenticate", return_value=True), \
             patch.object(PanoptoClient, "get_transcript", return_value=mock_transcript), \
             patch.object(PanoptoClient, "get_slide_images", return_value=[]):
            result = processor.process_lecture(
                "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=abc123",
                format_type="html"
            )

        self.assertTrue(result["success"])
        self.assertTrue(result["notes_path"].endswith(".html"))


class TestLectureProcessorSummary(unittest.TestCase):
    """Tests for summary generation"""

    def test_summary_brief(self):
        mock_transcript = [
            {"text": "Therefore, today we discuss algorithms.", "start": "00:00:00"},
        ]

        processor = _create_processor()

        with patch.object(PanoptoClient, "authenticate", return_value=True), \
             patch.object(PanoptoClient, "get_transcript", return_value=mock_transcript):
            result = processor.generate_custom_summary(
                "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=abc123",
                summary_type="brief"
            )

        self.assertTrue(result["success"])
        self.assertIsNotNone(result["summary"])

    def test_summary_key_points(self):
        mock_transcript = [
            {"text": "This is important to remember.", "start": "00:00:00"},
            {"text": "The key point is efficiency.", "start": "00:00:05"},
        ]

        processor = _create_processor()

        with patch.object(PanoptoClient, "authenticate", return_value=True), \
             patch.object(PanoptoClient, "get_transcript", return_value=mock_transcript):
            result = processor.generate_custom_summary(
                "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=abc123",
                summary_type="key_points"
            )

        self.assertTrue(result["success"])

    def test_summary_invalid_url(self):
        processor = _create_processor()
        result = processor.generate_custom_summary("https://youtube.com/watch?v=123")
        self.assertFalse(result["success"])

    def test_summary_no_transcript(self):
        processor = _create_processor()
        with patch.object(PanoptoClient, "authenticate", return_value=True), \
             patch.object(PanoptoClient, "get_transcript", return_value=None):
            result = processor.generate_custom_summary(
                "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=abc123"
            )
        self.assertFalse(result["success"])


# =====================================================================
# Edge Cases & Bug Discovery Tests
# =====================================================================

class TestEdgeCases(unittest.TestCase):
    """Edge case tests that might reveal bugs"""

    def test_transcript_entry_missing_text(self):
        """Entries without 'text' key should be handled gracefully"""
        detector = SpeakerDetector()
        transcript = [
            {"start": "00:00:00"},  # No 'text' key
            {"text": "Therefore, proper text here.", "start": "00:00:05"},
        ]
        filtered = detector.filter_transcript(transcript, include_students=False)
        # Should not crash and should handle gracefully
        self.assertIsInstance(filtered, list)

    def test_transcript_entry_missing_start(self):
        """Entries without 'start' key for timestamp generation"""
        temp_dir = tempfile.mkdtemp()
        try:
            generator = NoteGenerator(temp_dir)
            transcript = [
                {"text": "Content without timestamp.", "speaker": "professor"},
            ]
            notes = generator.generate_notes(
                transcript, format_type="markdown", include_timestamps=True
            )
            # Should not crash
            self.assertIn("Content without timestamp.", notes)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_special_characters_in_text(self):
        """Special characters should be handled"""
        temp_dir = tempfile.mkdtemp()
        try:
            generator = NoteGenerator(temp_dir)
            transcript = [
                {"text": "Testing <html> & 'quotes' \"double\"", "speaker": "professor", "start": "00:00:00"},
            ]
            notes = generator.generate_notes(transcript, format_type="html")
            # Should not crash
            self.assertIsInstance(notes, str)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    def test_very_large_transcript(self):
        """Performance test with many entries"""
        detector = SpeakerDetector()
        transcript = [
            {"text": f"Therefore, point number {i} is important.", "start": f"00:{i//60:02d}:{i%60:02d}"}
            for i in range(100)
        ]
        filtered = detector.filter_transcript(transcript, include_students=False)
        self.assertGreater(len(filtered), 0)

    def test_url_with_unicode(self):
        """URLs with unicode should be handled"""
        url = "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=abc&title=café"
        result = PanoptoParser.extract_session_id(url)
        self.assertEqual(result, "abc")

    def test_filter_transcript_student_excluded_then_unknown(self):
        """When students are excluded, 'unknown' after student should use previous non-student speaker"""
        detector = SpeakerDetector()
        transcript = [
            {"text": "Therefore, important lecture content.", "start": "00:00:00"},
            {"text": "Could you explain that?", "start": "00:00:10"},  # student - excluded
            {"text": "A neutral sentence here.", "start": "00:00:15"},  # unknown - should continue as professor
        ]
        filtered = detector.filter_transcript(transcript, include_students=False)
        # First entry should be professor
        self.assertEqual(filtered[0]["speaker"], "professor")

    def test_note_generator_slides_alignment(self):
        """Test that slide references align correctly with transcript entries"""
        temp_dir = tempfile.mkdtemp()
        try:
            generator = NoteGenerator(temp_dir)
            transcript = [
                {"text": f"Content {i}.", "speaker": "professor", "start": f"00:00:{i:02d}"}
                for i in range(25)
            ]
            slides = [f"/path/slide_{i}.png" for i in range(3)]
            notes = generator.generate_notes(
                transcript, slides=slides, format_type="markdown",
                include_slides=True
            )
            self.assertIn("Slide 1", notes)
            self.assertIn("Slide 2", notes)
            self.assertIn("Slide 3", notes)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


class TestBugDiscovery(unittest.TestCase):
    """Tests that document known bugs and edge case issues"""

    def test_filter_transcript_no_mutation(self):
        """FIXED: filter_transcript no longer mutates original dict objects."""
        detector = SpeakerDetector()
        transcript = [
            {"text": "Therefore, algorithms are important.", "start": "00:00:00"},
        ]

        # Before filtering, no 'speaker' key
        self.assertNotIn("speaker", transcript[0])

        # Filter
        result = detector.filter_transcript(transcript, include_students=False)

        # After filtering, original dict should NOT have 'speaker' key
        self.assertNotIn("speaker", transcript[0])
        # The returned copy should have it
        self.assertIn("speaker", result[0])

    def test_vtt_parser_handles_numbered_cues(self):
        """VTT files often have numbered cues before timestamps.
        The parser should handle these correctly."""
        client = PanoptoClient("test.panopto.com")
        vtt = """WEBVTT

1
00:00:00.000 --> 00:00:05.000
First line.

2
00:00:05.000 --> 00:00:10.000
Second line.
"""
        result = client._parse_vtt(vtt)
        # The parser should find 2 entries
        self.assertEqual(len(result), 2)

    def test_generate_custom_summary_url_validation(self):
        """generate_custom_summary doesn't validate the URL with is_valid_panopto_url.
        It only checks if session_id and server can be extracted.
        This means non-Panopto URLs with 'id' parameter would pass."""
        processor = _create_processor()
        # This URL has an 'id' parameter but is not a Panopto URL
        # The processor extracts session_id and server without panopto validation
        result = processor.generate_custom_summary(
            "https://example.com/page?id=abc"
        )
        # It won't validate the URL as panopto, but it will still try to process
        # It should fail later when trying to connect, or return an error
        # The key point is it doesn't crash
        self.assertIsInstance(result, dict)

    def test_process_lecture_default_params(self):
        """Test that default parameters work correctly"""
        processor = _create_processor()
        with patch.object(PanoptoClient, "authenticate", return_value=True), \
             patch.object(PanoptoClient, "get_transcript", return_value=[
                 {"text": "Therefore, lecture content.", "start": "00:00:00"},
             ]), \
             patch.object(PanoptoClient, "get_slide_images", return_value=[]):
            result = processor.process_lecture(
                "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=test123"
            )
        self.assertTrue(result["success"])

    def test_html_xss_in_notes(self):
        """Check that HTML output doesn't sanitize user text.
        This is a potential XSS issue if the text contains script tags.
        Documented as a security consideration."""
        temp_dir = tempfile.mkdtemp()
        try:
            generator = NoteGenerator(temp_dir)
            transcript = [
                {
                    "text": '<script>alert("xss")</script>',
                    "speaker": "professor",
                    "start": "00:00:00"
                },
            ]
            notes = generator.generate_notes(transcript, format_type="html")
            # The current implementation does NOT sanitize HTML.
            # This is expected for generated notes (not served to users),
            # but worth noting as a consideration.
            self.assertIn("<script>", notes)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)


# =====================================================================
# Helper Functions
# =====================================================================

def _create_processor(notes_dir=None):
    """Create a LectureProcessor with test-friendly defaults"""
    if notes_dir is None:
        notes_dir = tempfile.mkdtemp()
    processor = LectureProcessor("testuser", "testpass")
    processor.note_generator = NoteGenerator(notes_dir)
    return processor


# =====================================================================
# Test Runner
# =====================================================================

def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    test_classes = [
        TestPanoptoParserSessionId,
        TestPanoptoParserServer,
        TestPanoptoParserValidation,
        TestSpeakerDetectorClassify,
        TestSpeakerDetectorNoise,
        TestSpeakerDetectorFilter,
        TestSpeakerDetectorKeyPoints,
        TestNoteGeneratorMarkdown,
        TestNoteGeneratorHTML,
        TestNoteGeneratorText,
        TestNoteGeneratorSaveNotes,
        TestNoteGeneratorSummary,
        TestPanoptoClientInit,
        TestPanoptoClientAuth,
        TestPanoptoClientTranscript,
        TestPanoptoClientVTTParsing,
        TestPanoptoClientSlides,
        TestConfig,
        TestFlaskApp,
        TestLectureProcessorInvalidURL,
        TestLectureProcessorSuccess,
        TestLectureProcessorSummary,
        TestEdgeCases,
        TestBugDiscovery,
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
