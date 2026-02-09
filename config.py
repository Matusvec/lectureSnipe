"""
LectureSnipe - Panopto Lecture Note Generator
Main application module
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Application configuration
class Config:
    """Application configuration"""
    
    # Panopto credentials
    PANOPTO_USERNAME = os.getenv('PANOPTO_USERNAME', '')
    PANOPTO_PASSWORD = os.getenv('PANOPTO_PASSWORD', '')
    
    # AI API keys
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '')
    
    # Flask settings
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Output directories
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', './output')
    SLIDES_DIR = os.path.join(OUTPUT_DIR, 'slides')
    TRANSCRIPTS_DIR = os.path.join(OUTPUT_DIR, 'transcripts')
    NOTES_DIR = os.path.join(OUTPUT_DIR, 'notes')
    
    @staticmethod
    def init_app():
        """Initialize application directories"""
        for directory in [Config.OUTPUT_DIR, Config.SLIDES_DIR, 
                         Config.TRANSCRIPTS_DIR, Config.NOTES_DIR]:
            os.makedirs(directory, exist_ok=True)
