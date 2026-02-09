"""
Panopto API client for authentication and data extraction
"""

import requests
import json
from typing import Optional, Dict, List


class PanoptoClient:
    """Client for interacting with Panopto API and extracting lecture data"""
    
    def __init__(self, server: str, username: str = None, password: str = None):
        """
        Initialize Panopto client
        
        Args:
            server (str): Panopto server domain
            username (str, optional): Username for authentication
            password (str, optional): Password for authentication
        """
        self.server = server
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.authenticated = False
    
    def authenticate(self) -> bool:
        """
        Authenticate with Panopto server
        
        Returns:
            bool: True if authentication successful
        """
        if not self.username or not self.password:
            print("No credentials provided")
            return False
        
        try:
            # Panopto uses form-based authentication
            login_url = f"https://{self.server}/Panopto/Pages/Auth/Login.aspx"
            
            # First, get the login page to retrieve any tokens/cookies
            response = self.session.get(login_url)
            
            # Attempt login (this is simplified - actual implementation may need CSRF tokens)
            login_data = {
                'Email': self.username,
                'Password': self.password,
            }
            
            response = self.session.post(login_url, data=login_data)
            
            # Check if login was successful
            if response.status_code == 200 and 'auth' in response.cookies.get_dict():
                self.authenticated = True
                return True
            
            return False
            
        except Exception as e:
            print(f"Authentication error: {e}")
            return False
    
    def get_session_data(self, session_id: str) -> Optional[Dict]:
        """
        Get session data from Panopto
        
        Args:
            session_id (str): Panopto session ID
            
        Returns:
            dict: Session data or None if failed
        """
        try:
            # Panopto API endpoint for session data
            api_url = f"https://{self.server}/Panopto/Api/Sessions/{session_id}"
            
            response = self.session.get(api_url)
            
            if response.status_code == 200:
                return response.json()
            
            return None
            
        except Exception as e:
            print(f"Error fetching session data: {e}")
            return None
    
    def get_transcript(self, session_id: str) -> Optional[List[Dict]]:
        """
        Get transcript/captions for a Panopto session
        
        Args:
            session_id (str): Panopto session ID
            
        Returns:
            list: List of transcript entries with timestamps and text
        """
        try:
            # Panopto stores transcripts in multiple formats
            # Try to get the caption file
            transcript_url = f"https://{self.server}/Panopto/Pages/Viewer/Captions.ashx?id={session_id}"
            
            response = self.session.get(transcript_url)
            
            if response.status_code == 200:
                # Parse transcript data (usually JSON or VTT format)
                try:
                    transcript_data = response.json()
                    return transcript_data
                except:
                    # Might be VTT format
                    return self._parse_vtt(response.text)
            
            return None
            
        except Exception as e:
            print(f"Error fetching transcript: {e}")
            return None
    
    def _parse_vtt(self, vtt_text: str) -> List[Dict]:
        """
        Parse WebVTT format transcript
        
        Args:
            vtt_text (str): VTT format text
            
        Returns:
            list: List of transcript entries
        """
        entries = []
        lines = vtt_text.split('\n')
        
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            
            # Look for timestamp line (e.g., "00:00:10.000 --> 00:00:15.000")
            if '-->' in line:
                parts = line.split('-->')
                start_time = parts[0].strip()
                end_time = parts[1].strip() if len(parts) > 1 else ''
                
                # Next line should be the text
                i += 1
                text = ''
                while i < len(lines) and lines[i].strip() and '-->' not in lines[i]:
                    text += lines[i].strip() + ' '
                    i += 1
                
                entries.append({
                    'start': start_time,
                    'end': end_time,
                    'text': text.strip()
                })
            
            i += 1
        
        return entries
    
    def get_slide_images(self, session_id: str) -> List[str]:
        """
        Get URLs of slide images from Panopto session
        
        Args:
            session_id (str): Panopto session ID
            
        Returns:
            list: List of image URLs
        """
        try:
            # Panopto stores slide images in predictable URLs
            # This is a simplified version - actual implementation may need to parse manifest
            
            session_data = self.get_session_data(session_id)
            if not session_data:
                return []
            
            # Extract slide URLs from session data
            slides = []
            
            # Panopto typically stores slides in a sequence
            # URL pattern: https://server/Panopto/Pages/Viewer/Image.aspx?id=SESSION_ID&number=N
            # Try to determine number of slides
            for i in range(1, 200):  # Try up to 200 slides
                slide_url = f"https://{self.server}/Panopto/Pages/Viewer/Image.aspx?id={session_id}&number={i}"
                response = self.session.head(slide_url)
                
                if response.status_code == 200:
                    slides.append(slide_url)
                else:
                    # No more slides found
                    break
            
            return slides
            
        except Exception as e:
            print(f"Error fetching slides: {e}")
            return []
    
    def download_slide(self, slide_url: str, output_path: str) -> bool:
        """
        Download a slide image
        
        Args:
            slide_url (str): URL of slide image
            output_path (str): Path to save image
            
        Returns:
            bool: True if download successful
        """
        try:
            response = self.session.get(slide_url)
            
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    f.write(response.content)
                return True
            
            return False
            
        except Exception as e:
            print(f"Error downloading slide: {e}")
            return False
