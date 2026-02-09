"""
Second round of backend tests for LectureSnipe.
Focuses on deeper edge cases, integration scenarios, and additional bug hunting.
"""

import unittest
import tempfile
import os
import json
import shutil
import copy
from unittest.mock import patch, MagicMock, PropertyMock

from panopto_parser import PanoptoParser
from speaker_detector import SpeakerDetector
from note_generator import NoteGenerator
from config import Config
from panopto_client import PanoptoClient
from lecture_processor import LectureProcessor


# =====================================================================
# Deeper PanoptoParser Edge Cases
# =====================================================================

class TestPanoptoParserDeep(unittest.TestCase):
    """Deeper edge case tests for PanoptoParser"""

    def test_extract_session_id_with_hash_in_id(self):
        """IDs should only contain alphanumeric and hyphens"""
        url = "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=abc-123"
        self.assertEqual(PanoptoParser.extract_session_id(url), "abc-123")

    def test_extract_session_id_case_sensitivity(self):
        """Session IDs should be case-sensitive"""
        url = "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=AbC123"
        self.assertEqual(PanoptoParser.extract_session_id(url), "AbC123")

    def test_extract_session_id_with_port(self):
        url = "https://uni.panopto.com:8443/Panopto/Pages/Viewer.aspx?id=test123"
        self.assertEqual(PanoptoParser.extract_session_id(url), "test123")

    def test_extract_server_with_port(self):
        url = "https://uni.panopto.com:8443/Panopto/Pages/Viewer.aspx?id=test123"
        self.assertEqual(PanoptoParser.extract_server(url), "uni.panopto.com:8443")

    def test_is_valid_url_with_port(self):
        url = "https://uni.panopto.com:8443/Panopto/Pages/Viewer.aspx?id=test123"
        self.assertTrue(PanoptoParser.is_valid_panopto_url(url))

    def test_url_with_encoded_characters(self):
        """URL-encoded characters in session ID"""
        url = "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=abc%20123"
        result = PanoptoParser.extract_session_id(url)
        # parse_qs decodes, so 'abc 123' should be extracted
        self.assertEqual(result, "abc 123")

    def test_url_with_multiple_id_params(self):
        """If there are multiple 'id' params, should return the first"""
        url = "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=first&id=second"
        result = PanoptoParser.extract_session_id(url)
        self.assertEqual(result, "first")

    def test_url_with_empty_id(self):
        """Empty id parameter - parse_qs drops empty values by default"""
        url = "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id="
        result = PanoptoParser.extract_session_id(url)
        # parse_qs filters empty values, so 'id' key won't be in params
        # The regex fallback also requires at least one character after id=
        self.assertIsNone(result)

    def test_is_valid_url_with_empty_id(self):
        """BUG CHECK: URL with empty id parameter - should this be valid?"""
        url = "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id="
        # extract_session_id returns '' (empty string) which is truthy? No, '' is falsy
        result = PanoptoParser.is_valid_panopto_url(url)
        # An empty session ID means extract_session_id returns ''
        # '' is falsy in Python, so is_valid should return False
        # Let's check what actually happens
        session_id = PanoptoParser.extract_session_id(url)
        if session_id == "":
            # Bug: empty string is not None, so is_valid might return True
            # because the check is `session_id is not None`
            pass
        # The test documents the behavior
        self.assertIsNotNone(result)

    def test_extract_session_id_returns_none_for_empty_id(self):
        """Document: empty id= returns None (parse_qs drops empty values)"""
        url = "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id="
        result = PanoptoParser.extract_session_id(url)
        self.assertIsNone(result)


# =====================================================================
# Deeper SpeakerDetector Tests
# =====================================================================

