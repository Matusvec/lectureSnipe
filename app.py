"""
Flask web application for LectureSnipe
"""

from flask import Flask, render_template, request, jsonify, send_file, redirect, url_for
import os
from lecture_processor import LectureProcessor
from config import Config

app = Flask(__name__)
app.config['SECRET_KEY'] = Config.SECRET_KEY

# Initialize processor
processor = None


@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')


@app.route('/api/process', methods=['POST'])
def process_lecture():
    """
    API endpoint to process a Panopto lecture
    
    Expected JSON payload:
    {
        "url": "panopto_url",
        "username": "optional_username",
        "password": "optional_password",
        "include_students": false,
        "format": "markdown",
        "include_timestamps": false,
        "download_slides": true
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({'error': 'No URL provided'}), 400
        
        # Get parameters
        panopto_url = data.get('url')
        username = data.get('username') or Config.PANOPTO_USERNAME
        password = data.get('password') or Config.PANOPTO_PASSWORD
        include_students = data.get('include_students', False)
        format_type = data.get('format', 'markdown')
        include_timestamps = data.get('include_timestamps', False)
        download_slides = data.get('download_slides', True)
        
        # Initialize processor with credentials
        proc = LectureProcessor(username, password)
        
        # Process lecture
        result = proc.process_lecture(
            panopto_url,
            include_students=include_students,
            format_type=format_type,
            include_timestamps=include_timestamps,
            download_slides=download_slides
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'message': 'Lecture processed successfully',
                'notes_path': result['notes_path'],
                'session_id': result.get('session_id'),
                'stats': {
                    'transcript_entries': result.get('transcript_entries', 0),
                    'slides_downloaded': result.get('slides_downloaded', 0)
                }
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error')
            }), 500
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/summary', methods=['POST'])
def generate_summary():
    """
    API endpoint to generate a custom summary
    
    Expected JSON payload:
    {
        "url": "panopto_url",
        "username": "optional_username",
        "password": "optional_password",
        "summary_type": "brief|detailed|key_points",
        "include_students": false
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({'error': 'No URL provided'}), 400
        
        panopto_url = data.get('url')
        username = data.get('username') or Config.PANOPTO_USERNAME
        password = data.get('password') or Config.PANOPTO_PASSWORD
        summary_type = data.get('summary_type', 'brief')
        include_students = data.get('include_students', False)
        
        # Initialize processor
        proc = LectureProcessor(username, password)
        
        # Generate summary
        result = proc.generate_custom_summary(
            panopto_url,
            summary_type=summary_type,
            include_students=include_students
        )
        
        if result['success']:
            return jsonify({
                'success': True,
                'summary': result['summary']
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error')
            }), 500
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/download/<path:filename>')
def download_file(filename):
    """Download generated notes"""
    try:
        filepath = os.path.join(Config.NOTES_DIR, filename)
        if os.path.exists(filepath):
            return send_file(filepath, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({'status': 'healthy'})


if __name__ == '__main__':
    # Initialize config
    Config.init_app()
    
    # Run app
    app.run(debug=True, host='0.0.0.0', port=5000)
