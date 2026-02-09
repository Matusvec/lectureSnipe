"""
Panopto URL parser and session ID extractor
"""

import re
from urllib.parse import urlparse, parse_qs


class PanoptoParser:
    """Parse Panopto URLs and extract session information"""
    
    @staticmethod
    def extract_session_id(url):
        """
        Extract session ID from Panopto URL
        
        Examples:
        - https://university.hosted.panopto.com/Panopto/Pages/Viewer.aspx?id=abc123
        - https://university.hosted.panopto.com/Panopto/Pages/Embed.aspx?id=abc123
        
        Args:
            url (str): Panopto URL
            
        Returns:
            str: Session ID or None if not found
        """
        try:
            parsed = urlparse(url)
            
            # Extract from query parameters
            query_params = parse_qs(parsed.query)
            if 'id' in query_params:
                return query_params['id'][0]
            
            # Extract from path (alternative format)
            # /Panopto/Pages/Viewer.aspx?id=SESSION_ID
            match = re.search(r'[?&]id=([a-zA-Z0-9\-]+)', url)
            if match:
                return match.group(1)
            
            return None
        except Exception as e:
            print(f"Error parsing Panopto URL: {e}")
            return None
    
    @staticmethod
    def extract_server(url):
        """
        Extract Panopto server domain from URL
        
        Args:
            url (str): Panopto URL
            
        Returns:
            str: Server domain (e.g., 'university.hosted.panopto.com')
        """
        try:
            if not url:
                return None
            parsed = urlparse(url)
            return parsed.netloc or None
        except Exception as e:
            print(f"Error extracting server: {e}")
            return None
    
    @staticmethod
    def is_valid_panopto_url(url):
        """
        Check if URL is a valid Panopto URL
        
        Args:
            url (str): URL to validate
            
        Returns:
            bool: True if valid Panopto URL
        """
        try:
            if not url:
                return False
            
            parsed = urlparse(url)
            
            # Check if domain contains 'panopto'
            if 'panopto' not in parsed.netloc.lower():
                return False
            
            # Check if it has a session ID
            session_id = PanoptoParser.extract_session_id(url)
            return session_id is not None
            
        except Exception:
            return False
