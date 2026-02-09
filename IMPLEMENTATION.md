# LectureSnipe Implementation Guide

## Overview

LectureSnipe is a comprehensive Panopto lecture note-taking application that transforms video lectures into readable, organized notes. This guide explains the architecture and implementation details.

## Architecture

### Component Design

The application follows a modular design with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────┐
│                    User Interfaces                       │
│  ┌─────────────────┐        ┌─────────────────┐        │
│  │  Web Interface  │        │  CLI Interface  │        │
│  │    (Flask)      │        │   (argparse)    │        │
│  └────────┬────────┘        └────────┬────────┘        │
└───────────┼──────────────────────────┼──────────────────┘
            │                          │
            └──────────┬───────────────┘
                       │
            ┌──────────▼──────────┐
            │ Lecture Processor   │  (Orchestrator)
            └──────────┬──────────┘
                       │
        ┌──────────────┼──────────────┐
        │              │              │
┌───────▼──────┐ ┌────▼─────┐ ┌──────▼──────┐
│ URL Parser   │ │ Panopto  │ │   Speaker   │
│              │ │  Client  │ │  Detector   │
└──────────────┘ └────┬─────┘ └──────┬──────┘
                      │              │
                      └──────┬───────┘
                             │
                    ┌────────▼────────┐
                    │ Note Generator  │
                    └─────────────────┘
```

### Module Descriptions

#### 1. `panopto_parser.py`
**Purpose**: Parse and validate Panopto URLs

**Key Functions**:
- `extract_session_id(url)`: Extract session ID from URL
- `extract_server(url)`: Get Panopto server domain
- `is_valid_panopto_url(url)`: Validate URL format

**Example**:
```python
from panopto_parser import PanoptoParser

url = "https://university.panopto.com/Panopto/Pages/Viewer.aspx?id=abc123"
session_id = PanoptoParser.extract_session_id(url)  # Returns: "abc123"
```

#### 2. `panopto_client.py`
**Purpose**: Interact with Panopto API for data extraction

**Key Features**:
- Authentication with username/password
- Transcript/caption retrieval
- Slide image extraction
- VTT format parsing

**Authentication Flow**:
```python
from panopto_client import PanoptoClient

client = PanoptoClient("university.panopto.com", "username", "password")
if client.authenticate():
    transcript = client.get_transcript(session_id)
    slides = client.get_slide_images(session_id)
```

#### 3. `speaker_detector.py`
**Purpose**: Classify speakers and filter content

**Detection Algorithm**:
1. **Pattern Matching**: Uses regex patterns to identify:
   - Student questions: "could you", "what if", "can you explain"
   - Professor content: "therefore", "in conclusion", "let's"
   - Noise: "[laughter]", "(inaudible)", "um"

2. **Scoring System**: Assigns scores based on pattern matches
   - Student patterns: +1 per match
   - Professor patterns: +1 per match
   - Custom keywords: +2 per match

3. **Context Awareness**: Uses previous speaker to handle ambiguous segments

**Example**:
```python
from speaker_detector import SpeakerDetector

detector = SpeakerDetector()

# Classify individual segments
text = "Could you explain that again?"
speaker = detector.classify_segment(text)  # Returns: "student"

# Filter entire transcript
filtered = detector.filter_transcript(transcript, include_students=False)
```

#### 4. `note_generator.py`
**Purpose**: Format and generate notes in multiple formats

**Output Formats**:
- **Markdown**: Clean, readable format with headers and bullet points
- **HTML**: Styled web page with CSS
- **Plain Text**: Simple text format

**Features**:
- Timestamp inclusion
- Slide integration
- Student question highlighting
- Summary generation

**Example**:
```python
from note_generator import NoteGenerator

generator = NoteGenerator("./output/notes")

notes = generator.generate_notes(
    transcript,
    slides=slide_paths,
    format_type='markdown',
    include_timestamps=True
)

path = generator.save_notes(notes, 'my_lecture', 'markdown')
```

#### 5. `lecture_processor.py`
**Purpose**: Orchestrate the entire workflow

**Process Flow**:
```
1. Parse URL → Extract session ID and server
2. Authenticate → Login with credentials (if provided)
3. Get Transcript → Download captions/transcript
4. Get Slides → Download slide images
5. Detect Speakers → Classify professor vs student
6. Filter Content → Remove noise and optional student questions
7. Generate Notes → Format in chosen output type
8. Save → Write to file
```

**Example**:
```python
from lecture_processor import LectureProcessor

processor = LectureProcessor(username="user", password="pass")

result = processor.process_lecture(
    panopto_url="https://...",
    include_students=False,
    format_type='markdown',
    download_slides=True
)

if result['success']:
    print(f"Notes saved to: {result['notes_path']}")
