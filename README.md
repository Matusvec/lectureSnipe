# 📚 LectureSnipe

**Transform Panopto lectures into readable notes automatically**

LectureSnipe is an intelligent lecture note-taking application that extracts slides and transcripts from Panopto videos, filters out student questions and noise using smart speaker detection, and generates clean, organized notes in multiple formats.

## ✨ Features

- 🎯 **Smart URL Processing**: Simply paste a Panopto lecture link
- 🔐 **Authentication Support**: Handle password-protected lectures
- 🎤 **Speaker Detection**: Automatically distinguishes professor content from student questions
- 📊 **Slide Extraction**: Downloads lecture slides/images automatically
- 📝 **Multiple Output Formats**: Generate notes in Markdown, HTML, or plain text
- ⚙️ **Customizable Options**:
  - Include/exclude student questions
  - Add timestamps to notes
  - Choose different summarization styles (brief, detailed, key points)
- 🌐 **Web Interface**: Easy-to-use web UI
- 💻 **CLI Support**: Command-line interface for automation

## 🚀 Quick Start

### Installation

1. **Clone the repository**:
```bash
git clone https://github.com/Matusvec/lectureSnipe.git
cd lectureSnipe
```

2. **Install dependencies**:
```bash
pip install -r requirements.txt
```

3. **Configure environment** (optional):
```bash
cp .env.example .env
# Edit .env with your credentials
```

### Usage

#### Web Interface

1. **Start the web server**:
```bash
python app.py
```

2. **Open your browser** to `http://localhost:5000`

3. **Paste your Panopto URL** and configure options:
   - Enter your Panopto lecture URL
   - Optionally add username/password for locked lectures
   - Choose output format and options
   - Click "Generate Full Notes" or "Quick Summary"

#### Command Line Interface

```bash
# Basic usage
python cli.py "https://university.panopto.com/Panopto/Pages/Viewer.aspx?id=SESSION_ID"

# With authentication
python cli.py -u username -p password "PANOPTO_URL"

# Include student questions and timestamps
python cli.py --include-students --timestamps "PANOPTO_URL"

# Generate HTML notes without slides
python cli.py --format html --no-slides "PANOPTO_URL"

# Generate a quick summary
python cli.py --summary brief "PANOPTO_URL"
```

#### CLI Options

```
positional arguments:
  url                   Panopto lecture URL

optional arguments:
  -h, --help            Show help message
  -u, --username        Panopto username (for locked lectures)
  -p, --password        Panopto password
  -f, --format          Output format: markdown, html, text (default: markdown)
  --include-students    Include student questions in notes
  --timestamps          Include timestamps in notes
  --no-slides           Do not download slides
  --summary             Generate summary: brief, detailed, key_points
```

## 📋 Example Workflows

### Example 1: Quick Notes (Professor Only)
```bash
python cli.py "https://university.panopto.com/Panopto/Pages/Viewer.aspx?id=abc123"
```
This generates Markdown notes with professor content only.

### Example 2: Comprehensive Notes (Include Everything)
```bash
python cli.py --include-students --timestamps --format html "PANOPTO_URL"
```
This generates HTML notes including student questions and timestamps.

### Example 3: Key Points Summary
```bash
python cli.py --summary key_points "PANOPTO_URL"
```
This generates a bullet-point summary of key lecture points.

## 🏗️ Project Structure

```
lectureSnipe/
├── app.py                  # Flask web application
├── cli.py                  # Command-line interface
├── config.py              # Configuration management
├── panopto_parser.py      # URL parsing and validation
├── panopto_client.py      # Panopto API client
├── speaker_detector.py    # Smart speaker detection
├── note_generator.py      # Note formatting and generation
├── lecture_processor.py   # Main orchestrator
├── templates/
│   └── index.html        # Web UI template
├── requirements.txt       # Python dependencies
├── .env.example          # Environment template
└── output/               # Generated content
    ├── notes/           # Generated notes
    ├── slides/          # Downloaded slides
    └── transcripts/     # Extracted transcripts
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file (copy from `.env.example`):

```env
# Panopto Credentials
PANOPTO_USERNAME=your_username
PANOPTO_PASSWORD=your_password

# AI API Keys (Optional - for enhanced summarization)
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Application Settings
FLASK_SECRET_KEY=your_secret_key
OUTPUT_DIR=./output
```

## 🎯 How It Works

1. **URL Parsing**: Extracts session ID and server from Panopto URL
2. **Authentication**: Logs in to Panopto if credentials provided
3. **Transcript Extraction**: Downloads lecture captions/transcript
4. **Speaker Detection**: Uses pattern matching to classify professor vs student speech
5. **Slide Extraction**: Downloads slide images from the lecture
6. **Note Generation**: Combines transcript and slides into formatted notes
7. **Output**: Saves notes in your chosen format

## 🤖 Smart Features

### Speaker Detection

The speaker detector uses multiple techniques:
- Pattern matching for question indicators ("could you explain...")
- Keyword analysis for professor language ("therefore", "in conclusion")
- Sentence structure analysis
- Context from previous segments

### Filtering Options

- **Professor Only** (default): Clean notes with just lecture content
- **Include Students**: Keep student questions for context
- **Filter Noise**: Removes "[laughter]", "(inaudible)", etc.

### Summarization Types

- **Brief**: ~200 word summary
- **Detailed**: ~1000 word summary
- **Key Points**: Bullet-point list of important concepts

## 📦 Dependencies

- **Flask**: Web framework
- **requests**: HTTP client
- **beautifulsoup4**: HTML parsing
- **python-dotenv**: Environment configuration
- **Pillow**: Image processing

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is for educational purposes. Ensure you have the right to access and download content from Panopto lectures. Respect copyright and institutional policies.

## 🐛 Troubleshooting

### "Could not retrieve transcript"
- Check if the lecture URL is correct
- Verify the lecture is not private/locked
- If locked, provide valid credentials

### "Authentication failed"
- Verify username and password are correct
- Check if your institution uses SSO (may require different auth method)

### "No slides downloaded"
- Some lectures may not have slides
- Check if slide extraction is enabled
- Verify you have permission to access the content

## 📧 Support

For issues or questions, please open an issue on GitHub.
