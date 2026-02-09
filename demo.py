#!/usr/bin/env python3
"""
Demo script to showcase LectureSnipe functionality with mock data
"""

from speaker_detector import SpeakerDetector
from note_generator import NoteGenerator
from config import Config
import os

def create_demo():
    """Create a demo with sample transcript data"""
    
    print("=" * 70)
    print("LectureSnipe Demo - Mock Lecture Processing")
    print("=" * 70)
    print()
    
    # Initialize
    Config.init_app()
    detector = SpeakerDetector()
    generator = NoteGenerator(Config.NOTES_DIR)
    
    # Sample transcript (simulating what we'd get from Panopto)
    raw_transcript = [
        {'text': 'Good morning everyone. Today we will be covering data structures.', 'start': '00:00:05', 'end': '00:00:10'},
        {'text': 'Specifically, we will look at binary search trees and their properties.', 'start': '00:00:11', 'end': '00:00:16'},
        {'text': 'Could you explain what a node is again?', 'start': '00:00:17', 'end': '00:00:20'},
        {'text': 'Of course. A node is a fundamental unit that stores data and references to other nodes.', 'start': '00:00:21', 'end': '00:00:27'},
        {'text': '[background noise]', 'start': '00:00:28', 'end': '00:00:29'},
        {'text': 'The key property of a binary search tree is that for each node, all values in the left subtree are smaller.', 'start': '00:00:30', 'end': '00:00:37'},
        {'text': 'And all values in the right subtree are larger. This is important to remember.', 'start': '00:00:38', 'end': '00:00:43'},
        {'text': 'What if there are duplicate values?', 'start': '00:00:44', 'end': '00:00:46'},
        {'text': 'Good question. Typically, we handle duplicates by placing them in either the left or right subtree consistently.', 'start': '00:00:47', 'end': '00:00:54'},
        {'text': 'Let\'s move on to discussing the search operation in a BST.', 'start': '00:00:55', 'end': '00:00:59'},
        {'text': 'The search operation has a time complexity of O(log n) in a balanced tree.', 'start': '00:01:00', 'end': '00:01:06'},
        {'text': 'However, in the worst case with an unbalanced tree, it can degrade to O(n).', 'start': '00:01:07', 'end': '00:01:12'},
        {'text': 'This is critical to understand for exam questions.', 'start': '00:01:13', 'end': '00:01:17'},
        {'text': 'In conclusion, BSTs provide efficient search, insert, and delete operations when properly balanced.', 'start': '00:01:18', 'end': '00:01:25'},
    ]
    
    print("Step 1: Raw Transcript Entries")
    print(f"  - Total entries: {len(raw_transcript)}")
    print()
    
    # Step 2: Speaker Detection
    print("Step 2: Speaker Detection & Filtering")
    filtered_transcript = detector.filter_transcript(raw_transcript, include_students=False)
    print(f"  - Filtered entries (professor only): {len(filtered_transcript)}")
    print()
    
    # Show classification results
    print("Classification Results:")
    for entry in raw_transcript:
        speaker = detector.classify_segment(entry['text'])
        status_icon = "👨‍🏫" if speaker == 'professor' else "🙋" if speaker == 'student' else "🔇"
        print(f"  {status_icon} [{entry['start']}] {speaker.upper()}: {entry['text'][:60]}...")
    print()
    
    # Step 3: Generate notes (professor only)
    print("Step 3: Generating Notes (Professor Only)")
    markdown_notes = generator.generate_notes(
        filtered_transcript,
        format_type='markdown',
        include_timestamps=True,
        include_slides=False
    )
    
    notes_path = generator.save_notes(
        markdown_notes,
        'demo_lecture_professor_only',
        'markdown'
    )
    print(f"  - Notes saved to: {notes_path}")
    print()
    
    # Step 4: Generate notes with students
    print("Step 4: Generating Notes (Including Students)")
    filtered_with_students = detector.filter_transcript(raw_transcript, include_students=True)
    
    markdown_with_students = generator.generate_notes(
        filtered_with_students,
        format_type='markdown',
        include_timestamps=True,
        include_slides=False
    )
    
    notes_with_students_path = generator.save_notes(
        markdown_with_students,
        'demo_lecture_with_students',
        'markdown'
    )
    print(f"  - Notes saved to: {notes_with_students_path}")
    print()
    
    # Step 5: Generate summary
    print("Step 5: Generating Summary")
    summary = generator.generate_summary(filtered_transcript, max_length=50)
    print(f"  Brief Summary:")
    print(f"  {summary}")
    print()
    
    # Step 6: Extract key points
    print("Step 6: Extracting Key Points")
    key_points = detector.extract_key_points(filtered_transcript)
    print(f"  Key Points Found: {len(key_points)}")
    for i, point in enumerate(key_points, 1):
        print(f"  {i}. {point}")
    print()
    
    # Display sample output
    print("=" * 70)
    print("Sample Generated Notes (First 500 chars):")
    print("=" * 70)
    print(markdown_notes[:500])
    print("...")
    print()
    
    print("=" * 70)
    print("✓ Demo Complete!")
    print("=" * 70)
    print()
    print(f"Generated files can be found in: {Config.NOTES_DIR}")
    print()
    print("Files created:")
    print(f"  1. {notes_path}")
    print(f"  2. {notes_with_students_path}")
    print()

if __name__ == '__main__':
    create_demo()