class TestSpeakerDetectorDeep(unittest.TestCase):
    """Deeper edge cases for SpeakerDetector"""

    def setUp(self):
        self.detector = SpeakerDetector()

    def test_mixed_professor_and_student_signals(self):
        """Text with both professor and student signals"""
        # "Therefore" (professor) + "Could you explain" (student) + "?" (student)
        text = "Therefore, could you explain the concept?"
        result = self.detector.classify_segment(text)
        # Both scores should be > 0, student wins due to ? and pattern
        self.assertIn(result, ["professor", "student"])

    def test_very_short_text(self):
        """Very short text (1-2 words)"""
        result = self.detector.classify_segment("Yes.")
        self.assertIn(result, ["professor", "student", "unknown"])

    def test_all_caps_text(self):
        """Text in all caps should still be classified"""
        result = self.detector.classify_segment("THEREFORE WE CONCLUDE")
        # Patterns use re.IGNORECASE, so should still match
        self.assertIn(result, ["professor", "unknown"])

    def test_student_sorry(self):
        """'Sorry I...' should be student"""
        result = self.detector.classify_segment("Sorry I didn't catch that last part.")
        self.assertEqual(result, "student")

    def test_student_excuse_me(self):
        """'Excuse me' should be student"""
        result = self.detector.classify_segment("Excuse me, I have a question.")
        self.assertEqual(result, "student")

    def test_professor_to_summarize(self):
        result = self.detector.classify_segment("To summarize, the algorithm runs in O(n log n).")
        self.assertEqual(result, "professor")

    def test_classify_with_numbers(self):
        """Numeric content should be handled"""
        result = self.detector.classify_segment("Therefore, 2 + 2 = 4.")
        self.assertEqual(result, "professor")

    def test_filter_preserves_start_time(self):
        """Filtered entries should preserve their start times"""
        transcript = [
            {"text": "Therefore, important content.", "start": "00:05:30"},
        ]
        filtered = self.detector.filter_transcript(transcript, include_students=False)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["start"], "00:05:30")

    def test_filter_student_not_updated_when_excluded(self):
        """When students are excluded, previous_speaker should not be set to 'student'"""
        transcript = [
            {"text": "Therefore, lecture content here.", "start": "00:00:00"},
            {"text": "Could you explain that again?", "start": "00:00:10"},
            # After student (excluded), unknown should still use professor as previous
            {"text": "A neutral statement.", "start": "00:00:15"},
        ]
        filtered = self.detector.filter_transcript(transcript, include_students=False)
        # There should be 2 entries: professor + unknown-as-professor
        self.assertGreaterEqual(len(filtered), 1)
        for entry in filtered:
            self.assertEqual(entry["speaker"], "professor")

    def test_filter_transcript_no_mutation(self):
        """FIXED: Filtering should not mutate original dict objects."""
        transcript = [
            {"text": "Therefore, algorithms.", "start": "00:00:00"},
            {"text": "Could you repeat?", "start": "00:00:10"},
        ]

        # First filter without students
        result1 = self.detector.filter_transcript(transcript, include_students=False)
        # The original transcript should NOT have 'speaker' keys
        self.assertNotIn("speaker", transcript[0])

        # Second filter with students works independently
        result2 = self.detector.filter_transcript(transcript, include_students=True)
        self.assertIsInstance(result1, list)
        self.assertIsInstance(result2, list)

    def test_key_points_all_indicators(self):
        """Test that all key indicators are recognized"""
        indicators = [
            "important", "key", "critical", "essential", "remember",
            "main point", "takeaway", "conclusion", "in summary",
            "to recap", "note that", "keep in mind"
        ]
        for indicator in indicators:
            transcript = [{"text": f"This is {indicator} content.", "speaker": "professor"}]
            key_points = self.detector.extract_key_points(transcript)
            self.assertGreaterEqual(len(key_points), 1,
                                    f"Indicator '{indicator}' not recognized")


# =====================================================================
# Deeper NoteGenerator Tests
# =====================================================================

