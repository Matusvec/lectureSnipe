#!/usr/bin/env python3
"""
Command-line interface for LectureSnipe
"""

import argparse
import sys
from lecture_processor import LectureProcessor
from config import Config


def main():
    """Main CLI function"""
    
    parser = argparse.ArgumentParser(
        description='LectureSnipe - Convert Panopto lectures to readable notes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python cli.py "https://university.panopto.com/Panopto/Pages/Viewer.aspx?id=abc123"
  
  # With authentication
  python cli.py -u username -p password "https://university.panopto.com/..."
  
  # Include student questions and timestamps
  python cli.py --include-students --timestamps "https://university.panopto.com/..."
  
  # Generate HTML notes without slides
  python cli.py --format html --no-slides "https://university.panopto.com/..."
  
  # Generate a quick summary
  python cli.py --summary brief "https://university.panopto.com/..."
        """
    )
    
    parser.add_argument('url', help='Panopto lecture URL')
    parser.add_argument('-u', '--username', help='Panopto username (for locked lectures)')
    parser.add_argument('-p', '--password', help='Panopto password')
    parser.add_argument('-f', '--format', 
                       choices=['markdown', 'html', 'text'],
                       default='markdown',
                       help='Output format (default: markdown)')
    parser.add_argument('--include-students', action='store_true',
                       help='Include student questions in notes')
    parser.add_argument('--timestamps', action='store_true',
                       help='Include timestamps in notes')
    parser.add_argument('--no-slides', action='store_true',
                       help='Do not download slides')
    parser.add_argument('--summary', 
                       choices=['brief', 'detailed', 'key_points'],
                       help='Generate summary instead of full notes')
    
    args = parser.parse_args()
    
    # Initialize config
    Config.init_app()
    
    # Initialize processor
    processor = LectureProcessor(args.username, args.password)
    
    print("=" * 70)
    print("LectureSnipe - Panopto Lecture Note Generator")
    print("=" * 70)
    print()
    
    if args.summary:
        # Generate summary
        print(f"Generating {args.summary} summary...")
        print()
        
        result = processor.generate_custom_summary(
            args.url,
            summary_type=args.summary,
            include_students=args.include_students
        )
        
        if result['success']:
            print("Summary:")
            print("-" * 70)
            print(result['summary'])
            print("-" * 70)
            print()
            print("✓ Summary generated successfully")
        else:
            print(f"✗ Error: {result['error']}")
            sys.exit(1)
    
    else:
        # Generate full notes
        print(f"Processing lecture from URL: {args.url}")
        print(f"Format: {args.format}")
        print(f"Include students: {args.include_students}")
        print(f"Include timestamps: {args.timestamps}")
        print(f"Download slides: {not args.no_slides}")
        print()
        
        result = processor.process_lecture(
            args.url,
            include_students=args.include_students,
            format_type=args.format,
            include_timestamps=args.timestamps,
            download_slides=not args.no_slides
        )
        
        if result['success']:
            print()
            print("=" * 70)
            print("✓ Lecture processed successfully!")
            print("=" * 70)
            print()
            print(f"Notes saved to: {result['notes_path']}")
            print(f"Transcript entries: {result['transcript_entries']}")
            print(f"Slides downloaded: {result['slides_downloaded']}")
            print()
        else:
            print()
            print(f"✗ Error: {result['error']}")
            print()
            sys.exit(1)


if __name__ == '__main__':
    main()