```

## Smart Speaker Detection

### Detection Patterns

**Professor Indicators**:
- Transition words: "therefore", "thus", "hence", "so"
- Teaching phrases: "let's", "we will", "notice that"
- Emphasis: "important", "key point", "remember"
- Conclusions: "in summary", "to recap", "in conclusion"

**Student Indicators**:
- Questions: "could you", "can you", "would you"
- Uncertainty: "I don't understand", "confused", "wondering"
- Hypotheticals: "what if", "what about", "how about"
- Politeness: "excuse me", "sorry"

**Noise Patterns**:
- Bracketed text: `[laughter]`, `[applause]`
- Parenthetical: `(inaudible)`, `(crosstalk)`
- Filler words in isolation: "um", "uh", "like"

### Classification Logic

```python
def classify_segment(text, previous_speaker=None):
    # 1. Check if noise
    if is_noise(text):
        return 'noise'
    
    # 2. Count pattern matches
    student_score = count_student_patterns(text)
    professor_score = count_professor_patterns(text)
    
    # 3. Apply heuristics
    if has_question_mark(text):
        student_score += 1
    
    if len(text.split()) > 30:  # Long segments tend to be professor
        professor_score += 1
    
    # 4. Decide based on scores
    if professor_score > student_score:
        return 'professor'
    elif student_score > professor_score:
        return 'student'
    else:
        # Use context as tie-breaker
        return previous_speaker or 'unknown'
```

## Configuration

### Environment Variables

The application uses `.env` file for configuration:

```env
# Panopto Authentication
PANOPTO_USERNAME=your_username
PANOPTO_PASSWORD=your_password

# AI API Keys (for future enhancements)
OPENAI_API_KEY=your_key
ANTHROPIC_API_KEY=your_key

# Application Settings
FLASK_SECRET_KEY=random_secret_key
OUTPUT_DIR=./output
```

### Directory Structure

```
output/
├── notes/         # Generated notes (MD, HTML, TXT)
├── slides/        # Downloaded slide images
└── transcripts/   # Raw transcript data
```

## API Endpoints

### Web API (Flask)

**POST `/api/process`**
Process a Panopto lecture and generate notes

Request:
```json
{
  "url": "https://university.panopto.com/...",
  "username": "optional",
  "password": "optional",
  "include_students": false,
  "format": "markdown",
  "include_timestamps": false,
  "download_slides": true
}
```

Response:
```json
{
  "success": true,
  "notes_path": "/path/to/notes.md",
  "session_id": "abc123",
  "stats": {
    "transcript_entries": 150,
    "slides_downloaded": 25
  }
}
```

**POST `/api/summary`**
Generate a quick summary

Request:
```json
{
  "url": "https://university.panopto.com/...",
  "summary_type": "brief",
  "include_students": false
}
```

Response:
```json
{
  "success": true,
  "summary": "Lecture summary text..."
}
```

## Testing

### Test Suite

The test suite (`test_lecturesnipe.py`) covers:

1. **URL Parsing Tests**
   - Valid URLs (Viewer and Embed formats)
   - Invalid URLs (no Panopto, no session ID)

2. **Speaker Detection Tests**
   - Professor classification
   - Student classification
   - Noise detection
   - Transcript filtering
   - Key point extraction

3. **Note Generation Tests**
   - Markdown generation
   - HTML generation
   - Text generation
   - Timestamp inclusion
   - Student question formatting
   - File saving

### Running Tests

```bash
python test_lecturesnipe.py
```

Expected output:
```
test_invalid_url_no_panopto ... ok
test_valid_url_viewer ... ok
test_professor_classification ... ok
...
----------------------------------------------------------------------
Ran 17 tests in 0.004s

OK
```

## Future Enhancements

Potential improvements for the application:

1. **AI-Powered Summarization**
   - Integration with OpenAI or Anthropic for better summaries
   - Topic extraction and organization
   - Automatic quiz generation

2. **Enhanced Speaker Detection**
   - Machine learning model for better accuracy
   - Voice recognition integration
   - Multi-speaker identification

3. **Additional Features**
   - PDF export with embedded images
   - Flashcard generation
   - Search functionality across notes
   - Note sharing and collaboration

4. **Performance Optimization**
   - Async processing for large lectures
   - Caching for repeated requests
   - Batch processing support

5. **User Experience**
   - Progress indicators
   - Preview before download
   - Customizable templates
   - Dark mode

## Troubleshooting

### Common Issues

**1. "Could not retrieve transcript"**
- Lecture may be private/locked
- Provide valid credentials
- Check if transcript is available in Panopto

**2. "Authentication failed"**
- Verify username and password
- Some institutions use SSO (not supported yet)
- Check if account has access to the lecture

**3. "No slides downloaded"**
- Some lectures don't have slides
- Slides may be embedded differently
- Try without slides: `--no-slides`

**4. Import errors**
- Ensure all dependencies installed: `pip install -r requirements.txt`
- Check Python version: 3.8+

## Contributing

When contributing to LectureSnipe:

1. **Code Style**: Follow PEP 8 guidelines
2. **Testing**: Add tests for new features
3. **Documentation**: Update this guide for major changes
4. **Commits**: Write clear, descriptive commit messages

## License

MIT License - See LICENSE file for details