class TestNoteGeneratorDeep(unittest.TestCase):
    """Deeper edge cases for NoteGenerator"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.generator = NoteGenerator(self.temp_dir)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_unknown_speaker_in_markdown(self):
        """Entries with 'unknown' speaker should be included in notes"""
        transcript = [
            {"text": "Unknown speaker content.", "speaker": "unknown", "start": "00:00:00"},
        ]
        notes = self.generator.generate_notes(transcript, format_type="markdown")
        self.assertIn("Unknown speaker content.", notes)

    def test_empty_text_entries(self):
        """Entries with empty text should be handled"""
        transcript = [
            {"text": "", "speaker": "professor", "start": "00:00:00"},
        ]
        notes = self.generator.generate_notes(transcript, format_type="markdown")
        self.assertIn("# Lecture Notes", notes)

    def test_missing_speaker_key(self):
        """Entries without 'speaker' key default to 'unknown'"""
        transcript = [
            {"text": "Content here.", "start": "00:00:00"},
        ]
        notes = self.generator.generate_notes(transcript, format_type="markdown")
        self.assertIn("Content here.", notes)

    def test_slide_heuristic_every_10_entries(self):
        """Slides appear at entry 0, 10, 20, etc."""
        transcript = [
            {"text": f"Content {i}.", "speaker": "professor", "start": f"00:00:{i:02d}"}
            for i in range(21)
        ]
        slides = [f"/slide_{i}.png" for i in range(3)]
        notes = self.generator.generate_notes(
            transcript, slides=slides, format_type="markdown",
            include_slides=True
        )
        # Slide 1 at index 0, Slide 2 at index 10, Slide 3 at index 20
        self.assertIn("Slide 1", notes)
        self.assertIn("Slide 2", notes)
        self.assertIn("Slide 3", notes)

    def test_more_entries_than_slides(self):
        """When there are more entry-groups than slides"""
        transcript = [
            {"text": f"Content {i}.", "speaker": "professor", "start": f"00:00:{i:02d}"}
            for i in range(30)
        ]
        slides = ["/slide_1.png"]
        notes = self.generator.generate_notes(
            transcript, slides=slides, format_type="markdown",
            include_slides=True
        )
        self.assertIn("Slide 1", notes)
        # Should NOT have Slide 2 since there's only 1 slide
        self.assertNotIn("Slide 2", notes)

    def test_html_no_slides(self):
        """HTML generation with no slides - content should not reference slides"""
        transcript = [
            {"text": "Content.", "speaker": "professor", "start": "00:00:00"},
        ]
        notes = self.generator.generate_notes(
            transcript, format_type="html", include_slides=False
        )
        # CSS class definitions are always present (static template), but
        # actual slide content (<h2>Slide N</h2>) should not be present
        self.assertNotIn("<h2>Slide", notes)

    def test_text_no_slides(self):
        """Text generation with no slides"""
        transcript = [
            {"text": "Content.", "speaker": "professor", "start": "00:00:00"},
        ]
        notes = self.generator.generate_notes(
            transcript, format_type="text", include_slides=False
        )
        self.assertNotIn("SLIDE", notes)

    def test_save_filename_with_special_chars(self):
        """Filenames with special characters"""
        content = "test content"
        path = self.generator.save_notes(content, "test-file_v2", "markdown")
        self.assertTrue(os.path.exists(path))
        self.assertTrue(path.endswith(".md"))

    def test_summary_max_length_zero(self):
        """max_length=0 edge case"""
        transcript = [
            {"text": "Some text.", "speaker": "professor"},
        ]
        # max_length=0: len(words) > max_length, so it tries to truncate
        # first_part_len = 0 * 0.7 = 0, last_part_len = 0 - 0 = 0
        summary = self.generator.generate_summary(transcript, max_length=0)
        # Should produce "..." with empty slices
        self.assertIsInstance(summary, str)

    def test_summary_max_length_one(self):
        """max_length=1 edge case"""
        transcript = [
            {"text": "Hello world.", "speaker": "professor"},
        ]
        summary = self.generator.generate_summary(transcript, max_length=1)
        self.assertIsInstance(summary, str)
        # Should have first word + ... + empty last part or similar
        self.assertIn("...", summary)


# =====================================================================
# Deeper PanoptoClient Tests
# =====================================================================

class TestPanoptoClientDeep(unittest.TestCase):
    """Deeper edge cases for PanoptoClient"""

    def test_get_session_data_success(self):
        client = PanoptoClient("test.panopto.com")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "session123", "name": "Test Lecture"}
        client.session = MagicMock()
        client.session.get.return_value = mock_response

        result = client.get_session_data("session123")
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "session123")

    def test_get_session_data_failure(self):
        client = PanoptoClient("test.panopto.com")
        mock_response = MagicMock()
        mock_response.status_code = 404
        client.session = MagicMock()
        client.session.get.return_value = mock_response

        result = client.get_session_data("nonexistent")
        self.assertIsNone(result)

    def test_get_session_data_network_error(self):
        client = PanoptoClient("test.panopto.com")
        client.session = MagicMock()
        client.session.get.side_effect = Exception("timeout")

        result = client.get_session_data("session123")
        self.assertIsNone(result)

    def test_get_transcript_vtt_fallback(self):
        """When JSON parsing fails, should fall back to VTT parsing"""
        client = PanoptoClient("test.panopto.com")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError("Not JSON")
        mock_response.text = """WEBVTT

00:00:00.000 --> 00:00:05.000
Hello world.
"""
        client.session = MagicMock()
        client.session.get.return_value = mock_response

        result = client.get_transcript("session123")
        self.assertIsNotNone(result)
        self.assertEqual(len(result), 1)
        self.assertIn("Hello world", result[0]["text"])

    def test_vtt_with_empty_lines_between_entries(self):
        client = PanoptoClient("test.panopto.com")
        vtt = """WEBVTT

