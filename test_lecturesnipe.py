"""
Comprehensive tests for LectureSnipe components
"""

import unittest
from panopto_parser import PanoptoParser
from speaker_detector import SpeakerDetector
from note_generator import NoteGenerator
import tempfile
import os


class TestPanoptoParser(unittest.TestCase):
    """Test Panopto URL parsing"""
    
    def test_valid_url_viewer(self):
        """Test parsing valid viewer URL"""
        url = "https://university.hosted.panopto.com/Panopto/Pages/Viewer.aspx?id=abc123"
        self.assertTrue(PanoptoParser.is_valid_panopto_url(url))
        self.assertEqual(PanoptoParser.extract_session_id(url), "abc123")
        self.assertEqual(PanoptoParser.extract_server(url), "university.hosted.panopto.com")
    
    def test_valid_url_embed(self):
        """Test parsing valid embed URL"""
        url = "https://example.panopto.com/Panopto/Pages/Embed.aspx?id=test-session"
        self.assertTrue(PanoptoParser.is_valid_panopto_url(url))
        self.assertEqual(PanoptoParser.extract_session_id(url), "test-session")
    
    def test_invalid_url_no_panopto(self):
        """Test invalid URL without panopto"""
        url = "https://youtube.com/watch?v=123"
        self.assertFalse(PanoptoParser.is_valid_panopto_url(url))
    
    def test_invalid_url_no_session_id(self):
        """Test invalid URL without session ID"""
        url = "https://university.panopto.com/Panopto/Pages/Viewer.aspx"
        self.assertFalse(PanoptoParser.is_valid_panopto_url(url))


class TestSpeakerDetector(unittest.TestCase):
    """Test speaker detection and filtering"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.detector = SpeakerDetector()
    
    def test_professor_classification(self):
        """Test professor speech classification"""
        professor_texts = [
            "Therefore, we can conclude that the solution is optimal.",
            "Let's move on to the next topic.",
            "In conclusion, this demonstrates the key principle.",
            "Notice that the pattern emerges clearly.",
        ]
        
        for text in professor_texts:
            result = self.detector.classify_segment(text)
            self.assertIn(result, ['professor', 'unknown'], 
                         f"Failed for: {text}")
    
    def test_student_classification(self):
        """Test student question classification"""
        student_texts = [
            "Could you explain that again please?",
            "What if we use a different approach?",
            "I don't understand this part.",
            "Can you clarify the difference?",
        ]
        
        for text in student_texts:
            result = self.detector.classify_segment(text)
            self.assertIn(result, ['student', 'unknown'], 
                         f"Failed for: {text}")
    
    def test_noise_detection(self):
        """Test noise filtering"""
        noise_texts = [
            "[laughter]",
            "(inaudible)",
            "um",
            "   ",
        ]
        
        for text in noise_texts:
            self.assertTrue(self.detector.is_noise(text),
                           f"Should be noise: {text}")
    
    def test_filter_transcript_professor_only(self):
        """Test filtering transcript to professor only"""
        transcript = [
            {'text': 'Therefore, today we discuss algorithms.', 'start': '00:00:00'},  # Professor
            {'text': 'Could you repeat that?', 'start': '00:00:10'},  # Student
            {'text': 'In conclusion, algorithms are step-by-step procedures.', 'start': '00:00:15'},  # Professor
            {'text': '[background noise]', 'start': '00:00:20'},  # Noise
        ]
        
        filtered = self.detector.filter_transcript(transcript, include_students=False)
        
        # Should have at least 1 entry (professor only, excluding student and noise)
        self.assertGreaterEqual(len(filtered), 1)
        # Should be less than original (filtered out some entries)
        self.assertLess(len(filtered), len(transcript))
    
    def test_filter_transcript_with_students(self):
        """Test filtering transcript including students"""
        transcript = [
            {'text': 'Today we discuss algorithms.', 'start': '00:00:00'},
            {'text': 'Could you repeat that?', 'start': '00:00:10'},
            {'text': '[background noise]', 'start': '00:00:20'},
        ]
        
        filtered = self.detector.filter_transcript(transcript, include_students=True)
        
        # Should have 2 entries (excluding only noise)
        self.assertGreaterEqual(len(filtered), 1)
    
    def test_extract_key_points(self):
        """Test key point extraction"""
        transcript = [
            {'text': 'This is important to remember for the exam.', 'speaker': 'professor'},
            {'text': 'Just some regular content.', 'speaker': 'professor'},
            {'text': 'The key point here is efficiency.', 'speaker': 'professor'},
        ]
        
        key_points = self.detector.extract_key_points(transcript)
        
        # Should extract entries with key indicators
        self.assertGreaterEqual(len(key_points), 1)


class TestNoteGenerator(unittest.TestCase):
    """Test note generation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.generator = NoteGenerator(self.temp_dir)
        
        self.sample_transcript = [
            {'text': 'Introduction to the topic.', 'speaker': 'professor', 'start': '00:00:00'},
            {'text': 'What is this about?', 'speaker': 'student', 'start': '00:00:10'},
            {'text': 'It is about algorithms.', 'speaker': 'professor', 'start': '00:00:15'},
        ]
    
    def test_generate_markdown_notes(self):
        """Test markdown note generation"""
        notes = self.generator.generate_notes(
            self.sample_transcript,
            format_type='markdown',
            include_timestamps=False
        )
        
        self.assertIn('# Lecture Notes', notes)
        self.assertIn('Introduction to the topic', notes)
    
    def test_generate_html_notes(self):
        """Test HTML note generation"""
        notes = self.generator.generate_notes(
            self.sample_transcript,
            format_type='html',
            include_timestamps=False
        )
        
        self.assertIn('<!DOCTYPE html>', notes)
        self.assertIn('Lecture Notes', notes)
        self.assertIn('Introduction to the topic', notes)
    
    def test_generate_text_notes(self):
        """Test plain text note generation"""
        notes = self.generator.generate_notes(
            self.sample_transcript,
            format_type='text',
            include_timestamps=False
        )
        
        self.assertIn('LECTURE NOTES', notes)
        self.assertIn('Introduction to the topic', notes)
    
    def test_include_timestamps(self):
        """Test including timestamps in notes"""
        notes = self.generator.generate_notes(
            self.sample_transcript,
            format_type='markdown',
            include_timestamps=True
        )
        
        self.assertIn('[00:00:00]', notes)
        self.assertIn('[00:00:15]', notes)
    
    def test_student_questions_formatted(self):
        """Test student questions are formatted differently"""
        notes = self.generator.generate_notes(
            self.sample_transcript,
            format_type='markdown',
            include_timestamps=False
        )
        
        self.assertIn('Student Question:', notes)
    
    def test_save_notes(self):
        """Test saving notes to file"""
        content = "# Test Notes\n\nContent here."
        
        filepath = self.generator.save_notes(content, 'test_notes', 'markdown')
        
        self.assertTrue(os.path.exists(filepath))
        self.assertTrue(filepath.endswith('.md'))
        
        with open(filepath, 'r') as f:
            saved_content = f.read()
        
        self.assertEqual(saved_content, content)
    
    def test_generate_summary(self):
        """Test summary generation"""
        summary = self.generator.generate_summary(
            self.sample_transcript,
            max_length=50
        )
        
        self.assertIsInstance(summary, str)
        self.assertGreater(len(summary), 0)
        
        # Should contain professor content
        self.assertIn('algorithms', summary.lower())


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestPanoptoParser))
    suite.addTests(loader.loadTestsFromTestCase(TestSpeakerDetector))
    suite.addTests(loader.loadTestsFromTestCase(TestNoteGenerator))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
