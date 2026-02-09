"""
Main lecture processor - orchestrates the entire workflow
"""

import os
from typing import Dict, List, Optional
from panopto_parser import PanoptoParser
from panopto_client import PanoptoClient
from speaker_detector import SpeakerDetector
from note_generator import NoteGenerator
from config import Config


class LectureProcessor:
    """Main processor for converting Panopto lectures to notes"""
    
    def __init__(self, username: str = None, password: str = None):
        """
        Initialize lecture processor
        
        Args:
            username (str, optional): Panopto username
            password (str, optional): Panopto password
        """
        self.username = username or Config.PANOPTO_USERNAME
        self.password = password or Config.PANOPTO_PASSWORD
        
        self.speaker_detector = SpeakerDetector()
        self.note_generator = NoteGenerator(Config.NOTES_DIR)
        
        Config.init_app()
    
    def process_lecture(self, 
                       panopto_url: str,
                       include_students: bool = False,
                       format_type: str = 'markdown',
                       include_timestamps: bool = False,
                       download_slides: bool = True) -> Dict:
        """
        Process a Panopto lecture and generate notes
        
        Args:
            panopto_url (str): Panopto lecture URL
            include_students (bool): Include student questions in notes
            format_type (str): Output format ('markdown', 'html', 'text')
            include_timestamps (bool): Include timestamps in notes
            download_slides (bool): Download and include slides
            
        Returns:
            dict: Results with status, notes_path, and other info
        """
        result = {
            'success': False,
            'error': None,
            'notes_path': None,
            'slides_downloaded': 0,
            'transcript_entries': 0
        }
        
        try:
            # Step 1: Parse URL
            if not PanoptoParser.is_valid_panopto_url(panopto_url):
                result['error'] = "Invalid Panopto URL"
                return result
            
            session_id = PanoptoParser.extract_session_id(panopto_url)
            server = PanoptoParser.extract_server(panopto_url)
            
            if not session_id or not server:
                result['error'] = "Could not extract session information from URL"
                return result
            
            print(f"Processing session: {session_id} from {server}")
            
            # Step 2: Initialize Panopto client
            client = PanoptoClient(server, self.username, self.password)
            
            # Authenticate if credentials provided
            if self.username and self.password:
                print("Authenticating...")
                if not client.authenticate():
                    print("Warning: Authentication failed, proceeding without auth")
            
            # Step 3: Get transcript
            print("Fetching transcript...")
            transcript = client.get_transcript(session_id)
            
            if not transcript:
                result['error'] = "Could not retrieve transcript. Lecture may be locked or unavailable."
                return result
            
            result['transcript_entries'] = len(transcript)
            print(f"Retrieved {len(transcript)} transcript entries")
            
            # Step 4: Filter transcript (detect professor vs student)
            print("Filtering transcript...")
            filtered_transcript = self.speaker_detector.filter_transcript(
                transcript, 
                include_students=include_students
            )
            
            print(f"Filtered to {len(filtered_transcript)} entries")
            
            # Step 5: Get slides if requested
            slide_paths = []
            if download_slides:
                print("Downloading slides...")
                slide_urls = client.get_slide_images(session_id)
                
                for i, slide_url in enumerate(slide_urls):
                    slide_path = os.path.join(
                        Config.SLIDES_DIR, 
                        f"{session_id}_slide_{i+1}.png"
                    )
                    
                    if client.download_slide(slide_url, slide_path):
                        slide_paths.append(slide_path)
                        result['slides_downloaded'] += 1
                
                print(f"Downloaded {len(slide_paths)} slides")
            
            # Step 6: Generate notes
            print(f"Generating notes in {format_type} format...")
            notes_content = self.note_generator.generate_notes(
                filtered_transcript,
                slides=slide_paths if download_slides else None,
                format_type=format_type,
                include_timestamps=include_timestamps,
                include_slides=download_slides
            )
            
            # Step 7: Save notes
            notes_path = self.note_generator.save_notes(
                notes_content,
                f"lecture_{session_id}",
                format_type
            )
            
            result['success'] = True
            result['notes_path'] = notes_path
            result['session_id'] = session_id
            
            print(f"Notes saved to: {notes_path}")
            
            return result
            
        except Exception as e:
            result['error'] = f"Error processing lecture: {str(e)}"
            print(result['error'])
            return result
    
    def generate_custom_summary(self, 
                               panopto_url: str,
                               summary_type: str = 'brief',
                               include_students: bool = False) -> Dict:
        """
        Generate a custom summary of the lecture
        
        Args:
            panopto_url (str): Panopto lecture URL
            summary_type (str): Summary type ('brief', 'detailed', 'key_points')
            include_students (bool): Include student questions
            
        Returns:
            dict: Results with summary
        """
        result = {
            'success': False,
            'error': None,
            'summary': None
        }
        
        try:
            # Validate URL
            if not PanoptoParser.is_valid_panopto_url(panopto_url):
                result['error'] = "Invalid Panopto URL"
                return result

            # Get session info
            session_id = PanoptoParser.extract_session_id(panopto_url)
            server = PanoptoParser.extract_server(panopto_url)
            
            if not session_id or not server:
                result['error'] = "Could not extract session information from URL"
                return result
            
            # Get and filter transcript
            client = PanoptoClient(server, self.username, self.password)
            
            if self.username and self.password:
                client.authenticate()
            
            transcript = client.get_transcript(session_id)
            
            if not transcript:
                result['error'] = "Could not retrieve transcript"
                return result
            
            filtered_transcript = self.speaker_detector.filter_transcript(
                transcript,
                include_students=include_students
            )
            
            # Generate summary based on type
            if summary_type == 'brief':
                summary = self.note_generator.generate_summary(filtered_transcript, max_length=200)
            elif summary_type == 'detailed':
                summary = self.note_generator.generate_summary(filtered_transcript, max_length=1000)
            elif summary_type == 'key_points':
                key_points = self.speaker_detector.extract_key_points(filtered_transcript)
                summary = '\n\n'.join([f"• {point}" for point in key_points])
            else:
                summary = self.note_generator.generate_summary(filtered_transcript)
            
            result['success'] = True
            result['summary'] = summary
            
            return result
            
        except Exception as e:
            result['error'] = f"Error generating summary: {str(e)}"
            return result
