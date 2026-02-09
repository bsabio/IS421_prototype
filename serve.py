#!/usr/bin/env python3
"""
Simple web server to view the newsletter
Usage: python3 serve.py
Then open: http://localhost:8000
"""
import http.server
import socketserver
import webbrowser
from pathlib import Path
import sys

PORT = 8000

class NewsletterHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler that serves from output directory"""
    
    def __init__(self, *args, **kwargs):
        # Change to output directory
        super().__init__(*args, directory="output", **kwargs)
    
    def end_headers(self):
        # Add headers to prevent caching during development
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Expires', '0')
        super().end_headers()


def main():
    # Check if newsletter exists
    output_dir = Path("output")
    html_file = output_dir / "newsletter.html"
    
    if not html_file.exists():
        print("❌ Newsletter not found!")
        print()
        print("Generate it first:")
        print("  python3 -m newsroom.collect --source mock")
        print("  python3 -m newsroom.rank")
        print("  python3 -m newsroom.render --format html")
        print()
        sys.exit(1)
    
    # Start server
    Handler = NewsletterHTTPRequestHandler
    
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            url = f"http://localhost:{PORT}/newsletter.html"
            
            print(f"🚀 AI Factory Newsletter Server")
            print(f"=" * 50)
            print(f"Server running at: {url}")
            print(f"Press Ctrl+C to stop")
            print()
            
            # Try to open browser
            try:
                webbrowser.open(url)
                print("✓ Opening in your default browser...")
            except:
                print(f"📱 Open this URL in your browser: {url}")
            
            print()
            httpd.serve_forever()
            
    except KeyboardInterrupt:
        print("\n\n✓ Server stopped")
        sys.exit(0)
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {PORT} is already in use!")
            print(f"   Try a different port or stop the other server.")
        else:
            print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