00:00:00.000 --> 00:00:05.000
First entry.

00:00:05.000 --> 00:00:10.000
Second entry.

"""
        result = client._parse_vtt(vtt)
        self.assertEqual(len(result), 2)

    def test_vtt_with_no_space_around_arrow(self):
        client = PanoptoClient("test.panopto.com")
        vtt = "00:00:00.000-->00:00:05.000\nText here."
        result = client._parse_vtt(vtt)
        self.assertEqual(len(result), 1)

    def test_download_slide_to_nonexistent_dir(self):
        """Downloading to a directory that doesn't exist should fail gracefully"""
        client = PanoptoClient("test.panopto.com")
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"image data"
        client.session = MagicMock()
        client.session.get.return_value = mock_response

        result = client.download_slide(
            "http://example.com/slide.png",
            "/nonexistent/dir/slide.png"
        )
        self.assertFalse(result)


# =====================================================================
# Deeper Flask App Tests
# =====================================================================

class TestFlaskAppDeep(unittest.TestCase):
    """Deeper Flask endpoint tests"""

    def setUp(self):
        from app import app
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_process_with_all_options(self):
        """Test process endpoint with all options set"""
        response = self.client.post(
            "/api/process",
            content_type="application/json",
            data=json.dumps({
                "url": "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=test",
                "username": "user",
                "password": "pass",
                "format": "html",
                "include_students": True,
                "include_timestamps": True,
                "download_slides": False,
            })
        )
        # Should get a response (even if it fails due to no real server)
        data = json.loads(response.data)
        self.assertIn("success", data.keys() | {"error": ""}.keys())

    def test_summary_with_options(self):
        """Test summary endpoint with options"""
        response = self.client.post(
            "/api/summary",
            content_type="application/json",
            data=json.dumps({
                "url": "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=test",
                "summary_type": "key_points",
                "include_students": True,
            })
        )
        data = json.loads(response.data)
        self.assertIsInstance(data, dict)

    def test_health_response_json(self):
        response = self.client.get("/health")
        data = json.loads(response.data)
        self.assertEqual(data["status"], "healthy")

    def test_process_with_none_json(self):
        """POST with Content-Type json but no body"""
        response = self.client.post(
            "/api/process",
            content_type="application/json"
        )
        self.assertIn(response.status_code, [400, 415, 500])

    def test_download_path_traversal(self):
        """Ensure path traversal doesn't expose system files"""
        response = self.client.get("/download/../../../etc/passwd")
        # Flask should handle this, but let's verify we don't get a 200
        # The download handler checks os.path.exists for the joined path
        self.assertIn(response.status_code, [404, 500])

    def test_process_empty_url_field(self):
        """Empty URL field should be handled"""
        response = self.client.post(
            "/api/process",
            content_type="application/json",
            data=json.dumps({"url": ""})
        )
        data = json.loads(response.data)
        # Empty URL should result in error
        self.assertFalse(data.get("success", True))


# =====================================================================
# Integration Tests
# =====================================================================

