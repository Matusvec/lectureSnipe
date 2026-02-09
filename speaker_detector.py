"""
Speaker detection and transcript filtering
Identifies professor vs student questions and filters noise
"""

import re
from typing import List, Dict


class SpeakerDetector:
    """Detect and classify speakers in transcripts"""
    
    # Common patterns for student questions
    STUDENT_PATTERNS = [
        r'\b(question|ask|wondering|confused|don\'t understand)\b',
        r'\b(could you|can you|would you)\s+(explain|clarify|repeat)\b',
        r'\b(what if|what about|how about)\b',
        r'\bsorry\s+(i|we)\b',
        r'\b(excuse me)\b',
    ]
    
    # Common patterns for professor speaking
    PROFESSOR_PATTERNS = [
        r'\b(so|therefore|thus|hence)\b',
        r'\b(let\'s|we\'re going to|we will)\b',
        r'\b(notice that|observe that|see that)\b',
        r'\b(the key point|important|remember)\b',
        r'\b(in conclusion|to summarize|in summary)\b',
    ]
    
    # Noise patterns to filter out
    NOISE_PATTERNS = [
        r'^\s*\[.*\]\s*$',  # [sound effects], [laughter], etc.
        r'^\s*\(.*\)\s*$',  # (inaudible), (crosstalk), etc.
        r'^\s*um+\s*$',
        r'^\s*uh+\s*$',
        r'^\s*like\s*$',
    ]
    
    def __init__(self, professor_keywords: List[str] = None):
        """
        Initialize speaker detector
        
        Args:
            professor_keywords (list, optional): Additional keywords associated with professor
        """
        self.professor_keywords = professor_keywords or []
    
    def classify_segment(self, text: str, previous_speaker: str = None) -> str:
        """
        Classify a transcript segment as professor or student
        
        Args:
            text (str): Transcript text
            previous_speaker (str, optional): Previous speaker for context
            
        Returns:
            str: 'professor', 'student', or 'unknown'
        """
        if not text or self.is_noise(text):
            return 'noise'
        
        text_lower = text.lower()
        
        # Count pattern matches
        student_score = 0
        professor_score = 0
        
        # Check student patterns
        for pattern in self.STUDENT_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                student_score += 1
        
        # Check professor patterns
        for pattern in self.PROFESSOR_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                professor_score += 1
        
        # Check custom professor keywords
        for keyword in self.professor_keywords:
            if keyword.lower() in text_lower:
                professor_score += 2
        
        # Question marks often indicate student questions
        if '?' in text:
            student_score += 1
        
        # Longer segments tend to be professor
        if len(text.split()) > 30:
            professor_score += 1
        
        # Decide based on scores
        if professor_score > student_score:
            return 'professor'
        elif student_score > professor_score:
            return 'student'
        else:
            # Use previous speaker as tie-breaker
            return previous_speaker if previous_speaker else 'unknown'
    
    def is_noise(self, text: str) -> bool:
        """
        Check if text is noise that should be filtered
        
        Args:
            text (str): Text to check
            
        Returns:
            bool: True if text is noise
        """
        if not text or not text.strip():
            return True
        
        for pattern in self.NOISE_PATTERNS:
            if re.match(pattern, text.strip(), re.IGNORECASE):
                return True
        
        return False
    
    def filter_transcript(self, transcript: List[Dict], 
                         include_students: bool = False) -> List[Dict]:
        """
        Filter transcript to include only relevant content
        
        Args:
            transcript (list): List of transcript entries
            include_students (bool): Whether to include student questions
            
        Returns:
            list: Filtered transcript entries (copies with 'speaker' key added)
        """
        filtered = []
        previous_speaker = None
        
        for entry in transcript:
            text = entry.get('text', '')
            
            speaker = self.classify_segment(text, previous_speaker)
            
            # Filter based on settings
            if speaker == 'noise':
                continue
            
            if speaker == 'professor':
                filtered_entry = dict(entry)
                filtered_entry['speaker'] = 'professor'
                filtered.append(filtered_entry)
                previous_speaker = 'professor'
            elif speaker == 'student' and include_students:
                filtered_entry = dict(entry)
                filtered_entry['speaker'] = 'student'
                filtered.append(filtered_entry)
                previous_speaker = 'student'
            elif speaker == 'unknown':
                # Include unknown segments if previous was professor
                if previous_speaker == 'professor':
                    filtered_entry = dict(entry)
                    filtered_entry['speaker'] = 'professor'  # Likely continuation
                    filtered.append(filtered_entry)
        
        return filtered
    
    def extract_key_points(self, transcript: List[Dict]) -> List[str]:
        """
        Extract key points from transcript
        
        Args:
            transcript (list): Transcript entries
            
        Returns:
            list: List of key point text segments
        """
        key_points = []
        
        # Keywords that indicate important content
        key_indicators = [
            'important', 'key', 'critical', 'essential', 'remember',
            'main point', 'takeaway', 'conclusion', 'in summary',
            'to recap', 'note that', 'keep in mind'
        ]
        
        for entry in transcript:
            text = entry.get('text', '').lower()
            
            # Check if any key indicator is present
            for indicator in key_indicators:
                if indicator in text:
                    key_points.append(entry.get('text', ''))
                    break
        
        return key_points
