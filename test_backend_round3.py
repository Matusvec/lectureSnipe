"""
Third round of backend tests for LectureSnipe.
Focuses on security, consistency, and additional edge cases found in rounds 1 and 2.
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
# Security Tests
# =====================================================================

class TestDownloadSecurity(unittest.TestCase):
    """Security tests for the download endpoint"""

    def setUp(self):
        from app import app
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_path_traversal_basic(self):
        """Basic path traversal attempt should not return system files"""
        response = self.client.get("/download/../../../etc/passwd")
        self.assertIn(response.status_code, [403, 404])

    def test_path_traversal_encoded(self):
        """URL-encoded path traversal"""
        response = self.client.get("/download/..%2F..%2F..%2Fetc%2Fpasswd")
        self.assertIn(response.status_code, [403, 404])

    def test_path_traversal_double_dot(self):
        """Double dot path traversal"""
        response = self.client.get("/download/../config.py")
        self.assertIn(response.status_code, [403, 404])

    def test_download_normal_filename(self):
        """Normal filename should work (returns 404 if file doesn't exist)"""
        response = self.client.get("/download/lecture_notes.md")
        self.assertEqual(response.status_code, 404)

    def test_download_basename_only(self):
        """Even with path separators, should use basename only"""
        response = self.client.get("/download/subdir/file.md")
        # Should be treated as basename only, so 404 since file doesn't exist
        self.assertIn(response.status_code, [403, 404])


# =====================================================================
# URL Validation Consistency Tests
# =====================================================================

class TestURLValidationConsistency(unittest.TestCase):
    """Test that URL validation is consistent across endpoints"""

    def test_process_lecture_validates_url(self):
        """process_lecture should validate URL with is_valid_panopto_url"""
        processor = _create_processor()
        result = processor.process_lecture("https://example.com/page?id=abc")
        self.assertFalse(result["success"])
        self.assertIn("Invalid", result["error"])

    def test_generate_summary_validates_url(self):
        """FIXED: generate_custom_summary now validates URL with is_valid_panopto_url"""
        processor = _create_processor()
        result = processor.generate_custom_summary("https://example.com/page?id=abc")
        self.assertFalse(result["success"])
        self.assertIn("Invalid", result["error"])

    def test_generate_summary_valid_panopto_url_no_transcript(self):
        """Valid panopto URL but no transcript available"""
        processor = _create_processor()
        with patch.object(PanoptoClient, "authenticate", return_value=False), \
             patch.object(PanoptoClient, "get_transcript", return_value=None):
            result = processor.generate_custom_summary(
                "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=abc123"
            )
        self.assertFalse(result["success"])
        self.assertIn("transcript", result["error"].lower())

    def test_process_lecture_none_url(self):
        """None URL should be handled gracefully"""
        processor = _create_processor()
        result = processor.process_lecture(None)
        self.assertFalse(result["success"])

    def test_generate_summary_none_url(self):
        """None URL in summary should be handled gracefully"""
        processor = _create_processor()
        result = processor.generate_custom_summary(None)
        self.assertFalse(result["success"])

    def test_generate_summary_empty_url(self):
        """Empty URL in summary should be handled gracefully"""
        processor = _create_processor()
        result = processor.generate_custom_summary("")
        self.assertFalse(result["success"])


# =====================================================================
# Filter Transcript No-Mutation Verification
# =====================================================================

class TestFilterNoMutation(unittest.TestCase):
    """Verify the mutation bug fix works correctly"""

    def setUp(self):
        self.detector = SpeakerDetector()

    def test_filter_twice_different_settings(self):
        """Same transcript filtered twice with different settings should work independently"""
        transcript = [
            {"text": "Therefore, algorithms are fundamental.", "start": "00:00:00"},
            {"text": "Could you explain that?", "start": "00:00:10"},
            {"text": "In conclusion, efficiency matters.", "start": "00:00:15"},
        ]

        # Filter 1: professor only
        result1 = self.detector.filter_transcript(transcript, include_students=False)
        # Filter 2: with students
        result2 = self.detector.filter_transcript(transcript, include_students=True)

        # Original should not have speaker keys
        for entry in transcript:
            self.assertNotIn("speaker", entry)

        # Result 1 should only have professor entries
        for entry in result1:
            self.assertEqual(entry["speaker"], "professor")

        # Result 2 should have both professor and student entries
        speakers = {e["speaker"] for e in result2}
        self.assertIn("professor", speakers)

    def test_filter_result_is_independent_copy(self):
        """Modifying filtered results should not affect originals"""
        transcript = [
            {"text": "Therefore, content here.", "start": "00:00:00"},
        ]

        result = self.detector.filter_transcript(transcript, include_students=False)
        # Modify the result
        result[0]["speaker"] = "modified"
        result[0]["extra_key"] = "extra_value"

        # Original should be unchanged
        self.assertNotIn("speaker", transcript[0])
        self.assertNotIn("extra_key", transcript[0])


# =====================================================================
# Summary Edge Cases
# =====================================================================

class TestSummaryEdgeCases(unittest.TestCase):
    """Test summary generation edge cases"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_key_points_empty_after_filter(self):
        """When filtered transcript has no key point indicators"""
        processor = _create_processor(notes_dir=self.temp_dir)
        mock_transcript = [
            {"text": "Therefore, regular content.", "start": "00:00:00"},
            {"text": "More regular content.", "start": "00:00:05"},
        ]

        with patch.object(PanoptoClient, "authenticate", return_value=True), \
             patch.object(PanoptoClient, "get_transcript", return_value=mock_transcript):
            result = processor.generate_custom_summary(
                "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=abc123",
                summary_type="key_points"
            )

        self.assertTrue(result["success"])
        # Summary should be empty string for no key points
        self.assertEqual(result["summary"], "")

    def test_summary_unknown_type_falls_back(self):
        """Unknown summary type should fall back to default"""
        processor = _create_processor(notes_dir=self.temp_dir)
        mock_transcript = [
            {"text": "Therefore, lecture content.", "start": "00:00:00"},
        ]

        with patch.object(PanoptoClient, "authenticate", return_value=True), \
             patch.object(PanoptoClient, "get_transcript", return_value=mock_transcript):
            result = processor.generate_custom_summary(
                "https://uni.panopto.com/Panopto/Pages/Viewer.aspx?id=abc123",
                summary_type="nonexistent_type"
            )

        self.assertTrue(result["success"])
        self.assertIsNotNone(result["summary"])


# =====================================================================
# VTT Parser Additional Edge Cases
# =====================================================================

class TestVTTParserRound3(unittest.TestCase):
    """Additional VTT parsing edge cases"""

    def setUp(self):
        self.client = PanoptoClient("test.panopto.com")

    def test_vtt_with_only_header(self):
        result = self.client._parse_vtt("WEBVTT")
        self.assertEqual(len(result), 0)

    def test_vtt_with_styles(self):
        """VTT files can have style blocks - parser should handle them"""
        vtt = """WEBVTT

STYLE
::cue { color: white; }

00:00:00.000 --> 00:00:05.000
Text after style block.
"""
        result = self.client._parse_vtt(vtt)
        self.assertGreaterEqual(len(result), 1)

    def test_vtt_with_position_metadata(self):
        """VTT can have position metadata on timestamp line"""
        vtt = """00:00:00.000 --> 00:00:05.000 position:10% align:start
Text with position.
"""
        result = self.client._parse_vtt(vtt)
        self.assertEqual(len(result), 1)

    def test_vtt_single_entry(self):
        vtt = "00:00:00.000 --> 00:00:05.000\nSingle entry."
        result = self.client._parse_vtt(vtt)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["text"], "Single entry.")


# =====================================================================
# Flask API Response Format Tests
# =====================================================================

class TestFlaskAPIResponses(unittest.TestCase):
    """Test that API responses have consistent format"""

    def setUp(self):
        from app import app
        app.config["TESTING"] = True
        self.client = app.test_client()

    def test_process_error_has_error_key(self):
        response = self.client.post(
            "/api/process",
            content_type="application/json",
            data=json.dumps({"url": "not-a-panopto-url"})
        )
        data = json.loads(response.data)
        # Should have either 'error' or 'success' key
        self.assertTrue("error" in data or "success" in data)

    def test_process_400_has_error_key(self):
        response = self.client.post(
            "/api/process",
            content_type="application/json",
            data=json.dumps({})
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)

    def test_summary_400_has_error_key(self):
        response = self.client.post(
            "/api/summary",
            content_type="application/json",
            data=json.dumps({})
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn("error", data)

    def test_health_returns_json(self):
        response = self.client.get("/health")
        data = json.loads(response.data)
        self.assertIn("status", data)


# =====================================================================
# Note Generation Consistency
# =====================================================================

class TestNoteConsistency(unittest.TestCase):
    """Test that note generation is consistent across formats"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.generator = NoteGenerator(self.temp_dir)
        self.transcript = [
            {"text": "Content A.", "speaker": "professor", "start": "00:00:00"},
            {"text": "Content B.", "speaker": "professor", "start": "00:00:10"},
        ]

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_all_formats_include_content(self):
        """All formats should include the transcript content"""
        for fmt in ["markdown", "html", "text"]:
            notes = self.generator.generate_notes(self.transcript, format_type=fmt)
            self.assertIn("Content A.", notes, f"Missing 'Content A.' in {fmt}")
            self.assertIn("Content B.", notes, f"Missing 'Content B.' in {fmt}")

    def test_all_formats_include_date(self):
        """All formats should include a generation date"""
        for fmt in ["markdown", "html", "text"]:
            notes = self.generator.generate_notes(self.transcript, format_type=fmt)
            self.assertIn("Generated on", notes, f"Missing date in {fmt}")

    def test_all_formats_handle_empty_transcript(self):
        """All formats should handle empty transcripts without crashing"""
        for fmt in ["markdown", "html", "text"]:
            notes = self.generator.generate_notes([], format_type=fmt)
            self.assertIsInstance(notes, str)
            self.assertGreater(len(notes), 0)

    def test_timestamps_in_all_formats(self):
        """Timestamps should work in all formats"""
        for fmt in ["markdown", "html", "text"]:
            notes = self.generator.generate_notes(
                self.transcript, format_type=fmt, include_timestamps=True
            )
            self.assertIn("[00:00:00]", notes, f"Missing timestamp in {fmt}")


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
    """Run all round-3 tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    test_classes = [
        TestDownloadSecurity,
        TestURLValidationConsistency,
        TestFilterNoMutation,
        TestSummaryEdgeCases,
        TestVTTParserRound3,
        TestFlaskAPIResponses,
        TestNoteConsistency,
    ]

    for test_class in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(test_class))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    exit(0 if success else 1)