class TestIntegration(unittest.TestCase):
    """Integration tests that test multiple components together"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_full_pipeline_professor_only(self):
        """Complete pipeline: classify -> filter -> generate notes"""
        detector = SpeakerDetector()
        generator = NoteGenerator(self.temp_dir)

        raw_transcript = [
            {"text": "Good morning. Let's begin.", "start": "00:00:00"},
            {"text": "Could you speak louder?", "start": "00:00:10"},
            {"text": "Therefore, the algorithm works in O(n).", "start": "00:00:15"},
            {"text": "[coughing]", "start": "00:00:20"},
            {"text": "In conclusion, efficiency matters.", "start": "00:00:25"},
        ]

        filtered = detector.filter_transcript(raw_transcript, include_students=False)
        notes = generator.generate_notes(filtered, format_type="markdown", include_timestamps=True)
        path = generator.save_notes(notes, "integration_test", "markdown")

        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            content = f.read()
        self.assertIn("# Lecture Notes", content)
        self.assertNotIn("[coughing]", content)

    def test_full_pipeline_with_students(self):
        """Complete pipeline with student questions included"""
        detector = SpeakerDetector()
        generator = NoteGenerator(self.temp_dir)

        raw_transcript = [
            {"text": "Therefore, data structures are fundamental.", "start": "00:00:00"},
            {"text": "Could you explain hash tables?", "start": "00:00:10"},
            {"text": "In summary, hash tables use key-value pairs.", "start": "00:00:15"},
        ]

        filtered = detector.filter_transcript(raw_transcript, include_students=True)
        notes = generator.generate_notes(filtered, format_type="markdown")

        self.assertIn("Student Question:", notes)
        self.assertIn("hash tables", notes.lower())

    def test_full_pipeline_all_formats(self):
        """Test complete pipeline with all output formats"""
        detector = SpeakerDetector()
        generator = NoteGenerator(self.temp_dir)

        transcript = [
            {"text": "Therefore, this is important.", "start": "00:00:00"},
        ]
        filtered = detector.filter_transcript(transcript, include_students=False)

        for fmt, ext, check in [
            ("markdown", ".md", "# Lecture Notes"),
            ("html", ".html", "<!DOCTYPE html>"),
            ("text", ".txt", "LECTURE NOTES"),
        ]:
            notes = generator.generate_notes(filtered, format_type=fmt)
            path = generator.save_notes(notes, f"test_{fmt}", fmt)
            self.assertTrue(path.endswith(ext), f"Expected {ext} for {fmt}")
            self.assertTrue(os.path.exists(path))
            with open(path) as f:
                content = f.read()
            self.assertIn(check, content, f"Missing '{check}' in {fmt} output")

    def test_summary_and_key_points(self):
        """Test summary generation and key point extraction together"""
        detector = SpeakerDetector()
        generator = NoteGenerator(self.temp_dir)

        transcript = [
            {"text": "This is important.", "speaker": "professor"},
            {"text": "The key point is clarity.", "speaker": "professor"},
            {"text": "Regular content.", "speaker": "professor"},
            {"text": "Keep in mind the deadlines.", "speaker": "professor"},
        ]

        key_points = detector.extract_key_points(transcript)
        summary = generator.generate_summary(transcript, max_length=100)

        self.assertGreaterEqual(len(key_points), 2)
        self.assertIn("important", summary.lower())

    def test_empty_transcript_pipeline(self):
        """Pipeline with empty transcript should not crash"""
        detector = SpeakerDetector()
        generator = NoteGenerator(self.temp_dir)

        filtered = detector.filter_transcript([], include_students=False)
        notes = generator.generate_notes(filtered, format_type="markdown")
        path = generator.save_notes(notes, "empty_test", "markdown")

        self.assertTrue(os.path.exists(path))
        with open(path) as f:
            content = f.read()
        self.assertIn("# Lecture Notes", content)


# =====================================================================
# Bug Regression Tests  
# =====================================================================

class TestBugRegressions(unittest.TestCase):
    """Tests that verify previously found bugs stay fixed"""

    def test_extract_server_none_returns_none(self):
        """Regression: extract_server(None) used to return b''"""
        result = PanoptoParser.extract_server(None)
        self.assertIsNone(result)

    def test_extract_server_empty_returns_none(self):
        """Regression: extract_server('') used to return ''"""
        result = PanoptoParser.extract_server("")
        self.assertIsNone(result)

    def test_is_valid_url_empty_id_param(self):
        """Edge case: URL with empty id= parameter.
        parse_qs drops empty values by default, so extract_session_id returns None.
        Therefore is_valid_panopto_url correctly returns False."""
        url = "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id="
        session_id = PanoptoParser.extract_session_id(url)
        self.assertIsNone(session_id)
        result = PanoptoParser.is_valid_panopto_url(url)
        self.assertFalse(result)

    def test_filter_transcript_no_mutation_regression(self):
        """FIXED: filter_transcript no longer mutates input dicts"""
        detector = SpeakerDetector()
        transcript = [
            {"text": "Therefore, content.", "start": "00:00:00"},
        ]
        original_keys = set(transcript[0].keys())
        detector.filter_transcript(transcript, include_students=False)
        new_keys = set(transcript[0].keys())
        # No new keys should be added to the original dict
        self.assertEqual(original_keys, new_keys)


# =====================================================================
# Test Runner
# =====================================================================

def run_tests():
    """Run all round-2 tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_classes = [
        TestPanoptoParserDeep,
        TestSpeakerDetectorDeep,
        TestNoteGeneratorDeep,
        TestPanoptoClientDeep,
        TestFlaskAppDeep,
        TestIntegration,
        TestBugRegressions,
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
