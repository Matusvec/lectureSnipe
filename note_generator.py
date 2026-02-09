"""
Note generator - combines slides and transcripts into readable notes
"""

import os
from typing import List, Dict, Optional
from datetime import datetime


class NoteGenerator:
    """Generate readable notes from lecture slides and transcripts"""
    
    def __init__(self, output_dir: str):
        """
        Initialize note generator
        
        Args:
            output_dir (str): Directory to save generated notes
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def generate_notes(self, 
                      transcript: List[Dict],
                      slides: List[str] = None,
                      format_type: str = 'markdown',
                      include_timestamps: bool = False,
                      include_slides: bool = True) -> str:
        """
        Generate notes from transcript and slides
        
        Args:
            transcript (list): Filtered transcript entries
            slides (list, optional): List of slide image paths
            format_type (str): Output format ('markdown', 'html', 'text')
            include_timestamps (bool): Include timestamps in notes
            include_slides (bool): Include slide references
            
        Returns:
            str: Generated notes content
        """
        if format_type == 'markdown':
            return self._generate_markdown(transcript, slides, include_timestamps, include_slides)
        elif format_type == 'html':
            return self._generate_html(transcript, slides, include_timestamps, include_slides)
        else:
            return self._generate_text(transcript, slides, include_timestamps, include_slides)
    
    def _generate_markdown(self, transcript: List[Dict], slides: List[str],
                          include_timestamps: bool, include_slides: bool) -> str:
        """Generate notes in Markdown format"""
        
        notes = []
        notes.append("# Lecture Notes\n")
        notes.append(f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n")
        notes.append("---\n\n")
        
        current_slide = 0
        
        for i, entry in enumerate(transcript):
            text = entry.get('text', '')
            speaker = entry.get('speaker', 'unknown')
            start_time = entry.get('start', '')
            
            # Add slide reference if available
            if include_slides and slides and current_slide < len(slides):
                # Heuristic: new slide every ~10 transcript entries
                if i % 10 == 0 and current_slide < len(slides):
                    notes.append(f"\n## Slide {current_slide + 1}\n")
                    notes.append(f"![Slide {current_slide + 1}]({slides[current_slide]})\n\n")
                    current_slide += 1
            
            # Add timestamp if requested
            if include_timestamps and start_time:
                notes.append(f"**[{start_time}]** ")
            
            # Format based on speaker
            if speaker == 'professor':
                notes.append(f"{text}\n\n")
            elif speaker == 'student':
                notes.append(f"> **Student Question:** {text}\n\n")
            else:
                notes.append(f"{text}\n\n")
        
        return ''.join(notes)
    
    def _generate_html(self, transcript: List[Dict], slides: List[str],
                      include_timestamps: bool, include_slides: bool) -> str:
        """Generate notes in HTML format"""
        
        html = []
        html.append("""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Lecture Notes</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }
        h1 {
            color: #333;
            border-bottom: 2px solid #333;
        }
        .timestamp {
            color: #666;
            font-size: 0.9em;
        }
        .student-question {
            background: #f0f0f0;
            border-left: 4px solid #0066cc;
            padding: 10px;
            margin: 10px 0;
        }
        .slide {
            max-width: 100%;
            margin: 20px 0;
        }
        .slide img {
            max-width: 100%;
            border: 1px solid #ddd;
        }
    </style>
</head>
<body>
""")
        
        html.append(f"<h1>Lecture Notes</h1>")
        html.append(f"<p><em>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}</em></p>")
        html.append("<hr>")
        
        current_slide = 0
        
        for i, entry in enumerate(transcript):
            text = entry.get('text', '')
            speaker = entry.get('speaker', 'unknown')
            start_time = entry.get('start', '')
            
            # Add slide if available
            if include_slides and slides and i % 10 == 0 and current_slide < len(slides):
                html.append(f'<div class="slide">')
                html.append(f'<h2>Slide {current_slide + 1}</h2>')
                html.append(f'<img src="{slides[current_slide]}" alt="Slide {current_slide + 1}">')
                html.append('</div>')
                current_slide += 1
            
            # Add content
            if speaker == 'student':
                html.append('<div class="student-question">')
                if include_timestamps and start_time:
                    html.append(f'<span class="timestamp">[{start_time}]</span> ')
                html.append(f'<strong>Student Question:</strong> {text}')
                html.append('</div>')
            else:
                html.append('<p>')
                if include_timestamps and start_time:
                    html.append(f'<span class="timestamp">[{start_time}]</span> ')
                html.append(text)
                html.append('</p>')
        
        html.append("</body></html>")
        
        return ''.join(html)
    
    def _generate_text(self, transcript: List[Dict], slides: List[str],
                      include_timestamps: bool, include_slides: bool) -> str:
        """Generate notes in plain text format"""
        
        notes = []
        notes.append("LECTURE NOTES\n")
        notes.append(f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
        notes.append("=" * 70 + "\n\n")
        
        current_slide = 0
        
        for i, entry in enumerate(transcript):
            text = entry.get('text', '')
            speaker = entry.get('speaker', 'unknown')
            start_time = entry.get('start', '')
            
            # Add slide reference
            if include_slides and slides and i % 10 == 0 and current_slide < len(slides):
                notes.append(f"\n--- SLIDE {current_slide + 1} ---\n")
                notes.append(f"[See: {slides[current_slide]}]\n\n")
                current_slide += 1
            
            # Add timestamp
            if include_timestamps and start_time:
                notes.append(f"[{start_time}] ")
            
            # Format based on speaker
            if speaker == 'student':
                notes.append(f">> STUDENT QUESTION: {text}\n\n")
            else:
                notes.append(f"{text}\n\n")
        
        return ''.join(notes)
    
    def save_notes(self, content: str, filename: str, format_type: str = 'markdown') -> str:
        """
        Save notes to file
        
        Args:
            content (str): Notes content
            filename (str): Base filename (without extension)
            format_type (str): Format type
            
        Returns:
            str: Path to saved file
        """
        extensions = {
            'markdown': '.md',
            'html': '.html',
            'text': '.txt'
        }
        
        ext = extensions.get(format_type, '.txt')
        filepath = os.path.join(self.output_dir, f"{filename}{ext}")
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def generate_summary(self, transcript: List[Dict], max_length: int = 500) -> str:
        """
        Generate a summary of the lecture
        
        Args:
            transcript (list): Transcript entries
            max_length (int): Maximum summary length in words
            
        Returns:
            str: Summary text
        """
        # Extract all professor text
        professor_text = []
        for entry in transcript:
            if entry.get('speaker') == 'professor':
                professor_text.append(entry.get('text', ''))
        
        # Combine text
        full_text = ' '.join(professor_text)
        words = full_text.split()
        
        # Simple extractive summary - take first portion and key sentences
        if len(words) <= max_length:
            return full_text
        
        # Take first 30% and last 10%
        first_part_len = int(max_length * 0.7)
        last_part_len = max_length - first_part_len
        
        summary = ' '.join(words[:first_part_len]) + ' ... ' + ' '.join(words[-last_part_len:])
        
        return summary
